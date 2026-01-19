
from django.db import models
from django.utils import timezone
import uuid
from datetime import timedelta


"""=========================Team Member Model========================="""
from django.conf import settings
from django.core.exceptions import ValidationError

class Team(models.Model):
    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='coached_teams',
        limit_choices_to={'role': 'coach'}
    )
    name = models.CharField(max_length=100)
    team_profile_pic = models.ImageField(upload_to='team_profiles/', blank=True, null=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='TeamMember',
        related_name='teams'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (Coach: {self.coach.email})"
    
    def get_active_token(self):
        """Get the active invitation token for this team"""
        try:
            token = self.invitation_tokens.filter(expires_at__gt=timezone.now()).first()
            return token
        except:
            return None

class TeamMember(models.Model):
    ROLE_CHOICES = (
        ('assistant', 'Assistant Coach'),
        ('player', 'Player'),
    )

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='memberships'
    )

    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='team_memberships'
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='player'
    )
    team_position = models.CharField(max_length=25, blank=False, null=False)
    is_role_approved = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('team', 'member')

    def clean(self):
        if self.team.coach == self.member:
            raise ValidationError("Coach cannot join their own team.")

    def __str__(self):
        return f"{self.member.email} - {self.role}"




"""=========================Invitation Token Model========================="""


def get_expiry_date():
    return timezone.now() + timedelta(days = 365)

class InvitationToken(models.Model):
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='invitation_tokens'
    )
    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='invitations',
        limit_choices_to={'role': 'coach'}
    )
    token = models.CharField(
        max_length=10,
        unique=True,
        editable=False
    )
    expires_at = models.DateTimeField(default=get_expiry_date)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def is_valid(self):
        return self.expires_at > timezone.now()

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.token} - {self.team.name} (Expires: {self.expires_at.strftime('%Y-%m-%d %H:%M')})"
