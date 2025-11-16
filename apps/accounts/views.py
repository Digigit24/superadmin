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
    """
    Register a new user and return JWT tokens.
    Enhanced with comprehensive logging for production debugging.
    """
    # Log incoming request details (excluding password)
    request_data_safe = {k: v for k, v in request.data.items() if k not in ['password', 'confirm_password']}
    logger.info(f'Registration attempt received - Data: {request_data_safe}, IP: {request.META.get("REMOTE_ADDR")}')

    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f'Registration validation failed - Errors: {serializer.errors}')
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        logger.debug(f'Creating new user: {serializer.validated_data.get("email")}')
        result = serializer.save()
        user = result['user']

        tenant_info = f'tenant: {user.tenant.slug}' if user.tenant else 'No tenant'
        logger.info(f'New user registered successfully: {user.email} (ID: {user.id}), {tenant_info}')

        # Generate tokens
        try:
            logger.debug(f'Generating JWT tokens for new user: {user.email}')
            tokens = get_tokens_for_user(user)

            # Serialize user data
            try:
                user_data = UserSerializer(user).data
                logger.debug(f'User data serialized for: {user.email}')
            except Exception as ser_error:
                logger.error(f'Error serializing user data for {user.email}: {str(ser_error)}',
                           exc_info=True)
                user_data = {
                    'id': str(user.id),
                    'email': user.email,
                    'is_super_admin': user.is_super_admin
                }

            logger.info(f'Registration completed successfully for: {user.email}')
            return Response({
                'message': 'Registration successful',
                'user': user_data,
                'tokens': tokens
            }, status=status.HTTP_201_CREATED)

        except Exception as token_error:
            logger.error(f'CRITICAL: Token generation failed for new user {user.email}: {str(token_error)}',
                        exc_info=True)
            return Response({
                'error': 'Registration successful but token generation failed',
                'details': str(token_error) if request.META.get('DEBUG') else 'Please try logging in'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as reg_error:
        logger.error(f'CRITICAL: Unexpected error during registration: {str(reg_error)}',
                    exc_info=True)
        return Response({
            'error': 'Registration failed',
            'details': str(reg_error) if request.META.get('DEBUG') else 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """
    Authenticate user and return JWT tokens.
    Enhanced with comprehensive logging for production debugging.
    """
    # Log incoming request details (excluding password)
    request_data_safe = {k: v for k, v in request.data.items() if k != 'password'}
    logger.info(f'Login attempt received - Data: {request_data_safe}, IP: {request.META.get("REMOTE_ADDR")}')

    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f'Login validation failed - Errors: {serializer.errors}')
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email']
    password = serializer.validated_data['password']

    logger.debug(f'Attempting authentication for email: {email}')

    try:
        # Authenticate user
        user = authenticate(
            request,
            username=email,
            password=password
        )

        # Log authentication result
        if user is None:
            logger.warning(f'Authentication failed for email: {email} - User not found or incorrect password')
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        # Check if user is active
        if not user.is_active:
            logger.warning(f'Login attempt for inactive user: {email} (ID: {user.id})')
            return Response({'error': 'Account is inactive'}, status=status.HTTP_403_FORBIDDEN)

        # Log successful authentication
        tenant_info = f'tenant: {user.tenant.slug}' if user.tenant else 'No tenant'
        logger.info(f'User authenticated successfully: {user.email} (ID: {user.id}), {tenant_info}')

        # Generate tokens
        try:
            logger.debug(f'Generating JWT tokens for user: {user.email}')
            tokens = get_tokens_for_user(user)
            logger.info(f'Login successful for user: {user.email}')

            # Serialize user data
            try:
                user_data = UserSerializer(user).data
                logger.debug(f'User data serialized for: {user.email}')
            except Exception as ser_error:
                logger.error(f'Error serializing user data for {user.email}: {str(ser_error)}',
                           exc_info=True)
                # Return tokens anyway, even if serialization fails
                user_data = {
                    'id': str(user.id),
                    'email': user.email,
                    'is_super_admin': user.is_super_admin
                }

            return Response({
                'message': 'Login successful',
                'user': user_data,
                'tokens': tokens
            })

        except Exception as token_error:
            logger.error(f'CRITICAL: Token generation failed for user {user.email} (ID: {user.id}): {str(token_error)}',
                        exc_info=True)
            return Response({
                'error': 'Token generation failed',
                'details': str(token_error) if request.META.get('DEBUG') else 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as auth_error:
        logger.error(f'CRITICAL: Unexpected error during login for email {email}: {str(auth_error)}',
                    exc_info=True)
        return Response({
            'error': 'Authentication error',
            'details': str(auth_error) if request.META.get('DEBUG') else 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        if self.action in ['me', 'update_me']:
            return [permissions.IsAuthenticated()]
        return [IsTenantAdmin()]
    
    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_super_admin:
            serializer.save(tenant=user.tenant)
        else:
            serializer.save()
    
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
