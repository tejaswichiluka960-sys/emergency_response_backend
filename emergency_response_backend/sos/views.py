import os
import uuid
from math import asin, cos, radians, sin, sqrt

from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from twilio.base.exceptions import TwilioException, TwilioRestException
from twilio.rest import Client

from emergency.models import EmergencyContact
from notifications.services import create_notification, send_push_notification
from users.models import UserProfile
from .models import (AIDigitalTwinSnapshot, AIKnowledgeGraphSnapshot, EscalationConfiguration,
                     GuardianEscalation, GuardianRelationship, IncidentHistory, IncidentMessage,
                     OfflineIncidentMessage, SOSIncident, SOSNotification, SOSResponse)
from .ai_features import build_digital_twin, build_knowledge_graph, simulate_digital_twin
from .permissions import (
    IsResponder,
    IsResident,
    IsGuardian,
    IsIncidentAdministrator,
    IsGuardianResponseParticipant,
    IsGuardianRelationshipParticipant,
    IsGuardianWorkflowManager,
    IsResidentOrIncidentAdministrator,
    IsNonResident,
    IsSOSResponder,
)
from users.permissions import (
    PLATFORM_ADMIN_ROLES,
    SOCIETY_ADMIN_ROLES,
    RESPONDER_ROLES,
    get_role,
    is_platform_admin,
    is_society_admin,
)
from .serializers import (IncidentMessageSerializer, SOSIncidentCreateSerializer,
                          SOSIncidentSerializer, SOSNotificationSerializer, SOSResponseSerializer)
from .services import (escalate_to_emergency_contact,
                       escalate_to_secondary_guardian, notify_primary_guardian,
                       record_history)


ADMIN_ROLES = PLATFORM_ADMIN_ROLES | SOCIETY_ADMIN_ROLES

INCIDENT_STATUS_TRANSITIONS = {
    'OPEN': {'NOTIFICATIONS_SENT', 'RESPONSE_RECEIVED', 'ACTIVE_RESPONSE', 'ESCALATED', 'CANCELLED'},
    'NOTIFICATIONS_SENT': {'RESPONSE_RECEIVED', 'ACTIVE_RESPONSE', 'ESCALATED', 'RESOLVED', 'CANCELLED'},
    'RESPONSE_RECEIVED': {'ACTIVE_RESPONSE', 'ESCALATED', 'RESOLVED', 'CANCELLED'},
    'ACTIVE_RESPONSE': {'ESCALATED', 'RESOLVED', 'CANCELLED'},
    'ESCALATED': {'RESPONSE_RECEIVED', 'ACTIVE_RESPONSE', 'RESOLVED', 'CANCELLED'},
    'RESOLVED': {'CLOSED'},
    'CANCELLED': set(),
    # Allow an authorized responder or administrator to reopen a closed
    # incident when follow-up assistance is required.
    'CLOSED': {'ACTIVE_RESPONSE'},
}

INCIDENT_STATUS_ALIASES = {
    'ACTIVE': 'ACTIVE_RESPONSE',
    'ACTIVE_RESPONSE': 'ACTIVE_RESPONSE',
    'IN_PROGRESS': 'ACTIVE_RESPONSE',
    'NOTIFIED': 'NOTIFICATIONS_SENT',
    'NOTIFICATIONS': 'NOTIFICATIONS_SENT',
}


def _role(user):
    return get_role(user)


PREVIEW_RESPONDER_ROLES = {'GUARDIAN', 'VOLUNTEER', 'SECURITY'}


def _dashboard_role(request):
    """Return the effective local dashboard role without weakening production auth."""
    actual_role = _role(request.user)
    requested_role = str(request.headers.get('X-SafeCircle-Dashboard-Role', '')).strip().upper().replace('-', '_')
    if settings.DEBUG and requested_role in PREVIEW_RESPONDER_ROLES:
        return requested_role, True
    return actual_role, False


def _normalize_incident_status(value):
    normalized = str(value or '').strip().upper().replace('-', '_').replace(' ', '_')
    return INCIDENT_STATUS_ALIASES.get(normalized, normalized)


def _same_society(user, incident):
    actor_society = getattr(getattr(user, 'userprofile', None), 'society_id', None)
    owner_society = getattr(getattr(incident.user, 'userprofile', None), 'society_id', None)
    return actor_society is not None and actor_society == owner_society


def _google_maps_url(latitude, longitude):
    return f'https://www.google.com/maps/search/?api=1&query={latitude},{longitude}'


def _is_unresolved_variable(value):
    if not isinstance(value, str):
        return False
    value = value.strip()
    return value.startswith('{{') and value.endswith('}}')


def _responder_can_access(user, incident):
    role = _role(user)
    if role == 'GUARDIAN':
        return GuardianRelationship.objects.filter(
            resident=incident.user, guardian=user, is_active=True
        ).exists()
    if role in {'VOLUNTEER', 'SECURITY'}:
        return _same_society(user, incident) and incident.status not in {'CANCELLED', 'CLOSED'}
    return False


def _can_access(user, incident):
    if incident.user_id == user.id or is_platform_admin(user) or _same_society(user, incident):
        return True
    if SOSResponse.objects.filter(incident=incident, responder=user).exists():
        return True
    return _responder_can_access(user, incident)


def _incident_or_forbidden(request, incident_id):
    incident = get_object_or_404(SOSIncident, id=incident_id)
    if not _can_access(request.user, incident):
        return None, Response({'success': False, 'message': 'You do not have access to this incident.'}, status=403)
    return incident, None


def _communication_incident(incident_id):
    """Communication is available to every authenticated application user."""
    return get_object_or_404(SOSIncident, id=incident_id)


def _response_incident_or_forbidden(request, incident_id):
    """Resolve an incident for the explicitly allowed SOS response roles."""
    incident = get_object_or_404(SOSIncident, id=incident_id)
    if _role(request.user) not in SOCIETY_ADMIN_ROLES | RESPONDER_ROLES:
        return None, Response({'success': False, 'message': 'You do not have permission to respond to this incident.'}, status=403)
    return incident, None


