from django.utils import timezone

from .models import (
    GuardianRelationship,
    GuardianEscalation,
    IncidentHistory,
)
from notifications.services import create_notification


def _location_suffix(incident):
    if incident.latitude is None or incident.longitude is None:
        return ' Location sharing is unavailable until the resident shares device location.'
    return f' Location: https://www.google.com/maps/search/?api=1&query={incident.latitude},{incident.longitude}'


def record_history(incident, event, message='', actor=None):
    return IncidentHistory.objects.create(
        incident=incident,
        actor=actor,
        event=event,
        message=message,
    )


def _notify_relationship(incident, relationship, level, message, event):
    """Create one escalation per incident/guardian/level and notify only once."""
    escalation, created = GuardianEscalation.objects.get_or_create(
        incident=incident,
        guardian=relationship.guardian,
        level=level,
        defaults={
            'status': 'NOTIFIED',
            'notified_at': timezone.now(),
        },
    )
    if created:
        create_notification(
            relationship.guardian,
            'Emergency Alert',
            message,
            'SOS',
        )
        record_history(incident, event, message)
    return escalation, created


def _mark_previous_level_no_response(incident, level):
    GuardianEscalation.objects.filter(
        incident=incident,
        level=level,
        status__in=['PENDING', 'NOTIFIED'],
    ).update(status='NO_RESPONSE')


def _has_response(incident):
    return incident.guardian_escalations.filter(status='RESPONDED').exists()


def notify_primary_guardian(incident):
    relationship = GuardianRelationship.objects.filter(
        resident=incident.user,
        relationship_type='PRIMARY',
        is_active=True,
    ).order_by('created_at', 'id').first()

    if not relationship:
        record_history(
            incident,
            'PRIMARY_GUARDIAN_MISSING',
            'No active primary guardian is configured.',
        )
        return None

    escalation, _ = _notify_relationship(
        incident,
        relationship,
        1,
        f'SOS incident #{incident.id} requires your attention.{_location_suffix(incident)}',
        'PRIMARY_GUARDIAN_NOTIFIED',
    )
    return escalation


def escalate_to_secondary_guardian(incident):
    if _has_response(incident):
        raise ValueError('An escalation has already been responded to.')

    relationship = GuardianRelationship.objects.filter(
        resident=incident.user,
        relationship_type='SECONDARY',
        is_active=True,
    ).order_by('created_at', 'id').first()
    if not relationship:
        return None

    _mark_previous_level_no_response(incident, 1)
    escalation, created = _notify_relationship(
        incident,
        relationship,
        2,
        f'SOS incident #{incident.id} has been escalated to you.{_location_suffix(incident)}',
        'SECONDARY_GUARDIAN_NOTIFIED',
    )
    if created:
        incident.status = 'ESCALATED'
        incident.save(update_fields=['status', 'updated_at'])
    return escalation


def escalate_to_emergency_contact(incident):
    if _has_response(incident):
        raise ValueError('An escalation has already been responded to.')

    relationships = GuardianRelationship.objects.filter(
        resident=incident.user,
        relationship_type='EMERGENCY',
        is_active=True,
    ).order_by('created_at', 'id')
    if not relationships.exists():
        return []

    _mark_previous_level_no_response(incident, 1)
    _mark_previous_level_no_response(incident, 2)
    escalations = []
    created_any = False
    for relationship in relationships:
        escalation, created = _notify_relationship(
            incident,
            relationship,
            3,
            f'URGENT: SOS incident #{incident.id} needs assistance.{_location_suffix(incident)}',
            'EMERGENCY_CONTACT_NOTIFIED',
        )
        escalations.append(escalation)
        created_any = created_any or created

    if created_any:
        incident.status = 'ESCALATED'
        incident.save(update_fields=['status', 'updated_at'])
    return escalations
