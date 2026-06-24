from django.urls import path
from . import views
from django.views.generic import RedirectView

urlpatterns = [
    # Redirect root 'goals/' to list_goals
    path('', RedirectView.as_view(url='list_goals/', permanent=False), name='goals'),
    path('list_goals/', views.list_goals, name='list_goals'),
    path('add_goal/', views.add_goal, name='add_goal'),
    path('add_amount/<int:goal_id>/', views.add_amount, name='add_amount'),
    path('delete_goal/<int:goal_id>/', views.delete_goal, name='delete_goal'),
    path('extend_deadline/<int:goal_id>/', views.extend_deadline, name='extend_deadline'),
    path('archive_goal/<int:goal_id>/', views.archive_goal, name='archive_goal'),
    path('unarchive_goal/<int:goal_id>/', views.unarchive_goal, name='unarchive_goal'),
    path('restore_goal/<int:goal_id>/', views.restore_goal, name='restore_goal'),
    path('goal_detail/<int:goal_id>/', views.goal_detail, name='goal_detail'),
    path('goal/<int:goal_id>/reopen/', views.reopen_goal, name='reopen_goal'),
    path('refresh_statuses/', views.refresh_goal_statuses, name='refresh_goal_statuses'),
]
