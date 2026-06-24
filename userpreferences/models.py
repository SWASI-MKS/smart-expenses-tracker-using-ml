from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import hashlib
# Create your models here.


class UserPreference(models.Model):
    user = models.OneToOneField(to=User, on_delete=models.CASCADE)
    currency = models.CharField(max_length=255, blank=True, null=True)
    
    # Timezone settings for daily summary (IANA format, e.g., "Asia/Kolkata")
    timezone = models.CharField(
        max_length=50, 
        default='UTC',
        help_text="User's timezone in IANA format (e.g., Asia/Kolkata, America/New_York)"
    )
    
    # Daily summary settings
    daily_summary_time = models.TimeField(
        default=None,  # Will be set to 00:00:00
        help_text="Preferred time to receive daily spending summary"
    )
    
    last_summary_sent_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Timestamp when daily summary was last sent"
    )
    
    daily_summary_enabled = models.BooleanField(
        default=True,
        help_text="Enable or disable daily spending summary notifications"
    )

    def __str__(self):
        return str(self.user)+'s'+'preferences'
    
    def save(self, *args, **kwargs):
        # Set default time to 00:00:00 if not provided
        if self.daily_summary_time is None:
            from datetime import time
            self.daily_summary_time = time(0, 0, 0)
        super().save(*args, **kwargs)


class Notification(models.Model):
    """Model to store user notifications with anti-duplicate support"""
    TYPE_CHOICES = [
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('info', 'Info'),
        ('critical', 'Critical'),
    ]
    
    # Event types that can trigger notifications
    EVENT_TYPES = [
        # SUCCESS - Store only, no email
        ('expense_added', 'Expense Added'),
        ('expense_updated', 'Expense Updated'),
        ('expense_deleted', 'Expense Deleted'),
        ('goal_created', 'Goal Created'),
        ('limit_updated', 'Limit Updated'),
        ('login_success', 'Login Success'),
        
        # WARNING - Store only
        ('daily_limit_80', '80% Daily Limit Reached'),
        ('goal_near_deadline', 'Goal Near Deadline'),
        
        # INFO - Daily Summary
        ('daily_summary', 'Daily Spending Summary'),
        
        # WARNING - Store + Email
        ('daily_limit_exceeded', 'Daily Limit Exceeded'),
        ('monthly_limit_exceeded', 'Monthly Limit Exceeded'),
        
        # ERROR - Store only
        ('invalid_input', 'Invalid Input'),
        ('future_date', 'Future Date'),
        ('voice_recognition_failed', 'Voice Recognition Failed'),
        ('insufficient_balance', 'Insufficient Balance'),
        
        # INFO - Store only
        ('no_expenses', 'No Expenses Found'),
        ('no_search_results', 'No Search Results'),
        ('listening_started', 'Listening Started'),
        
        # CRITICAL - Store + Email
        ('suspicious_login', 'Suspicious Login'),
        ('password_changed', 'Password Changed'),
        ('large_transaction', 'Large Unusual Transaction'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    send_email = models.BooleanField(default=False)
    
    # Anti-duplicate: hash of key attributes to prevent duplicates
    event_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    
    # Optional: related object for navigation
    related_object_id = models.IntegerField(blank=True, null=True)
    related_object_type = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['event_type', 'event_hash']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def unread_count(self):
        return Notification.objects.filter(user=self.user, is_read=False).count()
    
    # Color mapping for templates
    COLOR_MAP = {
        'success': 'green',
        'warning': 'yellow',
        'error': 'red',
        'info': 'blue',
        'critical': 'darkred',
    }
    
    # Icon mapping
    ICON_MAP = {
        'success': 'fa-check-circle',
        'warning': 'fa-exclamation-triangle',
        'error': 'fa-times-circle',
        'info': 'fa-info-circle',
        'critical': 'fa-exclamation-circle',
    }
    
    def generate_hash(self, **kwargs):
        """Generate unique hash for duplicate detection"""
        hash_input = f"{self.user.id}:{self.event_type}"
        for key, value in sorted(kwargs.items()):
            hash_input += f":{key}:{value}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
