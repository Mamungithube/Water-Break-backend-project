from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Drill, Block, plan, Notification, Reminder


@admin.register(Drill)
class DrillAdmin(ModelAdmin):
    list_display = ["name", "id", "get_assign_teams", "assistant_coach", "category", "create_By", "date_created"]  # ✅ CHANGE - assistant_coach added
    list_filter = ["category", "date_created"]
    search_fields = ["name", "category", "description"]
    
    fieldsets = (
        ("Main Information", {
            "fields": (
                "name",
                "assign_team",
                "category",
                "description",
            )
        }),
        # ✅ NEW FIELDSET - নতুন fields এর জন্য
        ("Team Assignment", {
            "fields": (
                "assigned_members",
                "assistant_coach",
            )
        }),
    )
    
    readonly_fields = ["create_By", "date_created", "date_modified"]
    
    # ✅ NEW - ManyToMany field এর জন্য filter_horizontal
    filter_horizontal = ['assign_team', 'assigned_members']
    
    def save_model(self, request, obj, form, change):
        """Automatically set create_By to current logged-in user"""
        if not change:  
            obj.create_By = request.user
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        """Edit করার সময় create_By field readonly থাকবে"""
        if obj:
            return self.readonly_fields + ["create_By"]
        return self.readonly_fields

    def get_assign_teams(self, obj):
        return ", ".join([t.name for t in obj.assign_team.all()])
    get_assign_teams.short_description = "Assigned Teams"


@admin.register(Block)
class BlockAdmin(ModelAdmin):
    list_display = ["title", "id", "drill", "practice_plan", "start_time", "end_time", "created_at"]
    list_filter = ["drill", "practice_plan", "start_time"]
    search_fields = ["title", "drill__name"]
    
    fieldsets = (
        ("Main Information", {
            "fields": (
                "drill",
                "practice_plan",
                "title",
                "color_code",
            )
        }),
        ("Time Schedule", {
            "fields": (
                "start_time",
                "end_time",
            )
        }),
    )
    
    readonly_fields = ["created_at", "updated_at"]


@admin.register(plan)
class PlanAdmin(ModelAdmin):
    list_display = ["id", "get_teams", "plan_title", "create_By", "get_plan_blocks", "start_practice_time", "end_practice_time", "created_at"] 
    list_filter = ["start_practice_time", "created_at"]
    search_fields = ["plan_title", "create_By__username"]
    
    fieldsets = (
        ("Main Information", {
            "fields": (
                "create_By",
                "plan_title",
            )
        }),
        ("Schedule", {
            "fields": (
                "start_practice_time",
                "end_practice_time",
            )
        }),
    )
    
    readonly_fields = ["create_By", "created_at", "updated_at"]
    
    def save_model(self, request, obj, form, change):
        """Automatically set create_By to current logged-in user"""
        if not change:
            obj.create_By = request.user
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        """Edit করার সময় create_By field readonly থাকবে"""
        if obj:
            return self.readonly_fields + ["create_By"]
        return self.readonly_fields
    
    def get_plan_blocks(self, obj):
        blocks = obj.Plan_Block.all()
        if blocks.exists():
            return ", ".join([b.title for b in blocks])
        return "No blocks"
    get_plan_blocks.short_description = "Blocks"
    
    def get_teams(self, obj):
        if hasattr(obj.assign_team, 'all'):
            return ", ".join([team.name for team in obj.assign_team.all()])
        return obj.assign_team.name if obj.assign_team else "No Team"
    
    get_teams.short_description = "Assigned Team"


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ["title", "user", "read", "created_at"]
    list_filter = ["read", "created_at"]
    search_fields = ["title", "message", "user__username", "user__email"]
    readonly_fields = ["created_at"]
    
    fieldsets = (
        ("Notification Details", {
            "fields": (
                "user",
                "title",
                "message",
                "read",
            )
        }),
        ("Metadata", {
            "fields": (
                "created_at",
            )
        }),
    )


@admin.register(Reminder)
class ReminderAdmin(ModelAdmin):
    list_display = ["created_for", "content_type", "object_id", "send_at", "sent", "sent_at"]
    list_filter = ["sent", "send_at", "method_email", "method_notification"]
    search_fields = ["created_for__username", "created_for__email"]
    readonly_fields = ["content_type", "object_id", "sent_at", "created_at"]
    
    fieldsets = (
        ("Reminder Target", {
            "fields": (
                "content_type",
                "object_id",
                "created_for",
            )
        }),
        ("Schedule", {
            "fields": (
                "send_at",
                "sent",
                "sent_at",
            )
        }),
        ("Methods", {
            "fields": (
                "method_email",
                "method_notification",
            )
        }),
    )