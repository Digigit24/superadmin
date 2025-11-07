import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from apps.tenants.models import Tenant


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
