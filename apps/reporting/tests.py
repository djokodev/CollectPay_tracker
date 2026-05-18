from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
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


User = get_user_model()


class DashboardReportingTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.agent = User.objects.create_user(
            username="report_agent",
            email="report_agent@example.com",
            password="CollectPaySecure123!",
        )
        self.no_tenant_user = User.objects.create_user(
            username="report_no_tenant",
            email="report_no_tenant@example.com",
            password="CollectPaySecure123!",
        )

        self.agent.account_profile.role = UserRole.AGENT
        self.agent.account_profile.save()

        self.org_a = Organization.objects.create(name="Report Org A", slug="report-org-a")
        self.org_b = Organization.objects.create(name="Report Org B", slug="report-org-b")

        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.agent,
            role=OrganizationRole.AGENT,
        )
        self.agent.account_profile.active_organization = self.org_a
        self.agent.account_profile.save()

        self.customer_a = Customer.objects.create(
            organization=self.org_a,
            first_name="Alice",
            last_name="A",
            phone="690111111",
            email="alice.a@example.com",
            created_by=self.agent,
        )
        self.customer_b = Customer.objects.create(
            organization=self.org_a,
            first_name="Bob",
            last_name="B",
            phone="690222222",
            email="bob.b@example.com",
            created_by=self.agent,
        )
        self.service_a = Service.objects.create(
            organization=self.org_a,
            name="Scolarite",
            description="Mensualite",
            expected_amount="100.00",
            currency="XAF",
            created_by=self.agent,
        )
        self.service_b = Service.objects.create(
            organization=self.org_a,
            name="Transport",
            description="Frais transport",
            expected_amount="90.00",
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

    def test_dashboard_metrics_returns_aggregates_for_active_org(self):
        self.auth("report_agent")
        today = timezone.localdate()
        month_start_dt = timezone.make_aware(datetime.combine(today.replace(day=1), time.min))

        pending = PaymentRequest.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            service=self.service_a,
            expected_amount="100.00",
            paid_amount="0.00",
            status=PaymentRequestStatus.PENDING,
            due_date=today - timedelta(days=1),
            created_by=self.agent,
        )
        partial = PaymentRequest.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            service=self.service_a,
            expected_amount="200.00",
            paid_amount="50.00",
            status=PaymentRequestStatus.PARTIAL,
            due_date=today + timedelta(days=3),
            created_by=self.agent,
        )
        paid = PaymentRequest.objects.create(
            organization=self.org_a,
            customer=self.customer_b,
            service=self.service_b,
            expected_amount="300.00",
            paid_amount="300.00",
            status=PaymentRequestStatus.PAID,
            created_by=self.agent,
        )
        PaymentRequest.objects.create(
            organization=self.org_a,
            customer=self.customer_b,
            service=self.service_b,
            expected_amount="400.00",
            paid_amount="0.00",
            status=PaymentRequestStatus.CANCELLED,
            created_by=self.agent,
        )

        PaymentTransaction.objects.create(
            organization=self.org_a,
            payment_request=partial,
            amount_received="50.00",
            payment_method=PaymentMethod.CASH,
            transaction_reference="RPT-TX-TODAY",
            status=PaymentTransactionStatus.CONFIRMED,
            confirmed_by=self.agent,
            paid_at=timezone.now(),
        )
        PaymentTransaction.objects.create(
            organization=self.org_a,
            payment_request=paid,
            amount_received="300.00",
            payment_method=PaymentMethod.ORANGE_MONEY,
            transaction_reference="RPT-TX-MONTH",
            status=PaymentTransactionStatus.CONFIRMED,
            confirmed_by=self.agent,
            paid_at=month_start_dt + timedelta(days=1),
        )
        PaymentTransaction.objects.create(
            organization=self.org_a,
            payment_request=pending,
            amount_received="90.00",
            payment_method=PaymentMethod.MTN_MOMO,
            transaction_reference="RPT-TX-OLD",
            status=PaymentTransactionStatus.CONFIRMED,
            confirmed_by=self.agent,
            paid_at=timezone.now() - timedelta(days=40),
        )

        response = self.client.get("/api/reporting/dashboard/metrics/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["organization_id"], self.org_a.id)
        self.assertEqual(response.data["today"]["transactions_count"], 1)
        self.assertEqual(response.data["today"]["total_collected"], Decimal("50.00"))
        self.assertEqual(response.data["month"]["transactions_count"], 2)
        self.assertEqual(response.data["month"]["total_collected"], Decimal("350.00"))
        self.assertEqual(response.data["requests"]["total_count"], 4)
        self.assertEqual(response.data["requests"]["expected_total"], Decimal("1000.00"))
        self.assertEqual(response.data["requests"]["paid_total"], Decimal("350.00"))
        self.assertEqual(response.data["requests"]["remaining_gap"], Decimal("250.00"))
        self.assertEqual(response.data["requests"]["overdue_count"], 1)
        self.assertEqual(response.data["requests"]["by_status"]["pending"]["count"], 1)
        self.assertEqual(response.data["requests"]["by_status"]["partial"]["count"], 1)
        self.assertEqual(response.data["requests"]["by_status"]["paid"]["count"], 1)

    def test_dashboard_metrics_supports_customer_filter(self):
        self.auth("report_agent")
        target = PaymentRequest.objects.create(
            organization=self.org_a,
            customer=self.customer_a,
            service=self.service_a,
            expected_amount="100.00",
            paid_amount="0.00",
            status=PaymentRequestStatus.PENDING,
            created_by=self.agent,
        )
        PaymentRequest.objects.create(
            organization=self.org_a,
            customer=self.customer_b,
            service=self.service_b,
            expected_amount="250.00",
            paid_amount="250.00",
            status=PaymentRequestStatus.PAID,
            created_by=self.agent,
        )
        PaymentTransaction.objects.create(
            organization=self.org_a,
            payment_request=target,
            amount_received="20.00",
            payment_method=PaymentMethod.CASH,
            transaction_reference="RPT-TX-FILTER",
            status=PaymentTransactionStatus.CONFIRMED,
            confirmed_by=self.agent,
            paid_at=timezone.now(),
        )

        response = self.client.get(
            f"/api/reporting/dashboard/metrics/?customer_id={self.customer_a.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["requests"]["total_count"], 1)
        self.assertEqual(response.data["requests"]["expected_total"], Decimal("100.00"))
        self.assertEqual(response.data["month"]["total_collected"], Decimal("20.00"))

    def test_dashboard_metrics_requires_valid_tenant_context(self):
        self.auth("report_no_tenant")
        response = self.client.get("/api/reporting/dashboard/metrics/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("organization_id", response.data["error"]["details"])


class ReportingExportsTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.agent = User.objects.create_user(
            username="export_agent",
            email="export_agent@example.com",
            password="CollectPaySecure123!",
        )
        self.agent.account_profile.role = UserRole.AGENT
        self.agent.account_profile.save()

        self.org_a = Organization.objects.create(name="Export Org A", slug="export-org-a")
        self.org_b = Organization.objects.create(name="Export Org B", slug="export-org-b")
        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.agent,
            role=OrganizationRole.AGENT,
        )
        self.agent.account_profile.active_organization = self.org_a
        self.agent.account_profile.save()

        self.customer_a = Customer.objects.create(
            organization=self.org_a,
            first_name="Client",
            last_name="Alpha",
            phone="697000001",
            email="client.alpha@example.com",
            created_by=self.agent,
        )
        self.customer_b = Customer.objects.create(
            organization=self.org_a,
            first_name="Client",
            last_name="Beta",
            phone="697000002",
            email="client.beta@example.com",
            created_by=self.agent,
        )
        self.service_a = Service.objects.create(
            organization=self.org_a,
            name="Inscription",
            description="Inscription annuelle",
            expected_amount="5000.00",
            currency="XAF",
            created_by=self.agent,
        )
        self.service_b = Service.objects.create(
            organization=self.org_a,
            name="Transport",
            description="Transport scolaire",
            expected_amount="3000.00",
            currency="XAF",
            created_by=self.agent,
        )

    def auth(self):
        login = self.client.post(
            "/api/auth/login/",
            {"username": "export_agent", "password": "CollectPaySecure123!"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def create_request(
        self,
        customer,
        service,
        status_value=PaymentRequestStatus.PENDING,
        expected_amount="1000.00",
        paid_amount="0.00",
    ):
        return PaymentRequest.objects.create(
            organization=self.org_a,
            customer=customer,
            service=service,
            status=status_value,
            expected_amount=expected_amount,
            paid_amount=paid_amount,
            due_date=timezone.localdate() + timedelta(days=5),
            created_by=self.agent,
        )

    def test_csv_export_returns_filtered_dataset(self):
        self.auth()
        self.create_request(self.customer_a, self.service_a, status_value=PaymentRequestStatus.PENDING)
        self.create_request(
            self.customer_b,
            self.service_b,
            status_value=PaymentRequestStatus.PAID,
            expected_amount="2000.00",
            paid_amount="2000.00",
        )

        response = self.client.get(
            f"/api/reporting/exports/payment-requests/?export_format=csv&status={PaymentRequestStatus.PENDING}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn(".csv", response["Content-Disposition"])

        payload = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("request_id,reference,status", payload)
        self.assertIn(PaymentRequestStatus.PENDING, payload)
        self.assertNotIn(f",{PaymentRequestStatus.PAID},", payload)

    def test_excel_export_returns_xlsx_attachment(self):
        self.auth()
        self.create_request(self.customer_a, self.service_a)

        response = self.client.get("/api/reporting/exports/payment-requests/?export_format=xlsx")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn(".xlsx", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"PK"))

    def test_pdf_export_returns_pdf_attachment(self):
        self.auth()
        self.create_request(self.customer_a, self.service_a)

        response = self.client.get("/api/reporting/exports/payment-requests/?export_format=pdf")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(".pdf", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_pdf_export_rejects_large_result_set(self):
        self.auth()
        from apps.reporting.views import PaymentRequestExportView

        old_limit = PaymentRequestExportView.PDF_MAX_ROWS
        PaymentRequestExportView.PDF_MAX_ROWS = 1
        try:
            self.create_request(self.customer_a, self.service_a)
            self.create_request(self.customer_b, self.service_b)
            response = self.client.get("/api/reporting/exports/payment-requests/?export_format=pdf")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("limite", str(response.data["error"]["details"]["detail"]))
        finally:
            PaymentRequestExportView.PDF_MAX_ROWS = old_limit
