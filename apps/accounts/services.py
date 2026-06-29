from rest_framework_simplejwt.tokens import RefreshToken
from apps.common.permissions import merge_role_permissions


def get_tokens_for_user(user):
    """
    Generate JWT tokens with custom claims including flattened permissions.

    Claims added (must match digihms/common/middleware.py required_fields):
      user_id, email, tenant_id, tenant_slug, is_super_admin,
      permissions, enabled_modules, roles, tenant_name
    """
    refresh = RefreshToken.for_user(user)

    merged_permissions = user.get_merged_permissions() if not user.is_super_admin else {}

    # Collect role name strings for digihms role-based access control.
    role_names = list(user.roles.filter(is_active=True).values_list('name', flat=True))

    # Ensure 'hms' is present in enabled_modules so that digihms middleware
    # grants access.  We include the tenant's own modules plus 'hms'.
    raw_modules = user.tenant.enabled_modules if user.tenant else []
    enabled_modules = list(raw_modules) if isinstance(raw_modules, (list, tuple)) else []
    if 'hms' not in enabled_modules:
        enabled_modules = enabled_modules + ['hms']

    tenant_id = str(user.tenant.id) if user.tenant else None
    tenant_slug = user.tenant.slug if user.tenant else None
    tenant_name = user.tenant.name if user.tenant else None

    for token in (refresh, refresh.access_token):
        token['email'] = user.email
        token['tenant_id'] = tenant_id
        token['tenant_slug'] = tenant_slug
        token['tenant_name'] = tenant_name
        token['is_super_admin'] = user.is_super_admin
        token['permissions'] = merged_permissions
        token['enabled_modules'] = enabled_modules
        token['roles'] = role_names

    access_token = refresh.access_token

    return {
        'refresh': str(refresh),
        'access': str(access_token),
    }
