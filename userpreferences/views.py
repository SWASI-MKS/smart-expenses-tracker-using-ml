from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import os
import json
from datetime import time
from django.conf import settings
from .models import UserPreference, Notification
from .notification_service import NotificationService
from .currency_service import CurrencyService
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from expenses.models import ExpenseLimit

# Common timezones for the dropdown
COMMON_TIMEZONES = [
    ('UTC', 'UTC'),
    ('America/New_York', 'Eastern Time (US & Canada)'),
    ('America/Chicago', 'Central Time (US & Canada)'),
    ('America/Denver', 'Mountain Time (US & Canada)'),
    ('America/Los_Angeles', 'Pacific Time (US & Canada)'),
    ('America/Toronto', 'Toronto'),
    ('America/Vancouver', 'Vancouver'),
    ('Europe/London', 'London'),
    ('Europe/Paris', 'Paris'),
    ('Europe/Berlin', 'Berlin'),
    ('Asia/Dubai', 'Dubai'),
    ('Asia/Kolkata', 'India (IST)'),
    ('Asia/Singapore', 'Singapore'),
    ('Asia/Tokyo', 'Tokyo'),
    ('Asia/Shanghai', 'Shanghai'),
    ('Australia/Sydney', 'Sydney'),
    ('Pacific/Auckland', 'Auckland'),
]

@login_required(login_url='/authentication/login')
def index(request):
    # Handle database errors gracefully
    try:
        daily_expense_limit, created = ExpenseLimit.objects.get_or_create(
            owner=request.user,
            defaults={'daily_expense_limit': 5000}
        )
        daily_limit_value = daily_expense_limit.daily_expense_limit
    except Exception:
        daily_limit_value = 0
    
    currency_data = []
    currencies_dict = {}  # Dictionary for easy lookup
    exists = UserPreference.objects.filter(user=request.user).exists()
    user_preferences = None
    if exists:
        user_preferences = UserPreference.objects.get(user=request.user)
    
    if request.method == "GET":
        file_path = os.path.join(settings.BASE_DIR, 'currencies.json')
        with open(file_path, 'r') as json_file:
            data = json.load(json_file)
            for k, v in data.items():
                currency_data.append({'name': k, 'value': v})
                currencies_dict[k] = v

        return render(request, 'preferences/index.html', {
            'currencies': currency_data, 
            'currencies_dict': currencies_dict,
            'user_preferences': user_preferences,
            'daily_expense_limit': daily_limit_value,
            'timezones': COMMON_TIMEZONES,
        })
    else:
        # Unified form handling - save all settings together
        currency = request.POST.get('currency')
        timezone_value = request.POST.get('timezone', 'UTC')
        daily_summary_time = request.POST.get('daily_summary_time', '00:00')
        daily_summary_enabled = request.POST.get('daily_summary_enabled') == 'on'
        daily_expense_limit_value = request.POST.get('daily_expense_limit')
        
        # Update daily expense limit
        if daily_expense_limit_value:
            try:
                expense_limit_obj, _ = ExpenseLimit.objects.get_or_create(
                    owner=request.user,
                    defaults={'daily_expense_limit': 5000}
                )
                expense_limit_obj.daily_expense_limit = float(daily_expense_limit_value)
                expense_limit_obj.save()
                daily_limit_value = expense_limit_obj.daily_expense_limit
            except Exception:
                pass  # Keep existing value if update fails
        
        if exists:
            user_preferences.currency = currency
            user_preferences.timezone = timezone_value
            
            # Parse time if provided
            if daily_summary_time:
                try:
                    hour, minute = map(int, daily_summary_time.split(':'))
                    user_preferences.daily_summary_time = time(hour, minute)
                except ValueError:
                    user_preferences.daily_summary_time = time(0, 0)
            
            user_preferences.daily_summary_enabled = daily_summary_enabled
            user_preferences.save()
            
            # Invalidate cache when currency is updated
            CurrencyService.invalidate_user_cache(request.user.id)
        else:
            # Parse time for creation
            parsed_time = time(0, 0)
            if daily_summary_time:
                try:
                    hour, minute = map(int, daily_summary_time.split(':'))
                    parsed_time = time(hour, minute)
                except ValueError:
                    pass
            
            UserPreference.objects.create(
                user=request.user, 
                currency=currency,
                timezone=timezone_value,
                daily_summary_time=parsed_time,
                daily_summary_enabled=daily_summary_enabled,
            )
        
        messages.success(request, "All preferences saved successfully")
        
        # Reload currency data for rendering
        file_path = os.path.join(settings.BASE_DIR, 'currencies.json')
        with open(file_path, 'r') as json_file:
            data = json.load(json_file)
            for k, v in data.items():
                currency_data.append({'name': k, 'value': v})
                currencies_dict[k] = v
        
        # Refresh user_preferences from database
        if exists:
            user_preferences = UserPreference.objects.get(user=request.user)
        
        return render(request, 'preferences/index.html', {
            'currencies': currency_data, 
            'currencies_dict': currencies_dict,
            'user_preferences': user_preferences,
            'daily_expense_limit': daily_limit_value,
            'timezones': COMMON_TIMEZONES,
        })


