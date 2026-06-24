from django.contrib import admin
from .models import UserPreference, Notification

# Register your models here.
admin.site.register(UserPreference)
admin.site.register(Notification)
