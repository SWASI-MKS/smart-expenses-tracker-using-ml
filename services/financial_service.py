"""
Centralized Financial Service Layer
====================================
This module provides a single source of truth for all financial calculations.
All functions use Django ORM aggregations to calculate values directly from the database.
No cached totals - always recalculate from database.

Functions:
- calculate_total_income(user) -> float
- calculate_total_expenses(user) -> float
- calculate_bank_balance(user) -> Decimal
- calculate_net_worth(user) -> dict
- calculate_monthly_summary(user) -> dict
- calculate_card_spending(user) -> dict
"""

from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import ExtractMonth, ExtractYear
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from typing import Dict, Optional

from expenses.models import Expense, ExpenseLimit
from userincome.models import UserIncome
from bank_simulator.models import BankAccount, BankTransaction, Card, CardTransaction


class FinancialService:
    """
    Centralized financial calculations using Django ORM.
    All totals are calculated dynamically from the database.
    """
    
    @staticmethod
    def calculate_total_income(user, start_date=None, end_date=None) -> float:
        """
        Calculate total income using Django ORM Sum aggregation.
        
        Args:
            user: The user object
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Total income as float
        """
        queryset = UserIncome.objects.filter(owner=user)
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        result = queryset.aggregate(total=Sum('amount'))
        return float(result['total'] or 0)
    
    @staticmethod
    def calculate_total_expenses(user, start_date=None, end_date=None) -> float:
        """
        Calculate total expenses using Django ORM Sum aggregation.
        
        Args:
            user: The user object
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Total expenses as float
        """
        queryset = Expense.objects.filter(owner=user)
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        result = queryset.aggregate(total=Sum('amount'))
        return float(result['total'] or 0)
    
    @staticmethod
    def calculate_bank_balance(user) -> Decimal:
        """
        Calculate current bank balance from BankAccount model.
        
        Args:
            user: The user object
            
        Returns:
            Bank balance as Decimal
        """
        try:
            account = BankAccount.objects.get(user=user)
            return account.balance
        except BankAccount.DoesNotExist:
            return Decimal('0.00')
    
    @staticmethod
    def calculate_card_spending(user, card_id=None) -> Dict:
        """
        Calculate card spending using Django ORM aggregation.
        
        Args:
            user: The user object
            card_id: Optional specific card ID
            
        Returns:
            Dict with total_spending and card_details
        """
        queryset = CardTransaction.objects.filter(user=user)
        
        if card_id:
            queryset = queryset.filter(card_id=card_id)
        
        total = queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Get spending by card
        by_card = queryset.values('card__card_name').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        return {
            'total_spending': float(total),
            'by_card': list(by_card),
            'transaction_count': queryset.count()
        }
    
    @staticmethod
    def calculate_net_worth(user) -> Dict:
        """
        Calculate comprehensive net worth.
        
        Formula: Total Income - Total Expenses - Card Spending
        
        Args:
            user: The user object
            
        Returns:
            Dict with all financial totals
        """
        total_income = FinancialService.calculate_total_income(user)
        total_expenses = FinancialService.calculate_total_expenses(user)
        card_spending_data = FinancialService.calculate_card_spending(user)
        card_spending = card_spending_data['total_spending']
        bank_balance = float(FinancialService.calculate_bank_balance(user))
        
        # Net worth = Bank Balance + Total Income - Total Expenses - Card Spending
        # (This represents: what's in bank + what you earned - what you spent)
        net_worth = bank_balance + total_income - total_expenses - card_spending
        
        return {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'card_spending': card_spending,
            'bank_balance': bank_balance,
            'net_worth': net_worth,
            # Alternative net worth (bank balance minus card debt)
            'liquid_net_worth': bank_balance - card_spending
        }
    
    @staticmethod
    def calculate_monthly_summary(user, year=None, month=None) -> Dict:
        """
        Calculate monthly summary using Django ORM aggregations.
        
        Args:
            user: The user object
            year: Optional year (defaults to current year)
            month: Optional month (defaults to current month)
            
        Returns:
            Dict with monthly totals
        """
        today = timezone.now().date()
        if year is None:
            year = today.year
        if month is None:
            month = today.month
        
        # Monthly income
        monthly_income = UserIncome.objects.filter(
            owner=user,
            date__year=year,
            date__month=month
        ).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        # Monthly expenses
        monthly_expenses = Expense.objects.filter(
            owner=user,
            date__year=year,
            date__month=month
        ).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        # Monthly card spending
        monthly_card = CardTransaction.objects.filter(
            user=user,
            transaction_date__year=year,
            transaction_date__month=month
        ).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        # Monthly bank transactions
        monthly_bank = BankTransaction.objects.filter(
            user=user,
            created_at__year=year,
            created_at__month=month
        ).aggregate(
            credits=Sum('amount', filter=Q(transaction_type='CREDIT')),
            debits=Sum('amount', filter=Q(transaction_type='DEBIT'))
        )
        
        income_total = float(monthly_income['total'] or 0)
        expenses_total = float(monthly_expenses['total'] or 0)
        card_total = float(monthly_card['total'] or 0)
        
        return {
            'year': year,
            'month': month,
            'income': {
                'total': income_total,
                'count': monthly_income['count'] or 0
            },
            'expenses': {
                'total': expenses_total,
                'count': monthly_expenses['count'] or 0
            },
            'card_spending': {
                'total': card_total,
                'count': monthly_card['count'] or 0
            },
            'bank_credits': float(monthly_bank.get('credits') or 0),
            'bank_debits': float(monthly_bank.get('debits') or 0),
            'net_savings': income_total - expenses_total,
            'total_outflow': expenses_total + card_total
        }
    
    @staticmethod
    def calculate_daily_summary(user, date=None) -> Dict:
        """
        Calculate daily summary for a specific date.
        
        Args:
            user: The user object
            date: Optional date (defaults to today)
            
        Returns:
            Dict with daily totals
        """
        if date is None:
            date = timezone.now().date()
        
        daily_income = UserIncome.objects.filter(
            owner=user,
            date=date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        daily_expenses = Expense.objects.filter(
            owner=user,
            date=date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        daily_card = CardTransaction.objects.filter(
            user=user,
            transaction_date=date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return {
            'date': date,
            'income': float(daily_income),
            'expenses': float(daily_expenses),
            'card_spending': float(daily_card),
            'total_outflow': float(daily_expenses) + float(daily_card)
        }
    
    @staticmethod
    def calculate_weekly_summary(user) -> Dict:
        """
        Calculate weekly summary (last 7 days).
        
        Args:
            user: The user object
            
        Returns:
            Dict with weekly totals
        """
        today = timezone.now().date()
        week_start = today - timedelta(days=6)
        
        weekly_income = UserIncome.objects.filter(
            owner=user,
            date__gte=week_start,
            date__lte=today
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        weekly_expenses = Expense.objects.filter(
            owner=user,
            date__gte=week_start,
            date__lte=today
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return {
            'start_date': week_start,
            'end_date': today,
            'income': float(weekly_income),
            'expenses': float(weekly_expenses),
            'net': float(weekly_income) - float(weekly_expenses)
        }
    
    @staticmethod
    def calculate_yearly_summary(user, year=None) -> Dict:
        """
        Calculate yearly summary.
        
        Args:
            user: The user object
            year: Optional year (defaults to current year)
            
        Returns:
            Dict with yearly totals
        """
        if year is None:
            year = timezone.now().year
        
        yearly_income = UserIncome.objects.filter(
            owner=user,
            date__year=year
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        yearly_expenses = Expense.objects.filter(
            owner=user,
            date__year=year
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return {
            'year': year,
            'income': float(yearly_income),
            'expenses': float(yearly_expenses),
            'net': float(yearly_income) - float(yearly_expenses)
        }
    
    @staticmethod
    def get_category_breakdown(user, start_date=None, end_date=None, limit=10) -> Dict:
        """
        Get expense breakdown by category using annotate.
        
        Args:
            user: The user object
            start_date: Optional start date
            end_date: Optional end date
            limit: Number of top categories to return
            
        Returns:
            Dict with category totals
        """
        queryset = Expense.objects.filter(owner=user)
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        categories = queryset.values('category').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')[:limit]
        
        total = sum(c['total'] for c in categories)
        
        return {
            'categories': [
                {
                    'name': c['category'],
                    'amount': float(c['total']),
                    'count': c['count'],
                    'percentage': round((c['total'] / total * 100) if total > 0 else 0, 1)
                }
                for c in categories
            ],
            'total': float(total)
        }
    
    @staticmethod
    def get_income_source_breakdown(user, start_date=None, end_date=None) -> Dict:
        """
        Get income breakdown by source using annotate.
        
        Args:
            user: The user object
            start_date: Optional start date
            end_date: Optional end date
            
        Returns:
            Dict with source totals
        """
        queryset = UserIncome.objects.filter(owner=user)
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        sources = queryset.values('source').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        total = sum(s['total'] for s in sources)
        
        return {
            'sources': [
                {
                    'name': s['source'],
                    'amount': float(s['total']),
                    'count': s['count'],
                    'percentage': round((s['total'] / total * 100) if total > 0 else 0, 1)
                }
                for s in sources
            ],
            'total': float(total)
        }


# Convenience functions for direct import
def calculate_total_income(user, start_date=None, end_date=None) -> float:
    """Convenience function for total income calculation."""
    return FinancialService.calculate_total_income(user, start_date, end_date)


def calculate_total_expenses(user, start_date=None, end_date=None) -> float:
    """Convenience function for total expenses calculation."""
    return FinancialService.calculate_total_expenses(user, start_date, end_date)


def calculate_bank_balance(user) -> Decimal:
    """Convenience function for bank balance calculation."""
    return FinancialService.calculate_bank_balance(user)


def calculate_net_worth(user) -> Dict:
    """Convenience function for net worth calculation."""
    return FinancialService.calculate_net_worth(user)


def calculate_monthly_summary(user, year=None, month=None) -> Dict:
    """Convenience function for monthly summary calculation."""
    return FinancialService.calculate_monthly_summary(user, year, month)


def calculate_card_spending(user, card_id=None) -> Dict:
    """Convenience function for card spending calculation."""
    return FinancialService.calculate_card_spending(user, card_id)

