"""
`IsSuperAdminOrOwnTenant` — the permission behind `/api/tenants/{id}/whatsapp-credentials/`.

DigiCRM used to authenticate to this endpoint with a static, super-admin-scoped
service JWT that had to be manually minted and hand-installed on DigiCRM's
server. Now it forwards the CALLER'S OWN already-verified JWT instead — so
this permission has to allow a regular tenant user through, but ONLY for
their own tenant. The tests that matter here are the scoping boundary: a
tenant user reaching another tenant's credential this way is a cross-tenant
secret leak, not a cosmetic bug.
"""
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import CustomUser
from apps.common.permissions import IsSuperAdminOrOwnTenant
from apps.tenants.models import Tenant


class _FakeView:
    def __init__(self, pk):
        self.kwargs = {'pk': pk}


class _FakeRequest:
    def __init__(self, user):
        self.user = user


class IsSuperAdminOrOwnTenantUnitTests(APITestCase):
    """Direct tests of the permission class, no HTTP round-trip."""

    def setUp(self):
        self.tenant_a = Tenant.objects.create(name='Tenant A', slug='tenant-a')
        self.tenant_b = Tenant.objects.create(name='Tenant B', slug='tenant-b')
        self.super_admin = CustomUser.objects.create_user(
            email='root@example.com', password='x', is_super_admin=True,
        )
        self.member_a = CustomUser.objects.create_user(
            email='member-a@example.com', password='x', tenant=self.tenant_a,
        )
        self.orphan = CustomUser.objects.create_user(email='orphan@example.com', password='x')
        self.perm = IsSuperAdminOrOwnTenant()

    def test_super_admin_may_reach_any_tenant(self):
        req = _FakeRequest(self.super_admin)
        self.assertTrue(self.perm.has_permission(req, _FakeView(str(self.tenant_a.id))))
        self.assertTrue(self.perm.has_permission(req, _FakeView(str(self.tenant_b.id))))

    def test_a_tenant_user_may_reach_their_own_tenant(self):
        req = _FakeRequest(self.member_a)
        self.assertTrue(self.perm.has_permission(req, _FakeView(str(self.tenant_a.id))))

    def test_a_tenant_user_may_not_reach_another_tenant(self):
        """This is the boundary that matters — a leak here is a cross-tenant secret exposure."""
        req = _FakeRequest(self.member_a)
        self.assertFalse(self.perm.has_permission(req, _FakeView(str(self.tenant_b.id))))

    def test_a_user_with_no_tenant_is_refused(self):
        req = _FakeRequest(self.orphan)
        self.assertFalse(self.perm.has_permission(req, _FakeView(str(self.tenant_a.id))))

    def test_an_unauthenticated_request_is_refused(self):
        class _Anon:
            is_authenticated = False

        req = _FakeRequest(_Anon())
        self.assertFalse(self.perm.has_permission(req, _FakeView(str(self.tenant_a.id))))


class WhatsAppCredentialsEndpointTests(APITestCase):
    """The actual endpoint, end to end — same boundary, over real HTTP."""

    def setUp(self):
        self.tenant_a = Tenant.objects.create(
            name='Tenant A', slug='tenant-a',
            settings={'whatsapp_vendor_uid': 'vendor-a', 'whatsapp_api_token': 'token-a'},
        )
        self.tenant_b = Tenant.objects.create(name='Tenant B', slug='tenant-b')
        self.super_admin = CustomUser.objects.create_user(
            email='root@example.com', password='x', is_super_admin=True,
        )
        self.member_a = CustomUser.objects.create_user(
            email='member-a@example.com', password='x', tenant=self.tenant_a,
        )
        self.member_b = CustomUser.objects.create_user(
            email='member-b@example.com', password='x', tenant=self.tenant_b,
        )

    def _url(self, tenant):
        return f'/api/tenants/{tenant.id}/whatsapp-credentials/'

    def test_the_tenants_own_user_can_read_its_own_credential(self):
        self.client.force_authenticate(user=self.member_a)
        response = self.client.get(self._url(self.tenant_a))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['vendor_uid'], 'vendor-a')

    def test_a_tenant_cannot_read_another_tenants_credential(self):
        self.client.force_authenticate(user=self.member_b)
        response = self.client.get(self._url(self.tenant_a))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_super_admin_can_still_read_any_tenants_credential(self):
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get(self._url(self.tenant_a))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_is_refused(self):
        response = self.client.get(self._url(self.tenant_a))
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
