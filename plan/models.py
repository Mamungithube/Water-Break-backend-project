from django.db import models
from django.utils import timezone
from django.conf import settings
from datetime import datetime, date, time, timedelta
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.db.models.signals import m2m_changed
from account.models import Notification

class Drill(models.Model):
    create_By = models.ForeignKey('account.User', on_delete=models.CASCADE)
    assign_team_name = models.CharField(max_length=100, blank=True, null=True)
    assign_team = models.ManyToManyField("teamapp.Team" , blank=True, related_name='drills')
    name = models.CharField(max_length=50)
    assigned_members = models.ManyToManyField(
        'account.User', 
        blank=True, 
        related_name='assigned_drills',
        help_text="Sub-team members who can VIEW this drill"
    )
    assistant_coach = models.ForeignKey(
        'account.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assisted_drills',
        help_text="Assistant coach who can MANAGE this drill"
    )
    category = models.TextField(max_length=100)
    description = models.TextField(max_length=250)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Plan(models.Model):
    create_By = models.ForeignKey('account.User', on_delete=models.CASCADE)
    assign_team = models.ManyToManyField("teamapp.Team" , blank=True, related_name='Teams')
    plan_title = models.CharField(max_length=100)
    start_practice_time = models.DateTimeField(null=True, blank=True)
    end_practice_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.plan_title


class Block(models.Model):
    create_By = models.ForeignKey('account.User', on_delete=models.CASCADE)
    drill = models.ForeignKey(Drill, on_delete=models.CASCADE , related_name='blocks', null=True, blank=True)
    practice_plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='Plan_Block', null=True, blank=True)
    title = models.CharField(max_length=50)
    color_code = models.CharField(max_length=7, null=True, blank=True)
    start_time = models.TimeField(auto_now=False, auto_now_add=False)
    end_time = models.TimeField(auto_now=False, auto_now_add=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        drill_name = self.drill.name if self.drill else "No Drill"
        return f"{drill_name} - {self.title}"
    


class Reminder(models.Model):
    """A scheduled reminder for a specific user about a Drill/Block/plan."""
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    created_for = models.ForeignKey('account.User', on_delete=models.CASCADE, related_name='plan_reminders')
    send_at = models.DateTimeField()
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

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
    """Create Reminder objects for users related to the provided object."""
    if offset_minutes is None:
        offset_minutes = _get_offset_minutes()

    now = timezone.now()
    users = set()

    if isinstance(obj, Drill):
        for member in obj.assigned_members.all():
            users.add(member)
        
        if obj.assistant_coach:
            users.add(obj.assistant_coach)

    elif isinstance(obj, Block):
        drill = obj.drill
        if drill:
            for member in drill.assigned_members.all():
                users.add(member)
            
            if drill.assistant_coach:
                users.add(drill.assistant_coach)
        
        if send_at is None:
            # Use practice_plan date if available, otherwise use tomorrow
            if obj.practice_plan and obj.practice_plan.start_practice_time:
                plan_date = obj.practice_plan.start_practice_time.date()
            else:
                plan_date = now.date() + timedelta(days=1)
            
            start_dt = datetime.combine(plan_date, obj.start_time)
            start_dt = timezone.make_aware(start_dt, timezone.get_current_timezone())
            
            if start_dt < now:
                start_dt = start_dt + timedelta(days=1)
            
            send_at = start_dt - timedelta(minutes=offset_minutes)

    elif isinstance(obj, Plan):
        # ✅ CHANGE - assigned_members and assistant_coach of the drill for all blocks in the Plan
        for block in obj.Plan_Block.all():
            drill = block.drill
            if drill:
                for member in drill.assigned_members.all():
                    users.add(member)
                
                if drill.assistant_coach:
                    users.add(drill.assistant_coach)
        
        if send_at is None and obj.start_practice_time:
            send_at = obj.start_practice_time - timedelta(minutes=offset_minutes)

    if send_at is None:
        send_at = now

    ct = ContentType.objects.get_for_model(obj)
    for user in users:
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
        send_at = timezone.now()
        schedule_reminders_for_object(instance, send_at=send_at)


# ✅ NEW SIGNAL - Trigger when assigned_members change in
@receiver(m2m_changed, sender=Drill.assigned_members.through)
def drill_assigned_members_changed(sender, instance, action, pk_set, **kwargs):
    """When assigned_members are added to a drill, send reminders"""
    print(f"🔔 SIGNAL FIRED: action={action}, drill={instance.name}, pk_set={pk_set}", flush=True)
    if action == 'post_add' and pk_set:
        send_at = timezone.now()
        schedule_reminders_for_object(instance, send_at=send_at)


@receiver(m2m_changed, sender=Drill.assign_team.through)
def drill_assign_team_changed(sender, instance, action, pk_set, **kwargs):
    if action == 'post_add' and pk_set:
        send_at = timezone.now()
        schedule_reminders_for_object(instance, send_at=send_at)


@receiver(post_save, sender=Block)
def create_block_reminders(sender, instance, created, **kwargs):
    if created:
        offset = _get_offset_minutes()
        now = timezone.now()
        
        # Determine the date for the block
        if instance.practice_plan and instance.practice_plan.start_practice_time:
            # Use practice plan's date
            plan_date = instance.practice_plan.start_practice_time.date()
        else:
            # Default to tomorrow
            plan_date = now.date() + timedelta(days=1)
        
        # Combine date with block's start_time
        start_dt = datetime.combine(plan_date, instance.start_time)
        start_dt = timezone.make_aware(start_dt, timezone.get_current_timezone())
        
        # If the time has already passed today, schedule for tomorrow
        if start_dt < now:
            start_dt = start_dt + timedelta(days=1)
        
        # Calculate send_at (offset minutes before start_time)
        send_at = start_dt - timedelta(minutes=offset)
        
        schedule_reminders_for_object(instance, send_at=send_at)

@receiver(post_save, sender=Plan)
def create_plan_reminders(sender, instance, created, **kwargs):
    if created:
        offset = _get_offset_minutes()
        schedule_reminders_for_object(instance, offset_minutes=offset)



@receiver(m2m_changed, sender=Plan.assign_team.through)
def notify_team_on_plan_assignment(sender, instance, action, pk_set, **kwargs):
    if action == "post_add":
        for team_id in pk_set:
            from teamapp.models import TeamMember
            # Finding all approved team members
            memberships = TeamMember.objects.filter(team_id=team_id, is_role_approved=True)
            for member_ship in memberships:
                Notification.objects.create(
                    recipient=member_ship.member,
                    sender=instance.create_By,
                    notification_type='assignment',
                    message=f"A new practice plan '{instance.plan_title}' has been assigned to your team."
                )

@receiver(m2m_changed, sender=Drill.assign_team.through)
def notify_team_on_drill_assignment(sender, instance, action, pk_set, **kwargs):
    if action == "post_add":
        for team_id in pk_set:
            from teamapp.models import TeamMember
            memberships = TeamMember.objects.filter(team_id=team_id, is_role_approved=True)
            for member_ship in memberships:
                Notification.objects.create(
                    recipient=member_ship.member,
                    sender=instance.create_By,
                    notification_type='assignment',
                    message=f"A new drill '{instance.name}' has been assigned to your team."
                )
