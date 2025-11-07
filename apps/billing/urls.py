from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.billing import views

router = DefaultRouter()
router.register('plans', views.SubscriptionPlanViewSet, basename='plan')
router.register('subscriptions', views.SubscriptionViewSet, basename='subscription')
router.register('invoices', views.InvoiceViewSet, basename='invoice')

urlpatterns = [
    path('', include(router.urls)),
]
