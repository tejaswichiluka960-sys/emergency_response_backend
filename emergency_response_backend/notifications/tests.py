from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from users.models import UserProfile

class SendPushNotificationTestCase(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="push-test-admin", password="test-password")
        UserProfile.objects.create(user=self.user, phone="+919999999998", role="ADMIN")
        self.client.force_authenticate(user=self.user)
        self.url = "/api/v1/notifications/send-push/"

    def test_missing_target_returns_400(self):
        payload = {"title": "Alert", "body": "Fire detected"}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get("success"))
        self.assertIn("device_token or topic", response.data.get("error"))

    @patch("notifications.services.messaging.send")
    def test_successful_topic_push_notification(self, mock_send):
        mock_send.return_value = "projects/test-project/messages/topic_12345"
        payload = {
            "topic": "emergency_alerts",
            "title": "Emergency Alert",
            "body": "Resident requested emergency assistance"
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))
        self.assertEqual(response.data.get("firebase_response"), "projects/test-project/messages/topic_12345")

    def test_missing_title_returns_400(self):
        payload = {"device_token": "fcm_token_123", "body": "Fire detected"}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get("success"))
        self.assertIn("title", response.data.get("error"))

    def test_missing_body_returns_400(self):
        payload = {"device_token": "fcm_token_123", "title": "Alert"}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get("success"))
        self.assertIn("body", response.data.get("error"))

    @patch("notifications.services.messaging.send")
    def test_successful_push_notification(self, mock_send):
        mock_send.return_value = "projects/test-project/messages/msg_12345"
        payload = {
            "device_token": "sample_fcm_device_token",
            "title": "Emergency Alert",
            "body": "Resident requested emergency assistance",
            "data": {"incident_id": "101", "type": "MEDICAL"}
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))
        self.assertEqual(response.data.get("firebase_response"), "projects/test-project/messages/msg_12345")
        mock_send.assert_called_once()

    @patch("notifications.services.messaging.send")
    def test_firebase_error_returns_500(self, mock_send):
        mock_send.side_effect = Exception("FCM registration token is not valid")
        payload = {
            "device_token": "invalid_token",
            "title": "Alert",
            "body": "Test message"
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertFalse(response.data.get("success"))
        self.assertIn("FCM registration token is not valid", response.data.get("error"))
