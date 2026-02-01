from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings

# Create your models here.
"""=========================Subscription Model========================="""
class Subscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, # এখানে পরিবর্তন করুন
        on_delete=models.CASCADE
    )
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
    