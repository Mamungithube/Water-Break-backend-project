from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import TeamChatMessage


@admin.register(TeamChatMessage)
class TeamChatMessageAdmin(ModelAdmin):
    list_display = [
        'id', 


    ]
    list_filter = [
        'team', 
        'created_at',
    ]
    search_fields = [
        'sender__email', 
        'sender__first_name',
        'sender__last_name',
        'team__name', 
        'message'
    ]
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    list_per_page = 25
    ordering = ['-created_at']
    

    list_filter_submit = True
    
    