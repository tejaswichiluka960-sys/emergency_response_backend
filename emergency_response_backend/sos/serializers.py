from rest_framework import serializers

from emergency.models import EmergencyCategory
from .models import IncidentMessage, SOSIncident, SOSNotification, SOSResponse


class IncidentLocationSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    accuracy = serializers.FloatField(required=False, allow_null=True)


class SOSIncidentCreateSerializer(serializers.Serializer):
    category = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    location = IncidentLocationSerializer(required=False, allow_null=True)
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    accuracy = serializers.FloatField(required=False, allow_null=True)

    def validate(self, attrs):
        category_value = attrs.get('category')
        category = None
        if category_value not in (None, ''):
            query = {'is_active': True}
            if str(category_value).isdigit():
                query['id'] = int(category_value)
            else:
                query['code'] = str(category_value).lower()
            category = EmergencyCategory.objects.filter(**query).first()
            if not category:
                raise serializers.ValidationError({'category': 'Unknown or inactive emergency category.'})
        if category is None:
            category = EmergencyCategory.objects.filter(is_active=True).order_by('id').first()
        if not category:
            raise serializers.ValidationError({'category': 'No active emergency category is configured.'})
        attrs['_category'] = category
        location = attrs.pop('location', None) or {}
        attrs['latitude'] = location.get('latitude', attrs.get('latitude'))
        attrs['longitude'] = location.get('longitude', attrs.get('longitude'))
        attrs['accuracy'] = location.get('accuracy', attrs.get('accuracy'))
        return attrs

    def create(self, validated_data):
        category = validated_data.pop('_category')
        # ``category`` is only the request's lookup value.  The model must
        # receive the resolved EmergencyCategory instance exactly once.
        validated_data.pop('category', None)
        return SOSIncident.objects.create(category=category, **validated_data)


class SOSIncidentSerializer(serializers.ModelSerializer):
    incident_id = serializers.SerializerMethodField()
    category = serializers.CharField(source='category.code', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    location = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = SOSIncident
        fields = ['id', 'incident_id', 'category', 'category_name', 'message', 'location', 'latitude', 'longitude', 'accuracy', 'status', 'created_at', 'updated_at']

    def get_incident_id(self, obj):
        return f'INC-{obj.created_at:%Y%m%d}-{obj.id:06d}'

    def get_location(self, obj):
        return {'latitude': obj.latitude, 'longitude': obj.longitude, 'accuracy': obj.accuracy}

    def get_status(self, obj):
        return str(obj.status).lower()


class SOSNotificationSerializer(serializers.ModelSerializer):
    recipient_name = serializers.CharField(source='recipient.username', read_only=True)

    class Meta:
        model = SOSNotification
        fields = ['id', 'recipient', 'recipient_name', 'channel', 'status', 'is_read', 'sent_at', 'delivered_at', 'created_at']


class SOSResponseSerializer(serializers.ModelSerializer):
    responder_name = serializers.CharField(source='responder.username', read_only=True)

    class Meta:
        model = SOSResponse
        fields = ['id', 'responder', 'responder_name', 'response_message', 'estimated_arrival_minutes', 'responder_role', 'created_at']


class IncidentMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    audio_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = IncidentMessage
        fields = [
            'id',
            'incident',
            'sender',
            'sender_name',
            'message_type',
            'message',
            'audio_url',
            'download_url',
            'duration_seconds',
            'created_at',
        ]
        read_only_fields = ['id', 'incident', 'sender', 'sender_name', 'audio_url', 'created_at']

    def get_audio_url(self, obj):
        if not obj.audio_file:
            return None
        url = obj.audio_file.url
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url

    def get_download_url(self, obj):
        if obj.message_type != 'VOICE' or not obj.audio_file:
            return None
        request = self.context.get('request')
        if not request:
            return None
        from django.urls import reverse
        return request.build_absolute_uri(reverse(
            'incident-message-download',
            kwargs={'incident_id': obj.incident_id, 'message_id': obj.id},
        ))
