from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Goal(models.Model):
    """Goal model with lifecycle management"""
    
    # Status choices for goal lifecycle
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_OVERDUE = 'OVERDUE'
    STATUS_ARCHIVED = 'ARCHIVED'
    
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_OVERDUE, 'Overdue'),
        (STATUS_ARCHIVED, 'Archived'),
    ]
    
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(to=User, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    amount_to_save = models.DecimalField(max_digits=10, decimal_places=2)
    current_saved_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE
    )
    is_achieved = models.BooleanField(default=False)  # Legacy field, kept for compatibility
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['end_date']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def saved_percentage(self):
        """Calculate saved percentage"""
        if self.amount_to_save > 0:
            return (self.current_saved_amount / self.amount_to_save) * 100
        return 0
    
    @property
    def days_remaining(self):
        """Calculate days remaining until deadline"""
        today = timezone.now().date()
        return (self.end_date - today).days
    
    @property
    def days_overdue(self):
        """Calculate days past deadline (negative if not yet due)"""
        today = timezone.now().date()
        return (today - self.end_date).days
    
    @property
    def is_completed(self):
        """Check if goal is completed"""
        return self.current_saved_amount >= self.amount_to_save
    
    @property
    def is_overdue(self):
        """Check if goal is overdue"""
        today = timezone.now().date()
        return today > self.end_date and not self.is_completed
    
    def calculate_progress(self):
        """Calculate progress with additional lifecycle info"""
        saved_percentage = self.saved_percentage
        days_remaining = self.days_remaining
        
        # Check if there are days remaining to avoid division by zero
        if days_remaining > 0:
            daily_savings_required = (self.amount_to_save - self.current_saved_amount) / days_remaining
        else:
            daily_savings_required = 0
        
        return {
            "saved_percentage": round(saved_percentage, 2),
            "daily_savings_required": round(daily_savings_required, 2),
            "days_remaining": days_remaining,
            "days_overdue": max(0, -days_remaining),  # Positive if overdue
            "is_overdue": self.is_overdue,
            "is_completed": self.is_completed,
            "status": self.status,
            "amount_remaining": max(0, self.amount_to_save - self.current_saved_amount),
        }
    
    def update_status(self):
        """Automatically update goal status based on current state"""
        if self.is_completed:
            self.status = self.STATUS_COMPLETED
            self.is_achieved = True
        elif self.is_overdue:
            self.status = self.STATUS_OVERDUE
        else:
            self.status = self.STATUS_ACTIVE
            self.is_achieved = False
        
        self.save(update_fields=['status', 'is_achieved', 'updated_at'])
        return self.status
    
    def extend_deadline(self, new_end_date):
        """Extend goal deadline"""
        from django.core.exceptions import ValidationError
        if new_end_date <= timezone.now().date():
            raise ValidationError("New end date must be in the future")
        self.end_date = new_end_date
        # Reset to active if was overdue
        if self.status == self.STATUS_OVERDUE:
            self.status = self.STATUS_ACTIVE
        self.save(update_fields=['end_date', 'status', 'updated_at'])
    
    def archive(self):
        """Archive the goal"""
        self.status = self.STATUS_ARCHIVED
        self.save(update_fields=['status', 'updated_at'])
