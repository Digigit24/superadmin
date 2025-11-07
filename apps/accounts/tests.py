from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from apps.accounts.models import CustomUser, Role
from apps.tenants.models import Tenant


class AuthenticationTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='Test Company',
            slug='test-company',
            enabled_modules=['crm', 'whatsapp']
        )
        self.admin_role = Role.objects.create(
            tenant=self.tenant,
            name='Admin',
            description='Full access',
            permissions={'admin': {'full_access': True}}
        )
    
    def test_registration(self):
        data = {
            'tenant_name': 'New Company',
            'tenant_slug': 'new-company',
            'admin_email': 'admin@example.com',
            'admin_password': 'TestPass123!',
            'admin_password_confirm': 'TestPass123!',
            'admin_first_name': 'John',
            'admin_last_name': 'Doe',
            'enabled_modules': ['crm', 'whatsapp']
        }
        response = self.client.post('/api/auth/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', response.data)
        self.assertIn('user', response.data)
    
    def test_login(self):
        user = CustomUser.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            tenant=self.tenant
        )
        user.roles.add(self.admin_role)
        
        data = {
            'email': 'test@example.com',
            'password': 'TestPass123!'
        }
        response = self.client.post('/api/auth/login/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)


class RoleTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='Test Company',
            slug='test-company'
        )
        self.user = CustomUser.objects.create_user(
            email='admin@example.com',
            password='TestPass123!',
            tenant=self.tenant
        )
        self.admin_role = Role.objects.create(
            tenant=self.tenant,
            name='Admin',
            description='Admin role',
            permissions={'admin': {'full_access': True}},
            created_by=self.user
        )
        self.user.roles.add(self.admin_role)
        self.client.force_authenticate(user=self.user)
    
    def test_create_role(self):
        data = {
            'name': 'Sales Rep',
            'description': 'Sales representative',
            'permissions': {
                'crm': {
                    'leads': {'view': 'team', 'create': True}
                }
            },
            'is_active': True
        }
        response = self.client.post('/api/roles/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Role.objects.filter(tenant=self.tenant).count(), 2)
    
    def test_list_roles(self):
        response = self.client.get('/api/roles/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_get_permissions_schema(self):
        response = self.client.get('/api/roles/permissions_schema/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('crm', response.data)
        self.assertIn('whatsapp', response.data)
