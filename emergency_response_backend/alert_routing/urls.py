from django.urls import path
from .views import AlertRoutingView
from .views import  AlertRoutingListView
from .views import AlertMonitoringView
from .views import  UpdateDeliveryStatusView
from .views import  UpdateResponseStatusView
urlpatterns = [
    path(
        'route-alert/',
        AlertRoutingView.as_view(),
        name='route-alert'
    ),
     

    path(
        'routes/',
        AlertRoutingListView.as_view(),
        name='routes'
    ),
    
     # Alert Monitoring
    path(
        'monitor/',
        AlertMonitoringView.as_view(),
        name='alert-monitor'
    ),

    # Update notification delivery
    path(
        'routes/<int:route_id>/delivery/',
        UpdateDeliveryStatusView.as_view(),
        name='update-delivery'
    ),

    # Update response
    path(
        'routes/<int:route_id>/response/',
        UpdateResponseStatusView.as_view(),
        name='update-response'
    ),
]