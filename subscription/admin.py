from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Subscription, SubscriptionPlan, ProcessedWebhookEvent

# ========================= Subscription Plan Admin =========================
@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(ModelAdmin):
    list_display = (
        'name', 'billing_period', 'price', 
        'max_teams_allowed', 'max_drills', 'max_practice_plans',
        'revenue_cat_product_id', 'is_active'
    )
    list_filter = ('name', 'billing_period', 'is_active')
    search_fields = ('name', 'revenue_cat_product_id')
    ordering = ('name', 'billing_period')
    
    fieldsets = (
        ('Plan Information', {
            'fields': ('name', 'billing_period', 'price', 'is_active')
        }),
        ('Limits', {
            'fields': ('max_teams_allowed', 'max_drills', 'max_practice_plans')
        }),
        ('RevenueCat Integration', {
            'fields': ('revenue_cat_product_id',)
        }),
    )
    
    @admin.action(description='Activate selected plans')
    def activate_plans(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} plans activated successfully.")
    
    @admin.action(description='Deactivate selected plans')
    def deactivate_plans(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} plans deactivated successfully.")
    
    actions = [activate_plans, deactivate_plans]


# ========================= Subscription Admin =========================
@admin.register(Subscription)
class SubscriptionAdmin(ModelAdmin):
    list_display = (
        'user_email', 'plan_name', 'status', 'is_active_badge',
        'current_teams', 'current_drills', 'current_practice_plans',
        'current_period_end'
    )
    list_filter = ('status', 'plan__name', 'plan__billing_period')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'revenue_cat_id')
    date_hierarchy = 'created_at'
    readonly_fields = (
        'revenue_cat_id', 'created_at', 'updated_at',
        'number_of_teams', 'number_of_drills', 'number_of_practice_plans'
    )
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'revenue_cat_id')
        }),
        ('Subscription Details', {
            'fields': ('plan', 'status')
        }),
        ('Subscription Period', {
            'fields': (
                'started_at', 'current_period_start', 
                'current_period_end', 'canceled_at'
            )
        }),
        ('Usage Statistics', {
            'fields': (
                'number_of_teams', 'number_of_drills', 'number_of_practice_plans'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'
    
    def plan_name(self, obj):
        period = f" ({obj.plan.get_billing_period_display()})" if obj.plan.billing_period else ""
        return f"{obj.plan.get_name_display()}{period}"
    plan_name.short_description = 'Plan'
    plan_name.admin_order_field = 'plan__name'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return '✅ Active'
        return '❌ Inactive'
    is_active_badge.short_description = 'Active Status'
    
    def current_teams(self, obj):
        current = obj.number_of_teams
        max_allowed = obj.plan.max_teams_allowed
        if max_allowed == 999:
            return f"{current} / Unlimited"
        return f"{current} / {max_allowed}"
    current_teams.short_description = 'Teams'
    
    def current_drills(self, obj):
        current = obj.number_of_drills
        max_allowed = obj.plan.max_drills
        if max_allowed == -1:
            return f"{current} / Unlimited"
        return f"{current} / {max_allowed}"
    current_drills.short_description = 'Drills'
    
    def current_practice_plans(self, obj):
        current = obj.number_of_practice_plans
        max_allowed = obj.plan.max_practice_plans
        if max_allowed == -1:
            return f"{current} / Unlimited"
        return f"{current} / {max_allowed}"
    current_practice_plans.short_description = 'Practice Plans'
    
    @admin.action(description='✅ Activate selected subscriptions')
    def activate_subscriptions(self, request, queryset):
        count = queryset.update(status='active')
        self.message_user(request, f"{count} subscription(s) activated successfully.")
    
    @admin.action(description='❌ Deactivate selected subscriptions')
    def deactivate_subscriptions(self, request, queryset):
        count = queryset.update(status='inactive')
        self.message_user(request, f"{count} subscription(s) deactivated successfully.")
    
    @admin.action(description='🔄 Mark as trialing')
    def mark_as_trialing(self, request, queryset):
        count = queryset.update(status='trialing')
        self.message_user(request, f"{count} subscription(s) marked as trialing.")
    
    @admin.action(description='🚫 Cancel selected subscriptions')
    def cancel_subscriptions(self, request, queryset):
        from django.utils import timezone
        count = queryset.update(status='canceled', canceled_at=timezone.now())
        self.message_user(request, f"{count} subscription(s) canceled successfully.")
    
    actions = [
        activate_subscriptions, 
        deactivate_subscriptions, 
        mark_as_trialing,
        cancel_subscriptions
    ]


# ========================= Processed Webhook Event Admin =========================
@admin.register(ProcessedWebhookEvent)
class ProcessedWebhookEventAdmin(ModelAdmin):
    list_display = ('event_id', 'event_type', 'app_user_id', 'processed_at')
    list_filter = ('event_type', 'processed_at')
    search_fields = ('event_id', 'app_user_id', 'event_type')
    date_hierarchy = 'processed_at'
    readonly_fields = ('event_id', 'event_type', 'app_user_id', 'processed_at', 'raw_data')
    
    fieldsets = (
        ('Event Information', {
            'fields': ('event_id', 'event_type', 'app_user_id')
        }),
        ('Timestamp', {
            'fields': ('processed_at',)
        }),
        ('Raw Data', {
            'fields': ('raw_data',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Webhook events শুধু automatically create হবে
        return False
    
    def has_change_permission(self, request, obj=None):
        # Webhook events edit করা যাবে না
        return False