from django.db import models
from django.conf import settings


class SOSIncident(models.Model):

    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('NOTIFICATIONS_SENT', 'Notifications Sent'),
        ('RESPONSE_RECEIVED', 'Response Received'),
        ('RESOLVED', 'Resolved'),
        ('CANCELLED', 'Cancelled'),
        ('ESCALATED', 'Escalated'),
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

    created_at = models.DateTimeField(auto_now_add=True)
