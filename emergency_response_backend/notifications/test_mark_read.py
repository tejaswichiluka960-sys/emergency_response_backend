from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from emergency.models import EmergencyCategory
from sos.models import SOSIncident, SOSNotification

from .models import Notification


class MarkNotificationReadTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='notification-reader',
            password='test-password',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.in_app_notification = Notification.objects.create(
            user=self.user,
            notification_type='SOS',
            title='Emergency alert',
            message='Assistance requested.',
        )
        category = EmergencyCategory.objects.create(code='medical', name='Medical')
        incident = SOSIncident.objects.create(
            user=self.user,
            category=category,
            message='Assistance requested.',
        )
        self.sos_notification = SOSNotification.objects.create(
            incident=incident,
            recipient=self.user,
            channel='PUSH',
            status='SENT',
        )

    def test_marks_in_app_notification_read(self):
        response = self.client.patch(
            f'/api/v1/notifications/{self.in_app_notification.id}/read/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertTrue(Notification.objects.get(id=self.in_app_notification.id).is_read)

    def test_marks_sos_notification_read(self):
        response = self.client.patch(
            f'/api/v1/notifications/{self.sos_notification.id}/read/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertIn('sos', response.data['notification_types'])
        self.assertTrue(SOSNotification.objects.get(id=self.sos_notification.id).is_read)

    def test_marks_all_notification_types_read(self):
        response = self.client.patch('/api/v1/notifications/read-all/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['marked_count'], 2)
        self.assertTrue(Notification.objects.get(id=self.in_app_notification.id).is_read)
        self.assertTrue(SOSNotification.objects.get(id=self.sos_notification.id).is_read)
