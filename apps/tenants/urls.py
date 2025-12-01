from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.tenants import views

router = DefaultRouter()
router.register('tenants', views.TenantViewSet, basename='tenant')
router.register('tenant-images', views.TenantImageViewSet, basename='tenant-image')

urlpatterns = [
    path('', include(router.urls)),
]
