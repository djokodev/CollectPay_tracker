from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.catalog.models import Service
from apps.customers.models import Customer
from apps.organizations.models import Organization, OrganizationMembership, OrganizationRole
from apps.payments.models import PaymentRequest, PaymentRequestStatus


User = get_user_model()


class PaymentRequestsCoreTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.agent = User.objects.create_user(
            username="pay_agent",
            email="pay_agent@example.com",
            password="CollectPaySecure123!",
        )
        self.viewer = User.objects.create_user(
            username="pay_viewer",
            email="pay_viewer@example.com",
            password="CollectPaySecure123!",
        )

        self.agent.account_profile.role = UserRole.AGENT
        self.agent.account_profile.save()
        self.viewer.account_profile.role = UserRole.VIEWER
        self.viewer.account_profile.save()

        self.org_a = Organization.objects.create(name="Pay Org A", slug="pay-org-a")
        self.org_b = Organization.objects.create(name="Pay Org B", slug="pay-org-b")

        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.agent,
            role=OrganizationRole.AGENT,
        )
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.viewer,
            role=OrganizationRole.VIEWER,
        )

        self.agent.account_profile.active_organization = self.org_a
        self.agent.account_profile.save()
        self.viewer.account_profile.active_organization = self.org_a
        self.viewer.account_profile.save()

        self.customer_a = Customer.objects.create(
            organization=self.org_a,
            first_name="Patrice",
            last_name="Mbi",
            phone="691000001",
            email="patrice@example.com",
            created_by=self.agent,
        )
        self.customer_b = Customer.objects.create(
            organization=self.org_b,
            first_name="Other",
            last_name="Tenant",
            phone="691000002",
            email="other@example.com",
            created_by=self.agent,
        )

        self.service_a = Service.objects.create(
            organization=self.org_a,
            name="Frais scolarite",
            description="Mensualite",
            expected_amount="50000.00",
            currency="XAF",
            created_by=self.agent,
        )
        self.service_b = Service.objects.create(
            organization=self.org_b,
            name="Service B",
            description="Other",
            expected_amount="12000.00",
            currency="XAF",
            created_by=self.agent,
        )

    def auth(self, username):
        login = self.client.post(
            "/api/auth/login/",
            {"username": username, "password": "CollectPaySecure123!"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_agent_can_create_payment_request(self):
        self.auth("pay_agent")
        response = self.client.post(
            "/api/payments/requests/",
            {
                "customer": self.customer_a.id,
                "service": self.service_a.id,
                "expected_amount": "50000.00",
                "due_date": str(timezone.localdate() + timedelta(days=5)),
                "notes": "Paiement d'inscription",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], PaymentRequestStatus.PENDING)
        self.assertEqual(response.data["organization_id"], self.org_a.id)

    def test_viewer_cannot_create_payment_request(self):
        self.auth("pay_viewer")
        response = self.client.post(
            "/api/payments/requests/",
            {
                "customer": self.customer_a.id,
                "service": self.service_a.id,
                "expected_amount": "50000.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_request_must_use_customer_and_service_of_active_org(self):
        self.auth("pay_agent")
        response = self.client.post(
            "/api/payments/requests/",
            {
                "customer": self.customer_b.id,
                "service": self.service_a.id,
                "expected_amount": "50000.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manual_payment_moves_status_partial_then_paid(self):
        self.auth("pay_agent")
        create = self.client.post(
            "/api/payments/requests/",
            {
                "customer": self.customer_a.id,
                "service": self.service_a.id,
                "expected_amount": "50000.00",
            },
            format="json",
        )
        request_id = create.data["id"]

        partial = self.client.post(
            f"/api/payments/requests/{request_id}/apply-manual-payment/",
            {"amount": "30000.00"},
            format="json",
        )
        self.assertEqual(partial.status_code, status.HTTP_200_OK)
        self.assertEqual(partial.data["status"], PaymentRequestStatus.PARTIAL)

        paid = self.client.post(
            f"/api/payments/requests/{request_id}/apply-manual-payment/",
            {"amount": "20000.00"},
            format="json",
        )
        self.assertEqual(paid.status_code, status.HTTP_200_OK)
        self.assertEqual(paid.data["status"], PaymentRequestStatus.PAID)

    def test_cancelled_request_rejects_manual_payment(self):
        self.auth("pay_agent")
        create = self.client.post(
            "/api/payments/requests/",
            {
                "customer": self.customer_a.id,
                "service": self.service_a.id,
                "expected_amount": "50000.00",
            },
            format="json",
        )
        request_id = create.data["id"]

        cancel = self.client.post(f"/api/payments/requests/{request_id}/cancel/")
        self.assertEqual(cancel.status_code, status.HTTP_200_OK)
        self.assertEqual(cancel.data["status"], PaymentRequestStatus.CANCELLED)

        apply_response = self.client.post(
            f"/api/payments/requests/{request_id}/apply-manual-payment/",
            {"amount": "10000.00"},
            format="json",
        )
        self.assertEqual(apply_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_overdue_endpoint_returns_late_requests(self):
        self.auth("pay_agent")
        old_request = PaymentRequest.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            service=self.service_a,
            expected_amount="50000.00",
            due_date=timezone.localdate() - timedelta(days=2),
            created_by=self.agent,
        )
        old_request.recompute_status()
        old_request.save()

        response = self.client.get("/api/payments/requests/overdue/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], old_request.id)
