from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import math


class Debt(models.Model):
    """Debt/Loan tracking model with EMI calculations."""
    
    # Loan types
    LOAN_PERSONAL = 'PERSONAL'
    LOAN_CAR = 'CAR'
    LOAN_HOME = 'HOME'
    LOAN_EDUCATION = 'EDUCATION'
    LOAN_CREDIT_CARD = 'CREDIT_CARD'
    LOAN_OTHER = 'OTHER'
    
    LOAN_TYPE_CHOICES = [
        (LOAN_PERSONAL, 'Personal Loan'),
        (LOAN_CAR, 'Car Loan'),
        (LOAN_HOME, 'Home Loan'),
        (LOAN_EDUCATION, 'Education Loan'),
        (LOAN_CREDIT_CARD, 'Credit Card'),
        (LOAN_OTHER, 'Other'),
    ]
    
    # Status choices
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_PAID_OFF = 'PAID_OFF'
    STATUS_DEFAULTED = 'DEFAULTED'
    STATUS_PENDING = 'PENDING'
    
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_PAID_OFF, 'Paid Off'),
        (STATUS_DEFAULTED, 'Defaulted'),
        (STATUS_PENDING, 'Pending'),
    ]
    
    # Core fields
    owner = models.ForeignKey(to=User, on_delete=models.CASCADE)
    loan_name = models.CharField(max_length=200, help_text="Name of the loan")
    loan_type = models.CharField(max_length=20, choices=LOAN_TYPE_CHOICES, default=LOAN_PERSONAL)
    
    # Loan details
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Original loan amount")
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Annual interest rate (%)")
    loan_term_months = models.IntegerField(help_text="Loan term in months")
    emi_amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Monthly EMI amount")
    
    # Dates
    start_date = models.DateField(help_text="Loan start date")
    end_date = models.DateField(help_text="Expected loan end date")
    next_emi_date = models.DateField(help_text="Next EMI due date")
    
    # Additional info
    lender_name = models.CharField(max_length=200, blank=True, help_text="Bank/lender name")
    account_number = models.CharField(max_length=50, blank=True, help_text="Loan account number")
    notes = models.TextField(blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.loan_name} - ${self.principal_amount}"
    
    @property
    def total_amount_paid(self):
        """Calculate total amount paid so far."""
        paid_installments = self.emi_payments.filter(is_paid=True).count()
        return self.emi_amount * paid_installments
    
    @property
    def remaining_balance(self):
        """Calculate remaining balance to be paid."""
        # Convert loan_term_months to Decimal to avoid TypeError with Decimal * float
        term_in_years = Decimal(self.loan_term_months) / Decimal(12)
        total_loan = self.principal_amount * (1 + (self.interest_rate / 100) * term_in_years)
        return max(Decimal(0), total_loan - self.total_amount_paid)
    
    @property
    def progress_percentage(self):
        """Calculate loan payoff progress percentage."""
        if self.principal_amount > 0:
            paid = float(self.total_amount_paid)
            total = float(self.principal_amount) * (1 + (float(self.interest_rate) / 100) * (self.loan_term_months / 12))
            return min(100, (paid / total) * 100) if total > 0 else 0
        return 0
    
    @property
    def emi_remaining(self):
        """Calculate number of EMI payments remaining."""
        paid_count = self.emi_payments.filter(is_paid=True).count()
        return max(0, self.loan_term_months - paid_count)
    
    @property
    def is_overdue(self):
        """Check if any EMI is overdue."""
        return self.next_emi_date < timezone.now().date() and self.status == self.STATUS_ACTIVE
    
    @property
    def total_interest(self):
        """Calculate total interest to be paid over loan term."""
        total_payment = self.emi_amount * self.loan_term_months
        return total_payment - self.principal_amount
    
    @property
    def total_cost_of_loan(self):
        """Total amount to be paid (principal + interest)."""
        return self.emi_amount * self.loan_term_months
    
    def calculate_emi(self):
        """Calculate EMI using standard formula."""
        # EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
        # Where P = Principal, r = monthly interest rate, n = number of months
        try:
            P = float(self.principal_amount)
            r = float(self.interest_rate) / 100 / 12  # Monthly interest rate
            n = self.loan_term_months
            
            if r > 0:
                emi = P * r * (math.pow(1 + r, n)) / (math.pow(1 + r, n) - 1)
            else:
                emi = P / n
            
            return round(emi, 2)
        except:
            return 0
    
    def calculate_amortization_schedule(self):
        """Generate amortization schedule."""
        schedule = []
        balance = float(self.principal_amount)
        monthly_rate = float(self.interest_rate) / 100 / 12
        emi = float(self.emi_amount)
        
        for month in range(1, self.loan_term_months + 1):
            interest_payment = balance * monthly_rate
            principal_payment = emi - interest_payment
            balance -= principal_payment
            
            schedule.append({
                'month': month,
                'emi': emi,
                'principal': round(principal_payment, 2),
                'interest': round(interest_payment, 2),
                'balance': max(0, round(balance, 2))
            })
        
        return schedule
    
    def update_status(self):
        """Automatically update debt status based on payments."""
        if self.emi_remaining <= 0:
            self.status = self.STATUS_PAID_OFF
            self.save(update_fields=['status', 'updated_at'])
        return self.status
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['next_emi_date']),
        ]


class EMIPayment(models.Model):
    """Individual EMI payment tracking."""
    
    debt = models.ForeignKey(to=Debt, on_delete=models.CASCADE, related_name='emi_payments')
    due_date = models.DateField(help_text="EMI due date")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    principal_portion = models.DecimalField(max_digits=12, decimal_places=2)
    interest_portion = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"EMI for {self.debt.loan_name} - Due: {self.due_date}"
    
    @property
    def is_overdue(self):
        """Check if EMI is overdue."""
        return not self.is_paid and self.due_date < timezone.now().date()
    
    class Meta:
        ordering = ['due_date']
        indexes = [
            models.Index(fields=['debt', 'is_paid']),
            models.Index(fields=['due_date']),
        ]
