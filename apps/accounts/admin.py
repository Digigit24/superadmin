from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from django.utils.html import format_html
from apps.accounts.models import CustomUser, Role, IntegrationToken


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


@admin.register(IntegrationToken)
class IntegrationTokenAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'integration_name', 'tenant', 'full_access', 'is_active',
        'revoked_at', 'last_used_at', 'expires_at'
    ]
    list_filter = ['is_active', 'full_access', 'tenant', 'created_at', 'expires_at']
    search_fields = ['name', 'integration_name', 'email', 'tenant__name', 'tenant__slug']
    readonly_fields = [
        'service_account_id', 'token_jti', 'generated_token', 'created_by',
        'created_at', 'updated_at', 'last_used_at', 'revoked_at'
    ]
    actions = ['rotate_tokens', 'revoke_tokens', 'reactivate_tokens']

    fieldsets = (
        (None, {
            'fields': ('tenant', 'name', 'integration_name', 'email', 'is_active')
        }),
        ('Access', {
            'fields': ('full_access', 'enabled_modules', 'permissions')
        }),
        ('System Token', {
            'fields': ('generated_token', 'expires_at', 'token_jti', 'service_account_id')
        }),
        ('Audit Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at', 'last_used_at', 'revoked_at')
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        self.message_user(
            request,
            "Integration token created. Open this record and copy the System Token value."
        )
        return super().response_add(request, obj, post_url_continue)

    @admin.display(description='Current system access token')
    def generated_token(self, obj):
        if not obj.pk:
            return "Save the token first, then copy it from this field."
        if obj.revoked_at or not obj.is_active:
            return "This token is revoked/inactive. Rotate or reactivate it before use."
        token = obj.generate_jwt()
        return format_html(
            '<textarea rows="8" style="width: 100%; font-family: monospace;" readonly>{}</textarea>',
            token
        )

    @admin.action(description='Rotate selected tokens')
    def rotate_tokens(self, request, queryset):
        for token in queryset:
            token.rotate()
        self.message_user(request, f"Rotated {queryset.count()} integration token(s).")

    @admin.action(description='Revoke selected tokens')
    def revoke_tokens(self, request, queryset):
        updated = queryset.update(is_active=False, revoked_at=timezone.now())
        self.message_user(request, f"Revoked {updated} integration token(s).")

    @admin.action(description='Reactivate selected tokens')
    def reactivate_tokens(self, request, queryset):
        updated = queryset.update(is_active=True, revoked_at=None)
        self.message_user(request, f"Reactivated {updated} integration token(s).")
