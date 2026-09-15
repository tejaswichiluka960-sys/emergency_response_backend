from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):

    NOTIFICATION_TYPES = (
        ('SOS', 'SOS'),
        ('EMAIL', 'EMAIL'),
        ('SMS', 'SMS'),
        ('PUSH', 'PUSH'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES
    )

    title = models.CharField(
        max_length=255
    )

    message = models.TextField()

    is_read = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.title
