from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from emergency.models import EmergencyCategory
from users.models import UserProfile

from .models import GuardianEscalation, GuardianRelationship, SOSIncident


class GuardianResponsePermissionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.resident = user_model.objects.create_user('guardian-response-resident', password='password123')
        self.guardian = user_model.objects.create_user('guardian-response-guardian', password='password123')
        self.admin = user_model.objects.create_user('guardian-response-admin', password='password123')
        self.subadmin = user_model.objects.create_user('guardian-response-subadmin', password='password123')
        UserProfile.objects.create(user=self.resident, phone='9000000101', role='RESIDENT', society_id=1)
        UserProfile.objects.create(user=self.guardian, phone='9000000102', role='GUARDIAN', society_id=1)
        UserProfile.objects.create(user=self.admin, phone='9000000103', role='ADMIN')
        UserProfile.objects.create(user=self.subadmin, phone='9000000104', role='SUB_ADMIN', society_id=1)
        category = EmergencyCategory.objects.create(code='medical', name='Medical')
        self.category = category
        GuardianRelationship.objects.create(
            resident=self.resident,
            guardian=self.guardian,
            relationship_type='PRIMARY',
        )
        self.client = APIClient()

    def _pending_escalation(self):
        incident = SOSIncident.objects.create(
            user=self.resident,
            category=self.category,
            message='Guardian response permission test',
        )
        return incident, GuardianEscalation.objects.create(
            incident=incident,
            guardian=self.guardian,
            level=1,
            status='NOTIFIED',
        )

    def _assert_can_respond(self, user):
        incident, escalation = self._pending_escalation()
        self.client.force_authenticate(user)
        response = self.client.post(
            f'/api/v1/incidents/{incident.id}/guardian/respond/',
            {'response_message': 'Response recorded.'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['guardian_id'], escalation.guardian_id)

    def test_guardian_can_respond(self):
        self._assert_can_respond(self.guardian)

    def test_admin_can_respond(self):
        self._assert_can_respond(self.admin)

    def test_subadmin_can_respond_within_society(self):
        self._assert_can_respond(self.subadmin)

    def test_guardian_without_pending_escalation_gets_actionable_error(self):
        incident = SOSIncident.objects.create(
            user=self.resident,
            category=self.category,
            message='Guardian response without notification',
        )
        self.client.force_authenticate(self.guardian)

        response = self.client.post(
            f'/api/v1/incidents/{incident.id}/guardian/respond/',
            {'response_message': 'Response recorded.'},
            format='json',
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(response.data['success'] is False)
        self.assertIn('notify the guardian before responding', response.data['message'])
        self.assertNotIn('detail', response.data)
