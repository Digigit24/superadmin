from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from apps.accounts import views

router = DefaultRouter()
router.register('users', views.UserViewSet, basename='user')
router.register('roles', views.RoleViewSet, basename='role')

urlpatterns = [
    path('auth/register/', views.register_view, name='register'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('auth/password/change/', views.change_password_view, name='change_password'),
    path('', include(router.urls)),
]
