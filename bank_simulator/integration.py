"""
Bank Transaction Integration Service
Automatically syncs bank transactions with expenses and income records.
This module works even when data is inserted directly via phpMyAdmin.
"""
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone

from expenses.models import Expense, Category
from userincome.models import UserIncome, Source
from .models import BankAccount, BankTransaction, CardTransaction, Card
from .services import categorize_transaction, calculate_net_worth


# =====================================================
# CORE INTEGRATION FUNCTIONS
# =====================================================

def sync_bank_transaction_to_expense_income(bank_transaction: BankTransaction) -> Tuple[bool, str]:
    """
    Sync a single bank transaction to Expense or Income.
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Normalize transaction type (handle both uppercase and lowercase)
        tx_type = bank_transaction.transaction_type.upper() if bank_transaction.transaction_type else ''
        
        # Check if already synced (by checking description and amount)
        existing_expense = Expense.objects.filter(
            owner=bank_transaction.user,
            amount=float(bank_transaction.amount),
            description=bank_transaction.description,
            payment_method='BANK'
        ).exists()
        
        existing_income = UserIncome.objects.filter(
            owner=bank_transaction.user,
            amount=float(bank_transaction.amount),
            description=bank_transaction.description,
            payment_method='BANK'
        ).exists()
        
        if existing_expense or existing_income:
            return True, "Transaction already synced"
        
        if tx_type == 'DEBIT':
            # Create expense
            category = categorize_transaction(bank_transaction.description)
            Expense.objects.create(
                owner=bank_transaction.user,
                amount=float(bank_transaction.amount),
                description=bank_transaction.description,
                category=category,
                date=bank_transaction.created_at.date(),
                payment_method='BANK',
                notes=f"Auto-synced from Bank Transaction #{bank_transaction.id}"
            )
            return True, "Created expense from debit transaction"
        
        elif tx_type == 'CREDIT':
            # Create income
            UserIncome.objects.create(
                owner=bank_transaction.user,
                amount=float(bank_transaction.amount),
                description=bank_transaction.description,
                source='Bank Transfer',
                date=bank_transaction.created_at.date(),
                payment_method='BANK',
                is_verified=True,
                notes=f"Auto-synced from Bank Transaction #{bank_transaction.id}"
            )
            return True, "Created income from credit transaction"
        
        return False, f"Unknown transaction type: {tx_type}"
    
    except Exception as e:
        return False, f"Error syncing transaction: {str(e)}"


def sync_all_bank_transactions(user=None) -> Dict:
    """
    Sync all bank transactions that haven't been synced to expenses/income.
    
    Args:
        user: Optional user to filter transactions syncs all. If None, users.
    
    Returns:
        Dict with sync results
    """
    if user:
        transactions = BankTransaction.objects.filter(user=user)
    else:
        transactions = BankTransaction.objects.all()
    
    results = {
        'total': transactions.count(),
        'synced': 0,
        'failed': 0,
        'errors': []
    }
    
    for tx in transactions:
        success, message = sync_bank_transaction_to_expense_income(tx)
        if success:
            results['synced'] += 1
        else:
            results['failed'] += 1
            results['errors'].append(f"Tx #{tx.id}: {message}")
    
    return results


def get_unprocessed_transactions(user=None) -> List[BankTransaction]:
    """
    Get bank transactions that haven't been synced to expenses/income.
    """
    if user:
        return BankTransaction.objects.filter(user=user)
    return BankTransaction.objects.all()


# =====================================================
# MONTHLY SUMMARY QUERIES
# =====================================================

def get_monthly_income_summary(user, year=None, month=None) -> Dict:
    """
    Get monthly income summary for a user.
    """
    if year is None:
        year = timezone.now().year
    if month is None:
        month = timezone.now().month
    
    # Get all income for the month
    income = UserIncome.objects.filter(
        owner=user,
        date__year=year,
        date__month=month
    )
    
    total_income = income.aggregate(total=Sum('amount'))['total'] or 0
    
    # Breakdown by source
    by_source = income.values('source').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Breakdown by payment method
    by_payment = income.values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Bank transfers (from synced transactions)
    bank_income = income.filter(payment_method='BANK').aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    return {
        'year': year,
        'month': month,
        'total_income': total_income,
        'transaction_count': income.count(),
        'by_source': list(by_source),
        'by_payment_method': list(by_payment),
        'bank_transfer_income': bank_income,
    }


def get_monthly_expense_summary(user, year=None, month=None) -> Dict:
    """
    Get monthly expense summary for a user.
    """
    if year is None:
        year = timezone.now().year
    if month is None:
        month = timezone.now().month
    
    # Get all expenses for the month
    expenses = Expense.objects.filter(
        owner=user,
        date__year=year,
        date__month=month
    )
    
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
    
    # Breakdown by category
    by_category = expenses.values('category').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Breakdown by payment method
    by_payment = expenses.values('payment_method').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Bank transfers (from synced transactions)
    bank_expenses = expenses.filter(payment_method='BANK').aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    return {
        'year': year,
        'month': month,
        'total_expenses': total_expenses,
        'transaction_count': expenses.count(),
        'by_category': list(by_category),
        'by_payment_method': list(by_payment),
        'bank_transfer_expenses': bank_expenses,
    }


def get_combined_monthly_summary(user, year=None, month=None) -> Dict:
    """
    Get combined monthly summary (income + expenses + net).
    """
    income_summary = get_monthly_income_summary(user, year, month)
    expense_summary = get_monthly_expense_summary(user, year, month)
    
    return {
        'year': year,
        'month': month,
        'income': income_summary,
        'expenses': expense_summary,
        'net_savings': income_summary['total_income'] - expense_summary['total_expenses'],
        'savings_rate': (
            (income_summary['total_income'] - expense_summary['total_income']) / 
            income_summary['total_income'] * 100 
            if income_summary['total_income'] > 0 else 0
        )
    }


# =====================================================
# BANK ACCOUNT BALANCE UPDATE
# =====================================================

def update_bank_account_balance(user) -> Decimal:
    """
    Update bank account balance based on all transactions.
    """
    try:
        bank_account = BankAccount.objects.get(user=user)
    except BankAccount.DoesNotExist:
        # Create bank account if doesn't exist
        bank_account = BankAccount.objects.create(
            user=user,
            account_number=f"ACC-{user.id}-{timezone.now().strftime('%Y%m%d')}",
            balance=0
        )
    
    # Calculate balance from transactions
    credits = BankTransaction.objects.filter(
        user=user,
        transaction_type='CREDIT'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    debits = BankTransaction.objects.filter(
        user=user,
        transaction_type='DEBIT'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    new_balance = credits - debits
    bank_account.balance = new_balance
    bank_account.save()
    
    return new_balance


def get_bank_balance(user) -> Decimal:
    """
    Get current bank account balance.
    """
    try:
        bank_account = BankAccount.objects.get(user=user)
        return bank_account.balance
    except BankAccount.DoesNotExist:
        return Decimal('0.00')


# =====================================================
# NET WORTH CALCULATION (ENHANCED)
# =====================================================

def calculate_total_net_worth(user) -> Dict:
    """
    Calculate comprehensive net worth including all accounts.
    """
    # Bank balance
    bank_balance = get_bank_balance(user)
    
    # Income total (all time)
    total_income = UserIncome.objects.filter(
        owner=user
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Expense total (all time)
    total_expenses = Expense.objects.filter(
        owner=user
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Card spending
    card_spending = CardTransaction.objects.filter(
        user=user
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Credit card outstanding
    credit_cards = Card.objects.filter(user=user, card_type='CREDIT')
    credit_outstanding = 0
    for card in credit_cards:
        spent = card.card_transactions.aggregate(
            total=Sum('amount')
        )['total'] or 0
        credit_outstanding += spent
    
    return {
        'bank_balance': bank_balance,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'card_spending': card_spending,
        'credit_outstanding': credit_outstanding,
        'net_worth': total_income - total_expenses - credit_outstanding,
    }


# =====================================================
# CATEGORY TOTALS
# =====================================================

def get_category_totals(user, year=None, month=None) -> List[Dict]:
    """
    Get expense totals by category for a given period.
    """
    if year is None:
        year = timezone.now().year
    if month is None:
        month = timezone.now().month
    
    expenses = Expense.objects.filter(
        owner=user,
        date__year=year,
        date__month=month
    )
    
    category_totals = expenses.values('category').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Calculate percentages
    total_amount = sum(item['total'] for item in category_totals)
    
    result = []
    for item in category_totals:
        percentage = (item['total'] / total_amount * 100) if total_amount > 0 else 0
        result.append({
            'category': item['category'],
            'total': item['total'],
            'count': item['count'],
            'percentage': round(percentage, 2)
        })
    
    return result


# =====================================================
# DASHBOARD ANALYTICS
# =====================================================

def get_dashboard_analytics(user, period='month') -> Dict:
    """
    Get analytics data for dashboard.
    """
    from datetime import timedelta
    
    today = timezone.now().date()
    
    if period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'month':
        start_date = today.replace(day=1)
    elif period == 'quarter':
        start_date = today - timedelta(days=90)
    elif period == 'year':
        start_date = today.replace(month=1, day=1)
    else:
        start_date = today.replace(day=1)
    
    # Income in period
    period_income = UserIncome.objects.filter(
        owner=user,
        date__gte=start_date
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Expenses in period
    period_expenses = Expense.objects.filter(
        owner=user,
        date__gte=start_date
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Bank transactions in period
    bank_credits = BankTransaction.objects.filter(
        user=user,
        transaction_type='CREDIT',
        created_at__date__gte=start_date
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    bank_debits = BankTransaction.objects.filter(
        user=user,
        transaction_type='DEBIT',
        created_at__date__gte=start_date
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Net worth
    net_worth = calculate_total_net_worth(user)
    
    return {
        'period': period,
        'start_date': start_date,
        'income': period_income,
        'expenses': period_expenses,
        'net_savings': period_income - period_expenses,
        'bank_credits': bank_credits,
        'bank_debits': bank_debits,
        'net_worth': net_worth['net_worth'],
        'bank_balance': net_worth['bank_balance'],
    }


# =====================================================
# TRANSACTION HISTORY
# =====================================================

def get_combined_transaction_history(user, limit=50) -> List[Dict]:
    """
    Get combined transaction history (bank + expenses + income).
    """
    from django.db.models import Case, When, Value, CharField
    
    # Get recent bank transactions
    bank_txs = BankTransaction.objects.filter(
        user=user
    ).order_by('-created_at')[:limit]
    
    transactions = []
    
    for tx in bank_txs:
        tx_type = 'income' if tx.transaction_type == 'CREDIT' else 'expense'
        transactions.append({
            'date': tx.created_at,
            'description': tx.description,
            'amount': float(tx.amount),
            'type': tx_type,
            'source': 'Bank',
            'category': categorize_transaction(tx.description) if tx_type == 'expense' else 'Income',
            'balance_after': float(tx.balance_after),
        })
    
    # Sort by date (most recent first)
    transactions.sort(key=lambda x: x['date'], reverse=True)
    
    return transactions[:limit]


# =====================================================
# AUTO-SYNC UTILITY
# =====================================================

def auto_sync_new_transactions() -> Dict:
    """
    Check for new transactions and sync them.
    This function can be called by a cron job or management command.
    """
    results = {
        'transactions_checked': 0,
        'new_expenses': 0,
        'new_income': 0,
        'errors': []
    }
    
    # Get all users with bank accounts
    users_with_bank = BankAccount.objects.values_list('user', flat=True).distinct()
    
    for user_id in users_with_bank:
        from django.contrib.auth.models import User
        try:
            user = User.objects.get(id=user_id)
            transactions = BankTransaction.objects.filter(user=user).order_by('-created_at')[:10]
            
            for tx in transactions:
                results['transactions_checked'] += 1
                success, message = sync_bank_transaction_to_expense_income(tx)
                
                if success and 'Created' in message:
                    if 'expense' in message.lower():
                        results['new_expenses'] += 1
                    else:
                        results['new_income'] += 1
                
                if not success:
                    results['errors'].append(message)
        
        except Exception as e:
            results['errors'].append(f"Error processing user {user_id}: {str(e)}")
    
    return results

