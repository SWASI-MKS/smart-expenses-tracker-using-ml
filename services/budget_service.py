"""
Budget Service - Category-wise Budget Management
===============================================
Service for managing budgets including:
- Category-wise budget tracking
- Budget vs actual comparisons
- Budget alerts and projections
- Spending projections
"""

from django.db.models import Sum
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

from expenses.models import Expense, ExpenseLimit, Category
from userincome.models import UserIncome

logger = logging.getLogger(__name__)


class BudgetService:
    """
    Service for managing budgets at category and overall levels.
    """
    
    CACHE_TIMEOUT = 300  # 5 minutes
    
    @staticmethod
    def _get_cache_key(user_id, key_prefix):
        """Generate user-specific cache key."""
        return f"budget_{user_id}_{key_prefix}"
    
    @staticmethod
    def get_overall_budget_status(user, use_cache=True):
        """
        Get overall monthly budget status.
        
        Returns:
            dict: {limit, spent, remaining, percentage, status}
        """
        cache_key = BudgetService._get_cache_key(user.id, 'overall')
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        try:
            today = timezone.now().date()
            start_of_month = today.replace(day=1)
            
            # Get budget limit
            expense_limit = ExpenseLimit.objects.filter(owner=user).first()
            
            if not expense_limit or not expense_limit.monthly_expense_limit:
                # Try daily limit converted to monthly
                if expense_limit and expense_limit.daily_expense_limit:
                    monthly_limit = expense_limit.daily_expense_limit * 30
                else:
                    return BudgetService._no_budget_response()
            else:
                monthly_limit = expense_limit.monthly_expense_limit
            
            # Get spending
            spent = Expense.objects.filter(
                owner=user,
                date__gte=start_of_month,
                date__lte=today
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            remaining = monthly_limit - spent
            percentage = (spent / monthly_limit * 100) if monthly_limit > 0 else 0
            
            # Determine status
            if percentage < 70:
                status = 'green'
                color = '#10b981'
            elif percentage < 90:
                status = 'yellow'
                color = '#f59e0b'
            elif percentage <= 100:
                status = 'orange'
                color = '#f97316'
            else:
                status = 'red'
                color = '#ef4444'
            
            # Calculate daily average
            days_passed = (today - start_of_month).days + 1
            daily_avg = spent / days_passed if days_passed > 0 else 0
            
            # Project end of month spending
            projected = daily_avg * 30
            
            result = {
                'limit': round(monthly_limit, 2),
                'spent': round(spent, 2),
                'remaining': round(remaining, 2),
                'percentage': round(percentage, 1),
                'status': status,
                'color': color,
                'daily_average': round(daily_avg, 2),
                'projected_spending': round(projected, 2),
                'days_remaining': 30 - days_passed,
                'has_budget': True
            }
            
            cache.set(cache_key, result, BudgetService.CACHE_TIMEOUT)
            return result
            
        except Exception as e:
            logger.error(f"Error getting overall budget status: {e}")
            return BudgetService._no_budget_response()
    
    @staticmethod
    def _no_budget_response():
        """Return response when no budget is set."""
        return {
            'limit': 0,
            'spent': 0,
            'remaining': 0,
            'percentage': 0,
            'status': 'no_budget',
            'color': '#6b7280',
            'has_budget': False,
            'message': 'No budget set. Set a budget to track spending.'
        }
    
    @staticmethod
    def get_category_budgets(user, use_cache=True):
        """
        Get budget status for each category.
        
        Returns:
            list: [{category, budget, spent, remaining, percentage, status}, ...]
        """
        cache_key = BudgetService._get_cache_key(user.id, 'categories')
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        try:
            today = timezone.now().date()
            start_of_month = today.replace(day=1)
            
            # Get all categories with spending this month
            categories = Category.objects.filter(
                models.Q(owner=user) | models.Q(is_global=True)
            ).distinct()
            
            # Get spending by category
            category_spending = Expense.objects.filter(
                owner=user,
                date__gte=start_of_month,
                date__lte=today
            ).values('category').annotate(spent=Sum('amount'))
            
            spending_dict = {c['category']: c['spent'] for c in category_spending}
            
            result = []
            for category in categories:
                budget = category.budget_limit if category.budget_limit else 0
                spent = spending_dict.get(category.name, 0)
                remaining = budget - spent if budget > 0 else None
                percentage = (spent / budget * 100) if budget > 0 else 0
                
                # Determine status
                if budget == 0:
                    status = 'no_budget'
                    color = '#6b7280'
                elif percentage < 70:
                    status = 'green'
                    color = '#10b981'
                elif percentage < 90:
                    status = 'yellow'
                    color = '#f59e0b'
                elif percentage <= 100:
                    status = 'orange'
                    color = '#f97316'
                else:
                    status = 'red'
                    color = '#ef4444'
                
                result.append({
                    'category': category.name,
                    'icon': category.icon or 'fa-tag',
                    'color': category.color if hasattr(category, 'color') else color,
                    'budget': round(budget, 2),
                    'spent': round(spent, 2),
                    'remaining': round(remaining, 2) if remaining is not None else None,
                    'percentage': round(percentage, 1),
                    'status': status,
                    'color': color
                })
            
            # Sort by percentage (most over budget first)
            result.sort(key=lambda x: x['percentage'], reverse=True)
            
            cache.set(cache_key, result, BudgetService.CACHE_TIMEOUT)
            return result
            
        except Exception as e:
            logger.error(f"Error getting category budgets: {e}")
            return []
    
    @staticmethod
    def set_category_budget(user, category_name, budget_amount):
        """
        Set or update budget for a specific category.
        
        Args:
            user: User instance
            category_name: Name of the category
            budget_amount: Monthly budget amount
        """
        try:
            category = Category.objects.get(name=category_name, owner=user)
            category.budget_limit = budget_amount
            category.save()
            
            # Invalidate cache
            cache.delete(BudgetService._get_cache_key(user.id, 'categories'))
            
            return True
        except Category.DoesNotExist:
            # Create new category with budget
            Category.objects.create(
                name=category_name,
                owner=user,
                budget_limit=budget_amount
            )
            return True
        except Exception as e:
            logger.error(f"Error setting category budget: {e}")
            return False
    
    @staticmethod
    def set_overall_budget(user, daily_limit=None, monthly_limit=None):
        """
        Set or update overall budget limits.
        
        Args:
            user: User instance
            daily_limit: Daily expense limit
            monthly_limit: Monthly expense limit
        """
        try:
            expense_limit, created = ExpenseLimit.objects.get_or_create(
                owner=user,
                defaults={
                    'daily_expense_limit': daily_limit or 0,
                    'monthly_expense_limit': monthly_limit or 0
                }
            )
            
            if not created:
                if daily_limit is not None:
                    expense_limit.daily_expense_limit = daily_limit
                if monthly_limit is not None:
                    expense_limit.monthly_expense_limit = monthly_limit
                expense_limit.save()
            
            # Invalidate cache
            cache.delete(BudgetService._get_cache_key(user.id, 'overall'))
            cache.delete(BudgetService._get_cache_key(user.id, 'categories'))
            
            return True
        except Exception as e:
            logger.error(f"Error setting overall budget: {e}")
            return False
    
    @staticmethod
    def get_budget_alerts(user):
        """
        Get list of budget alerts.
        
        Returns:
            list: [{type, category, message, percentage}]
        """
        alerts = []
        
        try:
            today = timezone.now().date()
            start_of_month = today.replace(day=1)
            days_passed = (today - start_of_month).days + 1
            
            # Check overall budget
            overall = BudgetService.get_overall_budget_status(user, use_cache=False)
            
            if overall['has_budget']:
                if overall['percentage'] >= 100:
                    alerts.append({
                        'type': 'danger',
                        'category': 'Overall',
                        'message': 'Monthly budget exceeded!',
                        'percentage': overall['percentage']
                    })
                elif overall['percentage'] >= 90:
                    alerts.append({
                        'type': 'warning',
                        'category': 'Overall',
                        'message': f"{overall['percentage']}% of monthly budget used",
                        'percentage': overall['percentage']
                    })
            
            # Check category budgets
            categories = BudgetService.get_category_budgets(user, use_cache=False)
            
            for cat in categories:
                if cat['percentage'] >= 100:
                    alerts.append({
                        'type': 'danger',
                        'category': cat['category'],
                        'message': f"{cat['category']} budget exceeded!",
                        'percentage': cat['percentage']
                    })
                elif cat['percentage'] >= 90:
                    alerts.append({
                        'type': 'warning',
                        'category': cat['category'],
                        'message': f"{cat['category']}: {cat['percentage']}% of budget used",
                        'percentage': cat['percentage']
                    })
            
            # Check if on track to exceed budget
            if overall['has_budget'] and overall['projected_spending'] > overall['limit']:
                alerts.append({
                    'type': 'info',
                    'category': 'Projection',
                    'message': f"At current rate, you'll spend ${overall['projected_spending']} this month",
                    'percentage': (overall['projected_spending'] / overall['limit'] * 100) if overall['limit'] > 0 else 0
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting budget alerts: {e}")
            return []
    
    @staticmethod
    def get_spending_projection(user, days_ahead=7):
        """
        Project spending for upcoming days based on current rate.
        
        Args:
            user: User instance
            days_ahead: Number of days to project ahead
        
        Returns:
            dict: {projected_spending, daily_rate, days_ahead}
        """
        try:
            today = timezone.now().date()
            start_of_month = today.replace(day=1)
            days_passed = (today - start_of_month).days + 1
            
            # Get current month spending
            spent = Expense.objects.filter(
                owner=user,
                date__gte=start_of_month,
                date__lte=today
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Calculate daily rate
            daily_rate = spent / days_passed if days_passed > 0 else 0
            
            # Project future spending
            projected = daily_rate * (days_passed + days_ahead)
            
            return {
                'current_spending': round(spent, 2),
                'daily_rate': round(daily_rate, 2),
                'days_ahead': days_ahead,
                'projected_spending': round(projected, 2),
                'projected_additional': round(daily_rate * days_ahead, 2)
            }
        except Exception as e:
            logger.error(f"Error getting spending projection: {e}")
            return {}
    
    @staticmethod
    def get_budget_recommendations(user):
        """
        Get AI-style recommendations for budget management.
        
        Returns:
            list: [{type, title, description}]
        """
        recommendations = []
        
        try:
            overall = BudgetService.get_overall_budget_status(user, use_cache=False)
            spending = BudgetService.get_spending_projection(user)
            
            # Recommendation 1: Budget utilization
            if overall['has_budget']:
                if overall['percentage'] < 50:
                    recommendations.append({
                        'type': 'success',
                        'title': 'Under Budget',
                        'description': f"You're using only {overall['percentage']}% of your budget. Great job!"
                    })
                elif overall['percentage'] > 90:
                    recommendations.append({
                        'type': 'warning',
                        'title': 'Budget Warning',
                        'description': "You've used over 90% of your monthly budget. Consider reducing spending."
                    })
            
            # Recommendation 2: Spending projection
            if overall['has_budget'] and spending.get('projected_spending', 0) > overall['limit']:
                recommendations.append({
                    'type': 'danger',
                    'title': 'Over Budget Projection',
                    'description': f"At your current rate, you'll exceed your budget by ${round(spending['projected_spending'] - overall['limit'], 2)} this month."
                })
            
            # Recommendation 3: Daily spending limit
            if overall['has_budget']:
                daily_remaining = overall['remaining'] / max(1, overall.get('days_remaining', 1))
                recommendations.append({
                    'type': 'info',
                    'title': 'Daily Spending Limit',
                    'description': f"To stay within budget, limit daily spending to ${round(daily_remaining, 2)} for the remaining {overall.get('days_remaining', 0)} days."
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting budget recommendations: {e}")
            return []


# Import models at module level for Category query
from django.db import models
