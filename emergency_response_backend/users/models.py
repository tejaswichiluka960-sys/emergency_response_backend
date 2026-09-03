from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.db import models



class UserProfile(models.Model):

    ROLE_CHOICES = (
    ("ADMIN", "ADMIN"),
    ("SUB_ADMIN", "SUB_ADMIN"),
    ("SECURITY", "SECURITY"),
    ("RESIDENT", "RESIDENT"),
    ("VOLUNTEER", "VOLUNTEER"),
    ("GUARDIAN", "GUARDIAN"),
)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    phone = models.CharField(max_length=15)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='GUARDIAN'
    )
    otp = models.CharField(max_length=6, null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username
    
