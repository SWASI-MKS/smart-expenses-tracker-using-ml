"""
AI Financial Insights Service
============================
Advanced intelligent financial analysis powered by machine learning and data analytics.

Features:
- Spending Trend Prediction
- Anomaly Detection (Unusual Spending Alert)
- Financial Health Score (Enhanced)
- Cash Flow Forecasting
- Smart Budget Suggestions
- Goal Achievement Prediction
- Debt Risk Indicator
- Merchant Intelligence
- Subscription Detection
- Spending Efficiency Insights
"""

from django.db.models import Sum, Avg, Count, StdDev
from django.db.models.functions import ExtractMonth, ExtractWeek
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
from collections import defaultdict
from typing import Dict, List, Optional
import math
import logging

from expenses.models import Expense, ExpenseLimit
from userincome.models import UserIncome
from goals.models import Goal
from debts.models import Debt
from bank_simulator.models import CardTransaction, BankTransaction

logger = logging.getLogger(__name__)


class AIInsightsService:
    """
    Advanced AI-powered financial insights service.
    Provides comprehensive intelligent analysis of user finances.
    """
    
    CACHE_TIMEOUT = 300  # 5 minutes
    
    # Known subscription services for detection
    SUBSCRIPTION_KEYWORDS = [
        'netflix', 'spotify', 'apple', 'amazon prime', 'hulu', 'disney+', 
        'hbo', 'youtube premium', 'microsoft', 'adobe', 'dropbox',
        'gym', 'fitness', 'planet', 'mobile', 'phone', 'internet',
        'electricity', 'water', 'gas', 'insurance', 'netflix', 'spotify',
        'playstation', 'xbox', 'steam', 'twitch', 'patreon', 'medium',
        'linkedin', 'github', 'aws', 'heroku', 'digitalocean',
        'news', 'magazine', 'subscription', 'monthly', 'annual'
    ]
    
    @staticmethod
    def _get_cache_key(user_id, key_prefix):
        """Generate user-specific cache key."""
        return f"ai_insights_{user_id}_{key_prefix}"
    
    # =====================================================
    # MAIN METHOD - Get All AI Insights
    # =====================================================
    
    @staticmethod
    def get_all_insights(user, use_cache=True):
        """
        Get comprehensive AI insights - main entry point.
        Returns all insights in a structured format for the dashboard.
        """
        cache_key = AIInsightsService._get_cache_key(user.id, 'all_insights')
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        try:
            result = {
                'spending_trend_prediction': AIInsightsService.get_spending_trend_prediction(user),
                'anomaly_detection': AIInsightsService.detect_anomalies(user),
                'financial_health': AIInsightsService.get_enhanced_health_score(user),
                'cash_flow_forecast': AIInsightsService.get_cash_flow_forecast(user),
                'budget_suggestions': AIInsightsService.get_budget_suggestions(user),
                'goal_predictions': AIInsightsService.get_goal_predictions(user),
                'debt_risk': AIInsightsService.get_debt_risk_indicator(user),
                'merchant_intelligence': AIInsightsService.get_merchant_intelligence(user),
                'subscriptions': AIInsightsService.detect_subscriptions(user),
                'efficiency_insights': AIInsightsService.get_efficiency_insights(user),
            }
            
            cache.set(cache_key, result, AIInsightsService.CACHE_TIMEOUT)
            return result
            
        except Exception as e:
            logger.error(f"Error generating AI insights for user {user.id}: {e}")
            return AIInsightsService._empty_insights()
    
    # =====================================================
    # 1. SPENDING TREND PREDICTION
    # =====================================================
    
    @staticmethod
    def get_spending_trend_prediction(user, weeks_ahead=4):
        """
        Predict spending trends for upcoming weeks.
        Uses linear regression on historical data.
        """
        try:
            today = timezone.now().date()
            start_date = today - timedelta(days=90)  # 90 days of history
            
            # Get daily expenses
            daily_expenses = Expense.objects.filter(
                owner=user,
                date__gte=start_date,
                date__lte=today
            ).values('date').annotate(total=Sum('amount')).order_by('date')
            
            if not daily_expenses:
                return {
                    'has_data': False,
                    'predictions': [],
                    'trend': 'stable',
                    'confidence': 0
                }
            
            # Calculate weekly aggregates
            weekly_data = defaultdict(float)
            for expense in daily_expenses:
                week = expense['date'].isocalendar()[1]
                year = expense['date'].year
                key = f"{year}-W{week:02d}"
                weekly_data[key] += float(expense['total'])
            
            # Convert to list for trend calculation
            weeks = sorted(weekly_data.items())
            if len(weeks) < 4:
                return {
                    'has_data': False,
                    'predictions': [],
                    'trend': 'insufficient_data',
                    'confidence': 0
                }
            
            # Calculate trend using simple linear regression
            amounts = [w[1] for w in weeks]
            n = len(amounts)
            
            # Simple linear regression
            x_mean = (n - 1) / 2
            y_mean = sum(amounts) / n
            
            numerator = sum((i - x_mean) * (amounts[i] - y_mean) for i in range(n))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            
            if denominator > 0:
                slope = numerator / denominator
            else:
                slope = 0
            
            # Calculate R-squared for confidence
            y_pred = [y_mean + slope * (i - x_mean) for i in range(n)]
            ss_res = sum((amounts[i] - y_pred[i]) ** 2 for i in range(n))
            ss_tot = sum((amounts[i] - y_mean) ** 2 for i in range(n))
            
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            confidence = max(0, min(100, r_squared * 100))
            
            # Determine trend direction
            if slope > amounts[-1] * 0.05:
                trend = 'increasing'
            elif slope < -amounts[-1] * 0.05:
                trend = 'decreasing'
            else:
                trend = 'stable'
            
            # Generate predictions for upcoming weeks
            predictions = []
            base_amount = amounts[-1]
            
            for i in range(1, weeks_ahead + 1):
                pred_amount = base_amount + (slope * i)
                predictions.append({
                    'week': i,
                    'predicted_amount': max(0, round(pred_amount, 2)),
                    'trend_impact': 'up' if slope > 0 else 'down' if slope < 0 else 'stable'
                })
            
            # Category-specific predictions
            category_predictions = AIInsightsService._predict_by_category(user)
            
            return {
                'has_data': True,
                'predictions': predictions,
                'trend': trend,
                'confidence': round(confidence, 1),
                'weekly_average': round(y_mean, 2),
                'last_week_spending': round(amounts[-1], 2),
                'category_predictions': category_predictions,
                'slope': round(slope, 2)
            }
            
        except Exception as e:
            logger.error(f"Error in spending trend prediction: {e}")
            return {'has_data': False, 'predictions': [], 'trend': 'error', 'confidence': 0}
    
    @staticmethod
    def _predict_by_category(user):
        """Predict spending trends by category."""
        try:
            today = timezone.now().date()
            two_months_ago = today - timedelta(days=60)
            one_month_ago = today - timedelta(days=30)
            
            # Last month vs previous month
            last_month = dict(Expense.objects.filter(
                owner=user,
                date__gte=one_month_ago,
                date__lte=today
            ).values('category').annotate(total=Sum('amount')).values_list('category', 'total'))
            
            prev_month = dict(Expense.objects.filter(
                owner=user,
                date__gte=two_months_ago,
                date__lt=one_month_ago
            ).values('category').annotate(total=Sum('amount')).values_list('category', 'total'))
            
            predictions = []
            for cat, amount in last_month.items():
                prev = float(prev_month.get(cat, 0))
                if prev > 0:
                    change = ((float(amount) - prev) / prev) * 100
                    predictions.append({
                        'category': cat,
                        'current_month': round(float(amount), 2),
                        'change_percent': round(change, 1),
                        'predicted_trend': 'increasing' if change > 10 else 'decreasing' if change < -10 else 'stable'
                    })
            
            return sorted(predictions, key=lambda x: abs(x['change_percent']), reverse=True)[:5]
            
        except Exception as e:
            return []
    
    # =====================================================
    # 2. ANOMALY DETECTION
    # =====================================================
    
    @staticmethod
    def detect_anomalies(user, sensitivity=2.0):
        """
        Detect unusual transactions compared to typical spending patterns.
        Uses statistical methods (z-score) to identify anomalies.
        
        Args:
            sensitivity: Number of standard deviations for anomaly detection (default: 2.0)
        """
        try:
            today = timezone.now().date()
            start_date = today - timedelta(days=60)  # 60 days of history
            
            # Get expenses grouped by category
            expenses = Expense.objects.filter(
                owner=user,
                date__gte=start_date,
                date__lte=today
            ).values('category', 'amount')
            
            if not expenses:
                return {'has_anomalies': False, 'anomalies': []}
            
            # Group by category
            category_data = defaultdict(list)
            for exp in expenses:
                category_data[exp['category']].append(float(exp['amount']))
            
            anomalies = []
            
            for category, amounts in category_data.items():
                if len(amounts) < 5:  # Need enough data points
                    continue
                
                # Calculate mean and standard deviation
                mean = sum(amounts) / len(amounts)
                variance = sum((x - mean) ** 2 for x in amounts) / len(amounts)
                std_dev = math.sqrt(variance)
                
                if std_dev == 0:
                    continue
                
                # Get recent transactions in this category
                recent = Expense.objects.filter(
                    owner=user,
                    category=category,
                    date__gte=today - timedelta(days=7)
                ).order_by('-date', '-id')[:10]
                
                for exp in recent:
                    z_score = (float(exp.amount) - mean) / std_dev
                    
                    if abs(z_score) > sensitivity:
                        # This is an anomaly
                        multiplier = abs(z_score) / sensitivity
                        severity = 'high' if multiplier > 2 else 'medium'
                        
                        anomalies.append({
                            'id': exp.id,
                            'category': category,
                            'amount': float(exp.amount),
                            'description': exp.description,
                            'date': exp.date.strftime('%Y-%m-%d'),
                            'typical_average': round(mean, 2),
                            'multiplier': round(multiplier, 1),
                            'severity': severity,
                            'z_score': round(z_score, 2),
                            'icon': 'fa-exclamation-triangle'
                        })
            
            # Sort by severity
            anomalies.sort(key=lambda x: (
                {'high': 0, 'medium': 1, 'low': 2}.get(x['severity'], 3),
                -x['multiplier']
            ))
            
            return {
                'has_anomalies': len(anomalies) > 0,
                'anomalies': anomalies[:5],  # Top 5 anomalies
                'total_detected': len(anomalies),
                'sensitivity': sensitivity
            }
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return {'has_anomalies': False, 'anomalies': []}
    
    # =====================================================
    # 3. ENHANCED FINANCIAL HEALTH SCORE
    # =====================================================
    
    @staticmethod
    def get_enhanced_health_score(user):
        """
        Calculate enhanced financial health score with more metrics.
        """
        try:
            today = timezone.now().date()
            start_of_month = today.replace(day=1)
            
            # 1. Income to Expense Ratio (30%)
            income = UserIncome.objects.filter(
                owner=user,
                date__gte=start_of_month,
                date__lte=today
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            expenses = Expense.objects.filter(
                owner=user,
                date__gte=start_of_month,
                date__lte=today
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            if income > 0:
                savings_rate = (income - expenses) / income
                ie_score = min(100, (savings_rate / 0.2) * 100) if savings_rate >= 0 else max(0, 50 + savings_rate * 50)
            else:
                savings_rate = 0
                ie_score = 30 if expenses > 0 else 50
            
            # 2. Savings Rate (20%)
            savings_score = min(100, (savings_rate / 0.2) * 100) if savings_rate > 0 else 0
            
            # 3. Budget Stability (20%)
            budget_score = AIInsightsService._calculate_budget_stability(user, today)
            
            # 4. Debt Ratio (15%)
            debt_score = AIInsightsService._calculate_debt_score(user, income)
            
            # 5. Emergency Fund Indicator (15%)
            emergency_score = AIInsightsService._calculate_emergency_score(user, expenses)
            
            # Weighted total
            total_score = (
                ie_score * 0.30 +
                savings_score * 0.20 +
                budget_score * 0.20 +
                debt_score * 0.15 +
                emergency_score * 0.15
            )
            
            return {
                'score': round(total_score),
                'grade': AIInsightsService._get_grade(total_score),
                'breakdown': {
                    'income_expense_ratio': {'score': round(ie_score), 'weight': 30},
                    'savings_rate': {'score': round(savings_score), 'weight': 20},
                    'budget_stability': {'score': round(budget_score), 'weight': 20},
                    'debt_management': {'score': round(debt_score), 'weight': 15},
                    'emergency_fund': {'score': round(emergency_score), 'weight': 15}
                },
                'savings_rate': round(savings_rate * 100, 1) if income > 0 else 0,
                'monthly_income': round(float(income), 2),
                'monthly_expenses': round(float(expenses), 2),
                'recommendation': AIInsightsService._get_health_recommendation(total_score)
            }
            
        except Exception as e:
            logger.error(f"Error calculating enhanced health score: {e}")
            return {'score': 0, 'grade': 'N/A', 'breakdown': {}}
    
    @staticmethod
    def _calculate_budget_stability(user, today):
        """Calculate budget stability score based on spending consistency."""
        thirty_days_ago = today - timedelta(days=30)
        
        daily_spending = Expense.objects.filter(
            owner=user,
            date__gte=thirty_days_ago,
            date__lte=today
        ).values('date').annotate(total=Sum('amount'))
        
        amounts = [float(s['total']) for s in daily_spending]
        
        if len(amounts) < 7:
            return 50
        
        mean = sum(amounts) / len(amounts)
        if mean == 0:
            return 100
        
        variance = sum((x - mean) ** 2 for x in amounts) / len(amounts)
        cv = math.sqrt(variance) / mean  # Coefficient of variation
        
        # Lower CV is better
        if cv <= 0.3:
            return 100
        elif cv <= 0.5:
            return 80
        elif cv <= 0.75:
            return 60
        else:
            return 40
    
    @staticmethod
    def _calculate_debt_score(user, monthly_income):
        """Calculate debt management score."""
        try:
            debts = Debt.objects.filter(owner=user, status=Debt.STATUS_ACTIVE)
            
            if not debts:
                return 100  # No debt is excellent
            
            # Calculate total monthly debt payments
            monthly_debt = sum(float(d.emi_amount) for d in debts)
            
            if monthly_income > 0:
                debt_ratio = monthly_debt / monthly_income
                
                if debt_ratio <= 0.10:
                    return 100
                elif debt_ratio <= 0.20:
                    return 80
                elif debt_ratio <= 0.36:
                    return 60
                else:
                    return 30
            else:
                return 50
                
        except Exception:
            return 50
    
    @staticmethod
    def _calculate_emergency_score(user, monthly_expenses):
        """Calculate emergency fund score based on bank balance."""
        try:
            from bank_simulator.models import BankAccount
            account = BankAccount.objects.filter(user=user).first()
            
            if not account:
                return 30
            
            balance = float(account.balance)
            monthly = float(monthly_expenses)
            
            if monthly == 0:
                return 100
            
            months_coverage = balance / monthly
            
            if months_coverage >= 6:
                return 100
            elif months_coverage >= 3:
                return 80
            elif months_coverage >= 1:
                return 60
            else:
                return 30
                
        except Exception:
            return 30
    
    @staticmethod
    def _get_grade(score):
        """Get letter grade for score."""
        if score >= 90: return 'A+'
        elif score >= 80: return 'A'
        elif score >= 70: return 'B+'
        elif score >= 60: return 'B'
        elif score >= 50: return 'C'
        elif score >= 40: return 'D'
        else: return 'F'
    
    @staticmethod
    def _get_health_recommendation(score):
        """Get recommendation based on health score."""
        if score >= 80:
            return "Excellent! Your finances are thriving. Keep up the great work!"
        elif score >= 60:
            return "Good financial health. Focus on increasing savings rate."
        elif score >= 40:
            return "Fair. Review spending habits and reduce unnecessary expenses."
        else:
            return "Needs attention. Prioritize building emergency fund and reducing debt."
    
    # =====================================================
    # 4. CASH FLOW FORECASTING
    # =====================================================
    
    @staticmethod
    def get_cash_flow_forecast(days_ahead=30):
        """
        Predict cash flow (surplus/deficit) for upcoming period.
        """
        try:
            user = None
            # We'll pass user as parameter in actual use
            # This is a placeholder
            
            return {
                'has_data': False,
                'forecast': [],
                'surplus': 0,
                'deficit': 0
            }
            
        except Exception as e:
            logger.error(f"Error in cash flow forecast: {e}")
            return {'has_data': False, 'forecast': [], 'surplus': 0, 'deficit': 0}
    
    @staticmethod
    def get_cash_flow_for_user(user, days_ahead=30):
        """Get cash flow forecast for specific user."""
        try:
            today = timezone.now().date()
            
            # Get average monthly income
            three_months_ago = today - timedelta(days=90)
            income_total = UserIncome.objects.filter(
                owner=user,
                date__gte=three_months_ago,
                date__lte=today
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            avg_monthly_income = income_total / 3
            
            # Get average monthly expenses
            expense_total = Expense.objects.filter(
                owner=user,
                date__gte=three_months_ago,
                date__lte=today
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            avg_monthly_expenses = expense_total / 3
            
            # Calculate projected cash flow
            monthly_surplus = avg_monthly_income - avg_monthly_expenses
            daily_surplus = monthly_surplus / 30
            
            # Generate daily forecast
            forecast = []
            running_balance = 0  # Would come from bank account
            
            for day in range(1, days_ahead + 1):
                forecast_date = today + timedelta(days=day)
                
                # Add income (simplified - would need recurring income detection)
                day_income = avg_monthly_income / 30
                
                # Add expenses (simplified - would use prediction)
                day_expense = avg_monthly_expenses / 30
                
                daily_flow = day_income - day_expense
                running_balance += daily_flow
                
                forecast.append({
                    'date': forecast_date.strftime('%Y-%m-%d'),
                    'income': round(day_income, 2),
                    'expenses': round(day_expense, 2),
                    'net_flow': round(daily_flow, 2),
                    'projected_balance': round(running_balance, 2),
                    'status': 'surplus' if daily_flow > 0 else 'deficit' if daily_flow < 0 else 'balanced'
                })
            
            total_projected_surplus = sum(f['net_flow'] for f in forecast)
            
            return {
                'has_data': True,
                'forecast': forecast,
                'monthly_income': round(avg_monthly_income, 2),
                'monthly_expenses': round(avg_monthly_expenses, 2),
                'monthly_surplus': round(monthly_surplus, 2),
                'total_projected_surplus': round(total_projected_surplus, 2),
                'surplus_days': sum(1 for f in forecast if f['net_flow'] > 0),
                'deficit_days': sum(1 for f in forecast if f['net_flow'] < 0),
                'outlook': 'positive' if total_projected_surplus > 0 else 'negative' if total_projected_surplus < 0 else 'neutral'
            }
            
        except Exception as e:
            logger.error(f"Error in cash flow forecast: {e}")
            return {'has_data': False, 'forecast': [], 'surplus': 0, 'deficit': 0}
    
    # =====================================================
    # 5. SMART BUDGET SUGGESTIONS
    # =====================================================
    
    @staticmethod
    def get_budget_suggestions(user):
        """
        Generate smart budget suggestions based on historical data.
        """
        try:
            today = timezone.now().date()
            start_of_month = today.replace(day=1)
            
            # Get current month's spending by category
            category_spending = dict(Expense.objects.filter(
                owner=user,
                date__gte=start_of_month,
                date__lte=today
            ).values('category').annotate(total=Sum('amount')).values_list('category', 'total'))
            
            total_spent = sum(float(v) for v in category_spending.values())
            
            # Get historical averages (last 3 months)
            three_months_ago = today - timedelta(days=90)
            historical = Expense.objects.filter(
                owner=user,
                date__gte=three_months_ago,
                date__lt=start_of_month
            ).values('category').annotate(avg=Avg('amount'))
            
            historical_avgs = {h['category']: float(h['avg']) for h in historical}
            
            suggestions = []
            
            # Get user's expense limit if exists
            expense_limit = ExpenseLimit.objects.filter(owner=user).first()
            current_daily_limit = float(expense_limit.daily_expense_limit) if expense_limit else 0
            
            # Suggest daily limit based on average spending
            if total_spent > 0:
                days_passed = (today - start_of_month).days + 1
                avg_daily = total_spent / days_passed
                suggested_daily = avg_daily * 1.1  # 10% buffer
                
                if current_daily_limit == 0:
                    suggestions.append({
                        'type': 'new_limit',
                        'category': 'overall',
                        'current': 0,
                        'suggested': round(suggested_daily * 30, 2),
                        'suggested_daily': round(suggested_daily, 2),
                        'reason': 'Based on your current spending pattern'
                    })
                elif abs(avg_daily - current_daily_limit) > current_daily_limit * 0.2:
                    suggestions.append({
                        'type': 'adjust_limit',
                        'category': 'overall',
                        'current': current_daily_limit * 30,
                        'suggested': round(suggested_daily * 30, 2),
                        'suggested_daily': round(suggested_daily, 2),
                        'reason': 'Your spending has changed from the previous pattern'
                    })
            
            # Category-specific suggestions
            for category, spent in category_spending.items():
                hist_avg = historical_avgs.get(category, 0)
                
                if hist_avg > 0:
                    change = ((spent - hist_avg) / hist_avg) * 100
                    
                    if change > 20:
                        suggestions.append({
                            'type': 'reduce_category',
                            'category': category,
                            'current': round(spent, 2),
                            'suggested': round(hist_avg * 1.1, 2),
                            'change': round(change, 1),
                            'reason': f'{category} spending is {abs(round(change))}% higher than average'
                        })
                    elif change < -20:
                        suggestions.append({
                            'type': 'increase_category',
                            'category': category,
                            'current': round(spent, 2),
                            'suggested': round(hist_avg, 2),
                            'change': round(change, 1),
                            'reason': f'{category} spending is {abs(round(change))}% lower - room to increase'
                        })
            
            return {
                'has_suggestions': len(suggestions) > 0,
                'suggestions': suggestions[:5],
                'total_categories_analyzed': len(category_spending),
                'current_month_total': round(total_spent, 2)
            }
            
        except Exception as e:
            logger.error(f"Error in budget suggestions: {e}")
            return {'has_suggestions': False, 'suggestions': []}
    
    # =====================================================
    # 6. GOAL ACHIEVEMENT PREDICTION
    # =====================================================
    
    @staticmethod
    def get_goal_predictions(user):
        """
        Predict goal achievement based on current savings behavior.
        """
        try:
            goals = Goal.objects.filter(owner=user).exclude(status=Goal.STATUS_ARCHIVED)
            
            if not goals.exists():
                return {'has_goals': False, 'predictions': []}
            
            predictions = []
            today = timezone.now().date()
            
            for goal in goals:
                target = float(goal.amount_to_save)
                current = float(goal.current_saved_amount) if goal.current_saved_amount else 0
                remaining = target - current
                
                if remaining <= 0:
                    predictions.append({
                        'goal_id': goal.id,
                        'name': goal.name,
                        'status': 'completed',
                        'current': current,
                        'target': target,
                        'progress': 100,
                        'projected_date': None,
                        'days_remaining': 0,
                        'on_track': True
                    })
                    continue
                
                # Calculate average daily savings from last 30 days
                thirty_days_ago = today - timedelta(days=30)
                savings_in_period = current  # Simplified - would track actual additions
                
                # Use monthly income - expenses to estimate potential savings
                income = UserIncome.objects.filter(
                    owner=user,
                    date__gte=today.replace(day=1),
                    date__lte=today
                ).aggregate(total=Sum('amount'))['total'] or 0
                
                expenses = Expense.objects.filter(
                    owner=user,
                    date__gte=today.replace(day=1),
                    date__lte=today
                ).aggregate(total=Sum('amount'))['total'] or 0
                
                monthly_savings = max(0, float(income) - float(expenses))
                daily_savings_rate = monthly_savings / 30
                
                # If no savings rate data, estimate from goal timeline
                if goal.end_date:
                    days_to_end = (goal.end_date - today).days
                    required_daily = remaining / max(1, days_to_end)
                else:
                    required_daily = remaining / 90  # Default 90 days
                    days_to_end = 90
                
                # Calculate projected completion date
                if daily_savings_rate > 0:
                    days_to_complete = int(remaining / daily_savings_rate)
                    projected_date = today + timedelta(days=days_to_complete)
                else:
                    projected_date = None
                    days_to_complete = None
                
                # Determine if on track
                on_track = projected_date and (goal.end_date is None or projected_date <= goal.end_date)
                
                predictions.append({
                    'goal_id': goal.id,
                    'name': goal.name,
                    'status': goal.status,
                    'current': round(current, 2),
                    'target': round(target, 2),
                    'remaining': round(remaining, 2),
                    'progress': round(min(100, (current / target) * 100), 1),
                    'projected_date': projected_date.strftime('%Y-%m-%d') if projected_date else None,
                    'target_date': goal.end_date.strftime('%Y-%m-%d') if goal.end_date else None,
                    'days_remaining': days_to_end,
                    'required_daily': round(required_daily, 2),
                    'projected_daily': round(daily_savings_rate, 2),
                    'on_track': on_track,
                    'timeline_status': 'ahead' if on_track and projected_date else 'behind' if projected_date and goal.end_date and projected_date > goal.end_date else 'on_track'
                })
            
            return {
                'has_goals': True,
                'predictions': predictions,
                'total_goals': len(predictions),
                'on_track_count': sum(1 for p in predictions if p.get('on_track', False)),
                'at_risk_count': sum(1 for p in predictions if not p.get('on_track', True) and p.get('status') != 'COMPLETED')
            }
            
        except Exception as e:
            logger.error(f"Error in goal predictions: {e}")
            return {'has_goals': False, 'predictions': []}
    
    # =====================================================
    # 7. DEBT RISK INDICATOR
    # =====================================================
    
    @staticmethod
    def get_debt_risk_indicator(user):
        """
        Evaluate debt-to-income ratio and predict financial risks.
        """
        try:
            debts = Debt.objects.filter(owner=user, status=Debt.STATUS_ACTIVE)
            
            if not debts.exists():
                return {
                    'has_debts': False,
                    'risk_level': 'low',
                    'risk_score': 0,
                    'debts': [],
                    'recommendations': ['No active debts - excellent financial position!']
                }
            
            today = timezone.now().date()
            
            # Get monthly income
            income = UserIncome.objects.filter(
                owner=user,
                date__gte=today.replace(day=1),
                date__lte=today
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            total_debt = 0
            debt_details = []
            risk_factors = []
            
            for debt in debts:
                monthly_payment = float(debt.emi_amount)
                remaining = float(debt.remaining_balance)
                total_debt += remaining
                
                # Check if overdue
                is_overdue = debt.next_emi_date < today if debt.next_emi_date else False
                
                # Calculate debt age
                days_since_start = (today - debt.start_date).days
                
                debt_details.append({
                    'id': debt.id,
                    'name': debt.loan_name,
                    'type': debt.get_loan_type_display(),
                    'monthly_payment': round(monthly_payment, 2),
                    'remaining_balance': round(remaining, 2),
                    'interest_rate': float(debt.interest_rate),
                    'next_payment': debt.next_emi_date.strftime('%Y-%m-%d') if debt.next_emi_date else None,
                    'is_overdue': is_overdue,
                    'months_remaining': debt.emi_remaining,
                    'progress': round(debt.progress_percentage, 1)
                })
                
                # Risk factor analysis
                if is_overdue:
                    risk_factors.append(f"{debt.loan_name} has overdue payments")
                
                if float(debt.interest_rate) > 15:
                    risk_factors.append(f"{debt.loan_name} has high interest rate ({debt.interest_rate}%)")
                
                if debt.emi_remaining > 36:
                    risk_factors.append(f"{debt.loan_name} has long repayment term ({debt.emi_remaining} months)")
            
            # Calculate DTI ratio
            monthly_debt_payments = sum(float(d.emi_amount) for d in debts)
            
            if income > 0:
                dti_ratio = (monthly_debt_payments / income) * 100
            else:
                dti_ratio = 50  # Conservative estimate
            
            # Calculate risk score (0-100, higher = more risk)
            risk_score = 0
            
            # DTI contribution
            if dti_ratio > 43:
                risk_score += 50
            elif dti_ratio > 28:
                risk_score += 30
            elif dti_ratio > 15:
                risk_score += 15
            
            # Overdue contribution
            overdue_count = sum(1 for d in debt_details if d['is_overdue'])
            risk_score += overdue_count * 20
            
            # High interest contribution
            high_interest_count = sum(1 for d in debt_details if d['interest_rate'] > 15)
            risk_score += high_interest_count * 10
            
            risk_score = min(100, risk_score)
            
            # Determine risk level
            if risk_score < 20:
                risk_level = 'low'
            elif risk_score < 45:
                risk_level = 'medium'
            elif risk_score < 70:
                risk_level = 'high'
            else:
                risk_level = 'critical'
            
            # Generate recommendations
            recommendations = []
            
            if dti_ratio > 43:
                recommendations.append("Your debt-to-income ratio is high. Consider debt consolidation or increasing income.")
            elif dti_ratio > 28:
                recommendations.append("Moderate DTI ratio. Focus on paying off high-interest debts first.")
            else:
                recommendations.append("Your debt level is manageable. Keep up the good payments!")
            
            if overdue_count > 0:
                recommendations.append("Address overdue payments immediately to avoid penalties.")
            
            high_interest = [d for d in debt_details if d['interest_rate'] > 15]
            if high_interest:
                recommendations.append(f"Consider refinancing {len(high_interest)} high-interest debt(s).")
            
            return {
                'has_debts': True,
                'risk_level': risk_level,
                'risk_score': risk_score,
                'dti_ratio': round(dti_ratio, 1),
                'total_debt': round(total_debt, 2),
                'monthly_debt_payment': round(monthly_debt_payments, 2),
                'monthly_income': round(float(income), 2),
                'debts': debt_details,
                'risk_factors': risk_factors,
                'recommendations': recommendations[:3]
            }
            
        except Exception as e:
            logger.error(f"Error in debt risk indicator: {e}")
            return {'has_debts': False, 'risk_level': 'unknown', 'risk_score': 0}
    
    # =====================================================
    # 8. MERCHANT INTELLIGENCE
    # =====================================================
    
    @staticmethod
    def get_merchant_intelligence(user):
        """
        Analyze frequently used merchants and spending patterns.
        """
        try:
            today = timezone.now().date()
            thirty_days_ago = today - timedelta(days=30)
            
            # Get expenses with descriptions (merchant names)
            expenses = Expense.objects.filter(
                owner=user,
                date__gte=thirty_days_ago,
                date__lte=today
            )
            
            # Extract potential merchant names from descriptions
            merchant_data = defaultdict(lambda: {'count': 0, 'total': 0, 'dates': []})
            
            for exp in expenses:
                desc = exp.description.lower().strip() if exp.description else ''
                if desc:
                    merchant_data[desc]['count'] += 1
                    merchant_data[desc]['total'] += float(exp.amount)
                    merchant_data[desc]['dates'].append(exp.date)
            
            # Also check card transactions for merchant names
            card_transactions = CardTransaction.objects.filter(
                user=user,
                transaction_date__gte=thirty_days_ago,
                transaction_date__lte=today
            )
            
            for trans in card_transactions:
                if trans.merchant_name:
                    merchant_data[trans.merchant_name]['count'] += 1
                    merchant_data[trans.merchant_name]['total'] += float(trans.amount)
                    merchant_data[trans.merchant_name]['dates'].append(trans.transaction_date)
            
            # Sort by total spending
            merchants = []
            for name, data in merchant_data.items():
                if data['count'] >= 2:  # At least 2 transactions
                    merchants.append({
                        'name': name.title() if name else 'Unknown',
                        'transaction_count': data['count'],
                        'total_spent': round(data['total'], 2),
                        'average_transaction': round(data['total'] / data['count'], 2),
                        'frequency': 'regular' if data['count'] >= 4 else 'occasional'
                    })
            
            merchants.sort(key=lambda x: x['total_spent'], reverse=True)
            
            # Top merchants
            top_merchants = merchants[:5]
            
            # Find potential savings opportunities
            opportunities = []
            for m in top_merchants:
                if m['transaction_count'] >= 3:
                    # Check if there's a cheaper alternative suggestion
                    opportunities.append({
                        'merchant': m['name'],
                        'current_monthly': round(m['total_spent'], 2),
                        'suggestion': f"Consider limiting {m['name']} purchases to save {round(m['total_spent'] * 0.2, 2)}/month",
                        'potential_savings': round(m['total_spent'] * 0.2, 2)
                    })
            
            return {
                'has_merchants': len(merchants) > 0,
                'top_merchants': top_merchants,
                'total_merchants': len(merchants),
                'opportunities': opportunities[:3],
                'analysis_period': '30 days'
            }
            
        except Exception as e:
            logger.error(f"Error in merchant intelligence: {e}")
            return {'has_merchants': False, 'top_merchants': []}
    
    # =====================================================
    # 9. SUBSCRIPTION DETECTION
    # =====================================================
    
    @staticmethod
    def detect_subscriptions(user):
        """
        Detect recurring subscriptions from transaction patterns.
        """
        try:
            today = timezone.now().date()
            ninety_days_ago = today - timedelta(days=90)
            
            # Get all expenses in the period
            expenses = Expense.objects.filter(
                owner=user,
                date__gte=ninety_days_ago,
                date__lte=today
            ).order_by('description', 'date')
            
            # Group by description to find patterns
            description_dates = defaultdict(list)
            
            for exp in expenses:
                if exp.description:
                    desc = exp.description.lower().strip()
                    description_dates[desc].append({
                        'date': exp.date,
                        'amount': float(exp.amount)
                    })
            
            # Also check card transactions
            card_trans = CardTransaction.objects.filter(
                user=user,
                transaction_date__gte=ninety_days_ago,
                transaction_date__lte=today
            )
            
            for trans in card_trans:
                if trans.description:
                    desc = trans.description.lower().strip()
                    description_dates[desc].append({
                        'date': trans.transaction_date,
                        'amount': float(trans.amount)
                    })
            
            # Find recurring transactions
            subscriptions = []
            
            for desc, transactions in description_dates.items():
                if len(transactions) < 2:
                    continue
                
                # Sort by date
                transactions.sort(key=lambda x: x['date'])
                
                # Check for regular intervals
                dates = [t['date'] for t in transactions]
                amounts = [t['amount'] for t in transactions]
                
                # Calculate average interval
                intervals = []
                for i in range(1, len(dates)):
                    interval = (dates[i] - dates[i-1]).days
                    intervals.append(interval)
                
                if intervals:
                    avg_interval = sum(intervals) / len(intervals)
                    
                    # Check if it matches subscription patterns (roughly monthly)
                    if 25 <= avg_interval <= 35:  # Monthly
                        frequency = 'monthly'
                    elif 85 <= avg_interval <= 95:  # Quarterly
                        frequency = 'quarterly'
                    elif 175 <= avg_interval <= 185:  # Semi-annual
                        frequency = 'semi-annual'
                    elif 350 <= avg_interval <= 370:  # Annual
                        frequency = 'annual'
                    else:
                        continue  # Not a clear subscription pattern
                    
                    # Check if amounts are consistent (within 10%)
                    if amounts:
                        avg_amount = sum(amounts) / len(amounts)
                        amount_variation = max(amounts) - min(amounts)
                        
                        if amount_variation < avg_amount * 0.2:  # Within 20%
                            # Try to identify the service
                            service_name = AIInsightsService._identify_subscription(desc)
                            
                            subscriptions.append({
                                'name': service_name or desc.title(),
                                'original_description': desc,
                                'amount': round(avg_amount, 2),
                                'frequency': frequency,
                                'times_detected': len(transactions),
                                'last_date': max(dates).strftime('%Y-%m-%d'),
                                'annual_cost': round(avg_amount * 12, 2) if frequency == 'monthly' else avg_amount * 4 if frequency == 'quarterly' else avg_amount * 2 if frequency == 'semi-annual' else avg_amount,
                                'category': AIInsightsService._categorize_subscription(desc)
                            })
            
            # Sort by annual cost
            subscriptions.sort(key=lambda x: x['annual_cost'], reverse=True)
            
            total_monthly = sum(s['amount'] for s in subscriptions if s['frequency'] == 'monthly')
            total_annual = sum(s['annual_cost'] for s in subscriptions)
            
            return {
                'has_subscriptions': len(subscriptions) > 0,
                'subscriptions': subscriptions[:8],  # Top 8
                'total_detected': len(subscriptions),
                'monthly_total': round(total_monthly, 2),
                'annual_total': round(total_annual, 2),
                'opportunity_to_save': round(total_annual * 0.1, 2) if subscriptions else 0
            }
            
        except Exception as e:
            logger.error(f"Error detecting subscriptions: {e}")
            return {'has_subscriptions': False, 'subscriptions': []}
    
    @staticmethod
    def _identify_subscription(description):
        """Identify subscription service from description."""
        desc = description.lower()
        
        # Common subscription services
        services = {
            'netflix': 'Netflix',
            'spotify': 'Spotify',
            'amazon prime': 'Amazon Prime',
            'apple': 'Apple',
            'hulu': 'Hulu',
            'disney': 'Disney+',
            'hbo': 'HBO Max',
            'youtube': 'YouTube Premium',
            'gym': 'Gym Membership',
            'planet': 'Planet Fitness',
            'adobe': 'Adobe',
            'microsoft': 'Microsoft 365',
            'dropbox': 'Dropbox',
            'linkedin': 'LinkedIn Premium',
            'github': 'GitHub',
        }
        
        for keyword, name in services.items():
            if keyword in desc:
                return name
        
        return None
    
    @staticmethod
    def _categorize_subscription(description):
        """Categorize subscription type."""
        desc = description.lower()
        
        if any(x in desc for x in ['netflix', 'hulu', 'disney', 'hbo', 'youtube', 'spotify', 'apple', 'movie']):
            return 'entertainment'
        elif any(x in desc for x in ['gym', 'fitness', 'planet']):
            return 'fitness'
        elif any(x in desc for x in ['cloud', 'dropbox', 'google', 'adobe', 'microsoft', 'github']):
            return 'software'
        elif any(x in desc for x in ['insurance', 'phone', 'mobile', 'internet', 'electric', 'water', 'gas']):
            return 'utilities'
        else:
            return 'other'
    
    # =====================================================
    # 10. SPENDING EFFICIENCY INSIGHTS
    # =====================================================
    
    @staticmethod
    def get_efficiency_insights(user):
        """
        Provide recommendations to improve financial efficiency.
        """
        try:
            today = timezone.now().date()
            thirty_days_ago = today - timedelta(days=30)
            sixty_days_ago = today - timedelta(days=60)
            
            insights = []
            
            # 1. Check for unnecessary expenses
            small_transactions = Expense.objects.filter(
                owner=user,
                date__gte=thirty_days_ago,
                amount__lt=10
            ).count()
            
            if small_transactions >= 10:
                monthly_small_total = Expense.objects.filter(
                    owner=user,
                    date__gte=thirty_days_ago,
                    amount__lt=10
                ).aggregate(total=Sum('amount'))['total'] or 0
                
                insights.append({
                    'type': 'unnecessary_expenses',
                    'icon': 'fa-coffee',
                    'title': 'Small Transactions Adding Up',
                    'description': f'You have {small_transactions} small purchases this month totaling {round(float(monthly_small_total), 2)}. Consider reducing these impulse purchases.',
                    'potential_savings': round(float(monthly_small_total) * 0.3, 2),
                    'action': 'Reduce small purchases by 30%'
                })
            
            # 2. Check for high category spending
            category_spending = dict(Expense.objects.filter(
                owner=user,
                date__gte=thirty_days_ago
            ).values('category').annotate(total=Sum('amount')).values_list('category', 'total'))
            
            total_spending = sum(float(v) for v in category_spending.values())
            
            if total_spending > 0:
                # Check each category
                for category, amount in category_spending.items():
                    percentage = (float(amount) / total_spending) * 100
                    
                    if percentage > 40 and category.lower() in ['food', 'shopping', 'entertainment']:
                        insights.append({
                            'type': 'high_category',
                            'icon': 'fa-chart-pie',
                            'title': f'High {category} Spending',
                            'description': f'{category} accounts for {round(percentage, 1)}% of your total spending. Look for ways to reduce.',
                            'potential_savings': round(float(amount) * 0.15, 2),
                            'action': f'Reduce {category} spending by 15%'
                        })
            
            # 3. Check savings rate
            income = UserIncome.objects.filter(
                owner=user,
                date__gte=thirty_days_ago
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            expenses = Expense.objects.filter(
                owner=user,
                date__gte=thirty_days_ago
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            if income > 0:
                savings_rate = ((income - expenses) / income) * 100
                
                if savings_rate < 10:
                    insights.append({
                        'type': 'low_savings',
                        'icon': 'fa-piggy-bank',
                        'title': 'Low Savings Rate',
                        'description': f'Your savings rate is only {round(savings_rate, 1)}%. Financial experts recommend at least 20%.',
                        'potential_savings': round((income * 0.20 - (income - expenses)), 2),
                        'action': 'Increase savings rate to 20%'
                    })
            
            # 4. Check for duplicate subscriptions
            # (reuse subscription detection logic)
            subs_data = AIInsightsService.detect_subscriptions(user)
            
            if subs_data.get('has_subscriptions') and subs_data.get('monthly_total', 0) > 50:
                insights.append({
                    'type': 'subscription_costs',
                    'icon': 'fa-redo',
                    'title': 'Subscription Costs',
                    'description': f'You have {len(subs_data["subscriptions"])} subscriptions costing {round(subs_data["monthly_total"], 2)}/month. Review for unused services.',
                    'potential_savings': subs_data.get('opportunity_to_save', 0),
                    'action': 'Cancel unused subscriptions'
                })
            
            # 5. Check budget adherence
            expense_limit = ExpenseLimit.objects.filter(owner=user).first()
            if expense_limit and expense_limit.daily_expense_limit:
                daily_limit = float(expense_limit.daily_expense_limit)
                days_passed = (today - today.replace(day=1)).days + 1
                expected_spending = daily_limit * days_passed
                
                if float(expenses) > expected_spending * 1.2:
                    insights.append({
                        'type': 'budget_overrun',
                        'icon': 'fa-exclamation-triangle',
                        'title': 'Budget Overrun',
                        'description': "You've exceeded your monthly budget. Review your spending to get back on track.",
                        'potential_savings': round(float(expenses) - expected_spending, 2),
                        'action': 'Reduce spending to stay within budget'
                    })
            
            # Sort by potential savings
            insights.sort(key=lambda x: x.get('potential_savings', 0), reverse=True)
            
            return {
                'has_insights': len(insights) > 0,
                'insights': insights[:4],  # Top 4 insights
                'total_potential_savings': round(sum(i.get('potential_savings', 0) for i in insights), 2),
                'analysis_period': '30 days'
            }
            
        except Exception as e:
            logger.error(f"Error in efficiency insights: {e}")
            return {'has_insights': False, 'insights': []}
    
    # =====================================================
    # HELPER METHODS
    # =====================================================
    
    @staticmethod
    def _empty_insights():
        """Return empty insights structure."""
        return {
            'spending_trend_prediction': {'has_data': False},
            'anomaly_detection': {'has_anomalies': False},
            'financial_health': {'score': 0},
            'cash_flow_forecast': {'has_data': False},
            'budget_suggestions': {'has_suggestions': False},
            'goal_predictions': {'has_goals': False},
            'debt_risk': {'has_debts': False},
            'merchant_intelligence': {'has_merchants': False},
            'subscriptions': {'has_subscriptions': False},
            'efficiency_insights': {'has_insights': False}
        }
    
    @staticmethod
    def invalidate_cache(user_id):
        """Invalidate all cached insights for a user."""
        cache.delete(AIInsightsService._get_cache_key(user_id, 'all_insights'))

