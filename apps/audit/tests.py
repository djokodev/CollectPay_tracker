from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.audit.models import AuditLog
from apps.audit.services import write_audit_log
from apps.catalog.models import Service
from apps.customers.models import Customer
from apps.organizations.models import Organization, OrganizationMembership, OrganizationRole
from apps.payments.models import PaymentRequest


User = get_user_model()


class AuditTrailTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.agent = User.objects.create_user(
            username="audit_agent",
            email="audit_agent@example.com",
            password="CollectPaySecure123!",
        )
        self.agent.account_profile.role = UserRole.AGENT
        self.agent.account_profile.save()

        self.org_a = Organization.objects.create(name="Audit Org A", slug="audit-org-a")
        self.org_b = Organization.objects.create(name="Audit Org B", slug="audit-org-b")

        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.agent,
            role=OrganizationRole.AGENT,
        )
        self.agent.account_profile.active_organization = self.org_a
        self.agent.account_profile.save()

        self.customer = Customer.objects.create(
            organization=self.org_a,
            first_name="Audit",
            last_name="Customer",
            phone="693100001",
            email="audit.customer@example.com",
            created_by=self.agent,
        )
        self.service = Service.objects.create(
            organization=self.org_a,
            name="Audit Service",
            description="Service for audit",
            expected_amount="5000.00",
            currency="XAF",
            created_by=self.agent,
        )
        self.payment_request = PaymentRequest.objects.create(
            organization=self.org_a,
            customer=self.customer,
            service=self.service,
            expected_amount="5000.00",
            created_by=self.agent,
        )

    def auth(self):
        login = self.client.post(
            "/api/auth/login/",
            {"username": "audit_agent", "password": "CollectPaySecure123!"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_transaction_creation_writes_audit_logs(self):
        self.auth()
        response = self.client.post(
            "/api/payments/transactions/",
            {
                "payment_request": self.payment_request.id,
                "amount_received": "5000.00",
                "payment_method": "CASH",
                "transaction_reference": "AUDIT-TX-001",
                "status": "CONFIRMED",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        actions = list(AuditLog.objects.values_list("action", flat=True))
        self.assertIn("payment_transaction.created", actions)
        self.assertIn("payment_request.status_recomputed_from_transaction", actions)

    def test_audit_logs_endpoint_is_scoped_and_filterable(self):
        self.auth()
        write_audit_log(
            action="custom.org_a.action",
            entity_type="test_entity",
            entity_id="1",
            organization_id=self.org_a.id,
            actor=self.agent,
            after_data={"foo": "bar"},
        )
        write_audit_log(
            action="custom.org_b.action",
            entity_type="test_entity",
            entity_id="2",
            organization_id=self.org_b.id,
            actor=self.agent,
            after_data={"foo": "baz"},
        )

        response = self.client.get("/api/audit/logs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["action"], "custom.org_a.action")

        filtered = self.client.get("/api/audit/logs/?action=custom.org_a.action")
        self.assertEqual(filtered.status_code, status.HTTP_200_OK)
        self.assertEqual(filtered.data["count"], 1)
