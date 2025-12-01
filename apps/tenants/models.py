import uuid
from django.db import models


class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    domain = models.CharField(max_length=255, blank=True, null=True)

    database_name = models.CharField(max_length=255, blank=True, null=True, help_text="Neon database name")
    database_url = models.TextField(blank=True, null=True, help_text="Neon PostgreSQL connection URL")

    enabled_modules = models.JSONField(default=list, help_text="List of enabled modules: ['crm', 'whatsapp', 'meetings']")
    settings = models.JSONField(default=dict, help_text="Tenant-specific configuration")

    is_active = models.BooleanField(default=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tenants'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class TenantImage(models.Model):
    """Model for storing multiple images for a tenant with labels/keys"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='gallery_images',
        help_text="The tenant this image belongs to"
    )
    image = models.ImageField(
        upload_to='tenant_gallery/%Y/%m/%d/',
        help_text="Image file"
    )
    label = models.CharField(
        max_length=100,
        help_text="Label/key for the image (e.g., 'logo', 'banner', 'profile')"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description for the image"
    )
    order = models.IntegerField(
        default=0,
        help_text="Order of the image in the gallery"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this image is active"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tenant_images'
        ordering = ['tenant', 'order', '-created_at']
        unique_together = [['tenant', 'label']]
        indexes = [
            models.Index(fields=['tenant', 'label']),
            models.Index(fields=['tenant', 'is_active']),
        ]

    def __str__(self):
        return f"{self.tenant.name} - {self.label}"
