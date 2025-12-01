from django.contrib import admin
from apps.tenants.models import Tenant, TenantImage


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


@admin.register(TenantImage)
class TenantImageAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'label', 'order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'tenant']
    search_fields = ['label', 'description', 'tenant__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['tenant', 'order', '-created_at']

    fieldsets = (
        (None, {'fields': ('tenant', 'image', 'label', 'description')}),
        ('Options', {'fields': ('order', 'is_active')}),
        ('Metadata', {'fields': ('id', 'created_at', 'updated_at')}),
    )
