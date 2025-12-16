from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Profile, Subscription, TeamMember, InvitationToken
from django.utils import timezone


# =========================
# Custom User Admin
# =========================

class UserAdmin(BaseUserAdmin):
    # Fieldsets for editing in Admin change view
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('Fullname', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    # Fields displayed in the list view
    list_display = ('email', 'Fullname', 'role', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'role', 'groups')
    search_fields = ('email', 'Fullname')
    ordering = ('email',)
    
    # Use 'email' as the username field
    # Removes the default 'username' field entirely from the admin
    filter_horizontal = ('groups', 'user_permissions')

# Register the User model
admin.site.register(User, UserAdmin)


# =========================
# Profile Admin
# =========================

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'is_verified', 'otp')
    search_fields = ('user__email', 'user__Fullname')
    list_filter = ('is_verified',)
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'


# =========================
# Subscription Admin
# =========================

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'is_active', 'start_date', 'end_date') # এখন এটি কাজ করবে
    search_fields = ('user__email', 'user__Fullname')
    list_filter = ('is_active',)
    date_hierarchy = 'start_date'
    
    # 🌟 এই মেথডটি ক্লাসের ভেতরে যোগ করুন 🌟
    def user_email(self, obj):
        """Subscription অবজেক্ট থেকে user এর ইমেল ফিরিয়ে আনে।"""
        return obj.user.email
    user_email.short_description = 'ব্যবহারকারীর ইমেল' # অ্যাডমিন প্যানেলে কলামের নাম
    
    # Custom action to activate selected subscriptions
    @admin.action(description='Activate selected subscriptions')
    def activate_subscription(self, request, queryset):
        # ... (rest of the code) ...
        pass # বাকি কোড অপরিবর্তিত থাকবে

    actions = [activate_subscription]


# =========================
# Team Member Admin
# =========================

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('coach_email', 'member_email', 'role', 'is_role_approved', 'created_at')
    list_filter = ('role', 'is_role_approved')
    search_fields = ('coach__email', 'member__email', 'member__Fullname')
    raw_id_fields = ('coach', 'member') # Use raw ID input for easier selection
    
    # Custom actions for approval flow
    @admin.action(description='Approve selected member roles')
    def approve_roles(self, request, queryset):
        updated_count = queryset.filter(is_role_approved=False).update(is_role_approved=True)
        self.message_user(request, f"{updated_count} member roles successfully approved.")

    @admin.action(description='Set selected members to Player role')
    def set_to_player(self, request, queryset):
        updated_count = queryset.update(role='player')
        self.message_user(request, f"{updated_count} members roles set to Player.")

    actions = [approve_roles, set_to_player]

    def coach_email(self, obj):
        return obj.coach.email
    coach_email.short_description = 'Coach'

    def member_email(self, obj):
        return obj.member.email
    member_email.short_description = 'Member'


# =========================
# Invitation Token Admin
# =========================

@admin.register(InvitationToken)
class InvitationTokenAdmin(admin.ModelAdmin):
    list_display = ('coach_email', 'token', 'is_valid_display', 'is_used', 'expires_at', 'suggested_role')
    list_filter = ('is_used', 'suggested_role')
    search_fields = ('coach__email', 'token')
    date_hierarchy = 'created_at'
    readonly_fields = ('token', 'created_at')
    raw_id_fields = ('coach',) # Use raw ID input for coach

    def coach_email(self, obj):
        return obj.coach.email
    coach_email.short_description = 'Coach'
    
    def is_valid_display(self, obj):
        # Uses the is_valid method from the model
        return obj.is_valid()
    is_valid_display.short_description = 'Is Valid'
    is_valid_display.boolean = True