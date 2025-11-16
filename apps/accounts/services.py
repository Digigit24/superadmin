from rest_framework_simplejwt.tokens import RefreshToken
from apps.common.permissions import merge_role_permissions
from apps.common.logger import get_logger

logger = get_logger(__name__)


def get_tokens_for_user(user):
    """
    Generate JWT tokens with custom claims including flattened permissions.
    """
    try:
        logger.info(f'Starting token generation for user: {user.email} (ID: {user.id})')

        # Log user state for debugging
        logger.debug(f'User details - is_super_admin: {user.is_super_admin}, '
                    f'is_active: {user.is_active}, has_tenant: {user.tenant is not None}')

        # Generate base refresh token
        refresh = RefreshToken.for_user(user)
        logger.debug(f'Base refresh token generated for user: {user.email}')

        # Get merged permissions with error handling
        try:
            merged_permissions = user.get_merged_permissions() if not user.is_super_admin else {}
            logger.debug(f'Merged permissions retrieved for user: {user.email}, '
                        f'permission_count: {len(merged_permissions)}')
        except Exception as perm_error:
            logger.error(f'Error getting merged permissions for user {user.email}: {str(perm_error)}',
                        exc_info=True)
            merged_permissions = {}

        # Safely get tenant information
        tenant_id = None
        tenant_slug = None
        enabled_modules = []

        if user.tenant:
            try:
                tenant_id = str(user.tenant.id)
                tenant_slug = user.tenant.slug
                # Safely access enabled_modules with fallback
                enabled_modules = user.tenant.enabled_modules if user.tenant.enabled_modules is not None else []
                logger.debug(f'Tenant info retrieved - ID: {tenant_id}, slug: {tenant_slug}, '
                           f'modules: {enabled_modules}')
            except AttributeError as attr_error:
                logger.error(f'AttributeError accessing tenant data for user {user.email}: {str(attr_error)}',
                           exc_info=True)
                # Continue with None values
            except Exception as tenant_error:
                logger.error(f'Unexpected error accessing tenant for user {user.email}: {str(tenant_error)}',
                           exc_info=True)
                # Continue with None values
        else:
            logger.debug(f'No tenant associated with user: {user.email}')

        # Add custom claims to refresh token
        try:
            refresh['email'] = user.email
            refresh['tenant_id'] = tenant_id
            refresh['tenant_slug'] = tenant_slug
            refresh['is_super_admin'] = user.is_super_admin
            refresh['permissions'] = merged_permissions
            refresh['enabled_modules'] = enabled_modules
            logger.debug(f'Custom claims added to refresh token for user: {user.email}')
        except Exception as claim_error:
            logger.error(f'Error adding custom claims to refresh token for user {user.email}: {str(claim_error)}',
                        exc_info=True)
            raise

        # Generate access token with same claims
        try:
            access_token = refresh.access_token
            access_token['email'] = user.email
            access_token['tenant_id'] = tenant_id
            access_token['tenant_slug'] = tenant_slug
            access_token['is_super_admin'] = user.is_super_admin
            access_token['permissions'] = merged_permissions
            access_token['enabled_modules'] = enabled_modules
            logger.debug(f'Custom claims added to access token for user: {user.email}')
        except Exception as access_error:
            logger.error(f'Error generating access token for user {user.email}: {str(access_error)}',
                        exc_info=True)
            raise

        token_data = {
            'refresh': str(refresh),
            'access': str(access_token),
        }

        logger.info(f'Tokens successfully generated for user: {user.email}')
        return token_data

    except Exception as e:
        logger.error(f'CRITICAL: Failed to generate tokens for user {user.email if user else "Unknown"}: {str(e)}',
                    exc_info=True)
        raise
