from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Notification
from .fcm import push_notification_for_user


@receiver(post_save, sender=Notification)
def notify_via_fcm(sender, instance, created, **kwargs):
    """Whenever a new Notification is persisted, push it to the recipient's devices."""
    if not created:
        return

    # prepare basic payload
    title = "New notification"
    body = instance.message or "You have a new notification."
    data = {
        'notification_id': str(instance.id),
        'type': instance.notification_type,
    }
    if instance.team_id:
        data['team_id'] = str(instance.team_id)

    # send asynchronously
    push_notification_for_user(instance.recipient, title, body, data)