def _response_participant_incident_or_forbidden(request, incident_id):
    """Allow response actions only to assigned guardians and responders."""
    incident = get_object_or_404(SOSIncident, id=incident_id)
    role, is_preview = _dashboard_role(request)
    if is_preview:
        allowed = True
    elif role == 'GUARDIAN':
        relationship_allowed = GuardianRelationship.objects.filter(
            resident=incident.user,
            guardian=request.user,
            is_active=True,
        ).exists()
        escalation_allowed = GuardianEscalation.objects.filter(
            incident=incident,
            guardian=request.user,
            status__in=['PENDING', 'NOTIFIED'],
        ).exists()
        allowed = relationship_allowed or escalation_allowed
    elif role in {'VOLUNTEER', 'SECURITY'}:
        allowed = _responder_can_access(request.user, incident)
    else:
        allowed = False
    if not allowed:
        return None, Response({'success': False, 'message': 'Only the assigned guardian, volunteer, or security responder may act on this incident.'}, status=403)
    return incident, None


def _preview_or_incident_forbidden(request, incident_id):
    """Allow local dashboard previews to inspect an incident for response actions."""
    _, is_preview = _dashboard_role(request)
    if is_preview:
        return get_object_or_404(SOSIncident, id=incident_id), None
    return _incident_or_forbidden(request, incident_id)


def _transition_incident(incident, new_status, actor, event='STATUS_UPDATED', message=''):
    new_status = str(new_status).upper()
    if new_status == incident.status:
        return None
    allowed = INCIDENT_STATUS_TRANSITIONS.get(incident.status, set())
    if new_status not in allowed:
        return Response({
            'success': False,
            'message': f'Cannot transition incident from {incident.status} to {new_status}.',
            'current_status': incident.status,
            'requested_status': new_status,
        }, status=status.HTTP_409_CONFLICT)
    incident.status = new_status
    incident.save(update_fields=['status', 'updated_at'])
    record_history(incident, event, message or f'Incident status changed to {new_status}.', actor)
    return None


class CreateSOSIncidentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Every authenticated role may read the incident feed. Creation stays
        # resident-only and is enforced in post() below.
        incidents = SOSIncident.objects.all().order_by('-created_at')
        if request.query_params.get('status'):
            incidents = incidents.filter(status=request.query_params['status'].upper())
        if request.query_params.get('category'):
            incidents = incidents.filter(category__code=request.query_params['category'].lower())
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        page = max(int(request.query_params.get('page', 1)), 1)
        start = (page - 1) * page_size
        data = SOSIncidentSerializer(incidents[start:start + page_size], many=True).data
        return Response({'success': True, 'data': data, 'page': page, 'page_size': page_size})

    def post(self, request):
        if _role(request.user) != 'RESIDENT':
            return Response({'success': False, 'message': 'Only residents may trigger an SOS incident.'}, status=403)

        serializer = SOSIncidentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        incident = serializer.save(user=request.user, status='OPEN')
        # Preserve the resident's last synced device location when the
        # browser could not include coordinates in this SOS request.
        resident_profile = getattr(request.user, 'userprofile', None)
        if (incident.latitude is None or incident.longitude is None) and resident_profile and resident_profile.latitude is not None and resident_profile.longitude is not None:
            incident.latitude = resident_profile.latitude
            incident.longitude = resident_profile.longitude
            incident.accuracy = resident_profile.accuracy
            incident.save(update_fields=['latitude', 'longitude', 'accuracy', 'updated_at'])
        record_history(incident, 'INCIDENT_CREATED', 'SOS incident created.', request.user)

        # Keep an in-app record for the resident who triggered the alert so
        # the originating client can show the alert in its notification feed.
        create_notification(
            request.user,
            'Emergency Alert Created',
            f"{incident.message or 'Your emergency alert was activated.'} { _google_maps_url(incident.latitude, incident.longitude) if incident.latitude is not None and incident.longitude is not None else 'Location was not shared.' }",
            'SOS',
        )
        primary = notify_primary_guardian(incident)

        push_summary = {'status': 'skipped'}
        try:
            push_response = send_push_notification(
                topic='emergency_alerts',
                title=f'SOS Alert: {incident.category.name}',
                body=f"{incident.message or 'A resident triggered an emergency alert.'} {'Location shared.' if incident.latitude is not None and incident.longitude is not None else 'Location unavailable.'}",
                data={
                    'incident_id': str(incident.id),
                    'category': incident.category.code,
                    'latitude': str(incident.latitude) if incident.latitude is not None else '',
                    'longitude': str(incident.longitude) if incident.longitude is not None else '',
                    'location_url': _google_maps_url(incident.latitude, incident.longitude) if incident.latitude is not None and incident.longitude is not None else '',
                },
            )
            SOSNotification.objects.create(incident=incident, recipient=request.user, channel='PUSH', status='SENT', sent_at=timezone.now())
            push_summary = {'status': 'sent', 'response': push_response}
        except Exception:
            SOSNotification.objects.create(incident=incident, recipient=request.user, channel='PUSH', status='FAILED')
            push_summary = {'status': 'failed'}

        sms_summary = []
        recipients = [str(request.data['phone']).strip()] if request.data.get('phone') else []
        recipients += [c.mobile.strip() for c in EmergencyContact.objects.filter(user=request.user) if c.mobile and c.mobile.strip() not in recipients]
        account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None) or os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None) or os.getenv('TWILIO_AUTH_TOKEN')
        from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', None) or os.getenv('TWILIO_PHONE_NUMBER')
        if account_sid and auth_token and from_number:
            try:
                client = Client(account_sid, auth_token)
                for phone in recipients:
                    normalized = phone if phone.startswith('+') else (f'+91{phone}' if len(phone) == 10 else f'+{phone}')
                    try:
                        message = client.messages.create(
                            body=f'SOS ALERT: {incident.category.name}. {incident.message or "Immediate assistance required."}',
                            from_=from_number, to=normalized,
                        )
                        SOSNotification.objects.create(incident=incident, recipient=request.user, channel='SMS', status='SENT', sent_at=timezone.now())
                        sms_summary.append({'phone': normalized, 'status': 'sent', 'sid': message.sid})
                    except (TwilioRestException, TwilioException):
                        SOSNotification.objects.create(incident=incident, recipient=request.user, channel='SMS', status='FAILED')
                        sms_summary.append({'phone': normalized, 'status': 'failed'})
            except Exception:
                sms_summary.append({'status': 'failed'})

        # In-app routing for configured responders and email delivery for
        # verified emergency contacts. Delivery attempts are recorded.
        responder_users = UserProfile.objects.filter(
            role__in=['SECURITY', 'VOLUNTEER']
        ).select_related('user')
        if primary:
            primary_profile = UserProfile.objects.filter(user_id=primary.guardian_id).select_related('user').first()
            responder_users = list(responder_users) + ([primary_profile] if primary_profile else [])
        for profile in responder_users:
            try:
                location_message = (
                    f" Location: {_google_maps_url(incident.latitude, incident.longitude)}"
                    if incident.latitude is not None and incident.longitude is not None
                    else ' Location sharing is unavailable until the resident shares device location.'
                )
                create_notification(
                    profile.user,
                    'Emergency Alert',
                    f"{incident.message or 'A resident needs assistance.'}{location_message}",
                    'SOS',
                )
                SOSNotification.objects.create(
                    incident=incident,
                    recipient=profile.user,
                    channel='IN_APP',
                    status='SENT',
                    sent_at=timezone.now(),
                )
            except Exception:
                SOSNotification.objects.create(
                    incident=incident,
                    recipient=request.user,
                    channel='IN_APP',
                    status='FAILED',
                )

        for contact in EmergencyContact.objects.filter(user=request.user, is_verified=True):
            try:
                send_mail(
                    f'SOS Alert: {incident.category.name}',
                    incident.message or 'A resident needs immediate assistance.',
                    settings.DEFAULT_FROM_EMAIL,
                    [contact.email],
                    fail_silently=False,
                )
                SOSNotification.objects.create(incident=incident, recipient=request.user, channel='EMAIL', status='SENT', sent_at=timezone.now())
            except Exception:
                SOSNotification.objects.create(incident=incident, recipient=request.user, channel='EMAIL', status='FAILED')

        incident.status = 'NOTIFICATIONS_SENT'
        incident.save(update_fields=['status', 'updated_at'])
        return Response({
            'success': True,
            'message': 'Emergency alert activated.',
            'data': SOSIncidentSerializer(incident).data,
            'notifications_dispatched': {'push': push_summary, 'sms': sms_summary},
            'guardian_escalation': {'status': 'notified' if primary else 'not_configured', 'level': primary.level if primary else None},
        }, status=201)


