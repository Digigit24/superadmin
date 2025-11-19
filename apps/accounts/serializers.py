from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from apps.accounts.models import CustomUser, Role
from apps.tenants.models import Tenant
from apps.common.constants import PERMISSION_SCHEMA
from datetime import datetime, timedelta


class RoleSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = ['id', 'tenant', 'name', 'description', 'permissions', 'is_active', 
                  'created_by', 'created_by_email', 'member_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'tenant', 'created_by', 'created_at', 'updated_at']
    
    def get_member_count(self, obj):
        return obj.users.count()
    
    def validate_permissions(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Permissions must be a JSON object")
        return value


class UserSerializer(serializers.ModelSerializer):
    roles = RoleSerializer(many=True, read_only=True)
    role_ids = serializers.ListField(
        child=serializers.UUIDField(), 
        write_only=True, 
        required=False
    )
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'phone', 'first_name', 'last_name', 'tenant', 
                  'tenant_name', 'roles', 'role_ids', 'is_super_admin', 
                  'profile_picture', 'timezone', 'is_active', 'date_joined']
        read_only_fields = ['id', 'tenant', 'is_super_admin', 'date_joined']
    
    def update(self, instance, validated_data):
        role_ids = validated_data.pop('role_ids', None)
        instance = super().update(instance, validated_data)
        
        if role_ids is not None:
            roles = Role.objects.filter(id__in=role_ids, tenant=instance.tenant)
            instance.roles.set(roles)
        
        return instance


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    role_ids = serializers.ListField(
        child=serializers.UUIDField(), 
        write_only=True, 
        required=False
    )
    
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'password', 'password_confirm', 'phone', 'first_name', 
                  'last_name', 'role_ids', 'timezone']
        
        read_only_fields = ['id']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords don't match"})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        role_ids = validated_data.pop('role_ids', [])
        
        password = validated_data.pop('password')
        user = CustomUser.objects.create_user(password=password, **validated_data)
        
        if role_ids:
            roles = Role.objects.filter(id__in=role_ids, tenant=user.tenant)
            user.roles.set(roles)
        
        return user


class RegisterSerializer(serializers.Serializer):
    tenant_name = serializers.CharField(max_length=255)
    tenant_slug = serializers.SlugField(max_length=255)
    admin_email = serializers.EmailField()
    admin_password = serializers.CharField(write_only=True, validators=[validate_password])
    admin_password_confirm = serializers.CharField(write_only=True)
    admin_first_name = serializers.CharField(max_length=150)
    admin_last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    enabled_modules = serializers.ListField(
        child=serializers.CharField(), 
        default=['crm', 'whatsapp', 'meetings']
    )
    
    def validate(self, attrs):
        if attrs['admin_password'] != attrs['admin_password_confirm']:
            raise serializers.ValidationError({"admin_password": "Passwords don't match"})
        
        if Tenant.objects.filter(slug=attrs['tenant_slug']).exists():
            raise serializers.ValidationError({"tenant_slug": "This slug is already taken"})
        
        if CustomUser.objects.filter(email=attrs['admin_email']).exists():
            raise serializers.ValidationError({"admin_email": "User with this email already exists"})
        
        return attrs
    
    def create(self, validated_data):
        from apps.billing.models import SubscriptionPlan, Subscription
        
        tenant = Tenant.objects.create(
            name=validated_data['tenant_name'],
            slug=validated_data['tenant_slug'],
            enabled_modules=validated_data.get('enabled_modules', ['crm', 'whatsapp', 'meetings']),
            trial_ends_at=datetime.now() + timedelta(days=14)
        )
        
        admin_user = CustomUser.objects.create_user(
            email=validated_data['admin_email'],
            password=validated_data['admin_password'],
            first_name=validated_data['admin_first_name'],
            last_name=validated_data.get('admin_last_name', ''),
            tenant=tenant
        )
        
        admin_role = Role.objects.create(
            tenant=tenant,
            name='Admin',
            description='Full access to all features',
            permissions={
                'admin': {'full_access': True}
            },
            created_by=admin_user
        )
        
        admin_user.roles.add(admin_role)
        
        trial_plan = SubscriptionPlan.objects.filter(is_trial=True, is_active=True).first()
        if trial_plan:
            Subscription.objects.create(
                tenant=tenant,
                plan=trial_plan,
                status='TRIAL',
                billing_cycle='MONTHLY',
                current_period_start=datetime.now(),
                current_period_end=datetime.now() + timedelta(days=14)
            )
        
        return {'tenant': tenant, 'user': admin_user}


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "Passwords don't match"})
        return attrs
