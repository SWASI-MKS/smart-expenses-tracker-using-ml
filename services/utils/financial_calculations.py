
"""
Financial Calculations Utils
===========================
Complete implementation of all required financial health score calculations.
Uses Django ORM for database queries. Handles edge cases and division by zero.

Dependencies:
- expenses.models.Expense
- userincome.models.UserIncome
- debts.models.Debt
- goals.models.Goal
- bank_simulator.models.BankAccount
"""

from django.db.models import Sum, Avg, Count, Q, F
from django.db.models.functions import ExtractMonth, ExtractYear, TruncMonth
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import timedelta
from typing import Dict, Tuple, Optional
import math
from dateutil.relativedelta import relativedelta

from expenses.models import Expense
from userincome.models import UserIncome
from debts.models import Debt
from goals.models import Goal
from bank_simulator.models import BankAccount


def get_user_monthly_expenses(user: User, months_back: int = 3) -> Tuple[float, float]:
    """
    Get average monthly expenses over last N months.
    """
    end_date = timezone.now()
    start_date = end_date - relativedelta(months=months_back)
    
    expenses = Expense.objects.filter(
        owner=user,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(avg_monthly=Avg('amount'))['avg_monthly'] or 0
    
    return float(expenses), float(expenses * 3)  # Monthly, 3-month total


def calculate_emergency_fund_ratio(user: User) -> float:
    """
    Emergency Fund Ratio = (Bank Balance + Goal Savings for Emergency) / (3 * Monthly Expenses)
    Target: 100% = 3 months expenses covered
    """
    try:
        bank_balance = BankAccount.objects.get(user=user).balance or Decimal('0.00')
    except BankAccount.DoesNotExist:
        bank_balance = Decimal('0.00')
    
    emergency_goals = Goal.objects.filter(
        owner=user,
        status__in=['ACTIVE', 'OVERDUE'],
        name__icontains='emergency'
    ).aggregate(total_saved=Sum('current_saved_amount'))['total_saved'] or Decimal('0.00')
    
    monthly_expense, three_month_expense = get_user_monthly_expenses(user)
    
    if three_month_expense == 0:
        return 0.0  # No expenses, infinite ratio
    
    emergency_fund = float(bank_balance + emergency_goals)
    ratio = (emergency_fund / three_month_expense) * 100
    return min(100.0, ratio)  # Cap at 100%


def calculate_savings_rate(user: User) -> float:
    """
    Savings Rate = (Monthly Income - Monthly Expenses) / Monthly Income * 100
    Target: 20%+
    Handles zero income case
    """
    end_date = timezone.now()
    start_date = end_date - relativedelta(months=1)
    
    income_qs = UserIncome.objects.filter(
        owner=user,
        date__gte=start_date
    ).aggregate(total_income=Sum('amount'))['total_income'] or 0
    
    expense_qs = Expense.objects.filter(
        owner=user,
        date__gte=start_date
    ).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
    
    monthly_income = float(income_qs)
    monthly_expenses = float(expense_qs)
    
    if monthly_income == 0:
        return 0.0
    
    savings = monthly_income - monthly_expenses
    rate = (savings / monthly_income) * 100
    return max(0.0, rate)  # No negative rates


def calculate_debt_to_income_ratio(user: User) -> float:
    """
    DTI = (Total Monthly Debt Payments) / Monthly Income * 100
    Target: <36%
    """
    monthly_debt_payments = Debt.objects.filter(
        owner=user,
        status='ACTIVE'
    ).aggregate(total_payments=Sum('emi_amount'))['total_payments'] or Decimal('0.00')
    
    monthly_income = UserIncome.objects.filter(owner=user).aggregate(avg=Avg('amount'))['avg'] or Decimal('0.00')
    
    if monthly_income == 0:
        return 100.0  # Worst case if no income
    
    dti = (float(monthly_debt_payments) / float(monthly_income)) * 100
    return min(100.0, dti)


def calculate_budget_adherence(user: User) -> float:
    """
    Budget Adherence = (Actual Expenses / Budget Limit) * 100
    If no budget, use 50% of income as proxy budget
    """
    # Get last month's data
    end_date = timezone.now() - relativedelta(months=1)
    start_date = end_date - relativedelta(months=1)
    
    actual_expenses = Expense.objects.filter(
        owner=user,
        date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Proxy budget = 50% of income if no ExpenseLimit
    income_last_month = UserIncome.objects.filter(
        owner=user,
        date__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    proxy_budget = float(income_last_month) * 0.5
    
    if proxy_budget == 0:
        return 0.0
    
    adherence_ratio = (float(actual_expenses) / proxy_budget) * 100
    # Lower ratio = better adherence (under budget)
    return max(0.0, 100 - adherence_ratio)  # Invert to score


def calculate_goal_progress(user: User) -> float:
    """
    Overall Goal Progress = Average saved percentage across all active goals
    """
    goals = Goal.objects.filter(
        owner=user,
        status__in=['ACTIVE', 'OVERDUE']
    )
    
    if not goals.exists():
        return 0.0
    
    total_progress = 0
    count = 0
    for goal in goals:
        progress = min(100, (goal.current_saved_amount / goal.amount_to_save * 100) if goal.amount_to_save > 0 else 0)
        total_progress += progress
        count += 1
    
    return (total_progress / count) if count > 0 else 0.0


def calculate_net_worth_growth(user: User) -> float:
    """
    Month-over-month net worth growth percentage
    Net Worth = Bank Balance + Goal Savings - Debt Remaining
    """
    current_nw = 0.0
    
    # Bank balance
    try:
        bank = BankAccount.objects.get(user=user)
        current_nw += float(bank.balance)
    except BankAccount.DoesNotExist:
        pass
    
    # Goal savings
    goal_savings = Goal.objects.filter(owner=user).aggregate(total=Sum('current_saved_amount'))['total'] or 0
    current_nw += float(goal_savings)
    
    # Debt
    total_debt = Debt.objects.filter(owner=user, status='ACTIVE').aggregate(total=Sum('remaining_balance'))['total'] or 0
    current_nw -= float(total_debt)
    
    # Previous month (simplified - use total income/expenses)
    monthly_income = UserIncome.objects.filter(owner=user).aggregate(avg=Avg('amount'))['avg'] or 0
    monthly_expenses = Expense.objects.filter(owner=user).aggregate(avg=Avg('amount'))['avg'] or 0
    prev_nw = float(monthly_income - monthly_expenses)
    
    if prev_nw == 0:
        return 0.0
    
    growth = ((current_nw - prev_nw) / prev_nw) * 100
    return growth


def calculate_financial_health_score(user: User) -> Dict:
    """
    Weighted Financial Health Score (0-100) with A-F grade.
    
    Weights:
    - Emergency Fund: 25%
    - Savings Rate: 20%
    - DTI: 20%
    - Budget Adherence: 20%
    - Goal Progress: 15%
    
    Returns:
    Dict with score, grade, factors breakdown
    """
    
    emergency_fund = calculate_emergency_fund_ratio(user)
    savings_rate = calculate_savings_rate(user)
    dti = calculate_debt_to_income_ratio(user)
    budget_adherence = calculate_budget_adherence(user)
    goal_progress = calculate_goal_progress(user)
    
    # Normalize each factor to 0-100 score
    emergency_score = min(100, emergency_fund)
    savings_score = min(100, savings_rate * 5)  # 20% optimal
    dti_score = max(0, 100 - dti)  # Lower better
    budget_score = budget_adherence
    goal_score = min(100, goal_progress)
    
    # Weighted score
    total_score = (
        emergency_score * 0.25 +
        savings_score * 0.20 +
        dti_score * 0.20 +
        budget_score * 0.20 +
        goal_score * 0.15
    )
    
    # Grade
    if total_score >= 90:
        grade = 'A'
    elif total_score >= 80:
        grade = 'B'
    elif total_score >= 70:
        grade = 'C'
    elif total_score >= 60:
        grade = 'D'
    else:
        grade = 'F'
    
    return {
        'score': round(total_score, 1),
        'grade': grade,
        'factors': {
            'Emergency_Fund': {
                'value': f'{emergency_fund:.1f}%',
                'score': emergency_score
            },
            'Savings_Rate': {
                'value': f'{savings_rate:.1f}%',
                'score': savings_score
            },
            'DTI_Ratio': {
                'value': f'{dti:.1f}%',
                'score': dti_score
            },
            'Budget_Adherence': {
                'value': f'{budget_adherence:.1f}%',
                'score': budget_score
            },
            'Goal_Progress': {
                'value': f'{goal_progress:.1f}%',
                'score': goal_score
            }
        }
    }


def generate_recommendations(user: User) -> List[str]:
    """
    Generate personalized recommendations based on low scores.
    """
    health_score = calculate_financial_health_score(user)
    recs = []
    
    factors = health_score['factors']
    
    if factors['Emergency_Fund']['score'] < 50:
        recs.append('🏦 Build emergency fund for 3 months expenses')
    
    if factors['Savings_Rate']['score'] < 50:
        recs.append('💰 Aim for 10-20% savings rate from monthly income')
    
    if factors['DTI_Ratio']['score'] < 50:
        recs.append('💳 Keep debt payments <36% of income')
    
    if factors['Budget_Adherence']['score'] < 50:
        recs.append('📊 Track and stick to your budget limits')
    
    if factors['Goal_Progress']['score'] < 50:
        recs.append('🎯 Increase contributions to your savings goals')
    
    return recs

