from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from emergency.models import EmergencyCategory
from users.models import UserProfile

from .models import GuardianEscalation, GuardianRelationship, SOSIncident


class GuardianEscalationSetupTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.resident = user_model.objects.create_user(
            'guardian-setup-resident', password='password123'
        )
        self.guardian = user_model.objects.create_user(
            'guardian-setup-guardian', password='password123'
        )
        UserProfile.objects.create(
            user=self.resident, phone='9000000201', role='RESIDENT', society_id=1
        )
        UserProfile.objects.create(
            user=self.guardian, phone='9000000202', role='GUARDIAN', society_id=1
        )
        self.category = EmergencyCategory.objects.create(
            code='medical', name='Medical'
        )
        self.client = APIClient()

    def test_relationship_notify_and_guardian_response_flow(self):
        self.client.force_authenticate(self.resident)
        relationship_response = self.client.post(
            '/api/v1/guardians/relationships/',
            {
                'guardian_id': self.guardian.id,
                'relationship_type': 'PRIMARY',
                'is_active': True,
            },
            format='json',
        )
        self.assertEqual(relationship_response.status_code, 201)
        self.assertEqual(GuardianRelationship.objects.count(), 1)

        incident = SOSIncident.objects.create(
            user=self.resident,
            category=self.category,
            message='Guardian setup flow test',
        )
        notify_response = self.client.post(
            f'/api/v1/incidents/{incident.id}/guardian/notify/',
            {},
            format='json',
        )
        self.assertEqual(notify_response.status_code, 200)
        escalation = GuardianEscalation.objects.get(incident=incident)
        self.assertEqual(escalation.guardian_id, self.guardian.id)
        self.assertEqual(escalation.status, 'NOTIFIED')

        self.client.force_authenticate(self.guardian)
        response = self.client.post(
            f'/api/v1/incidents/{incident.id}/guardian/respond/',
            {'response_message': 'I am responding now.'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        escalation.refresh_from_db()
        self.assertEqual(escalation.status, 'RESPONDED')

    def test_notify_explains_missing_primary_guardian(self):
        incident = SOSIncident.objects.create(
            user=self.resident,
            category=self.category,
            message='Missing guardian setup test',
        )
        self.client.force_authenticate(self.resident)
        response = self.client.post(
            f'/api/v1/incidents/{incident.id}/guardian/notify/',
            {},
            format='json',
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn('PRIMARY guardian relationship', response.data['message'])
