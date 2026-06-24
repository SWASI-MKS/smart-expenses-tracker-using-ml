from .models import Notification
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone


def create_notification(user, title, message, type, send_email=False):
    """
    Safe helper function to create notifications.
    Prevents duplicate email notifications on the same day.
    """
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        type=type,
        send_email=send_email
    )

    # Send email only if allowed and not duplicate today
    if send_email:
        # Check if we already sent a notification with same title today
        today = timezone.now().date()
        already_sent_today = Notification.objects.filter(
            user=user,
            title=title,
            send_email=True,
            created_at__date=today
        ).exists()
        
        if not already_sent_today:
            try:
                send_mail(
                    subject=title,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else settings.EMAIL_HOST_USER,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            except Exception:
                pass  # Fail silently for email errors

    return notification
