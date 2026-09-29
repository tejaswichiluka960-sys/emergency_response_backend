from django.urls import path

from .views import (
    EmergencyContactListCreateView,
    EmergencyContactDetailView,
    EmergencyContactSendOTPView,
    EmergencyContactVerifyView,
    SOSConfigurationView,
    EmergencyCategoryListView,
    SendSosSMSView,
    EmergencyCategoryDetailView,
)

urlpatterns = [
    # Twilio SOS SMS endpoint
    # Accessible via /api/emergency/send-sos-sms/ and /api/v1/send-sos-sms/
    path(
        "send-sos-sms/",
        SendSosSMSView.as_view(),
        name="send_sos_sms",
    ),

    # Emergency Categories
    path(
        "emergency-categories/",
        EmergencyCategoryListView.as_view(),
        name="emergency-category-list",
    ),
    path("emergency-categories/<int:category_id>/", EmergencyCategoryDetailView.as_view(), name="emergency-category-detail"),
    path("emergency-categories/<int:category_id>/status/", EmergencyCategoryDetailView.as_view(), name="emergency-category-status"),

    # Add / List Emergency Contacts
    path(
        "users/me/emergency-contacts/",
        EmergencyContactListCreateView.as_view(),
        name="emergency-contact-list-create",
    ),

    # Update / Delete Emergency Contact
    path(
        "emergency-contacts/<int:contact_id>/",
        EmergencyContactDetailView.as_view(),
        name="emergency-contact-detail",
    ),

    # Send OTP
    path(
        "emergency-contacts/<int:contact_id>/send-otp/",
        EmergencyContactSendOTPView.as_view(),
        name="emergency-contact-send-otp",
    ),

    # Verify OTP
    path(
        "emergency-contacts/<int:contact_id>/verify/",
        EmergencyContactVerifyView.as_view(),
        name="emergency-contact-verify",
    ),

    # SOS Configuration
    path(
        "users/me/sos-config/",
        SOSConfigurationView.as_view(),
        name="sos-configuration",
    ),

]