class SOSIncidentListView(APIView):
    """Incident feed available to every authenticated role."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        incidents = SOSIncident.objects.all()

        if request.query_params.get('status'):
            incidents = incidents.filter(status=request.query_params['status'].upper())
        if request.query_params.get('category'):
            incidents = incidents.filter(category__code=request.query_params['category'].lower())
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        page = max(int(request.query_params.get('page', 1)), 1)
        start = (page - 1) * page_size
        data = SOSIncidentSerializer(incidents.order_by('-created_at')[start:start + page_size], many=True).data
        return Response({'success': True, 'data': data, 'page': page, 'page_size': page_size})


class SOSIncidentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, incident_id):
        incident = get_object_or_404(SOSIncident, id=incident_id)
        return Response({'success': True, 'data': SOSIncidentSerializer(incident).data})


class IncidentChatView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, incident_id):
        incident = _communication_incident(incident_id)
        messages = incident.chat_messages.select_related('sender').all()
        return Response({
            'success': True,
            'data': {
                'incident_id': incident.id,
                'status': incident.status,
                'messages': IncidentMessageSerializer(
                    messages,
                    many=True,
                    context={'request': request},
                ).data,
            },
        })


class IncidentChatMessagesView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request, incident_id):
        incident = _communication_incident(incident_id)
        messages = incident.chat_messages.select_related('sender').all()
        return Response({
            'success': True,
            'data': IncidentMessageSerializer(
                messages,
                many=True,
                context={'request': request},
            ).data,
        })

    def post(self, request, incident_id):
        incident = _communication_incident(incident_id)
        if incident.status in {'CANCELLED', 'CLOSED'}:
            return Response({
                'success': False,
                'message': 'Chat is read-only after an incident is cancelled or closed.',
            }, status=status.HTTP_409_CONFLICT)

        message_type = str(request.data.get('message_type', 'TEXT')).strip().upper()
        if message_type not in {'TEXT', 'VOICE'}:
            return Response({'success': False, 'message': 'message_type must be TEXT or VOICE.'}, status=400)

        message_text = str(request.data.get('message') or '').strip()
        audio_file = request.FILES.get('audio_file')
        if message_type == 'TEXT':
            if not message_text:
                return Response({'success': False, 'message': 'message is required for a TEXT message.'}, status=400)
            if audio_file:
                return Response({'success': False, 'message': 'audio_file is only valid for a VOICE message.'}, status=400)
        else:
            if not audio_file:
                return Response({'success': False, 'message': 'audio_file is required for a VOICE message.'}, status=400)
            content_type = str(getattr(audio_file, 'content_type', '')).lower()
            file_extension = os.path.splitext(str(getattr(audio_file, 'name', '')))[1].lower()
            audio_extensions = {'.aac', '.flac', '.m4a', '.mp3', '.ogg', '.opus', '.wav', '.webm'}
            if not content_type.startswith('audio/') and file_extension not in audio_extensions:
                return Response({
                    'success': False,
                    'message': 'audio_file must be an audio file (mp3, m4a, wav, ogg, webm, aac, flac, or opus).',
                }, status=400)
            if audio_file.size > 10 * 1024 * 1024:
                return Response({'success': False, 'message': 'audio_file must be 10 MB or smaller.'}, status=400)
            message_text = message_text or 'Voice message'

        duration_value = request.data.get('duration_seconds')
        duration_seconds = None
        if duration_value not in (None, ''):
            try:
                duration_seconds = int(duration_value)
            except (TypeError, ValueError):
                return Response({'success': False, 'message': 'duration_seconds must be a whole number.'}, status=400)
            if duration_seconds <= 0 or duration_seconds > 20:
                return Response({'success': False, 'message': 'duration_seconds must be between 1 and 20 seconds.'}, status=400)

        incident_message = IncidentMessage.objects.create(
            incident=incident,
            sender=request.user,
            message_type=message_type,
            message=message_text,
            audio_file=audio_file if message_type == 'VOICE' else None,
            duration_seconds=duration_seconds,
        )
        record_history(
            incident,
            'CHAT_MESSAGE_SENT',
            f'{message_type} message sent by {request.user.username}.',
            request.user,
        )
        return Response({
            'success': True,
            'message': 'Chat message sent successfully.',
            'data': IncidentMessageSerializer(
                incident_message,
                context={'request': request},
            ).data,
        }, status=status.HTTP_201_CREATED)


class IncidentMessageDownloadView(APIView):
    """Download an uploaded voice message for any authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request, incident_id, message_id):
        incident = _communication_incident(incident_id)
        message = get_object_or_404(
            IncidentMessage,
            id=message_id,
            incident=incident,
            message_type='VOICE',
        )
        if not message.audio_file:
            return Response({'success': False, 'message': 'This voice message has no audio file.'}, status=404)
        try:
            audio = message.audio_file.open('rb')
        except FileNotFoundError:
            return Response({'success': False, 'message': 'The voice message file is unavailable.'}, status=404)
        return FileResponse(
            audio,
            as_attachment=True,
            filename=os.path.basename(message.audio_file.name),
            content_type='audio/mpeg' if message.audio_file.name.lower().endswith(('.mp3', '.mpeg')) else 'audio/wav',
        )


