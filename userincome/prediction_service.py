from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta, date
import calendar
import logging

logger = logging.getLogger(__name__)


class IncomePredictionService:
    """
    Service for calculating income predictions using historical data.
    Uses moving average for predictions. Scalable for future ML upgrades.
    """

    @staticmethod
    def get_historical_income(user, days_back=30):
        """
        Get historical income for the user over the last N days.
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days_back)
        from userincome.models import UserIncome
        return UserIncome.objects.filter(
            owner=user,
            date__gte=start_date,
            date__lte=end_date
        )

    @staticmethod
    def calculate_moving_average(income_queryset, window=7):
        """
        Calculate moving average of income over a window period.
        """
        if not income_queryset.exists():
            return 0

        # Get daily totals
        daily_totals = income_queryset.values('date').annotate(total=Sum('amount')).order_by('date')

        if len(daily_totals) < window:
            # If less than window, use overall average
            return sum(item['total'] for item in daily_totals) / len(daily_totals)

        # Calculate moving average of the last window days
        recent_totals = [item['total'] for item in daily_totals[-window:]]
        return sum(recent_totals) / len(recent_totals)

    @staticmethod
    def predict_next_month(user):
        """
        Predict income for next month based on historical data.
        Uses last 3 months average to predict next month's income.
        """
        try:
            # Check if user has any income
            from userincome.models import UserIncome
            income_count = UserIncome.objects.filter(owner=user).count()
            
            if income_count == 0:
                # For new users without income history, return None or default
                return None
            
            today = timezone.now().date()
            
            # Get income data for the last 3 months
            three_months_ago = today - timedelta(days=90)
            income_qs = UserIncome.objects.filter(
                owner=user,
                date__gte=three_months_ago,
                date__lte=today
            )
            
            if not income_qs.exists():
                return None
            
            # Calculate monthly totals for each of the last 3 months
            monthly_totals = []
            
            for i in range(3):
                # Calculate the target month
                current_month = today.month
                current_year = today.year
                
                target_month = current_month - i
                target_year = current_year
                
                while target_month <= 0:
                    target_month += 12
                    target_year -= 1
                
                # Get first and last day of target month
                first_day = date(target_year, target_month, 1)
                last_day = date(target_year, target_month, calendar.monthrange(target_year, target_month)[1])
                
                # Get income for this month
                month_income = income_qs.filter(
                    date__gte=first_day,
                    date__lte=last_day
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                
                monthly_totals.append(float(month_income))
            
            # Calculate average monthly income
            avg_monthly_income = sum(monthly_totals) / len(monthly_totals) if monthly_totals else 0
            
            # Get next month name for display
            next_month_num = today.month + 1
            next_month_year = today.year
            if next_month_num > 12:
                next_month_num = 1
                next_month_year += 1
            next_month_name = calendar.month_name[next_month_num]
            
            return {
                'predicted_amount': round(avg_monthly_income, 2),
                'month': next_month_name,
                'year': next_month_year,
                'based_on_avg': round(avg_monthly_income, 2),
                'has_data': True,
                'trend': 'stable'  # Could be enhanced with trend detection
            }
            
        except Exception as e:
            logger.error(f"Error calculating income prediction for user {user.id}: {e}")
            return None

    @staticmethod
    def predict_this_month(user):
        """
        Predict income for current month based on historical data.
        """
        try:
            from userincome.models import UserIncome
            income_count = UserIncome.objects.filter(owner=user).count()
            
            if income_count == 0:
                return None
            
            today = timezone.now().date()
            
            # Get current month income
            current_month_income = UserIncome.objects.filter(
                owner=user,
                date__month=today.month,
                date__year=today.year
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            
            # Calculate average from last 3 months
            three_months_ago = today - timedelta(days=90)
            income_qs = UserIncome.objects.filter(
                owner=user,
                date__gte=three_months_ago,
                date__lte=today
            )
            
            if not income_qs.exists():
                return None
            
            # Calculate average monthly income
            monthly_totals = []
            for i in range(3):
                current_month = today.month
                current_year = today.year
                
                target_month = current_month - i
                target_year = current_year
                
                while target_month <= 0:
                    target_month += 12
                    target_year -= 1
                
                first_day = date(target_year, target_month, 1)
                last_day = date(target_year, target_month, calendar.monthrange(target_year, target_month)[1])
                
                month_income = income_qs.filter(
                    date__gte=first_day,
                    date__lte=last_day
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                
                monthly_totals.append(float(month_income))
            
            avg_monthly_income = sum(monthly_totals) / len(monthly_totals) if monthly_totals else 0
            
            # Days passed this month
            days_passed = today.day
            # Days in current month
            days_in_month = calendar.monthrange(today.year, today.month)[1]
            # Expected income based on average (pro-rated)
            expected_pro_rated = (avg_monthly_income / days_in_month) * days_passed
            
            return {
                'current_month_total': round(float(current_month_income), 2),
                'predicted_total': round(avg_monthly_income, 2),
                'expected_by_now': round(expected_pro_rated, 2),
                'has_data': True
            }
            
        except Exception as e:
            logger.error(f"Error calculating this month prediction for user {user.id}: {e}")
            return None

