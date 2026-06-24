"""
Production-Ready Email Service for Expense Tracker
===================================================
A scalable, secure email notification system with:
- HTML email templates with plain text fallback
- Asynchronous sending via Celery
- Anti-spam protection (rate limiting)
- Comprehensive logging
- Django best practices

Events that trigger emails:
- Daily limit exceeded
- Goal achieved
- Suspicious login
- Password changed
- Large unusual transaction
"""

import logging
import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.contrib.auth import get_user_model

# Celery import (optional - will fallback to sync if not available)
try:
    from celery import shared_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    # Create a dummy decorator for sync mode
    def shared_task(func):
        return func

# Configure logging
logger = logging.getLogger(__name__)

# Rate limiting cache (in production, use Redis)
_email_rate_cache: Dict[str, datetime] = {}

# Email rate limit in seconds (configurable via settings)
EMAIL_RATE_LIMIT = getattr(settings, 'EMAIL_RATE_LIMIT_SECONDS', 300)


class EmailType:
    """Email type constants"""
    DAILY_LIMIT_EXCEEDED = 'daily_limit_exceeded'
    GOAL_ACHIEVED = 'goal_achieved'
    SUSPICIOUS_LOGIN = 'suspicious_login'
    PASSWORD_CHANGED = 'password_changed'
    LARGE_TRANSACTION = 'large_transaction'
    DAILY_SUMMARY = 'daily_summary'


def _get_user_display_name(user) -> str:
    """Get user display name"""
    if hasattr(user, 'get_full_name') and user.get_full_name():
        return user.get_full_name()
    return user.username


def _get_user_email(user) -> Optional[str]:
    """Get user email address"""
    if hasattr(user, 'email') and user.email:
        return user.email
    
    # Try get_user_model if user is not the model
    User = get_user_model()
    if isinstance(user, int):
        try:
            user_obj = User.objects.get(pk=user)
            return user_obj.email
        except User.DoesNotExist:
            return None
    return None


def _generate_email_key(user_id: int, email_type: str) -> str:
    """Generate unique key for rate limiting"""
    return f"{user_id}:{email_type}"


def _check_rate_limit(user_id: int, email_type: str) -> bool:
    """
    Check if email can be sent based on rate limiting
    Returns True if email can be sent, False if rate limited
    """
    key = _generate_email_key(user_id, email_type)
    now = datetime.now()
    
    if key in _email_rate_cache:
        last_sent = _email_rate_cache[key]
        if (now - last_sent).total_seconds() < EMAIL_RATE_LIMIT:
            logger.warning(
                f"Email rate limited for user {user_id}, type {email_type}. "
                f"Last sent: {last_sent}"
            )
            return False
    
    return True


def _update_rate_limit(user_id: int, email_type: str) -> None:
    """Update rate limit cache after sending email"""
    key = _generate_email_key(user_id, email_type)
    _email_rate_cache[key] = datetime.now()


def _log_email_attempt(email_type: str, recipient: str, success: bool, 
                       error: Optional[str] = None) -> None:
    """Log email delivery attempts"""
    if success:
        logger.info(
            f"Email sent successfully | Type: {email_type} | "
            f"Recipient: {recipient} | Time: {datetime.now()}"
        )
    else:
        logger.error(
            f"Email failed | Type: {email_type} | "
            f"Recipient: {recipient} | Error: {error} | Time: {datetime.now()}"
        )


def _get_email_subject(email_type: str, context: Dict[str, Any]) -> str:
    """Get subject line based on email type"""
    subjects = {
        EmailType.DAILY_LIMIT_EXCEEDED: "⚠️ Daily Expense Limit Exceeded",
        EmailType.GOAL_ACHIEVED: "🎉 Congratulations! Goal Achieved!",
        EmailType.SUSPICIOUS_LOGIN: "🔐 Suspicious Login Detected",
        EmailType.PASSWORD_CHANGED: "🔒 Password Changed Successfully",
        EmailType.LARGE_TRANSACTION: "💰 Large Transaction Alert",
        EmailType.DAILY_SUMMARY: "📊 Your Daily Spending Summary",
    }
    return subjects.get(email_type, "ExpenseWise Notification")


