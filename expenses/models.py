from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now
import os
import uuid


def receipt_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('receipts/', filename)


class Expense(models.Model):
    FREQUENCY_DAILY = 'DAILY'
    FREQUENCY_WEEKLY = 'WEEKLY'
    FREQUENCY_MONTHLY = 'MONTHLY'
    FREQUENCY_YEARLY = 'YEARLY'
    FREQUENCY_NONE = 'NONE'
    
    FREQUENCY_CHOICES = [
        (FREQUENCY_NONE, 'One-time'),
        (FREQUENCY_DAILY, 'Daily'),
        (FREQUENCY_WEEKLY, 'Weekly'),
        (FREQUENCY_MONTHLY, 'Monthly'),
        (FREQUENCY_YEARLY, 'Yearly'),
    ]
    
    # Payment methods
    PAYMENT_CASH = 'CASH'
    PAYMENT_CARD = 'CARD'
    PAYMENT_BANK = 'BANK'
    PAYMENT_UPI = 'UPI'
    PAYMENT_OTHER = 'OTHER'
    
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_CASH, 'Cash'),
        (PAYMENT_CARD, 'Credit/Debit Card'),
        (PAYMENT_BANK, 'Bank Transfer'),
        (PAYMENT_UPI, 'UPI'),
        (PAYMENT_OTHER, 'Other'),
    ]
    
    
    amount = models.FloatField()
    date = models.DateField(default=now)
    time = models.TimeField(default=now)  
    description = models.TextField()
    owner = models.ForeignKey(to=User, on_delete=models.CASCADE)
    category = models.CharField(max_length=266)
    
    tags = models.JSONField(default=list, blank=True, null=True)
    receipt = models.FileField(upload_to=receipt_upload_path, blank=True, null=True)
    is_recurring = models.BooleanField(default=False)
    recurring_frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default=FREQUENCY_NONE, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default=PAYMENT_OTHER, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    
    def __str__(self):
        return f"{self.category} - ${self.amount}"
    
    class Meta:
        ordering = ['-date', '-time'] 


class ExpenseLimit(models.Model):
    """Model for setting expense limits."""
    owner = models.ForeignKey(to=User, on_delete=models.CASCADE)
    daily_expense_limit = models.FloatField(default=5000)
    monthly_expense_limit = models.FloatField(default=50000)
    
    def __str__(self):
        return f"Daily: {self.daily_expense_limit}, Monthly: {self.monthly_expense_limit}"


class Category(models.Model):
    """Model for expense categories."""
    name = models.CharField(max_length=266)
    owner = models.ForeignKey(to=User, on_delete=models.CASCADE, null=True, blank=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=20, blank=True, null=True)
    budget_limit = models.FloatField(default=0)
    is_global = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = 'Categories'