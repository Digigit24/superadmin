from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from apps.tenants.models import Tenant, TenantImage
from apps.tenants.serializers import (
    TenantSerializer,
    TenantImageSerializer,
    TenantImageCreateSerializer
)
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


class TenantImageViewSet(viewsets.ModelViewSet):
    """ViewSet for managing tenant gallery images"""
    queryset = TenantImage.objects.all()
    serializer_class = TenantImageSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ['tenant', 'label', 'is_active']
    search_fields = ['label', 'description']
    ordering_fields = ['order', 'created_at', 'label']

    def get_permissions(self):
        """Allow tenant admins to manage their own images"""
        if self.action in ['list', 'retrieve']:
            return [IsTenantAdmin()]
        return [IsTenantAdmin()]

    def get_queryset(self):
        """Filter images based on user's tenant"""
        queryset = super().get_queryset()
        user = self.request.user

        # SuperAdmins can see all images
        if user.role == 'superadmin':
            return queryset

        # Tenant admins and users can only see their tenant's images
        if user.tenant:
            return queryset.filter(tenant=user.tenant)

        return queryset.none()

    def get_serializer_class(self):
        """Use different serializer for create/update"""
        if self.action in ['create', 'update', 'partial_update']:
            return TenantImageCreateSerializer
        return TenantImageSerializer

    def perform_create(self, serializer):
        """Automatically set the tenant when creating an image"""
        user = self.request.user

        # SuperAdmins must specify tenant explicitly
        if user.role == 'superadmin':
            if 'tenant' not in self.request.data:
                raise serializers.ValidationError({
                    'tenant': 'SuperAdmins must specify a tenant_id'
                })
            tenant_id = self.request.data.get('tenant')
            try:
                tenant = Tenant.objects.get(id=tenant_id)
            except Tenant.DoesNotExist:
                raise serializers.ValidationError({
                    'tenant': 'Tenant not found'
                })
            serializer.save(tenant=tenant)
        else:
            # Regular users use their own tenant
            if not user.tenant:
                raise serializers.ValidationError({
                    'error': 'User not associated with any tenant'
                })
            serializer.save(tenant=user.tenant)

    @action(detail=False, methods=['get'], permission_classes=[IsTenantAdmin])
    def by_label(self, request):
        """Get images filtered by label for the current tenant"""
        label = request.query_params.get('label')
        if not label:
            return Response(
                {'error': 'Label parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        queryset = self.get_queryset().filter(label=label, is_active=True)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['delete'], permission_classes=[IsTenantAdmin])
    def delete_by_label(self, request):
        """Delete all images with a specific label for the current tenant"""
        label = request.query_params.get('label')
        if not label:
            return Response(
                {'error': 'Label parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        queryset = self.get_queryset().filter(label=label)
        count = queryset.count()
        queryset.delete()

        return Response(
            {'message': f'Deleted {count} image(s) with label "{label}"'},
            status=status.HTTP_200_OK
        )
