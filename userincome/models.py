from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now


class UserIncome(models.Model):
    """Enhanced Income model with advanced features."""
    
    # Frequency options for recurring income
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
    PAYMENT_BANK = 'BANK'
    PAYMENT_CHECK = 'CHECK'
    PAYMENT_UPI = 'UPI'
    PAYMENT_OTHER = 'OTHER'
    
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_CASH, 'Cash'),
        (PAYMENT_BANK, 'Bank Transfer'),
        (PAYMENT_CHECK, 'Check'),
        (PAYMENT_UPI, 'UPI'),
        (PAYMENT_OTHER, 'Other'),
    ]
    
    # Core fields
    amount = models.FloatField()
    date = models.DateField(default=now)
    description = models.TextField()
    owner = models.ForeignKey(to=User, on_delete=models.CASCADE)
    source = models.CharField(max_length=266)
    
    # New enhanced fields
    is_recurring = models.BooleanField(default=False, help_text="Is this recurring income?")
    recurring_frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, 
                                           default=FREQUENCY_NONE)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES,
                                      default=PAYMENT_BANK)
    is_verified = models.BooleanField(default=False, help_text="Has income been verified?")
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.source} - ${self.amount}"
    
    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['owner', 'date']),
            models.Index(fields=['owner', 'source']),
            models.Index(fields=['date']),
            models.Index(fields=['is_recurring']),
        ]


class Source(models.Model):
    """Income source model."""
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(to=User, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon class for UI")
    color = models.CharField(max_length=7, default='#1CC88A', help_text="Hex color code")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=now)
    
    def __str__(self):
        return self.name
    
    @property
    def total_received_this_month(self):
        """Calculate total received from this source this month."""
        from django.db.models import Sum
        from django.utils import timezone
        
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        
        return UserIncome.objects.filter(
            owner=self.owner,
            source=self.name,
            date__gte=start_of_month,
            date__lte=today
        ).aggregate(total=Sum('amount'))['total'] or 0
    
    @property
    def average_monthly(self):
        """Calculate average monthly income from this source."""
        from django.db.models import Avg
        
        return UserIncome.objects.filter(
            owner=self.owner,
            source=self.name
        ).aggregate(avg=Avg('amount'))['avg'] or 0