def _offline_message_data(message):
    return {
        'id': message.id,
        'client_message_id': message.client_message_id,
        'incident_id': message.incident_id,
        'message_type': message.message_type,
        'message': message.message,
        'duration_seconds': message.duration_seconds,
        'sync_status': message.sync_status,
        'sync_attempts': message.sync_attempts,
        'error_message': message.error_message,
        'synced_message_id': message.synced_message_id,
        'client_created_at': message.client_created_at,
        'synced_at': message.synced_at,
        'created_at': message.created_at,
    }


class OfflineMessageQueueView(APIView):
    """Queue messages locally on the server and synchronize them after reconnect."""

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request, incident_id):
        incident = _communication_incident(incident_id)
        queued = OfflineIncidentMessage.objects.filter(
            incident=incident,
            sender=request.user,
        )
        return Response({'success': True, 'data': [_offline_message_data(item) for item in queued]})

    def post(self, request, incident_id):
        incident = _communication_incident(incident_id)
        client_message_id = str(request.data.get('client_message_id') or uuid.uuid4()).strip()
        existing = OfflineIncidentMessage.objects.filter(client_message_id=client_message_id).first()
        if existing:
            if existing.sender_id != request.user.id or existing.incident_id != incident.id:
                return Response({'success': False, 'message': 'client_message_id is already in use.'}, status=409)
            return Response({'success': True, 'message': 'Offline message already queued.', 'data': _offline_message_data(existing)}, status=200)

        message_type = str(request.data.get('message_type', 'TEXT')).strip().upper()
        if message_type not in {'TEXT', 'VOICE'}:
            return Response({'success': False, 'message': 'message_type must be TEXT or VOICE.'}, status=400)
        message_text = str(request.data.get('message') or '').strip()
        audio_file = request.FILES.get('audio_file')
        if message_type == 'TEXT' and not message_text:
            return Response({'success': False, 'message': 'message is required for a TEXT message.'}, status=400)
        if message_type == 'VOICE':
            if not audio_file:
                return Response({'success': False, 'message': 'audio_file is required for a VOICE message.'}, status=400)
            content_type = str(getattr(audio_file, 'content_type', '')).lower()
            file_extension = os.path.splitext(str(getattr(audio_file, 'name', '')))[1].lower()
            audio_extensions = {'.aac', '.flac', '.m4a', '.mp3', '.ogg', '.opus', '.wav', '.webm'}
            if not content_type.startswith('audio/') and file_extension not in audio_extensions:
                return Response({'success': False, 'message': 'audio_file must be an audio file.'}, status=400)
            if audio_file.size > 10 * 1024 * 1024:
                return Response({'success': False, 'message': 'audio_file must be 10 MB or smaller.'}, status=400)
            message_text = message_text or 'Voice message'

        duration_seconds = None
        duration_value = request.data.get('duration_seconds')
        if duration_value not in (None, ''):
            try:
                duration_seconds = int(duration_value)
            except (TypeError, ValueError):
                return Response({'success': False, 'message': 'duration_seconds must be a whole number.'}, status=400)
            if duration_seconds <= 0 or duration_seconds > 20:
                return Response({'success': False, 'message': 'duration_seconds must be between 1 and 20 seconds.'}, status=400)

        client_created_at = request.data.get('client_created_at')
        parsed_client_created_at = parse_datetime(str(client_created_at)) if client_created_at else None
        offline_message = OfflineIncidentMessage.objects.create(
            incident=incident,
            sender=request.user,
            client_message_id=client_message_id,
            message_type=message_type,
            message=message_text,
            audio_file=audio_file if message_type == 'VOICE' else None,
            duration_seconds=duration_seconds,
            client_created_at=parsed_client_created_at,
        )
        return Response({
            'success': True,
            'message': 'Message queued for synchronization.',
            'data': _offline_message_data(offline_message),
        }, status=201)


class OfflineMessageSyncView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, incident_id):
        incident = _communication_incident(incident_id)
        synchronized = []
        failed = []
        queued = OfflineIncidentMessage.objects.filter(
            incident=incident,
            sender=request.user,
            sync_status='QUEUED',
        ).order_by('created_at', 'id')
        for queued_message in queued:
            with transaction.atomic():
                queued_message = OfflineIncidentMessage.objects.select_for_update().get(id=queued_message.id)
                if queued_message.sync_status != 'QUEUED':
                    continue
                queued_message.sync_attempts += 1
                if incident.status in {'CANCELLED', 'CLOSED'}:
                    queued_message.sync_status = 'FAILED'
                    queued_message.error_message = 'Incident is not accepting new messages.'
                    queued_message.save(update_fields=['sync_attempts', 'sync_status', 'error_message'])
                    failed.append(_offline_message_data(queued_message))
                    continue
                if queued_message.message_type == 'VOICE' and not queued_message.audio_file:
                    queued_message.sync_status = 'FAILED'
                    queued_message.error_message = 'Voice message has no audio file.'
                    queued_message.save(update_fields=['sync_attempts', 'sync_status', 'error_message'])
                    failed.append(_offline_message_data(queued_message))
                    continue
                synced_message = IncidentMessage.objects.create(
                    incident=incident,
                    sender=request.user,
                    message_type=queued_message.message_type,
                    message=queued_message.message,
                    audio_file=queued_message.audio_file,
                    duration_seconds=queued_message.duration_seconds,
                )
                record_history(
                    incident,
                    'OFFLINE_MESSAGE_SYNCED',
                    f'{queued_message.message_type} offline message synchronized by {request.user.username}.',
                    request.user,
                )
                queued_message.sync_status = 'SYNCED'
                queued_message.synced_message = synced_message
                queued_message.synced_at = timezone.now()
                queued_message.save(update_fields=['sync_attempts', 'sync_status', 'synced_message', 'synced_at'])
                synchronized.append(_offline_message_data(queued_message))
        return Response({
            'success': True,
            'message': 'Offline message synchronization completed.',
            'data': {'synchronized': synchronized, 'failed': failed},
        })


