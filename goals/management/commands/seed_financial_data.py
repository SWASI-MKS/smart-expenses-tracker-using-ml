from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import random

from expenses.models import Expense, Category
from userincome.models import UserIncome
from debts.models import Debt
from goals.models import Goal
from bank_simulator.models import BankAccount, Budget


class Command(BaseCommand):
    help = 'Seed test financial data for a test user'

    def handle(self, *args, **options):
        # Create test user if not exists
        test_user, created = User.objects.get_or_create(
            username='testuser',
            defaults={'email': 'test@example.com', 'is_staff': True}
        )
        if created:
            test_user.set_password('testpass123')
            test_user.save()
            self.stdout.write(self.style.SUCCESS('Created test user: testuser/testpass123'))

        # Create bank account
        BankAccount.objects.update_or_create(
            user=test_user,
            defaults={
                'account_number': '1234567890',
                'balance': Decimal('25000.00')
            }
        )

        # Create 3 months income (Salary + Freelance)
        months_back = 3
        for i in range(months_back):
            month_date = timezone.now().date() - relativedelta(months=i)
            UserIncome.objects.create(
                owner=test_user,
                source='Salary',
                description='Monthly salary',
                amount=Decimal('75000.00'),
                date=month_date,
                is_recurring=True
            )
            UserIncome.objects.create(
                owner=test_user,
                source='Freelance',
                description='Project work',
                amount=Decimal('15000.00'),
                date=month_date
            )

        # Create expenses across categories
        categories = ['Food', 'Transport', 'Shopping', 'Entertainment', 'Utilities', 'Rent']
        for i in range(months_back):
            month_date = timezone.now().date() - relativedelta(months=i)
            for cat in categories:
                Expense.objects.create(
                    owner=test_user,
                    category=cat,
                    description=f'{cat} expense',
                    amount=Decimal(str(random.randint(2000, 8000))),
                    date=month_date
                )

        # Create 2 debts
        Debt.objects.update_or_create(
            owner=test_user,
            loan_name='Credit Card',
            defaults={
                'loan_type': 'credit_card',
                'lender_name': 'HDFC Bank',
                'remaining_balance': Decimal('45000.00'),
                'emi_amount': Decimal('5000.00'),
                'interest_rate': 18.5,
                'status': 'ACTIVE'
            }
        )
        Debt.objects.update_or_create(
            owner=test_user,
            loan_name='Personal Loan',
            defaults={
                'loan_type': 'personal_loan',
                'lender_name': 'SBI',
                'remaining_balance': Decimal('120000.00'),
                'emi_amount': Decimal('12000.00'),
                'interest_rate': 12.0,
                'status': 'ACTIVE'
            }
        )

        # Create 2 goals
        Goal.objects.update_or_create(
            owner=test_user,
            name='Emergency Fund',
            defaults={
                'amount_to_save': Decimal('150000.00'),
                'current_saved_amount': Decimal('45000.00'),
                'start_date': timezone.now().date() - timedelta(days=90),
                'end_date': timezone.now().date() + timedelta(days=180),
                'status': 'ACTIVE'
            }
        )
        Goal.objects.update_or_create(
            owner=test_user,
            name='Vacation Fund',
            defaults={
                'amount_to_save': Decimal('50000.00'),
                'current_saved_amount': Decimal('15000.00'),
                'start_date': timezone.now().date() - timedelta(days=60),
                'end_date': timezone.now().date() + timedelta(days=90),
                'status': 'ACTIVE'
            }
        )

        # Create test budgets for this month
        this_month_start = timezone.now().date().replace(day=1)
        this_month_end = (this_month_start + relativedelta(months=1) - timedelta(days=1))
        
        budget_data = [
            {'category': 'Food', 'limit': Decimal('10000'), 'spent': Decimal('8500')},
            {'category': 'Transport', 'limit': Decimal('5000'), 'spent': Decimal('4200')},
            {'category': 'Entertainment', 'limit': Decimal('3000'), 'spent': Decimal('2800')}
        ]
        
        for b in budget_data:
            Budget.objects.update_or_create(
                user=test_user,
                category=b['category'],
                period_start=this_month_start,
                defaults={
                    'monthly_limit': b['limit'],
                    'spent': b['spent'],
                    'period_end': this_month_end,
                    'is_active': True
                }
            )

        self.stdout.write(
            self.style.SUCCESS(
                'Successfully seeded test data for user "testuser"!\n'
                'Login: testuser / testpass123\n'
                'Check /services/financial_suggestions/'
            )
        )
