from django.urls import path

from .views import (
    CreateSOSIncidentView,
    SOSIncidentListView,
    SOSIncidentDetailView,
    SOSIncidentStatusView,
    SOSNotificationListView,
    SOSResponseView,
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
        'incidents/<int:incident_id>/respond/',
        SOSResponseView.as_view(),
        name='sos-respond'
    ),
]