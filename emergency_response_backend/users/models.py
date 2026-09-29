from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.db import models



class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    phone = models.CharField(max_length=15)

    # Resident onboarding details. These are intentionally denormalized so a
    # resident can register before society administrators have created the
    # corresponding society/flat records.
    name = models.CharField(max_length=120, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    society_name = models.CharField(max_length=100, blank=True, default="")
    flat_number = models.CharField(max_length=20, blank=True, default="")

    role = models.CharField(
        max_length=50
    )

    # Assignment fields used by the PDF's society-scoped permissions. They
    # stay nullable so existing accounts continue to work during migration.
    society_id = models.PositiveIntegerField(null=True, blank=True)
    flat_id = models.PositiveIntegerField(null=True, blank=True)

    otp = models.CharField(max_length=6, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    
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

    is_available = models.BooleanField(default=False)

    availability_updated_at = models.DateTimeField(
        null=True,
        blank=True
    )

    location_updated_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return self.user.username
    
    

  
    
