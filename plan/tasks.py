# plan/tasks.py
from celery import shared_task
from django.utils import timezone
from .models import Reminder
from account.models import Notification

@shared_task(name="send_due_reminders_task")
def send_due_reminders_task():
    now = timezone.now()
    reminders = Reminder.objects.filter(sent=False, send_at__lte=now)
    
    for r in reminders:
        user = r.created_for
        message = f"Reminder: Your activity '{r.content_object}' is starting soon!"

        # ইন-অ্যাপ নটিফিকেশন তৈরি (এটি তৈরি হওয়ামাত্র account/signals.py পুশ পাঠিয়ে দেবে)
        Notification.objects.create(
            recipient=user,
            sender=user,
            notification_type='reminder',
            message=message
        )

        # ইমেইল রিমাইন্ডার (Celery টাস্ক এর ভেতর থেকে আরেকটা টাস্ক কল করা)
        if r.method_email:
            from account.tasks import send_email_task
            send_email_task.delay("Practice Reminder", message, [user.email])

        r.sent = True
        r.sent_at = now
        r.save()
        
    return f"Processed {reminders.count()} reminders"