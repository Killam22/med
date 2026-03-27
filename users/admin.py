from django.contrib import admin

from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    permission_classes = (
        'delete', 'change',
    )
    list_display = ('first_name','last_name', 'email', 'role','phone','is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('first_name', 'last_name', 'email', 'password', 'role')}),
        ('Permissions', {'fields': ('is_staff', 'is_active')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'email', 'password1', 'password2', 'role', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('first_name', 'last_name', 'email', 'role')
    ordering = ('first_name',)

admin.site.register(CustomUser, CustomUserAdmin)