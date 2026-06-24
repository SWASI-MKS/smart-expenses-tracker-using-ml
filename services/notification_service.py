"""
Notification Service - Alerts & Reminders
======================================
Comprehensive notification system including:
- Budget exceeded alerts
- Savings milestone notifications
- Recurring expense reminders
- Large transaction alerts
- In-app + Email notifications
"""

from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
import logging
import json

from expenses.models import Expense, ExpenseLimit
from goals.models import Goal
from expenses.models import RecurringExpense
from userpreferences.models import UserPreference

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for managing all user notifications.
    Supports both in-app and email notifications.
    """
    
    # Notification types
    TYPE_BUDGET_EXCEEDED = 'budget_exceeded'
    TYPE_BUDGET_WARNING = 'budget_warning'
    TYPE_GOAL_MILESTONE = 'goal_milestone'
    TYPE_GOAL_COMPLETED = 'goal_completed'
    TYPE_RECURRING_DUE = 'recurring_due'
    TYPE_LARGE_TRANSACTION = 'large_transaction'
    TYPE_DAILY_SUMMARY = 'daily_summary'
    TYPE_DEBT_REMINDER = 'debt_reminder'
    
    @staticmethod
    def send_budget_alert(user, expense_amount, budget_limit, percentage_used):
        """
        Send budget exceeded/warning notification.
        
        Args:
            user: User instance
            expense_amount: Current expense amount
            budget_limit: Budget limit
            percentage_used: Percentage of budget used
        """
        try:
            if percentage_used >= 100:
                notification_type = NotificationService.TYPE_BUDGET_EXCEEDED
                subject = "⚠️ Budget Exceeded!"
                message = f"You've exceeded your daily budget of ${budget_limit}. You've spent ${expense_amount} today."
            elif percentage_used >= 90:
                notification_type = NotificationService.TYPE_BUDGET_WARNING
                subject = "⚠️ Budget Warning - 90%"
                message = f"You've used 90% of your daily budget (${budget_limit}). You have ${budget_limit - expense_amount} remaining."
            else:
                return  # No notification needed
            
            # Get user preferences
            try:
                prefs = UserPreference.objects.get(user=user)
                currency = prefs.currency_symbol or '$'
            except:
                currency = '$'
            
            # Send email notification
            if user.email:
                try:
                    send_mail(
                        subject=f"[Expense Tracker] {subject}",
                        message=message,
                        from_email=None,  # Uses DEFAULT_FROM_EMAIL
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    logger.error(f"Failed to send budget alert email to {user.email}: {e}")
            
            # Store in-app notification (would be stored in notification model)
            logger.info(f"Budget alert for user {user.id}: {message}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending budget alert for user {user.id}: {e}")
            return False
    
    @staticmethod
    def check_budget_limits(user, expense_amount):
        """
        Check if expense would exceed budget and send notification if needed.
        
        Call this after each expense is added.
        """
        try:
            expense_limit = ExpenseLimit.objects.filter(owner=user).first()
            if not expense_limit or not expense_limit.daily_expense_limit:
                return
            
            daily_limit = expense_limit.daily_expense_limit
            
            # Get today's spending
            today = timezone.now().date()
            today_spending = Expense.objects.filter(
                owner=user, date=today
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Check if adding this expense would exceed budget
            new_total = today_spending + expense_amount
            percentage_used = (new_total / daily_limit) * 100
            
            if percentage_used >= 90:
                NotificationService.send_budget_alert(
                    user, new_total, daily_limit, percentage_used
                )
                
        except Exception as e:
            logger.error(f"Error checking budget limits for user {user.id}: {e}")
    
    @staticmethod
    def check_goal_milestones(user):
        """
        Check for goal milestones and send notifications.
        
        Notifies when goals reach 25%, 50%, 75%, and 100%.
        """
        try:
            goals = Goal.objects.filter(
                owner=user, 
                is_achieved=False
            )
            
            for goal in goals:
                percentage = goal.saved_percentage
                
                # Check milestones
                milestones = [25, 50, 75, 100]
                for milestone in milestones:
                    if percentage >= milestone:
                        # Check if we've already notified for this milestone
                        # (In production, would store notification history)
                        if percentage < milestone + 1:  # Just crossed the milestone
                            NotificationService._send_goal_notification(
                                user, goal, milestone
                            )
            
        except Exception as e:
            logger.error(f"Error checking goal milestones for user {user.id}: {e}")
    
    @staticmethod
    def _send_goal_notification(user, goal, milestone):
        """Send goal milestone notification."""
        try:
            if milestone == 100:
                subject = f"🎉 Goal Achieved: {goal.name}!"
                message = f"Congratulations! You've reached your savings goal of ${goal.amount_to_save} for '{goal.name}'!"
            else:
                subject = f"🏆 Goal Milestone: {goal.name}"
                message = f"You've reached {milestone}% of your savings goal for '{goal.name}'. Keep going!"
            
            if user.email:
                send_mail(
                    subject=f"[Expense Tracker] {subject}",
                    message=message,
                    from_email=None,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            
            logger.info(f"Goal milestone notification sent to user {user.id} for goal {goal.id}")
            
        except Exception as e:
            logger.error(f"Error sending goal notification: {e}")
    
    @staticmethod
    def check_recurring_expenses(user):
        """
        Send reminders for upcoming recurring expenses.
        
        Notifies 1-3 days before due date.
        """
        try:
            today = timezone.now().date()
            upcoming = today + timedelta(days=3)
            
            recurring = RecurringExpense.objects.filter(
                owner=user,
                is_active=True,
                next_due_date__lte=upcoming,
                next_due_date__gte=today
            )
            
            for expense in recurring:
                days_until = (expense.next_due_date - today).days
                
                subject = f"📅 Upcoming Expense: {expense.name}"
                message = f"Your recurring expense '{expense.name}' of ${expense.amount} is due in {days_until} day(s) ({expense.next_due_date})."
                
                if user.email:
                    send_mail(
                        subject=f"[Expense Tracker] {subject}",
                        message=message,
                        from_email=None,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
            
        except Exception as e:
            logger.error(f"Error checking recurring expenses for user {user.id}: {e}")
    
    @staticmethod
    def check_large_transactions(user, expense_amount, threshold=500):
        """
        Send alert for unusually large transactions.
        
        Args:
            user: User instance
            expense_amount: Amount of the expense
            threshold: Amount threshold for large transaction alert
        """
        try:
            if expense_amount >= threshold:
                subject = "💰 Large Transaction Recorded"
                message = f"A large expense of ${expense_amount} has been recorded. If this wasn't you, please review your account."
                
                if user.email:
                    send_mail(
                        subject=f"[Expense Tracker] {subject}",
                        message=message,
                        from_email=None,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
        
        except Exception as e:
            logger.error(f"Error checking large transactions for user {user.id}: {e}")
    
    @staticmethod
    def send_daily_summary(user, summary_data):
        """
        Send daily spending summary email.
        
        Args:
            user: User instance
            summary_data: Dict with summary information
        """
        try:
            if not user.email:
                return
            
            # Get currency
            try:
                prefs = UserPreference.objects.get(user=user)
                currency = prefs.currency_symbol or '$'
            except:
                currency = '$'
            
            subject = f"📊 Daily Summary - {timezone.now().date().strftime('%B %d, %Y')}"
            
            message = f"""Hello {user.first_name or 'there'},

