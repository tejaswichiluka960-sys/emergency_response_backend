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

    # Accept both the API codes (for example, ``medical``) and the display
    # labels returned by the model choices (for example, ``Medical``).
    # Normalize all accepted values back to the canonical lowercase code.
    default_category = serializers.CharField(required=False)

    def validate_default_category(self, value):
        choices = dict(SOSConfiguration.CATEGORY_CHOICES)
        normalized = str(value).strip().casefold()

        for code, label in choices.items():
            if normalized in {code.casefold(), label.casefold()}:
                return code

        valid_values = ", ".join(choices.keys())
        raise serializers.ValidationError(
            f"Invalid category. Use one of: {valid_values}."
        )

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
