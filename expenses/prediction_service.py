from django.db.models import Sum, Avg
from django.utils import timezone
from datetime import timedelta
from .models import Expense
import logging

logger = logging.getLogger(__name__)

class PredictionService:
    """
    Service for calculating financial predictions using historical expense data.
    Uses moving average for predictions. Scalable for future ML upgrades.
    """

    @staticmethod
    def get_historical_expenses(user, days_back=30):
        """
        Get historical expenses for the user over the last N days.
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days_back)
        return Expense.objects.filter(
            owner=user,
            date__gte=start_date,
            date__lte=end_date
        )

    @staticmethod
    def calculate_moving_average(expenses, window=7):
        """
        Calculate moving average of expenses over a window period.
        """
        if not expenses.exists():
            return 0

        # Get daily totals
        daily_totals = expenses.values('date').annotate(total=Sum('amount')).order_by('date')

        if len(daily_totals) < window:
            # If less than window, use overall average
            return sum(item['total'] for item in daily_totals) / len(daily_totals)

        # Calculate moving average of the last window days
        recent_totals = [item['total'] for item in daily_totals[-window:]]
        return sum(recent_totals) / len(recent_totals)

    @staticmethod
    def predict_today(user):
        """
        Predict spending for today based on last 7 days average.
        """
        expenses = PredictionService.get_historical_expenses(user, days_back=30)
        return PredictionService.calculate_moving_average(expenses, window=7)

    @staticmethod
    def predict_tomorrow(user):
        """
        Predict spending for tomorrow (same as today for simplicity).
        """
        return PredictionService.predict_today(user)

    @staticmethod
    def predict_this_week(user):
        """
        Predict spending for this week (7 days) based on last 4 weeks average.
        """
        expenses = PredictionService.get_historical_expenses(user, days_back=30)
        daily_avg = PredictionService.calculate_moving_average(expenses, window=7)
        return daily_avg * 7

    @staticmethod
    def predict_this_month(user):
        """
        Predict spending for this month (30 days) based on last 3 months average.
        """
        expenses = PredictionService.get_historical_expenses(user, days_back=90)
        daily_avg = PredictionService.calculate_moving_average(expenses, window=30)
        return daily_avg * 30

    @staticmethod
    def get_predictions(user):
        """
        Get all predictions for the user.
        Handles edge cases: no data, small dataset.
        Uses typical spending baselines for new users without history.
        """
        try:
            # Check if user has any expenses
            expenses_count = Expense.objects.filter(owner=user).count()
            
            if expenses_count == 0:
                # For new users without expense history, use baseline estimates
                # These are typical average values that can be customized by user later
                return {
                    'today': 50.00,  # Estimated daily spending
                    'tomorrow': 50.00,
                    'this_week': 350.00,  # 50 * 7 days
                    'this_month': 1500.00,  # 50 * 30 days
                    'has_data': False,
                    'is_estimate': True,
                    'message': 'Based on typical spending patterns'
                }
            
            # User has data - use historical predictions
            today = PredictionService.predict_today(user)
            tomorrow = PredictionService.predict_tomorrow(user)
            this_week = PredictionService.predict_this_week(user)
            this_month = PredictionService.predict_this_month(user)

            return {
                'today': round(today, 2),
                'tomorrow': round(tomorrow, 2),
                'this_week': round(this_week, 2),
                'this_month': round(this_month, 2),
                'has_data': True,
                'is_estimate': False
            }
        except Exception as e:
            logger.error(f"Error calculating predictions for user {user.id}: {e}")
            return {
                'today': 0,
                'tomorrow': 0,
                'this_week': 0,
                'this_month': 0,
                'has_data': False,
                'is_estimate': False
            }

    @staticmethod
    def get_color_indicator(predicted, average):
        """
        Get color indicator based on predicted vs average.
        Green: below average, Yellow: near average, Red: above average.
        """
        if predicted < average * 0.9:
            return 'green'
        elif predicted > average * 1.1:
            return 'red'
        else:
            return 'yellow'
