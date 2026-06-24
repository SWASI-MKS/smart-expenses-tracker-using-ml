import os
import random
from datetime import datetime, date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from expenses.models import Expense, Category, ExpenseLimit
from userincome.models import UserIncome, Source
from goals.models import Goal
from bank_simulator.models import BankAccount, BankTransaction, Card, Budget
from debts.models import Debt, EMIPayment

class Command(BaseCommand):
    help = 'Seed realistic financial mock data for the demo user spanning 6 months.'

    def handle(self, *args, **options):
        self.stdout.write("Starting demo data seeding...")

        # 1. Create or get Demo User
        demo_username = "demo"
        demo_password = "demo123"
        demo_email = "demo@example.com"

        user, created = User.objects.get_or_create(username=demo_username, defaults={
            "email": demo_email,
            "is_active": True
        })
        if created:
            user.set_password(demo_password)
            user.save()
            self.stdout.write(f"Created user '{demo_username}'")
        else:
            self.stdout.write(f"User '{demo_username}' already exists. Re-seeding data for this user...")

        # 2. Clear existing demo data to ensure idempotency
        Expense.objects.filter(owner=user).delete()
        Category.objects.filter(owner=user).delete()
        ExpenseLimit.objects.filter(owner=user).delete()
        UserIncome.objects.filter(owner=user).delete()
        Source.objects.filter(owner=user).delete()
        Goal.objects.filter(owner=user).delete()
        BankAccount.objects.filter(user=user).delete()
        BankTransaction.objects.filter(user=user).delete()
        Card.objects.filter(user=user).delete()
        Budget.objects.filter(user=user).delete()
        Debt.objects.filter(owner=user).delete()

        self.stdout.write("Cleared existing records for user 'demo'.")

        # 3. Create Categories for Expense
        categories_data = [
            {"name": "Food", "color": "#FFC107", "budget_limit": 12000, "icon": "fa-utensils"},
            {"name": "Transportation", "color": "#03A9F4", "budget_limit": 4000, "icon": "fa-car"},
            {"name": "Shopping", "color": "#E91E63", "budget_limit": 8000, "icon": "fa-shopping-bag"},
            {"name": "Education", "color": "#9C27B0", "budget_limit": 3000, "icon": "fa-graduation-cap"},
            {"name": "Rent", "color": "#4CAF50", "budget_limit": 25000, "icon": "fa-home"},
            {"name": "Utilities", "color": "#FF5722", "budget_limit": 6000, "icon": "fa-bolt"},
            {"name": "Entertainment", "color": "#9E9E9E", "budget_limit": 8000, "icon": "fa-film"},
            {"name": "Medical", "color": "#F44336", "budget_limit": 5000, "icon": "fa-medkit"},
        ]

        categories = {}
        for cat_info in categories_data:
            cat = Category.objects.create(
                name=cat_info["name"],
                owner=user,
                color=cat_info["color"],
                icon=cat_info["icon"],
                budget_limit=cat_info["budget_limit"],
                is_global=False
            )
            categories[cat_info["name"]] = cat

        # 4. Create Sources for Income
        sources_data = [
            {"name": "Salary", "color": "#1CC88A", "icon": "fa-wallet"},
            {"name": "Freelancing", "color": "#36B9CC", "icon": "fa-laptop-code"},
            {"name": "Internship", "color": "#4E73DF", "icon": "fa-university"},
            {"name": "Project Revenue", "color": "#F6C23E", "icon": "fa-chart-line"},
        ]

        sources = {}
        for src_info in sources_data:
            src = Source.objects.create(
                name=src_info["name"],
                owner=user,
                color=src_info["color"],
                icon=src_info["icon"],
                is_active=True
            )
            sources[src_info["name"]] = src

        # 5. Define Dates (Spread over last 6 months)
        today = date.today()
        start_date = today - timedelta(days=180)

        # 6. Generate Income (Exactly 60 transactions)
        incomes = []
        
        # Monthly Salary: 6 times
        for i in range(6):
            salary_date = start_date + timedelta(days=i*30 + 5)
            inc = UserIncome.objects.create(
                owner=user,
                amount=58000.0,
                date=salary_date,
                source="Salary",
                description="Monthly corporate salary credit",
                is_recurring=True,
                recurring_frequency=UserIncome.FREQUENCY_MONTHLY,
                payment_method=UserIncome.PAYMENT_BANK,
                is_verified=True,
                notes="Standard monthly paycheck"
            )
            incomes.append(inc)

        # Monthly Internship: 6 times
        for i in range(6):
            intern_date = start_date + timedelta(days=i*30 + 10)
            inc = UserIncome.objects.create(
                owner=user,
                amount=12000.0,
                date=intern_date,
                source="Internship",
                description="Monthly research internship stipend",
                is_recurring=True,
                recurring_frequency=UserIncome.FREQUENCY_MONTHLY,
                payment_method=UserIncome.PAYMENT_BANK,
                is_verified=True,
                notes="Paid by research lab"
            )
            incomes.append(inc)

        # Freelancing: 18 times
        freelance_desc = [
            "UI Design consulting for local shop",
            "WordPress site bug fixes and updates",
            "Logo design contract payout",
            "SEO audit report for client site",
            "Python script automation for data scraping",
            "Custom landing page HTML build"
        ]
        for _ in range(18):
            random_days = random.randint(1, 180)
            inc_date = start_date + timedelta(days=random_days)
            inc = UserIncome.objects.create(
                owner=user,
                amount=round(random.uniform(5000, 16000), 2),
                date=inc_date,
                source="Freelancing",
                description=random.choice(freelance_desc),
                is_recurring=False,
                payment_method=random.choice([UserIncome.PAYMENT_UPI, UserIncome.PAYMENT_BANK]),
                is_verified=True
            )
            incomes.append(inc)

        # Project Revenue: 30 times
        project_desc = [
            "SaaS App subscription revenue",
            "Adsense ad networks credit payout",
            "ThemeForest digital product sale royalty",
            "Paid API usage credit",
            "Affiliate product sales commission"
        ]
        for _ in range(30):
            random_days = random.randint(1, 180)
            inc_date = start_date + timedelta(days=random_days)
            inc = UserIncome.objects.create(
                owner=user,
                amount=round(random.uniform(2000, 10000), 2),
                date=inc_date,
                source="Project Revenue",
                description=random.choice(project_desc),
                is_recurring=False,
                payment_method=random.choice([UserIncome.PAYMENT_UPI, UserIncome.PAYMENT_BANK]),
                is_verified=True
            )
            incomes.append(inc)

        self.stdout.write(f"Generated {len(incomes)} income transactions.")

        # 7. Generate Expenses (Exactly 240 transactions)
        expenses = []

        # Rent: 6 times
        for i in range(6):
            rent_date = start_date + timedelta(days=i*30 + 1)
            exp = Expense.objects.create(
                owner=user,
                amount=16000.0,
                date=rent_date,
                category="Rent",
                description="Monthly flat rent payment",
                payment_method=Expense.PAYMENT_BANK,
                is_recurring=True,
                recurring_frequency=Expense.FREQUENCY_MONTHLY,
                notes="Transferred directly to landlord account"
            )
            expenses.append(exp)

        # Utilities: 6 times
        utility_descs = [
            "Electricity bill payment",
            "Water and maintenance charges",
            "High-speed Wi-Fi internet broadband",
            "Electricity bill payment",
            "LPG Gas refilling charges",
            "Wi-Fi internet billing"
        ]
        for i in range(6):
            util_date = start_date + timedelta(days=i*30 + 4)
            exp = Expense.objects.create(
                owner=user,
                amount=round(random.uniform(3000, 5000), 2),
                date=util_date,
                category="Utilities",
                description=utility_descs[i],
                payment_method=Expense.PAYMENT_UPI,
                is_recurring=True,
                recurring_frequency=Expense.FREQUENCY_MONTHLY
            )
            expenses.append(exp)

        # Food: 90 times
        food_descs = ["Office lunch", "Grocery shopping", "Zomato dinner", "Coffee shop checkin", "McDonald's meal", "Subway sandwich", "Fruits & Vegetables purchase", "Swiggy order", "Evening tea and snacks"]
        for _ in range(90):
            random_days = random.randint(1, 180)
            exp_date = start_date + timedelta(days=random_days)
            exp = Expense.objects.create(
                owner=user,
                amount=round(random.uniform(150, 1100), 2),
                date=exp_date,
                category="Food",
                description=random.choice(food_descs),
                payment_method=random.choice([Expense.PAYMENT_UPI, Expense.PAYMENT_CASH, Expense.PAYMENT_CARD])
            )
            expenses.append(exp)

        # Transportation: 50 times
        transport_descs = ["Uber cab fare", "Metro card auto-recharge", "Fuel fill-up at Shell", "Local bus fare", "Auto-rickshaw ride", "Ola cab booking"]
        for _ in range(50):
            random_days = random.randint(1, 180)
            exp_date = start_date + timedelta(days=random_days)
            exp = Expense.objects.create(
                owner=user,
                amount=round(random.uniform(40, 450), 2),
                date=exp_date,
                category="Transportation",
                description=random.choice(transport_descs),
                payment_method=random.choice([Expense.PAYMENT_UPI, Expense.PAYMENT_CASH])
            )
            expenses.append(exp)

        # Shopping: 30 times
        shopping_descs = ["New casual shirts", "Amazon shopping run", "Running shoes at Nike", "Electronics gadget", "Household items", "Jeans", "Watch", "Gifts for cousin"]
        for _ in range(30):
            random_days = random.randint(1, 180)
            exp_date = start_date + timedelta(days=random_days)
            exp = Expense.objects.create(
                owner=user,
                amount=round(random.uniform(800, 4800), 2),
                date=exp_date,
                category="Shopping",
                description=random.choice(shopping_descs),
                payment_method=random.choice([Expense.PAYMENT_CARD, Expense.PAYMENT_UPI])
            )
            expenses.append(exp)

        # Education: 12 times
        edu_descs = ["Udemy Python Masterclass", "Coursera subscription fee", "Technical textbooks", "Kindle eBook purchase", "Design course workshop", "Scientific calculator"]
        for _ in range(12):
            random_days = random.randint(1, 180)
            exp_date = start_date + timedelta(days=random_days)
            exp = Expense.objects.create(
                owner=user,
                amount=round(random.uniform(600, 3000), 2),
                date=exp_date,
                category="Education",
                description=random.choice(edu_descs),
                payment_method=random.choice([Expense.PAYMENT_UPI, Expense.PAYMENT_CARD, Expense.PAYMENT_BANK])
            )
            expenses.append(exp)

        # Entertainment: 35 times
        ent_descs = ["Netflix monthly membership", "Movie tickets with popcorn", "Spotify Premium monthly billing", "PlayStation store purchase", "Bowling weekend with colleagues", "Restaurant party bill sharing"]
        for _ in range(35):
            random_days = random.randint(1, 180)
            exp_date = start_date + timedelta(days=random_days)
            exp = Expense.objects.create(
                owner=user,
                amount=round(random.uniform(200, 1600), 2),
                date=exp_date,
                category="Entertainment",
                description=random.choice(ent_descs),
                payment_method=random.choice([Expense.PAYMENT_UPI, Expense.PAYMENT_CARD])
            )
            expenses.append(exp)

        # Medical: 11 times
        med_descs = ["Prescription medicines at Pharmacy", "Dentist consultation", "General health checkup fee", "Daily vitamins and supplements", "First-aid kit refilling"]
        for _ in range(11):
            random_days = random.randint(1, 180)
            exp_date = start_date + timedelta(days=random_days)
            exp = Expense.objects.create(
                owner=user,
                amount=round(random.uniform(300, 2500), 2),
                date=exp_date,
                category="Medical",
                description=random.choice(med_descs),
                payment_method=random.choice([Expense.PAYMENT_UPI, Expense.PAYMENT_CARD, Expense.PAYMENT_CASH])
            )
            expenses.append(exp)

        self.stdout.write(f"Generated {len(expenses)} expense transactions.")

        # 8. Seed Bank Accounts & Cards
        bank_acc = BankAccount.objects.create(
            user=user,
            account_number="100987654321",
            balance=Decimal("250000.00")  # Starting balance
        )

        # Create realistic cards
        card_credit = Card.objects.create(
            user=user,
            card_name="HDFC Credit Card",
            card_type="CREDIT",
            card_number="4532789012345678",
            last_four_digits="5678",
            bank_name="HDFC Bank",
            card_brand="VISA",
            credit_limit=Decimal("150000.00"),
            due_date=today + timedelta(days=15),
            is_active=True,
            expiry_date=today + timedelta(days=1000),
            cvv="123"
        )
        card_debit = Card.objects.create(
            user=user,
            card_name="SBI Debit Card",
            card_type="DEBIT",
            card_number="5241876543210987",
            last_four_digits="0987",
            bank_name="State Bank of India",
            card_brand="MASTERCARD",
            is_active=True,
            expiry_date=today + timedelta(days=800),
            cvv="456"
        )

        # Generate Bank Transactions (Synchronized with Expense/Income entries)
        running_balance = Decimal("250000.00")
        
        # Sort all transactions chronologically to calculate running balance correctly
        all_tx = []
        for inc in incomes:
            all_tx.append({"type": "CREDIT", "amount": Decimal(str(inc.amount)), "date": inc.date, "desc": inc.description, "src": inc.source, "cat": "", "id": inc.id, "is_inc": True})
        for exp in expenses:
            all_tx.append({"type": "DEBIT", "amount": Decimal(str(exp.amount)), "date": exp.date, "desc": exp.description, "src": "", "cat": exp.category, "id": exp.id, "is_inc": False})
            
        all_tx.sort(key=lambda x: x["date"])

        # Create transactions
        for tx in all_tx:
            if tx["type"] == "CREDIT":
                running_balance += tx["amount"]
                BankTransaction.objects.create(
                    user=user,
                    amount=tx["amount"],
                    transaction_type="CREDIT",
                    description=tx["desc"],
                    source=tx["src"],
                    balance_after=running_balance,
                    linked_income_id=tx["id"]
                )
            else:
                running_balance -= tx["amount"]
                BankTransaction.objects.create(
                    user=user,
                    amount=tx["amount"],
                    transaction_type="DEBIT",
                    description=tx["desc"],
                    category=tx["cat"],
                    balance_after=running_balance,
                    linked_expense_id=tx["id"]
                )
                
        # Sync final account balance
        bank_acc.balance = running_balance
        bank_acc.save()
        self.stdout.write("Created BankAccount and synchronized transactions.")

        # 9. Create Financial Goals
        Goal.objects.create(
            name="Emergency Fund",
            owner=user,
            start_date=today - timedelta(days=120),
            end_date=today + timedelta(days=120),
            amount_to_save=Decimal("100000.00"),
            current_saved_amount=Decimal("75000.00"),
            status=Goal.STATUS_ACTIVE,
            is_achieved=False
        )
        Goal.objects.create(
            name="MacBook Pro M3",
            owner=user,
            start_date=today - timedelta(days=90),
            end_date=today - timedelta(days=10),
            amount_to_save=Decimal("150000.00"),
            current_saved_amount=Decimal("150000.00"),
            status=Goal.STATUS_COMPLETED,
            is_achieved=True
        )
        Goal.objects.create(
            name="Vacation in Switzerland",
            owner=user,
            start_date=today - timedelta(days=30),
            end_date=today + timedelta(days=300),
            amount_to_save=Decimal("250000.00"),
            current_saved_amount=Decimal("35000.00"),
            status=Goal.STATUS_ACTIVE,
            is_achieved=False
        )

        self.stdout.write("Created financial goals.")

        # 10. Create Budgets for Current Month
        start_of_month = today.replace(day=1)
        # End of current month
        if today.month == 12:
            end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

        for cat_info in categories_data:
            # Calculate spent amount this month
            spent_amt = sum(e.amount for e in expenses if e.category == cat_info["name"] and e.date >= start_of_month and e.date <= today)
            Budget.objects.create(
                user=user,
                category=cat_info["name"],
                monthly_limit=Decimal(str(cat_info["budget_limit"])),
                spent=Decimal(str(spent_amt)),
                period_start=start_of_month,
                period_end=end_of_month,
                is_active=True
            )
            
        self.stdout.write("Created monthly budgets for the current month.")

        # 11. Create Debts (Loans)
        Debt.objects.create(
            owner=user,
            loan_name="Car Loan",
            loan_type=Debt.LOAN_CAR,
            principal_amount=Decimal("600000.00"),
            interest_rate=Decimal("8.50"),
            loan_term_months=36,
            emi_amount=Decimal("18940.00"),
            start_date=today - timedelta(days=180),
            end_date=today + timedelta(days=900),
            next_emi_date=today + timedelta(days=10),
            lender_name="HDFC Auto Finance",
            account_number="LA9876543210"
        )
        Debt.objects.create(
            owner=user,
            loan_name="Laptop Purchase Credit Card EMI",
            loan_type=Debt.LOAN_CREDIT_CARD,
            principal_amount=Decimal("120000.00"),
            interest_rate=Decimal("12.00"),
            loan_term_months=12,
            emi_amount=Decimal("10660.00"),
            start_date=today - timedelta(days=90),
            end_date=today + timedelta(days=270),
            next_emi_date=today + timedelta(days=15),
            lender_name="SBI Credit Card Division",
            account_number="CC09876543"
        )

        self.stdout.write("Created debts/loans.")
        self.stdout.write(self.style.SUCCESS("Successfully seeded all demo data!"))
