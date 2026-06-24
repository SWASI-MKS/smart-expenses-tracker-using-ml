"""
Analytics Service - Financial Intelligence & Insights
=====================================================
Comprehensive analytics including:
- Financial Health Score calculation
- Trend analysis (7-day, 30-day moving averages)
- Category comparison analytics
- AI-style smart insights generation
- Spending volatility analysis
"""

from django.db.models import Sum, Avg, Count
from django.db.models.functions import ExtractMonth, ExtractDay
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import math
import logging

from expenses.models import Expense, ExpenseLimit, Category
from userincome.models import UserIncome, Source
from goals.models import Goal

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Enterprise-grade analytics service for financial intelligence.
    All calculations are production-ready with caching and error handling.
    """
    
    CACHE_TIMEOUT = 300  # 5 minutes
    
    # Health score weights (must sum to 1.0)
    WEIGHT_INCOME_RATIO = 0.35
    WEIGHT_BUDGET_ADHERENCE = 0.25
    WEIGHT_SAVINGS_CONSISTENCY = 0.25
    WEIGHT_SPENDING_VOLATILITY = 0.15
    
    @staticmethod
    def _get_cache_key(user_id, key_prefix):
        """Generate user-specific cache key."""
        return f"analytics_{user_id}_{key_prefix}"
    
    # =====================================================
    # FINANCIAL HEALTH SCORE
    # =====================================================
    
    @staticmethod
    def calculate_financial_health_score(user, use_cache=True):
        """
        Calculate comprehensive financial health score (0-100).
        
        Formula:
        Total Score = (income_score × 0.35) + (budget_score × 0.25) + 
                      (savings_score × 0.25) + (volatility_score × 0.15)
        
        Returns:
            dict: {score, breakdown, recommendation}
        """
        cache_key = AnalyticsService._get_cache_key(user.id, 'health_score')
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        try:
            today = timezone.now().date()
            start_of_month = today.replace(day=1)
            
            # 1. SPENDING VS INCOME RATIO (35%)
            income_score = AnalyticsService._calculate_income_ratio_score(user, start_of_month, today)
            
            # 2. BUDGET ADHERENCE (25%)
            budget_score = AnalyticsService._calculate_budget_adherence_score(user, start_of_month, today)
            
            # 3. SAVINGS CONSISTENCY (25%)
            savings_score = AnalyticsService._calculate_savings_consistency_score(user)
            
            # 4. SPENDING VOLATILITY (15%)
            volatility_score = AnalyticsService._calculate_volatility_score(user, today)
            
            # Calculate weighted total
            total_score = (
                income_score['score'] * AnalyticsService.WEIGHT_INCOME_RATIO +
                budget_score['score'] * AnalyticsService.WEIGHT_BUDGET_ADHERENCE +
                savings_score['score'] * AnalyticsService.WEIGHT_SAVINGS_CONSISTENCY +
                volatility_score['score'] * AnalyticsService.WEIGHT_SPENDING_VOLATILITY
            )
            
            result = {
                'score': round(total_score),
                'breakdown': {
                    'income_ratio': income_score,
                    'budget_adherence': budget_score,
                    'savings_consistency': savings_score,
                    'spending_volatility': volatility_score
                },
                'recommendation': AnalyticsService._get_health_recommendation(total_score),
                'grade': AnalyticsService._get_health_grade(total_score)
            }
            
            cache.set(cache_key, result, AnalyticsService.CACHE_TIMEOUT)
            return result
            
        except Exception as e:
            logger.error(f"Error calculating financial health for user {user.id}: {e}")
            return AnalyticsService._empty_health_result()
    
    @staticmethod
    def _calculate_income_ratio_score(user, start_date, end_date):
        """Calculate score based on savings rate (income - expenses / income)."""
        total_income = UserIncome.objects.filter(
            owner=user, date__gte=start_date, date__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total_expenses = Expense.objects.filter(
            owner=user, date__gte=start_date, date__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        if total_income > 0:
            savings_rate = (total_income - total_expenses) / total_income
            
            if savings_rate >= 0.20:
                score = 100
                status = 'excellent'
            elif savings_rate >= 0.10:
                score = 70
                status = 'good'
            elif savings_rate >= 0:
                score = 40
                status = 'fair'
            else:
                score = 10
                status = 'poor'
        else:
            score = 50 if total_expenses == 0 else 20
            status = 'no_income' if total_income == 0 else 'deficit'
        
        return {
            'score': score,
            'status': status,
            'savings_rate': round(savings_rate * 100, 1) if total_income > 0 else 0,
            'total_income': total_income,
            'total_expenses': total_expenses
        }
    
    @staticmethod
    def _calculate_budget_adherence_score(user, start_date, end_date):
        """Calculate score based on budget adherence."""
        expense_limit = ExpenseLimit.objects.filter(owner=user).first()
        
        if not expense_limit or not expense_limit.daily_expense_limit:
            return {'score': 50, 'status': 'no_budget', 'adherence': 0}
        
        days_in_period = (end_date - start_date).days + 1
        expected_spending = expense_limit.daily_expense_limit * days_in_period
        
        actual_spending = Expense.objects.filter(
            owner=user, date__gte=start_date, date__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        if expected_spending > 0:
            adherence_ratio = actual_spending / expected_spending
            
            if adherence_ratio <= 0.7:
                score = 100
                status = 'excellent'
            elif adherence_ratio <= 0.9:
                score = 80
                status = 'good'
            elif adherence_ratio <= 1.0:
                score = 60
                status = 'fair'
            else:
                score = 30
                status = 'over_budget'
        else:
            score = 100
            status = 'no_spending'
        
        return {
            'score': score,
            'status': status,
            'adherence': round(adherence_ratio * 100, 1) if expected_spending > 0 else 0,
            'expected': expected_spending,
            'actual': actual_spending
        }
    
    @staticmethod
    def _calculate_savings_consistency_score(user):
        """Calculate score based on savings consistency over 3 months."""
        today = timezone.now().date()
        monthly_savings = []
        
        for i in range(3):
            month_start = (today - timedelta(days=30 * i)).replace(day=1)
            if i == 0:
                month_end = today
            else:
                month_end = (today - timedelta(days=30 * (i - 1))).replace(day=1) - timedelta(days=1)
            
            income = UserIncome.objects.filter(
                owner=user, date__gte=month_start, date__lte=month_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            expenses = Expense.objects.filter(
                owner=user, date__gte=month_start, date__lte=month_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            monthly_savings.append(income - expenses)
        
        positive_months = sum(1 for s in monthly_savings if s > 0)
        score = (positive_months / 3) * 100
        
        return {
            'score': round(score),
            'status': 'excellent' if score >= 80 else 'good' if score >= 60 else 'fair' if score >= 40 else 'poor',
            'monthly_savings': [round(s, 2) for s in monthly_savings],
            'positive_months': positive_months
        }
    
    @staticmethod
    def _calculate_volatility_score(user, today):
        """Calculate score based on spending volatility (lower is better)."""
        thirty_days_ago = today - timedelta(days=30)
        
        daily_expenses = Expense.objects.filter(
            owner=user, date__gte=thirty_days_ago, date__lte=today
        ).values('date').annotate(daily_total=Sum('amount')).order_by('date')
        
        expense_list = list(daily_expenses)
        
        if len(expense_list) < 7:
            return {'score': 50, 'status': 'insufficient_data', 'cv': 0}
        
        amounts = [e['daily_total'] for e in expense_list]
        avg = sum(amounts) / len(amounts)
        
        if avg > 0:
            variance = sum((x - avg) ** 2 for x in amounts) / len(amounts)
            std_dev = math.sqrt(variance)
            cv = std_dev / avg  # Coefficient of variation
            
            if cv <= 0.5:
                score = 100
                status = 'stable'
            elif cv <= 0.75:
                score = 80
                status = 'moderate'
            elif cv <= 1.0:
                score = 60
                status = 'variable'
            else:
                score = 40
                status = 'volatile'
        else:
            score = 100
            status = 'no_spending'
        
        return {
            'score': score,
            'status': status,
            'cv': round(cv, 2) if avg > 0 else 0,
            'avg_daily': round(avg, 2)
        }
    
    @staticmethod
    def _get_health_recommendation(score):
        """Get recommendation based on health score."""
        if score >= 80:
            return "Excellent! Your finances are in great shape. Keep up the good work!"
        elif score >= 60:
            return "Good. You're managing money well with room for improvement."
        elif score >= 40:
            return "Fair. Consider reviewing your spending habits and increasing savings."
        else:
            return "Needs attention. Focus on building savings and reducing expenses."
    
    @staticmethod
    def _get_health_grade(score):
        """Get letter grade based on health score."""
        if score >= 90:
            return 'A+'
        elif score >= 80:
            return 'A'
        elif score >= 70:
            return 'B+'
        elif score >= 60:
            return 'B'
        elif score >= 50:
            return 'C'
        elif score >= 40:
            return 'D'
        else:
            return 'F'
    
    @staticmethod
    def _empty_health_result():
        """Return empty result structure."""
        return {
            'score': 0,
            'breakdown': {},
            'recommendation': 'Unable to calculate financial health',
            'grade': 'N/A'
        }
    
    # =====================================================
    # TREND ANALYSIS
    # =====================================================
    
    @staticmethod
    def get_trend_analysis(user, days=30, use_cache=True):
        """
        Get comprehensive trend analysis with moving averages.
        
        Returns:
            dict: {daily_data, moving_averages, comparison}
        """
        cache_key = AnalyticsService._get_cache_key(user.id, f'trend_{days}')
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        try:
            today = timezone.now().date()
            start_date = today - timedelta(days=days)
            
            # Get daily expenses
            expenses = Expense.objects.filter(
                owner=user, date__gte=start_date, date__lte=today
            ).values('date').annotate(total=Sum('amount')).order_by('date')
            
            expense_dict = {e['date']: e['total'] for e in expenses}
            
            # Generate date range
            dates = []
            current = start_date
            while current <= today:
                dates.append(current)
                current += timedelta(days=1)
            
            # Calculate moving averages
            ma_7 = AnalyticsService._calculate_moving_average(expense_dict, dates, 7)
            ma_30 = AnalyticsService._calculate_moving_average(expense_dict, dates, 30)
            
            # Compare with previous period
            mid = len(dates) // 2
            current_period = sum(expense_dict.get(d, 0) for d in dates[mid:])
            prev_period = sum(expense_dict.get(d, 0) for d in dates[:mid])
            
            comparison = {}
            if prev_period > 0:
                change = ((current_period - prev_period) / prev_period) * 100
                comparison = {
                    'current': round(current_period, 2),
                    'previous': round(prev_period, 2),
                    'change': round(change, 1),
                    'trend': 'up' if change > 0 else 'down' if change < 0 else 'stable'
                }
            
            result = {
                'daily': [{'date': d.strftime('%Y-%m-%d'), 'amount': expense_dict.get(d, 0)} for d in dates],
                'moving_avg_7': ma_7,
                'moving_avg_30': ma_30,
                'comparison': comparison,
                'total_spent': round(sum(expense_dict.values()), 2),
                'avg_daily': round(sum(expense_dict.values()) / len(expense_dict), 2) if expense_dict else 0
            }
            
            cache.set(cache_key, result, AnalyticsService.CACHE_TIMEOUT)
            return result
            
        except Exception as e:
            logger.error(f"Error calculating trend for user {user.id}: {e}")
            return {'daily': [], 'moving_avg_7': [], 'moving_avg_30': [], 'comparison': {}}
    
    @staticmethod
    def _calculate_moving_average(expense_dict, dates, window):
        """Calculate moving average for given window."""
        ma = []
        for i, d in enumerate(dates):
            if i >= window - 1:
                window_sum = sum(expense_dict.get(dates[j], 0) for j in range(i - window + 1, i + 1))
                ma.append({'date': d.strftime('%Y-%m-%d'), 'value': round(window_sum / window, 2)})
            else:
                ma.append({'date': d.strftime('%Y-%m-%d'), 'value': 0})
        return ma
    
    # =====================================================
    # AI-STYLE INSIGHTS
    # =====================================================
    
    @staticmethod
    def generate_smart_insights(user, use_cache=True):
        """
        Generate intelligent insights based on spending patterns.
        
        Returns list of insight dictionaries with:
        - type: warning/success/info
        - icon: font-awesome icon class
        - message: human-readable insight
        - metric: optional numerical value
        """
        cache_key = AnalyticsService._get_cache_key(user.id, 'insights')
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        insights = []
        
        try:
            insights.extend(AnalyticsService._get_spending_comparison_insights(user))
            insights.extend(AnalyticsService._get_budget_projection_insights(user))
            insights.extend(AnalyticsService._get_category_trend_insights(user))
            insights.extend(AnalyticsService._get_savings_insights(user))
            insights.extend(AnalyticsService._get_transaction_insights(user))
            
            # Limit to 5 insights
            result = insights[:5]
            
            cache.set(cache_key, result, AnalyticsService.CACHE_TIMEOUT)
            return result
            
        except Exception as e:
            logger.error(f"Error generating insights for user {user.id}: {e}")
            return []
    
    @staticmethod
    def _get_spending_comparison_insights(user):
        """Compare spending with previous periods."""
        insights = []
        today = timezone.now().date()
        
        # This week vs last week
        week_start = today - timedelta(days=7)
        two_weeks_ago = today - timedelta(days=14)
        
        this_week = Expense.objects.filter(
            owner=user, date__gte=week_start, date__lte=today
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        last_week = Expense.objects.filter(
            owner=user, date__gte=two_weeks_ago, date__lt=week_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        if last_week > 0:
            change = ((this_week - last_week) / last_week) * 100
            
            if change > 15:
                insights.append({
                    'type': 'warning',
                    'icon': 'fa-exclamation-circle',
                    'message': f"You are spending {abs(round(change))}% more than last week.",
                    'metric': round(change, 1)
                })
            elif change < -15:
                insights.append({
                    'type': 'success',
                    'icon': 'fa-check-circle',
                    'message': f"Great job! You're spending {abs(round(change))}% less than last week.",
                    'metric': round(change, 1)
                })
        
        return insights
    
    @staticmethod
    def _get_budget_projection_insights(user):
        """Project budget exhaustion date."""
        insights = []
        
        expense_limit = ExpenseLimit.objects.filter(owner=user).first()
        if not expense_limit or not expense_limit.daily_expense_limit:
            return insights
        
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        
        days_in_month = 30
        monthly_budget = expense_limit.daily_expense_limit * days_in_month
        
        spent = Expense.objects.filter(
            owner=user, date__gte=start_of_month, date__lte=today
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        days_remaining = days_in_month - (today - start_of_month).days
        
        if days_remaining > 0 and spent < monthly_budget:
            daily_rate = spent / (days_in_month - days_remaining + 1)
            days_until_budget = (monthly_budget - spent) / daily_rate if daily_rate > 0 else 999
            
            if days_until_budget < days_remaining:
                insights.append({
                    'type': 'danger',
                    'icon': 'fa-clock',
                    'message': f"At current rate, you will exceed budget in {int(days_until_budget)} days.",
                    'metric': int(days_until_budget)
                })
        
        return insights
    
    @staticmethod
    def _get_category_trend_insights(user):
        """Analyze category trends."""
        insights = []
        today = timezone.now().date()
        
        current_month = today.replace(day=1)
        prev_month = (today - timedelta(days=1)).replace(day=1)
        
        current_cats = dict(Expense.objects.filter(
            owner=user, date__gte=current_month
        ).values('category').annotate(total=Sum('amount')).values_list('category', 'total'))
        
        prev_cats = dict(Expense.objects.filter(
            owner=user, date__gte=prev_month, date__lt=current_month
        ).values('category').annotate(total=Sum('amount')).values_list('category', 'total'))
        
        for cat, amount in current_cats.items():
            prev_amount = prev_cats.get(cat, 0)
            if prev_amount > 0:
                change = ((amount - prev_amount) / prev_amount) * 100
                if change > 30:
                    insights.append({
                        'type': 'info',
                        'icon': 'fa-chart-line',
                        'message': f"{cat} spending is trending up {round(change)}% vs last month.",
                        'metric': round(change, 1)
                    })
        
        return insights
    
    @staticmethod
    def _get_savings_insights(user):
        """Analyze savings rate."""
        insights = []
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        
        income = UserIncome.objects.filter(
            owner=user, date__gte=start_of_month, date__lte=today
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        expenses = Expense.objects.filter(
            owner=user, date__gte=start_of_month, date__lte=today
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        net_savings = income - expenses
        
        if income > 0:
            savings_rate = (net_savings / income) * 100
            
            if net_savings < 0:
                insights.append({
                    'type': 'warning',
                    'icon': 'fa-wallet',
                    'message': "You're spending more than you earn this month.",
                    'metric': round(net_savings, 2)
                })
            elif savings_rate >= 20:
                insights.append({
                    'type': 'success',
                    'icon': 'fa-piggy-bank',
                    'message': f"Excellent savings rate of {round(savings_rate)}%!",
                    'metric': round(savings_rate, 1)
                })
        
        return insights
    
    @staticmethod
    def _get_transaction_insights(user):
        """Analyze transaction patterns."""
        insights = []
        today = timezone.now().date()
        
        # Small transactions
        small_count = Expense.objects.filter(
            owner=user, date__gte=today - timedelta(days=7), amount__lt=10
        ).count()
        
        if small_count >= 10:
            insights.append({
                'type': 'info',
                'icon': 'fa-coffee',
                'message': f"You have {small_count} small transactions this week. These add up!",
                'metric': small_count
            })
        
        return insights
