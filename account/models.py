from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone


# =========================
# User Manager
# =========================
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


# =========================
# User Model
# =========================
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


# =========================
# Profile Model
# =========================
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    otp = models.CharField(max_length=4, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    is_verified = models.BooleanField(default=True)

    def __str__(self):
        return self.user.Fullname or self.user.email


# =========================
# Subscription Model
# =========================
class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    is_active = models.BooleanField(default=False)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # Check if the 'is_active' field is changing to True
        # To avoid unnecessary updates, we check the database state
        try:
            old_instance = Subscription.objects.get(pk=self.pk)
            is_active_changed_to_true = self.is_active and not old_instance.is_active
        except Subscription.DoesNotExist:
            # New subscription instance, check if it's being saved as active
            is_active_changed_to_true = self.is_active
        
        # Call the original save method
        super().save(*args, **kwargs)

        # If the subscription is now active, upgrade the user's role to 'coach'
        if is_active_changed_to_true and self.user.role != 'coach':
            self.user.role = 'coach'
            self.user.save(update_fields=['role'])
            
            # OPTIONAL: You may want to downgrade the role when 'is_active' changes to False
        else:
            if self.user.role == 'coach':
                self.user.role = 'player'
                self.user.save(update_fields=['role'])


    def __str__(self):
        return f"{self.user.email} - {'Active' if self.is_active else 'Inactive'}"


# =========================
# Team Member Model
# =========================
class TeamMember(models.Model):
    ROLE_CHOICES = ( 
        ('assistant', 'Assistant Coach'),
        ('player', 'Player'),
    )
    coach = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='teams',
        limit_choices_to={'role': 'coach'}
    )
    member = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='team_roles'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='player'
    )
    is_role_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('coach', 'member')

    def __str__(self):
        return f"{self.member.email} ({self.role}) under {self.coach.email}"



# =========================
# Invitation Token Model
# =========================
import uuid # unique token generation

class InvitationToken(models.Model):
    coach = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='invitations',
        limit_choices_to={'role': 'coach'}
    )
    # 1. টোকেন জেনারেট (The code/token generation)
    token = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        unique=True
    )
    # 2. মেয়াদ (Expiration)
    expires_at = models.DateTimeField(
        default=timezone.now() + timezone.timedelta(days=7) # Default 7 days validity
    )
    # 3. টোকেন ব্যবহারের স্থিতি (Usage status)
    is_used = models.BooleanField(default=False)
    
    # 4. প্রস্তাবিত ভূমিকা (Suggested Role for the user joining)
    # এই ভূমিকাটি coach নির্ধারণ করতে পারেন, অথবা এটি খালি রাখা যেতে পারে 
    # যেন জয়েন করার সময় ব্যবহারকারী নিজেই role select করতে পারে।
    ROLE_CHOICES = (
        ('assistant', 'Assistant Coach'),
        ('player', 'Player'),
    )
    suggested_role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='player'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        """Checks if the token is not used and not expired."""
        return not self.is_used and self.expires_at > timezone.now()

    def __str__(self):
        return f"Token for {self.coach.email} - Valid: {self.is_valid()}"