class AIKnowledgeGraphView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, incident_id):
        incident = _communication_incident(incident_id)
        graph = build_knowledge_graph(incident)
        snapshot = AIKnowledgeGraphSnapshot.objects.create(
            incident=incident,
            requested_by=request.user,
            graph=graph,
        )
        graph['snapshot_id'] = snapshot.id
        return Response({
            'success': True,
            'message': 'AI knowledge graph generated.',
            'data': graph,
        })


class AIDigitalTwinView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, incident_id):
        incident = _communication_incident(incident_id)
        twin = build_digital_twin(incident)
        snapshot = AIDigitalTwinSnapshot.objects.create(
            incident=incident,
            requested_by=request.user,
            twin=twin,
        )
        twin['snapshot_id'] = snapshot.id
        return Response({
            'success': True,
            'message': 'AI emergency digital twin generated.',
            'data': twin,
        })

    def post(self, request, incident_id):
        incident = _communication_incident(incident_id)
        return Response({
            'success': True,
            'message': 'Digital twin scenario simulated without changing the incident.',
            'data': simulate_digital_twin(incident, request.data.get('scenario')),
        })


class SOSIncidentStatusView(APIView):
    permission_classes = [IsAuthenticated, IsNonResident]

    def patch(self, request, incident_id):
        incident, error = _incident_or_forbidden(request, incident_id)
        if error:
            return error
        new_status = _normalize_incident_status(request.data.get('status'))
        if new_status not in INCIDENT_STATUS_TRANSITIONS:
            return Response({
                'success': False,
                'message': 'Invalid incident status.',
                'allowed_statuses': list(INCIDENT_STATUS_TRANSITIONS.keys()),
                'accepted_aliases': {'ACTIVE': 'ACTIVE_RESPONSE', 'IN_PROGRESS': 'ACTIVE_RESPONSE'},
            }, status=400)
        transition_error = _transition_incident(
            incident,
            new_status,
            request.user,
            message=request.data.get('note', ''),
        )
        if transition_error:
            return transition_error
        return Response({'success': True, 'message': 'Incident status updated successfully.', 'data': SOSIncidentSerializer(incident).data})


class CancelIncidentView(APIView):
    permission_classes = [IsAuthenticated, IsResident]

    def post(self, request, incident_id):
        incident = get_object_or_404(SOSIncident, id=incident_id, user=request.user)
        transition_error = _transition_incident(
            incident,
            'CANCELLED',
            request.user,
            event='INCIDENT_CANCELLED',
            message=request.data.get('reason', ''),
        )
        if transition_error:
            return transition_error
        return Response({'success': True, 'message': 'Incident cancelled successfully.'})


class ResolveIncidentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, incident_id):
        incident, error = _preview_or_incident_forbidden(request, incident_id)
        effective_role, is_preview = _dashboard_role(request)
        if error or (not is_preview and effective_role not in RESPONDER_ROLES | ADMIN_ROLES):
            return error or Response({'success': False, 'message': 'Only a responder or administrator may resolve an incident.'}, status=403)
        transition_error = _transition_incident(
            incident,
            'RESOLVED',
            request.user,
            event='INCIDENT_RESOLVED',
            message=request.data.get('resolution', ''),
        )
        if transition_error:
            return transition_error
        return Response({'success': True, 'message': 'Incident resolved successfully.', 'data': SOSIncidentSerializer(incident).data})


class CloseIncidentView(APIView):
    permission_classes = [IsAuthenticated, IsResidentOrIncidentAdministrator]

    def post(self, request, incident_id):
        incident = get_object_or_404(SOSIncident, id=incident_id)
        if incident.user_id != request.user.id and not (is_platform_admin(request.user) or _same_society(request.user, incident)):
            return Response({'success': False, 'message': 'Not permitted.'}, status=403)
        transition_error = _transition_incident(
            incident,
            'CLOSED',
            request.user,
            event='INCIDENT_CLOSED',
            message=request.data.get('closure_note', ''),
        )
        if transition_error:
            return transition_error
        return Response({'success': True, 'message': 'Incident closed successfully.'})


class IncidentUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsSOSResponder]

    def post(self, request, incident_id):
        incident, error = _response_incident_or_forbidden(request, incident_id)
        if error:
            return error
        requested_status = request.data.get('status')
        if requested_status:
            transition_error = _transition_incident(
                incident,
                requested_status,
                request.user,
                event='RESPONSE_UPDATE',
                message=request.data.get('message', ''),
            )
            if transition_error:
                return transition_error
        else:
            record_history(incident, 'RESPONSE_UPDATE', request.data.get('message', ''), request.user)
        return Response({'success': True, 'data': {'update_id': incident.history.order_by('-id').first().id, 'status': request.data.get('status'), 'message': request.data.get('message', '')}}, status=201)


class AcceptIncidentView(APIView):
    # Guardian acceptance is scoped below to an active guardian relationship;
    # volunteer/security/admin access remains scoped by the response helper.
    permission_classes = [IsAuthenticated]

    def post(self, request, incident_id):
        incident, error = _response_participant_incident_or_forbidden(request, incident_id)
        if error:
            return error
        effective_role, _ = _dashboard_role(request)
        transition_error = _transition_incident(incident, 'ACTIVE_RESPONSE', request.user, event='INCIDENT_ACCEPTED')
        if transition_error:
            return transition_error
        response_obj, _ = SOSResponse.objects.get_or_create(incident=incident, responder=request.user)
        eta = request.data.get('estimated_arrival_minutes')
        try:
            eta = max(1, int(eta)) if eta not in (None, '') else None
        except (TypeError, ValueError):
            eta = None
        response_message = str(request.data.get('response_message') or '').strip()
        response_obj.response_message = response_message or (f"ETA: {eta} minutes" if eta not in (None, '') else 'Responder accepted the incident.')
        response_obj.estimated_arrival_minutes = eta
        response_obj.responder_role = effective_role
        response_obj.save(update_fields=['response_message', 'estimated_arrival_minutes', 'responder_role'])
        if response_message:
            IncidentHistory.objects.filter(
                incident=incident,
                event='INCIDENT_ACCEPTED',
            ).order_by('-id').update(message=response_obj.response_message)
        return Response({'success': True, 'message': 'Incident accepted.', 'data': {'incident_id': incident.id, 'responder_id': request.user.id, 'status': 'active_response', 'estimated_arrival_minutes': eta, 'response_message': response_obj.response_message}})


class RejectIncidentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, incident_id):
        incident, error = _response_participant_incident_or_forbidden(request, incident_id)
        if error:
            return error
        record_history(incident, 'INCIDENT_REJECTED', request.data.get('reason', ''), request.user)
        return Response({'success': True, 'message': 'Incident rejected.'})


