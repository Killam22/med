
# Register your models here.
# settings/admin.py
from django.contrib import admin
from .models import UserSettings, AccountDeletionRequest


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display  = ['user', 'language', 'theme', 'two_factor_enabled', 'updated_at']
    search_fields = ['user__email']
    list_filter   = ['language', 'theme', 'two_factor_enabled']


@admin.register(AccountDeletionRequest)
class AccountDeletionRequestAdmin(admin.ModelAdmin):
    list_display  = ['user', 'status', 'created_at', 'reviewed_at']
    list_filter   = ['status']
    search_fields = ['user__email']
    actions       = ['approve_requests']

    def approve_requests(self, request, queryset):
        from django.utils import timezone
        queryset.filter(status='pending').update(
            status='approved', reviewed_at=timezone.now()
        )
    approve_requests.short_description = 'Approve selected deletion requests'