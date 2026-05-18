from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.organizations.models import OrganizationMembership, OrganizationRole


User = get_user_model()


class OrganizationsTenantTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.admin = User.objects.create_user(
            username="org_admin",
            email="org_admin@example.com",
            password="CollectPaySecure123!",
        )
        self.manager = User.objects.create_user(
            username="org_manager",
            email="org_manager@example.com",
            password="CollectPaySecure123!",
        )
        self.agent = User.objects.create_user(
            username="org_agent",
            email="org_agent@example.com",
            password="CollectPaySecure123!",
        )
        self.viewer = User.objects.create_user(
            username="org_viewer",
            email="org_viewer@example.com",
            password="CollectPaySecure123!",
        )

        self.admin.account_profile.role = UserRole.ADMIN
        self.admin.account_profile.save()
        self.manager.account_profile.role = UserRole.MANAGER
        self.manager.account_profile.save()
        self.agent.account_profile.role = UserRole.AGENT
        self.agent.account_profile.save()
        self.viewer.account_profile.role = UserRole.VIEWER
        self.viewer.account_profile.save()

    def auth(self, username):
        login = self.client.post(
            "/api/auth/login/",
            {"username": username, "password": "CollectPaySecure123!"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_agent_cannot_create_organization(self):
        self.auth("org_agent")
        response = self.client.post(
            "/api/organizations/",
            {"name": "Org Agent", "description": "No create"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_create_organization_and_becomes_owner(self):
        self.auth("org_manager")
        response = self.client.post(
            "/api/organizations/",
            {"name": "CollectPay School", "description": "School tenant"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        org_id = response.data["id"]
        membership = OrganizationMembership.objects.get(
            organization_id=org_id,
            user=self.manager,
        )
        self.assertEqual(membership.role, OrganizationRole.OWNER)

    def test_user_only_sees_own_organizations(self):
        self.auth("org_manager")
        org_response = self.client.post(
            "/api/organizations/",
            {"name": "Tenant A", "description": "A"},
            format="json",
        )
        org_id = org_response.data["id"]

        add_member = self.client.post(
            f"/api/organizations/{org_id}/members/",
            {"user_id": self.viewer.id, "role": OrganizationRole.VIEWER},
            format="json",
        )
        self.assertIn(add_member.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

        self.auth("org_viewer")
        list_response = self.client.get("/api/organizations/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(list_response.data["results"][0]["id"], org_id)

    def test_non_member_cannot_access_organization_detail(self):
        self.auth("org_manager")
        org_response = self.client.post(
            "/api/organizations/",
            {"name": "Tenant B", "description": "B"},
            format="json",
        )
        org_id = org_response.data["id"]

        self.auth("org_agent")
        detail_response = self.client.get(f"/api/organizations/{org_id}/")
        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_manager_can_manage_members(self):
        self.auth("org_manager")
        org_response = self.client.post(
            "/api/organizations/",
            {"name": "Tenant C", "description": "C"},
            format="json",
        )
        org_id = org_response.data["id"]

        add_response = self.client.post(
            f"/api/organizations/{org_id}/members/",
            {"user_id": self.agent.id, "role": OrganizationRole.AGENT},
            format="json",
        )
        self.assertIn(add_response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

        members_response = self.client.get(f"/api/organizations/{org_id}/members/")
        self.assertEqual(members_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(members_response.data), 2)

    def test_switch_active_organization_requires_membership(self):
        self.auth("org_manager")
        org_response = self.client.post(
            "/api/organizations/",
            {"name": "Tenant D", "description": "D"},
            format="json",
        )
        org_id = org_response.data["id"]

        switch_response = self.client.post(
            "/api/organizations/switch-active/",
            {"organization_id": org_id},
            format="json",
        )
        self.assertEqual(switch_response.status_code, status.HTTP_200_OK)
        self.manager.refresh_from_db()
        self.assertEqual(self.manager.account_profile.active_organization_id, org_id)

        invalid_switch = self.client.post(
            "/api/organizations/switch-active/",
            {"organization_id": 999999},
            format="json",
        )
        self.assertEqual(invalid_switch.status_code, status.HTTP_403_FORBIDDEN)
