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


class UserImportTenantTest(APITestCase):
    """P0 regression: import_users duplicate check must be scoped per tenant."""

    def setUp(self):
        self.tenant_a = Tenant.objects.create(
            name='Tenant A',
            slug='tenant-a',
            enabled_modules=['crm'],
        )
        self.tenant_b = Tenant.objects.create(
            name='Tenant B',
            slug='tenant-b',
            enabled_modules=['crm'],
        )

        self.admin_role_a = Role.objects.create(
            tenant=self.tenant_a,
            name='Admin',
            description='Full access',
            permissions={'admin': {'full_access': True}},
        )
        self.admin_user_a = CustomUser.objects.create_user(
            email='admin_a@example.com',
            password='TestPass123!',
            tenant=self.tenant_a,
        )
        self.admin_user_a.roles.add(self.admin_role_a)

        self.superuser = CustomUser.objects.create_superuser(
            email='super@example.com',
            password='TestPass123!',
        )

    def _build_xlsx(self, rows):
        """Return an in-memory Excel file with the given rows."""
        import io
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        for row in rows:
            ws.append(row)
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

    def test_same_email_in_different_tenant_is_allowed(self):
        """An email used in tenant B must not block import into tenant A."""
        CustomUser.objects.create_user(
            email='shared@example.com',
            password='TestPass123!',
            tenant=self.tenant_b,
        )

        self.client.force_authenticate(user=self.admin_user_a)
        file_data = self._build_xlsx([
            ['Email', 'First Name', 'Last Name', 'Phone', 'Timezone', 'Password'],
            ['shared@example.com', 'Shared', 'User', '9999999999', 'UTC', 'TestPass123!'],
        ])
        response = self.client.post(
            '/api/users/import_users/',
            {'file': file_data},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['created'], 1)
        self.assertEqual(response.data['skipped'], 0)

    def test_same_email_in_same_tenant_is_skipped(self):
        """Importing the same email into the same tenant twice should skip it."""
        CustomUser.objects.create_user(
            email='duplicate@example.com',
            password='TestPass123!',
            tenant=self.tenant_a,
        )

        self.client.force_authenticate(user=self.admin_user_a)
        file_data = self._build_xlsx([
            ['Email', 'First Name', 'Last Name', 'Phone', 'Timezone', 'Password'],
            ['duplicate@example.com', 'Dup', 'User', '9999999999', 'UTC', 'TestPass123!'],
        ])
        response = self.client.post(
            '/api/users/import_users/',
            {'file': file_data},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['created'], 0)
        self.assertEqual(response.data['skipped'], 1)

    def test_super_admin_import_requires_tenant_id(self):
        """Super-admin imports must explicitly name a target tenant."""
        self.client.force_authenticate(user=self.superuser)
        file_data = self._build_xlsx([
            ['Email', 'First Name', 'Last Name', 'Phone', 'Timezone', 'Password'],
            ['new@example.com', 'New', 'User', '9999999999', 'UTC', 'TestPass123!'],
        ])
        response = self.client.post(
            '/api/users/import_users/',
            {'file': file_data},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tenant_id', response.data['error'].lower())

    def test_super_admin_import_with_tenant_id_succeeds(self):
        """Super-admin imports scoped to the provided tenant_id."""
        self.client.force_authenticate(user=self.superuser)
        file_data = self._build_xlsx([
            ['Email', 'First Name', 'Last Name', 'Phone', 'Timezone', 'Password'],
            ['supernew@example.com', 'New', 'User', '9999999999', 'UTC', 'TestPass123!'],
        ])
        response = self.client.post(
            f'/api/users/import_users/?tenant_id={self.tenant_a.id}',
            {'file': file_data},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['created'], 1)
        self.assertTrue(
            CustomUser.objects.filter(
                email='supernew@example.com',
                tenant=self.tenant_a,
            ).exists()
        )
