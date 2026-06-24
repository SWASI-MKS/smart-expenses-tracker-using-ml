"""
Enterprise-Grade Dashboard Service for Financial Intelligence
=============================================================
This service provides comprehensive financial analytics with:
- Optimized Django ORM queries (aggregation, annotate, prefetch_related)
- Caching support for heavy computations
- Timezone-safe calculations
- Production-ready error handling
- Scalable architecture for 10,000+ users
"""

from django.db.models import Sum, Avg, Count, F, FloatField
from django.db.models.functions import Coalesce
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import logging
import math

# Import category colors from expenses utils
from expenses.utils import CATEGORY_COLORS, get_category_color
from expenses.models import Expense, ExpenseLimit
from userincome.models import UserIncome
from goals.models import Goal

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Main dashboard service for financial intelligence.
    All methods are static for easy consumption without instantiation.
    """
    
    # Cache timeout in seconds (5 minutes)
    CACHE_TIMEOUT = 300
    
    @staticmethod
    def _get_cache_key(user_id, key_prefix):
        """Generate cache key with user isolation."""
        return f"dashboard_{user_id}_{key_prefix}"
    
    @staticmethod
    def _get_date_range(period='month'):
        """Get date range based on period."""
        today = timezone.now().date()
        if period == 'week':
            start = today - timedelta(days=7)
        elif period == 'month':
            start = today.replace(day=1)  # First day of current month
        elif period == 'quarter':
            start = today - timedelta(days=90)
        elif period == 'year':
            start = today.replace(day=1, month=1)  # First day of year
        else:
            start = today - timedelta(days=30)
        return start, today
    
    # =====================================================
    # FINANCIAL HEALTH SCORE CALCULATION
    # =====================================================
    
    @staticmethod
    def calculate_financial_health(user, period='month', use_cache=True):
        """
        Calculate comprehensive financial health score (0-100).
        
        Factors:
        - Spending vs Income Ratio (35%)
        - Budget Adherence (25%)
        - Savings Consistency (25%)
        - Spending Volatility (15%)
        
        Args:
            user: The user object
            period: Time period - 'week', 'month', 'quarter', 'year'
            use_cache: Whether to use cached data
        """
        # Calculate start date based on period
        period_days = {'week': 7, 'month': 30, 'quarter': 90, 'year': 365}
        days = period_days.get(period, 30)
        
        cache_key = DashboardService._get_cache_key(user.id, f'financial_health_{period}')
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        try:
            today = timezone.now().date()
            start_date = today - timedelta(days=days)
            
            # 1. SPENDING VS INCOME RATIO (35%)
            total_income = UserIncome.objects.filter(
                owner=user,
                date__gte=start_date,
                date__lte=today
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            total_expenses = Expense.objects.filter(
                owner=user,
                date__gte=start_date,
                date__lte=today
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            if total_income > 0:
                savings_rate = (total_income - total_expenses) / total_income
                # Good savings rate is 20%+, poor is negative
                if savings_rate >= 0.2:
                    income_score = 100
                elif savings_rate >= 0.1:
                    income_score = 70
                elif savings_rate >= 0:
                    income_score = 40
                else:
                    income_score = 10
            else:
                income_score = 50 if total_expenses == 0 else 20
            
            # 2. BUDGET ADHERENCE (25%)
            budget_limit = ExpenseLimit.objects.filter(owner=user).first()
            if budget_limit and budget_limit.daily_expense_limit:
                daily_limit = budget_limit.daily_expense_limit
                # Calculate days in period so far
                days_so_far = min(days, (today - start_date).days + 1)
                expected_period = daily_limit * days_so_far
                
                if expected_period > 0:
                    budget_ratio = total_expenses / expected_period
                    if budget_ratio <= 0.7:
                        budget_score = 100
                    elif budget_ratio <= 0.9:
                        budget_score = 80
                    elif budget_ratio <= 1.0:
                        budget_score = 60
                    else:
                        budget_score = 30
                else:
                    budget_score = 50
            else:
                budget_score = 50  # No budget set
            
            # 3. SAVINGS CONSISTENCY (25%)
            # Check last 3 months savings
            three_months_ago = today - timedelta(days=90)
            monthly_savings = []
            
            for i in range(3):
                month_start = (today - timedelta(days=30 * i)).replace(day=1)
                if i == 0:
                    month_end = today
                else:
                    month_end = (today - timedelta(days=30 * (i - 1))).replace(day=1) - timedelta(days=1)
                
                income = UserIncome.objects.filter(
                    owner=user,
                    date__gte=month_start,
                    date__lte=month_end
                ).aggregate(total=Sum('amount'))['total'] or 0
                
                expenses = Expense.objects.filter(
                    owner=user,
                    date__gte=month_start,
                    date__lte=month_end
                ).aggregate(total=Sum('amount'))['total'] or 0
                
                monthly_savings.append(income - expenses)
            
            positive_months = sum(1 for s in monthly_savings if s > 0)
            savings_score = (positive_months / 3) * 100
            
            # 4. SPENDING VOLATILITY (15%)
            # Lower volatility = higher score
            expenses_last_30 = Expense.objects.filter(
                owner=user,
                date__gte=today - timedelta(days=30)
            ).values('date').annotate(daily_total=Sum('amount'))
            
            if len(list(expenses_last_30)) >= 7:
                amounts = [e['daily_total'] for e in expenses_last_30]
                avg = sum(amounts) / len(amounts)
                if avg > 0:
                    std_dev = math.sqrt(sum((x - avg) ** 2 for x in amounts) / len(amounts))
                    cv = std_dev / avg  # Coefficient of variation
                    # CV < 0.5 is stable, > 1.0 is volatile
                    if cv <= 0.5:
                        volatility_score = 100
                    elif cv <= 0.75:
                        volatility_score = 80
                    elif cv <= 1.0:
                        volatility_score = 60
                    else:
                        volatility_score = 40
                else:
                    volatility_score = 100
            else:
                volatility_score = 50  # Not enough data
            
            # Calculate weighted total
            total_score = (
                income_score * 0.35 +
                budget_score * 0.25 +
                savings_score * 0.25 +
                volatility_score * 0.15
            )
            
            result = {
                'score': round(total_score),
                'income_score': income_score,
                'budget_score': budget_score,
                'savings_score': savings_score,
                'volatility_score': volatility_score,
                'total_income': total_income,
                'total_expenses': total_expenses,
                'net_savings': total_income - total_expenses,
                'explanation': DashboardService._get_health_explanation(total_score)
            }
            
            cache.set(cache_key, result, DashboardService.CACHE_TIMEOUT)
            return result
            
        except Exception as e:
            logger.error(f"Error calculating financial health for user {user.id}: {e}")
            return {
                'score': 0,
                'income_score': 0,
                'budget_score': 0,
                'savings_score': 0,
                'volatility_score': 0,
                'total_income': 0,
                'total_expenses': 0,
                'net_savings': 0,
                'explanation': 'Unable to calculate financial health'
            }
    
    @staticmethod
    def _get_health_explanation(score):
        """Get human-readable explanation of health score."""
        if score >= 80:
            return "Excellent! Your finances are in great shape."
        elif score >= 60:
            return "Good. You're managing money well with room for improvement."
        elif score >= 40:
            return "Fair. Consider reviewing your spending habits."
        else:
            return "Needs attention. Focus on building savings and reducing expenses."
    
    # =====================================================
    # BUDGET UTILIZATION
    # =====================================================
    
    @staticmethod
    def get_budget_utilization(user, use_cache=True):
        """
        Get monthly budget utilization with color coding.
        """
        cache_key = DashboardService._get_cache_key(user.id, 'budget_utilization')
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        try:
            today = timezone.now().date()
            start_of_month = today.replace(day=1)
            
            # Get daily expense limit
            expense_limit = ExpenseLimit.objects.filter(owner=user).first()
            
            if not expense_limit or not expense_limit.daily_expense_limit:
                return {
                    'has_limit': False,
                    'limit': 0,
                    'spent': 0,
                    'remaining': 0,
                    'percentage': 0,
                    'status': 'no_limit'
                }
            
            daily_limit = expense_limit.daily_expense_limit
            days_in_month = (today - start_of_month).days + 1
            monthly_limit = daily_limit * days_in_month
            
            # Get current month expenses
            total_spent = Expense.objects.filter(
                owner=user,
                date__gte=start_of_month,
                date__lte=today
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            remaining = monthly_limit - total_spent
            percentage = (total_spent / monthly_limit * 100) if monthly_limit > 0 else 0
            
            # Determine status and color
            if percentage < 70:
                status = 'green'
                color = '#10b981'
            elif percentage < 90:
                status = 'yellow'
                color = '#f59e0b'
            else:
                status = 'red'
                color = '#ef4444'
            
            result = {
                'has_limit': True,
                'limit': monthly_limit,
                'daily_limit': daily_limit,
                'spent': round(total_spent, 2),
                'remaining': round(remaining, 2),
                'percentage': round(percentage, 1),
                'status': status,
                'color': color,
                'days_remaining': 30 - (today - start_of_month).days
            }
            
            cache.set(cache_key, result, DashboardService.CACHE_TIMEOUT)
            return result
            
        except Exception as e:
            logger.error(f"Error calculating budget utilization for user {user.id}: {e}")
            return {
                'has_limit': False,
                'limit': 0,
                'spent': 0,
                'remaining': 0,
                'percentage': 0,
                'status': 'error'
            }
    
    # =====================================================
    # SPENDING VS INCOME COMPARISON
    # =====================================================
    
    @staticmethod
    def get_spending_vs_income(user, use_cache=True):
        """
        Compare income vs expenses with period-over-period changes.
        """
        cache_key = DashboardService._get_cache_key(user.id, 'spending_vs_income')
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        try:
            today = timezone.now().date()
            current_month_start = today.replace(day=1)
            
            # Current month
            current_income = UserIncome.objects.filter(
                owner=user,
                date__gte=current_month_start,
                date__lte=today
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            current_expenses = Expense.objects.filter(
                owner=user,
                date__gte=current_month_start,
                date__lte=today
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Previous month
            if today.month == 1:
                prev_month_start = today.replace(year=today.year-1, month=12, day=1)
            else:
                prev_month_start = today.replace(month=today.month-1, day=1)
            prev_month_end = current_month_start - timedelta(days=1)
            
            prev_income = UserIncome.objects.filter(
                owner=user,
                date__gte=prev_month_start,
                date__lte=prev_month_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            prev_expenses = Expense.objects.filter(
                owner=user,
                date__gte=prev_month_start,
                date__lte=prev_month_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Calculate changes
            def calc_change(current, previous):
                if previous == 0:
                    return 100 if current > 0 else 0
                return ((current - previous) / previous) * 100
            
            income_change = calc_change(current_income, prev_income)
            expense_change = calc_change(current_expenses, prev_expenses)
            
            # Net savings
            current_savings = current_income - current_expenses
            prev_savings = prev_income - prev_expenses
            
            result = {
                'income': {
                    'current': round(current_income, 2),
                    'previous': round(prev_income, 2),
                    'change': round(income_change, 1),
                    'trend': 'up' if income_change > 0 else 'down' if income_change < 0 else 'stable'
                },
                'expenses': {
                    'current': round(current_expenses, 2),
                    'previous': round(prev_expenses, 2),
                    'change': round(expense_change, 1),
                    'trend': 'up' if expense_change > 0 else 'down' if expense_change < 0 else 'stable'
                },
                'savings': {
                    'current': round(current_savings, 2),
                    'previous': round(prev_savings, 2),
                    'change': round(calc_change(current_savings, prev_savings), 1) if prev_savings != 0 else 0,
                    'trend': 'up' if current_savings > prev_savings else 'down' if current_savings < prev_savings else 'stable'
                }
            }
            
            cache.set(cache_key, result, DashboardService.CACHE_TIMEOUT)
            return result
            
        except Exception as e:
            logger.error(f"Error calculating spending vs income for user {user.id}: {e}")
            return {
                'income': {'current': 0, 'previous': 0, 'change': 0, 'trend': 'stable'},
                'expenses': {'current': 0, 'previous': 0, 'change': 0, 'trend': 'stable'},
                'savings': {'current': 0, 'previous': 0, 'change': 0, 'trend': 'stable'}
            }
    
    # =====================================================
    # CATEGORY BREAKDOWN (TOP 5)
    # =====================================================
    
    @staticmethod
    def get_category_breakdown(user, months=1, use_cache=True):
        """
        Get top 5 expense categories with percentages.
        Uses optimized aggregation to avoid N+1 queries.
        """
        cache_key = DashboardService._get_cache_key(user.id, f'category_breakdown_{months}')
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        try:
            today = timezone.now().date()
            start_date = today - timedelta(days=30 * months)
            
            # Optimized aggregation - single query
            categories = Expense.objects.filter(
                owner=user,
                date__gte=start_date,
                date__lte=today
            ).values('category').annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('-total')[:5]
            
            # Calculate total for percentage
            total_amount = sum(c['total'] for c in categories)
            
            # Format for chart - Use consistent category-based colors
            result = {
                'categories': [
                    {
                        'name': c['category'],
                        'amount': round(c['total'], 2),
                        'count': c['count'],
                        'percentage': round((c['total'] / total_amount * 100) if total_amount > 0 else 0, 1),
                        'color': get_category_color(c['category'])  # Use consistent category color
                    }
                    for c in categories
                ],
                'total': round(total_amount, 2),
                'has_data': total_amount > 0
            }
            
            cache.set(cache_key, result, DashboardService.CACHE_TIMEOUT)
            return result
            
        except Exception as e:
            logger.error(f"Error calculating category breakdown for user {user.id}: {e}")
            return {
                'categories': [],
                'total': 0,
                'has_data': False
            }
    
    # =====================================================
    # ROLLING TREND ANALYTICS
    # =====================================================
    
    @staticmethod
    def get_trend_data(user, days=30, use_cache=True):
        """
        Get rolling trend data for charts.
        Includes 7-day and 30-day moving averages.
        """
        cache_key = DashboardService._get_cache_key(user.id, f'trend_{days}')
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        try:
            today = timezone.now().date()
            start_date = today - timedelta(days=days)
            
            # Get daily expenses with aggregation
            daily_expenses = Expense.objects.filter(
                owner=user,
                date__gte=start_date,
                date__lte=today
            ).values('date').annotate(
                total=Sum('amount')
            ).order_by('date')
            
            # Build date-indexed dictionary
            expense_dict = {e['date']: e['total'] for e in daily_expenses}
            
            # Generate all dates in range
            dates = []
            current = start_date
            while current <= today:
                dates.append(current)
                current += timedelta(days=1)
            
            # Calculate 7-day moving average
            moving_avg_7 = []
            moving_avg_30 = []
            daily_values = []
            
            for i, date in enumerate(dates):
                amount = expense_dict.get(date, 0)
                daily_values.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'label': date.strftime('%b %d'),
                    'amount': amount
                })
                
                # 7-day MA
                if i >= 6:
                    week_sum = sum(expense_dict.get(dates[j], 0) for j in range(i-6, i+1))
                    moving_avg_7.append(week_sum / 7)
                else:
                    moving_avg_7.append(0)
                
                # 30-day MA
                if i >= 29:
                    month_sum = sum(expense_dict.get(dates[j], 0) for j in range(i-29, i+1))
                    moving_avg_30.append(month_sum / 30)
                else:
                    moving_avg_30.append(0)
            
            # Calculate comparison with previous period
            mid_point = len(dates) // 2
            current_period = sum(expense_dict.get(d, 0) for d in dates[mid_point:])
            prev_period = sum(expense_dict.get(d, 0) for d in dates[:mid_point])
            
            comparison = {}
            if prev_period > 0:
                change = ((current_period - prev_period) / prev_period) * 100
                comparison = {
                    'current': round(current_period, 2),
                    'previous': round(prev_period, 2),
                    'change': round(change, 1),
                    'trend': 'up' if change > 0 else 'down' if change < 0 else 'stable'
                }
            else:
                comparison = {
                    'current': round(current_period, 2),
                    'previous': 0,
                    'change': 0,
                    'trend': 'stable'
                }
            
            result = {
                'daily': daily_values,
                'moving_avg_7': [{'date': dates[i].strftime('%Y-%m-%d'), 'value': round(v, 2)} for i, v in enumerate(moving_avg_7)],
                'moving_avg_30': [{'date': dates[i].strftime('%Y-%m-%d'), 'value': round(v, 2)} for i, v in enumerate(moving_avg_30)],
                'comparison': comparison,
                'total_spent': round(sum(expense_dict.values()), 2),
                'average_daily': round(sum(expense_dict.values()) / len(expense_dict), 2) if expense_dict else 0
            }
            
            cache.set(cache_key, result, DashboardService.CACHE_TIMEOUT)
            return result
            
        except Exception as e:
            logger.error(f"Error calculating trend data for user {user.id}: {e}")
            return {
                'daily': [],
                'moving_avg_7': [],
                'moving_avg_30': [],
                'comparison': {'current': 0, 'previous': 0, 'change': 0, 'trend': 'stable'},
                'total_spent': 0,
                'average_daily': 0
            }
    
    # =====================================================
    # AI-STYLE INSIGHTS
    # =====================================================
    
    @staticmethod
    def generate_ai_insights(user, use_cache=True):
        """
        Generate intelligent insights based on spending patterns.
        """
        cache_key = DashboardService._get_cache_key(user.id, 'ai_insights')
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        insights = []
        
        try:
            today = timezone.now().date()
            
            # 1. Compare to last week
            week_start = today - timedelta(days=7)
            two_weeks_ago = today - timedelta(days=14)
            
            this_week_expenses = Expense.objects.filter(
                owner=user,
                date__gte=week_start,
                date__lte=today
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            last_week_expenses = Expense.objects.filter(
                owner=user,
                date__gte=two_weeks_ago,
                date__lt=week_start
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            if last_week_expenses > 0:
                week_change = ((this_week_expenses - last_week_expenses) / last_week_expenses) * 100
                if week_change > 15:
                    insights.append({
                        'type': 'warning',
                        'icon': 'fa-exclamation-circle',
                        'message': f"You are spending {abs(round(week_change))}% more than last week."
                    })
                elif week_change < -15:
                    insights.append({
                        'type': 'success',
                        'icon': 'fa-check-circle',
                        'message': f"Great job! You're spending {abs(round(week_change))}% less than last week."
                    })
            
            # 2. Budget projection
            budget_info = DashboardService.get_budget_utilization(user, use_cache=False)
            if budget_info.get('has_limit') and budget_info.get('percentage', 0) > 0:
                days_remaining = budget_info.get('days_remaining', 30)
                if days_remaining > 0:
                    daily_burn_rate = budget_info['spent'] / (30 - days_remaining + 1)
                    days_until_budget = (budget_info['limit'] - budget_info['spent']) / daily_burn_rate if daily_burn_rate > 0 else 999
                    
                    if days_until_budget < days_remaining:
                        insights.append({
                            'type': 'danger',
                            'icon': 'fa-clock',
                            'message': f"At current rate, you will exceed budget in {int(days_until_budget)} days."
                        })
            
            # 3. Category trends
            current_month = today.replace(day=1)
            prev_month = (today - timedelta(days=1)).replace(day=1)
            
            current_categories = dict(Expense.objects.filter(
                owner=user,
                date__gte=current_month
            ).values('category').annotate(total=Sum('amount')).values_list('category', 'total'))
            
            prev_categories = dict(Expense.objects.filter(
                owner=user,
                date__gte=prev_month,
                date__lt=current_month
            ).values('category').annotate(total=Sum('amount')).values_list('category', 'total'))
            
            for category, amount in current_categories.items():
                prev_amount = prev_categories.get(category, 0)
                if prev_amount > 0:
                    cat_change = ((amount - prev_amount) / prev_amount) * 100
                    if cat_change > 30:
                        insights.append({
                            'type': 'info',
                            'icon': 'fa-chart-line',
                            'message': f"{category} spending is trending up {round(cat_change)}% vs last month."
                        })
            
            # 4. Savings check
            spending_vs_income = DashboardService.get_spending_vs_income(user, use_cache=False)
            net_savings = spending_vs_income.get('savings', {}).get('current', 0)
            
            if net_savings < 0:
                insights.append({
                    'type': 'warning',
                    'icon': 'fa-wallet',
                    'message': "You're spending more than you earn this month. Consider reducing expenses."
                })
            elif net_savings > 0:
                savings_rate = (net_savings / spending_vs_income.get('income', {}).get('current', 1)) * 100
                if savings_rate >= 20:
                    insights.append({
                        'type': 'success',
                        'icon': 'fa-piggy-bank',
                        'message': f"Excellent savings rate of {round(savings_rate)}%! Keep it up!"
                    })
            
            # 5. Frequent small transactions
            small_transactions = Expense.objects.filter(
                owner=user,
                date__gte=today - timedelta(days=7),
                amount__lt=10
            ).count()
            
            if small_transactions >= 10:
                insights.append({
                    'type': 'info',
                    'icon': 'fa-coffee',
                    'message': f"You have {small_transactions} small transactions this week. These add up!"
                })
            
            result = {
                'insights': insights[:5],  # Limit to 5 insights
                'count': len(insights)
            }
            
            cache.set(cache_key, result, DashboardService.CACHE_TIMEOUT)
            return result
            
        except Exception as e:
            logger.error(f"Error generating AI insights for user {user.id}: {e}")
            return {'insights': [], 'count': 0}
    
    # =====================================================
    # SAVINGS GOALS PROGRESS
    # =====================================================
    
    @staticmethod
    def get_savings_goals(user, use_cache=True):
        """
        Get active savings goals with progress.
        """
        cache_key = DashboardService._get_cache_key(user.id, 'savings_goals')
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        try:
            # Import here to avoid circular imports
            from services.goal_service import GoalService
            
            # Update all goal statuses first (same as Goals page)
            GoalService.update_all_goals_status(user)
            
            today = timezone.now().date()
            
            # Get all non-archived goals (matching Goals page behavior)
            # Exclude only archived goals, show active/completed/overdue
            goals = Goal.objects.filter(
                owner=user
            ).exclude(status=Goal.STATUS_ARCHIVED).order_by('-created_at')[:5]
            
            result = {
                'goals': [],
                'has_goals': goals.exists()
            }
            
            for goal in goals:
                # Calculate progress - use correct field names from Goal model
                target_amount = float(goal.amount_to_save)
                current_amount = float(goal.current_saved_amount) if goal.current_saved_amount else 0
                
                progress = (current_amount / target_amount * 100) if target_amount > 0 else 0
                
                # Calculate days remaining
                days_remaining = None
                if goal.end_date:
                    days_remaining = (goal.end_date - today).days
                
                result['goals'].append({
                    'id': goal.id,
                    'name': goal.name,
                    'target': target_amount,
                    'current': current_amount,
                    'remaining': round(target_amount - current_amount, 2),
                    'progress': round(min(progress, 100), 1),
                    'target_date': goal.end_date.strftime('%Y-%m-%d') if goal.end_date else None,
                    'days_remaining': days_remaining,
                    'status': goal.status
                })
            
            cache.set(cache_key, result, DashboardService.CACHE_TIMEOUT)
            return result
            
        except Exception as e:
            logger.error(f"Error getting savings goals for user {user.id}: {e}")
            return {'goals': [], 'has_goals': False}
    
    # =====================================================
    # UPCOMING RECURRING EXPENSES (Placeholder)
    # =====================================================
    
    @staticmethod
    def get_upcoming_expenses(user, days=7, use_cache=True):
        """
        Get upcoming/recurring expenses.
        Note: This requires a RecurringExpense model to be fully functional.
        Currently returns placeholder data structure.
        """
        cache_key = DashboardService._get_cache_key(user.id, 'upcoming_expenses')
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        # For now, return expected upcoming based on recurring categories
        # In production, you'd have a RecurringExpense model
        result = {
            'expenses': [],
            'has_upcoming': False
        }
        
        cache.set(cache_key, result, 3600)  # Cache for 1 hour
        return result
    
    # =====================================================
    # RECENT ACTIVITY TIMELINE
    # =====================================================
    
    @staticmethod
    def get_activity_timeline(user, limit=10, use_cache=False):
        """
        Get recent expense activity timeline.
        Optimized with select_related if needed.
        """
        try:
            today = timezone.now().date()
            
            # Get recent expenses
            recent_expenses = Expense.objects.filter(
                owner=user
            ).order_by('-date', '-id')[:limit]
            
            activities = []
            for expense in recent_expenses:
                # Determine time period
                days_ago = (today - expense.date).days
                if days_ago == 0:
                    time_label = 'Today'
                elif days_ago == 1:
                    time_label = 'Yesterday'
                elif days_ago < 7:
                    time_label = f'{days_ago} days ago'
                else:
                    time_label = expense.date.strftime('%b %d')
                
                activities.append({
                    'id': expense.id,
                    'category': expense.category,
                    'description': expense.description,
                    'amount': expense.amount,
                    'date': expense.date.strftime('%Y-%m-%d'),
                    'time_label': time_label
                })
            
            return {
                'activities': activities,
                'has_activities': len(activities) > 0
            }
            
        except Exception as e:
            logger.error(f"Error getting activity timeline for user {user.id}: {e}")
            return {'activities': [], 'has_activities': False}
    
    # =====================================================
    # PREDICTIONS (Using PredictionService)
    # =====================================================
    
    @staticmethod
    def get_predictions(user, use_cache=True):
        """
        Get spending predictions for the user.
        Imports PredictionService dynamically to avoid circular imports.
        """
        cache_key = DashboardService._get_cache_key(user.id, 'predictions')
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        try:
            # Import here to avoid circular imports
            from expenses.prediction_service import PredictionService
            predictions = PredictionService.get_predictions(user)
            
            cache.set(cache_key, predictions, DashboardService.CACHE_TIMEOUT)
            return predictions
        except Exception as e:
            logger.error(f"Error getting predictions for user {user.id}: {e}")
            return {
                'today': 0,
                'tomorrow': 0,
                'this_week': 0,
                'this_month': 0,
                'has_data': False,
                'is_estimate': False
            }
    
    # =====================================================
    # COMPREHENSIVE DASHBOARD DATA
    # =====================================================
    
    @staticmethod
    def get_dashboard_data(user, period='month'):
        """
        Get all dashboard data in one call for efficient loading.
        Uses caching for each component.
        
        Args:
            user: The user object
            period: Time period for filtering - 'week', 'month', 'quarter', 'year'
        """
        # Calculate days based on period
        period_days = {
            'week': 7,
            'month': 30,
            'quarter': 90,
            'year': 365
        }
        days = period_days.get(period, 30)

        # Disable cache when period is specified to get fresh data
        use_cache = (period == 'month')  # Only cache default month period
        
        return {
            'financial_health': DashboardService.calculate_financial_health(user, period=period, use_cache=use_cache),
            'budget_utilization': DashboardService.get_budget_utilization(user, use_cache=use_cache),
            'spending_vs_income': DashboardService.get_spending_vs_income(user, use_cache=use_cache),
            'category_breakdown': DashboardService.get_category_breakdown(user, months=days//30, use_cache=use_cache),
            'trend_data': DashboardService.get_trend_data(user, days=days, use_cache=use_cache),
            'ai_insights': DashboardService.generate_ai_insights(user, use_cache=use_cache),
            'savings_goals': DashboardService.get_savings_goals(user),
            'upcoming_expenses': DashboardService.get_upcoming_expenses(user),
            'activity_timeline': DashboardService.get_activity_timeline(user),
            'predictions': DashboardService.get_predictions(user),
            'current_period': period,  # Return period to template for display
            # NEW: Advanced AI Insights
            'advanced_ai_insights': DashboardService.get_advanced_ai_insights(user, use_cache=use_cache),
        }
    
    # =====================================================
    # ADVANCED AI INSIGHTS (NEW)
    # =====================================================
    
    @staticmethod
    def get_advanced_ai_insights(user, use_cache=True):
        """
        Get advanced AI-powered insights from AIInsightsService.
        Includes all 10 advanced features.
        """
        cache_key = DashboardService._get_cache_key(user.id, 'advanced_ai_insights')
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        try:
            from services.ai_insights_service import AIInsightsService
            
            # Get all advanced insights
            insights = AIInsightsService.get_all_insights(user, use_cache=use_cache)
            
            # Also get cash flow forecast (needs user parameter)
            cash_flow = AIInsightsService.get_cash_flow_for_user(user)
            insights['cash_flow_forecast'] = cash_flow
            
            cache.set(cache_key, insights, DashboardService.CACHE_TIMEOUT)
            return insights
            
        except Exception as e:
            logger.error(f"Error getting advanced AI insights for user {user.id}: {e}")
            return AIInsightsService._empty_insights()
