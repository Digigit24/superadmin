import uuid
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings
from django.utils import timezone
from apps.tenants.models import Tenant


def default_integration_token_expiry():
    return timezone.now() + timedelta(days=3650)


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_super_admin', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    username = None
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True, unique=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    roles = models.ManyToManyField('Role', related_name='users', blank=True)
    is_super_admin = models.BooleanField(default=False, help_text="Platform super admin")
    profile_picture = models.URLField(max_length=500, blank=True, null=True)
    timezone = models.CharField(max_length=50, default='Asia/Kolkata')
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = CustomUserManager()
    
    class Meta:
        db_table = 'users'
        ordering = ['-date_joined']
    
    def __str__(self):
        return self.email
    
    def get_merged_permissions(self):
        """Get merged permissions from all active roles."""
        from apps.common.permissions import merge_role_permissions
        return merge_role_permissions(self.roles.filter(is_active=True))


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='roles')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    permissions = models.JSONField(
        default=dict, 
        help_text="Nested permissions JSON: {'crm': {'leads': {'view': 'team', 'create': true}}}"
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_roles')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'roles'
        unique_together = [['tenant', 'name']]
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.tenant.name})"


class IntegrationToken(models.Model):
    """
    Long-lived JWT service account owned by a tenant for server-to-server integrations.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='integration_tokens')
    name = models.CharField(max_length=150)
    integration_name = models.SlugField(
        max_length=150,
        help_text="Stable machine name, e.g. make_meta_leads"
    )
    service_account_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    email = models.EmailField(blank=True)
    enabled_modules = models.JSONField(
        default=list,
        help_text="Modules this token can access, e.g. ['crm']"
    )
    permissions = models.JSONField(
        default=dict,
        help_text="Nested permissions JSON, e.g. {'crm': {'leads': {'create': true}}}"
    )
    full_access = models.BooleanField(
        default=False,
        help_text="Grant all actions for the selected enabled modules."
    )
    is_active = models.BooleanField(default=True)
    token_jti = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    expires_at = models.DateTimeField(
        default=default_integration_token_expiry,
        help_text="JWT expiry. Default is approximately 10 years."
    )
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_integration_tokens'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'integration_tokens'
        unique_together = [['tenant', 'integration_name']]
        ordering = ['tenant__name', 'name']

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"

    @property
    def is_revoked(self):
        return self.revoked_at is not None

    def save(self, *args, **kwargs):
        if not self.email:
            self.email = f"{self.integration_name}@system.local"
        if not self.enabled_modules and self.tenant_id:
            self.enabled_modules = self.tenant.enabled_modules
        if self.full_access:
            self.permissions = self.build_full_access_permissions()
        super().save(*args, **kwargs)

    def build_full_access_permissions(self):
        from apps.common.constants import PERMISSION_SCHEMA

        modules = self.enabled_modules or []
        permissions = {}
        for module_key in modules:
            module_schema = PERMISSION_SCHEMA.get(module_key)
            if not module_schema:
                continue
            permissions[module_key] = {}
            for resource_key, resource_schema in module_schema.get('resources', {}).items():
                permissions[module_key][resource_key] = {}
                for action_key, action_schema in resource_schema.get('actions', {}).items():
                    permissions[module_key][resource_key][action_key] = (
                        'all' if action_schema.get('type') == 'scope' else True
                    )
        return permissions

    def rotate(self):
        self.token_jti = uuid.uuid4()
        self.revoked_at = None
        self.is_active = True
        self.save(update_fields=['token_jti', 'revoked_at', 'is_active', 'updated_at'])

    def revoke(self):
        self.revoked_at = timezone.now()
        self.is_active = False
        self.save(update_fields=['revoked_at', 'is_active', 'updated_at'])

    def mark_used(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at', 'updated_at'])

    def generate_jwt(self):
        import jwt
        from django.conf import settings

        now = timezone.now()
        payload = {
            'token_type': 'integration',
            'integration_name': self.integration_name,
            'jti': str(self.token_jti),
            'user_id': str(self.service_account_id),
            'email': self.email,
            'tenant_id': str(self.tenant.id),
            'tenant_slug': self.tenant.slug,
            'is_super_admin': False,
            'enabled_modules': self.enabled_modules,
            'permissions': self.permissions,
            'iat': int(now.timestamp()),
            'exp': int(self.expires_at.timestamp()),
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
