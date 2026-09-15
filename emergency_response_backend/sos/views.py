from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SOSIncident, SOSNotification
from users.models import UserProfile
from notifications.services import create_notification
from django.shortcuts import get_object_or_404
from .models import SOSResponse
from .serializers import(
    SOSIncidentCreateSerializer,
    SOSIncidentSerializer,
    SOSNotificationSerializer,
    SOSResponseSerializer,
)
from .permissions import IsResponder


class CreateSOSIncidentView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = SOSIncidentCreateSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        incident = serializer.save(
            user=request.user,
            status='OPEN'
        )

        incident.status = 'NOTIFICATIONS_SENT'
        incident.save(update_fields=['status'])

        return Response(
            {
                'success': True,
                'message': 'SOS incident created successfully.',
                'data': SOSIncidentSerializer(incident).data
            },
            status=status.HTTP_201_CREATED
        )


class SOSIncidentListView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        incidents = SOSIncident.objects.filter(
            user=request.user
        ).order_by('-created_at')

        serializer = SOSIncidentSerializer(
            incidents,
            many=True
        )

        return Response({
            'success': True,
            'data': serializer.data
        })


class SOSIncidentDetailView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, incident_id):

        incident = SOSIncident.objects.get(
            id=incident_id
        )

        serializer = SOSIncidentSerializer(incident)

        return Response({
            'success': True,
            'data': serializer.data
        })


class SOSIncidentStatusView(APIView):

    permission_classes = [IsAuthenticated]

    def patch(self, request, incident_id):

        incident = SOSIncident.objects.get(
            id=incident_id
        )

        new_status = request.data.get('status')

        allowed_statuses = [
            'OPEN',
            'NOTIFICATIONS_SENT',
            'RESPONSE_RECEIVED',
            'RESOLVED',
            'CANCELLED',
            'ESCALATED'
        ]

        if new_status not in allowed_statuses:
            return Response(
                {
                    'success': False,
                    'message': 'Invalid status.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        incident.status = new_status
        incident.save()

        return Response({
            'success': True,
            'message': 'SOS status updated successfully.',
            'data': SOSIncidentSerializer(incident).data
        })


class SOSNotificationListView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, incident_id):

        notifications = SOSNotification.objects.filter(
            incident_id=incident_id
        )

        serializer = SOSNotificationSerializer(
            notifications,
            many=True
        )

        return Response({
            'success': True,
            'data': serializer.data
        })


class SOSResponseView(APIView):

    def post(self, request, incident_id):

        incident = get_object_or_404(
            SOSIncident,
            id=incident_id
        )

        response_obj = SOSResponse.objects.create(
            incident=incident,
            responder=request.user
        )

        incident.status = 'RESPONSE_RECEIVED'
        incident.save()

        security_users = UserProfile.objects.filter(
            role='SECURITY'
        )

        for profile in security_users:
            create_notification(
                profile.user,
                "Emergency Alert",
                "A resident needs assistance."
            )

        return Response(
            {
                'success': True,
                'message': 'Response recorded successfully.',
                'data': SOSResponseSerializer(
                    response_obj
                ).data
            },
            status=status.HTTP_201_CREATED
        )