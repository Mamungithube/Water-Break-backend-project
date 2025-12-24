from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from unfold.admin import ModelAdmin
from .models import User, Profile, Subscription, TeamMember, InvitationToken , Team
from django.utils import timezone
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
    
    list_display = ('email', 'Fullname', 'role', 'is_staff', 'is_active')
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

""" ==============================Team Member Admin=============================== """

@admin.register(Team)
class TeamAdmin(ModelAdmin): 
    list_display = ('name', 'coach_email', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'coach__email')
    autocomplete_fields = ('coach',)  
    
    def coach_email(self, obj):
        return obj.coach.email
    coach_email.short_description = 'Coach'
@admin.register(TeamMember)
class TeamMemberAdmin(ModelAdmin):

    list_display = (
        'coach_email',
        'get_members',
        'role',
        'is_role_approved',
        'joined_at',
    )

    list_editable = ('is_role_approved',)

    list_filter = ('role', 'is_role_approved')

    search_fields = (
        'team__coach__email',
        'member__email',
        'member__fullname',
    )

    autocomplete_fields = ('team', 'member')

    def coach_email(self, obj):
        return obj.team.coach.email
    coach_email.short_description = 'Coach'

    def get_members(self, obj):
        return obj.member.email
    get_members.short_description = 'Members'


""" =========================Invitation Token Admin========================="""


@admin.register(InvitationToken)
class InvitationTokenAdmin(ModelAdmin): 
    list_display = ('coach_email', 'token', 'is_valid_display', 'is_used', 'expires_at', 'suggested_role')
    list_filter = ('is_used', 'suggested_role')
    search_fields = ('coach__email', 'token')
    readonly_fields = ('token', 'created_at')
    raw_id_fields = ('coach',)

    def coach_email(self, obj):
        return obj.coach.email
    
    def is_valid_display(self, obj):
        return obj.is_valid()
    is_valid_display.boolean = True