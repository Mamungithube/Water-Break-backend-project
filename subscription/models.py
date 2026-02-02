from django.conf import settings
from django.db import models

class SubscriptionPlan(models.Model):
    """Pricing plans"""
    PLAN_TYPE_CHOICES = [
        ("free", "Free Mode"),
        ("team", "Team Plan"),
        ("club", "Club Discount"),
    ]
    
    BILLING_PERIOD_CHOICES = [
        ("monthly", "Monthly"),
        ("annual", "Annual"),
    ]
    
    name = models.CharField(max_length=50, choices=PLAN_TYPE_CHOICES)
    billing_period = models.CharField(
        max_length=20, 
        choices=BILLING_PERIOD_CHOICES,
        null=True,
        blank=True
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Limits
    max_teams_allowed = models.PositiveIntegerField(default=0)
    max_drills = models.PositiveIntegerField(default=5)  # -1 = unlimited
    max_practice_plans = models.PositiveIntegerField(default=5)  # -1 = unlimited
    
    # RevenueCat product ID
    revenue_cat_product_id = models.CharField(max_length=255, unique=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['name', 'billing_period']
    
    def __str__(self):
        period = f" ({self.get_billing_period_display()})" if self.billing_period else ""
        return f"{self.get_name_display()}{period} - ${self.price}"


class Subscription(models.Model):
    """User's subscription"""
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("canceled", "Canceled"),
        ("expired", "Expired"),
        ("trialing", "Trial"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription"
    )
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    revenue_cat_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="inactive")
    
    # Dates
    started_at = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.plan.name} ({self.status})"
    
    @property
    def is_active(self):
        return self.status in ['active', 'trialing']
    
    # Team count
    @property
    def number_of_teams(self):
        from teamapp.models import Team
        return Team.objects.filter(coach=self.user).count()
    
    # Drill count
    @property
    def number_of_drills(self):
        from plan.models import Drill
        return Drill.objects.filter(create_By=self.user).count()
    
    # Practice plan count
    @property
    def number_of_practice_plans(self):
        from plan.models import plan
        return plan.objects.filter(create_By=self.user).count()
    
    def can_create_team(self):
        """Check team creation limit"""
        if not self.is_active:
            return False, "Active subscription required"
        
        if self.plan.name == "free":
            return False, "Free plan does not allow team creation. Upgrade to Team or Club plan."
        
        current_count = self.number_of_teams
        max_allowed = self.plan.max_teams_allowed
        
        if self.plan.name == "team" and current_count >= max_allowed:
            return False, "Team plan allows only 1 team. Upgrade to Club plan for unlimited teams."
        
        return True, None
    
    def can_create_drill(self):
        """Check drill creation limit"""
        if not self.is_active:
            return False, "Active subscription required"
        
        max_drills = self.plan.max_drills
        if max_drills == -1:  # Unlimited
            return True, None
        
        current_count = self.number_of_drills
        if current_count >= max_drills:
            return False, f"Free plan allows only {max_drills} drills. Upgrade for unlimited drills."
        
        return True, None
    
    def can_create_practice_plan(self):
        """Check practice plan creation limit"""
        if not self.is_active:
            return False, "Active subscription required"
        
        max_plans = self.plan.max_practice_plans
        if max_plans == -1:  # Unlimited
            return True, None
        
        current_count = self.number_of_practice_plans
        if current_count >= max_plans:
            return False, f"Free plan allows only {max_plans} practice plans. Upgrade for unlimited plans."
        
        return True, None


class ProcessedWebhookEvent(models.Model):
    """Track RevenueCat webhooks"""
    event_id = models.CharField(max_length=255, unique=True, db_index=True)
    event_type = models.CharField(max_length=100, blank=True)
    app_user_id = models.CharField(max_length=255, blank=True, db_index=True)
    processed_at = models.DateTimeField(auto_now_add=True)
    raw_data = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-processed_at']

    def __str__(self):
        return f"{self.event_id} - {self.event_type}"