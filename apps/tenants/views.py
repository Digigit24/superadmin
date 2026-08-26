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
from apps.common.permissions import IsSuperAdmin, IsSuperAdminOrOwnTenant, IsTenantAdmin


class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer

    def get_permissions(self):
        # NOTE: this override shadows the `permission_classes` kwarg on any
        # individual `@action` below — DRF only consults that kwarg via the
        # DEFAULT `get_permissions()`, which this class replaces. Every
        # action needing something other than `IsSuperAdmin` must be listed
        # here explicitly, or its `@action(permission_classes=[...])` is
        # silently dead code. Confirmed the hard way: `whatsapp_credentials`
        # briefly declared `IsSuperAdminOrOwnTenant` on the action itself
        # while this method still fell through to `IsSuperAdmin` — every
        # regular tenant user got a 403 despite the "own tenant" class
        # working correctly in isolation.
        if self.action in ['me', 'update_me']:
            return [IsTenantAdmin()]
        if self.action == 'whatsapp_credentials':
            return [IsSuperAdminOrOwnTenant()]
        return [IsSuperAdmin()]

    @action(detail=False, methods=['get'], permission_classes=[IsTenantAdmin])
    def me(self, request):
        tenant = request.user.tenant
        if not tenant:
            return Response({'error': 'User not associated with any tenant'}, status=400)
        serializer = self.get_serializer(tenant)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['get'],
        url_path='whatsapp-credentials',
        permission_classes=[IsSuperAdminOrOwnTenant],
    )
    def whatsapp_credentials(self, request, pk=None):
        """
        The tenant's WhatsApp vendor credential, for DigiCRM's server-to-server use.

        DigiCRM needs this to call the Laravel WhatsApp gateway on the tenant's
        behalf. It is stored in `Tenant.settings` by the Admin Settings screen,
        which is the only self-serve UI for it.

        Deliberately NOT the tenant detail endpoint, even though a super-admin
        service token could call that: `TenantSerializer` also exposes
        `database_url`, and a credential lookup has no business handing a
        database URL to another service. This returns the two fields it needs
        and nothing else.

        `IsSuperAdminOrOwnTenant`, not `IsSuperAdmin` alone: DigiCRM calls this
        by forwarding the CALLER'S OWN already-verified JWT (the logged-in
        tenant user's token, from the incoming request it's handling) rather
        than a separately-minted, manually-rotated static service credential.
        That means the caller is almost always a regular tenant user, not a
        super-admin — so the permission has to allow "this token's own tenant,
        and only its own tenant" as well as genuine super-admins. `pk` in the
        URL is checked against the JWT's `tenant_id` claim in
        `IsSuperAdminOrOwnTenant` itself; a tenant can never reach another
        tenant's credential this way.
        """
        tenant = self.get_object()
        settings_blob = tenant.settings if isinstance(tenant.settings, dict) else {}
        vendor_uid = (settings_blob.get('whatsapp_vendor_uid') or '').strip()
        api_token = (settings_blob.get('whatsapp_api_token') or '').strip()

        return Response({
            'tenant_id': str(tenant.id),
            'vendor_uid': vendor_uid or None,
            'api_token': api_token or None,
            # Optional per-tenant gateway override; almost always unset.
            'base_url': (settings_blob.get('whatsapp_base_url') or '').strip() or None,
            'configured': bool(vendor_uid and api_token),
        })

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
