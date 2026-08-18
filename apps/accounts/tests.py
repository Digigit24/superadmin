from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from apps.accounts.models import CustomUser, Role
from apps.common.pagination import StandardResultsSetPagination
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


class UserDirectoryAPITests(APITestCase):
    LIST_URL = '/api/users/'

    SENSITIVE_KEYS = ['password', 'is_super_admin', 'preferences', 'roles',
                      'role_ids', 'tenant', 'permissions']

    def setUp(self):
        self.tenant_a = Tenant.objects.create(name='Tenant A', slug='tenant-a')
        self.tenant_b = Tenant.objects.create(name='Tenant B', slug='tenant-b')

        self.admin_role_a = Role.objects.create(
            tenant=self.tenant_a,
            name='Admin',
            permissions={'admin': {'full_access': {'enabled': True}}},
        )

        self.admin_a = CustomUser.objects.create_user(
            email='admin-a@example.com', password='TestPass123!',
            first_name='Ada', last_name='Admin', tenant=self.tenant_a,
        )
        self.admin_a.roles.add(self.admin_role_a)

        self.member_a = CustomUser.objects.create_user(
            email='asha@example.com', password='TestPass123!',
            first_name='Asha', last_name='Rao', tenant=self.tenant_a,
        )
        self.mate_a = CustomUser.objects.create_user(
            email='bharat@example.com', password='TestPass123!',
            first_name='Bharat', last_name='Singh', tenant=self.tenant_a,
        )
        # No first/last name - full_name must fall back to the email.
        self.nameless_a = CustomUser.objects.create_user(
            email='nameless@example.com', password='TestPass123!', tenant=self.tenant_a,
        )

        self.member_b = CustomUser.objects.create_user(
            email='secret-b@example.com', password='TestPass123!',
            first_name='Carol', last_name='Other', tenant=self.tenant_b,
        )

        self.super_admin = CustomUser.objects.create_user(
            email='root@example.com', password='TestPass123!', is_super_admin=True,
        )

    def emails(self, response):
        return {row['email'] for row in response.data['results']}

    # --- tenant scoping -------------------------------------------------

    def test_regular_user_can_list_own_tenant(self):
        """A non-admin member gets the directory (not a 403) - the whole point."""
        self.client.force_authenticate(user=self.member_a)
        response = self.client.get(self.LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(
            self.emails(response),
            {'admin-a@example.com', 'asha@example.com', 'bharat@example.com',
             'nameless@example.com'},
        )

    def test_regular_user_cannot_read_another_tenants_users(self):
        self.client.force_authenticate(user=self.member_a)
        response = self.client.get(self.LIST_URL)
        self.assertNotIn('secret-b@example.com', self.emails(response))
        self.assertNotIn('root@example.com', self.emails(response))

    def test_tenantless_regular_user_sees_nobody(self):
        orphan = CustomUser.objects.create_user(
            email='orphan@example.com', password='TestPass123!',
        )
        self.client.force_authenticate(user=orphan)
        response = self.client.get(self.LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    # --- x-tenant-id trust rules ----------------------------------------

    def test_x_tenant_id_is_ignored_for_a_regular_user_token(self):
        """The header must never widen a normal user's scope."""
        self.client.force_authenticate(user=self.member_a)
        response = self.client.get(self.LIST_URL, HTTP_X_TENANT_ID=str(self.tenant_b.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Falls back to the caller's own tenant: not tenant B, and not empty.
        self.assertEqual(response.data['count'], 4)
        self.assertNotIn('secret-b@example.com', self.emails(response))
        self.assertIn('asha@example.com', self.emails(response))

    def test_x_tenant_id_is_ignored_for_a_tenant_admin_token(self):
        self.client.force_authenticate(user=self.admin_a)
        response = self.client.get(self.LIST_URL, HTTP_X_TENANT_ID=str(self.tenant_b.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('secret-b@example.com', self.emails(response))
        self.assertEqual(response.data['count'], 4)

    def test_x_tenant_id_is_honoured_for_a_super_admin_token(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get(self.LIST_URL, HTTP_X_TENANT_ID=str(self.tenant_b.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.emails(response), {'secret-b@example.com'})

    def test_super_admin_without_header_sees_every_tenant(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get(self.LIST_URL, {'page_size': 100})
        self.assertEqual(response.data['count'], CustomUser.objects.count())

    def test_malformed_x_tenant_id_from_super_admin_returns_nothing(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get(self.LIST_URL, HTTP_X_TENANT_ID='not-a-uuid')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_anonymous_caller_is_rejected(self):
        response = self.client.get(self.LIST_URL)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    # --- pagination ------------------------------------------------------

    def test_page_size_query_param_is_honoured(self):
        for i in range(25):
            CustomUser.objects.create_user(
                email=f'bulk{i}@example.com', password='TestPass123!',
                first_name=f'Bulk{i}', tenant=self.tenant_a,
            )
        self.client.force_authenticate(user=self.member_a)

        response = self.client.get(self.LIST_URL, {'page_size': 5})
        self.assertEqual(len(response.data['results']), 5)
        self.assertIsNotNone(response.data['next'])

        # Stock PageNumberPagination would have capped this at 20.
        response = self.client.get(self.LIST_URL, {'page_size': 200})
        self.assertEqual(response.data['count'], 29)
        self.assertEqual(len(response.data['results']), 29)
        self.assertIsNone(response.data['next'])

    def test_page_size_is_capped_at_max(self):
        self.assertEqual(StandardResultsSetPagination.max_page_size, 500)
        self.assertEqual(StandardResultsSetPagination.page_size_query_param, 'page_size')

        self.client.force_authenticate(user=self.member_a)
        response = self.client.get(self.LIST_URL, {'page_size': 100000})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data['results']), 500)

    # --- search ----------------------------------------------------------

    def test_search_matches_first_name(self):
        self.client.force_authenticate(user=self.member_a)
        response = self.client.get(self.LIST_URL, {'search': 'bhara'})
        self.assertEqual(self.emails(response), {'bharat@example.com'})

    def test_search_matches_last_name_and_email(self):
        self.client.force_authenticate(user=self.member_a)
        self.assertEqual(
            self.emails(self.client.get(self.LIST_URL, {'search': 'Rao'})),
            {'asha@example.com'},
        )
        self.assertEqual(
            self.emails(self.client.get(self.LIST_URL, {'search': 'nameless@'})),
            {'nameless@example.com'},
        )

    def test_search_cannot_escape_the_tenant_scope(self):
        self.client.force_authenticate(user=self.member_a)
        response = self.client.get(self.LIST_URL, {'search': 'secret-b'})
        self.assertEqual(response.data['count'], 0)

    # --- response shape --------------------------------------------------

    def test_non_admin_list_omits_sensitive_fields(self):
        self.client.force_authenticate(user=self.member_a)
        for row in self.client.get(self.LIST_URL).data['results']:
            for key in self.SENSITIVE_KEYS:
                self.assertNotIn(key, row)

    def test_non_admin_list_matches_the_pinned_contract(self):
        self.client.force_authenticate(user=self.member_a)
        response = self.client.get(self.LIST_URL)
        for key in ('count', 'next', 'previous', 'results'):
            self.assertIn(key, response.data)
        row = next(r for r in response.data['results'] if r['email'] == 'asha@example.com')
        self.assertEqual(
            set(row.keys()),
            {'id', 'email', 'first_name', 'last_name', 'full_name', 'is_active', 'avatar'},
        )
        self.assertEqual(row['full_name'], 'Asha Rao')
        self.assertEqual(row['id'], str(self.member_a.id))
        self.assertIs(row['is_active'], True)
        self.assertIsNone(row['avatar'])

    def test_full_name_falls_back_to_email(self):
        self.client.force_authenticate(user=self.member_a)
        response = self.client.get(self.LIST_URL)
        row = next(r for r in response.data['results'] if r['email'] == 'nameless@example.com')
        self.assertEqual(row['full_name'], 'nameless@example.com')
        for row in response.data['results']:
            self.assertTrue(row['full_name'])

    def test_admin_list_keeps_the_rich_serializer_plus_contract_keys(self):
        self.client.force_authenticate(user=self.admin_a)
        response = self.client.get(self.LIST_URL)
        row = next(r for r in response.data['results'] if r['email'] == 'asha@example.com')
        for key in ('id', 'email', 'first_name', 'last_name', 'full_name',
                    'is_active', 'avatar'):
            self.assertIn(key, row)
        self.assertEqual(row['full_name'], 'Asha Rao')
        # Admins keep the richer shape.
        self.assertIn('roles', row)
        self.assertIn('preferences', row)
        self.assertNotIn('password', row)

    def test_detail_and_write_actions_still_require_tenant_admin(self):
        self.client.force_authenticate(user=self.member_a)
        response = self.client.get(f'{self.LIST_URL}{self.mate_a.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.delete(f'{self.LIST_URL}{self.mate_a.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
