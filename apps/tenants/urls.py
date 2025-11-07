from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.tenants import views

router = DefaultRouter()
router.register('tenants', views.TenantViewSet, basename='tenant')

urlpatterns = [
    path('', include(router.urls)),
]
