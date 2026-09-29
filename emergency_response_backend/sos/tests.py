from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from emergency.models import EmergencyCategory, EmergencyContact
from sos.models import (
    GuardianEscalation,
    GuardianRelationship,
    IncidentHistory,
    SOSIncident,
    SOSNotification,
)
from sos.services import (
    escalate_to_emergency_contact,
    escalate_to_secondary_guardian,
    notify_primary_guardian,
)
from notifications.models import Notification
from users.models import UserProfile

class SOSIncidentEndToEndTestCase(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="tester_sos",
            password="password123",
            email="tester@example.com"
        )
        UserProfile.objects.create(user=self.user, phone="9000000001", role="RESIDENT")
        self.category = EmergencyCategory.objects.create(
            code="medical",
            name="Medical Emergency"
        )
        self.contact = EmergencyContact.objects.create(
            user=self.user,
            name="Emergency Contact 1",
            mobile="+918919875820",
            email="contact@example.com",
            is_verified=True
        )
        self.client.force_authenticate(user=self.user)
        self.url = "/api/v1/sos/incidents/"

    @patch("sos.views.Client")
    @patch("sos.views.send_push_notification")
    def test_create_sos_incident_triggers_notifications_and_db_records(self, mock_push, mock_twilio_client_cls):
        mock_push.return_value = "projects/emergency-test/messages/msg-999"
        mock_twilio_client = MagicMock()
        mock_twilio_client_cls.return_value = mock_twilio_client
        mock_sms_msg = MagicMock()
        mock_sms_msg.sid = "SMsos999"
        mock_twilio_client.messages.create.return_value = mock_sms_msg

        payload = {
            "category": self.category.id,
            "message": "Heart palpitations, need urgent help!",
            "latitude": 17.385044,
            "longitude": 78.486671,
            "accuracy": 10.5
        }

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data.get("success"))

        # 1. Verify SOS Incident in DB
        incident = SOSIncident.objects.get(id=response.data["data"]["id"])
        self.assertEqual(incident.status, "NOTIFICATIONS_SENT")
        self.assertEqual(incident.user, self.user)
        self.assertEqual(incident.category, self.category)

        # 2. Verify Push Notification dispatched
        mock_push.assert_called_once()
        push_notifs = SOSNotification.objects.filter(incident=incident, channel='PUSH')
        self.assertEqual(push_notifs.count(), 1)
        self.assertEqual(push_notifs.first().status, 'SENT')

        # 3. Verify Twilio SMS dispatched
        mock_twilio_client.messages.create.assert_called_once()
        sms_notifs = SOSNotification.objects.filter(incident=incident, channel='SMS')
        self.assertEqual(sms_notifs.count(), 1)
        self.assertEqual(sms_notifs.first().status, 'SENT')

        # 4. Verify in-app Notification record in DB
        in_app_notifs = Notification.objects.filter(user=self.user, notification_type='SOS')
        self.assertTrue(in_app_notifs.exists())


class GuardianEscalationWorkflowTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.resident = User.objects.create_user('resident', password='password123')
        self.primary = User.objects.create_user('primary', password='password123')
        self.secondary = User.objects.create_user('secondary', password='password123')
        self.emergency = User.objects.create_user('emergency', password='password123')
        UserProfile.objects.create(user=self.resident, phone="9000000002", role="RESIDENT")
        UserProfile.objects.create(user=self.primary, phone="9000000003", role="GUARDIAN")
        UserProfile.objects.create(user=self.secondary, phone="9000000004", role="GUARDIAN")
        UserProfile.objects.create(user=self.emergency, phone="9000000005", role="GUARDIAN")
        self.category = EmergencyCategory.objects.create(code='fire', name='Fire')
        self.incident = SOSIncident.objects.create(
            user=self.resident,
            category=self.category,
            message='Test guardian workflow',
        )
        GuardianRelationship.objects.create(
            resident=self.resident,
            guardian=self.primary,
            relationship_type='PRIMARY',
        )
        GuardianRelationship.objects.create(
            resident=self.resident,
            guardian=self.secondary,
            relationship_type='SECONDARY',
        )
        GuardianRelationship.objects.create(
            resident=self.resident,
            guardian=self.emergency,
            relationship_type='EMERGENCY',
        )

    @patch('sos.services.create_notification')
    def test_primary_secondary_and_emergency_workflow(self, notify):
        primary = notify_primary_guardian(self.incident)
        self.assertEqual(primary.guardian, self.primary)
        self.assertEqual(primary.level, 1)
        self.assertEqual(primary.status, 'NOTIFIED')

        secondary = escalate_to_secondary_guardian(self.incident)
        primary.refresh_from_db()
        self.assertEqual(primary.status, 'NO_RESPONSE')
        self.assertEqual(secondary.guardian, self.secondary)
        self.assertEqual(secondary.level, 2)

        emergency_escalations = escalate_to_emergency_contact(self.incident)
        secondary.refresh_from_db()
        self.assertEqual(secondary.status, 'NO_RESPONSE')
        self.assertEqual(len(emergency_escalations), 1)
        self.assertEqual(emergency_escalations[0].guardian, self.emergency)
        self.assertEqual(emergency_escalations[0].level, 3)
        self.assertEqual(self.incident.history.count(), 3)
        self.assertEqual(notify.call_count, 3)

    @patch('sos.services.create_notification')
    def test_guardian_response_stops_further_escalation(self, notify):
        notify_primary_guardian(self.incident)
        self.client.force_authenticate(self.primary)

        response = self.client.post(
            f'/api/v1/sos/incidents/{self.incident.id}/guardian/respond/',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        escalation = GuardianEscalation.objects.get(incident=self.incident, guardian=self.primary)
        self.assertEqual(escalation.status, 'RESPONDED')
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, 'RESPONSE_RECEIVED')
        self.assertTrue(
            IncidentHistory.objects.filter(
                incident=self.incident,
                event='GUARDIAN_RESPONDED',
            ).exists()
        )

        self.client.force_authenticate(self.resident)
        response = self.client.post(
            f'/api/v1/sos/incidents/{self.incident.id}/guardian/escalate/',
            {'level': 2},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    @patch('sos.services.create_notification')
    def test_manual_escalation_requires_incident_owner(self, notify):
        self.client.force_authenticate(self.primary)
        response = self.client.post(
            f'/api/v1/sos/incidents/{self.incident.id}/guardian/escalate/',
            {'level': 2},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.resident)
        response = self.client.post(
            f'/api/v1/sos/incidents/{self.incident.id}/guardian/escalate/',
            {'level': 2},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['guardian_id'], self.secondary.id)
