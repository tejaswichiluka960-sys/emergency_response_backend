from django.contrib import admin
from .models import (
    AIDigitalTwinSnapshot,
    AIKnowledgeGraphSnapshot,
    GuardianEscalation,
    GuardianRelationship,
    IncidentHistory,
    IncidentMessage,
    OfflineIncidentMessage,
)


@admin.register(GuardianRelationship)
class GuardianRelationshipAdmin(admin.ModelAdmin):
    list_display = ('resident', 'guardian', 'relationship_type', 'is_active')
    list_filter = ('relationship_type', 'is_active')
    search_fields = ('resident__username', 'guardian__username')


@admin.register(GuardianEscalation)
class GuardianEscalationAdmin(admin.ModelAdmin):
    list_display = ('incident', 'guardian', 'level', 'status', 'notified_at', 'responded_at')
    list_filter = ('level', 'status')
    search_fields = ('incident__id', 'guardian__username')


@admin.register(IncidentHistory)
class IncidentHistoryAdmin(admin.ModelAdmin):
    list_display = ('incident', 'event', 'actor', 'created_at')
    list_filter = ('event',)
    search_fields = ('incident__id', 'actor__username', 'message')


@admin.register(IncidentMessage)
class IncidentMessageAdmin(admin.ModelAdmin):
    list_display = ('incident', 'sender', 'message_type', 'duration_seconds', 'created_at')
    list_filter = ('message_type',)
    search_fields = ('incident__id', 'sender__username', 'message')


@admin.register(OfflineIncidentMessage)
class OfflineIncidentMessageAdmin(admin.ModelAdmin):
    list_display = ('incident', 'sender', 'message_type', 'sync_status', 'sync_attempts', 'created_at', 'synced_at')
    list_filter = ('message_type', 'sync_status')
    search_fields = ('client_message_id', 'incident__id', 'sender__username', 'message')


@admin.register(AIKnowledgeGraphSnapshot)
class AIKnowledgeGraphSnapshotAdmin(admin.ModelAdmin):
    list_display = ('incident', 'requested_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('incident__id', 'requested_by__username')


@admin.register(AIDigitalTwinSnapshot)
class AIDigitalTwinSnapshotAdmin(admin.ModelAdmin):
    list_display = ('incident', 'requested_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('incident__id', 'requested_by__username')
