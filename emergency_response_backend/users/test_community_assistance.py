from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import UserProfile


class CommunityAssistanceViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.responder = user_model.objects.create_user('volunteer', password='password123')
        UserProfile.objects.create(user=self.responder, phone='9000000001', role='VOLUNTEER', society_id=1)
        self.client = APIClient()
        self.client.force_authenticate(self.responder)

    def test_responder_can_update_availability(self):
        response = self.client.patch(
            '/api/v1/responders/me/availability/',
            {'is_available': True},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['data']['is_available'])

    def test_responder_location_returns_google_maps_url(self):
        response = self.client.post(
            '/api/v1/responders/me/location/',
            {'latitude': 13.1143, 'longitude': 80.1485, 'accuracy': 8.5},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('https://www.google.com/maps/search/', response.data['data']['google_maps_url'])

    def test_resident_cannot_update_responder_availability(self):
        resident = get_user_model().objects.create_user('resident', password='password123')
        UserProfile.objects.create(user=resident, phone='9000000002', role='RESIDENT')
        self.client.force_authenticate(resident)
        response = self.client.patch(
            '/api/v1/responders/me/availability/',
            {'is_available': True},
            format='json',
        )
        self.assertEqual(response.status_code, 403)
