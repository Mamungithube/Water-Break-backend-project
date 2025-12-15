from django.contrib import admin
# Register your models here.
from .models import User, Profile
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

class UserAdmin(BaseUserAdmin):
    ordering = ('Fullname',)
    list_display = ('email', 'Fullname', 'is_staff', 'is_active', 'id')
    search_fields = ('email', 'Fullname')
    list_filter = ('is_staff', 'is_active')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('Fullname',)}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'Fullname', 'password1', 'password2', 'is_staff', 'is_active')
        }),
    )

admin.site.register(User, UserAdmin)
admin.site.register(Profile)