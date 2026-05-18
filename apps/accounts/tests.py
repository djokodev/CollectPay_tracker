from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import UserRole


User = get_user_model()


class FoundationEndpointsTests(SimpleTestCase):
    def test_api_root_endpoint_is_available(self):
        response = self.client.get("/api/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["name"], "CollectPay Tracker API")
        self.assertIn("endpoints", payload)
        self.assertIn("login", payload["endpoints"])

    def test_health_endpoint_is_available(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_schema_endpoint_is_available(self):
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)

    def test_docs_endpoint_is_available(self):
        response = self.client.get("/api/docs/")
        self.assertEqual(response.status_code, 200)

    def test_login_endpoint_is_wired(self):
        response = self.client.post("/api/auth/login/", data={}, content_type="application/json")
        self.assertEqual(response.status_code, 400)


class AuthEndpointsTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_creates_user_with_role(self):
        payload = {
            "username": "agent_a",
            "email": "agent@example.com",
            "first_name": "Agent",
            "last_name": "Alpha",
            "password": "CollectPaySecure123!",
            "role": UserRole.MANAGER,
        }
        response = self.client.post("/api/auth/register/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="agent_a")
        self.assertEqual(user.account_profile.role, UserRole.MANAGER)

    def test_login_returns_tokens_and_profile(self):
        user = User.objects.create_user(
            username="agent_b",
            email="agentb@example.com",
            password="CollectPaySecure123!",
        )
        user.account_profile.role = UserRole.AGENT
        user.account_profile.save()

        response = self.client.post(
            "/api/auth/login/",
            {"username": "agent_b", "password": "CollectPaySecure123!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["username"], "agent_b")

    def test_profile_requires_authentication(self):
        response = self.client.get("/api/auth/profile/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_is_accessible_with_token(self):
        user = User.objects.create_user(
            username="agent_c",
            email="agentc@example.com",
            password="CollectPaySecure123!",
        )

        login_response = self.client.post(
            "/api/auth/login/",
            {"username": "agent_c", "password": "CollectPaySecure123!"},
            format="json",
        )
        token = login_response.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        profile_response = self.client.get("/api/auth/profile/")

        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data["username"], user.username)

    def test_logout_blacklists_refresh_token(self):
        User.objects.create_user(
            username="agent_d",
            email="agentd@example.com",
            password="CollectPaySecure123!",
        )

        login_response = self.client.post(
            "/api/auth/login/",
            {"username": "agent_d", "password": "CollectPaySecure123!"},
            format="json",
        )
        access_token = login_response.data["access"]
        refresh_token = login_response.data["refresh"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        logout_response = self.client.post(
            "/api/auth/logout/",
            {"refresh": refresh_token},
            format="json",
        )

        self.assertEqual(logout_response.status_code, status.HTTP_205_RESET_CONTENT)


class RolePermissionsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin_user",
            email="admin@example.com",
            password="CollectPaySecure123!",
        )
        self.manager = User.objects.create_user(
            username="manager_user",
            email="manager@example.com",
            password="CollectPaySecure123!",
        )
        self.agent = User.objects.create_user(
            username="agent_user",
            email="agent@example.com",
            password="CollectPaySecure123!",
        )

        self.admin.account_profile.role = UserRole.ADMIN
        self.admin.account_profile.save()
        self.manager.account_profile.role = UserRole.MANAGER
        self.manager.account_profile.save()
        self.agent.account_profile.role = UserRole.AGENT
        self.agent.account_profile.save()

    def _auth_as(self, username):
        login_response = self.client.post(
            "/api/auth/login/",
            {"username": username, "password": "CollectPaySecure123!"},
            format="json",
        )
        token = login_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_admin_can_list_users(self):
        self._auth_as("admin_user")
        response = self.client.get("/api/auth/users/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 3)

    def test_non_admin_cannot_list_users(self):
        self._auth_as("manager_user")
        manager_response = self.client.get("/api/auth/users/")
        self.assertEqual(manager_response.status_code, status.HTTP_403_FORBIDDEN)

        self._auth_as("agent_user")
        response = self.client.get("/api/auth/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_only_admin_can_update_role(self):
        self._auth_as("manager_user")
        forbidden_response = self.client.patch(
            f"/api/auth/users/{self.agent.id}/role/",
            {"role": UserRole.VIEWER},
            format="json",
        )
        self.assertEqual(forbidden_response.status_code, status.HTTP_403_FORBIDDEN)

        self._auth_as("admin_user")
        allowed_response = self.client.patch(
            f"/api/auth/users/{self.agent.id}/role/",
            {"role": UserRole.VIEWER},
            format="json",
        )
        self.assertEqual(allowed_response.status_code, status.HTTP_200_OK)
        self.agent.refresh_from_db()
        self.assertEqual(self.agent.account_profile.role, UserRole.VIEWER)

    def test_my_permissions_returns_expected_matrix(self):
        self._auth_as("admin_user")
        response = self.client.get("/api/auth/my-permissions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], UserRole.ADMIN)
        self.assertTrue(response.data["permissions"]["can_update_roles"])
