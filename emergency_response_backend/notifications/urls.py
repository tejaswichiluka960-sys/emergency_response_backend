from django.urls import path
from .views import MyNotificationsView
from .views import MarkNotificationReadView
from .views import NotificationCountView
from .views import SendSMSView
from .views import SendEmailView
from .views import  SendNotificationView
urlpatterns = [
    path(
        '',
        MyNotificationsView.as_view(),
        name='notifications'
        
    ),
    path(
    '<int:notification_id>/read/',
    MarkNotificationReadView.as_view(),
    name='mark-read'
    ),
    path(
    'count/',
    NotificationCountView.as_view(),
    name='notification-count'
),
    path(
    'send-sms/',
    SendSMSView.as_view(),
    name='send-sms'
),
    path(
    'send-email/',
    SendEmailView.as_view(),
    name='send-email'
),
    path('send-push/', SendNotificationView.as_view(), name='send-push'),
]