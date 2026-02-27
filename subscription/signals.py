from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Subscription

@receiver(post_save, sender=Subscription)
def update_user_role_on_subscription_change(sender, instance, **kwargs):
    user = instance.user
    plan = instance.plan

    # Paid plan + active/trialing → coach
    if plan.name != 'free' and instance.status in ['active', 'trialing']:
        if user.role != 'coach':
            user.role = 'coach'
            user.save(update_fields=['role'])

    # Free plan বা expired/canceled → player
    elif plan.name == 'free' or instance.status in ['expired', 'inactive']:
        if user.role == 'coach':
            user.role = 'player'
            user.save(update_fields=['role'])