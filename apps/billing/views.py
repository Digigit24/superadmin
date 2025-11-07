from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.billing.models import SubscriptionPlan, Subscription, Invoice
from apps.billing.serializers import SubscriptionPlanSerializer, SubscriptionSerializer, InvoiceSerializer
from apps.common.permissions import IsTenantAdmin
from datetime import datetime, timedelta


class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.AllowAny]


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsTenantAdmin]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin:
            return Subscription.objects.all()
        elif user.tenant:
            return Subscription.objects.filter(tenant=user.tenant)
        return Subscription.objects.none()
    
    @action(detail=False, methods=['get'])
    def my_subscription(self, request):
        if not request.user.tenant:
            return Response({'error': 'No tenant associated'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            subscription = Subscription.objects.get(tenant=request.user.tenant)
            return Response(self.get_serializer(subscription).data)
        except Subscription.DoesNotExist:
            return Response({'error': 'No active subscription'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def subscribe(self, request):
        plan_id = request.data.get('plan_id')
        billing_cycle = request.data.get('billing_cycle', 'MONTHLY')
        
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({'error': 'Plan not found'}, status=status.HTTP_404_NOT_FOUND)
        
        tenant = request.user.tenant
        subscription, created = Subscription.objects.get_or_create(
            tenant=tenant,
            defaults={
                'plan': plan,
                'billing_cycle': billing_cycle,
                'status': 'TRIAL' if plan.is_trial else 'ACTIVE',
                'current_period_start': datetime.now(),
                'current_period_end': datetime.now() + timedelta(days=30)
            }
        )
        
        if not created:
            subscription.plan = plan
            subscription.billing_cycle = billing_cycle
            subscription.status = 'ACTIVE'
            subscription.save()
        
        return Response(self.get_serializer(subscription).data)
    
    @action(detail=False, methods=['post'])
    def cancel(self, request):
        try:
            subscription = Subscription.objects.get(tenant=request.user.tenant)
            subscription.cancel_at_period_end = True
            subscription.cancelled_at = datetime.now()
            subscription.save()
            return Response({'message': 'Subscription will be cancelled at period end'})
        except Subscription.DoesNotExist:
            return Response({'error': 'No active subscription'}, status=status.HTTP_404_NOT_FOUND)


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [IsTenantAdmin]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin:
            return Invoice.objects.all()
        elif user.tenant:
            return Invoice.objects.filter(tenant=user.tenant)
        return Invoice.objects.none()
