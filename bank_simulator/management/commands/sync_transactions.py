"""
Management command to sync bank transactions with expenses and income.
Run this command periodically (e.g., via cron) to sync transactions
that were inserted directly into the database (e.g., via phpMyAdmin).
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.contrib.auth.models import User

from bank_simulator.integration import (
    sync_all_bank_transactions,
    auto_sync_new_transactions,
    update_bank_account_balance,
    get_combined_monthly_summary,
    get_dashboard_analytics,
)
from bank_simulator.models import BankAccount


class Command(BaseCommand):
    help = 'Sync bank transactions with expenses and income records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Sync transactions for a specific user ID',
        )
        parser.add_argument(
            '--update-balances',
            action='store_true',
            help='Update bank account balances after syncing',
        )
        parser.add_argument(
            '--show-summary',
            action='store_true',
            help='Show monthly summary after syncing',
        )
        parser.add_argument(
            '--auto',
            action='store_true',
            help='Auto-sync new transactions (check and sync)',
        )
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear dashboard cache after syncing',
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        update_balances = options.get('update_balances', False)
        show_summary = options.get('show_summary', False)
        auto_sync = options.get('auto', False)
        clear_cache = options.get('clear_cache', True)  # Default to True
        
        if auto_sync:
            # Auto-sync mode: check for new transactions
            self.stdout.write('Running auto-sync for new transactions...')
            results = auto_sync_new_transactions()
            
            self.stdout.write(self.style.SUCCESS(
                f"\n✓ Auto-sync complete:"
            ))
            self.stdout.write(f"  - Transactions checked: {results['transactions_checked']}")
            self.stdout.write(f"  - New expenses created: {results['new_expenses']}")
            self.stdout.write(f"  - New income created: {results['new_income']}")
            
            if results['errors']:
                self.stdout.write(self.style.WARNING(f"  - Errors: {len(results['errors'])}"))
                for error in results['errors'][:5]:  # Show first 5 errors
                    self.stdout.write(self.style.ERROR(f"    {error}"))
            
            if update_balances:
                self._update_all_balances()
            
            if clear_cache:
                self._clear_dashboard_cache()
                
            return
        
        if user_id:
            # Sync for specific user
            try:
                user = User.objects.get(id=user_id)
                self.stdout.write(f'Syncing transactions for user: {user.username}')
                
                results = sync_all_bank_transactions(user=user)
                
                self.stdout.write(self.style.SUCCESS(
                    f"\n✓ Sync complete for {user.username}:"
                ))
                self.stdout.write(f"  - Total transactions: {results['total']}")
                self.stdout.write(f"  - Synced: {results['synced']}")
                self.stdout.write(f"  - Failed: {results['failed']}")
                
                if results['errors']:
                    self.stdout.write(self.style.WARNING("Errors:"))
                    for error in results['errors'][:5]:
                        self.stdout.write(self.style.ERROR(f"    {error}"))
                
                if update_balances:
                    balance = update_bank_account_balance(user)
                    self.stdout.write(self.style.SUCCESS(
                        f"\n✓ Bank balance updated: ₹{balance}"
                    ))
                
                if clear_cache:
                    self._clear_user_cache(user.id)
                
                if show_summary:
                    self._show_user_summary(user)
                    
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User with ID {user_id} not found"))
                return
        else:
            # Sync for all users
            self.stdout.write('Syncing transactions for all users...')
            results = sync_all_bank_transactions()
            
            self.stdout.write(self.style.SUCCESS(
                f"\n✓ Sync complete:"
            ))
            self.stdout.write(f"  - Total transactions: {results['total']}")
            self.stdout.write(f"  - Synced: {results['synced']}")
            self.stdout.write(f"  - Failed: {results['failed']}")
            
            if results['errors']:
                self.stdout.write(self.style.WARNING("Errors:"))
                for error in results['errors'][:5]:
                    self.stdout.write(self.style.ERROR(f"    {error}"))
            
            if update_balances:
                self._update_all_balances()
            
            if clear_cache:
                self._clear_dashboard_cache()
    
    def _update_all_balances(self):
        """Update balances for all bank accounts."""
        self.stdout.write('\nUpdating bank account balances...')
        accounts = BankAccount.objects.all()
        
        for account in accounts:
            balance = update_bank_account_balance(account.user)
            self.stdout.write(f"  - {account.user.username}: ₹{balance}")
        
        self.stdout.write(self.style.SUCCESS(f"✓ Updated {accounts.count()} bank accounts"))
    
    def _clear_dashboard_cache(self):
        """Clear all dashboard cache for all users."""
        self.stdout.write('\nClearing dashboard cache...')
        cache.clear()
        self.stdout.write(self.style.SUCCESS("✓ Dashboard cache cleared"))
    
    def _clear_user_cache(self, user_id):
        """Clear dashboard cache for a specific user."""
        # Clear cache keys related to this user
        cache.delete(f'dashboard_{user_id}_financial_health_month')
        cache.delete(f'dashboard_{user_id}_budget_utilization')
        cache.delete(f'dashboard_{user_id}_spending_vs_income')
        cache.delete(f'dashboard_{user_id}_category_breakdown_1')
        cache.delete(f'dashboard_{user_id}_trend_30')
        cache.delete(f'dashboard_{user_id}_ai_insights')
        self.stdout.write(self.style.SUCCESS(f"✓ Cache cleared for user {user_id}"))
    
    def _show_user_summary(self, user):
        """Show monthly summary for a user."""
        self.stdout.write(f'\n--- Monthly Summary for {user.username} ---')
        
        summary = get_combined_monthly_summary(user)
        
        self.stdout.write(f"Period: {summary['month']}/{summary['year']}")
        self.stdout.write(f"Total Income: ₹{summary['income']['total_income']}")
        self.stdout.write(f"Total Expenses: ₹{summary['expenses']['total_expenses']}")
        self.stdout.write(f"Net Savings: ₹{summary['net_savings']}")
        self.stdout.write(f"Savings Rate: {summary['savings_rate']:.1f}%")
        
        # Show top categories
        self.stdout.write('\nTop Expense Categories:')
        for cat in summary['expenses']['by_category'][:5]:
            self.stdout.write(f"  - {cat['category']}: ₹{cat['total']}")

