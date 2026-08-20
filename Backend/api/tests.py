from rest_framework.test import APITestCase


class PlannerApiTests(APITestCase):
    def test_health_endpoint(self):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_chat_requires_a_message(self):
        response = self.client.post("/api/chat/", {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Message is required")

    def test_help_chat_requires_a_message(self):
        response = self.client.post("/api/help/", {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Message is required")

    def test_upload_requires_at_least_one_file(self):
        response = self.client.post("/api/upload/", {}, format="multipart")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["error"],
            "Upload all three required files: guidelines, venues, and activities.",
        )
