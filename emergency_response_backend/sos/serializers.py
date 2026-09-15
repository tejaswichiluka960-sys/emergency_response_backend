from rest_framework import serializers

from .models import (
    SOSIncident,
    SOSNotification,
    SOSResponse
)


class SOSIncidentCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = SOSIncident

        fields = [
            'category',
            'message',
            'latitude',
            'longitude',
            'accuracy'
        ]


class SOSIncidentSerializer(serializers.ModelSerializer):

    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )

    class Meta:
        model = SOSIncident

        fields = [
            'id',
            'category',
            'category_name',
            'message',
            'latitude',
            'longitude',
            'accuracy',
            'status',
            'created_at',
            'updated_at'
        ]


class SOSNotificationSerializer(serializers.ModelSerializer):

    recipient_name = serializers.CharField(
        source='recipient.username',
        read_only=True
    )

    class Meta:
        model = SOSNotification

        fields = [
            'id',
            'recipient',
            'recipient_name',
            'channel',
            'status',
            'sent_at',
            'delivered_at',
            'created_at'
        ]


class SOSResponseSerializer(serializers.ModelSerializer):

    responder_name = serializers.CharField(
        source='responder.username',
        read_only=True
    )

    class Meta:
        model = SOSResponse

        fields = [
            'id',
            'responder',
            'responder_name',
            'response_message',
            'created_at'
        ]