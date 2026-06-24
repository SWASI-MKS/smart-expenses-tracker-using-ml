from django.urls import path
from . import views
urlpatterns = [
    path('', views.index, name="preferences"),
    path('notifications/', views.notifications, name="notifications"),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name="mark-notification-read"),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name="mark-all-notifications-read"),
    path('notifications/delete/<int:notification_id>/', views.delete_notification, name="delete-notification"),
    path('notifications/delete-all/', views.delete_all_notifications, name="delete-all-notifications"),
]
