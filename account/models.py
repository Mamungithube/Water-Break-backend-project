from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from datetime import timedelta
# compatibility helper for older migrations that reference
# `account.models.get_expiry_date` (InvitationToken default)
def get_expiry_date():
    return timezone.now() + timedelta(days=365)

# avoid importing Team at module import time to prevent circular imports
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
    




"""=========================Notification Model========================="""


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('join_request', 'Join Request'),
        ('team_message', 'Team Message'),
    )

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_notifications'
    )
    team = models.ForeignKey(
        'teamapp.Team',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    related_message = models.ForeignKey(
        'chat_system.TeamChatMessage',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )

    class Meta: 
        ordering = ['-created_at']  

    def __str__(self):
        return f"Notification to {self.recipient.email}"
