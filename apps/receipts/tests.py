from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.catalog.models import Service
from apps.customers.models import Customer
from apps.organizations.models import Organization, OrganizationMembership, OrganizationRole
from apps.payments.models import (
    PaymentMethod,
    PaymentRequest,
    PaymentRequestStatus,
    PaymentTransaction,
    PaymentTransactionStatus,
)
from apps.receipts.models import Receipt


User = get_user_model()


class ReceiptsVerificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.agent = User.objects.create_user(
            username="receipt_agent",
            email="receipt_agent@example.com",
            password="CollectPaySecure123!",
        )
        self.viewer = User.objects.create_user(
            username="receipt_viewer",
            email="receipt_viewer@example.com",
            password="CollectPaySecure123!",
        )

        self.agent.account_profile.role = UserRole.AGENT
        self.agent.account_profile.save()
        self.viewer.account_profile.role = UserRole.VIEWER
        self.viewer.account_profile.save()

        self.org_a = Organization.objects.create(name="Receipt Org A", slug="receipt-org-a")
        self.org_b = Organization.objects.create(name="Receipt Org B", slug="receipt-org-b")

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

        self.customer = Customer.objects.create(
            organization=self.org_a,
            first_name="Rece",
            last_name="Ipt",
            phone="692000001",
            email="receipt@example.com",
            created_by=self.agent,
        )
        self.service = Service.objects.create(
            organization=self.org_a,
            name="Frais examen",
            description="Frais",
            expected_amount="20000.00",
            currency="XAF",
            created_by=self.agent,
        )

        self.payment_request = PaymentRequest.objects.create(
            organization=self.org_a,
            customer=self.customer,
            service=self.service,
            expected_amount="20000.00",
            paid_amount="20000.00",
            status=PaymentRequestStatus.PAID,
            created_by=self.agent,
        )

        self.confirmed_transaction = PaymentTransaction.objects.create(
            organization=self.org_a,
            payment_request=self.payment_request,
            amount_received="20000.00",
            payment_method=PaymentMethod.ORANGE_MONEY,
            transaction_reference="RCPT-REF-001",
            status=PaymentTransactionStatus.CONFIRMED,
            confirmed_by=self.agent,
        )

    def auth(self, username):
        login = self.client.post(
            "/api/auth/login/",
            {"username": username, "password": "CollectPaySecure123!"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_agent_can_generate_receipt(self):
        self.auth("receipt_agent")
        response = self.client.post(
            "/api/receipts/generate/",
            {
                "payment_request_id": self.payment_request.id,
                "transaction_id": self.confirmed_transaction.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("public_reference", response.data)
        self.assertEqual(response.data["amount_paid"], "20000.00")

    def test_viewer_cannot_generate_receipt(self):
        self.auth("receipt_viewer")
        response = self.client.post(
            "/api/receipts/generate/",
            {
                "payment_request_id": self.payment_request.id,
                "transaction_id": self.confirmed_transaction.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_receipts_list_scoped_to_tenant(self):
        self.auth("receipt_agent")
        receipt = Receipt.objects.create(
            organization=self.org_a,
            payment_request=self.payment_request,
            transaction=self.confirmed_transaction,
            amount_paid="20000.00",
            currency="XAF",
            payment_status_snapshot=PaymentRequestStatus.PAID,
            customer_name=self.payment_request.customer.full_name,
            service_name=self.payment_request.service.name,
            issued_by=self.agent,
        )

        other_org = Organization.objects.create(name="Other Org", slug="other-receipt-org")
        other_customer = Customer.objects.create(
            organization=other_org,
            first_name="Other",
            last_name="Customer",
            phone="692000999",
            email="other@example.com",
            created_by=self.agent,
        )
        other_service = Service.objects.create(
            organization=other_org,
            name="Other Service",
            description="Other desc",
            expected_amount="1000.00",
            currency="XAF",
            created_by=self.agent,
        )
        other_request = PaymentRequest.objects.create(
            organization=other_org,
            customer=other_customer,
            service=other_service,
            expected_amount="1000.00",
            paid_amount="1000.00",
            status=PaymentRequestStatus.PAID,
            created_by=self.agent,
        )
        Receipt.objects.create(
            organization=other_org,
            payment_request=other_request,
            amount_paid="1000.00",
            currency="XAF",
            payment_status_snapshot=PaymentRequestStatus.PARTIAL,
            customer_name="Other",
            service_name="Other",
            issued_by=self.agent,
        )

        response = self.client.get("/api/receipts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], receipt.id)

    def test_public_verification_endpoint(self):
        receipt = Receipt.objects.create(
            organization=self.org_a,
            payment_request=self.payment_request,
            transaction=self.confirmed_transaction,
            amount_paid="20000.00",
            currency="XAF",
            payment_status_snapshot=PaymentRequestStatus.PAID,
            customer_name=self.payment_request.customer.full_name,
            service_name=self.payment_request.service.name,
            issued_by=self.agent,
        )

        response = self.client.get(f"/api/receipts/verify/{receipt.public_reference}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_valid"])
        self.assertEqual(response.data["receipt_number"], receipt.receipt_number)

    def test_cannot_generate_for_cancelled_request(self):
        self.auth("receipt_agent")
        self.payment_request.status = PaymentRequestStatus.CANCELLED
        self.payment_request.save(update_fields=["status"])

        response = self.client.post(
            "/api/receipts/generate/",
            {
                "payment_request_id": self.payment_request.id,
                "transaction_id": self.confirmed_transaction.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
