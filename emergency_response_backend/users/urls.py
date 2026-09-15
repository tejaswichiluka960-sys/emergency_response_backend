from django.urls import path
from .views import *
from users.views import VerifyOTPView
from .views import SendOTPView
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UpdateLocationView,
    GetLocationView,
)

urlpatterns = [
    path('auth/register/', RegisterView.as_view()),
    path('auth/login/', LoginView.as_view()),
    path('auth/profile/', ProfileView.as_view()),
    path('auth/profile/update/', UpdateProfileView.as_view()),
    path('auth/profile/delete/', DeleteProfileView.as_view()),
    path("verify-otp/", VerifyOTPView.as_view()),
    path('send-otp/', SendOTPView.as_view()),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path(
    "me/location/",
    UpdateLocationView.as_view(),
    name="update-location"
),

path(
    "me/location/get/",
    GetLocationView.as_view(),
    name="get-location"
),
]
