from django.conf import settings
from django.db import models


class EmergencyRequest(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def _str_(self):
        return self.title
    
class EmergencyContact(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergency_contacts"
    )

    name = models.CharField(max_length=100)

    email = models.EmailField()

    mobile = models.CharField(max_length=20)

    relationship = models.CharField(max_length=50)

    priority = models.PositiveIntegerField(default=1)

    is_verified = models.BooleanField(default=False)

    otp = models.CharField(
        max_length=6,
        blank=True,
        null=True
    )

    otp_expiry = models.DateTimeField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.name} - {self.mobile}"
    
class SOSConfiguration(models.Model):
    CATEGORY_CHOICES = [
        ("medical", "Medical"),
        ("security", "Security"),
        ("fire", "Fire"),
        ("accident", "Accident"),
        ("other", "Other"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sos_configuration"
    )

    default_category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="medical"
    )

    response_timeout_seconds = models.IntegerField(
        default=60
    )

    notify_guardians = models.BooleanField(
        default=True
    )

    notify_security = models.BooleanField(
        default=True
    )

    notify_volunteers = models.BooleanField(
        default=True
    )

    community_broadcast = models.BooleanField(
        default=True
    )

    location_sharing = models.BooleanField(
        default=True
    )

    def __str__(self):
        return f"SOS Configuration - {self.user}"   
    
class EmergencyCategory(models.Model):

    code = models.CharField(
        max_length=50,
        unique=True
    )

    name = models.CharField(
        max_length=100
    )

    icon = models.CharField(
        max_length=100,
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name     


