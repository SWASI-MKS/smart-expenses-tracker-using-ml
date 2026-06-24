"""
Production-ready Notification Service for Expense Tracker
=========================================================
Features:
- Anti-duplicate logic based on event type and context
- Automatic email trigger for critical/warning events
- Batch operations for performance
- Scalable design with database indexes
"""

import hashlib
import logging
from datetime import timedelta
from typing import Optional, List, Dict, Any
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings

from .models import Notification

User = get_user_model()
logger = logging.getLogger(__name__)


# ============================================================
# Event Configuration - Define which events trigger notifications
# ============================================================

class EventConfig:
    """Configuration for notification events"""
    
    # Map event types to notification types and email settings
    EVENT_SETTINGS = {
        # SUCCESS - Store only, no email
        'expense_added': {'type': 'success', 'send_email': False},
        'expense_updated': {'type': 'success', 'send_email': False},
        'expense_deleted': {'type': 'success', 'send_email': False},
        'goal_created': {'type': 'success', 'send_email': False},
        'limit_updated': {'type': 'success', 'send_email': False},
        'login_success': {'type': 'success', 'send_email': False},
        
        # WARNING - Store only
        'daily_limit_80': {'type': 'warning', 'send_email': False},
        'goal_near_deadline': {'type': 'warning', 'send_email': False},
        'goal_overdue': {'type': 'warning', 'send_email': False},
        'goal_completed': {'type': 'success', 'send_email': False},
        
        # WARNING - Store + Email
        'daily_limit_exceeded': {'type': 'warning', 'send_email': True},
        'monthly_limit_exceeded': {'type': 'warning', 'send_email': True},
        
        # ERROR - Store only
        'invalid_input': {'type': 'error', 'send_email': False},
        'future_date': {'type': 'error', 'send_email': False},
        'voice_recognition_failed': {'type': 'error', 'send_email': False},
        'insufficient_balance': {'type': 'error', 'send_email': False},
        
        # INFO - Store only
        'no_expenses': {'type': 'info', 'send_email': False},
        'no_search_results': {'type': 'info', 'send_email': False},
        'listening_started': {'type': 'info', 'send_email': False},
        
        # CRITICAL - Store + Email
        'suspicious_login': {'type': 'critical', 'send_email': True},
        'password_changed': {'type': 'critical', 'send_email': True},
        'large_transaction': {'type': 'critical', 'send_email': True},
    }
    
    # Anti-duplicate window (in minutes) - prevents duplicate notifications within this window
    DUPLICATE_WINDOW_MINUTES = {
        'expense_added': 60,        # 1 hour
        'expense_updated': 60,
        'expense_deleted': 60,
        'daily_limit_80': 30,       # 30 minutes
        'daily_limit_exceeded': 60,
        'monthly_limit_exceeded': 60,
        'suspicious_login': 0,      # Always create (security)
        'password_changed': 0,      # Always create (security)
        'large_transaction': 30,
        'goal_near_deadline': 1440,  # 24 hours
        'goal_created': 0,           # Always create
        'goal_overdue': 1440,        # 24 hours (one notification per day)
        'goal_completed': 0,         # Always create (celebration)
    }
    
    # Default window for events not specified
    DEFAULT_DUPLICATE_WINDOW = 60  # 1 hour
    
    @classmethod
    def get_settings(cls, event_type: str) -> Dict[str, Any]:
        """Get notification settings for an event type"""
        return cls.EVENT_SETTINGS.get(event_type, {
            'type': 'info',
            'send_email': False
        })
    
    @classmethod
    def get_duplicate_window(cls, event_type: str) -> int:
        """Get duplicate window in minutes"""
        return cls.DUPLICATE_WINDOW_MINUTES.get(
            event_type, 
            cls.DEFAULT_DUPLICATE_WINDOW
        )


# ============================================================
# Notification Service
# ============================================================

