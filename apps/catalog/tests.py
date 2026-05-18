from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.catalog.models import Service
from apps.organizations.models import Organization, OrganizationMembership, OrganizationRole


User = get_user_model()


class CatalogServicesTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.agent = User.objects.create_user(
            username="svc_agent",
            email="svc_agent@example.com",
            password="CollectPaySecure123!",
        )
        self.viewer = User.objects.create_user(
            username="svc_viewer",
            email="svc_viewer@example.com",
            password="CollectPaySecure123!",
        )

        self.agent.account_profile.role = UserRole.AGENT
        self.agent.account_profile.save()
        self.viewer.account_profile.role = UserRole.VIEWER
        self.viewer.account_profile.save()

        self.org_a = Organization.objects.create(name="Service Org A", slug="service-org-a")
        self.org_b = Organization.objects.create(name="Service Org B", slug="service-org-b")

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

        self.service_a = Service.objects.create(
            organization=self.org_a,
            name="Frais inscription",
            description="Inscription annuelle",
            expected_amount="25000.00",
            currency="XAF",
            created_by=self.agent,
        )
        self.service_b = Service.objects.create(
            organization=self.org_b,
            name="Cotisation B",
            description="Cotisation externe",
            expected_amount="10000.00",
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

    def test_agent_can_create_service(self):
        self.auth("svc_agent")
        response = self.client.post(
            "/api/catalog/services/",
            {
                "name": "Frais mensuels",
                "description": "Mensualite",
                "expected_amount": "15000.00",
                "currency": "XAF",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["organization_id"], self.org_a.id)

    def test_viewer_cannot_create_service(self):
        self.auth("svc_viewer")
        response = self.client.post(
            "/api/catalog/services/",
            {
                "name": "Denied",
                "description": "No",
                "expected_amount": "5000.00",
                "currency": "XAF",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_service_list_scoped_by_organization(self):
        self.auth("svc_agent")
        response = self.client.get("/api/catalog/services/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.service_a.id)

    def test_service_search_filters_results(self):
        self.auth("svc_agent")
        response = self.client.get("/api/catalog/services/?q=inscription")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Frais inscription")

    def test_agent_can_deactivate_service(self):
        self.auth("svc_agent")
        response = self.client.post(f"/api/catalog/services/{self.service_a.id}/deactivate/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.service_a.refresh_from_db()
        self.assertFalse(self.service_a.is_active)
