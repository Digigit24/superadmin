from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from apps.accounts.models import CustomUser, Role
from apps.accounts.serializers import (
    UserSerializer, UserCreateSerializer, RoleSerializer,
    RegisterSerializer, LoginSerializer, ChangePasswordSerializer
)
from apps.accounts.services import get_tokens_for_user
from apps.common.permissions import IsSuperAdmin, IsTenantAdmin, IsTenantMember
from apps.common.constants import PERMISSION_SCHEMA
from apps.common.logger import get_logger

logger = get_logger(__name__)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        result = serializer.save()
        user = result['user']
        logger.info(f'New user registered: {user.email}')
        tokens = get_tokens_for_user(user)
        return Response({
            'message': 'Registration successful',
            'user': UserSerializer(user).data,
            'tokens': tokens
        }, status=status.HTTP_201_CREATED)
    logger.warning(f'Registration failed: {serializer.errors}')
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        user = authenticate(
            request,
            username=email,
            password=serializer.validated_data['password']
        )

        if user and user.is_active:
            logger.info(f'User logged in successfully: {user.email}, tenant: {user.tenant.slug if user.tenant else "No tenant"}')
            try:
                tokens = get_tokens_for_user(user)
                logger.debug(f'JWT tokens generated for user: {user.email}')
                return Response({
                    'message': 'Login successful',
                    'user': UserSerializer(user).data,
                    'tokens': tokens
                })
            except Exception as e:
                logger.error(f'Error generating tokens for user {user.email}: {str(e)}', exc_info=True)
                return Response({'error': 'Token generation failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.warning(f'Failed login attempt for email: {email}')
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    logger.warning(f'Invalid login request data: {serializer.errors}')
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def logout_view(request):
    try:
        refresh_token = request.data.get('refresh_token')
        token = RefreshToken(refresh_token)
        token.blacklist()
        logger.info(f'User logged out: {request.user.email}')
        return Response({'message': 'Logout successful'})
    except Exception as e:
        logger.warning(f'Logout failed for user {request.user}: {str(e)}')
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def change_password_view(request):
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({'error': 'Current password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'message': 'Password changed successfully'})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin:
            return CustomUser.objects.all()
        elif user.tenant:
            return CustomUser.objects.filter(tenant=user.tenant)
        return CustomUser.objects.none()
    
    def get_permissions(self):
        if self.action in ['me', 'update_me', 'create']:
            return [permissions.IsAuthenticated()]
        return [IsTenantAdmin()]
    
    def perform_create(self, serializer):
        user = self.request.user
        # Only set tenant from logged-in user if tenant is not provided in request
        if not user.is_super_admin and 'tenant' not in serializer.validated_data:
            serializer.save(tenant=user.tenant)
        else:
            serializer.save()

    def create(self, request, *args, **kwargs):
        logger.info(f'Create user request from: {request.user.email if request.user.is_authenticated else "Anonymous"}')
        logger.debug(f'Request data: {request.data}')

        # Security check: non-super-admins can only create users in their own tenant
        if not request.user.is_super_admin:
            tenant_id = request.data.get('tenant')
            if tenant_id:
                # Validate tenant exists and user has access
                if not request.user.tenant:
                    logger.error(f'User {request.user.email} has no tenant assigned')
                    return Response(
                        {'error': 'Your account is not associated with a tenant'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if str(request.user.tenant.id) != str(tenant_id):
                    logger.warning(f'User {request.user.email} attempted to create user in different tenant')
                    return Response(
                        {'error': 'You can only create users in your own tenant'},
                        status=status.HTTP_403_FORBIDDEN
                    )

        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            user = serializer.instance

            if not user or not user.id:
                logger.error('User object created but has no ID')
                return Response(
                    {'error': 'User creation failed - no ID generated'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            logger.info(f'User created successfully: {user.email} (ID: {user.id}) in tenant: {user.tenant.slug if user.tenant else "No tenant"}')
            response_data = UserSerializer(user).data
            # Use UserSerializer for the response (includes id and all fields)
           
            

            # Ensure id is in the response
            if 'id' not in response_data:
                logger.error(f'Serializer did not include id field. Data: {response_data}')
                response_data['id'] = str(user.id)

            logger.debug(f'Response data: {response_data}')

            headers = self.get_success_headers(response_data)
            return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

        except Exception as e:
            logger.error(f'Error creating user: {str(e)}', exc_info=True)
            return Response(
                {'error': f'Failed to create user: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_me(self, request):
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def assign_roles(self, request, pk=None):
        user = self.get_object()
        role_ids = request.data.get('role_ids', [])
        roles = Role.objects.filter(id__in=role_ids, tenant=user.tenant)
        user.roles.set(roles)
        return Response({'message': 'Roles assigned successfully'})
    
    @action(detail=True, methods=['delete'])
    def remove_role(self, request, pk=None):
        user = self.get_object()
        role_id = request.data.get('role_id')
        user.roles.remove(role_id)
        return Response({'message': 'Role removed successfully'})


class RoleViewSet(viewsets.ModelViewSet):
    serializer_class = RoleSerializer
    permission_classes = [IsTenantMember]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin:
            return Role.objects.all()
        elif user.tenant:
            return Role.objects.filter(tenant=user.tenant)
        return Role.objects.none()
    
    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(tenant=user.tenant, created_by=user)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def permissions_schema(self, request):
        return Response(PERMISSION_SCHEMA)
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        role = self.get_object()
        users = role.users.all()
        return Response(UserSerializer(users, many=True).data)