class NotificationService:
    """
    Production-ready notification service with anti-duplicate logic.
    
    Usage:
        # Create notification
        NotificationService.create(
            user=request.user,
            event_type='expense_added',
            title='Expense Added',
            message='Your expense of ₹500 has been added.'
        )
        
        # Get unread count
        count = NotificationService.get_unread_count(user)
        
        # Mark as read
        NotificationService.mark_as_read(notification_id)
        
        # Mark all as read
        NotificationService.mark_all_as_read(user)
    """
    
    @staticmethod
    def generate_event_hash(user_id: int, event_type: str, **context) -> str:
        """Generate unique hash for duplicate detection"""
        hash_input = f"{user_id}:{event_type}"
        for key, value in sorted(context.items()):
            hash_input += f":{key}:{value}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    @staticmethod
    def is_duplicate(user_id: int, event_type: str, window_minutes: int, **context) -> bool:
        """
        Check if similar notification exists within the duplicate window.
        Returns True if duplicate exists, False otherwise.
        """
        if window_minutes == 0:
            # Never treat as duplicate (for security events)
            return False
        
        event_hash = NotificationService.generate_event_hash(user_id, event_type, **context)
        cutoff_time = timezone.now() - timedelta(minutes=window_minutes)
        
        return Notification.objects.filter(
            user_id=user_id,
            event_type=event_type,
            event_hash=event_hash,
            created_at__gte=cutoff_time
        ).exists()
    
    @classmethod
    def create(
        cls,
        user,
        event_type: str,
        title: str,
        message: str,
        send_email_override: Optional[bool] = None,
        related_object_id: Optional[int] = None,
        related_object_type: Optional[str] = None,
        **context
    ) -> Optional[Notification]:
        """
        Create a notification with anti-duplicate logic.
        
        Args:
            user: User instance or User ID
            event_type: Type of event (from EVENT_TYPES)
            title: Notification title
            message: Notification message
            send_email_override: Force email sending (optional)
            related_object_id: ID of related object (optional)
            related_object_type: Type of related object (optional)
            **context: Additional context for duplicate detection
            
        Returns:
            Notification object if created, None if duplicate
        """
        # Get user ID if user object passed
        user_id = user.id if hasattr(user, 'id') else user
        
        # Get event settings
        settings = EventConfig.get_settings(event_type)
        window_minutes = EventConfig.get_duplicate_window(event_type)
        
        # Check for duplicates
        if cls.is_duplicate(user_id, event_type, window_minutes, **context):
            logger.debug(f"Duplicate notification prevented: {event_type} for user {user_id}")
            return None
        
        # Determine if email should be sent
        send_email = send_email_override if send_email_override is not None else settings['send_email']
        
        # Generate event hash
        event_hash = cls.generate_event_hash(user_id, event_type, **context)
        
        # Create notification
        notification = Notification.objects.create(
            user_id=user_id,
            title=title,
            message=message,
            type=settings['type'],
            event_type=event_type,
            send_email=send_email,
            event_hash=event_hash,
            related_object_id=related_object_id,
            related_object_type=related_object_type
        )
        
        logger.info(f"Notification created: {event_type} for user {user_id}")
        
        # Trigger email if needed
        if send_email:
            cls._send_email_async(notification)
        
        return notification
    
    @staticmethod
    def _send_email_async(notification: Notification):
        """Send email asynchronously (or synchronously if Celery not available)"""
        try:
            # Import here to avoid circular imports
            from expenses.email_service import send_daily_limit_exceeded_email, send_suspicious_login_email, send_large_transaction_email
            
            if notification.event_type == 'daily_limit_exceeded':
                send_daily_limit_exceeded_email(notification.user, notification.message)
            elif notification.event_type == 'monthly_limit_exceeded':
                send_daily_limit_exceeded_email(notification.user, notification.message)
            elif notification.event_type == 'suspicious_login':
                send_suspicious_login_email(notification.user, notification.message)
            elif notification.event_type == 'password_changed':
                # Use generic notification for password change
                from expenses.email_service import send_generic_notification
                send_generic_notification(notification.user, notification.title, notification.message)
            elif notification.event_type == 'large_transaction':
                send_large_transaction_email(notification.user, notification.message)
                
        except Exception as e:
            logger.error(f"Failed to send email for notification {notification.id}: {e}")
    
    @staticmethod
    def get_unread_count(user) -> int:
        """Get count of unread notifications for a user"""
        return Notification.objects.filter(user=user, is_read=False).count()
    
    @staticmethod
    def get_notifications(user, limit: int = 50, include_read: bool = False):
        """Get notifications for a user"""
        qs = Notification.objects.filter(user=user)
        if not include_read:
            qs = qs.filter(is_read=False)
        return qs[:limit]
    
    @staticmethod
    def mark_as_read(notification_id: int, user=None) -> bool:
        """Mark a single notification as read"""
        try:
            notification = Notification.objects.get(id=notification_id)
            if user and notification.user != user:
                return False
            notification.is_read = True
            notification.save(update_fields=['is_read'])
            return True
        except Notification.DoesNotExist:
            return False
    
    @staticmethod
    def mark_all_as_read(user) -> int:
        """Mark all notifications as read for a user"""
        return Notification.objects.filter(user=user, is_read=False).update(is_read=True)
    
    @staticmethod
    def delete_old_notifications(days: int = 30) -> int:
        """Delete notifications older than specified days (cleanup)"""
        cutoff = timezone.now() - timedelta(days=days)
        return Notification.objects.filter(created_at__lt=cutoff).delete()[0]
    
    @staticmethod
    def get_unread_by_type(user, notification_type: str) -> List[Notification]:
        """Get unread notifications of a specific type"""
        return list(Notification.objects.filter(
            user=user,
            type=notification_type,
            is_read=False
        ))
    
    @classmethod
    def create_bulk(cls, notifications_data: List[Dict]) -> List[Notification]:
        """
        Create multiple notifications efficiently.
        
        Args:
            notifications_data: List of dicts with keys: user, event_type, title, message
            
        Returns:
            List of created Notification objects
        """
        created = []
        
        for data in notifications_data:
            notification = cls.create(
                user=data['user'],
                event_type=data['event_type'],
                title=data['title'],
                message=data['message'],
                send_email_override=data.get('send_email_override'),
                related_object_id=data.get('related_object_id'),
                related_object_type=data.get('related_object_type'),
                **data.get('context', {})
            )
            if notification:
                created.append(notification)
        
        return created


