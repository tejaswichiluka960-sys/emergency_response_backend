from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import UserProfile
from users.permissions import (
    IsAdminOrSubAdmin,
    PLATFORM_ADMIN_ROLES,
    SOCIETY_ADMIN_ROLES,
    SUPPORTED_ROLES,
    get_role,
    is_platform_admin,
    is_society_admin,
    IsLocationParticipant,
    IsResponder,
    get_role_permissions,
)
import random
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from.serializers import LocationSerializer


class RegisterView(APIView):

    def post(self, request):

        username = request.data.get("username") or request.data.get("email")
        email = request.data.get("email")
        password = request.data.get("password")
        phone = request.data.get("phone")
        name = str(request.data.get("name") or "").strip()
        location = str(request.data.get("location") or "").strip()
        society_name = str(request.data.get("society_name") or "").strip()
        flat_number = str(request.data.get("flat_number") or "").strip()
        role = str(request.data.get("role", "RESIDENT")).strip().upper()
        if not username or not email or not password or not phone or not role or not name or not location or not society_name or not flat_number:
            return Response(
                {"message": "name, location, society name, flat number, contact number, username, email, and password are required."},
                status=400,
            )
        if len(str(password)) < 5:
            return Response(
                {"message": "Password must be at least 5 characters long."},
                status=400,
            )
        if role not in SUPPORTED_ROLES:
            return Response(
                {"message": "role must be one of ADMIN, SUB_ADMIN, RESIDENT, GUARDIAN, VOLUNTEER, or SECURITY."},
                status=400,
            )

        # Public registration may create residents only. Administrative roles
        # must be provisioned by an already authenticated administrator.
        requester = request.user if request.user.is_authenticated else None
        if requester is None and role != "RESIDENT":
            return Response(
                {"success": False, "message": "Only residents can self-register."},
                status=403,
            )
        if requester is not None and is_society_admin(requester) and role in (PLATFORM_ADMIN_ROLES | SOCIETY_ADMIN_ROLES):
            return Response(
                {"success": False, "message": "Society administrators cannot create administrator accounts."},
                status=403,
            )
        if requester is not None and not (is_platform_admin(requester) or is_society_admin(requester)) and role != "RESIDENT":
            return Response(
                {"success": False, "message": "Only administrators can assign non-resident roles."},
                status=403,
            )

        if User.objects.filter(username__iexact=username).exists():
            return Response(
                {"success": False, "message": "Username already exists. Please choose another username."},
                status=400,
            )

        otp = str(random.randint(100000, 999999))

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )

                UserProfile.objects.create(
                    user=user,
                    phone=phone,
                    name=name,
                    location=location,
                    society_name=society_name,
                    flat_number=flat_number,
                    role=role,
                    society_id=request.data.get("society_id") or None,
                    flat_id=request.data.get("flat_id") or None,
                    otp=otp
                )
        except IntegrityError:
            return Response(
                {"success": False, "message": "Username already exists. Please use different registration details."},
                status=400,
            )

        email_sent = True
        try:
            send_mail(
                subject="OTP Verification",
                message=f"Your OTP is {otp}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception:
            # Registration remains usable when SMTP is unavailable; the OTP
            # stays stored for environments that provide another delivery path.
            email_sent = False

        return Response({
            "success": True,
            "message": "User registered successfully.",
            "email_delivery": "sent" if email_sent else "failed",
        }, status=201)


class LoginView(APIView):

    def post(self, request):

        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(
            username=username,
            password=password
        )

        if user is None:
            return Response(
                {"message": "Invalid Credentials"},
                status=401
            )

        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        })


from .models import UserProfile

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        profile = UserProfile.objects.get(user=user)

        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "phone": profile.phone,
            "name": profile.name,
            "location": profile.location,
            "society_name": profile.society_name,
            "flat_number": profile.flat_number,
            "role": profile.role,
            "permissions": get_role_permissions(request.user),
            "society_id": profile.society_id,
            "flat_id": profile.flat_id,
        })


class MeView(ProfileView):
    """Canonical alias for the authenticated user's profile."""


