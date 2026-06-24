"""
Goal Lifecycle Service
=====================
Manages goal status updates, notifications, and lifecycle operations.

Features:
- Automatic status updates (ACTIVE, COMPLETED, OVERDUE)
- Overdue notification with anti-duplicate logic
- Bulk operations for performance
- Optimized queries with select_related
"""

import logging
from datetime import timedelta
from typing import List, Optional
from django.utils import timezone
from django.db import models  # IMPORTANT: Add this import for models.F
from django.db.models import QuerySet

from goals.models import Goal
from userpreferences.notification_service import NotificationService

logger = logging.getLogger(__name__)


class GoalService:
    """
    Service class for managing goal lifecycle operations.
    
    Usage:
        # Update single goal status
        GoalService.update_goal_status(goal)
        
        # Check overdue and notify
        GoalService.check_and_notify_overdue(user)
        
        # Get all overdue goals
        overdue_goals = GoalService.get_overdue_goals(user)
        
        # Bulk update all user goals
        GoalService.update_all_goals_status(user)
    """
    
    # Notification event type for goal overdue
    EVENT_TYPE_GOAL_OVERDUE = 'goal_overdue'
    
    # Anti-duplicate window in minutes (24 hours)
    DUPLICATE_WINDOW_MINUTES = 1440
    
    @staticmethod
    def update_goal_status(goal: Goal) -> str:
        """
        Update goal status based on current state.
        
        Args:
            goal: Goal instance to update
            
        Returns:
            New status string
        """
        old_status = goal.status
        
        # Determine new status
        if goal.is_completed:
            new_status = Goal.STATUS_COMPLETED
        elif goal.is_overdue:
            new_status = Goal.STATUS_OVERDUE
        else:
            new_status = Goal.STATUS_ACTIVE
        
        # Only save if status changed
        if old_status != new_status:
            goal.status = new_status
            if goal.is_completed:
                goal.is_achieved = True
            goal.save(update_fields=['status', 'is_achieved', 'updated_at'])
            logger.info(f"Goal '{goal.name}' status updated from {old_status} to {new_status}")
        
        return new_status
    
    @staticmethod
    def update_all_goals_status(user) -> dict:
        """
        Update status for all active goals of a user.
        
        Args:
            user: User instance
            
        Returns:
            Dict with counts of updated goals
        """
        goals = Goal.objects.filter(
            owner=user
        ).exclude(
            status=Goal.STATUS_ARCHIVED
        )
        
        counts = {
            'total': 0,
            'completed': 0,
            'overdue': 0,
            'active': 0,
        }
        
        for goal in goals:
            old_status = goal.status
            GoalService.update_goal_status(goal)
            
            counts['total'] += 1
            if goal.status == Goal.STATUS_COMPLETED:
                counts['completed'] += 1
            elif goal.status == Goal.STATUS_OVERDUE:
                counts['overdue'] += 1
            else:
                counts['active'] += 1
        
        return counts
    
    @staticmethod
    def get_active_goals(user) -> QuerySet:
        """Get all active goals for a user"""
        return Goal.objects.filter(
            owner=user,
            status=Goal.STATUS_ACTIVE
        ).order_by('end_date')
    
    @staticmethod
    def get_completed_goals(user) -> QuerySet:
        """Get all completed goals for a user"""
        return Goal.objects.filter(
            owner=user,
            status=Goal.STATUS_COMPLETED
        ).order_by('-updated_at')
    
    @staticmethod
    def get_overdue_goals(user) -> QuerySet:
        """Get all overdue goals for a user"""
        return Goal.objects.filter(
            owner=user,
            status=Goal.STATUS_OVERDUE
        ).order_by('end_date')
    
    @staticmethod
    def get_archived_goals(user) -> QuerySet:
        """Get all archived goals for a user"""
        return Goal.objects.filter(
            owner=user,
            status=Goal.STATUS_ARCHIVED
        ).order_by('-updated_at')
    
    @staticmethod
    def get_goals_by_status(user, status: str) -> QuerySet:
        """Get goals filtered by status"""
        return Goal.objects.filter(
            owner=user,
            status=status
        ).order_by('-created_at')
    
    @staticmethod
    def check_and_notify_overdue(user, force_notify: bool = False) -> List[Goal]:
        """
        Check for overdue goals and create notifications.
        
        Args:
            user: User instance
            force_notify: If True, ignore duplicate prevention
            
        Returns:
            List of goals that became overdue
        """
        from django.utils import timezone
        
        today = timezone.now().date()
        
        # Find goals that are overdue but still marked as active
        # FIXED: models is now imported at the top
        potentially_overdue = Goal.objects.filter(
            owner=user,
            status=Goal.STATUS_ACTIVE,
            end_date__lt=today,
            current_saved_amount__lt=models.F('amount_to_save')
        )
        
        newly_overdue = []
        
        for goal in potentially_overdue:
            # Update status
            old_status = goal.status
            goal.status = Goal.STATUS_OVERDUE
            goal.save(update_fields=['status', 'updated_at'])
            
            logger.info(f"Goal '{goal.name}' marked as OVERDUE")
            newly_overdue.append(goal)
            
            # Create notification (unless archived)
            if goal.status != Goal.STATUS_ARCHIVED:
                GoalService._create_overdue_notification(goal, force=force_notify)
        
        return newly_overdue
    
    @staticmethod
    def _create_overdue_notification(goal: Goal, force: bool = False) -> Optional[object]:
        """
        Create notification for overdue goal.
        
        Args:
            goal: Overdue goal instance
            force: If True, ignore duplicate prevention
            
        Returns:
            Notification object or None if duplicate
        """
        # Calculate achievement percentage
        percentage = goal.saved_percentage
        
        # Build message
        message = (
            f"Your goal '{goal.name}' has reached its deadline without completion. "
            f"You achieved {percentage:.0f}% of your goal ({goal.current_saved_amount} / {goal.amount_to_save}). "
            f"You can extend the deadline or continue saving."
        )
        
        # Determine duplicate window
        window = 0 if force else GoalService.DUPLICATE_WINDOW_MINUTES
        
        # Check for duplicate (unless forcing)
        if not force:
            if NotificationService.is_duplicate(
                goal.owner.id,
                GoalService.EVENT_TYPE_GOAL_OVERDUE,
                window,
                goal_id=goal.id
            ):
                logger.debug(f"Duplicate overdue notification prevented for goal {goal.id}")
                return None
        
        # Create notification
        notification = NotificationService.create(
            user=goal.owner,
            event_type=GoalService.EVENT_TYPE_GOAL_OVERDUE,
            title='Goal Deadline Missed',
            message=message,
            related_object_id=goal.id,
            related_object_type='goal',
            goal_name=goal.name,
            goal_id=goal.id,
            saved_percentage=percentage
        )
        
        return notification
    
    @staticmethod
    def notify_goal_completed(goal: Goal) -> Optional[object]:
        """Create notification when goal is completed"""
        message = (
            f"Congratulations! You've achieved your goal '{goal.name}'. "
            f"You saved {goal.amount_to_save}. Great job!"
        )
        
        return NotificationService.create(
            user=goal.owner,
            event_type='goal_completed',
            title='Goal Achieved! 🎉',
            message=message,
            related_object_id=goal.id,
            related_object_type='goal',
            goal_name=goal.name,
            target_amount=float(goal.amount_to_save)
        )
    
    @staticmethod
    def check_goal_near_deadline(user, days_threshold: int = 7) -> List[Goal]:
        """Get goals that are near deadline (within days_threshold)"""
        from django.utils import timezone
        
        today = timezone.now().date()
        threshold_date = today + timedelta(days=days_threshold)
        
        return list(Goal.objects.filter(
            owner=user,
            status=Goal.STATUS_ACTIVE,
            end_date__gte=today,
            end_date__lte=threshold_date
        ))
    
    @staticmethod
    def bulk_extend_deadline(goal_ids: List[int], new_end_date, user) -> dict:
        """
        Extend deadline for multiple goals.
        
        Args:
            goal_ids: List of goal IDs
            new_end_date: New end date
            user: User instance (for authorization)
            
        Returns:
            Dict with success/failure counts
        """
        from django.core.exceptions import ValidationError
        
        results = {'success': 0, 'failed': 0, 'errors': []}
        
        goals = Goal.objects.filter(
            id__in=goal_ids,
            owner=user
        ).exclude(status=Goal.STATUS_ARCHIVED)
        
        for goal in goals:
            try:
                goal.extend_deadline(new_end_date)
                results['success'] += 1
            except ValidationError as e:
                results['failed'] += 1
                results['errors'].append(f"Goal {goal.id}: {str(e)}")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Goal {goal.id}: {str(e)}")
        
        return results
    
    @staticmethod
    def archive_completed_goals(user, older_than_days: int = 30) -> int:
        """
        Archive completed goals older than specified days.
        
        Args:
            user: User instance
            older_than_days: Number of days to consider for archiving
            
        Returns:
            Number of goals archived
        """
        from django.utils import timezone
        
        cutoff_date = timezone.now() - timedelta(days=older_than_days)
        
        goals = Goal.objects.filter(
            owner=user,
            status=Goal.STATUS_COMPLETED,
            updated_at__lt=cutoff_date
        )
        
        count = goals.count()
        goals.update(status=Goal.STATUS_ARCHIVED, updated_at=timezone.now())
        
        return count


# ============================================================
# Celery Task Integration (Optional)
# ============================================================

def check_all_users_overdue_goals():
    """
    Celery task to check overdue goals for all users.
    Run this daily using Celery beat.
    """
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    for user in User.objects.filter(is_active=True):
        try:
            GoalService.check_and_notify_overdue(user)
        except Exception as e:
            logger.error(f"Error checking overdue goals for user {user.id}: {e}")
    
    return "Completed checking overdue goals"


def daily_goal_health_check():
    """
    Celery task for daily goal health check.
    Updates statuses and sends notifications.
    """
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    results = {
        'users_processed': 0,
        'goals_updated': 0,
        'notifications_sent': 0,
    }
    
    for user in User.objects.filter(is_active=True):
        try:
            # Update all goal statuses
            counts = GoalService.update_all_goals_status(user)
            results['goals_updated'] += counts['total']
            
            # Check for overdue and notify
            newly_overdue = GoalService.check_and_notify_overdue(user)
            results['notifications_sent'] += len(newly_overdue)
            
            results['users_processed'] += 1
        except Exception as e:
            logger.error(f"Error in daily goal health check for user {user.id}: {e}")
    
    logger.info(f"Daily goal health check completed: {results}")
    return results