# ============================================================
# Convenience Functions - Simple API for common use cases
# ============================================================

def notify_expense_added(user, expense_amount: float, expense_category: str = None):
    """Notify when an expense is added"""
    category_text = f" in {expense_category}" if expense_category else ""
    return NotificationService.create(
        user=user,
        event_type='expense_added',
        title='Expense Added',
        message=f'Your expense of ₹{expense_amount}{category_text} has been added successfully.',
        expense_amount=expense_amount,
        expense_category=expense_category
    )

def notify_expense_updated(user, expense_amount: float):
    """Notify when an expense is updated"""
    return NotificationService.create(
        user=user,
        event_type='expense_updated',
        title='Expense Updated',
        message=f'Your expense of ₹{expense_amount} has been updated.',
        expense_amount=expense_amount
    )

def notify_expense_deleted(user, expense_amount: float):
    """Notify when an expense is deleted"""
    return NotificationService.create(
        user=user,
        event_type='expense_deleted',
        title='Expense Deleted',
        message=f'Your expense of ₹{expense_amount} has been deleted.',
        expense_amount=expense_amount
    )

def notify_daily_limit_80(user, current_spent: float, limit: float):
    """Notify when 80% of daily limit is reached"""
    percentage = (current_spent / limit) * 100 if limit > 0 else 0
    return NotificationService.create(
        user=user,
        event_type='daily_limit_80',
        title='Daily Limit Warning',
        message=f'You have spent {percentage:.0f}% (₹{current_spent}) of your daily limit of ₹{limit}.',
        current_spent=current_spent,
        limit=limit
    )

def notify_daily_limit_exceeded(user, current_spent: float, limit: float):
    """Notify when daily limit is exceeded"""
    return NotificationService.create(
        user=user,
        event_type='daily_limit_exceeded',
        title='Daily Limit Exceeded!',
        message=f'You have exceeded your daily limit of ₹{limit}. Current spending: ₹{current_spent}',
        current_spent=current_spent,
        limit=limit
    )

def notify_goal_created(user, goal_name: str, target_amount: float):
    """Notify when a goal is created"""
    return NotificationService.create(
        user=user,
        event_type='goal_created',
        title='Goal Created',
        message=f'Your savings goal "{goal_name}" of ₹{target_amount} has been created.',
        goal_name=goal_name,
        target_amount=target_amount
    )

def notify_goal_near_deadline(user, goal_name: str, days_left: int):
    """Notify when a goal is near deadline"""
    return NotificationService.create(
        user=user,
        event_type='goal_near_deadline',
        title='Goal Deadline Approaching',
        message=f'Your goal "{goal_name}" is due in {days_left} days. Keep saving!',
        goal_name=goal_name,
        days_left=days_left
    )

def notify_suspicious_login(user, ip_address: str, location: str):
    """Notify about suspicious login (always creates, no duplicates)"""
    return NotificationService.create(
        user=user,
        event_type='suspicious_login',
        title='Suspicious Login Detected',
        message=f'A login attempt was made from {location} (IP: {ip_address}). If this wasn\'t you, please change your password.',
        ip_address=ip_address,
        location=location
    )

def notify_password_changed(user):
    """Notify when password is changed (always creates, no duplicates)"""
    return NotificationService.create(
        user=user,
        event_type='password_changed',
        title='Password Changed',
        message='Your password has been changed successfully. If you didn\'t make this change, please contact support immediately.'
    )

def notify_large_transaction(user, amount: float, merchant: str = None):
    """Notify about large unusual transaction"""
    merchant_text = f" at {merchant}" if merchant else ""
    return NotificationService.create(
        user=user,
        event_type='large_transaction',
        title='Large Transaction Alert',
        message=f'A large transaction of ₹{amount}{merchant_text} was detected.',
        amount=amount,
        merchant=merchant
    )

def notify_voice_listening(user):
    """Notify that voice recognition is listening"""
    return NotificationService.create(
        user=user,
        event_type='listening_started',
        title='Voice Recognition Active',
        message='Listening for your voice command...'
    )

def notify_no_expenses(user):
    """Notify when no expenses are found"""
    return NotificationService.create(
        user=user,
        event_type='no_expenses',
        title='No Expenses',
        message='No expenses found for the selected period.'
    )

def notify_insufficient_balance(user, required: float, available: float):
    """Notify about insufficient balance"""
    return NotificationService.create(
        user=user,
        event_type='insufficient_balance',
        title='Insufficient Balance',
        message=f'Cannot complete transaction. Required: ₹{required}, Available: ₹{available}',
        required=required,
        available=available
    )
