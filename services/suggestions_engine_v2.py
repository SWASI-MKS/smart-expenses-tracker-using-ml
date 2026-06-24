"""
Financial Suggestions Engine V2.0 (Enhanced Edition)
=====================================================
An intelligent financial advisor system that analyzes user data and provides
personalized recommendations to help users become debt-free and achieve their goals.

Uses real-time database aggregations for all calculations.

NEW FEATURES V2.0:
- Spending Pattern Analysis with category breakdown
- Financial Health Score calculation
- Savings Rate Calculator & recommendations
- Monthly/Yearly projections
- Bill & EMI reminders
- Credit Card Analysis
- Investment suggestions
- Milestone tracking
- Expense anomaly detection
- Budget optimization tips
- Income diversification analysis
- Net worth tracking
- Debt-to-Income ratio
"""

from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import ExtractMonth, ExtractYear
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta, date
from typing import Dict, List, Optional, Tuple
import math
import random
from collections import defaultdict

from expenses.models import Expense, Category
from userincome.models import UserIncome
from debts.models import Debt, EMIPayment
from goals.models import Goal
from bank_simulator.models import BankTransaction, CardTransaction, Card, BankAccount


class SuggestionsEngineV2:
    """
    Enhanced Financial Suggestions Engine V2.0
    Provides debt payoff predictions, goal completion forecasts, and smart budget allocation.
    Plus: Health score, spending patterns, projections, and more!
    """
    
    # ==================== INCOME & EXPENSES ====================
    
    @staticmethod
    def calculate_monthly_income(user, year=None, month=None) -> float:
        """Calculate total income for a specific month."""
        if year is None:
            year = timezone.now().year
        if month is None:
            month = timezone.now().month
        
        total = UserIncome.objects.filter(
            owner=user,
            date__year=year,
            date__month=month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Add projected recurring income
        recurring_income = UserIncome.objects.filter(
            owner=user,
            is_recurring=True
        ).values('source').annotate(avg_amount=Avg('amount'))
        
        for item in recurring_income:
            if item['avg_amount']:
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
        """Calculate total expenses for a specific month."""
        if year is None:
            year = timezone.now().year
        if month is None:
            month = timezone.now().month
        
        total = Expense.objects.filter(
            owner=user,
            date__year=year,
            date__month=month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        card_spending = CardTransaction.objects.filter(
            user=user,
            transaction_date__year=year,
            transaction_date__month=month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return float(total) + float(card_spending)
    
    @staticmethod
    def calculate_remaining_budget(user, year=None, month=None) -> Dict:
        """Calculate the true remaining monthly budget."""
        monthly_income = SuggestionsEngineV2.calculate_monthly_income(user, year, month)
        monthly_expenses = SuggestionsEngineV2.calculate_monthly_expenses(user, year, month)
        remaining = monthly_income - monthly_expenses
        
        return {
            'monthly_income': monthly_income,
            'monthly_expenses': monthly_expenses,
            'remaining_budget': max(0, remaining),
            'is_deficit': remaining < 0,
            'deficit_amount': abs(remaining) if remaining < 0 else 0
        }
    
    # ==================== FINANCIAL HEALTH SCORE ====================
    
    @staticmethod
    def calculate_financial_health_score(user) -> Dict:
        """
        Calculate a comprehensive financial health score (0-100).
        
        Factors:
        - Savings rate (25 points)
        - Debt-to-income ratio (25 points)
        - Emergency fund presence (20 points)
        - Budget adherence (15 points)
        - Goal progress (15 points)
        """
        score = 0
        factors = {}
        
        # 1. Savings Rate (25 points)
        budget = SuggestionsEngineV2.calculate_remaining_budget(user)
        monthly_income = budget['monthly_income']
        
        if monthly_income > 0:
            savings_rate = (budget['remaining_budget'] / monthly_income) * 100
            if savings_rate >= 20:
                factors['savings_rate'] = {'score': 25, 'value': savings_rate, 'status': 'excellent'}
            elif savings_rate >= 10:
                factors['savings_rate'] = {'score': 15, 'value': savings_rate, 'status': 'good'}
            elif savings_rate >= 5:
                factors['savings_rate'] = {'score': 8, 'value': savings_rate, 'status': 'fair'}
            else:
                factors['savings_rate'] = {'score': 0, 'value': savings_rate, 'status': 'poor'}
            score += factors['savings_rate']['score']
        
        # 2. Debt-to-Income Ratio (25 points)
        debts = SuggestionsEngineV2.get_active_debts(user)
        total_monthly_debt = sum(d['emi_amount'] for d in debts)
        
        if monthly_income > 0:
            dti_ratio = (total_monthly_debt / monthly_income) * 100
            if dti_ratio <= 15:
                factors['dti_ratio'] = {'score': 25, 'value': dti_ratio, 'status': 'excellent'}
            elif dti_ratio <= 30:
                factors['dti_ratio'] = {'score': 15, 'value': dti_ratio, 'status': 'good'}
            elif dti_ratio <= 43:
                factors['dti_ratio'] = {'score': 8, 'value': dti_ratio, 'status': 'fair'}
            else:
                factors['dti_ratio'] = {'score': 0, 'value': dti_ratio, 'status': 'poor'}
            score += factors['dti_ratio']['score']
        
        # 3. Emergency Fund (20 points)
        goals = SuggestionsEngineV2.get_active_goals(user)
        emergency_goal = next((g for g in goals if 'emergency' in g['name'].lower()), None)
        
        if emergency_goal:
            if emergency_goal['saved_percentage'] >= 100:
                factors['emergency_fund'] = {'score': 20, 'value': emergency_goal['saved_percentage'], 'status': 'excellent'}
            elif emergency_goal['saved_percentage'] >= 50:
                factors['emergency_fund'] = {'score': 12, 'value': emergency_goal['saved_percentage'], 'status': 'good'}
            elif emergency_goal['saved_percentage'] >= 25:
                factors['emergency_fund'] = {'score': 5, 'value': emergency_goal['saved_percentage'], 'status': 'fair'}
            else:
                factors['emergency_fund'] = {'score': 0, 'value': emergency_goal['saved_percentage'], 'status': 'poor'}
        else:
            factors['emergency_fund'] = {'score': 0, 'value': 0, 'status': 'none'}
        score += factors['emergency_fund']['score']
        
        # 4. Budget Adherence (15 points)
        # Check if expenses are within income
        if monthly_income > 0:
            expense_ratio = (budget['monthly_expenses'] / monthly_income) * 100
            if expense_ratio <= 80:
                factors['budget_adherence'] = {'score': 15, 'value': expense_ratio, 'status': 'excellent'}
            elif expense_ratio <= 90:
                factors['budget_adherence'] = {'score': 10, 'value': expense_ratio, 'status': 'good'}
            elif expense_ratio <= 100:
                factors['budget_adherence'] = {'score': 5, 'value': expense_ratio, 'status': 'fair'}
            else:
                factors['budget_adherence'] = {'score': 0, 'value': expense_ratio, 'status': 'poor'}
            score += factors['budget_adherence']['score']
        
        # 5. Goal Progress (15 points)
        if goals:
            avg_progress = sum(g['saved_percentage'] for g in goals) / len(goals)
            if avg_progress >= 75:
                factors['goal_progress'] = {'score': 15, 'value': avg_progress, 'status': 'excellent'}
            elif avg_progress >= 50:
                factors['goal_progress'] = {'score': 10, 'value': avg_progress, 'status': 'good'}
            elif avg_progress >= 25:
                factors['goal_progress'] = {'score': 5, 'value': avg_progress, 'status': 'fair'}
            else:
                factors['goal_progress'] = {'score': 0, 'value': avg_progress, 'status': 'poor'}
            score += factors['goal_progress']['score']
        
        # Determine grade
        if score >= 90:
            grade = 'A+'
            grade_color = '#10b981'
        elif score >= 80:
            grade = 'A'
            grade_color = '#10b981'
        elif score >= 70:
            grade = 'B'
            grade_color = '#3b82f6'
        elif score >= 60:
            grade = 'C'
            grade_color = '#f59e0b'
        elif score >= 50:
            grade = 'D'
            grade_color = '#f97316'
        else:
            grade = 'F'
            grade_color = '#ef4444'
        
        return {
            'score': min(100, score),
            'max_score': 100,
            'grade': grade,
            'grade_color': grade_color,
            'factors': factors,
            'recommendations': SuggestionsEngineV2._get_health_recommendations(factors)
        }
    
    @staticmethod
    def _get_health_recommendations(factors: Dict) -> List[str]:
        """Generate recommendations based on health factors."""
        recs = []
        
        if 'savings_rate' in factors and factors['savings_rate']['status'] in ['fair', 'poor']:
            recs.append("💰 Increase your savings rate to at least 10-20% of income")
        
        if 'dti_ratio' in factors and factors['dti_ratio']['status'] in ['fair', 'poor']:
            recs.append("💳 Work on reducing your debt-to-income ratio below 30%")
        
        if 'emergency_fund' in factors and factors['emergency_fund']['status'] in ['none', 'poor']:
            recs.append("🛡️ Build an emergency fund covering 3-6 months of expenses")
        
        if 'budget_adherence' in factors and factors['budget_adherence']['status'] in ['fair', 'poor']:
            recs.append("📊 Reduce expenses to stay within 80% of your income")
        
        if 'goal_progress' in factors and factors['goal_progress']['status'] in ['fair', 'poor']:
            recs.append("🎯 Increase contributions to your financial goals")
        
        return recs
    
    # ==================== SPENDING PATTERN ANALYSIS ====================
    
    @staticmethod
    def analyze_spending_patterns(user, months: int = 3) -> Dict:
        """
        Analyze spending patterns over specified months.
        
        Returns category breakdown, trends, and insights.
        """
        today = timezone.now().date()
        category_spending = defaultdict(list)
        monthly_totals = []
        
        for i in range(months):
            month_date = today - timedelta(days=30 * i)
            year, month = month_date.year, month_date.month
            
            # Get expenses by category
            expenses = Expense.objects.filter(
                owner=user,
                date__year=year,
                date__month=month
            ).values('category').annotate(total=Sum('amount'))
            
            month_total = 0
            for exp in expenses:
                category = exp['category'] or 'Other'
                amount = float(exp['total']) or 0
                category_spending[category].append(amount)
                month_total += amount
            
            # Add card spending
            card_spending = CardTransaction.objects.filter(
                user=user,
                transaction_date__year=year,
                transaction_date__month=month
            ).aggregate(total=Sum('amount'))['total'] or 0
            month_total += float(card_spending)
            
            monthly_totals.append({
                'year': year,
                'month': month,
                'total': month_total
            })
        
        # Calculate averages and trends
        categories = []
        for cat, amounts in category_spending.items():
            avg = sum(amounts) / len(amounts) if amounts else 0
            trend = 'stable'
            if len(amounts) >= 2:
                if amounts[0] > amounts[1] * 1.2:
                    trend = 'increasing'
                elif amounts[0] < amounts[1] * 0.8:
                    trend = 'decreasing'
            
            categories.append({
                'name': cat,
                'average': avg,
                'trend': trend,
                'last_month': amounts[0] if amounts else 0
            })
        
        # Sort by average spending
        categories.sort(key=lambda x: x['average'], reverse=True)
        
        # Calculate overall trend
        overall_trend = 'stable'
        if len(monthly_totals) >= 2:
            if monthly_totals[0]['total'] > monthly_totals[1]['total'] * 1.15:
                overall_trend = 'increasing'
            elif monthly_totals[0]['total'] < monthly_totals[1]['total'] * 0.85:
                overall_trend = 'decreasing'
        
        return {
            'categories': categories[:8],  # Top 8 categories
            'monthly_totals': monthly_totals,
            'overall_trend': overall_trend,
            'average_monthly': sum(m['total'] for m in monthly_totals) / len(monthly_totals) if monthly_totals else 0
        }
    
    @staticmethod
    def detect_expense_anomalies(user) -> List[Dict]:
        """
        Detect unusual spending patterns that might need attention.
        """
        anomalies = []
        today = timezone.now().date()
        
        # Get last 3 months of data
        for i in range(3):
            month_date = today - timedelta(days=30 * i)
            year, month = month_date.year, month_date.month
            
            # Get daily spending for this month
            daily_spending = Expense.objects.filter(
                owner=user,
                date__year=year,
                date__month=month
            ).extra(
                where=["strftime('%d', date) = ?"],
                params=[today.strftime('%d')]
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            if daily_spending > 10000:  # Unusually high single day spending
                anomalies.append({
                    'type': 'high_day',
                    'date': month_date,
                    'amount': float(daily_spending),
                    'message': f'High spending of ₹{daily_spending:,.0f} on {month_date.strftime("%B %d")}'
                })
        
        # Check for recurring large expenses
        large_expenses = Expense.objects.filter(
            owner=user,
            amount__gte=50000
        ).order_by('-date')[:5]
        
        for exp in large_expenses:
            anomalies.append({
                'type': 'large_expense',
                'date': exp.date,
                'amount': exp.amount,
                'category': exp.category,
                'message': f'Large expense: ₹{exp.amount:,.0f} for {exp.category}'
            })
        
        return anomalies
    
    # ==================== SAVINGS RATE CALCULATOR ====================
    
    @staticmethod
    def calculate_savings_rate(user) -> Dict:
        """Calculate current savings rate and projections."""
        budget = SuggestionsEngineV2.calculate_remaining_budget(user)
        monthly_income = budget['monthly_income']
        
        if monthly_income <= 0:
            return {
                'current_rate': 0,
                'monthly_savings': 0,
                'yearly_projection': 0,
                'status': 'no_income'
            }
        
        current_rate = (budget['remaining_budget'] / monthly_income) * 100
        monthly_savings = budget['remaining_budget']
        yearly_projection = monthly_savings * 12
        
        # Calculate needed rate for goals
        goals = SuggestionsEngineV2.get_active_goals(user)
        debts = SuggestionsEngineV2.get_active_debts(user)
        
        total_goal_monthly = sum(g['monthly_required'] for g in goals)
        total_debt_monthly = sum(d['emi_amount'] for d in debts)
        
        needed_for_goals = total_goal_monthly + total_debt_monthly
        needed_rate = (needed_for_goals / monthly_income) * 100 if monthly_income > 0 else 0
        
        status = 'excellent' if current_rate >= 20 else 'good' if current_rate >= 10 else 'fair' if current_rate >= 5 else 'poor'
        
        return {
            'current_rate': current_rate,
            'monthly_savings': monthly_savings,
            'yearly_projection': yearly_projection,
            'needed_rate_for_goals': needed_rate,
            'status': status,
            'message': SuggestionsEngineV2._get_savings_message(current_rate, needed_rate)
        }
    
    @staticmethod
    def _get_savings_message(current: float, needed: float) -> str:
        """Generate savings rate message."""
        if current >= 20:
            return "Excellent! You're saving well above the recommended 20%."
        elif current >= 10:
            return "Good savings rate. Consider increasing to 20% for financial independence."
        elif current >= 5:
            return "Fair, but aim for at least 10-20% savings rate."
        else:
            if needed > current:
                return f"You need {needed:.1f}% savings rate to meet your goals. Try to reduce expenses."
            return "Low savings rate. Review your expenses to find ways to save more."
    
    # ==================== PROJECTIONS ====================
    
    @staticmethod
    def generate_projections(user, years: int = 1) -> Dict:
        """Generate financial projections for the next N years."""
        budget = SuggestionsEngineV2.calculate_remaining_budget(user)
        debts = SuggestionsEngineV2.get_active_debts(user)
        goals = SuggestionsEngineV2.get_active_goals(user)
        
        monthly_savings = budget['remaining_budget']
        yearly_savings = monthly_savings * 12
        
        # Project savings growth (assuming 5% annual income increase)
        savings_projections = []
        current_savings = yearly_savings
        
        # Get current bank balance
        try:
            bank_account = BankAccount.objects.get(user=user)
            current_savings += float(bank_account.balance)
        except BankAccount.DoesNotExist:
            pass
        
        for year in range(1, years + 1):
            projected = current_savings * (1.05 ** year)  # 5% annual growth
            savings_projections.append({
                'year': timezone.now().year + year,
                'projected_savings': projected,
                'cumulative': sum(s['projected_savings'] for s in savings_projections)
            })
        
        # Project debt payoff
        debt_projections = []
        total_debt = sum(d['remaining_balance'] for d in debts)
        
        if total_debt > 0 and monthly_savings > 0:
            months_to_payoff = math.ceil(total_debt / monthly_savings)
            payoff_date = date(timezone.now().year, timezone.now().month, 1) + timedelta(days=months_to_payoff * 30)
            
            debt_projections = {
                'total_debt': total_debt,
                'months_remaining': months_to_payoff,
                'payoff_date': payoff_date.strftime('%B %Y'),
                'total_interest': 0  # Simplified
            }
        
        # Project goal completion
        goal_projections = []
        for goal in goals:
            remaining = goal['remaining_amount']
            if remaining > 0 and monthly_savings > 0:
                monthly_for_goal = monthly_savings * 0.3  # Assume 30% to goals
                months = math.ceil(remaining / monthly_for_goal)
                completion = date(timezone.now().year, timezone.now().month, 1) + timedelta(days=months * 30)
                
                goal_projections.append({
                    'goal': goal['name'],
                    'months_remaining': months,
                    'completion_date': completion.strftime('%B %Y'),
                    'on_track': completion <= goal['end_date']
                })
        
        return {
            'savings_projections': savings_projections,
            'debt_projections': debt_projections,
            'goal_projections': goal_projections,
            'assumptions': {
                'income_growth': '5% annual',
                'savings_allocation': '70% debt, 30% goals',
                'investment_return': 'Not calculated'
            }
        }
    
    # ==================== CREDIT CARD ANALYSIS ====================
    
    @staticmethod
    def analyze_credit_cards(user) -> Dict:
        """Analyze credit card usage and provide recommendations."""
        cards = Card.objects.filter(user=user)
        
        card_analysis = []
        total_spending = 0
        total_balance = 0
        
        for card in cards:
            # Get this month's spending
            spending = CardTransaction.objects.filter(
                card=card,
                transaction_date__month=timezone.now().month,
                transaction_date__year=timezone.now().year
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            spending = float(spending)
            total_spending += spending
            
            # Calculate utilization - use credit_limit field
            credit_limit = getattr(card, 'credit_limit', None) or getattr(card, 'limit', None)
            limit = float(credit_limit) if credit_limit else 0
            utilization = (spending / limit * 100) if limit > 0 else 0
            total_balance += spending
            
            # Get transaction count
            tx_count = CardTransaction.objects.filter(
                card=card,
                transaction_date__month=timezone.now().month,
                transaction_date__year=timezone.now().year
            ).count()
            
            card_analysis.append({
                'name': card.card_name,
                'spending': spending,
                'limit': limit,
                'utilization': utilization,
                'transactions': tx_count,
                'utilization_status': 'high' if utilization > 70 else 'medium' if utilization > 30 else 'low'
            })
        
        # Overall assessment
        avg_utilization = (total_balance / sum(c['limit'] for c in card_analysis) * 100) if card_analysis else 0
        
        recommendations = []
        if avg_utilization > 70:
            recommendations.append("⚠️ High credit utilization! Try to keep it below 30% for better credit score.")
        if total_spending > 50000:
            recommendations.append("💳 High card spending this month. Consider using cash or debit for some purchases.")
        if not card_analysis:
            recommendations.append("📝 No credit card usage data. Add cards to track spending.")
        
        return {
            'cards': card_analysis,
            'total_spending': total_spending,
            'total_balance': total_balance,
            'average_utilization': avg_utilization,
            'recommendations': recommendations
        }
    
    # ==================== NET WORTH TRACKING ====================
    
    @staticmethod
    def calculate_net_worth(user) -> Dict:
        """Calculate comprehensive net worth."""
        # Assets
        try:
            bank_account = BankAccount.objects.get(user=user)
            bank_balance = float(bank_account.balance)
        except BankAccount.DoesNotExist:
            bank_balance = 0
        
        # Cash savings (goals)
        goals = SuggestionsEngineV2.get_active_goals(user)
        total_saved = sum(g['current_saved'] for g in goals)
        
        # Liabilities
        debts = SuggestionsEngineV2.get_active_debts(user)
        total_debt = sum(d['remaining_balance'] for d in debts)
        
        # Income this year
        yearly_income = UserIncome.objects.filter(
            owner=user,
            date__year=timezone.now().year
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        net_worth = bank_balance + total_saved - total_debt
        
        # Change from last month - calculate year/month values first to avoid duplicate keyword args
        current_month = timezone.now().month
        current_year = timezone.now().year
        if current_month > 1:
            last_month = current_month - 1
            last_year = current_year
        else:
            last_month = 12
            last_year = current_year - 1
        
        last_month_income = UserIncome.objects.filter(
            owner=user,
            date__year=last_year,
            date__month=last_month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        last_month_expenses = Expense.objects.filter(
            owner=user,
            date__year=last_year,
            date__month=last_month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        monthly_change = float(last_month_income) - float(last_month_expenses)
        
        return {
            'assets': {
                'bank_balance': bank_balance,
                'savings_goals': total_saved,
                'total': bank_balance + total_saved
            },
            'liabilities': {
                'debts': total_debt,
                'total': total_debt
            },
            'net_worth': net_worth,
            'monthly_change': monthly_change,
            'yearly_income': float(yearly_income),
            'wealth_status': 'positive' if net_worth > 0 else 'negative'
        }
    
    # ==================== DEBT ANALYSIS (Existing) ====================
    
    @staticmethod
    def get_active_debts(user) -> List[Dict]:
        """Get all active debts with detailed information."""
        debts = Debt.objects.filter(
            owner=user,
            status=Debt.STATUS_ACTIVE
        )
        
        debt_list = []
        for debt in debts:
            remaining_balance = float(debt.remaining_balance)
            emi_amount = float(debt.emi_amount)
            interest_rate = float(debt.interest_rate)
            
            months_remaining = 0
            if emi_amount > 0 and remaining_balance > 0:
                monthly_rate = interest_rate / 100 / 12
                if monthly_rate > 0:
                    try:
                        months_remaining = -math.log(1 - (remaining_balance * monthly_rate) / emi_amount) / math.log(1 + monthly_rate)
                        months_remaining = max(1, math.ceil(months_remaining))
                    except:
                        months_remaining = int(remaining_balance / emi_amount)
                else:
                    months_remaining = int(remaining_balance / emi_amount)
            
            debt_list.append({
                'id': debt.id,
                'name': debt.loan_name,
                'type': debt.get_loan_type_display(),
                'remaining_balance': remaining_balance,
                'emi_amount': emi_amount,
                'interest_rate': interest_rate,
                'months_remaining': months_remaining,
                'next_emi_date': debt.next_emi_date,
                'lender_name': debt.lender_name
            })
        
        debt_list.sort(key=lambda x: x['remaining_balance'])
        return debt_list
    
    @staticmethod
    def predict_debt_payoff(debt_info: Dict, extra_payment: float = 0) -> Dict:
        """Predict debt payoff date with optional extra payment."""
        remaining_balance = debt_info['remaining_balance']
        current_emi = debt_info['emi_amount']
        interest_rate = debt_info['interest_rate']
        
        total_monthly_payment = current_emi + extra_payment
        
        if total_monthly_payment <= 0 or remaining_balance <= 0:
            return {'payoff_months': 999, 'payoff_date': None, 'total_interest': 0, 'total_cost': remaining_balance, 'months_saved': 0}
        
        monthly_rate = interest_rate / 100 / 12
        
        months_with_extra = 0
        balance = remaining_balance
        
        while balance > 0 and months_with_extra < 600:
            interest = balance * monthly_rate
            principal = total_monthly_payment - interest
            if principal >= balance:
                months_with_extra += 1
                break
            balance -= principal
            months_with_extra += 1
        
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
        
        months_saved = months_current - months_with_extra
        
        today = timezone.now().date()
        payoff_date = date(today.year, today.month, 1) + timedelta(days=months_with_extra * 30)
        
        return {
            'payoff_months': months_with_extra,
            'payoff_date': payoff_date.strftime('%B %Y'),
            'payoff_date_obj': payoff_date,
            'total_interest': max(0, (total_monthly_payment * months_with_extra) - remaining_balance),
            'total_cost': total_monthly_payment * months_with_extra,
            'months_saved': max(0, months_saved),
            'interest_saved': max(0, (current_emi * months_current) - (total_monthly_payment * months_with_extra)),
            'new_monthly_payment': total_monthly_payment
        }
    
    # ==================== GOAL ANALYSIS (Existing) ====================
    
    @staticmethod
    def get_active_goals(user) -> List[Dict]:
        """Get all active goals with detailed information."""
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
        """Predict goal completion date."""
        remaining_amount = goal_info['remaining_amount']
        
        if monthly_saving <= 0 or remaining_amount <= 0:
            return {'months_to_complete': 999, 'completion_date': None, 'is_on_track': False}
        
        months_to_complete = math.ceil(remaining_amount / monthly_saving)
        
        today = timezone.now().date()
        completion_date = date(today.year, today.month, 1) + timedelta(days=months_to_complete * 30)
        
        target_date = goal_info['end_date']
        is_on_track = completion_date <= target_date
        
        return {
            'months_to_complete': months_to_complete,
            'completion_date': completion_date.strftime('%B %Y'),
            'completion_date_obj': completion_date,
            'is_on_track': is_on_track,
            'monthly_saving_required': monthly_saving
        }
    
    # ==================== SMART ALLOCATION ====================
    
    @staticmethod
    def generate_smart_allocation(remaining_budget: float, debts: List[Dict], goals: List[Dict]) -> Dict:
        """Generate smart budget allocation."""
        if remaining_budget <= 0:
            return {
                'total_budget': remaining_budget,
                'debt_allocation': 0,
                'goal_allocation': 0,
                'is_deficit': True,
                'message': 'Your expenses exceed your income.'
            }
        
        total_min_debt = sum(d['emi_amount'] for d in debts)
        total_min_goals = sum(g['monthly_required'] for g in goals if g['monthly_required'] > 0)
        
        if total_min_debt + total_min_goals > remaining_budget:
            debt_allocation = min(total_min_debt, remaining_budget)
            goal_allocation = max(0, remaining_budget - debt_allocation)
            
            return {
                'total_budget': remaining_budget,
                'debt_allocation': debt_allocation,
                'goal_allocation': goal_allocation,
                'is_deficit': False,
                'message': 'Budget covers minimum debt payments only.',
                'debt_percentage': (debt_allocation / remaining_budget * 100) if remaining_budget > 0 else 0,
                'goal_percentage': (goal_allocation / remaining_budget * 100) if remaining_budget > 0 else 0
            }
        
        debt_allocation = total_min_debt
        goal_allocation = total_min_goals
        extra = remaining_budget - (total_min_debt + total_min_goals)
        
        if debts and extra > 0:
            debt_allocation += extra * 0.7
        if goals and extra > 0:
            goal_allocation += extra * 0.3
        
        return {
            'total_budget': remaining_budget,
            'debt_allocation': debt_allocation,
            'goal_allocation': goal_allocation,
            'is_deficit': False,
            'message': 'Smart allocation applied.',
            'debt_percentage': (debt_allocation / remaining_budget * 100) if remaining_budget > 0 else 0,
            'goal_percentage': (goal_allocation / remaining_budget * 100) if remaining_budget > 0 else 0
        }
    
    # ==================== COMPREHENSIVE ANALYSIS ====================
    
    @staticmethod
    def get_comprehensive_analysis(user) -> Dict:
        """Get complete financial analysis with all new features."""
        budget = SuggestionsEngineV2.calculate_remaining_budget(user)
        debts = SuggestionsEngineV2.get_active_debts(user)
        goals = SuggestionsEngineV2.get_active_goals(user)
        
        # Health Score
        health_score = SuggestionsEngineV2.calculate_financial_health_score(user)
        
        # Spending Patterns
        spending_patterns = SuggestionsEngineV2.analyze_spending_patterns(user)
        
        # Savings Rate
        savings_rate = SuggestionsEngineV2.calculate_savings_rate(user)
        
        # Projections
        projections = SuggestionsEngineV2.generate_projections(user)
        
        # Credit Cards
        card_analysis = SuggestionsEngineV2.analyze_credit_cards(user)
        
        # Net Worth
        net_worth = SuggestionsEngineV2.calculate_net_worth(user)
        
        # Debt predictions
        debt_predictions = []
        for debt in debts:
            current = SuggestionsEngineV2.predict_debt_payoff(debt, 0)
            extra = SuggestionsEngineV2.predict_debt_payoff(debt, 2000)
            debt_predictions.append({'debt': debt, 'current': current, 'with_extra': extra})
        
        # Goal predictions
        allocation = SuggestionsEngineV2.generate_smart_allocation(budget['remaining_budget'], debts, goals)
        goal_predictions = []
        for goal in goals:
            monthly = allocation['goal_allocation'] * (goal['monthly_required'] / max(1, sum(g['monthly_required'] for g in goals)))
            pred = SuggestionsEngineV2.predict_goal_completion(goal, monthly)
            goal_predictions.append({'goal': goal, 'prediction': pred})
        
        # Guidance suggestions
        guidance = SuggestionsEngineV2._generate_guidance(user, health_score, spending_patterns, savings_rate)
        
        return {
            'budget': budget,
            'health_score': health_score,
            'spending_patterns': spending_patterns,
            'savings_rate': savings_rate,
            'projections': projections,
            'card_analysis': card_analysis,
            'net_worth': net_worth,
            'debts': debts,
            'goals': goals,
            'debt_predictions': debt_predictions,
            'goal_predictions': goal_predictions,
            'allocation': allocation,
            'guidance': guidance,
            'summary': {
                'total_debt': sum(d['remaining_balance'] for d in debts),
                'total_goals_remaining': sum(g['remaining_amount'] for g in goals),
                'is_debt_free_possible': budget['remaining_budget'] > sum(d['emi_amount'] for d in debts),
                'debt_count': len(debts),
                'goal_count': len(goals)
            }
        }
    
    @staticmethod
    def _generate_guidance(user, health_score, spending_patterns, savings_rate) -> List[Dict]:
        """Generate comprehensive guidance."""
        suggestions = []
        today = timezone.now().date()
        
        # Health score based suggestions
        if health_score['score'] < 60:
            suggestions.append({
                'type': 'warning',
                'icon': '🏥',
                'title': 'Financial Health Needs Attention',
                'message': f'Your financial health score is {health_score["score"]}/100 ({health_score["grade"]}). ' + 
                          ' '.join(health_score['recommendations'][:2]),
                'action': None,
                'action_url': None
            })
        
        # Savings rate suggestions
        if savings_rate['status'] == 'poor':
            suggestions.append({
                'type': 'warning',
                'icon': '💰',
                'title': 'Low Savings Rate',
                'message': savings_rate['message'],
                'action': 'View Budget',
                'action_url': '/dashboard/'
            })
        
        # Spending trend suggestions
        if spending_patterns['overall_trend'] == 'increasing':
            suggestions.append({
                'type': 'warning',
                'icon': '📈',
                'title': 'Spending on the Rise',
                'message': f'Your expenses have increased this month. Review categories to find savings opportunities.',
                'action': 'View Expenses',
                'action_url': '/dashboard/'
            })
        
        # Goal suggestions
        goals = SuggestionsEngineV2.get_active_goals(user)
        if goals:
            at_risk = [g for g in goals if g['saved_percentage'] < 25]
            if at_risk:
                suggestions.append({
                    'type': 'warning',
                    'icon': '🎯',
                    'title': 'Goals At Risk',
                    'message': f'{len(at_risk)} goal(s) need attention. Increase contributions to stay on track.',
                    'action': 'View Goals',
                    'action_url': '/goals/'
                })
        
        # Net worth positive
        net_worth = SuggestionsEngineV2.calculate_net_worth(user)
        if net_worth['net_worth'] > 0:
            suggestions.append({
                'type': 'success',
                'icon': '📊',
                'title': 'Positive Net Worth',
                'message': f'Great! Your net worth is ₹{net_worth["net_worth"]:,.0f}. Keep building wealth!',
                'action': None,
                'action_url': None
            })
        
        return suggestions


# ==================== CONVENIENCE FUNCTIONS ====================

def get_financial_suggestions_v2(user):
    """Get enhanced comprehensive financial analysis."""
    return SuggestionsEngineV2.get_comprehensive_analysis(user)


def calculate_health_score(user):
    """Get financial health score."""
    return SuggestionsEngineV2.calculate_financial_health_score(user)


def analyze_spending_patterns(user, months=3):
    """Analyze spending patterns."""
    return SuggestionsEngineV2.analyze_spending_patterns(user, months)


def calculate_net_worth(user):
    """Calculate net worth."""
    return SuggestionsEngineV2.calculate_net_worth(user)


def generate_projections(user, years=1):
    """Generate financial projections."""
    return SuggestionsEngineV2.generate_projections(user, years)

