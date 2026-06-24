from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    """
    Extended user profile model to store additional user information.
    Linked to Django's built-in User model using OneToOneField.
    """
    user = models.OneToOneField(
        to=User, 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    profile_image = models.ImageField(
        upload_to='profile_images/', 
        null=True, 
        blank=True,
        help_text="Upload a profile picture (JPG, PNG, WebP - max 2MB)"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

