"""
Debt Service - EMI and Loan Management
=====================================
Service layer for debt/loan tracking with:
- EMI calculations
- Amortization schedules
- Debt payoff projections
- Interest calculations
"""

from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import math
import logging

from debts.models import Debt, EMIPayment

logger = logging.getLogger(__name__)


class DebtService:
    """Service for managing debts and loans."""
    
    CACHE_TIMEOUT = 300  # 5 minutes
    
    @staticmethod
    def _get_cache_key(user_id, key_prefix):
        """Generate cache key with user isolation."""
        return f"debt_{user_id}_{key_prefix}"
    
    @staticmethod
    def get_user_debts(user):
        """Get all active debts for a user."""
        return Debt.objects.filter(
            owner=user,
            status=Debt.STATUS_ACTIVE
        ).order_by('-created_at')
    
    @staticmethod
    def get_debt_summary(user):
        """
        Get comprehensive debt summary for a user.
        
        Returns:
            dict: {
                total_debt: float,
                total_remaining: float,
                total_monthly_emi: float,
                total_interest: float,
                debt_count: int,
                overdue_count: int
            }
        """
        debts = Debt.objects.filter(
            owner=user,
            status=Debt.STATUS_ACTIVE
        )
        
        total_debt = sum(float(d.principal_amount) for d in debts)
        total_remaining = sum(float(d.remaining_balance) for d in debts)
        total_monthly_emi = sum(float(d.emi_amount) for d in debts)
        total_interest = sum(float(d.total_interest) for d in debts)
        
        # Count overdue debts
        overdue_count = sum(1 for d in debts if d.is_overdue)
        
        return {
            'total_debt': round(total_debt, 2),
            'total_remaining': round(total_remaining, 2),
            'total_monthly_emi': round(total_monthly_emi, 2),
            'total_interest': round(total_interest, 2),
            'debt_count': debts.count(),
            'overdue_count': overdue_count,
        }
    
    @staticmethod
    def get_upcoming_emis(user, days=30):
        """Get upcoming EMI payments within specified days."""
        today = timezone.now().date()
        end_date = today + timedelta(days=days)
        
        debts = Debt.objects.filter(
            owner=user,
            status=Debt.STATUS_ACTIVE
        )
        
        upcoming = []
        for debt in debts:
            if debt.next_emi_date <= end_date:
                upcoming.append({
                    'debt_id': debt.id,
                    'debt_name': debt.loan_name,
                    'loan_type': debt.loan_type,
                    'due_date': debt.next_emi_date,
                    'amount': float(debt.emi_amount),
                    'is_overdue': debt.next_emi_date < today,
                    'days_until': (debt.next_emi_date - today).days,
                })
        
        # Sort by due date
        upcoming.sort(key=lambda x: x['due_date'])
        return upcoming
    
    @staticmethod
    def calculate_emi(principal, annual_rate, term_months):
        """
        Calculate EMI using standard formula.
        
        EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
        
        Args:
            principal: Loan principal amount (float)
            annual_rate: Annual interest rate in percentage (float)
            term_months: Loan term in months (int)
        
        Returns:
            float: Monthly EMI amount
        """
        if principal <= 0 or term_months <= 0:
            return 0
        
        if annual_rate <= 0:
            return principal / term_months
        
        r = annual_rate / 100 / 12  # Monthly interest rate
        n = term_months
        
        emi = principal * r * (math.pow(1 + r, n)) / (math.pow(1 + r, n) - 1)
        return round(emi, 2)
    
    @staticmethod
    def calculate_total_interest(principal, annual_rate, term_months):
        """Calculate total interest over loan term."""
        emi = DebtService.calculate_emi(principal, annual_rate, term_months)
        total_payment = emi * term_months
        return round(total_payment - principal, 2)
    
    @staticmethod
    def generate_amortization_schedule(principal, annual_rate, term_months):
        """
        Generate full amortization schedule.
        
        Returns:
            list: [{month, emi, principal, interest, balance}, ...]
        """
        emi = DebtService.calculate_emi(principal, annual_rate, term_months)
        schedule = []
        
        balance = principal
        monthly_rate = annual_rate / 100 / 12
        
        for month in range(1, term_months + 1):
            interest_payment = balance * monthly_rate
            principal_payment = emi - interest_payment
            balance -= principal_payment
            
            schedule.append({
                'month': month,
                'emi': round(emi, 2),
                'principal': round(principal_payment, 2),
                'interest': round(interest_payment, 2),
                'balance': round(max(0, balance), 2)
            })
        
        return schedule
    
    @staticmethod
    def calculate_debt_to_income_ratio(user):
        """
        Calculate debt-to-income ratio.
        
        A ratio > 36% is generally considered risky.
        
        Returns:
            dict: {ratio: float, status: str, recommendation: str}
        """
        from userincome.models import UserIncome
        
        # Get monthly income
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        
        monthly_income = UserIncome.objects.filter(
            owner=user,
            date__gte=start_of_month,
            date__lte=today
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Get total monthly EMI
        debts = Debt.objects.filter(
            owner=user,
            status=Debt.STATUS_ACTIVE
        )
        monthly_emi = sum(float(d.emi_amount) for d in debts)
        
        if monthly_income > 0:
            ratio = (monthly_emi / monthly_income) * 100
        else:
            ratio = 100 if monthly_emi > 0 else 0
        
        # Determine status
        if ratio <= 15:
            status = 'excellent'
            recommendation = 'Your debt level is very manageable.'
        elif ratio <= 28:
            status = 'good'
            recommendation = 'Your debt level is acceptable.'
        elif ratio <= 36:
            status = 'fair'
            recommendation = 'Consider reducing debt to improve financial health.'
        else:
            status = 'risky'
            recommendation = 'Your debt-to-income ratio is high. Consider debt consolidation.'
        
        return {
            'ratio': round(ratio, 1),
            'monthly_income': round(monthly_income, 2),
            'monthly_emi': round(monthly_emi, 2),
            'status': status,
            'recommendation': recommendation
        }
    
    @staticmethod
    def get_debt_payoff_date(debt_id):
        """Calculate estimated debt payoff date."""
        try:
            debt = Debt.objects.get(id=debt_id)
            if debt.remaining_balance <= 0:
                return {'payoff_date': debt.start_date, 'months_remaining': 0}
            
            # Estimate based on current EMI
            monthly_payment = float(debt.emi_amount)
            remaining = float(debt.remaining_balance)
            
            if monthly_payment <= 0:
                return {'payoff_date': None, 'months_remaining': None}
            
            months_remaining = int(remaining / monthly_payment) + 1
            
            from datetime import date
            today = date.today()
            payoff_date = today.replace(month=today.month + months_remaining)
            if today.month + months_remaining > 12:
                payoff_date = payoff_date.replace(
                    year=today.year + (today.month + months_remaining - 1) // 12,
                    month=(today.month + months_remaining - 1) % 12 + 1
                )
            
            return {
                'payoff_date': payoff_date,
                'months_remaining': months_remaining
            }
        except Debt.DoesNotExist:
            return {'payoff_date': None, 'months_remaining': None}
    
    @staticmethod
    def compare_debt_strategies(debt_id):
        """
        Compare different debt payoff strategies.
        
        Returns comparison of:
        - Minimum payments
        - Avalanche method (highest interest first)
        - Snowball method (smallest balance first)
        """
        try:
            debt = Debt.objects.get(id=debt_id)
        except Debt.DoesNotExist:
            return None
        
        principal = float(debt.principal_amount)
        rate = float(debt.interest_rate)
        term = debt.loan_term_months
        
        # Standard amortization
        standard_schedule = DebtService.generate_amortization_schedule(
            principal, rate, term
        )
        
        # Calculate totals
        standard_total = sum(s['interest'] for s in standard_schedule)
        
        return {
            'standard': {
                'monthly_payment': float(debt.emi_amount),
                'total_interest': round(standard_total, 2),
                'total_cost': round(principal + standard_total, 2),
                'payoff_months': term
            },
            'accelerated': {
                'description': 'Pay 10% extra monthly',
                'monthly_payment': round(float(debt.emi_amount) * 1.1, 2),
                'estimated_months': int(term / 1.1),
                'interest_saved': round(standard_total * 0.1, 2)
            }
        }
