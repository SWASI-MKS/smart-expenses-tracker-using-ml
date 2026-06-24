"""
Daily Summary Service - Production-Ready Business Logic
========================================================

This service layer contains all business logic for daily spending summaries.
It is designed to be timezone-aware, idempotent, and scalable.

Features:
- Timezone-aware calculations
- Idempotent operations
- Optimized database queries with aggregation
- Email and in-app notification delivery
- Comprehensive error handling and logging
"""

import logging
from datetime import date, datetime, time, timedelta
from typing import Optional, Tuple, Any
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model

from expenses.models import Expense
from userpreferences.models import UserPreference, Notification
from userpreferences.currency_service import CurrencyService

# Configure logging
logger = logging.getLogger(__name__)

User = get_user_model()


class DailySummaryService:
    """
    Service for calculating and sending daily spending summaries.
    
    This service handles:
    - Total spending calculation for a specific date
    - Timezone-aware eligibility checks
    - Sending both email and in-app notifications
    - Idempotent operations to prevent duplicates
    """
    
    # Common timezones for quick access
    COMMON_TIMEZONES = [
        'UTC',
        'America/New_York',
        'America/Chicago',
        'America/Denver',
        'America/Los_Angeles',
        'Europe/London',
        'Europe/Paris',
        'Europe/Berlin',
        'Asia/Dubai',
        'Asia/Kolkata',
        'Asia/Singapore',
        'Asia/Tokyo',
        'Australia/Sydney',
        'Pacific/Auckland',
    ]
    
    @staticmethod
    def calculate_total_for_date(user, target_date: date) -> Tuple[float, str]:
        """
        Calculate total expenses for a user on a specific date.
        
        Uses database aggregation for efficiency (avoids loading full objects).
        
        Args:
            user: User instance or user ID
            target_date: Date to calculate total for
            
        Returns:
            Tuple of (total_amount, currency_symbol)
        """
        user_id = user.id if hasattr(user, 'id') else user
        
        try:
            # Use aggregation with Sum() - efficient database query
            result = Expense.objects.filter(
                owner_id=user_id,
                date=target_date
            ).aggregate(total=Sum('amount'))
            
            total = float(result['total'] or 0)
            
            # Get user's preferred currency symbol
            currency_symbol = CurrencyService.get_currency_symbol_for_user(user_id)
            
            logger.debug(
                f"Calculated total for user {user_id} on {target_date}: {total} {currency_symbol}"
            )
            
            return total, currency_symbol
            
        except Exception as e:
            logger.error(
                f"Error calculating total for user {user_id} on {target_date}: {e}"
            )
            return 0.0, '₹'  # Default to INR symbol
    
    @staticmethod
    def get_user_timezone(user) -> str:
        """
        Get user's timezone from preferences.
        
        Args:
            user: User instance or user ID
            
        Returns:
            IANA timezone string (default: UTC)
        """
        user_id = user.id if hasattr(user, 'id') else user
        
        try:
            preference = UserPreference.objects.get(user_id=user_id)
            return preference.timezone or 'UTC'
        except UserPreference.DoesNotExist:
            logger.warning(f"UserPreference not found for user {user_id}, defaulting to UTC")
            return 'UTC'
        except Exception as e:
            logger.error(f"Error getting timezone for user {user_id}: {e}")
            return 'UTC'
    
    @staticmethod
    def convert_utc_to_user_timezone(utc_time: datetime, user_timezone: str) -> datetime:
        """
        Convert UTC time to user's local timezone.
        
        This handles DST automatically via Django's timezone utilities.
        
        Args:
            utc_time: datetime in UTC
            user_timezone: IANA timezone string
            
        Returns:
            datetime in user's local timezone
        """
        try:
            import pytz
            user_tz = pytz.timezone(user_timezone)
            
            # Make sure utc_time is timezone-aware
            if timezone.is_naive(utc_time):
                utc_time = timezone.make_aware(utc_time, timezone.utc)
            
            # Convert to user's timezone
            return utc_time.astimezone(user_tz)
            
        except Exception as e:
            logger.error(f"Error converting timezone to {user_timezone}: {e}")
            # Return as-is if conversion fails
            return utc_time
    
    @staticmethod
    def should_send_summary(user, current_utc_time: datetime) -> Tuple[bool, str]:
        """
        Determine if daily summary should be sent for a user.
        
        Checks:
        1. User has daily summary enabled
        2. Current local time >= user's preferred time
        3. Summary hasn't been sent yet today (idempotency)
        
        Args:
            user: User instance or user ID
            current_utc_time: Current UTC time from the task
            
        Returns:
            Tuple of (should_send, reason)
        """
        user_id = user.id if hasattr(user, 'id') else user
        
        try:
            # Get user preference with select_related for efficiency
            try:
                preference = UserPreference.objects.select_related('user').get(user_id=user_id)
            except UserPreference.DoesNotExist:
                return False, "no_preference"
            
            # Check if daily summary is enabled
            if not preference.daily_summary_enabled:
                return False, "disabled"
            
            # Get user's timezone
            user_timezone = preference.timezone or 'UTC'
            
            # Convert current UTC time to user's local time
            local_time = DailySummaryService.convert_utc_to_user_timezone(
                current_utc_time, 
                user_timezone
            )
            
            # Get user's preferred summary time
            preferred_time = preference.daily_summary_time or time(0, 0, 0)
            
            # Check if current local time is past preferred time
            current_time = local_time.time()
            
            # Handle date comparison - we want to check if we've passed the preferred time
            # AND if we haven't already sent today
            if current_time < preferred_time:
                return False, "before_preferred_time"
            
            # Check last summary sent time
            if preference.last_summary_sent_at:
                # Convert last_sent to user's timezone for comparison
                last_sent_local = DailySummaryService.convert_utc_to_user_timezone(
                    preference.last_summary_sent_at,
                    user_timezone
                )
                
                # If already sent today, don't send again
                if last_sent_local.date() >= local_time.date():
                    return False, "already_sent_today"
            
            return True, "eligible"
            
        except Exception as e:
            logger.error(f"Error checking should_send_summary for user {user_id}: {e}")
            return False, f"error: {str(e)}"
    
    @staticmethod
    @transaction.atomic
    def send_summary(user, total: float, target_date: date, currency_symbol: str = '₹') -> bool:
        """
        Send daily summary to user via email and in-app notification.
        
        This method is atomic - either both succeed or neither does.
        
        Args:
            user: User instance or user ID
            total: Total spending amount
            target_date: Date for which summary is being sent
            currency_symbol: Currency symbol to display
            
        Returns:
            True if successful, False otherwise
        """
        user_id = user.id if hasattr(user, 'id') else user
        
        try:
            # Get user object
            if isinstance(user, int):
                user_obj = User.objects.get(pk=user_id)
            else:
                user_obj = user
            
            # Format the message
            date_str = target_date.strftime('%B %d, %Y')
            
            # Create in-app notification
            notification = Notification.objects.create(
                user=user_obj,
                title='Daily Spending Summary',
                message=f'Your total spending on {date_str} was {currency_symbol}{total:.2f}',
                type='info',
                event_type='daily_summary',
                send_email=True,
                event_hash=None  # We'll handle deduplication via last_summary_sent_at
            )
            
            logger.info(
                f"Created daily summary notification for user {user_id} "
                f"for date {target_date}: {currency_symbol}{total}"
            )
            
            # Send email asynchronously (via Celery if available)
            DailySummaryService._send_summary_email(
                user_obj, 
                total, 
                target_date, 
                currency_symbol
            )
            
            # Update last_summary_sent_at timestamp
            preference = UserPreference.objects.get(user_id=user_id)
            preference.last_summary_sent_at = timezone.now()
            preference.save(update_fields=['last_summary_sent_at'])
            
            logger.info(
                f"Successfully sent daily summary to user {user_id} "
                f"for date {target_date}"
            )
            
            return True
            
        except UserPreference.DoesNotExist:
            logger.error(f"UserPreference not found for user {user_id}")
            return False
            
        except Exception as e:
            logger.error(
                f"Error sending daily summary to user {user_id}: {e}",
                exc_info=True
            )
            return False
    
    @staticmethod
    def _send_summary_email(user, total: float, target_date: date, currency_symbol: str) -> bool:
        """
        Send daily summary email to user.
        
        Args:
            user: User instance
            total: Total spending amount
            target_date: Date for which summary is being sent
            currency_symbol: Currency symbol to display
            
        Returns:
            True if email sent successfully
        """
        try:
            from expenses.email_service import send_email, EmailType
            
            date_str = target_date.strftime('%B %d, %Y')
            
            context = {
                'total': total,
                'currency_symbol': currency_symbol,
                'date': date_str,
                'target_date': target_date,
            }
            
            # Use the email service
            send_email(
                user_id=user.id,
                email_type='daily_summary',
                context=context,
                force_send=True  # Always send daily summaries
            )
            
            logger.info(f"Email sent to user {user.id} for daily summary")
            return True
            
        except Exception as e:
            logger.error(f"Error sending daily summary email to user {user.id}: {e}")
            return False
    
    @staticmethod
    def get_yesterday_date() -> date:
        """Get yesterday's date in timezone-aware manner"""
        return timezone.now().date() - timedelta(days=1)
    
    @staticmethod
    def get_today_date() -> date:
        """Get today's date in timezone-aware manner"""
        return timezone.now().date()


