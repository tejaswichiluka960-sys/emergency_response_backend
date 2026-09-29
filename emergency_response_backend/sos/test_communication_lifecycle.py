import tempfile

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from emergency.models import EmergencyCategory
from users.models import UserProfile

from .models import GuardianRelationship, IncidentHistory, IncidentMessage, SOSIncident


class CommunicationAndLifecycleTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.resident = user_model.objects.create_user('chat-resident', password='password123')
        self.guardian = user_model.objects.create_user('chat-guardian', password='password123')
        self.responder = user_model.objects.create_user('chat-responder', password='password123')
        UserProfile.objects.create(user=self.resident, phone='9000000301', role='RESIDENT', society_id=1)
        UserProfile.objects.create(user=self.guardian, phone='9000000302', role='GUARDIAN', society_id=1)
        UserProfile.objects.create(user=self.responder, phone='9000000303', role='VOLUNTEER', society_id=1)
        category = EmergencyCategory.objects.create(code='medical', name='Medical')
        self.incident = SOSIncident.objects.create(
            user=self.resident,
            category=category,
            message='Communication and lifecycle test',
            status='NOTIFICATIONS_SENT',
        )
        GuardianRelationship.objects.create(
            resident=self.resident,
            guardian=self.guardian,
            relationship_type='PRIMARY',
        )
        self.client = APIClient()

    def test_text_and_voice_messages_are_stored(self):
        self.client.force_authenticate(self.resident)
        url = f'/api/v1/incidents/{self.incident.id}/chat/messages/'

        text_response = self.client.post(url, {'message': 'I am safe.'}, format='json')
        self.assertEqual(text_response.status_code, 201)
        self.assertEqual(text_response.data['data']['message_type'], 'TEXT')

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                audio = SimpleUploadedFile('incident.m4a', b'fake-audio', content_type='audio/mp4')
                voice_response = self.client.post(
                    url,
                    {
                        'message_type': 'VOICE',
                        'duration_seconds': '8',
                        'audio_file': audio,
                    },
                    format='multipart',
                )

        self.assertEqual(voice_response.status_code, 201)
        self.assertEqual(voice_response.data['data']['message_type'], 'VOICE')
        self.assertEqual(voice_response.data['data']['duration_seconds'], 8)
        self.assertEqual(IncidentMessage.objects.filter(incident=self.incident).count(), 2)

    def test_any_authenticated_user_can_use_incident_chat(self):
        outsider = get_user_model().objects.create_user('chat-outsider', password='password123')
        self.client.force_authenticate(outsider)
        url = f'/api/v1/incidents/{self.incident.id}/chat/messages/'

        read_response = self.client.get(url)
        self.assertEqual(read_response.status_code, 200)

        write_response = self.client.post(url, {'message': 'I can assist.'}, format='json')
        self.assertEqual(write_response.status_code, 201)
        self.assertEqual(write_response.data['data']['sender'], outsider.id)

    def test_voice_message_is_limited_to_20_seconds_and_downloadable(self):
        self.client.force_authenticate(self.resident)
        url = f'/api/v1/incidents/{self.incident.id}/chat/messages/'

        too_long = self.client.post(
            url,
            {
                'message_type': 'VOICE',
                'duration_seconds': '21',
                'audio_file': SimpleUploadedFile('too-long.wav', b'fake-audio', content_type='audio/wav'),
            },
            format='multipart',
        )
        self.assertEqual(too_long.status_code, 400)

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                voice_response = self.client.post(
                    url,
                    {
                        'message_type': 'VOICE',
                        'duration_seconds': '20',
                        'audio_file': SimpleUploadedFile('incident.wav', b'fake-audio', content_type='audio/wav'),
                    },
                    format='multipart',
                )
                self.assertEqual(voice_response.status_code, 201)
                message_id = voice_response.data['data']['id']
                self.assertIn(f'/api/v1/incidents/{self.incident.id}/chat/messages/{message_id}/download/',
                              voice_response.data['data']['download_url'])

                download = self.client.get(
                    f'/api/v1/incidents/{self.incident.id}/chat/messages/{message_id}/download/'
                )
                self.assertEqual(download.status_code, 200)
                self.assertIn('attachment', download['Content-Disposition'])
                self.assertEqual(b''.join(download.streaming_content), b'fake-audio')
                download.close()
                # Force Django to reopen the test connection after the streamed
                # file response on Windows closes its underlying resources.
                connection.close()

    def test_a_voice_upload_accepts_audio_extension_when_client_omits_mime_type(self):
        self.client.force_authenticate(self.resident)
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    f'/api/v1/incidents/{self.incident.id}/chat/messages/',
                    {
                        'message_type': 'VOICE',
                        'duration_seconds': '20',
                        'audio_file': SimpleUploadedFile(
                            'incident.m4a', b'client-audio', content_type='application/octet-stream'
                        ),
                    },
                    format='multipart',
                )
        self.assertEqual(response.status_code, 201)

    def test_incident_lifecycle_requires_resolve_before_close(self):
        self.client.force_authenticate(self.resident)
        close_url = f'/api/v1/incidents/{self.incident.id}/close/'
        early_close = self.client.post(close_url, {'closure_note': 'Too early.'}, format='json')
        self.assertEqual(early_close.status_code, 409)

        self.client.force_authenticate(self.responder)
        accept = self.client.post(
            f'/api/v1/incidents/{self.incident.id}/accept/',
            {'response_message': 'Responder accepted.'},
            format='json',
        )
        self.assertEqual(accept.status_code, 200)
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, 'ACTIVE_RESPONSE')

        resolve = self.client.post(
            f'/api/v1/incidents/{self.incident.id}/resolve/',
            {'resolution': 'Assistance completed.'},
            format='json',
        )
        self.assertEqual(resolve.status_code, 200)
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, 'RESOLVED')

        self.client.force_authenticate(self.resident)
        close = self.client.post(close_url, {'closure_note': 'Incident documented and closed.'}, format='json')
        self.assertEqual(close.status_code, 200)
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, 'CLOSED')
        self.assertTrue(IncidentHistory.objects.filter(incident=self.incident, event='INCIDENT_RESOLVED').exists())
        self.assertTrue(IncidentHistory.objects.filter(incident=self.incident, event='INCIDENT_CLOSED').exists())

    def test_status_update_accepts_human_readable_active_response(self):
        self.client.force_authenticate(self.responder)
        response = self.client.patch(
            f'/api/v1/incidents/{self.incident.id}/status/',
            {'status': 'ACTIVE RESPONSE', 'note': 'Responder is on the way.'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['status'], 'active_response')

    def test_closed_incident_can_be_reopened_for_follow_up(self):
        self.incident.status = 'CLOSED'
        self.incident.save(update_fields=['status', 'updated_at'])
        self.client.force_authenticate(self.responder)
        response = self.client.patch(
            f'/api/v1/incidents/{self.incident.id}/status/',
            {'status': 'ACTIVE_RESPONSE'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['status'], 'active_response')
