from rest_framework import serializers
from .models import EmergencyContact

from .models import SOSConfiguration



class EmergencyContactSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmergencyContact

        fields = [
            "id",
            "name",
            "email",
            "mobile",
            "relationship",
            "priority",
            "is_verified",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "is_verified",
            "created_at",
            "updated_at",
        ]
        
class SOSConfigurationSerializer(serializers.ModelSerializer):

    class Meta:
        model = SOSConfiguration

        fields = [
            "default_category",
            "response_timeout_seconds",
            "notify_guardians",
            "notify_security",
            "notify_volunteers",
            "community_broadcast",
            "location_sharing",
        ]