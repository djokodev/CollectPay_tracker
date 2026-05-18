from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.customers.models import Customer
from apps.organizations.models import Organization, OrganizationMembership, OrganizationRole


User = get_user_model()


class CustomersManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.manager = User.objects.create_user(
            username="cust_manager",
            email="cust_manager@example.com",
            password="CollectPaySecure123!",
        )
        self.agent = User.objects.create_user(
            username="cust_agent",
            email="cust_agent@example.com",
            password="CollectPaySecure123!",
        )
        self.viewer = User.objects.create_user(
            username="cust_viewer",
            email="cust_viewer@example.com",
            password="CollectPaySecure123!",
        )

        self.manager.account_profile.role = UserRole.MANAGER
        self.manager.account_profile.save()
        self.agent.account_profile.role = UserRole.AGENT
        self.agent.account_profile.save()
        self.viewer.account_profile.role = UserRole.VIEWER
        self.viewer.account_profile.save()

        self.org_a = Organization.objects.create(name="Org A", slug="org-a")
        self.org_b = Organization.objects.create(name="Org B", slug="org-b")

        OrganizationMembership.objects.create(
            organization=self.org_a,
            user=self.manager,
            role=OrganizationRole.MANAGER,
        )
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
            first_name="Alice",
            last_name="Ngo",
            phone="690000001",
            email="alice@example.com",
            created_by=self.agent,
        )
        self.customer_b = Customer.objects.create(
            organization=self.org_b,
            first_name="Boris",
            last_name="Mba",
            phone="690000002",
            email="boris@example.com",
            created_by=self.manager,
        )

    def auth(self, username):
        response = self.client.post(
            "/api/auth/login/",
            {"username": username, "password": "CollectPaySecure123!"},
            format="json",
        )
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_agent_can_create_customer_in_active_organization(self):
        self.auth("cust_agent")
        response = self.client.post(
            "/api/customers/",
            {
                "first_name": "Charly",
                "last_name": "Nsom",
                "phone": "690000003",
                "email": "charly@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["organization_id"], self.org_a.id)

    def test_viewer_cannot_create_customer(self):
        self.auth("cust_viewer")
        response = self.client.post(
            "/api/customers/",
            {
                "first_name": "Denied",
                "last_name": "User",
                "phone": "690000004",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_list_is_scoped_to_organization(self):
        self.auth("cust_agent")
        response = self.client.get("/api/customers/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.customer_a.id)

    def test_customer_search_filters_results(self):
        self.auth("cust_agent")
        response = self.client.get("/api/customers/?q=Alice")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["first_name"], "Alice")

    def test_agent_can_deactivate_customer(self):
        self.auth("cust_agent")
        response = self.client.post(f"/api/customers/{self.customer_a.id}/deactivate/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.customer_a.refresh_from_db()
        self.assertFalse(self.customer_a.is_active)

    def test_history_endpoint_returns_payload(self):
        self.auth("cust_agent")
        response = self.client.get(f"/api/customers/{self.customer_a.id}/history/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("customer", response.data)
        self.assertIn("payment_requests", response.data)
        self.assertIn("transactions", response.data)
