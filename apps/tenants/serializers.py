from rest_framework import serializers
from apps.tenants.models import Tenant, TenantImage


class TenantImageSerializer(serializers.ModelSerializer):
    """Serializer for tenant gallery images"""
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = TenantImage
        fields = ['id', 'tenant', 'image', 'image_url', 'label', 'description',
                  'order', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_image_url(self, obj):
        """Return the full URL for the image"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class TenantImageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/uploading tenant images"""

    class Meta:
        model = TenantImage
        fields = ['image', 'label', 'description', 'order', 'is_active']

    def validate_label(self, value):
        """Ensure label is not empty and is valid"""
        if not value or not value.strip():
            raise serializers.ValidationError("Label cannot be empty")
        return value.strip()


class TenantSerializer(serializers.ModelSerializer):
    user_count = serializers.SerializerMethodField()
    gallery_images = TenantImageSerializer(many=True, read_only=True)

    class Meta:
        model = Tenant
        fields = ['id', 'name', 'slug', 'domain', 'database_name', 'database_url',
                  'enabled_modules', 'settings', 'is_active', 'trial_ends_at',
                  'user_count', 'gallery_images', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_user_count(self, obj):
        return obj.users.count()
