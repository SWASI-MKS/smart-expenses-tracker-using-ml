"""
Celery Configuration for Expense Tracker
=======================================
This file configures Celery for asynchronous task processing,
including email sending in the background.

Installation:
    pip install celery redis

Usage:
    # Start Celery worker
    celery -A expensetracker worker -l info
    
    # Start Celery beat (for scheduled tasks)
    celery -A expensetracker beat -l info

Environment Variables:
    CELERY_BROKER_URL=redis://localhost:6379/0
    CELERY_RESULT_BACKEND=redis://localhost:6379/0
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expensetracker.settings')

# Create Celery app
app = Celery('expensetracker')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# ===========================================
# Celery Configuration
# ===========================================

# Task settings
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.timezone = 'UTC'
app.conf.enable_utc = True

# Task execution settings
app.conf.task_acks_late = True  # Acknowledge after task execution
app.conf.task_reject_on_worker_lost = True  # Requeue if worker dies
app.conf.task_track_started = True  # Track task start time

# Result backend settings
app.conf.result_expires = 3600  # Results expire after 1 hour

# Worker settings
app.conf.worker_prefetch_multiplier = 4  # Prefetch tasks
app.conf.worker_max_tasks_per_child = 1000  # Restart worker after 1000 tasks

# Broker settings
app.conf.broker_connection_retry_on_startup = True

# ===========================================
# Periodic Tasks (Celery Beat)
# ===========================================

app.conf.beat_schedule = {
    # Process daily spending summaries every 10 minutes
    # This runs frequently to handle different user timezone preferences
    'process-daily-summaries': {
        'task': 'notifications.tasks.process_daily_summaries',
        'schedule': 600.0,  # Every 10 minutes (600 seconds)
    },
    
    # Clean up old daily summary notifications weekly
    'cleanup-old-summaries': {
        'task': 'notifications.tasks.cleanup_old_summaries',
        'schedule': crontab(hour=3, minute=0, day_of_week='sunday'),
    },
}


# ===========================================
# Error Handling
# ===========================================

@app.task(bind=True, max_retries=3)
def debug_task(self):
    """Debug task for testing Celery"""
    print(f'Request: {self.request!r}')


# Handle task failures gracefully
@app.task
def task_failure_handler(request, exc, traceback):
    """Handle task failures"""
    from expenses.email_service import logger
    logger.error(f"Task {request.id} failed: {exc}")
    # You could send an email to admins here
    
    # Re-raise for Celery to handle
    raise
