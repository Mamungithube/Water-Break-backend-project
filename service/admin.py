
from .models import FAQ, privacy_policy, termsandconditions, aboutus
# Register your models here.

from django.contrib import admin
from unfold.admin import ModelAdmin # Unfold এর ModelAdmin ব্যবহার করুন

@admin.register(FAQ)
class FAQAdmin(ModelAdmin):
    list_display = ('question', 'is_published', 'created_at')
    list_editable = ('is_published',)
    

    fieldsets = (
        ("FAQ Content", {
            "classes": ["wide"],
            "fields": (
                "question", 
                "answer",
            ),
        }),
        ("Status & Dates", {
            "classes": ["wide"],
            "fields": (
                "is_published",
                "created_at",
                "updated_at",
            ),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(privacy_policy)
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


@admin.register(termsandconditions)
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

@admin.register(aboutus)
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