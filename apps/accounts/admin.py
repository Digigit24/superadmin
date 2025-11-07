from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from apps.accounts.models import CustomUser, Role


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'tenant', 'is_super_admin', 'is_active', 'date_joined']
    list_filter = ['is_super_admin', 'is_active', 'tenant', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone', 'profile_picture', 'timezone')}),
        ('Tenant & Roles', {'fields': ('tenant', 'roles', 'is_super_admin')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'tenant', 'is_super_admin'),
        }),
    )
    
    filter_horizontal = ('roles', 'groups', 'user_permissions')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active', 'tenant', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {'fields': ('tenant', 'name', 'description', 'is_active')}),
        ('Permissions', {'fields': ('permissions',)}),
        ('Metadata', {'fields': ('created_by', 'created_at', 'updated_at')}),
    )
