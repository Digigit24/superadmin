from rest_framework_simplejwt.tokens import RefreshToken
from apps.common.permissions import merge_role_permissions


def get_tokens_for_user(user):
    """
    Generate JWT tokens with custom claims including flattened permissions.
    """
    refresh = RefreshToken.for_user(user)
    
    merged_permissions = user.get_merged_permissions() if not user.is_super_admin else {}
    
    refresh['email'] = user.email
    refresh['tenant_id'] = str(user.tenant.id) if user.tenant else None
    refresh['tenant_slug'] = user.tenant.slug if user.tenant else None
    refresh['is_super_admin'] = user.is_super_admin
    refresh['permissions'] = merged_permissions
    refresh['enabled_modules'] = user.tenant.enabled_modules if user.tenant else []
    
    access_token = refresh.access_token
    access_token['email'] = user.email
    access_token['tenant_id'] = str(user.tenant.id) if user.tenant else None
    access_token['tenant_slug'] = user.tenant.slug if user.tenant else None
    access_token['is_super_admin'] = user.is_super_admin
    access_token['permissions'] = merged_permissions
    access_token['enabled_modules'] = user.tenant.enabled_modules if user.tenant else []
    
    return {
        'refresh': str(refresh),
        'access': str(access_token),
    }
