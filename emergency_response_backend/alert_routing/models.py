from django.db import models


class AlertRoute(models.Model):

    RECIPIENT_TYPES = [
        ('GUARDIAN', 'Primary Guardian'),
        ('SECURITY', 'Security Staff'),
        ('VOLUNTEER', 'Volunteer'),
        ('COMMUNITY', 'Community Member'),
    ]

    DELIVERY_STATUS = [
        ('PENDING', 'Pending'),
        ('DELIVERED', 'Delivered'),
        ('FAILED', 'Failed'),
    ]

    RESPONSE_STATUS = [
        ('NO_RESPONSE', 'No Response'),
        ('RESPONDED', 'Responded'),
        ('RESPONDING', 'Responding'),
        ('RESOLVED', 'Resolved'),
    ]

    incident_id = models.IntegerField()

    recipient_id = models.IntegerField()

    recipient_type = models.CharField(
        max_length=20,
        choices=RECIPIENT_TYPES
    )

    priority = models.IntegerField(default=1)

    delivery_status = models.CharField(
        max_length=20,
        choices=DELIVERY_STATUS,
        default='PENDING'
    )

    response_status = models.CharField(
        max_length=20,
        choices=RESPONSE_STATUS,
        default='NO_RESPONSE'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.recipient_type} - Incident {self.incident_id}"