class ProfileListView(APIView):
    """Return all profiles with the roles assigned during registration."""

    permission_classes = [IsAuthenticated, IsAdminOrSubAdmin]

    def get(self, request):
        profiles = UserProfile.objects.select_related("user").order_by("id")
        if is_society_admin(request.user):
            profiles = profiles.filter(society_id=getattr(request.user.userprofile, "society_id", None))
        return Response({
            "count": profiles.count(),
            "profiles": [
                {
                    "id": profile.user.id,
                    "username": profile.user.username,
                    "email": profile.user.email,
                    "phone": profile.phone,
                    "role": profile.role,
                    "permissions": get_role_permissions(profile.user),
                    "society_id": profile.society_id,
                    "flat_id": profile.flat_id,
                }
                for profile in profiles
            ],
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Access-token invalidation requires a configured token blacklist.
        # The client must discard both tokens; this endpoint remains safe and idempotent.
        return Response({"success": True, "message": "Logged out successfully."})


class ForgotPasswordView(APIView):
    def post(self, request):
        email = request.data.get("email")
        user = User.objects.filter(email=email).first()
        if user and hasattr(user, "userprofile"):
            profile = user.userprofile
            profile.otp = str(random.randint(100000, 999999))
            profile.save(update_fields=["otp"])
            try:
                send_mail("Password reset OTP", f"Your OTP is {profile.otp}", settings.DEFAULT_FROM_EMAIL, [email], fail_silently=True)
            except Exception:
                pass
        return Response({"success": True, "message": "If the account exists, a reset OTP was sent."})


class ResetPasswordView(APIView):
    def post(self, request):
        email = request.data.get("email")
        otp = str(request.data.get("otp", ""))
        password = request.data.get("new_password")
        user = User.objects.filter(email=email).first()
        if not user or not password or not hasattr(user, "userprofile") or user.userprofile.otp != otp:
            return Response({"success": False, "message": "Invalid reset request."}, status=400)
        user.set_password(password)
        user.save(update_fields=["password"])
        user.userprofile.otp = None
        user.userprofile.save(update_fields=["otp"])
        return Response({"success": True, "message": "Password reset successfully."})
        

from rest_framework.permissions import IsAuthenticated

class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        requester = request.user
        requester_role = get_role(requester)
        target_id = request.data.get("user_id")
        target_username = request.data.get("target_username")

        # For admin requests, keep the existing username field as a backwards-
        # compatible target selector. Use new_username only when renaming.
        if is_platform_admin(requester) and not target_id and not target_username and "username" in request.data:
            target_username = request.data.get("username")
        user = requester

        if target_id not in (None, "") or target_username not in (None, ""):
            if not (is_platform_admin(requester) or is_society_admin(requester)):
                return Response(
                    {"success": False, "message": "Only an admin can update another profile."},
                    status=403,
                )
            try:
                user = (
                    User.objects.get(pk=target_id)
                    if target_id not in (None, "")
                    else User.objects.get(username__iexact=str(target_username).strip())
                )
            except (User.DoesNotExist, ValueError, TypeError):
                return Response(
                    {"success": False, "message": "Target profile was not found."},
                    status=404,
                )
            if is_society_admin(requester):
                requester_society = getattr(requester.userprofile, "society_id", None)
                if getattr(getattr(user, "userprofile", None), "society_id", None) != requester_society:
                    return Response({"success": False, "message": "Target profile is outside your society."}, status=403)

        if "new_username" in request.data:
            username = str(request.data.get("new_username", "")).strip()
            if not username:
                return Response(
                    {"success": False, "message": "Username cannot be empty."},
                    status=400,
                )
            if User.objects.filter(username__iexact=username).exclude(pk=user.pk).exists():
                return Response(
                    {"success": False, "message": "Username already exists. Choose another username."},
                    status=400,
                )
            user.username = username
        elif not is_platform_admin(requester) and "username" in request.data:
            username = str(request.data.get("username", "")).strip()
            if not username:
                return Response(
                    {"success": False, "message": "Username cannot be empty."},
                    status=400,
                )
            if User.objects.filter(username__iexact=username).exclude(pk=user.pk).exists():
                return Response(
                    {"success": False, "message": "Username already exists. Choose another username."},
                    status=400,
                )
            user.username = username

        if "email" in request.data:
            email = str(request.data.get("email", "")).strip()
            if not email:
                return Response(
                    {"success": False, "message": "Email cannot be empty."},
                    status=400,
                )
            user.email = email

        profile = getattr(user, "userprofile", None)
        if profile:
            profile_fields = []
            for field in ("phone", "name", "location", "society_name", "flat_number"):
                if field in request.data:
                    value = str(request.data.get(field) or "").strip()
                    if field in ("phone", "name", "location", "society_name", "flat_number") and not value:
                        return Response({"success": False, "message": f"{field.replace('_', ' ').capitalize()} cannot be empty."}, status=400)
                    setattr(profile, field, value)
                    profile_fields.append(field)
            if profile_fields:
                profile.save(update_fields=profile_fields)

        try:
            user.save()
        except IntegrityError:
            return Response(
                {"success": False, "message": "Username already exists. Choose another username."},
                status=400,
            )

        return Response({
            "message": "Profile updated successfully",
            "user_id": user.id,
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "phone": profile.phone if profile else "",
            "name": profile.name if profile else "",
            "location": profile.location if profile else "",
            "society_name": profile.society_name if profile else "",
            "flat_number": profile.flat_number if profile else "",
            "role": profile.role if profile else "RESIDENT",
        })
    
class DeleteProfileView(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self, request):
        requester = request.user
        requester_role = get_role(requester)
        target_id = request.query_params.get("user_id") or request.data.get("user_id")
        target_username = request.query_params.get("username") or request.data.get("target_username")
        user = requester

        if target_id not in (None, "") or target_username not in (None, ""):
            if not (is_platform_admin(requester) or is_society_admin(requester)):
                return Response(
                    {"success": False, "message": "Only an admin can delete another profile."},
                    status=403,
                )
            try:
                user = (
                    User.objects.get(pk=target_id)
                    if target_id not in (None, "")
                    else User.objects.get(username__iexact=str(target_username).strip())
                )
            except (User.DoesNotExist, ValueError, TypeError):
                return Response(
                    {"success": False, "message": "Target profile was not found."},
                    status=404,
                )
            if is_society_admin(requester):
                requester_society = getattr(requester.userprofile, "society_id", None)
                if getattr(getattr(user, "userprofile", None), "society_id", None) != requester_society:
                    return Response({"success": False, "message": "Target profile is outside your society."}, status=403)

        deleted_id = user.id
        user.delete()

        return Response({
            "message": "Profile deleted successfully",
            "user_id": deleted_id,
        })
        
class SendOTPView(APIView):
    def post(self, request):
        email = str(request.data.get("email") or "").strip()

        if not email:
            return Response({"message": "Email is required."}, status=400)
        try:
            validate_email(email)
        except ValidationError:
            return Response({"message": "A valid email address is required."}, status=400)

        try:
            users = User.objects.filter(email=email)

            if not users.exists():
                return Response({
                    "message": "User not found"
                }, status=404)

            user = users.first()

            profile = UserProfile.objects.get(user=user)

            otp = str(random.randint(100000, 999999))

            profile.otp = otp
            profile.save()

            if settings.EMAIL_BACKEND.endswith("console.EmailBackend"):
                return Response({
                    "success": False,
                    "message": "SMTP email is not configured. Add EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, and DEFAULT_FROM_EMAIL to .env.",
                }, status=503)

            sent = send_mail(
                "OTP Verification",
                f"Your OTP is {otp}",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

            if sent != 1:
                return Response({
                    "success": False,
                    "message": "OTP email was not accepted by the email backend.",
                }, status=503)

            return Response({
                "success": True,
                "message": "OTP sent successfully"
            })

        except Exception:
            return Response({
                "success": False,
                "message": "OTP email could not be sent. Check the SMTP configuration.",
            }, status=503)
class VerifyOTPView(APIView):
    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        try:
            users = User.objects.filter(email=email)

            if not users.exists():
                return Response({
                    "message": "User not found"
                }, status=404)

            user = users.first()

            profile = UserProfile.objects.get(user=user)

            if profile.otp == otp:
                profile.is_verified = True
                profile.otp = None
                profile.save()

                return Response({
                    "message": "OTP verified successfully"
                })

            return Response({
                "message": "Invalid OTP"
            }, status=400)

        except Exception as e:
            return Response({
                "error": str(e)
            }, status=400)
            
class UpdateLocationView(APIView):
    permission_classes = [IsAuthenticated, IsLocationParticipant]

    def post(self, request):

        profile = request.user.userprofile

        serializer = LocationSerializer(
            profile,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()

            return Response({
                "success": True,
                "message": "Location updated successfully."
            })

        return Response(serializer.errors)

    def get(self, request):
        profile = request.user.userprofile
        return Response(LocationSerializer(profile).data)
    
    
class GetLocationView(APIView):
    permission_classes = [IsAuthenticated, IsLocationParticipant]

    def get(self, request):

        profile = request.user.userprofile

        serializer = LocationSerializer(profile)

        return Response(serializer.data)                


class ResponderAvailabilityView(APIView):
    permission_classes = [IsAuthenticated, IsResponder]

    def get(self, request):
        profile = request.user.userprofile
        return Response({
            "success": True,
            "data": {
                "is_available": profile.is_available,
                "availability_status": "AVAILABLE" if profile.is_available else "UNAVAILABLE",
                "updated_at": profile.availability_updated_at,
            },
        })

    def patch(self, request):
        raw_value = request.data.get("is_available", request.data.get("available"))
        if isinstance(raw_value, bool):
            is_available = raw_value
        elif str(raw_value).strip().lower() in {"true", "1", "yes", "available"}:
            is_available = True
        elif str(raw_value).strip().lower() in {"false", "0", "no", "unavailable"}:
            is_available = False
        else:
            return Response({
                "success": False,
                "message": "is_available must be a boolean.",
            }, status=400)

        profile = request.user.userprofile
        profile.is_available = is_available
        profile.availability_updated_at = timezone.now()
        profile.save(update_fields=["is_available", "availability_updated_at"])
        return Response({
            "success": True,
            "message": "Availability updated successfully.",
            "data": {
                "is_available": profile.is_available,
                "availability_status": "AVAILABLE" if profile.is_available else "UNAVAILABLE",
                "updated_at": profile.availability_updated_at,
            },
        })


class ResponderLocationView(APIView):
    permission_classes = [IsAuthenticated, IsResponder]

    def get(self, request):
        profile = request.user.userprofile
        return Response({"success": True, "data": LocationSerializer(profile).data})

    def post(self, request):
        profile = request.user.userprofile
        serializer = LocationSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(location_updated_at=timezone.now())
        return Response({
            "success": True,
            "message": "Responder location updated successfully.",
            "data": LocationSerializer(profile).data,
        })
            