class GuardianIncidentListView(APIView):
    permission_classes = [IsAuthenticated, IsGuardian]

    def get(self, request):
        relationships = GuardianRelationship.objects.filter(guardian=request.user, is_active=True).values_list('resident_id', flat=True)
        incidents = SOSIncident.objects.filter(user_id__in=relationships).order_by('-created_at')
        return Response({'success': True, 'data': SOSIncidentSerializer(incidents, many=True).data})


class GuardianRelationshipView(APIView):
    permission_classes = [IsAuthenticated, IsGuardianRelationshipParticipant]

    def get(self, request):
        role = _role(request.user)
        relationships = GuardianRelationship.objects.select_related('resident', 'guardian').order_by('id')
        if role == 'RESIDENT':
            relationships = relationships.filter(resident=request.user)
        elif role == 'GUARDIAN':
            relationships = relationships.filter(guardian=request.user)
        elif role in SOCIETY_ADMIN_ROLES:
            society_id = getattr(getattr(request.user, 'userprofile', None), 'society_id', None)
            relationships = relationships.filter(resident__userprofile__society_id=society_id)
        return Response({'success': True, 'data': [self._serialize(item) for item in relationships]})

    def post(self, request):
        role = _role(request.user)
        guardian_id = request.data.get('guardian_id')
        resident_id = request.data.get('resident_id')
        relationship_type = str(request.data.get('relationship_type', '')).strip().upper()
        if relationship_type not in {'PRIMARY', 'SECONDARY', 'EMERGENCY'}:
            return Response({'success': False, 'message': 'relationship_type must be PRIMARY, SECONDARY, or EMERGENCY.'}, status=400)
        if not guardian_id:
            return Response({'success': False, 'message': 'guardian_id is required.'}, status=400)
        if role == 'RESIDENT':
            resident = request.user
        elif resident_id:
            resident = get_object_or_404(User, id=resident_id)
        else:
            return Response({'success': False, 'message': 'resident_id is required for administrator requests.'}, status=400)

        guardian = get_object_or_404(User, id=guardian_id)
        if _role(resident) != 'RESIDENT' or _role(guardian) != 'GUARDIAN':
            return Response({'success': False, 'message': 'resident_id must belong to a resident and guardian_id must belong to a guardian.'}, status=400)
        if role in SOCIETY_ADMIN_ROLES:
            requester_society = getattr(getattr(request.user, 'userprofile', None), 'society_id', None)
            if requester_society is None or getattr(getattr(resident, 'userprofile', None), 'society_id', None) != requester_society:
                return Response({'success': False, 'message': 'Resident is outside your society.'}, status=403)

        relationship, created = GuardianRelationship.objects.update_or_create(
            resident=resident,
            guardian=guardian,
            relationship_type=relationship_type,
            defaults={'is_active': bool(request.data.get('is_active', True))},
        )
        return Response({'success': True, 'message': 'Guardian relationship created.' if created else 'Guardian relationship updated.', 'data': self._serialize(relationship)}, status=201 if created else 200)

    @staticmethod
    def _serialize(relationship):
        return {
            'id': relationship.id,
            'resident_id': relationship.resident_id,
            'guardian_id': relationship.guardian_id,
            'relationship_type': relationship.relationship_type,
            'is_active': relationship.is_active,
            'created_at': relationship.created_at,
        }


class NotifyPrimaryGuardianView(APIView):
    permission_classes = [IsAuthenticated, IsGuardianWorkflowManager]

    def post(self, request, incident_id):
        incident = get_object_or_404(SOSIncident, id=incident_id)
        role = _role(request.user)
        if role == 'RESIDENT' and incident.user_id != request.user.id:
            return Response({'success': False, 'message': 'Only the incident owner may notify its guardian.'}, status=403)
        if role in SOCIETY_ADMIN_ROLES and not _same_society(request.user, incident):
            return Response({'success': False, 'message': 'This incident is outside your society.'}, status=403)
        escalation = notify_primary_guardian(incident)
        if escalation is None:
            return Response({'success': False, 'message': 'No active PRIMARY guardian relationship is configured for this resident.'}, status=404)
        return Response({'success': True, 'message': 'Primary guardian notification created.', 'data': {
            'incident_id': incident.id,
            'guardian_id': escalation.guardian_id,
            'level': escalation.level,
            'status': escalation.status,
        }})


class NearbyIncidentView(APIView):
    permission_classes = [IsAuthenticated, IsResponder]

    def get(self, request):
        profile = request.user.userprofile
        latitude_value = request.query_params.get('latitude')
        longitude_value = request.query_params.get('longitude')
        radius_value = request.query_params.get('radius_km', 5)
        if latitude_value in (None, '') or _is_unresolved_variable(latitude_value):
            latitude_value = profile.latitude
        if longitude_value in (None, '') or _is_unresolved_variable(longitude_value):
            longitude_value = profile.longitude
        if radius_value in (None, '') or _is_unresolved_variable(radius_value):
            radius_value = 5
        if latitude_value in (None, '') or longitude_value in (None, ''):
            return Response({
                'success': False,
                'message': 'latitude and longitude are required, or share responder location first.',
            }, status=400)

        try:
            latitude = float(latitude_value)
            longitude = float(longitude_value)
            radius_km = float(radius_value)
        except (TypeError, ValueError):
            return Response({'success': False, 'message': 'latitude, longitude, and radius_km must be numeric.'}, status=400)
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            return Response({'success': False, 'message': 'Invalid latitude or longitude.'}, status=400)
        if radius_km <= 0 or radius_km > 100:
            return Response({'success': False, 'message': 'radius_km must be greater than 0 and no more than 100.'}, status=400)

        incidents = SOSIncident.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
        ).exclude(status__in={'CANCELLED', 'CLOSED'}).select_related('category', 'user')

        role = _role(request.user)
        if role == 'GUARDIAN':
            resident_ids = GuardianRelationship.objects.filter(
                guardian=request.user,
                is_active=True,
            ).values_list('resident_id', flat=True)
            incidents = incidents.filter(user_id__in=resident_ids)
        elif role in {'VOLUNTEER', 'SECURITY'}:
            society_id = getattr(profile, 'society_id', None)
            if society_id is None:
                incidents = incidents.none()
            else:
                incidents = incidents.filter(user__userprofile__society_id=society_id)

        earth_radius_km = 6371.0
        nearby = []
        for incident in incidents.order_by('-created_at'):
            incident_latitude = float(incident.latitude)
            incident_longitude = float(incident.longitude)
            delta_latitude = radians(incident_latitude - latitude)
            delta_longitude = radians(incident_longitude - longitude)
            haversine = (
                sin(delta_latitude / 2) ** 2
                + cos(radians(latitude))
                * cos(radians(incident_latitude))
                * sin(delta_longitude / 2) ** 2
            )
            distance_km = earth_radius_km * 2 * asin(sqrt(haversine))
            if distance_km <= radius_km:
                nearby.append({
                    'id': incident.id,
                    'incident_id': f'INC-{incident.created_at:%Y%m%d}-{incident.id:06d}',
                    'category': incident.category.code,
                    'category_name': incident.category.name,
                    'status': incident.status.lower(),
                    'message': incident.message,
                    'distance_km': round(distance_km, 3),
                    'location': {
                        'latitude': incident.latitude,
                        'longitude': incident.longitude,
                        'accuracy': incident.accuracy,
                        'google_maps_url': _google_maps_url(incident.latitude, incident.longitude),
                    },
                    'created_at': incident.created_at,
                })

        return Response({
            'success': True,
            'data': nearby,
            'count': len(nearby),
            'search': {
                'latitude': latitude,
                'longitude': longitude,
                'radius_km': radius_km,
                'google_maps_url': _google_maps_url(latitude, longitude),
            },
        })