@login_required(login_url='/authentication/login')
def notifications(request):
    """Display all notifications for the current user"""
    user_notifications = Notification.objects.filter(user=request.user)
    unread_count = user_notifications.filter(is_read=False).count()
    
    return render(request, 'userpreferences/notifications.html', {
        'notifications': user_notifications,
        'unread_count': unread_count
    })


@login_required(login_url='/authentication/login')
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    messages.success(request, "Notification marked as read")
    return redirect('notifications')


@login_required(login_url='/authentication/login')
def mark_all_notifications_read(request):
    """Mark all notifications as read for the current user"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read")
    return redirect('notifications')


@login_required(login_url='/authentication/login')
def delete_notification(request, notification_id):
    """Delete a single notification"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.delete()
    messages.success(request, "Notification deleted")
    return redirect('notifications')


@login_required(login_url='/authentication/login')
def delete_all_notifications(request):
    """Delete all notifications for the current user"""
    Notification.objects.filter(user=request.user).delete()
    messages.success(request, "All notifications deleted")
    return redirect('notifications')


# ============================================================
# AJAX API Endpoints for Notifications
# ============================================================

@login_required(login_url='/authentication/login')
def api_get_unread_count(request):
    """API endpoint to get unread notification count"""
    count = NotificationService.get_unread_count(request.user)
    return JsonResponse({'unread_count': count})


@login_required(login_url='/authentication/login')
def api_get_notifications(request):
    """API endpoint to get notifications (with pagination)"""
    limit = int(request.GET.get('limit', 20))
    offset = int(request.GET.get('offset', 0))
    include_read = request.GET.get('include_read', 'false').lower() == 'true'
    
    notifications = NotificationService.get_notifications(
        request.user, 
        limit=limit + offset, 
        include_read=include_read
    )[offset:offset + limit]
    
    data = [{
        'id': n.id,
        'title': n.title,
        'message': n.message,
        'type': n.type,
        'icon': n.ICON_MAP.get(n.type, 'fa-bell'),
        'is_read': n.is_read,
        'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S'),
    } for n in notifications]
    
    return JsonResponse({'notifications': data})


@login_required(login_url='/authentication/login')
@require_POST
def api_mark_read(request):
    """API endpoint to mark notification as read"""
    notification_id = request.POST.get('notification_id')
    success = NotificationService.mark_as_read(notification_id, request.user)
    return JsonResponse({'success': success})


@login_required(login_url='/authentication/login')
@require_POST
def api_mark_all_read(request):
    """API endpoint to mark all notifications as read"""
    count = NotificationService.mark_all_as_read(request.user)
    return JsonResponse({'success': True, 'count': count})
