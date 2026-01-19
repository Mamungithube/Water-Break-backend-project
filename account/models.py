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
    

"""=========================Subscription Model========================="""
class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    revenue_cat_id = models.CharField(max_length=255, blank=True, null=True, help_text="The App User ID in RevenueCat.")
    is_active = models.BooleanField(default=False)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(blank=True, null=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)

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


class ProcessedWebhookEvent(models.Model):
    event_id = models.CharField(max_length=255, unique=True)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Processed Webhook Event"
        verbose_name_plural = "Processed Webhook Events"

    def __str__(self):
        return self.event_id
    


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
