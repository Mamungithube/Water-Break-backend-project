from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail

from .models import Reminder, Notification


@shared_task
def send_due_reminders_task():
    now = timezone.now()
    reminders = Reminder.objects.filter(sent=False, send_at__lte=now)
    count = 0
    for r in reminders:
        user = r.created_for
        try:
            title = f"Reminder: {r.content_object}"
        except Exception:
            title = "Reminder"
        try:
            message = f"You have a reminder for {r.content_object}."
        except Exception:
            message = "You have a reminder."

        if r.method_email and getattr(user, 'email', None):
            try:
                send_mail(
                    title,
                    message,
                    getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com'),
                    [user.email],
                    fail_silently=False,
                )
            except Exception:
                pass

        if r.method_notification:
            try:
                Notification.objects.create(user=user, title=title, message=message)
            except Exception:
                pass

        r.sent = True
        r.sent_at = now
        r.save()
        count += 1

    return {'processed': count}
