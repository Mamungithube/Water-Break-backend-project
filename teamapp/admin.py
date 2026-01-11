from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import TeamMember, InvitationToken , Team
from django.utils import timezone
from datetime import timedelta

# Register your models here.
""" ==============================Team Admin=============================== """

@admin.register(Team)
class TeamAdmin(ModelAdmin): 
    list_display = ('name','id','coach_email', 'get_members_count', 'get_active_token_display', 'created_at')
    search_fields = ('name', 'coach__email')
    autocomplete_fields = ('coach',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Team Information', {
            'fields': ('name', 'coach', 'team_profile_pic')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def coach_email(self, obj):
        return obj.coach.email
    coach_email.short_description = 'Coach Email'
    
    def get_members_count(self, obj):
        return obj.memberships.filter(is_role_approved=True).count()
    get_members_count.short_description = 'Approved Members'
    
    def get_active_token_display(self, obj):
        token = obj.get_active_token()
        if token:
            return f"{token.token} (Valid)" if token.is_valid() else f"{token.token} (Expired)"
        return "No Token"
    get_active_token_display.short_description = 'Active Token'

""" ==============================Team Member Admin=============================== """

@admin.register(TeamMember)
class TeamMemberAdmin(ModelAdmin):
    list_display = (
        'is_role_approved',
        'id',
        'get_team_name',
        'get_member_email',
        'role',
        'joined_at',
    )

    # list_editable = ('is_role_approved',)
    list_filter = ('role', 'is_role_approved', 'joined_at')
    search_fields = (
        'team__name',
        'team__coach__email',
        'member__email',
        'member__Fullname',
    )
    autocomplete_fields = ('team', 'member')
    readonly_fields = ('joined_at',)
    
    actions = ['approve_members', 'reject_members']
    
    fieldsets = (
        ('Team & Member', {
            'fields': ('team', 'member', 'role')
        }),
        ('Status', {
            'fields': ('is_role_approved', 'joined_at')
        }),
    )

    def get_team_name(self, obj):
        return f"{obj.team.name} (Coach: {obj.team.coach.email})"
    get_team_name.short_description = 'Team'

    def get_member_email(self, obj):
        fullname = obj.member.Fullname if obj.member.Fullname else "N/A"
        return f"{obj.member.email} ({fullname})"
    get_member_email.short_description = 'Member'
    
    @admin.action(description='✅ Approve selected members')
    def approve_members(self, request, queryset):
        updated = queryset.update(is_role_approved=True)
        self.message_user(request, f'{updated} members approved successfully.')
    
    @admin.action(description='❌ Reject and remove selected members')
    def reject_members(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} members rejected and removed.')

""" =========================Invitation Token Admin========================="""

@admin.register(InvitationToken)
class InvitationTokenAdmin(ModelAdmin): 
    list_display = (
        'token', 
        'get_team_name', 
        'get_coach_email', 
        'is_valid_display', 
        'is_active',
        'expires_at', 
        'created_at'
    )
    list_filter = ('is_active', 'expires_at', 'created_at')
    search_fields = ('token', 'team__name', 'coach__email')
    readonly_fields = ('token', 'created_at')
    autocomplete_fields = ('team', 'coach')
    
    actions = ['deactivate_tokens', 'activate_tokens', 'extend_expiry_7_days', 'extend_expiry_30_days']
    
    fieldsets = (
        ('Token Information', {
            'fields': ('token', 'team', 'coach')
        }),
        ('Validity', {
            'fields': ('is_active', 'expires_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def get_team_name(self, obj):
        return obj.team.name
    get_team_name.short_description = 'Team'
    
    def get_coach_email(self, obj):
        return obj.coach.email
    get_coach_email.short_description = 'Coach Email'
    
    def is_valid_display(self, obj):
        return obj.is_valid()
    is_valid_display.boolean = True
    is_valid_display.short_description = 'Valid'
    
    @admin.action(description='🔒 Deactivate selected tokens')
    def deactivate_tokens(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} tokens deactivated.')
    
    @admin.action(description='🔓 Activate selected tokens')
    def activate_tokens(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} tokens activated.')
    
    @admin.action(description='📅 Extend expiry by 7 days')
    def extend_expiry_7_days(self, request, queryset):
        for token in queryset:
            token.expires_at = timezone.now() + timedelta(days=7)
            token.save()
        self.message_user(request, f'{queryset.count()} tokens extended by 7 days.')
    
    @admin.action(description='📅 Extend expiry by 30 days')
    def extend_expiry_30_days(self, request, queryset):
        for token in queryset:
            token.expires_at = timezone.now() + timedelta(days=30)
            token.save()
        self.message_user(request, f'{queryset.count()} tokens extended by 30 days.')