from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
import uuid
from datetime import timedelta
"""=========================Custom User Manager========================="""
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email must be provided")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'coach')
        return self.create_user(email, password, **extra_fields)


"""=========================Custom User Model========================="""

class User(AbstractUser):
    ROLE_CHOICES = (
        ('coach', 'Coach'),
        ('assistant', 'Assistant Coach'),
        ('player', 'Player'),
    )

    username = None
    email = models.EmailField(unique=True)
    Fullname = models.CharField(max_length=55)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='player'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.Fullname or self.email


"""=========================Profile Model========================="""

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    otp = models.CharField(max_length=4, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    is_verified = models.BooleanField(default=True)

    def __str__(self):
        return self.user.Fullname or self.user.email
    


"""=========================Subscription Model========================="""
class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    is_active = models.BooleanField(default=False)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        try:
            old_instance = Subscription.objects.get(pk=self.pk)
            is_active_changed_to_true = self.is_active and not old_instance.is_active
        except Subscription.DoesNotExist:
            is_active_changed_to_true = self.is_active
        
        super().save(*args, **kwargs)

        if is_active_changed_to_true and self.user.role != 'coach':
            self.user.role = 'coach'
            self.user.save(update_fields=['role'])
            
        else:
            if self.user.role == 'coach':
                self.user.role = 'player'
                self.user.save(update_fields=['role'])


    def __str__(self):
        return f"{self.user.email} - {'Active' if self.is_active else 'Inactive'}"


"""=========================Team Member Model========================="""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class Team(models.Model):
    coach = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='coached_teams',
        limit_choices_to={'role': 'coach'}
    )
    name = models.CharField(max_length=100)
    team_profile_pic = models.ImageField(upload_to='team_profiles/', blank=True, null=True)
    members = models.ManyToManyField(
        User,
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
        User,
        on_delete=models.CASCADE,
        related_name='team_memberships'
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='player'
    )

    is_role_approved = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('team', 'member')

    def clean(self):
        # Coach নিজের team-এর member হতে পারবে না
        if self.team.coach == self.member:
            raise ValidationError(
                f"Coach {self.member.email} cannot be added as a member of their own team."
            )

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
        User,
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
