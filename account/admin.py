from datetime import timedelta
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from unfold.admin import ModelAdmin
from .models import User, Profile, Subscription
from unfold.forms import UserChangeForm, UserCreationForm
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

"""=========================unregister Models from admin========================="""


admin.site.unregister(OutstandingToken)
admin.site.unregister(BlacklistedToken)
admin.site.unregister(Group)

""" =============================== User Admin =============================== """

@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    
    # **FIX: Define fieldsets without username**
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (('Personal info'), {'fields': ('Fullname', 'role')}),
        (('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
        (('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    # **FIX: Add fields for the add form**
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'Fullname', 'role', 'password1', 'password2'),
        }),
    )
    
    list_display = ('email', 'Fullname', 'role','id','is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'role')
    search_fields = ('email', 'Fullname')
    ordering = ('email',)

""" =========================== Profile Admin ============================= """

@admin.register(Profile)
class ProfileAdmin(ModelAdmin):
    list_display = ('user_email', 'is_verified', 'otp')
    search_fields = ('user__email', 'user__Fullname')
    list_filter = ('is_verified',)
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'

    

""" ========================= Subscription Admin ========================= """

@admin.register(Subscription)
class SubscriptionAdmin(ModelAdmin):
    list_display = ('user_email', 'is_active', 'start_date', 'end_date')
    search_fields = ('user__email', 'user__Fullname')
    list_filter = ('is_active',)
    date_hierarchy = 'start_date'
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    
    @admin.action(description='Activate selected subscriptions')
    def activate_subscription(self, request, queryset):
        queryset.update(is_active=True)

    actions = [activate_subscription]





"""=========================Notification Admin========================="""
from .models import Notification
@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ('recipient_email', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('recipient__email', 'message')
    readonly_fields = ('created_at',)
    
    def recipient_email(self, obj):
        return obj.recipient.email
    recipient_email.short_description = 'Recipient Email'