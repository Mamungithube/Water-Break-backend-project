# account/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Notification
from .tasks import send_fcm_notification_task  # Celery task ইমপোর্ট করুন

@receiver(post_save, sender=Notification)
def notify_via_fcm(sender, instance, created, **kwargs):
    """
    যখনই কোনো নটিফিকেশন তৈরি হবে, Celery এর মাধ্যমে পুশ পাঠানো হবে।
    """
    if not created:
        return

    # টাইপ অনুযায়ী মেসেজ টাইটেল সেট করা
    titles = {
        'join_request': "New Join Request",
        'request_accepted': "Request Approved!",
        'team_message': f"New message from {instance.team.name if instance.team else 'Team'}",
        'assignment': "New Activity Assigned",
        'reminder': "Practice Reminder",
    }

    title = titles.get(instance.notification_type, "Water Break Update")
    body = instance.message
    
    data = {
        'notification_id': str(instance.id),
        'type': instance.notification_type,
    }
    if instance.team_id:
        data['team_id'] = str(instance.team_id)

    # .delay() ব্যবহার করে Celery কিউ-তে পাঠিয়ে দিন (থ্রেড এর প্রয়োজন নেই)
    send_fcm_notification_task.delay(instance.recipient.id, title, body, data)