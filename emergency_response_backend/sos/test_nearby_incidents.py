from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from emergency.models import EmergencyCategory
from users.models import UserProfile

from .models import SOSIncident


class NearbyIncidentViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.responder = user_model.objects.create_user('security', password='password123')
        UserProfile.objects.create(user=self.responder, phone='9000000010', role='SECURITY', society_id=1)
        resident = user_model.objects.create_user('incident-resident', password='password123')
        UserProfile.objects.create(user=resident, phone='9000000011', role='RESIDENT', society_id=1)
        category = EmergencyCategory.objects.create(code='medical', name='Medical')
        SOSIncident.objects.create(
            user=resident,
            category=category,
            message='Nearby incident',
            latitude=13.1144,
            longitude=80.1486,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.responder)

    def test_responder_can_find_nearby_incidents(self):
        response = self.client.get(
            '/api/v1/responders/incidents/nearby/',
            {'latitude': 13.1143, 'longitude': 80.1485, 'radius_km': 5},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertIn('google_maps_url', response.data['data'][0]['location'])

    def test_unresolved_postman_variables_fall_back_to_saved_location(self):
        profile = self.responder.userprofile
        profile.latitude = 13.1143
        profile.longitude = 80.1485
        profile.save(update_fields=['latitude', 'longitude'])

        response = self.client.get(
            '/api/v1/responders/incidents/nearby/',
            {
                'latitude': '{{responder_latitude}}',
                'longitude': '{{responder_longitude}}',
                'radius_km': '{{nearby_radius_km}}',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['search']['latitude'], 13.1143)
        self.assertEqual(response.data['search']['longitude'], 80.1485)
        self.assertEqual(response.data['search']['radius_km'], 5.0)
