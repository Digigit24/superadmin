# apps/common/permissions.py

import logging

from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


def flatten_permissions(role_permissions_json):
    """
    Convert nested JSON permissions to flat dict.
    
    Example:
        Input: {"crm": {"leads": {"view": "team", "create": true}}}
        Output: {"crm.leads.view": "team", "crm.leads.create": true}
    """
    flat_perms = {}
    
    def flatten_recursive(data, prefix=""):
        for key, value in data.items():
            new_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict) and not all(isinstance(v, (bool, str)) for v in value.values()):
                flatten_recursive(value, new_key)
            elif isinstance(value, dict):
                for action, perm_value in value.items():
                    flat_perms[f"{new_key}.{action}"] = perm_value
            else:
                flat_perms[new_key] = value
    
    flatten_recursive(role_permissions_json)
    return flat_perms


def merge_role_permissions(user_roles):
    """
    Merge permissions from multiple roles.
    
    Rules:
    - For boolean permissions: True wins over False
    - For scope permissions: 'all' > 'team' > 'own'
    - Later roles override earlier roles with same priority
    """
    scope_hierarchy = {'own': 1, 'team': 2, 'all': 3}
    merged = {}
    
    for role in user_roles:
        if not role.is_active:
            continue
        
        flat_perms = flatten_permissions(role.permissions)
        
        for perm_key, perm_value in flat_perms.items():
            if perm_key not in merged:
                merged[perm_key] = perm_value
            else:
                current_value = merged[perm_key]
                
                if isinstance(perm_value, bool) and isinstance(current_value, bool):
                    merged[perm_key] = perm_value or current_value
                elif isinstance(perm_value, str) and isinstance(current_value, str):
                    if scope_hierarchy.get(perm_value, 0) > scope_hierarchy.get(current_value, 0):
                        merged[perm_key] = perm_value
                else:
                    merged[perm_key] = perm_value
    
    return merged


def has_permission(user_permissions, permission_string, resource_owner_id=None, user_id=None, user_team_id=None):
    """
    Check if user has permission.
    
    Args:
        user_permissions: Flattened permissions dict
        permission_string: e.g., "crm.leads.edit"
        resource_owner_id: UUID of resource owner (for 'own' scope check)
        user_id: UUID of current user
        user_team_id: UUID of user's team (for 'team' scope check)
    
    Returns:
        bool: True if user has permission
    """
    if permission_string not in user_permissions:
        # TEMPORARY migration reader: the canonical admin flag now has the
        # explicit action suffix. Remove after legacy grants are migrated.
        if permission_string == 'admin.full_access.enabled' and 'admin.full_access' in user_permissions:
            perm_value = user_permissions['admin.full_access']
            logger.warning('permission_legacy_admin_full_access_normalized')
        else:
            return False
    else:
        perm_value = user_permissions[permission_string]
    
    if isinstance(perm_value, bool):
        return perm_value
    
    if isinstance(perm_value, str):
        if perm_value == 'all':
            return True
        elif perm_value == 'team':
            return True
        elif perm_value == 'own':
            if resource_owner_id and user_id:
                return str(resource_owner_id) == str(user_id)
            return True
    
    return False


def is_platform_super_admin(request):
    """May this caller select an *arbitrary* tenant via ``x-tenant-id``?

    Only a platform super-admin. Nothing else on the platform is allowed to
    pick a tenant freely - see :func:`get_service_token_tenant_id` for the
    service path, which is pinned to a single tenant instead.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return False
    return bool(getattr(user, 'is_super_admin', False))


def get_service_token_tenant_id(request):
    """The single tenant a service/integration token is pinned to, or ``None``.

    An ``IntegrationToken`` is minted by, and belongs to, exactly one tenant,
    and ``IntegrationToken.generate_jwt()`` stamps that tenant on the
    ``tenant_id`` claim. Such a token is trusted to act for *that* tenant and
    for no other, so callers must scope to this value and must **not** let the
    request override it - being a service principal is not the same thing as
    being a super-admin.

    Fails closed: an integration token whose ``tenant_id`` claim is missing or
    unreadable resolves to no tenant at all rather than to a wide scope.
    """
    token = getattr(request, 'auth', None)
    getter = getattr(token, 'get', None)
    if not callable(getter):
        return None

    try:
        if getter('token_type') != 'integration':
            return None
        tenant_id = getter('tenant_id')
    except Exception:  # pragma: no cover - defensive, unknown auth object
        logger.warning('permission_service_token_unreadable')
        return None

    if not tenant_id:
        logger.warning('permission_service_token_missing_tenant_claim')
        return None

    return str(tenant_id)


class IsSuperAdmin(BasePermission):
    """
    Permission class for super admins only.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_super_admin


class IsTenantAdmin(BasePermission):
    """
    Permission class for tenant admins.
    Checks if user has admin role in their tenant.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_super_admin:
            return True
        
        user_perms = getattr(request.user, 'cached_permissions', None)
        if user_perms is None and hasattr(request.user, 'get_merged_permissions'):
            user_perms = request.user.get_merged_permissions()
        return has_permission(user_perms, 'admin.full_access.enabled')


class IsTenantMember(BasePermission):
    """
    Permission class to check if user belongs to a tenant.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.tenant is not None or request.user.is_super_admin
        )
