from django.test import SimpleTestCase


class FoundationEndpointsTests(SimpleTestCase):
    def test_api_root_endpoint_is_available(self):
        response = self.client.get("/api/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["name"], "CollectPay Tracker API")
        self.assertIn("endpoints", payload)
        self.assertIn("token", payload["endpoints"])

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

    def test_token_endpoint_is_wired(self):
        response = self.client.post("/api/auth/token/", data={}, content_type="application/json")
        self.assertEqual(response.status_code, 400)