class SharedLocationView(APIView):
    """Return the live SOS location and the response participants' routes."""

    permission_classes = [IsAuthenticated]

    def get(self, request, incident_id):
        incident, error = _incident_or_forbidden(request, incident_id)
        if error:
            return error

        owner_profile = getattr(incident.user, 'userprofile', None)
        resident_latitude = incident.latitude if incident.latitude is not None else getattr(owner_profile, 'latitude', None)
        resident_longitude = incident.longitude if incident.longitude is not None else getattr(owner_profile, 'longitude', None)
        resident_accuracy = incident.accuracy if incident.accuracy is not None else getattr(owner_profile, 'accuracy', None)
        incident_location = None
        if resident_latitude is not None and resident_longitude is not None:
            incident_location = {
                'latitude': float(resident_latitude),
                'longitude': float(resident_longitude),
                'accuracy': resident_accuracy,
                'google_maps_url': _google_maps_url(resident_latitude, resident_longitude),
            }

        guardian_ids = GuardianRelationship.objects.filter(
            resident=incident.user,
            is_active=True,
        ).values_list('guardian_id', flat=True)
        responder_filter = Q(role__in=['VOLUNTEER', 'SECURITY'])
        if owner_profile and (owner_profile.society_id or owner_profile.society_name):
            society_filter = Q(society_id=owner_profile.society_id) if owner_profile.society_id else Q(society_name=owner_profile.society_name)
            responder_filter &= society_filter

        primary_guardian_id = GuardianRelationship.objects.filter(
            resident=incident.user,
            relationship_type='PRIMARY',
            is_active=True,
        ).values_list('guardian_id', flat=True).first()

        accepted_responses = {}
        for response in SOSResponse.objects.filter(incident=incident).order_by('-created_at'):
            accepted_responses.setdefault(response.responder_id, response)

        profiles = UserProfile.objects.filter(
            Q(user_id__in=guardian_ids) | responder_filter | Q(user_id__in=accepted_responses.keys()),
        ).select_related('user').distinct()

        speed_by_role = {'GUARDIAN': 25.0, 'VOLUNTEER': 30.0, 'SECURITY': 35.0}
        participants = []
        for profile in profiles:
            response = accepted_responses.get(profile.user_id)
            # A responder's location is shared only after that responder has
            # explicitly accepted this incident. Before acceptance the map
            # exposes no responder coordinates.
            if response is None:
                continue
            participant = {
                'id': profile.user_id,
                'username': profile.user.username,
                'role': ((response.responder_role if response else None) or profile.role).lower(),
                'is_primary_guardian': profile.user_id == primary_guardian_id,
                'accepted': response is not None,
                'accepted_eta_minutes': response.estimated_arrival_minutes if response else None,
                'response_message': response.response_message if response else None,
                'latitude': float(profile.latitude) if profile.latitude is not None else None,
                'longitude': float(profile.longitude) if profile.longitude is not None else None,
                'accuracy': profile.accuracy,
                'distance_km': None,
                'estimated_arrival_minutes': None,
                'route_url': None,
                'location_available': profile.latitude is not None and profile.longitude is not None,
            }
            if incident_location and participant['location_available']:
                delta_latitude = radians(participant['latitude'] - incident_location['latitude'])
                delta_longitude = radians(participant['longitude'] - incident_location['longitude'])
                haversine = (
                    sin(delta_latitude / 2) ** 2
                    + cos(radians(incident_location['latitude']))
                    * cos(radians(participant['latitude']))
                    * sin(delta_longitude / 2) ** 2
                )
                straight_line_km = 6371.0 * 2 * asin(sqrt(haversine))
                distance_km = straight_line_km * 1.35
                speed_kmh = speed_by_role.get(((response.responder_role if response else None) or profile.role).upper(), 25.0)
                participant['distance_km'] = round(distance_km, 2)
                participant['estimated_arrival_minutes'] = max(1, round(distance_km / speed_kmh * 60))
                participant['route_url'] = (
                    'https://www.google.com/maps/dir/?api=1'
                    f"&origin={participant['latitude']},{participant['longitude']}"
                    f"&destination={incident_location['latitude']},{incident_location['longitude']}"
                    '&travelmode=driving'
                )
            if response and response.estimated_arrival_minutes is not None:
                participant['estimated_arrival_minutes'] = response.estimated_arrival_minutes
            participants.append(participant)

        return Response({
            'success': True,
            'data': {
                'incident_id': incident.id,
                'incident_status': incident.status.lower(),
                'resident': {
                    'id': incident.user_id,
                    'username': incident.user.username,
                },
                'location': incident_location,
                'participants': participants,
                'shared_with_count': profiles.count(),
                'accepted_count': sum(1 for participant in participants if participant['accepted']),
                'updated_at': incident.updated_at,
            },
        })


class SOSNotificationListView(APIView):
    permission_classes = [IsAuthenticated, IsResidentOrIncidentAdministrator]

    def get(self, request, incident_id):
        incident, error = _incident_or_forbidden(request, incident_id)
        if error:
            return error
        return Response({'success': True, 'data': SOSNotificationSerializer(incident.notifications.all(), many=True).data})


class SOSResponseView(AcceptIncidentView):
    """Compatibility alias for the former /respond/ endpoint."""


