from rest_framework import serializers
from .models import AlertRoute


class AlertRouteSerializer(serializers.ModelSerializer):

    class Meta:
        model = AlertRoute
        fields = '__all__'