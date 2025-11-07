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
