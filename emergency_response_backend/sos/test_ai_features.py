from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from emergency.models import EmergencyCategory
from users.models import UserProfile

from .models import (
    AIDigitalTwinSnapshot,
    AIKnowledgeGraphSnapshot,
    GuardianRelationship,
    IncidentMessage,
    SOSIncident,
)


class AdvancedEmergencyFeatureTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.resident = user_model.objects.create_user('ai-resident', password='password123')
        self.guardian = user_model.objects.create_user('ai-guardian', password='password123')
        self.responder = user_model.objects.create_user('ai-responder', password='password123')
        UserProfile.objects.create(user=self.resident, role='RESIDENT', society_id=1, phone='9000000401')
        UserProfile.objects.create(user=self.guardian, role='GUARDIAN', society_id=1, phone='9000000402')
        UserProfile.objects.create(
            user=self.responder,
            role='VOLUNTEER',
            society_id=1,
            phone='9000000403',
            is_available=True,
        )
        category = EmergencyCategory.objects.create(code='ai-medical', name='AI Medical')
        self.incident = SOSIncident.objects.create(
            user=self.resident,
            category=category,
            message='AI feature test incident',
            latitude=17.385,
            longitude=78.4867,
            status='NOTIFICATIONS_SENT',
        )
        GuardianRelationship.objects.create(
            resident=self.resident,
            guardian=self.guardian,
            relationship_type='PRIMARY',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.resident)

    def test_offline_message_queue_and_sync_are_idempotent(self):
        queue_url = f'/api/v1/incidents/{self.incident.id}/chat/offline/'
        sync_url = f'/api/v1/incidents/{self.incident.id}/chat/offline/sync/'

        queued = self.client.post(queue_url, {
            'client_message_id': 'mobile-message-001',
            'message': 'Queued while offline.',
        }, format='json')
        self.assertEqual(queued.status_code, 201)

        duplicate = self.client.post(queue_url, {
            'client_message_id': 'mobile-message-001',
            'message': 'Queued while offline.',
        }, format='json')
        self.assertEqual(duplicate.status_code, 200)

        synced = self.client.post(sync_url, {}, format='json')
        self.assertEqual(synced.status_code, 200)
        self.assertEqual(len(synced.data['data']['synchronized']), 1)
        self.assertEqual(IncidentMessage.objects.filter(incident=self.incident).count(), 1)

        repeat_sync = self.client.post(sync_url, {}, format='json')
        self.assertEqual(repeat_sync.status_code, 200)
        self.assertEqual(repeat_sync.data['data']['synchronized'], [])

    def test_knowledge_graph_is_generated_and_persisted(self):
        response = self.client.get(f'/api/v1/incidents/{self.incident.id}/ai/knowledge-graph/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(node['type'] == 'INCIDENT' for node in response.data['data']['nodes']))
        self.assertTrue(any(edge['relation'] == 'GUARDED_BY' for edge in response.data['data']['edges']))
        self.assertEqual(AIKnowledgeGraphSnapshot.objects.filter(incident=self.incident).count(), 1)

    def test_digital_twin_and_simulation_do_not_change_incident(self):
        twin = self.client.get(f'/api/v1/incidents/{self.incident.id}/ai/digital-twin/')
        self.assertEqual(twin.status_code, 200)
        self.assertEqual(twin.data['data']['incident']['status'], 'NOTIFICATIONS_SENT')
        self.assertEqual(AIDigitalTwinSnapshot.objects.filter(incident=self.incident).count(), 1)

        simulation = self.client.post(
            f'/api/v1/incidents/{self.incident.id}/ai/digital-twin/',
            {'scenario': 'RESPONDER_ACCEPTS'},
            format='json',
        )
        self.assertEqual(simulation.status_code, 200)
        self.assertEqual(simulation.data['data']['simulation']['scenario'], 'RESPONDER_ACCEPTS')
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, 'NOTIFICATIONS_SENT')
