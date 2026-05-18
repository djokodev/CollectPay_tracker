from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import UserRole
from apps.catalog.models import Service
from apps.customers.models import Customer
from apps.organizations.models import Organization, OrganizationMembership, OrganizationRole
from apps.payments.models import PaymentRequest, PaymentRequestStatus


User = get_user_model()


class BackofficeViewsTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username="backoffice_agent",
            email="backoffice_agent@example.com",
            password="CollectPaySecure123!",
        )
        self.client_user.account_profile.role = UserRole.AGENT
        self.client_user.account_profile.save()

        self.org_a = Organization.objects.create(name="Backoffice Org A", slug="backoffice-org-a")
        self.org_b = Organization.objects.create(name="Backoffice Org B", slug="backoffice-org-b")

        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.client_user,
            role=OrganizationRole.AGENT,
        )
        self.client_user.account_profile.active_organization = self.org_a
        self.client_user.account_profile.save()

        self.customer_a = Customer.objects.create(
            organization=self.org_a,
            first_name="Alpha",
            last_name="Client",
            phone="699100001",
            email="alpha@example.com",
            created_by=self.client_user,
        )
        self.service_a = Service.objects.create(
            organization=self.org_a,
            name="Inscription",
            expected_amount="12000.00",
            currency="XAF",
            created_by=self.client_user,
        )
        self.request_a = PaymentRequest.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            service=self.service_a,
            expected_amount="12000.00",
            status=PaymentRequestStatus.PENDING,
            created_by=self.client_user,
        )

        customer_b = Customer.objects.create(
            organization=self.org_b,
            first_name="Beta",
            last_name="Client",
            phone="699100002",
            email="beta@example.com",
            created_by=self.client_user,
        )
        service_b = Service.objects.create(
            organization=self.org_b,
            name="Autre Service",
            expected_amount="5000.00",
            currency="XAF",
            created_by=self.client_user,
        )
        self.request_b = PaymentRequest.objects.create(
            organization=self.org_b,
            customer=customer_b,
            service=service_b,
            expected_amount="5000.00",
            status=PaymentRequestStatus.PAID,
            created_by=self.client_user,
        )

    def get_access_token(self):
        refresh = RefreshToken.for_user(self.client_user)
        return str(refresh.access_token)

    def test_backoffice_home_page_is_accessible(self):
        response = self.client.get("/backoffice/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "CollectPay Backoffice")

    def test_payment_requests_partial_requires_bearer_token(self):
        response = self.client.get("/backoffice/partials/payment-requests/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_payment_requests_partial_is_tenant_scoped(self):
        token = self.get_access_token()
        response = self.client.get(
            "/backoffice/partials/payment-requests/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, self.request_a.reference)
        self.assertNotContains(response, self.request_b.reference)

    def test_kpi_cards_partial_requires_auth_and_returns_metrics(self):
        token = self.get_access_token()
        response = self.client.get(
            "/backoffice/partials/kpi-cards/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Pending")
