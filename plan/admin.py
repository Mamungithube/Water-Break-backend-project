from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Drill


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