Here's your daily spending summary:

💰 Today's Spending: {currency}{summary_data.get('today_total', 0)}
📈 This Week: {currency}{summary_data.get('week_total', 0)}
📅 This Month: {currency}{summary_data.get('month_total', 0)}

Top Categories:
{summary_data.get('top_categories', 'No data')}

{summary_data.get('insight', '')}

Best regards,
Expense Tracker Team
"""
            
            send_mail(
                subject=f"[Expense Tracker] {subject}",
                message=message,
                from_email=None,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            logger.info(f"Daily summary sent to {user.email}")
            
        except Exception as e:
            logger.error(f"Error sending daily summary to {user.email}: {e}")
    
    @staticmethod
    def process_all_notifications(user):
        """
        Run all notification checks for a user.
        
        Should be called periodically (e.g., daily via Celery).
        """
        try:
            # Check budget limits (would need expense amount)
            # NotificationService.check_budget_limits(user, 0)
            
            # Check goal milestones
            NotificationService.check_goal_milestones(user)
            
            # Check recurring expenses
            NotificationService.check_recurring_expenses(user)
            
            logger.info(f"Notification checks completed for user {user.id}")
            
        except Exception as e:
            logger.error(f"Error processing notifications for user {user.id}: {e}")


class InAppNotification:
    """
    In-app notification model (would be stored in database).
    
    In production, this would be a Django model with fields like:
    - user (FK to User)
    - notification_type
    - title
    - message
    - is_read
    - created_at
    - link
    """
    
    @staticmethod
    def create_notification(user, notification_type, title, message, link=None):
        """
        Create in-app notification.
        
        In production, would save to database.
        """
        logger.info(f"In-app notification for user {user.id}: [{notification_type}] {title}")
        return {
            'user_id': user.id,
            'type': notification_type,
            'title': title,
            'message': message,
            'link': link,
            'created_at': timezone.now().isoformat()
        }
    
    @staticmethod
    def get_unread_count(user):
        """
        Get count of unread notifications.
        
        In production, would query database.
        """
        return 0  # Placeholder