def _render_email_template(email_type: str, context: Dict[str, Any]) -> Dict[str, str]:
    """
    Render HTML and plain text email content
    Returns dict with 'html' and 'text' keys
    """
    template_mapping = {
        EmailType.DAILY_LIMIT_EXCEEDED: 'emails/daily_limit_exceeded.html',
        EmailType.GOAL_ACHIEVED: 'emails/goal_achieved.html',
        EmailType.SUSPICIOUS_LOGIN: 'emails/suspicious_login.html',
        EmailType.PASSWORD_CHANGED: 'emails/password_changed.html',
        EmailType.LARGE_TRANSACTION: 'emails/large_transaction.html',
        EmailType.DAILY_SUMMARY: 'emails/daily_summary.html',
    }
    
    template_name = template_mapping.get(email_type)
    
    if template_name:
        try:
            html_content = render_to_string(template_name, context)
            text_content = strip_tags(html_content)
            return {'html': html_content, 'text': text_content}
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
    
    # Fallback to generic template
    html_content = render_to_string('emails/generic_notification.html', context)
    text_content = strip_tags(html_content)
    return {'html': html_content, 'text': text_content}


def _send_email_internal(
    user_id: int,
    email_type: str,
    context: Dict[str, Any],
    force_send: bool = False
) -> bool:
    """
    Internal function to send email with all production features
    
    Args:
        user_id: User ID to send email to
        email_type: Type of email (from EmailType class)
        context: Template context variables
        force_send: Skip rate limiting (use carefully)
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # Check rate limit unless force_send is True
    if not force_send and not _check_rate_limit(user_id, email_type):
        return False
    
    # Get user email
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        _log_email_attempt(email_type, f"user_id:{user_id}", False, "User not found")
        return False
    
    recipient_email = _get_user_email(user)
    if not recipient_email:
        _log_email_attempt(email_type, f"user_id:{user_id}", False, "No email address")
        return False
    
    # Add user info to context
    context['user'] = user
    context['user_name'] = _get_user_display_name(user)
    context['email_type'] = email_type
    context['site_url'] = getattr(settings, 'SITE_URL', 'http://localhost:8000')
    context['current_year'] = datetime.now().year
    
    # Render email content
    content = _render_email_template(email_type, context)
    subject = _get_email_subject(email_type, context)
    
    try:
        # Create email message
        message = EmailMultiAlternatives(
            subject=subject,
            body=content['text'],
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        
        # Attach HTML content
        message.attach_alternative(content['html'], 'text/html')
        
        # Send email
        message.send(fail_silently=False)
        
        # Update rate limit
        _update_rate_limit(user_id, email_type)
        
        # Log success
        _log_email_attempt(email_type, recipient_email, True)
        
        return True
        
    except Exception as e:
        _log_email_attempt(email_type, recipient_email, False, str(e))
        return False


# ===========================================
# Async Email Tasks (Celery)
# ===========================================

if CELERY_AVAILABLE:
    
    @shared_task(
        bind=True,
        max_retries=3,
        default_retry_delay=60,
        autoretry_for=(Exception,),
        retry_backoff=True
    )
    def send_email_task(self, user_id: int, email_type: str, 
                        context: Dict[str, Any], force_send: bool = False) -> bool:
        """Celery task for async email sending"""
        return _send_email_internal(user_id, email_type, context, force_send)
    
    def send_email(user_id: int, email_type: str, 
                  context: Dict[str, Any], force_send: bool = False) -> bool:
        """Send email asynchronously via Celery"""
        return send_email_task.delay(user_id, email_type, context, force_send)

else:
    
    def send_email(user_id: int, email_type: str, 
                   context: Dict[str, Any], force_send: bool = False) -> bool:
        """Send email synchronously (fallback when Celery not available)"""
        return _send_email_internal(user_id, email_type, context, force_send)


# ===========================================
# Convenience Functions for Specific Events
# ===========================================

def send_daily_limit_exceeded_email(user_id: int, limit: float, spent: float, 
                                   date: datetime) -> bool:
    """Send daily limit exceeded notification"""
    context = {
        'limit': limit,
        'spent': spent,
        'overage': spent - limit,
        'date': date.strftime('%B %d, %Y'),
    }
    return send_email(user_id, EmailType.DAILY_LIMIT_EXCEEDED, context)


def send_goal_achieved_email(user_id: int, goal_name: str, target_amount: float,
                            current_amount: float, goal_id: int) -> bool:
    """Send goal achieved notification"""
    context = {
        'goal_name': goal_name,
        'target_amount': target_amount,
        'current_amount': current_amount,
        'goal_id': goal_id,
        'achievement_date': datetime.now().strftime('%B %d, %Y'),
    }
    # Force send for important notifications
    return send_email(user_id, EmailType.GOAL_ACHIEVED, context, force_send=True)


def send_suspicious_login_email(user_id: int, ip_address: str, 
                                location: str, device: str, timestamp: datetime) -> bool:
    """Send suspicious login alert"""
    context = {
        'ip_address': ip_address,
        'location': location,
        'device': device,
        'timestamp': timestamp.strftime('%B %d, %Y at %I:%M %p'),
        'user_agent': device,
    }
    # Force send for security notifications
    return send_email(user_id, EmailType.SUSPICIOUS_LOGIN, context, force_send=True)


def send_password_changed_email(user_id: int, timestamp: datetime, 
                                ip_address: Optional[str] = None) -> bool:
    """Send password changed confirmation"""
    context = {
        'timestamp': timestamp.strftime('%B %d, %Y at %I:%M %p'),
        'ip_address': ip_address or 'Unknown',
        'change_date': timestamp.strftime('%B %d, %Y'),
    }
    # Force send for security notifications
    return send_email(user_id, EmailType.PASSWORD_CHANGED, context, force_send=True)


def send_large_transaction_email(user_id: int, amount: float, 
                                 transaction_type: str, description: str,
                                 timestamp: datetime, threshold: float) -> bool:
    """Send large/unusual transaction alert"""
    context = {
        'amount': amount,
        'transaction_type': transaction_type,
        'description': description,
        'timestamp': timestamp.strftime('%B %d, %Y at %I:%M %p'),
        'threshold': threshold,
        'is_unusual': amount > threshold * 2,  # 2x threshold = unusual
    }
    return send_email(user_id, EmailType.LARGE_TRANSACTION, context)


def send_daily_summary_email(user_id: int, total: float, date: datetime,
                             currency_symbol: str = '₹') -> bool:
    """Send daily spending summary email"""
    context = {
        'total': total,
        'date': date.strftime('%B %d, %Y'),
        'currency_symbol': currency_symbol,
        'formatted_total': f"{currency_symbol}{total:,.2f}",
    }
    return send_email(user_id, EmailType.DAILY_SUMMARY, context)


# ===========================================
# Bulk Email (for admins)
# ===========================================

def send_bulk_email(user_ids: List[int], email_type: str, 
                   context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send bulk emails to multiple users
    Returns summary of success/failure counts
    """
    results = {'success': 0, 'failed': 0, 'rate_limited': 0}
    
    for user_id in user_ids:
        success = send_email(user_id, email_type, context)
        if success:
            results['success'] += 1
        else:
            # Check if it was rate limited
            if not _check_rate_limit(user_id, email_type):
                results['rate_limited'] += 1
            else:
                results['failed'] += 1
    
    logger.info(f"Bulk email completed: {results}")
    return results


# ===========================================
# Health Check
# ===========================================

def test_email_configuration() -> Dict[str, Any]:
    """
    Test email configuration
    Returns dict with status and details
    """
    result = {
        'status': 'unknown',
        'email_backend': getattr(settings, 'EMAIL_BACKEND', 'Not configured'),
        'email_host': getattr(settings, 'EMAIL_HOST', 'Not configured'),
        'default_from': getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not configured'),
        'celery_available': CELERY_AVAILABLE,
    }
    
    try:
        # Test email sending
        send_mail(
            subject='ExpenseWise - Test Email',
            message='This is a test email from ExpenseWise.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.DEFAULT_FROM_EMAIL],  # Send to self
            fail_silently=False,
        )
        result['status'] = 'success'
        result['message'] = 'Test email sent successfully'
    except Exception as e:
        result['status'] = 'error'
        result['message'] = str(e)
    
    return result
