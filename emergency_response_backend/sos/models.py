import uuid

from django.db import models
from django.conf import settings


def default_client_message_id():
    return str(uuid.uuid4())


class SOSIncident(models.Model):

    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('NOTIFICATIONS_SENT', 'Notifications Sent'),
        ('RESPONSE_RECEIVED', 'Response Received'),
        ('ACTIVE_RESPONSE', 'Active Response'),
        ('RESOLVED', 'Resolved'),
        ('CANCELLED', 'Cancelled'),
        ('ESCALATED', 'Escalated'),
        ('CLOSED', 'Closed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sos_incidents'
    )

    category = models.ForeignKey(
        'emergency.EmergencyCategory',
        on_delete=models.PROTECT,
        related_name='sos_incidents'
    )

    message = models.TextField(blank=True)

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )

    accuracy = models.FloatField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='OPEN'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SOSNotification(models.Model):

    CHANNEL_CHOICES = [
        ('PUSH', 'Push'),
        ('SMS', 'SMS'),
        ('EMAIL', 'Email'),
        ('IN_APP', 'In App'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('DELIVERED', 'Delivered'),
        ('FAILED', 'Failed'),
    ]

    incident = models.ForeignKey(
        SOSIncident,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sos_notifications'
    )

    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    is_read = models.BooleanField(default=False)

    sent_at = models.DateTimeField(
        null=True,
        blank=True
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)


class SOSResponse(models.Model):

    incident = models.ForeignKey(
        SOSIncident,
        on_delete=models.CASCADE,
        related_name='responses'
    )

    responder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    response_message = models.TextField(
        blank=True
    )

    estimated_arrival_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Responder-provided estimated arrival time in minutes.',
    )

    responder_role = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text='Role used for a local development dashboard preview, when applicable.',
    )

    created_at = models.DateTimeField(auto_now_add=True)

class GuardianRelationship(models.Model):

    RELATIONSHIP_TYPE = [
        ('PRIMARY', 'Primary Guardian'),
        ('SECONDARY', 'Secondary Guardian'),
        ('EMERGENCY', 'Emergency Contact'),
    ]

    resident = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='guardian_relationships'
    )

    guardian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='guardian_for_residents'
    )

    relationship_type = models.CharField(
        max_length=20,
        choices=RELATIONSHIP_TYPE
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.resident_id} -> "
            f"{self.guardian_id} "
            f"({self.relationship_type})"
        )

class GuardianEscalation(models.Model):

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('NOTIFIED', 'Notified'),
        ('RESPONDED', 'Responded'),
        ('NO_RESPONSE', 'No Response'),
        ('ESCALATED', 'Escalated'),
    ]

    incident = models.ForeignKey(
        SOSIncident,
        on_delete=models.CASCADE,
        related_name='guardian_escalations'
    )

    guardian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sos_guardian_alerts'
    )

    level = models.PositiveIntegerField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    notified_at = models.DateTimeField(
        null=True,
        blank=True
    )

    responded_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"SOS {self.incident_id} - "
            f"Guardian {self.guardian_id} - "
            f"Level {self.level}"
        )


class IncidentHistory(models.Model):
    """An append-only audit trail for the guardian escalation workflow."""

    incident = models.ForeignKey(
        SOSIncident,
        on_delete=models.CASCADE,
        related_name='history',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='sos_history_events',
        null=True,
        blank=True,
    )
    event = models.CharField(max_length=50)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f"SOS {self.incident_id}: {self.event}"


class IncidentMessage(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ('TEXT', 'Text'),
        ('VOICE', 'Voice'),
    ]

    incident = models.ForeignKey(
        SOSIncident,
        on_delete=models.CASCADE,
        related_name='chat_messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='incident_messages',
    )
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES, default='TEXT')
    message = models.TextField(blank=True)
    audio_file = models.FileField(
        upload_to='incident_voice_messages/%Y/%m/%d/',
        null=True,
        blank=True,
    )
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f"Incident {self.incident_id}: {self.message_type} by {self.sender_id}"


class OfflineIncidentMessage(models.Model):
    """Client-side messages waiting to be synchronized after reconnecting."""

    SYNC_STATUS_CHOICES = [
        ('QUEUED', 'Queued'),
        ('SYNCED', 'Synced'),
        ('FAILED', 'Failed'),
    ]

    incident = models.ForeignKey(
        SOSIncident,
        on_delete=models.CASCADE,
        related_name='offline_messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='offline_incident_messages',
    )
    client_message_id = models.CharField(max_length=100, unique=True, default=default_client_message_id)
    message_type = models.CharField(max_length=10, choices=IncidentMessage.MESSAGE_TYPE_CHOICES, default='TEXT')
    message = models.TextField(blank=True)
    audio_file = models.FileField(
        upload_to='incident_offline_voice_messages/%Y/%m/%d/',
        null=True,
        blank=True,
    )
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    sync_status = models.CharField(max_length=10, choices=SYNC_STATUS_CHOICES, default='QUEUED')
    sync_attempts = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    synced_message = models.OneToOneField(
        IncidentMessage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='offline_source',
    )
    client_created_at = models.DateTimeField(null=True, blank=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f"Offline message {self.client_message_id} ({self.sync_status})"


class AIKnowledgeGraphSnapshot(models.Model):
    incident = models.ForeignKey(
        SOSIncident,
        on_delete=models.CASCADE,
        related_name='ai_knowledge_graph_snapshots',
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_knowledge_graph_snapshots',
    )
    graph = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']


class AIDigitalTwinSnapshot(models.Model):
    incident = models.ForeignKey(
        SOSIncident,
        on_delete=models.CASCADE,
        related_name='ai_digital_twin_snapshots',
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_digital_twin_snapshots',
    )
    twin = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']


class EscalationConfiguration(models.Model):
    response_timeout_seconds = models.PositiveIntegerField(default=60)
    primary_guardian_enabled = models.BooleanField(default=True)
    secondary_guardian_enabled = models.BooleanField(default=True)
    emergency_contact_enabled = models.BooleanField(default=True)
    security_enabled = models.BooleanField(default=True)
    volunteer_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Escalation configuration'
