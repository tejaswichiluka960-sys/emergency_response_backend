from rest_framework import serializers
from urllib.parse import urlencode
from .models import UserProfile

class LocationSerializer(serializers.ModelSerializer):
    google_maps_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "latitude",
            "longitude",
            "accuracy",
            "location_updated_at",
            "google_maps_url",
        ]
        read_only_fields = ["location_updated_at", "google_maps_url"]

    def validate(self, attrs):
        latitude = attrs.get("latitude", getattr(self.instance, "latitude", None))
        longitude = attrs.get("longitude", getattr(self.instance, "longitude", None))
        if latitude is not None and not -90 <= float(latitude) <= 90:
            raise serializers.ValidationError({"latitude": "Must be between -90 and 90."})
        if longitude is not None and not -180 <= float(longitude) <= 180:
            raise serializers.ValidationError({"longitude": "Must be between -180 and 180."})
        return attrs

    def get_google_maps_url(self, obj):
        if obj.latitude is None or obj.longitude is None:
            return None
        query = urlencode({"api": "1", "query": f"{obj.latitude},{obj.longitude}"})
        return f"https://www.google.com/maps/search/?{query}"
