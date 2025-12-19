from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Drill, Block ,plan


@admin.register(Drill)
class DrillAdmin(ModelAdmin):
    # ড্যাশবোর্ডে কোন কলামগুলো দেখাবে
    list_display = ["name", "category"]
    fieldsets = (
        ("main information", {
            "fields": (
                "name",
                "category",
                "description",
            )
        }),
    )


@admin.register(Block)
class BlockAdmin(ModelAdmin):
    # ড্যাশবোর্ডে কোন কলামগুলো দেখাবে
    list_display = ["title", "assign_team", "drill", "start_time", "end_time"]
    fieldsets = (
        ("main information", {
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
class planAdmin(ModelAdmin):
    list_display = ["plan_title","Drill", "prectice_time"]
    fieldsets = (
        ("main information", {
            "fields": (
                "plan_title",
                "Drill",
                "prectice_time",
            )
        }),
    )