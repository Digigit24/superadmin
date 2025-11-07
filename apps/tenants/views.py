from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.tenants.models import Tenant
from apps.tenants.serializers import TenantSerializer
from apps.common.permissions import IsSuperAdmin, IsTenantAdmin


class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    
    def get_permissions(self):
        if self.action in ['me', 'update_me']:
            return [IsTenantAdmin()]
        return [IsSuperAdmin()]
    
    @action(detail=False, methods=['get'], permission_classes=[IsTenantAdmin])
    def me(self, request):
        tenant = request.user.tenant
        if not tenant:
            return Response({'error': 'User not associated with any tenant'}, status=400)
        serializer = self.get_serializer(tenant)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'], permission_classes=[IsTenantAdmin])
    def update_me(self, request):
        tenant = request.user.tenant
        if not tenant:
            return Response({'error': 'User not associated with any tenant'}, status=400)
        serializer = self.get_serializer(tenant, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
