
from .models import Privacy_Policy, TermsAndConditions, AboutUs
# Register your models here.

from django.contrib import admin
from unfold.admin import ModelAdmin

@admin.register(Privacy_Policy)
class PrivacyPolicyAdmin(ModelAdmin):
    list_display = ('updated_at',)
    
    fieldsets = (
        ("Privacy Policy Content", {
            "classes": ["wide"],
            "fields": (
                "content",
            ),
        }),
        ("Dates", {
            "classes": ["wide"],
            "fields": (
                "created_at",
                "updated_at",
            ),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(TermsAndConditions)
class TermsAndConditionsAdmin(ModelAdmin):  
    list_display = ('updated_at',)
    
    fieldsets = (
        ("Terms and Conditions Content", {
            "classes": ["wide"],
            "fields": (
                "content",
            ),
        }),
        ("Dates", {
            "classes": ["wide"],
            "fields": (
                "created_at",
                "updated_at",
            ),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')

@admin.register(AboutUs)
class AboutUsAdmin(ModelAdmin):  
    list_display = ('updated_at',)
    
    fieldsets = (
        ("About Us Content", {
            "classes": ["wide"],
            "fields": (
                "content",
            ),
        }),
        ("Dates", {
            "classes": ["wide"],
            "fields": (
                "created_at",
                "updated_at",
            ),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')