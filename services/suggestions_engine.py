"""
Financial Suggestions Engine
===========================
An intelligent financial advisor system that analyzes user data and provides
personalized recommendations to help users become debt-free and achieve their goals.

Uses real-time database aggregations for all calculations.
"""

from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import ExtractMonth, ExtractYear
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta, date
from typing import Dict, List, Optional
import math

from expenses.models import Expense
from userincome.models import UserIncome
from debts.models import Debt
from goals.models import Goal
from bank_simulator.models import BankTransaction, CardTransaction


class SuggestionsEngine:
    """
    Intelligent Financial Suggestions Engine
    Provides debt payoff predictions, goal completion forecasts, and smart budget allocation.
    """
    
    # ==================== INCOME & EXPENSES ====================
    
    @staticmethod
    def calculate_monthly_income(user, year=None, month=None) -> float:
        """
        Calculate total income for a specific month using Django ORM.
        
        Args:
            user: The user object
            year: Optional year (defaults to current year)
            month: Optional month (defaults to current month)
            
        Returns:
            Total monthly income as float
        """
        if year is None:
            year = timezone.now().year
        if month is None:
            month = timezone.now().month
        
        # Include recurring income projected for the month
        total = UserIncome.objects.filter(
            owner=user,
            date__year=year,
            date__month=month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Also add projected recurring income (salary, etc.)
        recurring_income = UserIncome.objects.filter(
            owner=user,
            is_recurring=True
        ).values('source').annotate(avg_amount=Avg('amount'))
        
        # For monthly recurring, add the average if no income recorded yet
        for item in recurring_income:
            if item['avg_amount']:
                # Check if this source has income this month
                has_income = UserIncome.objects.filter(
                    owner=user,
                    source=item['source'],
                    date__year=year,
                    date__month=month
                ).exists()
                
                if not has_income:
                    total += item['avg_amount']
        
        return float(total)
    
    @staticmethod
    def calculate_monthly_expenses(user, year=None, month=None) -> float:
        """
        Calculate total expenses for a specific month using Django ORM.
        
        Args:
            user: The user object
            year: Optional year (defaults to current year)
            month: Optional month (defaults to current month)
            
        Returns:
            Total monthly expenses as float
        """
        if year is None:
            year = timezone.now().year
        if month is None:
            month = timezone.now().month
        
        total = Expense.objects.filter(
            owner=user,
            date__year=year,
            date__month=month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Also include card spending for the month
        card_spending = CardTransaction.objects.filter(
            user=user,
            transaction_date__year=year,
            transaction_date__month=month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return float(total) + float(card_spending)
    
    @staticmethod
    def calculate_remaining_budget(user, year=None, month=None) -> Dict:
        """
        Calculate the true remaining monthly budget.
        
        Formula: Remaining Budget = Total Monthly Income − Total Monthly Expenses
        
        Args:
            user: The user object
            year: Optional year
            month: Optional month
            
        Returns:
            Dict with income, expenses, and remaining budget
        """
        monthly_income = SuggestionsEngine.calculate_monthly_income(user, year, month)
        monthly_expenses = SuggestionsEngine.calculate_monthly_expenses(user, year, month)
        remaining = monthly_income - monthly_expenses
        
        return {
            'monthly_income': monthly_income,
            'monthly_expenses': monthly_expenses,
            'remaining_budget': max(0, remaining),  # Don't show negative
            'is_deficit': remaining < 0,
            'deficit_amount': abs(remaining) if remaining < 0 else 0
        }
    
    # ==================== DEBT ANALYSIS ====================
    
    @staticmethod
    def get_active_debts(user) -> List[Dict]:
        """
        Get all active debts with detailed information.
        
        Args:
            user: The user object
            
        Returns:
            List of debt dictionaries with all relevant info
        """
        debts = Debt.objects.filter(
            owner=user,
            status=Debt.STATUS_ACTIVE
        )  # Fetch first, then sort by calculated property
        
        debt_list = []
        for debt in debts:
            remaining_balance = float(debt.remaining_balance)
            emi_amount = float(debt.emi_amount)
            interest_rate = float(debt.interest_rate)
            
            # Calculate months remaining at current payment rate
            months_remaining = 0
            if emi_amount > 0 and remaining_balance > 0:
                # Simple calculation - doesn't account for interest precisely
                monthly_rate = interest_rate / 100 / 12
                if monthly_rate > 0:
                    # EMI formula: n = -log(1 - P*r/EMI) / log(1+r)
                    try:
                        months_remaining = -math.log(1 - (remaining_balance * monthly_rate) / emi_amount) / math.log(1 + monthly_rate)
                        months_remaining = max(1, math.ceil(months_remaining))
                    except:
                        months_remaining = int(remaining_balance / emi_amount)
                else:
                    months_remaining = int(remaining_balance / emi_amount)
            
            # Calculate total interest remaining
            total_payments = emi_amount * months_remaining
            total_interest = max(0, total_payments - remaining_balance)
            
            debt_list.append({
                'id': debt.id,
                'name': debt.loan_name,
                'type': debt.get_loan_type_display(),
                'remaining_balance': remaining_balance,
                'emi_amount': emi_amount,
                'interest_rate': interest_rate,
                'months_remaining': months_remaining,
                'total_interest_remaining': total_interest,
                'next_emi_date': debt.next_emi_date,
                'lender_name': debt.lender_name
            })
        
        # Sort by remaining balance (in Python, not in DB)
        debt_list.sort(key=lambda x: x['remaining_balance'])
        
        return debt_list
    
    @staticmethod
    def predict_debt_payoff(debt_info: Dict, extra_payment: float = 0) -> Dict:
        """
        Predict debt payoff date with optional extra payment.
        
        Args:
            debt_info: Debt dictionary from get_active_debts
            extra_payment: Additional monthly payment amount
            
        Returns:
            Dict with payoff prediction details
        """
        remaining_balance = debt_info['remaining_balance']
        current_emi = debt_info['emi_amount']
        interest_rate = debt_info['interest_rate']
        
        total_monthly_payment = current_emi + extra_payment
        
        if total_monthly_payment <= 0 or remaining_balance <= 0:
            return {
                'payoff_months': 999,
                'payoff_date': None,
                'total_interest': 0,
                'total_cost': remaining_balance,
                'months_saved': 0,
                'interest_saved': 0
            }
        
        monthly_rate = interest_rate / 100 / 12
        
        # Calculate months to payoff with extra payment
        months_with_extra = 0
        balance = remaining_balance
        
        while balance > 0 and months_with_extra < 600:  # Max 50 years
            interest = balance * monthly_rate
            principal = total_monthly_payment - interest
            
            if principal >= balance:
                months_with_extra += 1
                break
            
            balance -= principal
            months_with_extra += 1
        
        # Calculate months to payoff without extra payment
        months_current = 0
        balance = remaining_balance
        
        while balance > 0 and months_current < 600:
            interest = balance * monthly_rate
            principal = current_emi - interest
            
            if principal >= balance:
                months_current += 1
                break
            
            balance -= principal
            months_current += 1
        
        # Calculate totals
        total_cost_with_extra = total_monthly_payment * months_with_extra
        total_cost_current = current_emi * months_current
        
        months_saved = months_current - months_with_extra
        interest_saved = total_cost_current - total_cost_with_extra - remaining_balance
        
        # Calculate payoff date
        today = timezone.now().date()
        payoff_date = date(today.year, today.month, 1) + timedelta(days=months_with_extra * 30)
        
        return {
            'payoff_months': months_with_extra,
            'payoff_date': payoff_date.strftime('%B %Y'),
            'payoff_date_obj': payoff_date,
            'total_interest': max(0, total_cost_with_extra - remaining_balance),
            'total_cost': total_cost_with_extra,
            'months_saved': max(0, months_saved),
            'interest_saved': max(0, interest_saved),
            'suggested_extra_payment': extra_payment,
            'new_monthly_payment': total_monthly_payment
        }
    
    # ==================== GOAL ANALYSIS ====================
    
    @staticmethod
    def get_active_goals(user) -> List[Dict]:
        """
        Get all active goals with detailed information.
        
        Args:
            user: The user object
            
        Returns:
            List of goal dictionaries
        """
        goals = Goal.objects.filter(
            owner=user,
            status__in=[Goal.STATUS_ACTIVE, Goal.STATUS_OVERDUE]
        ).order_by('end_date')
        
        goal_list = []
        for goal in goals:
            amount_to_save = float(goal.amount_to_save)
            current_saved = float(goal.current_saved_amount)
            remaining_amount = max(0, amount_to_save - current_saved)
            days_remaining = goal.days_remaining
            
            # Calculate required daily savings
            daily_required = remaining_amount / days_remaining if days_remaining > 0 else remaining_amount
            monthly_required = daily_required * 30
            
            goal_list.append({
                'id': goal.id,
                'name': goal.name,
                'target_amount': amount_to_save,
                'current_saved': current_saved,
                'remaining_amount': remaining_amount,
                'saved_percentage': goal.saved_percentage,
                'days_remaining': days_remaining,
                'monthly_required': monthly_required,
                'end_date': goal.end_date,
                'status': goal.status
            })
        
        return goal_list
    
    @staticmethod
    def predict_goal_completion(goal_info: Dict, monthly_saving: float) -> Dict:
        """
        Predict goal completion date based on monthly saving amount.
        
        Args:
            goal_info: Goal dictionary from get_active_goals
            monthly_saving: Monthly savings amount
            
        Returns:
            Dict with completion prediction
        """
        remaining_amount = goal_info['remaining_amount']
        
        if monthly_saving <= 0 or remaining_amount <= 0:
            return {
                'months_to_complete': 999,
                'completion_date': None,
                'is_on_track': False,
                'shortfall': remaining_amount
            }
        
        months_to_complete = math.ceil(remaining_amount / monthly_saving)
        
        # Calculate completion date
        today = timezone.now().date()
        completion_date = date(today.year, today.month, 1) + timedelta(days=months_to_complete * 30)
        
        # Check if on track
        target_date = goal_info['end_date']
        is_on_track = completion_date <= target_date
        
        return {
            'months_to_complete': months_to_complete,
            'completion_date': completion_date.strftime('%B %Y'),
            'completion_date_obj': completion_date,
            'is_on_track': is_on_track,
            'monthly_saving_required': monthly_saving,
            'months_ahead_or_behind': 0 if is_on_track else (months_to_complete * 30 - (target_date - today).days) // 30
        }
    
    # ==================== DEBT STRATEGIES ====================
    
    @staticmethod
    def calculate_snowball_strategy(debts: List[Dict]) -> Dict:
        """
        Debt Snowball Method: Pay smallest debts first.
        
        Args:
            debts: List of debt dictionaries
            
        Returns:
            Dict with payoff timeline and order
        """
        if not debts:
            return {'total_months': 0, 'total_interest': 0, 'order': [], 'debt_free_date': None}
        
        # Sort by remaining balance (smallest first)
        sorted_debts = sorted(debts, key=lambda x: x['remaining_balance'])
        
        total_interest = 0
        month = 0
        balances = [d['remaining_balance'] for d in sorted_debts]
        rates = [d['interest_rate'] / 100 / 12 for d in sorted_debts]
        emis = [d['emi_amount'] for d in sorted_debts]
        
        while any(b > 0 for b in balances) and month < 600:
            month += 1
            extra_payment = 0
            
            # Apply minimum payment to all debts
            for i in range(len(sorted_debts)):
                if balances[i] > 0:
                    interest = balances[i] * rates[i]
                    total_interest += interest
                    
                    payment = emis[i]
                    if i == 0:  # Add extra to smallest debt
                        # Find freed up money from paid off debts
                        for j in range(1, len(sorted_debts)):
                            if balances[j] <= 0:
                                extra_payment += emis[j]
                    
                    principal = payment - interest
                    balances[i] = max(0, balances[i] - principal)
        
        today = timezone.now().date()
        debt_free_date = date(today.year, today.month, 1) + timedelta(days=month * 30)
        
        return {
            'strategy': 'snowball',
            'total_months': month,
            'total_interest': total_interest,
            'order': [d['name'] for d in sorted_debts],
            'debt_free_date': debt_free_date.strftime('%B %Y'),
            'debt_free_date_obj': debt_free_date
        }
    
    @staticmethod
    def calculate_avalanche_strategy(debts: List[Dict]) -> Dict:
        """
        Debt Avalanche Method: Pay highest interest debts first.
        
        Args:
            debts: List of debt dictionaries
            
        Returns:
            Dict with payoff timeline and order
        """
        if not debts:
            return {'total_months': 0, 'total_interest': 0, 'order': [], 'debt_free_date': None}
        
        # Sort by interest rate (highest first)
        sorted_debts = sorted(debts, key=lambda x: x['interest_rate'], reverse=True)
        
        total_interest = 0
        month = 0
        balances = [d['remaining_balance'] for d in sorted_debts]
        rates = [d['interest_rate'] / 100 / 12 for d in sorted_debts]
        emis = [d['emi_amount'] for d in sorted_debts]
        
        while any(b > 0 for b in balances) and month < 600:
            month += 1
            extra_payment = 0
            
            for i in range(len(sorted_debts)):
                if balances[i] > 0:
                    interest = balances[i] * rates[i]
                    total_interest += interest
                    
                    payment = emis[i]
                    if i == 0:  # Add extra to highest interest debt
                        for j in range(1, len(sorted_debts)):
                            if balances[j] <= 0:
                                extra_payment += emis[j]
                    
                    principal = payment - interest
                    balances[i] = max(0, balances[i] - principal)
        
        today = timezone.now().date()
        debt_free_date = date(today.year, today.month, 1) + timedelta(days=month * 30)
        
        return {
            'strategy': 'avalanche',
            'total_months': month,
            'total_interest': total_interest,
            'order': [d['name'] for d in sorted_debts],
            'debt_free_date': debt_free_date.strftime('%B %Y'),
            'debt_free_date_obj': debt_free_date
        }
    
    @staticmethod
    def compare_debt_strategies(debts: List[Dict], available_extra: float) -> Dict:
        """
        Compare Snowball vs Avalanche strategies.
        
        Args:
            debts: List of debt dictionaries
            available_extra: Extra amount available for debt payments
            
        Returns:
            Dict comparing both strategies
        """
        snowball = SuggestionsEngine.calculate_snowball_strategy(debts)
        avalanche = SuggestionsEngine.calculate_avalanche_strategy(debts)
        
        interest_diff = snowball['total_interest'] - avalanche['total_interest']
        
        # Avalanche usually saves more money but snowball is faster psychologically
        recommended = 'avalanche' if interest_diff > 0 else 'snowball'
        
        return {
            'snowball': snowball,
            'avalanche': avalanche,
            'savings_with_avalanche': abs(interest_diff),
            'recommended_strategy': recommended,
            'reason': (
                f"The Avalanche method saves you ₹{abs(interest_diff):,.0f} in interest "
                f"by prioritizing high-interest debts."
            ) if interest_diff > 0 else (
                "Both methods will cost you the same total interest."
            )
        }
    
    # ==================== SMART ALLOCATION ====================
    
    @staticmethod
    def generate_smart_allocation(remaining_budget: float, debts: List[Dict], goals: List[Dict]) -> Dict:
        """
        Generate smart budget allocation between debts and goals.
        
        Uses a weighted priority system:
        - Debts get priority (70%) due to interest costs
        - Goals get (30%) for savings momentum
        
        Args:
            remaining_budget: Available monthly budget
            debts: List of active debts
            goals: List of active goals
            
        Returns:
            Dict with allocation recommendations
        """
        if remaining_budget <= 0:
            return {
                'total_budget': remaining_budget,
                'debt_allocation': 0,
                'goal_allocation': 0,
                'is_deficit': True,
                'message': 'Your expenses exceed your income. Consider reducing expenses.'
            }
        
        # Calculate minimum debt payments required
        total_min_debt = sum(d['emi_amount'] for d in debts)
        
        # Calculate minimum goal contributions
        total_min_goals = sum(g['monthly_required'] for g in goals if g['monthly_required'] > 0)
        
        # If we can't cover minimums, prioritize debts
        if total_min_debt + total_min_goals > remaining_budget:
            # First priority: minimum debt payments
            debt_allocation = min(total_min_debt, remaining_budget)
            goal_allocation = max(0, remaining_budget - debt_allocation)
            
            return {
                'total_budget': remaining_budget,
                'debt_allocation': debt_allocation,
                'goal_allocation': goal_allocation,
                'is_deficit': False,
                'message': 'Budget covers minimum debt payments only. Goals may need to wait.',
                'details': {
                    'minimum_debt_required': total_min_debt,
                    'minimum_goals_required': total_min_goals,
                    'shortfall': max(0, total_min_debt + total_min_goals - remaining_budget)
                }
            }
        
        # Normal allocation: 70% debts, 30% goals (adjusted by what's needed)
        # First allocate minimums, then distribute extra
        debt_allocation = total_min_debt
        goal_allocation = total_min_goals
        extra = remaining_budget - (total_min_debt + total_min_goals)
        
        # Distribute extra based on priority
        if debts and extra > 0:
            # Extra goes primarily to debts (avalanche method)
            debt_allocation += extra * 0.7
        
        if goals and extra > 0:
            goal_allocation += extra * 0.3
        
        # Calculate per-debt allocation
        debt_breakdown = []
        for debt in debts:
            proportion = debt['emi_amount'] / total_min_debt if total_min_debt > 0 else 0
            debt_breakdown.append({
                'name': debt['name'],
                'allocated': debt_allocation * proportion,
                'current_emi': debt['emi_amount'],
                'can_increase': debt_allocation * proportion > debt['emi_amount']
            })
        
        # Calculate per-goal allocation
        goal_breakdown = []
        for goal in goals:
            proportion = goal['monthly_required'] / total_min_goals if total_min_goals > 0 else 0
            goal_breakdown.append({
                'name': goal['name'],
                'allocated': goal_allocation * proportion,
                'required': goal['monthly_required'],
                'on_track': (goal_allocation * proportion) >= goal['monthly_required']
            })
        
        return {
            'total_budget': remaining_budget,
            'debt_allocation': debt_allocation,
            'goal_allocation': goal_allocation,
            'is_deficit': False,
            'message': 'Smart allocation applied based on debt priority and goal targets.',
            'debt_breakdown': debt_breakdown,
            'goal_breakdown': goal_breakdown,
            'debt_percentage': (debt_allocation / remaining_budget * 100) if remaining_budget > 0 else 0,
            'goal_percentage': (goal_allocation / remaining_budget * 100) if remaining_budget > 0 else 0
        }
    
    # ==================== FINANCIAL GUIDANCE ====================
    
    @staticmethod
    def generate_financial_guidance(user) -> List[Dict]:
        """
        Generate AI-style financial guidance suggestions.
        
        Analyzes spending patterns, debt situation, and goals to provide
        personalized recommendations.
        
        Args:
            user: The user object
            
        Returns:
            List of guidance dictionaries with suggestions
        """
        suggestions = []
        
        # Get current data
        budget = SuggestionsEngine.calculate_remaining_budget(user)
        debts = SuggestionsEngine.get_active_debts(user)
        goals = SuggestionsEngine.get_active_goals(user)
        
        # Calculate last month vs this month comparison
        today = timezone.now().date()
        this_month = (today.year, today.month)
        last_month = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
        
        this_month_expenses = SuggestionsEngine.calculate_monthly_expenses(user, this_month[0], this_month[1])
        last_month_expenses = SuggestionsEngine.calculate_monthly_expenses(user, last_month[0], last_month[1])
        
        # Suggestion 1: Expense trend
        if last_month_expenses > 0:
            expense_change = ((this_month_expenses - last_month_expenses) / last_month_expenses) * 100
            
            if expense_change > 10:
                suggestions.append({
                    'type': 'warning',
                    'icon': '⚠️',
                    'title': 'Spending Increase Detected',
                    'message': f'You are spending {expense_change:.0f}% more this month compared to last month. '
                              f'Consider reviewing your expenses to stay on track.',
                    'action': 'Review Expenses',
                    'action_url': '/dashboard/'
                })
            elif expense_change < -10:
                suggestions.append({
                    'type': 'success',
                    'icon': '🎉',
                    'title': 'Great Job!',
                    'message': f'You spent {abs(expense_change):.0f}% less this month compared to last month. '
                              f'Keep up the good financial habits!',
                    'action': None,
                    'action_url': None
                })
        
        # Suggestion 2: Debt payment acceleration
        if debts:
            # Find the debt with highest interest
            highest_interest_debt = max(debts, key=lambda x: x['interest_rate'])
            
            # Calculate impact of extra payment
            extra_payment_impact = SuggestionsEngine.predict_debt_payoff(
                highest_interest_debt, 
                extra_payment=2000
            )
            
            if extra_payment_impact['months_saved'] > 0:
                suggestions.append({
                    'type': 'tip',
                    'icon': '💡',
                    'title': 'Accelerate Debt Payoff',
                    'message': f'Pay ₹2,000 extra monthly toward "{highest_interest_debt["name"]}" '
                              f'and become debt-free {extra_payment_impact["months_saved"]} months earlier!',
                    'action': 'View Debts',
                    'action_url': '/debts/',
                    'savings': extra_payment_impact['interest_saved']
                })
            
            # Suggestion: Debt-free date
            if debts:
                total_debt = sum(d['remaining_balance'] for d in debts)
                total_emi = sum(d['emi_amount'] for d in debts)
                avg_months = total_debt / total_emi if total_emi > 0 else 0
                debt_free_date = date(today.year, today.month, 1) + timedelta(days=int(avg_months) * 30)
                
                suggestions.append({
                    'type': 'info',
                    'icon': '📅',
                    'title': 'Debt-Free Projection',
                    'message': f'At your current payment rate, you will become debt-free by {debt_free_date.strftime("%B %Y")}.',
                    'action': None,
                    'action_url': None
                })
        
        # Suggestion 3: Goal progress
        if goals:
            for goal in goals:
                if goal['remaining_amount'] > 0:
                    # Calculate required monthly saving
                    required = goal['remaining_amount'] / max(1, goal['days_remaining']) * 30
                    
                    if budget['remaining_budget'] >= required:
                        completion = SuggestionsEngine.predict_goal_completion(
                            goal, 
                            budget['remaining_budget'] * 0.3  # Assume 30% to goals
                        )
                        
                        if completion['is_on_track']:
                            suggestions.append({
                                'type': 'success',
                                'icon': '🎯',
                                'title': f'Goal On Track: {goal["name"]}',
                                'message': f'At your current budget, "{goal["name"]}" will be completed by {completion["completion_date"]}.',
                                'action': 'View Goals',
                                'action_url': '/goals/'
                            })
                        else:
                            suggestions.append({
                                'type': 'warning',
                                'icon': '⚡',
                                'title': f'Goal Needs Attention: {goal["name"]}',
                                'message': f'Increase monthly savings by ₹{required - (budget["remaining_budget"] * 0.3):.0f} '
                                          f'to reach your {goal["name"]} goal by {goal["end_date"].strftime("%B %Y")}.',
                                'action': 'View Goals',
                                'action_url': '/goals/'
                            })
        
        # Suggestion 4: Budget utilization
        if budget['remaining_budget'] > 0 and (debts or goals):
            allocation = SuggestionsEngine.generate_smart_allocation(
                budget['remaining_budget'], 
                debts, 
                goals
            )
            
            suggestions.append({
                'type': 'tip',
                'icon': '💰',
                'title': 'Recommended Budget Split',
                'message': f'With ₹{budget["remaining_budget"]:,.0f} remaining: '
                          f'₹{allocation["debt_allocation"]:,.0f} for debts, '
                          f'₹{allocation["goal_allocation"]:,.0f} for goals.',
                'action': None,
                'action_url': None
            })
        
        # Suggestion 5: Emergency fund check
        emergency_goal = next((g for g in goals if 'emergency' in g['name'].lower()), None)
        
        if not emergency_goal:
            suggestions.append({
                'type': 'info',
                'icon': '🛡️',
                'title': 'Start an Emergency Fund',
                'message': 'Consider creating an emergency fund goal. Aim for 3-6 months of expenses as a safety net.',
                'action': 'Create Goal',
                'action_url': '/goals/'
            })
        elif emergency_goal['saved_percentage'] < 50:
            suggestions.append({
                'type': 'warning',
                'icon': '⚠️',
                'title': 'Emergency Fund Progress',
                'message': f'Your emergency fund is at {emergency_goal["saved_percentage"]:.0f}%. '
                          f'Keep building it before focusing on other goals.',
                'action': 'View Goals',
                'action_url': '/goals/'
            })
        
        return suggestions
    
    # ==================== COMPREHENSIVE ANALYSIS ====================
    
    @staticmethod
    def get_comprehensive_analysis(user) -> Dict:
        """
        Get a complete financial analysis with all suggestions.
        
        This is the main function that brings everything together.
        
        Args:
            user: The user object
            
        Returns:
            Complete analysis dictionary
        """
        # Get core data
        budget = SuggestionsEngine.calculate_remaining_budget(user)
        debts = SuggestionsEngine.get_active_debts(user)
        goals = SuggestionsEngine.get_active_goals(user)
        
        # Get debt predictions
        debt_predictions = []
        for debt in debts:
            # Current trajectory
            current_prediction = SuggestionsEngine.predict_debt_payoff(debt, extra_payment=0)
            
            # With extra payment suggestion
            extra_prediction = SuggestionsEngine.predict_debt_payoff(debt, extra_payment=2000)
            
            debt_predictions.append({
                'debt': debt,
                'current': current_prediction,
                'with_extra': extra_prediction
            })
        
        # Get goal predictions
        goal_predictions = []
        allocation = SuggestionsEngine.generate_smart_allocation(
            budget['remaining_budget'], 
            debts, 
            goals
        )
        
        for goal in goals:
            monthly_saving = allocation['goal_allocation'] * (
                goal['monthly_required'] / max(1, sum(g['monthly_required'] for g in goals))
            )
            prediction = SuggestionsEngine.predict_goal_completion(goal, monthly_saving)
            
            goal_predictions.append({
                'goal': goal,
                'prediction': prediction
            })
        
        # Get strategy comparison
        strategy_comparison = None
        if len(debts) > 1:
            available_extra = max(0, budget['remaining_budget'] - sum(d['emi_amount'] for d in debts))
            strategy_comparison = SuggestionsEngine.compare_debt_strategies(debts, available_extra)
        
        # Get guidance
        guidance = SuggestionsEngine.generate_financial_guidance(user)
        
        return {
            'budget': budget,
            'debts': debts,
            'goals': goals,
            'debt_predictions': debt_predictions,
            'goal_predictions': goal_predictions,
            'allocation': allocation,
            'strategy_comparison': strategy_comparison,
            'guidance': guidance,
            'summary': {
                'total_debt': sum(d['remaining_balance'] for d in debts),
                'total_goals_remaining': sum(g['remaining_amount'] for g in goals),
                'is_debt_free_possible': budget['remaining_budget'] > sum(d['emi_amount'] for d in debts),
                'debt_count': len(debts),
                'goal_count': len(goals)
            }
        }


# ==================== CONVENIENCE FUNCTIONS ====================

def get_financial_suggestions(user) -> Dict:
    """Convenience function for getting comprehensive financial analysis."""
    return SuggestionsEngine.get_comprehensive_analysis(user)


def calculate_remaining_budget(user) -> Dict:
    """Convenience function for remaining budget calculation."""
    return SuggestionsEngine.calculate_remaining_budget(user)


def predict_debt_payoff(user):
    """Convenience function for debt payoff prediction."""
    debts = SuggestionsEngine.get_active_debts(user)
    predictions = []
    for debt in debts:
        predictions.append({
            'debt': debt,
            'prediction': SuggestionsEngine.predict_debt_payoff(debt, extra_payment=0),
            'with_extra': SuggestionsEngine.predict_debt_payoff(debt, extra_payment=2000)
        })
    return predictions


def predict_goal_completion(user):
    """Convenience function for goal completion prediction."""
    goals = SuggestionsEngine.get_active_goals(user)
    budget = SuggestionsEngine.calculate_remaining_budget(user)
    allocation = SuggestionsEngine.generate_smart_allocation(
        budget['remaining_budget'], 
        [], 
        goals
    )
    
    predictions = []
    for goal in goals:
        monthly_saving = allocation['goal_allocation'] / max(1, len(goals))
        predictions.append({
            'goal': goal,
            'prediction': SuggestionsEngine.predict_goal_completion(goal, monthly_saving)
        })
    return predictions

