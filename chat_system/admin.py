from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from django.utils.html import format_html
from .models import TeamChatMessage


@admin.register(TeamChatMessage)
class TeamChatMessageAdmin(ModelAdmin):
    list_display = [
        'id',
        'team',
        'get_sender_info',  # Custom method
        'truncated_message',  # Custom method for message preview
        'created_at_formatted',  # Custom formatted date
    ]
    
    list_display_links = ['id', 'team']  # Make these clickable
    
    list_filter = [
        'team',
        'created_at',
        'sender',  # You can filter by sender too
    ]
    
    search_fields = [
        'sender__email',
        'sender__first_name',
        'sender__last_name',
        'team__name',
        'message'
    ]
    
    readonly_fields = ['created_at', 'get_message_preview']
    
    date_hierarchy = 'created_at'
    
    list_per_page = 25
    
    ordering = ['-created_at']
    
    list_filter_submit = True
    
    fieldsets = (
        ('Message Details', {
            'fields': ('team', 'sender', 'created_at')
        }),
        ('Message Content', {
            'fields': ('message', 'get_message_preview'),
            'classes': ('wide',),
        }),
    )
    
    @display(description="Sender", ordering="sender__email")
    def get_sender_info(self, obj):
        """Display sender with full name and email"""
        if obj.sender.first_name and obj.sender.last_name:
            return f"{obj.sender.get_full_name()} ({obj.sender.email})"
        return obj.sender.email
    
    @display(description="Message", ordering="message")
    def truncated_message(self, obj):
        """Show truncated message in list view"""
        if len(obj.message) > 50:
            return f"{obj.message[:50]}..."
        return obj.message
    
    @display(description="Sent At")
    def created_at_formatted(self, obj):
        """Format the created_at date nicely"""
        return obj.created_at.strftime("%Y-%m-%d %H:%M")
    
    @display(description="Full Message Preview")
    def get_message_preview(self, obj):
        """Show message in detail view with line breaks"""
        return format_html('<div style="black-space: pre-wrap; padding: 10px; border-radius: 5px;">{}</div>', obj.message)
    
    # Optional: Add custom actions
    actions = ['mark_as_important']
    
    @admin.action(description="Mark selected messages as important")
    def mark_as_important(self, request, queryset):
        # You can add custom logic here
        self.message_user(request, f"{queryset.count()} messages marked as important")