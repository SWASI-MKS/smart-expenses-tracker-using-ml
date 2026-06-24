
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone  # Add this line
from decimal import Decimal

class BankAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=20, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.account_number}"


class BankTransaction(models.Model):
    TRANSACTION_TYPE = (
        ('DEBIT', 'Debit'),
        ('CREDIT', 'Credit'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=6, choices=TRANSACTION_TYPE)
    description = models.CharField(max_length=255)
    
    # Source for credit transactions (e.g., Salary, Freelance, Investment)
    source = models.CharField(max_length=100, blank=True, default='')
    
    # Category for debit transactions (e.g., Food, Transport, Shopping)
    category = models.CharField(max_length=100, blank=True, default='')
    
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Reference to related Income/Expense for sync tracking
    linked_income_id = models.IntegerField(null=True, blank=True)
    linked_expense_id = models.IntegerField(null=True, blank=True)
    
    # Optional: transaction hash for duplicate prevention
    transaction_hash = models.CharField(max_length=64, blank=True, default='')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - ₹{self.amount}"

    def save(self, *args, **kwargs):
        # Auto-calculate balance_after if not provided
        if not self.balance_after:
            # Get the last transaction to calculate running balance
            last_transaction = BankTransaction.objects.filter(
                user=self.user
            ).exclude(id=self.id).order_by('-created_at').first()
            
            last_balance = last_transaction.balance_after if last_transaction else 0
            
            if self.transaction_type == 'CREDIT':
                self.balance_after = last_balance + self.amount
            else:  # DEBIT
                self.balance_after = last_balance - self.amount
        
        super().save(*args, **kwargs)


class Card(models.Model):
    CARD_TYPES = (
        ('DEBIT', 'Debit Card'),
        ('CREDIT', 'Credit Card'),
    )

    CARD_BRANDS = (
        ('VISA', 'Visa'),
        ('MASTERCARD', 'Mastercard'),
        ('RUPAY', 'RuPay'),
        ('AMEX', 'American Express'),
        ('OTHER', 'Other'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cards')
    card_name = models.CharField(max_length=100)  # e.g. HDFC Debit
    card_type = models.CharField(max_length=10, choices=CARD_TYPES)
    card_number = models.CharField(max_length=16, unique=True, null=True, blank=True)  # Full card number
    last_four_digits = models.CharField(max_length=4)
    
    # Bank/Card details
    bank_name = models.CharField(max_length=100, blank=True, default='')
    card_brand = models.CharField(max_length=20, choices=CARD_BRANDS, default='OTHER')
    
    # Credit card specific fields
    limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Deprecated, use credit_limit
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    expiry_date = models.DateField(null=True, blank=True)
    cvv = models.CharField(max_length=4, blank=True, default='')  # Store encrypted in production
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.card_name} (****{self.last_four_digits})"

    @property
    def available_credit(self):
        """Calculate available credit for credit cards"""
        if self.card_type != 'CREDIT' or not self.credit_limit:
            return None
        
        total_spent = self.card_transactions.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        return self.credit_limit - total_spent

    @property
    def utilization_percentage(self):
        """Calculate credit utilization percentage"""
        if not self.credit_limit or self.credit_limit <= 0:
            return 0

        total_spent = self.card_transactions.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')

        utilization = (total_spent / self.credit_limit) * 100
        return round(utilization, 2)

    def save(self, *args, **kwargs):
        # Auto-populate last_four_digits from card_number if not set
        if self.card_number and not self.last_four_digits:
            self.last_four_digits = self.card_number[-4:]
        
        # Backwards compatibility: copy limit to credit_limit if needed
        if self.limit and not self.credit_limit:
            self.credit_limit = self.limit
            
        super().save(*args, **kwargs)


class CardTransaction(models.Model):
    SOURCE_TYPES = (
        ('MANUAL', 'Manual'),
        ('SIMULATED', 'Simulated'),
        ('CSV_IMPORT', 'CSV Import'),
        ('AUTO_SYNC', 'Auto Sync'),
    )

    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='card_transactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='card_transactions')
    
    # Transaction details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    merchant_name = models.CharField(max_length=255, blank=True, default='')
    category = models.CharField(max_length=100, blank=True, default='')
    
    # Transaction metadata
    transaction_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Enhanced fields
    is_recurring = models.BooleanField(default=False)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES, default='MANUAL')
    transaction_hash = models.CharField(max_length=64, blank=True, default='', db_index=True)
    
    # Reference to linked expense (for sync tracking)
    linked_expense_id = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'transaction_date']),
            models.Index(fields=['transaction_hash']),
        ]

    def __str__(self):
        return f"{self.card.card_name} - ₹{self.amount} - {self.transaction_date}"

    def save(self, *args, **kwargs):
        # Auto-generate transaction hash if not provided
        if not self.transaction_hash:
            import hashlib
            hash_string = f"{self.card.id}{self.amount}{self.description}{self.transaction_date}"
            self.transaction_hash = hashlib.sha256(hash_string.encode()).hexdigest()
        
        # Auto-calculate balance_after for credit cards
        if self.card.card_type == 'CREDIT' and not self.balance_after:
            # Get last transaction balance
            last_transaction = CardTransaction.objects.filter(
                card=self.card,
                transaction_date__lte=self.transaction_date
            ).exclude(id=self.id).order_by('-transaction_date', '-created_at').first()
            
            last_balance = last_transaction.balance_after if last_transaction else 0
            self.balance_after = last_balance + self.amount
        
        super().save(*args, **kwargs)


