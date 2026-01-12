from django.db import models
from django.utils import timezone
from django.conf import settings
from datetime import datetime, date, time, timedelta

# contenttypes for generic relation so a Reminder can attach to Drill/Block/plan
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

# signals
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver


# Create your models here.
class Drill(models.Model):
    create_By = models.ForeignKey('account.User', on_delete=models.CASCADE)
    assign_team = models.ManyToManyField("teamapp.Team")
    name = models.CharField(max_length=50)
    category = models.TextField(max_length=100)
    description = models.TextField(max_length=250)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Block(models.Model):
    drill = models.ForeignKey(Drill, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    start_time = models.TimeField(auto_now=False, auto_now_add=False)
    end_time = models.TimeField(auto_now=False, auto_now_add=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.drill.name} - {self.title}"


class plan(models.Model):
    plan_title = models.CharField(max_length=100)
    Plan_Block = models.ManyToManyField(Block)
    prectice_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.plan_title


class Notification(models.Model):
    """Simple in-app notification stored for a user."""
    user = models.ForeignKey('account.User', on_delete=models.CASCADE, related_name='plan_notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user.email}: {self.title}"


class Reminder(models.Model):
    """A scheduled reminder for a specific user about a Drill/Block/plan.

    Uses GenericForeignKey to point at the source object.
    """
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    created_for = models.ForeignKey('account.User', on_delete=models.CASCADE, related_name='plan_reminders')
    send_at = models.DateTimeField()
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

    # methods
    method_email = models.BooleanField(default=True)
    method_notification = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['send_at']

    def __str__(self):
        return f"Reminder to {self.created_for.email} for {self.content_object} at {self.send_at}"


def _get_offset_minutes():
    return getattr(settings, 'REMINDER_DEFAULT_OFFSET_MINUTES', 60)


def schedule_reminders_for_object(obj, send_at=None, offset_minutes=None):
    """Create Reminder objects for users related to the provided object.

    - For `Drill`: all users in `assign_team`
    - For `Block`: users from `block.drill.assign_team`
    - For `plan`: users from drills referenced by its Plan_Block's drills

    `send_at` if provided is used as the reminder datetime. If not,
    for time-based objects we derive sensible defaults and subtract
    `offset_minutes` before the event time.
    """
    if offset_minutes is None:
        offset_minutes = _get_offset_minutes()

    now = timezone.now()
    users = set()

    # collect users depending on object type
    if isinstance(obj, Drill):
        for team in obj.assign_team.all():
            for user in team.members.all():
                users.add(user)

    elif isinstance(obj, Block):
        drill = obj.drill
        for team in drill.assign_team.all():
            for user in team.members.all():
                users.add(user)
        # derive send_at from block.start_time if not provided
        if send_at is None:
            today = now.date()
            start_dt = datetime.combine(today, obj.start_time)
            start_dt = timezone.make_aware(start_dt, timezone.get_current_timezone())
            if start_dt < now:
                start_dt = start_dt + timedelta(days=1)
            send_at = start_dt - timedelta(minutes=offset_minutes)

    elif isinstance(obj, plan):
        # collect users from drills referenced by blocks in the plan
        for block in obj.Plan_Block.all():
            drill = block.drill
            for team in drill.assign_team.all():
                for user in team.members.all():
                    users.add(user)
        # derive send_at from plan.prectice_time if not provided
        if send_at is None:
            send_at = obj.prectice_time - timedelta(minutes=offset_minutes)

    # fallback: if send_at not provided, set to now
    if send_at is None:
        send_at = now

    # create reminders
    ct = ContentType.objects.get_for_model(obj)
    for user in users:
        # avoid duplicate reminders for same object/user/send_at
        Reminder.objects.get_or_create(
            content_type=ct,
            object_id=obj.id,
            created_for=user,
            send_at=send_at,
            defaults={
                'method_email': True,
                'method_notification': True,
            }
        )


@receiver(post_save, sender=Drill)
def create_drill_reminders(sender, instance, created, **kwargs):
    if created:
        # notify assigned team members immediately (creation notice)
        send_at = timezone.now()
        schedule_reminders_for_object(instance, send_at=send_at)


@receiver(m2m_changed, sender=Drill.assign_team.through)
def drill_assign_team_changed(sender, instance, action, pk_set, **kwargs):
    # when teams are added to a drill schedule reminders for newly added teams
    if action == 'post_add' and pk_set:
        send_at = timezone.now()
        schedule_reminders_for_object(instance, send_at=send_at)


@receiver(post_save, sender=Block)
def create_block_reminders(sender, instance, created, **kwargs):
    if created:
        # schedule a reminder before the block start_time
        offset = _get_offset_minutes()
        # schedule_reminders_for_object will derive send_at from start_time
        schedule_reminders_for_object(instance, offset_minutes=offset)


@receiver(post_save, sender=plan)
def create_plan_reminders(sender, instance, created, **kwargs):
    if created:
        offset = _get_offset_minutes()
        schedule_reminders_for_object(instance, offset_minutes=offset)
