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


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        result = serializer.save()
        user = result['user']
        tokens = get_tokens_for_user(user)
        return Response({
            'message': 'Registration successful',
            'user': UserSerializer(user).data,
            'tokens': tokens
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = authenticate(
            request,
            username=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )
        
        if user and user.is_active:
            tokens = get_tokens_for_user(user)
            return Response({
                'message': 'Login successful',
                'user': UserSerializer(user).data,
                'tokens': tokens
            })
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def logout_view(request):
    try:
        refresh_token = request.data.get('refresh_token')
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'Logout successful'})
    except Exception:
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
