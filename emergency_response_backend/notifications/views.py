from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from firebase_admin.exceptions import FirebaseError

from .models import Notification
from .serializers import NotificationSerializer
from .services import send_push_notification
from sos.models import SOSNotification
from users.permissions import IsPlatformOrSocietyAdmin, IsResidentOrIncidentAdministrator


class MyNotificationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
        return Response({
            'success': True,
            'data': {
                'unread_count': notifications.filter(is_read=False).count(),
                'results': NotificationSerializer(notifications, many=True).data,
            },
        })


class MarkNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def _mark(self, request, notification_id):
        # Any authenticated role may acknowledge an existing notification.
        # Do not scope the lookup to the current user, because SOS alerts may
        # be delivered across responder roles.
        marked_types = []
        notification = Notification.objects.filter(id=notification_id).first()
        if notification is not None:
            notification.is_read = True
            notification.save(update_fields=['is_read'])
            marked_types.append('in_app')

        # SOS delivery feeds expose SOSNotification IDs. Support those IDs
        # here as well so clients do not have to know which notification
        # table produced the feed item they are acknowledging.
        sos_notification = SOSNotification.objects.filter(id=notification_id).first()
        if sos_notification is not None:
            sos_notification.is_read = True
            sos_notification.save(update_fields=['is_read'])
            marked_types.append('sos')

        if marked_types:
            return Response({
                'success': True,
                'message': 'Notification marked as read',
                'notification_types': marked_types,
                'marked_count': len(marked_types),
            })

        return Response(
            {
                'success': False,
                'message': 'Notification not found.',
                'hint': 'Use an id returned by GET /api/v1/notifications/ or GET /api/v1/incidents/{incident_id}/notifications/.',
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    def patch(self, request, notification_id):
        return self._mark(request, notification_id)

    def post(self, request, notification_id):
        return self._mark(request, notification_id)


class MarkAllNotificationsReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        in_app_count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        sos_count = SOSNotification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({
            'success': True,
            'message': 'Notifications marked as read',
            'marked_count': in_app_count + sos_count,
        })

    def post(self, request):
        return self.patch(request)


class NotificationCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'success': True, 'unread_count': Notification.objects.filter(user=request.user, is_read=False).count()})


class SendSMSView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response({'success': False, 'message': 'Use the SOS incident workflow to send SMS alerts.'}, status=400)


class SendEmailView(APIView):
    permission_classes = [IsAuthenticated, IsResidentOrIncidentAdministrator]

    def post(self, request):
        email = request.data.get('email')
        subject = request.data.get('subject')
        message = request.data.get('message')
        if not email or not subject or not message:
            return Response({'success': False, 'message': 'email, subject, and message are required.'}, status=400)
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
        except Exception:
            return Response({'success': False, 'message': 'Email delivery failed.'}, status=502)
        return Response({'success': True, 'message': 'Email sent successfully'})


class SendNotificationView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformOrSocietyAdmin]

    def post(self, request):
        device_token = request.data.get('device_token')
        topic = request.data.get('topic')
        title = request.data.get('title')
        body = request.data.get('body')
        data = request.data.get('data', {})
        if not (device_token or topic) or not title or not body:
            return Response({'success': False, 'error': 'device_token or topic, title, and body are required'}, status=400)
        if device_token and str(device_token).strip().startswith('REPLACE_WITH_'):
            return Response({
                'success': False,
                'error': 'Replace fcm_device_token with a real Firebase registration token, or use the topic field.'
            }, status=400)
        if topic and str(topic).strip().startswith('REPLACE_WITH_'):
            return Response({
                'success': False,
                'error': 'Replace fcm_topic with a real Firebase topic name.'
            }, status=400)
        try:
            response = send_push_notification(device_token=device_token, topic=topic, title=title, body=body, data=data if isinstance(data, dict) else {})
        except FirebaseError as exc:
            return Response({
                'success': False,
                'error': f'Push notification delivery failed: {str(exc)}',
                'firebase_error_code': getattr(exc, 'code', None),
            }, status=502)
        except Exception as exc:
            return Response({
                'success': False,
                'error': f'Push notification delivery failed: {str(exc)}',
            }, status=502)
        return Response({'success': True, 'message': 'Notification sent successfully', 'firebase_response': response})
