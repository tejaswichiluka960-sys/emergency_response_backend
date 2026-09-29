from django.urls import path
from .views import GuardianResponseView
from .views import GuardianEscalateView
from .views import SOSIncidentHistoryView
from .views import (
    CreateSOSIncidentView,
    SOSIncidentListView,
    SOSIncidentDetailView,
    SOSIncidentStatusView,
    SOSNotificationListView,
    SOSResponseView,
    CancelIncidentView,
    ResolveIncidentView,
    CloseIncidentView,
    IncidentUpdateView,
    AcceptIncidentView,
    RejectIncidentView,
    GuardianIncidentListView,
    EscalationConfigView,
    ManualEscalateView,
    NearbyIncidentView,
    SharedLocationView,
    GuardianRelationshipView,
    NotifyPrimaryGuardianView,
    IncidentChatView,
    IncidentChatMessagesView,
    IncidentMessageDownloadView,
    OfflineMessageQueueView,
    OfflineMessageSyncView,
    AIKnowledgeGraphView,
    AIDigitalTwinView,
)


urlpatterns = [

    path(
        'incidents/',
        CreateSOSIncidentView.as_view(),
        name='create-sos'
    ),

    path(
        'incidents/my/',
        SOSIncidentListView.as_view(),
        name='my-sos'
    ),

    path(
        'incidents/<int:incident_id>/shared-location/',
        SharedLocationView.as_view(),
        name='shared-incident-location',
    ),

    path(
        'incidents/<int:incident_id>/',
        SOSIncidentDetailView.as_view(),
        name='sos-detail'
    ),

    path(
        'incidents/<int:incident_id>/status/',
        SOSIncidentStatusView.as_view(),
        name='sos-status'
    ),

    path(
        'incidents/<int:incident_id>/notifications/',
        SOSNotificationListView.as_view(),
        name='sos-notifications'
    ),

    path(
        'incidents/<int:incident_id>/chat/',
        IncidentChatView.as_view(),
        name='incident-chat',
    ),

    path(
        'incidents/<int:incident_id>/chat/messages/',
        IncidentChatMessagesView.as_view(),
        name='incident-chat-messages',
    ),

    path(
        'incidents/<int:incident_id>/chat/messages/<int:message_id>/download/',
        IncidentMessageDownloadView.as_view(),
        name='incident-message-download',
    ),

    path(
        'incidents/<int:incident_id>/chat/offline/',
        OfflineMessageQueueView.as_view(),
        name='offline-message-queue',
    ),
    path(
        'incidents/<int:incident_id>/chat/offline/sync/',
        OfflineMessageSyncView.as_view(),
        name='offline-message-sync',
    ),

    path(
        'incidents/<int:incident_id>/ai/knowledge-graph/',
        AIKnowledgeGraphView.as_view(),
        name='ai-knowledge-graph',
    ),
    path(
        'incidents/<int:incident_id>/ai/digital-twin/',
        AIDigitalTwinView.as_view(),
        name='ai-digital-twin',
    ),

    path(
        'responders/incidents/nearby/',
        NearbyIncidentView.as_view(),
        name='nearby-incidents',
    ),

    path(
        'incidents/<int:incident_id>/respond/',
        SOSResponseView.as_view(),
        name='sos-respond'
    ),

    path(
        'incidents/<int:incident_id>/guardian/respond/',
        GuardianResponseView.as_view()
    ),
    path(
        'guardians/relationships/',
        GuardianRelationshipView.as_view(),
        name='guardian-relationships',
    ),
    path(
        'incidents/<int:incident_id>/guardian/notify/',
        NotifyPrimaryGuardianView.as_view(),
        name='notify-primary-guardian',
    ),
    path(
    'incidents/<int:incident_id>/guardian/escalate/',
    GuardianEscalateView.as_view()
),
    path(
        'incidents/<int:incident_id>/history/',
        SOSIncidentHistoryView.as_view(),
        name='sos-history',
    ),
    path('incidents/sos/', CreateSOSIncidentView.as_view(), name='trigger-sos'),
    path('incidents/<int:incident_id>/cancel/', CancelIncidentView.as_view(), name='cancel-incident'),
    path('incidents/<int:incident_id>/resolve/', ResolveIncidentView.as_view(), name='resolve-incident'),
    path('incidents/<int:incident_id>/close/', CloseIncidentView.as_view(), name='close-incident'),
    path('incidents/<int:incident_id>/updates/', IncidentUpdateView.as_view(), name='incident-update'),
    path('incidents/<int:incident_id>/accept/', AcceptIncidentView.as_view(), name='accept-incident'),
    path('incidents/<int:incident_id>/reject/', RejectIncidentView.as_view(), name='reject-incident'),
    path('guardian/incidents/', GuardianIncidentListView.as_view(), name='guardian-incidents'),
    path('escalation/config/', EscalationConfigView.as_view(), name='escalation-config'),
    path('incidents/<int:incident_id>/escalate/', ManualEscalateView.as_view(), name='manual-escalation'),
]
