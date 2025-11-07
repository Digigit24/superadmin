from django.contrib import admin
from apps.tenants.models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'trial_ends_at', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug', 'domain']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'domain', 'is_active')}),
        ('Database', {'fields': ('database_name', 'database_url')}),
        ('Configuration', {'fields': ('enabled_modules', 'settings', 'trial_ends_at')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
