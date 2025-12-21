from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Drill, Block, plan


@admin.register(Drill)
class DrillAdmin(ModelAdmin):
    # ড্যাশবোর্ডে কোন কলামগুলো দেখাবে
    list_display = ["name", "category", "create_By", "date_created"]
    
    fieldsets = (
        ("Main Information", {
            "fields": (
                "name",
                "category",
                "description",
            )
        }),
    )
    
    # create_By field টি readonly করে show করতে চাইলে
    readonly_fields = ["create_By", "date_created", "date_modified"]
    
    def save_model(self, request, obj, form, change):
        """
        Automatically set create_By to current logged-in user
        """
        if not change:  # শুধুমাত্র নতুন object create করার সময়
            obj.create_By = request.user
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        """
        Edit করার সময় create_By field readonly থাকবে
        """
        if obj:  # editing existing object
            return self.readonly_fields + ["create_By"]
        return self.readonly_fields


@admin.register(Block)
class BlockAdmin(ModelAdmin):
    # ড্যাশবোর্ডে কোন কলামগুলো দেখাবে
    list_display = ["title", "assign_team", "drill", "start_time", "end_time"]
    list_filter = ["drill", "assign_team", "start_time"]
    search_fields = ["title", "drill__name"]
    
    fieldsets = (
        ("Main Information", {
            "fields": (
                "assign_team",
                "drill",
                "title",
                "start_time",
                "end_time",
            )
        }),
    )


@admin.register(plan)
class PlanAdmin(ModelAdmin):
    list_display = ["plan_title", "Drill", "prectice_time", "created_at"]
    list_filter = ["Drill", "prectice_time"]
    search_fields = ["plan_title", "Drill__name"]
    
    fieldsets = (
        ("Main Information", {
            "fields": (
                "plan_title",
                "Drill",
                "prectice_time",
            )
        }),
    )