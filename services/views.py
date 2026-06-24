from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .utils.financial_calculations import (
    calculate_financial_health_score, 
    generate_recommendations,
    calculate_emergency_fund_ratio,
    calculate_savings_rate,
    calculate_goal_progress
)
from .financial_service import FinancialService
from expenses.models import Expense
from userincome.models import UserIncome
from debts.models import Debt
from goals.models import Goal
from bank_simulator.models import BankAccount
from django.utils import timezone
from decimal import Decimal


@login_required
def financial_suggestions(request):
    user = request.user
    currency_symbol = '₹'  # Customize per user currency if needed
    
    # Calculate health score and recommendations
    health_score = calculate_financial_health_score(user)
    raw_recs = generate_recommendations(user)
    recommendations = []
    for rec in raw_recs:
        icon, text = rec.split(' ', 1) if ' ' in rec else ('', rec)
        rec_type = 'warning' if any(word in rec.lower() for word in ['build', 'aim', 'keep', 'track']) else 'good'
        recommendations.append({
            'title': text.strip(),
            'message': text.strip(),
            'type': rec_type
        })
    
    emergency_fund_pct = calculate_emergency_fund_ratio(user)
    goal_progress_pct = calculate_goal_progress(user)
    
    # Budget breakdown
    budget = {
        'monthly_income': FinancialService.calculate_total_income(user),
        'monthly_expenses': FinancialService.calculate_total_expenses(user),
        'remaining': FinancialService.calculate_total_income(user) - FinancialService.calculate_total_expenses(user)
    }
    
    # Net worth
    net_worth_data = {
        'assets': {
            'bank_balance': 0.0,
            'liabilities': 0.0
        },
        'total': 0.0
    }
    try:
        bank_account = BankAccount.objects.get(user=user)
        net_worth_data['assets']['bank_balance'] = float(bank_account.balance)
    except BankAccount.DoesNotExist:
        pass
    
    debts_total = Debt.objects.filter(owner=user, status='ACTIVE').aggregate(total=Sum('remaining_balance'))['total'] or 0
    goals_saved = Goal.objects.filter(owner=user).aggregate(saved=Sum('current_saved_amount'))['saved'] or 0
    
    net_worth_data['total'] = float(net_worth_data['assets']['bank_balance'] + goals_saved - debts_total)
    net_worth_data['wealth_status'] = 'Healthy' if net_worth_data['total'] > 0 else 'Building' if net_worth_data['total'] > -10000 else 'Needs Attention'
    
    # Savings rate
    savings_rate_current = calculate_savings_rate(user)
    savings_status = 'Excellent' if savings_rate_current >= 20 else 'Good' if savings_rate_current >= 10 else 'Fair' if savings_rate_current >= 5 else 'Needs Improvement'
    savings_rate = {
        'current': savings_rate_current,
        'current_rate': savings_rate_current,  # for template
        'status': savings_status,
        'monthly_savings': budget['remaining'],
        'yearly_projection': budget['remaining'] * 12
    }
    
    # Debt predictions
    debts = Debt.objects.filter(owner=user, status='ACTIVE')
    debt_predictions = []
    for debt in debts:
        debt_info = {
            'name': debt.loan_name,
            'remaining_balance': float(debt.remaining_balance),
            'emi_amount': float(debt.emi_amount),
            'interest_rate': float(debt.interest_rate)
        }
        # Current trajectory
        # Simplified prediction (full logic in suggestions_engine.py if needed)
        months_remaining = debt.remaining_balance / debt.emi_amount if debt.emi_amount > 0 else 999
        debt_predictions.append({
            'debt': debt_info,
            'payoff_months': int(months_remaining),
            'payoff_date': 'TBD'  # Calculate full in JS or service
        })
    
    # Goal predictions
    goals = Goal.objects.filter(owner=user, status__in=['ACTIVE', 'OVERDUE'])
    goal_predictions = []
    for goal in goals:
        saved_pct = (goal.current_saved_amount / goal.amount_to_save * 100) if goal.amount_to_save > 0 else 0
        goal_predictions.append({
            'name': goal.name,
            'saved_percentage': saved_pct,
            'completion_date': goal.end_date.strftime('%B %Y') if goal.end_date else 'TBD',
            'on_track': saved_pct >= 50  # Simple check
        })
    
    # Guidance (personalized)
    guidance = []
    if health_score['score'] < 60:
        guidance.append({
            'type': 'warning',
            'title': 'Financial Health Needs Work',
            'message': f'Your score is {health_score["score"]}/100. Focus on emergency fund and savings rate.',
            'action_url': '/goals/add/'
        })
    
    context = {
        'health_score': health_score,
        'recommendations': recommendations,
        'budget': budget,
        'net_worth': net_worth_data,
        'savings_rate': savings_rate,
        'emergency_fund_pct': emergency_fund_pct,
        'goal_progress_pct': goal_progress_pct,
        'net_worth': net_worth_data,
        'debt_predictions': debt_predictions,
        'goal_predictions': goal_predictions,
        'guidance': guidance,
        'currency_symbol': currency_symbol,
        'has_health_score': True,
        'has_debts': bool(debt_predictions),
        'has_goals': bool(goal_predictions),
        'has_budget': budget['monthly_income'] > 0
    }
    
    return render(request, 'suggestions/financial_suggestions.html', context)

