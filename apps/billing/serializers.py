from rest_framework import serializers
from apps.billing.models import SubscriptionPlan, Subscription, Invoice


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = Subscription
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class InvoiceSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = Invoice
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'subscription', 'invoice_number', 'created_at', 'updated_at']
