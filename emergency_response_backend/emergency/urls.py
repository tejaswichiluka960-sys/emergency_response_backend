from django.urls import path
from .views import SOSConfigurationView

from .views import (
    EmergencyContactListCreateView,
    EmergencyContactDetailView,
    EmergencyContactSendOTPView,
    EmergencyContactVerifyView,
)


urlpatterns = [

    # Add / List Emergency Contacts
    path(
        "api/v1/users/me/emergency-contacts/",
        EmergencyContactListCreateView.as_view(),
    ),

    # Update / Delete Emergency Contact
    path(
        "api/v1/emergency-contacts/<int:contact_id>/",
        EmergencyContactDetailView.as_view(),
    ),

    # Send OTP
    path(
        "api/v1/emergency-contacts/<int:contact_id>/send-otp/",
        EmergencyContactSendOTPView.as_view(),
    ),

    # Verify OTP
    path(
        "api/v1/emergency-contacts/<int:contact_id>/verify/",
        EmergencyContactVerifyView.as_view(),
    ),
    
    path(
        "users/me/sos-config/",
        SOSConfigurationView.as_view(),
        name="sos-configuration"
    ),
]

from django.urls import path

from .views import EmergencyCategoryListView
from .views import SendSosSMSView



urlpatterns = [

    path(
        'emergency-categories/',
        EmergencyCategoryListView.as_view(),
        name='emergency-category-list'
    ),
    
     

    path(
        'send-sos-sms/',
        SendSosSMSView.as_view(),
        name='send_sos_sms'
    ),
]