class GuardianResponseView(APIView):
    permission_classes = [IsAuthenticated, IsGuardianResponseParticipant]

    def post(self, request, incident_id):
        role = _role(request.user)
        incident = SOSIncident.objects.filter(id=incident_id).first()
        if incident is None:
            return Response(
                {'success': False, 'message': 'SOS incident not found.', 'incident_id': incident_id},
                status=status.HTTP_404_NOT_FOUND,
            )

        escalations = GuardianEscalation.objects.filter(
            incident=incident,
            status='NOTIFIED',
        ).select_related('incident', 'guardian')
        if role == 'GUARDIAN':
            escalation = escalations.filter(guardian=request.user).order_by('level', 'id').first()
            if escalation is None:
                return Response(
                    {
                        'success': False,
                        'message': (
                            'No pending guardian escalation exists for this guardian. '
                            'Configure an active PRIMARY guardian relationship and notify '
                            'the guardian before responding.'
                        ),
                        'incident_id': incident.id,
                        'guardian_id': request.user.id,
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            escalation = escalations.order_by('level', 'id').first()
            if escalation is None:
                return Response(
                    {
                        'success': False,
                        'message': (
                            'No pending guardian escalation found. Configure an active '
                            'PRIMARY guardian relationship and notify the primary guardian first.'
                        ),
                        'incident_id': incident.id,
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            if role in SOCIETY_ADMIN_ROLES and not _same_society(request.user, escalation.incident):
                return Response({'success': False, 'message': 'This incident is outside your society.'}, status=403)

        escalation.status = 'RESPONDED'
        escalation.responded_at = timezone.now()
        escalation.save(update_fields=['status', 'responded_at'])
        escalation.incident.status = 'RESPONSE_RECEIVED'
        escalation.incident.save(update_fields=['status', 'updated_at'])
        response_message = str(request.data.get('response_message') or 'Guardian accepted the alert.').strip()
        eta = request.data.get('estimated_arrival_minutes')
        try:
            eta = max(1, int(eta)) if eta not in (None, '') else None
        except (TypeError, ValueError):
            eta = None
        response_obj, _ = SOSResponse.objects.get_or_create(incident=incident, responder=request.user)
        response_obj.response_message = response_message
        response_obj.estimated_arrival_minutes = eta
        response_obj.responder_role = 'GUARDIAN'
        response_obj.save(update_fields=['response_message', 'estimated_arrival_minutes', 'responder_role'])
        record_history(escalation.incident, 'GUARDIAN_RESPONDED', response_message, request.user)
        return Response({'success': True, 'message': 'Guardian response recorded successfully.', 'data': {
            'incident_id': incident_id,
            'guardian_id': escalation.guardian_id,
            'responded_by': request.user.id,
            'status': 'RESPONDED',
            'response_message': response_message,
            'estimated_arrival_minutes': eta,
        }})


class GuardianEscalateView(APIView):
    permission_classes = [IsAuthenticated, IsResident]

    def post(self, request, incident_id):
        incident = get_object_or_404(SOSIncident, id=incident_id)
        if incident.user_id != request.user.id:
            return Response(
                {'success': False, 'message': 'Only the incident owner may escalate it.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            level = int(request.data.get('level'))
            result = escalate_to_secondary_guardian(incident) if level == 2 else escalate_to_emergency_contact(incident) if level == 3 else None
        except ValueError as exc:
            return Response({'success': False, 'message': str(exc)}, status=409)
        if not result:
            return Response({'success': False, 'message': 'No matching escalation recipient found.'}, status=404)
        record_history(incident, f'ESCALATED_LEVEL_{level}', 'Manual escalation requested.', request.user)
        recipients = result if isinstance(result, list) else [result]
        return Response({'success': True, 'message': 'Incident escalated.', 'data': {
            'incident_id': incident.id,
            'escalation_level': level,
            'count': len(recipients),
            'guardian_id': recipients[0].guardian_id,
        }})


class EscalationConfigView(APIView):
    permission_classes = [IsAuthenticated, IsIncidentAdministrator]

    def _allowed(self, request):
        return _role(request.user) in ADMIN_ROLES

    def get(self, request):
        if not self._allowed(request):
            return Response({'success': False, 'message': 'Administrator permission required.'}, status=403)
        config, _ = EscalationConfiguration.objects.get_or_create(pk=1)
        return Response({'success': True, 'data': {
            'response_timeout_seconds': config.response_timeout_seconds,
            'primary_guardian_enabled': config.primary_guardian_enabled,
            'secondary_guardian_enabled': config.secondary_guardian_enabled,
            'emergency_contact_enabled': config.emergency_contact_enabled,
            'security_enabled': config.security_enabled,
            'volunteer_enabled': config.volunteer_enabled,
        }})

    def patch(self, request):
        if not self._allowed(request):
            return Response({'success': False, 'message': 'Administrator permission required.'}, status=403)
        config, _ = EscalationConfiguration.objects.get_or_create(pk=1)
        for field in ('response_timeout_seconds', 'primary_guardian_enabled', 'secondary_guardian_enabled', 'emergency_contact_enabled', 'security_enabled', 'volunteer_enabled'):
            if field in request.data:
                setattr(config, field, request.data[field])
        config.save()
        return Response({'success': True, 'message': 'Escalation configuration updated.'})


class ManualEscalateView(GuardianEscalateView):
    permission_classes = [IsAuthenticated, IsIncidentAdministrator]

    def post(self, request, incident_id):
        if _role(request.user) not in ADMIN_ROLES:
            return Response({'success': False, 'message': 'Administrator permission required.'}, status=403)
        incident = get_object_or_404(SOSIncident, id=incident_id)
        level = int(request.data.get('level', 2))
        result = escalate_to_secondary_guardian(incident) if level == 2 else escalate_to_emergency_contact(incident)
        if not result:
            return Response({'success': False, 'message': 'No matching escalation recipient found.'}, status=404)
        record_history(incident, 'MANUAL_ESCALATION', request.data.get('reason', ''), request.user)
        return Response({'success': True, 'message': 'Incident escalated.', 'data': {'incident_id': incident.id, 'escalation_level': level}})


class SOSIncidentHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, incident_id):
        incident, error = _incident_or_forbidden(request, incident_id)
        if error:
            return error
        history = incident.history.select_related('actor').all()
        return Response({'success': True, 'data': [{'id': e.id, 'action': e.event.lower(), 'event': e.event, 'message': e.message, 'performed_by': e.actor_id, 'timestamp': e.created_at} for e in history]})
