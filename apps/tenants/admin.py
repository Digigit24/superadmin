from django.contrib import admin
from apps.tenants.models import Tenant
from apps.accounts.models import IntegrationToken


class IntegrationTokenInline(admin.TabularInline):
    model = IntegrationToken
    extra = 0
    fields = [
        'name', 'integration_name', 'full_access', 'enabled_modules',
        'is_active', 'expires_at', 'last_used_at', 'revoked_at'
    ]
    readonly_fields = ['last_used_at', 'revoked_at']
    show_change_link = True


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'trial_ends_at', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug', 'domain']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [IntegrationTokenInline]
    
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'domain', 'is_active')}),
        ('Database', {'fields': ('database_name', 'database_url')}),
        ('Configuration', {'fields': ('enabled_modules', 'settings', 'trial_ends_at')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
