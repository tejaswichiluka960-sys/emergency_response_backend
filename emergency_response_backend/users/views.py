from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import UserProfile
from users.permissions import IsAdminOrSubAdmin
import random
from django.core.mail import send_mail
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from.serializers import LocationSerializer


class RegisterView(APIView):

    def post(self, request):

        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")
        phone = request.data.get("phone")
        role = request.data.get("role", "GUARDIAN")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        otp = str(random.randint(100000, 999999))

        profile = UserProfile.objects.create(
        user=user,
        phone=phone,
        role=role,
        otp=otp
        )
        send_mail(
        subject="OTP Verification",
        message=f"Your OTP is {otp}",
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False,
        )
        return Response({
            "message": "User Registered Successfully"
        })


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
            "role": profile.role
        })
        

from rest_framework.permissions import IsAuthenticated

class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user

        user.username = request.data.get("username", user.username)
        user.email = request.data.get("email", user.email)

        user.save()

        return Response({
            "message": "Profile updated successfully",
            "username": user.username,
            "email": user.email
        })
    
class DeleteProfileView(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self, request):
        request.user.delete()

        return Response({
            "message": "Profile deleted successfully"
        })
        
class SendOTPView(APIView):
    def post(self, request):
        email = request.data.get("email")

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

            send_mail(
                "OTP Verification",
                f"Your OTP is {otp}",
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )

            return Response({
                "message": "OTP sent successfully"
            })

        except Exception as e:
            return Response({
                "error": str(e)
            }, status=400)          
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
    permission_classes = [IsAuthenticated]

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
    
    
class GetLocationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        profile = request.user.userprofile

        serializer = LocationSerializer(profile)

        return Response(serializer.data)                
            
            