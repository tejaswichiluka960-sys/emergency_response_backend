import random
from datetime import timedelta

from django.core.mail import send_mail
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EmergencyContact
from .serializers import EmergencyContactSerializer
from .models import SOSConfiguration
from .serializers import SOSConfigurationSerializer

import os
from twilio.rest import Client
from rest_framework.decorators import api_view



class EmergencyContactListCreateView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        contacts = EmergencyContact.objects.filter(
            user=request.user
        ).order_by("priority", "-created_at")

        serializer = EmergencyContactSerializer(
            contacts,
            many=True
        )

        return Response({
            "success": True,
            "data": serializer.data
        })

    def post(self, request):

        serializer = EmergencyContactSerializer(
            data=request.data
        )

        if serializer.is_valid():

            contact = serializer.save(
                user=request.user
            )

            return Response({
                "success": True,
                "message": "Emergency contact added.",
                "data": {
                    "id": contact.id,
                    "is_verified": contact.is_verified
                }
            }, status=status.HTTP_201_CREATED)

        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
        
class EmergencyContactDetailView(APIView):

    permission_classes = [IsAuthenticated]

    def get_contact(self, request, contact_id):

        try:

            return EmergencyContact.objects.get(
                id=contact_id,
                user=request.user
            )

        except EmergencyContact.DoesNotExist:

            return None

    def patch(self, request, contact_id):

        contact = self.get_contact(
            request,
            contact_id
        )

        if not contact:

            return Response({
                "success": False,
                "message": "Emergency contact not found."
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = EmergencyContactSerializer(
            contact,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            serializer.save()

            return Response({
                "success": True,
                "message": "Emergency contact updated.",
                "data": serializer.data
            })

        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, contact_id):

        contact = self.get_contact(
            request,
            contact_id
        )

        if not contact:

            return Response({
                "success": False,
                "message": "Emergency contact not found."
            }, status=status.HTTP_404_NOT_FOUND)

        contact.delete()

        return Response({
            "success": True,
            "message": "Emergency contact deleted successfully."
        })
        
        
class EmergencyContactSendOTPView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, contact_id):

        try:

            contact = EmergencyContact.objects.get(
                id=contact_id,
                user=request.user
            )

        except EmergencyContact.DoesNotExist:

            return Response({
                "success": False,
                "message": "Emergency contact not found."
            }, status=status.HTTP_404_NOT_FOUND)

        otp = str(
            random.randint(100000, 999999)
        )

        contact.otp = otp

        contact.otp_expiry = (
            timezone.now() +
            timedelta(minutes=5)
        )

        contact.is_verified = False

        contact.save(
            update_fields=[
                "otp",
                "otp_expiry",
                "is_verified",
                "updated_at"
            ]
        )

        # Send OTP to email
        try:

            send_mail(
                subject="Emergency Contact Verification OTP",
                message=(
                    f"Your emergency contact "
                    f"verification OTP is: {otp}"
                ),
                from_email=None,
                recipient_list=[contact.email],
                fail_silently=False
            )

        except Exception:

            # For development, print OTP
            print(
                f"Emergency Contact OTP for "
                f"{contact.email}: {otp}"
            )

        return Response({
            "success": True,
            "message": "Verification OTP sent to email."
        })
        
        
class EmergencyContactVerifyView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, contact_id):

        try:

            contact = EmergencyContact.objects.get(
                id=contact_id,
                user=request.user
            )

        except EmergencyContact.DoesNotExist:

            return Response({
                "success": False,
                "message": "Emergency contact not found."
            }, status=status.HTTP_404_NOT_FOUND)

        otp = request.data.get("otp")

        if not otp:

            return Response({
                "success": False,
                "message": "OTP is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        if contact.otp != str(otp):

            return Response({
                "success": False,
                "message": "Invalid OTP."
            }, status=status.HTTP_400_BAD_REQUEST)

        if not contact.otp_expiry:

            return Response({
                "success": False,
                "message": "OTP has expired."
            }, status=status.HTTP_400_BAD_REQUEST)

        if timezone.now() > contact.otp_expiry:

            return Response({
                "success": False,
                "message": "OTP has expired."
            }, status=status.HTTP_400_BAD_REQUEST)

        contact.is_verified = True

        contact.otp = None

        contact.otp_expiry = None

        contact.save(
            update_fields=[
                "is_verified",
                "otp",
                "otp_expiry",
                "updated_at"
            ]
        )

        return Response({
            "success": True,
            "message": "Emergency contact verified successfully."
        })
        

class SOSConfigurationView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        config, created = SOSConfiguration.objects.get_or_create(
            user=request.user
        )

        serializer = SOSConfigurationSerializer(config)

        return Response({
            "success": True,
            "data": serializer.data
        })

    def patch(self, request):

        config, created = SOSConfiguration.objects.get_or_create(
            user=request.user
        )

        serializer = SOSConfigurationSerializer(
            config,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            serializer.save()

            return Response({
                "success": True,
                "message": "SOS configuration updated successfully."
            })

        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import EmergencyCategory


class EmergencyCategoryListView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        categories = EmergencyCategory.objects.filter(
            is_active=True
        ).order_by('id')

        data = []

        for category in categories:
            data.append({
                'id': category.id,
                'code': category.code,
                'name': category.name,
                'is_active': category.is_active
            })

        return Response({
            'success': True,
            'data': data
        })


class SendSosSMSView(APIView):

    def post(self, request):
        message = request.data.get("message")
        phone = request.data.get("phone")

        if not phone:
            return Response(
                {"error": "Phone number is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not message:
            message = "SOS Alert! Resident needs help."

        try:
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

            client = Client(account_sid, auth_token)

            sms = client.messages.create(
                body="sms_account_alerts",
                from_=+17372508034,
                to=+918919875820
            )

            return Response({
                "success": True,
                "message": "SOS SMS sent successfully",
                "sid": sms.sid
            })

        except Exception as e:
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    