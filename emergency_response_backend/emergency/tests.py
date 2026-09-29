from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from twilio.base.exceptions import TwilioRestException
from users.models import UserProfile

class SendSosSMSTestCase(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="sms-test-resident", password="test-password")
        UserProfile.objects.create(user=self.user, phone="+919999999999", role="RESIDENT")
        self.client.force_authenticate(user=self.user)
        self.url = "/api/emergency/send-sos-sms/"

    def test_missing_phone_returns_400(self):
        response = self.client.post(self.url, {"message": "Test SOS"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get("success"))
        self.assertIn("Phone number is required", response.data.get("error"))

    def test_missing_message_returns_400(self):
        response = self.client.post(self.url, {"phone": "+919999999999"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get("success"))
        self.assertIn("Message is required", response.data.get("error"))

    def test_empty_strings_return_400(self):
        response = self.client.post(self.url, {"phone": "   ", "message": "   "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("emergency.views.Client")
    def test_successful_sms_send(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_msg = MagicMock()
        mock_msg.sid = "SMtest123456"
        mock_client.messages.create.return_value = mock_msg

        payload = {
            "phone": "+918919875820",
            "message": "sms_appointment_reminders"
        }
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("success"))
        self.assertEqual(response.data.get("sid"), "SMtest123456")
        mock_client.messages.create.assert_called_once_with(
            body="sms_appointment_reminders",
            from_="+17372508034",
            to="+918919875820"
        )

    @patch("emergency.views.Client")
    def test_twilio_trial_restriction_handling(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.messages.create.side_effect = TwilioRestException(
            status=400,
            uri="/2010-04-01/Accounts/ACtest/Messages.json",
            msg="The number is unverified. Trial accounts cannot send messages to unverified numbers",
            code=21608
        )

        payload = {
            "phone": "+919999999999",
            "message": "Test SOS"
        }
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get("success"))
        self.assertTrue(response.data.get("is_trial_restriction"))
        self.assertEqual(response.data.get("code"), 21608)
        self.assertIsNotNone(response.data.get("trial_note"))
