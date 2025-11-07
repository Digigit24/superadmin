from django.contrib import admin
from apps.billing.models import SubscriptionPlan, Subscription, Invoice


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'price_monthly', 'price_yearly', 'is_trial', 'is_active', 'sort_order']
    list_filter = ['is_trial', 'is_active', 'currency']
    search_fields = ['name', 'slug']
    ordering = ['sort_order', 'name']
    
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'description', 'is_active', 'sort_order')}),
        ('Pricing', {'fields': ('price_monthly', 'price_yearly', 'currency')}),
        ('Limits', {'fields': ('max_users', 'max_leads', 'storage_gb')}),
        ('Features', {'fields': ('included_modules', 'features')}),
        ('Trial', {'fields': ('is_trial', 'trial_days')}),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'plan', 'status', 'billing_cycle', 'current_period_end', 'cancel_at_period_end']
    list_filter = ['status', 'billing_cycle', 'cancel_at_period_end']
    search_fields = ['tenant__name', 'plan__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {'fields': ('tenant', 'plan', 'status', 'billing_cycle')}),
        ('Period', {'fields': ('current_period_start', 'current_period_end')}),
        ('Cancellation', {'fields': ('cancel_at_period_end', 'cancelled_at')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'tenant', 'amount', 'status', 'due_date', 'paid_at']
    list_filter = ['status', 'created_at']
    search_fields = ['invoice_number', 'tenant__name']
    readonly_fields = ['invoice_number', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {'fields': ('invoice_number', 'tenant', 'subscription')}),
        ('Amount', {'fields': ('amount', 'currency', 'status')}),
        ('Dates', {'fields': ('due_date', 'paid_at', 'invoice_url')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    
    actions = ['mark_as_paid']
    
    def mark_as_paid(self, request, queryset):
        from datetime import datetime
        count = queryset.update(status='PAID', paid_at=datetime.now())
        self.message_user(request, f'{count} invoices marked as paid.')
    mark_as_paid.short_description = 'Mark selected invoices as paid'