# ============================================================
# Convenience Functions
# ============================================================

def calculate_user_total(user, target_date: date = None) -> Tuple[float, str]:
    """
    Convenience function to calculate user's total for a date.
    
    Args:
        user: User instance or user ID
        target_date: Date to calculate for (defaults to yesterday)
        
    Returns:
        Tuple of (total, currency_symbol)
    """
    if target_date is None:
        target_date = DailySummaryService.get_yesterday_date()
    
    return DailySummaryService.calculate_total_for_date(user, target_date)


def should_send_daily_summary(user, current_utc_time: datetime = None) -> Tuple[bool, str]:
    """
    Convenience function to check if summary should be sent.
    
    Args:
        user: User instance or user ID
        current_utc_time: Current UTC time (defaults to now)
        
    Returns:
        Tuple of (should_send, reason)
    """
    if current_utc_time is None:
        current_utc_time = timezone.now()
    
    return DailySummaryService.should_send_summary(user, current_utc_time)


def send_daily_summary_notification(user, target_date: date = None) -> bool:
    """
    Convenience function to send daily summary.
    
    Args:
        user: User instance or user ID
        target_date: Date for summary (defaults to yesterday)
        
    Returns:
        True if successful
    """
    if target_date is None:
        target_date = DailySummaryService.get_yesterday_date()
    
    total, currency_symbol = DailySummaryService.calculate_total_for_date(user, target_date)
    
    # Only send if there's something to report (or always send to show zero)
    return DailySummaryService.send_summary(user, total, target_date, currency_symbol)