# PHASE 6: Smart Alerts Model
class Alert(models.Model):
    ALERT_TYPES = (
        ('CREDIT_LIMIT', 'Credit Limit Crossed'),
        ('LARGE_TRANSACTION', 'Large Transaction'),
        ('RECURRING_RENEWAL', 'Subscription Renewal'),
        ('SPENDING_INCREASE', 'Spending Increased'),
        ('LOW_BALANCE', 'Low Bank Balance'),
        ('DUPLICATE_TRANSACTION', 'Duplicate Transaction'),
    )

    PRIORITY_LEVELS = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='MEDIUM')
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Related transaction (optional)
    related_bank_transaction = models.ForeignKey(BankTransaction, on_delete=models.SET_NULL, null=True, blank=True)
    related_card_transaction = models.ForeignKey(CardTransaction, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Alert status
    is_read = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.alert_type} - {self.title}"


# Import timezone for default dates
from django.utils import timezone


# =====================================================
# PHASE 7: Beneficiary Model for Money Transfer
# =====================================================

class Beneficiary(models.Model):
    """Saved recipients for money transfers"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='beneficiaries')
    name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=20, blank=True, default='')
    ifsc_code = models.CharField(max_length=20, blank=True, default='')
    upi_id = models.CharField(max_length=50, blank=True, default='')
    phone = models.CharField(max_length=15, blank=True, default='')
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.account_number or self.upi_id}"


# =====================================================
# PHASE 7: Transfer Request Model for Money Transfer Flow
# =====================================================

class TransferRequest(models.Model):
    """Track money transfer requests with realistic flow"""
    
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('PROCESSING', 'Processing'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    )

    TRANSFER_TYPE_CHOICES = (
        ('UPI', 'UPI'),
        ('ACCOUNT', 'Account Transfer'),
        ('BENEFICIARY', 'Saved Beneficiary'),
    )

    transaction_id = models.CharField(max_length=50, unique=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_transfers')
    beneficiary = models.ForeignKey(Beneficiary, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_transfers')
    
    # Transfer details
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True, default='')
    transfer_type = models.CharField(max_length=20, choices=TRANSFER_TYPE_CHOICES, default='BENEFICIARY')
    
    # For account transfer (non-beneficiary)
    receiver_account = models.CharField(max_length=20, blank=True, default='')
    receiver_name = models.CharField(max_length=100, blank=True, default='')
    receiver_ifsc = models.CharField(max_length=20, blank=True, default='')
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    status_message = models.CharField(max_length=255, blank=True, default='')
    
    # Verification
    pin_verified = models.BooleanField(default=False)
    otp_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, default='')
    
    # Balance tracking
    balance_before = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Failure details
    failure_reason = models.CharField(max_length=255, blank=True, default='')
    
    # Reference to linked expense (for sync tracking)
    linked_expense_id = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_id} - ₹{self.amount} - {self.status}"


# =====================================================
# PHASE 7: Transaction Status History
# =====================================================

class TransactionStatus(models.Model):
    """Track status changes for each transaction"""
    transfer = models.ForeignKey(TransferRequest, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=20)
    status_message = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.transfer.transaction_id} - {self.status}"

# =====================================================
# BUDGET MODEL FOR FINANCIAL DASHBOARD
# =====================================================

class Budget(models.Model):
    """Monthly category budgets for financial tracking"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.CharField(max_length=100)
    monthly_limit = models.DecimalField(max_digits=12, decimal_places=2)
    spent = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    period_start = models.DateField()
    period_end = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'category', 'period_start']

    def __str__(self):
        return f"{self.user.username} - {self.category}: ₹{self.monthly_limit}"

    @property
    def utilization(self):
        return (self.spent / self.monthly_limit * 100) if self.monthly_limit > 0 else 0
