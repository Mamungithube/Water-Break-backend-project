from celery import shared_task
from django.utils import timezone
from .models import Reminder
from account.models import Notification

@shared_task(name="send_due_reminders_task")
def send_due_reminders_task():
    now = timezone.now()
    reminders = list(Reminder.objects.filter(sent=False, send_at__lte=now))
    count = len(reminders)

    for r in reminders:
        user = r.created_for
        message = f"Reminder: Your activity '{r.content_object}' is starting soon!"

        Notification.objects.create(
            recipient=user,
            sender=user,
            notification_type='reminder',
            message=message
        )

        if r.method_email:
            from account.tasks import send_email_task
            send_email_task.delay("Practice Reminder", message, [user.email])

        r.sent = True
        r.sent_at = now
        r.save()

    return f"Processed {count} reminders"
