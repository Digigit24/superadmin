import uuid
from django.db import models
from apps.tenants.models import Tenant
from apps.common.constants import (
    SUBSCRIPTION_STATUS_CHOICES, 
    BILLING_CYCLE_CHOICES, 
    INVOICE_STATUS_CHOICES
)


class SubscriptionPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    
    max_users = models.IntegerField(null=True, blank=True, help_text="null = unlimited")
    max_leads = models.IntegerField(null=True, blank=True, help_text="null = unlimited")
    storage_gb = models.IntegerField(null=True, blank=True, help_text="null = unlimited")
    
    included_modules = models.JSONField(default=list, help_text="List of module slugs: ['crm', 'whatsapp']")
    features = models.JSONField(default=list, help_text="List of feature descriptions")
    
    is_trial = models.BooleanField(default=False)
    trial_days = models.IntegerField(default=14)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscription_plans'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name


class Subscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    
    status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS_CHOICES, default='TRIAL')
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default='MONTHLY')
    
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    
    cancel_at_period_end = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscriptions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.tenant.name} - {self.plan.name} ({self.status})"


class Invoice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='invoices')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=50, unique=True, editable=False)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default='PENDING')
    
    due_date = models.DateTimeField()
    paid_at = models.DateTimeField(null=True, blank=True)
    invoice_url = models.URLField(max_length=500, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'invoices'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.tenant.name}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last_invoice = Invoice.objects.order_by('-created_at').first()
            if last_invoice and last_invoice.invoice_number:
                try:
                    last_num = int(last_invoice.invoice_number.split('-')[-1])
                    self.invoice_number = f"INV-{last_num + 1:06d}"
                except (ValueError, IndexError):
                    self.invoice_number = f"INV-{Invoice.objects.count() + 1:06d}"
            else:
                self.invoice_number = "INV-000001"
        super().save(*args, **kwargs)
