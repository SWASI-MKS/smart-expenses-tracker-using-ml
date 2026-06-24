"""
Daily Summary Celery Tasks - Production-Ready
============================================

This module contains Celery tasks for processing daily spending summaries.
Designed for:
- Scalability (batch processing)
- Idempotency (prevent duplicates)
- Timezone-awareness
- Retry with exponential backoff
- Comprehensive logging

Task runs every 10 minutes via Celery Beat.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Tuple

from celery import shared_task
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model

from userpreferences.models import UserPreference
from services.daily_summary_service import DailySummaryService

# Configure logging
logger = logging.getLogger(__name__)

User = get_user_model()

# Batch size for processing users (100-200 to avoid email rate limits)
BATCH_SIZE = getattr(settings, 'DAILY_SUMMARY_BATCH_SIZE', 100)

# Global feature flag
DAILY_SUMMARY_FEATURE_ENABLED = getattr(settings, 'DAILY_SUMMARY_ENABLED', True)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1 minute initial delay
    autoretry_for=(Exception,),
    retry_backoff=True,  # Exponential backoff
    retry_backoff_max=600,  # Max 10 minutes
    acks_late=True,  # Acknowledge after processing
    reject_on_worker_lost=True,
)
def process_daily_summaries(self) -> dict:
    """
    Process daily spending summaries for all eligible users.
    
    This task:
    1. Runs every 10 minutes via Celery Beat
    2. Processes users in batches (100 per batch)
    3. Converts UTC time to each user's timezone
    4. Checks if summary should be sent based on user's preferred time
    5. Ensures idempotency via last_summary_sent_at
    6. Sends both email and in-app notification
    
    Args:
        self: Celery task instance
        
    Returns:
        dict with processing statistics
    """
    start_time = timezone.now()
    
    # Check global feature flag
    if not DAILY_SUMMARY_FEATURE_ENABLED:
        logger.info("Daily summary feature is disabled globally")
        return {
            'status': 'skipped',
            'reason': 'feature_disabled',
            'processed': 0,
            'sent': 0,
            'failed': 0,
        }
    
    stats = {
        'status': 'success',
        'processed': 0,
        'sent': 0,
        'failed': 0,
        'skipped': 0,
        'batches': 0,
        'start_time': start_time.isoformat(),
    }
    
    try:
        # Get current UTC time
        current_utc_time = timezone.now()
        
        # Get target date (yesterday) for the summary
        target_date = DailySummaryService.get_yesterday_date()
        
        logger.info(
            f"Starting daily summary processing for date {target_date} "
            f"at UTC time {current_utc_time}"
        )
        
        # Get total count of eligible users
        total_users = UserPreference.objects.filter(
            daily_summary_enabled=True
        ).count()
        
        logger.info(f"Total users with daily summary enabled: {total_users}")
        
        # Process in batches
        offset = 0
        batch_num = 0
        
        while True:
            # Get batch of users with select_related for efficiency
            user_preferences = UserPreference.objects.filter(
                daily_summary_enabled=True
            ).select_related('user').order_by('id')[offset:offset + BATCH_SIZE]
            
            if not user_preferences:
                break
            
            batch_num += 1
            stats['batches'] = batch_num
            
            # Process each user in the batch
            batch_results = process_user_batch(
                user_preferences, 
                current_utc_time, 
                target_date
            )
            
            stats['processed'] += batch_results['processed']
            stats['sent'] += batch_results['sent']
            stats['failed'] += batch_results['failed']
            stats['skipped'] += batch_results['skipped']
            
            logger.info(
                f"Batch {batch_num} completed: "
                f"processed={batch_results['processed']}, "
                f"sent={batch_results['sent']}, "
                f"failed={batch_results['failed']}, "
                f"skipped={batch_results['skipped']}"
            )
            
            offset += BATCH_SIZE
        
        # Calculate duration
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        stats['duration_seconds'] = duration
        stats['end_time'] = end_time.isoformat()
        
        logger.info(
            f"Daily summary processing completed in {duration:.2f} seconds. "
            f"Stats: {stats}"
        )
        
        return stats
        
    except Exception as e:
        logger.error(
            f"Error in process_daily_summaries: {e}",
            exc_info=True
        )
        
        # Retry with exponential backoff
        raise self.retry(exc=e)


def process_user_batch(
    user_preferences: List[UserPreference],
    current_utc_time: datetime,
    target_date
) -> dict:
    """
    Process a batch of users for daily summaries.
    
    Args:
        user_preferences: List of UserPreference objects
        current_utc_time: Current UTC time
        target_date: Date to summarize
        
    Returns:
        dict with batch statistics
    """
    results = {
        'processed': 0,
        'sent': 0,
        'failed': 0,
        'skipped': 0,
    }
    
    for preference in user_preferences:
        user = preference.user
        
        # Skip if user is inactive
        if not user.is_active:
            results['skipped'] += 1
            continue
        
        # Skip if user has no email
        if not user.email:
            logger.debug(f"Skipping user {user.id} - no email address")
            results['skipped'] += 1
            continue
        
        results['processed'] += 1
        
        try:
            # Check if summary should be sent
            should_send, reason = DailySummaryService.should_send_summary(
                user, 
                current_utc_time
            )
            
            if not should_send:
                results['skipped'] += 1
                logger.debug(
                    f"User {user.id} not eligible for summary: {reason}"
                )
                continue
            
            # Calculate total spending for the date
            total, currency_symbol = DailySummaryService.calculate_total_for_date(
                user, 
                target_date
            )
            
            # Send summary (email + in-app notification)
            success = DailySummaryService.send_summary(
                user, 
                total, 
                target_date, 
                currency_symbol
            )
            
            if success:
                results['sent'] += 1
            else:
                results['failed'] += 1
                logger.warning(f"Failed to send summary to user {user.id}")
                
        except Exception as e:
            results['failed'] += 1
            logger.error(
                f"Error processing user {user.id}: {e}",
                exc_info=True
            )
            # Continue with next user
    
    return results


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def send_single_summary(self, user_id: int, target_date_str: str = None) -> dict:
    """
    Send daily summary to a single user.
    
    This can be called directly for testing or manual triggering.
    
    Args:
        user_id: ID of the user
        target_date_str: Date string (YYYY-MM-DD), defaults to yesterday
        
    Returns:
        dict with result status
    """
    from datetime import datetime
    
    try:
        user = User.objects.get(pk=user_id)
        
        # Parse target date
        if target_date_str:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        else:
            target_date = DailySummaryService.get_yesterday_date()
        
        # Check eligibility
        current_time = timezone.now()
        should_send, reason = DailySummaryService.should_send_summary(
            user, 
            current_time
        )
        
        if not should_send:
            return {
                'status': 'skipped',
                'user_id': user_id,
                'reason': reason,
            }
        
        # Calculate and send
        total, currency_symbol = DailySummaryService.calculate_total_for_date(
            user, 
            target_date
        )
        
        success = DailySummaryService.send_summary(
            user, 
            total, 
            target_date, 
            currency_symbol
        )
        
        return {
            'status': 'success' if success else 'failed',
            'user_id': user_id,
            'total': total,
            'currency': currency_symbol,
            'date': target_date.isoformat(),
        }
        
    except User.DoesNotExist:
        return {
            'status': 'error',
            'user_id': user_id,
            'error': 'User not found',
        }
    except Exception as e:
        logger.error(f"Error in send_single_summary for user {user_id}: {e}")
        raise self.retry(exc=e)


@shared_task
def cleanup_old_summaries(days: int = 30) -> dict:
    """
    Cleanup old daily summary notifications.
    
    Args:
        days: Number of days to keep
        
    Returns:
        dict with cleanup statistics
    """
    from userpreferences.models import Notification
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    deleted_count = Notification.objects.filter(
        event_type='daily_summary',
        created_at__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f"Cleaned up {deleted_count} old daily summary notifications")
    
    return {
        'status': 'success',
        'deleted': deleted_count,
    }
