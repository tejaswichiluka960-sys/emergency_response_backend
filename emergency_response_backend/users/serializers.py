from rest_framework import serializers
from .models import UserProfile

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "latitude",
            "longitude",
            "accuracy"
        ]