"""
Management command to populate sample bank data for testing.
Run with: python manage.py populate_bank_data
"""
import random
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from bank_simulator.models import (
    BankAccount,
    BankTransaction,
    Card,
    CardTransaction,
    Alert
)


class Command(BaseCommand):
    help = 'Populate sample bank data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Username to populate data for (default: first user)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing bank data before populating',
        )

    def handle(self, *args, **options):
        username = options.get('user')
        clear_data = options.get('clear', False)

        # Get or create user
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User "{username}" not found'))
                return
        else:
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR('No users found. Create a user first.'))
                return

        self.stdout.write(f'Populating bank data for user: {user.username}')

        # Clear existing data if requested
        if clear_data:
            BankTransaction.objects.filter(user=user).delete()
            CardTransaction.objects.filter(user=user).delete()
            Card.objects.filter(user=user).delete()
            BankAccount.objects.filter(user=user).delete()
            Alert.objects.filter(user=user).delete()
            self.stdout.write(self.style.WARNING('Cleared existing bank data'))

        # Create Bank Account
        bank_account, created = BankAccount.objects.get_or_create(
            user=user,
            defaults={
                'account_number': f'ACC{user.id}{datetime.now().strftime("%Y%m%d")}',
                'balance': Decimal('50000.00')
            }
        )
        if created:
            self.stdout.write(f'Created Bank Account: {bank_account.account_number}')
        else:
            self.stdout.write(f'Bank Account already exists: {bank_account.account_number}')

        # Sample bank transactions
        bank_tx_data = [
            # Credits (Income)
            {'type': 'CREDIT', 'amount': '50000', 'desc': 'Salary Deposit', 'source': 'Salary'},
            {'type': 'CREDIT', 'amount': '50000', 'desc': 'Salary Deposit', 'source': 'Salary'},
            {'type': 'CREDIT', 'amount': '50000', 'desc': 'Salary Deposit', 'source': 'Salary'},
            {'type': 'CREDIT', 'amount': '15000', 'desc': 'Freelance Project', 'source': 'Freelance'},
            {'type': 'CREDIT', 'amount': '5000', 'desc': 'Interest Income', 'source': 'Investment'},
            {'type': 'CREDIT', 'amount': '10000', 'desc': 'Bonus', 'source': 'Salary'},
            # Debits (Expenses)
            {'type': 'DEBIT', 'amount': '15000', 'desc': 'Rent Payment', 'category': 'Bills & Utilities'},
            {'type': 'DEBIT', 'amount': '3000', 'desc': 'Electricity Bill', 'category': 'Bills & Utilities'},
            {'type': 'DEBIT', 'amount': '1200', 'desc': 'Internet Bill', 'category': 'Bills & Utilities'},
            {'type': 'DEBIT', 'amount': '2500', 'desc': 'Grocery Shopping - DMart', 'category': 'Shopping'},
            {'type': 'DEBIT', 'amount': '1800', 'desc': 'Grocery Shopping - Big Bazaar', 'category': 'Shopping'},
            {'type': 'DEBIT', 'amount': '800', 'desc': 'Metro Recharge', 'category': 'Transportation'},
            {'type': 'DEBIT', 'amount': '450', 'desc': 'Uber Ride', 'category': 'Transportation'},
            {'type': 'DEBIT', 'amount': '600', 'desc': 'Fuel - Petrol Pump', 'category': 'Transportation'},
            {'type': 'DEBIT', 'amount': '1200', 'desc': 'Movie & Dinner - PVR', 'category': 'Entertainment'},
            {'type': 'DEBIT', 'amount': '799', 'desc': 'Netflix Subscription', 'category': 'Entertainment'},
            {'type': 'DEBIT', 'amount': '999', 'desc': 'Amazon Prime Membership', 'category': 'Entertainment'},
            {'type': 'DEBIT', 'amount': '2500', 'desc': 'Mobile Recharge - Jio', 'category': 'Bills & Utilities'},
            {'type': 'DEBIT', 'amount': '3500', 'desc': 'Dinner with Friends - Restaurant', 'category': 'Food & Dining'},
            {'type': 'DEBIT', 'amount': '800', 'desc': 'Coffee & Snacks - Starbucks', 'category': 'Food & Dining'},
            {'type': 'DEBIT', 'amount': '4500', 'desc': 'Clothing - Myntra', 'category': 'Shopping'},
            {'type': 'DEBIT', 'amount': '22000', 'desc': 'Laptop EMI Payment', 'category': 'Bills & Utilities'},
            {'type': 'DEBIT', 'amount': '3500', 'desc': 'Doctor Visit - Hospital', 'category': 'Healthcare'},
            {'type': 'DEBIT', 'amount': '1200', 'desc': 'Medicine - Pharmacy', 'category': 'Healthcare'},
            {'type': 'DEBIT', 'amount': '25000', 'desc': 'Flight Tickets - Booking.com', 'category': 'Travel'},
            {'type': 'DEBIT', 'amount': '8000', 'desc': 'Hotel Reservation - OYO', 'category': 'Travel'},
        ]

        # Create bank transactions with dates
        base_date = timezone.now() - timedelta(days=90)
        running_balance = Decimal('50000.00')

        for i, tx_data in enumerate(bank_tx_data):
            tx_date = base_date + timedelta(days=random.randint(0, 90))
            
            if tx_data['type'] == 'CREDIT':
                running_balance += Decimal(tx_data['amount'])
            else:
                running_balance -= Decimal(tx_data['amount'])
            
            BankTransaction.objects.get_or_create(
                user=user,
                amount=Decimal(tx_data['amount']),
                transaction_type=tx_data['type'],
                description=tx_data['desc'],
                defaults={
                    'source': tx_data.get('source', ''),
                    'category': tx_data.get('category', ''),
                    'balance_after': running_balance,
                    'created_at': tx_date,
                }
            )

        self.stdout.write(f'Created {len(bank_tx_data)} bank transactions')

        # Update bank account balance
        total_credits = BankTransaction.objects.filter(
            user=user, transaction_type='CREDIT'
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        total_debits = BankTransaction.objects.filter(
            user=user, transaction_type='DEBIT'
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        bank_account.balance = total_credits - total_debits
        bank_account.save()

        # Create Debit Card
        debit_card, created = Card.objects.get_or_create(
            user=user,
            card_name='HDFC Debit Card',
            defaults={
                'card_type': 'DEBIT',
                'card_number': '4532' + ''.join([str(random.randint(0, 9)) for _ in range(12)]),
                'last_four_digits': ''.join([str(random.randint(0, 9)) for _ in range(4)]),
                'bank_name': 'HDFC Bank',
                'card_brand': 'VISA',
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(f'Created Debit Card: {debit_card.card_name}')

        # Create Credit Card
        credit_card, created = Card.objects.get_or_create(
            user=user,
            card_name='SBI Credit Card',
            defaults={
                'card_type': 'CREDIT',
                'card_number': '5555' + ''.join([str(random.randint(0, 9)) for _ in range(12)]),
                'last_four_digits': ''.join([str(random.randint(0, 9)) for _ in range(4)]),
                'bank_name': 'State Bank of India',
                'card_brand': 'MASTERCARD',
                'credit_limit': Decimal('100000.00'),
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(f'Created Credit Card: {credit_card.card_name}')

        # Sample card transactions
        card_tx_data = [
            # Debit Card Transactions
            {'card': debit_card, 'amount': '450', 'desc': 'Uber Ride to Airport', 'merchant': 'Uber', 'category': 'Transportation'},
            {'card': debit_card, 'amount': '1800', 'desc': 'Monthly Groceries', 'merchant': 'DMart', 'category': 'Shopping'},
            {'card': debit_card, 'amount': '650', 'desc': 'Fuel - HP Petrol Pump', 'merchant': 'HP', 'category': 'Transportation'},
            {'card': debit_card, 'amount': '350', 'desc': 'Coffee & Pastries', 'merchant': 'Starbucks', 'category': 'Food & Dining'},
            {'card': debit_card, 'amount': '2200', 'desc': 'Dinner with Family', 'merchant': 'Restaurant', 'category': 'Food & Dining'},
            {'card': debit_card, 'amount': '599', 'desc': 'Shirt - Amazon', 'merchant': 'Amazon', 'category': 'Shopping'},
            {'card': debit_card, 'amount': '1200', 'desc': 'Movie Tickets - PVR', 'merchant': 'PVR', 'category': 'Entertainment'},
            {'card': debit_card, 'amount': '899', 'desc': 'Snacks & Drinks', 'merchant': 'Big Bazaar', 'category': 'Shopping'},
            {'card': debit_card, 'amount': '450', 'desc': 'Metro Card Recharge', 'merchant': 'Metro', 'category': 'Transportation'},
            {'card': debit_card, 'amount': '1500', 'desc': 'Mobile Accessories', 'merchant': 'Croma', 'category': 'Shopping'},
            # Credit Card Transactions
            {'card': credit_card, 'amount': '2500', 'desc': 'Lunch - Office', 'merchant': 'Zomato', 'category': 'Food & Dining'},
            {'card': credit_card, 'amount': '3500', 'desc': 'Weekend Shopping', 'merchant': 'Flipkart', 'category': 'Shopping'},
            {'card': credit_card, 'amount': '799', 'desc': 'Netflix Subscription', 'merchant': 'Netflix', 'category': 'Entertainment'},
            {'card': credit_card, 'amount': '4500', 'desc': 'Flight Tickets', 'merchant': 'MakeMyTrip', 'category': 'Travel'},
            {'card': credit_card, 'amount': '1200', 'desc': 'Gas Cylinder Booking', 'merchant': 'Indian Oil', 'category': 'Bills & Utilities'},
            {'card': credit_card, 'amount': '9500', 'desc': 'Electronics Purchase', 'merchant': 'Amazon', 'category': 'Shopping'},
            {'card': credit_card, 'amount': '2800', 'desc': 'Restaurant Birthday Party', 'merchant': 'Swiggy', 'category': 'Food & Dining'},
            {'card': credit_card, 'amount': '1500', 'desc': 'Online Course', 'merchant': 'Udemy', 'category': 'Education'},
            {'card': credit_card, 'amount': '2200', 'desc': 'Hotel Booking', 'merchant': 'Oyo', 'category': 'Travel'},
            {'card': credit_card, 'amount': '650', 'desc': 'Swiggy Order', 'merchant': 'Swiggy', 'category': 'Food & Dining'},
        ]

        # Create card transactions
        base_date = timezone.now() - timedelta(days=60)
        card_balance = Decimal('0.00')

        for i, tx_data in enumerate(card_tx_data):
            tx_date = base_date + timedelta(days=random.randint(0, 60))
            card = tx_data['card']
            
            # For credit cards, track running balance
            if card.card_type == 'CREDIT':
                card_balance += Decimal(tx_data['amount'])
            
            CardTransaction.objects.get_or_create(
                user=user,
                card=card,
                amount=Decimal(tx_data['amount']),
                description=tx_data['desc'],
                defaults={
                    'merchant_name': tx_data['merchant'],
                    'category': tx_data['category'],
                    'transaction_date': tx_date.date(),
                    'balance_after': card_balance if card.card_type == 'CREDIT' else None,
                    'source_type': 'SIMULATED',
                }
            )

        self.stdout.write(f'Created {len(card_tx_data)} card transactions')

        # Create some alerts
        Alert.objects.get_or_create(
            user=user,
            alert_type='CREDIT_LIMIT',
            title='Credit Limit Warning',
            message=f'{credit_card.card_name} has significant outstanding balance',
            defaults={
                'priority': 'MEDIUM',
                'is_read': False,
            }
        )
        
        Alert.objects.get_or_create(
            user=user,
            alert_type='RECURRING_RENEWAL',
            title='Recurring Payment Detected',
            message='Netflix subscription payment detected as recurring',
            defaults={
                'priority': 'LOW',
                'is_read': False,
            }
        )

        self.stdout.write(self.style.SUCCESS(f'Successfully populated bank data for {user.username}'))
        self.stdout.write('')
        self.stdout.write('Summary:')
        self.stdout.write(f'  - Bank Account: {bank_account.account_number} (Balance: ₹{bank_account.balance})')
        self.stdout.write(f'  - Bank Transactions: {BankTransaction.objects.filter(user=user).count()}')
        self.stdout.write(f'  - Cards: {Card.objects.filter(user=user).count()}')
        self.stdout.write(f'  - Card Transactions: {CardTransaction.objects.filter(user=user).count()}')
        self.stdout.write(f'  - Alerts: {Alert.objects.filter(user=user).count()}')


# Import models for aggregate
from django.db.models import Sum, Count

