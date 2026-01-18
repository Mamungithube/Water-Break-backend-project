from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Drill, Block, plan


@admin.register(Drill)
class DrillAdmin(ModelAdmin):
    list_display = ["name", "get_assign_teams", "category", "create_By", "date_created"]
    
    fieldsets = (
        ("Main Information", {
            "fields": (
                "name",
                "assign_team",
                "category",
                "description",
            )
        }),
    )
    
    readonly_fields = ["create_By", "date_created", "date_modified"]
    
    def save_model(self, request, obj, form, change):
        """
        Automatically set create_By to current logged-in user
        """
        if not change:  
            obj.create_By = request.user
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        """
        Edit করার সময় create_By field readonly থাকবে
        """
        if obj:  # editing existing object
            return self.readonly_fields + ["create_By"]
        return self.readonly_fields

    def get_assign_teams(self, obj):
        return ", ".join([t.name for t in obj.assign_team.all()])
    get_assign_teams.short_description = "Assign Teams"


@admin.register(Block)
class BlockAdmin(ModelAdmin):
    list_display = ["title",  "drill", "start_time", "end_time"]
    list_filter = ["drill",  "start_time"]
    search_fields = ["title", "drill__name"]
    
    fieldsets = (
        ("Main Information", {
            "fields": (
                "drill",
                "title",
                "start_time",
                "end_time",
            )
        }),
    )


@admin.register(plan)
class PlanAdmin(ModelAdmin):
    list_display = ["plan_title", "prectice_time", "get_plan_blocks", "created_at"]
    list_filter = ["prectice_time"]
    search_fields = ["plan_title"]
    
    fieldsets = (
        ("Main Information", {
            "fields": (
                "plan_title",
                "Plan_Block",
                "prectice_time",
            )
        }),
    )

    def get_plan_blocks(self, obj):
        return ", ".join([b.title for b in obj.Plan_Block.all()])
    get_plan_blocks.short_description = "Blocks"