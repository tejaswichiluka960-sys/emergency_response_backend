import json
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone
from django.shortcuts import get_object_or_404

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
from twilio.base.exceptions import TwilioRestException, TwilioException
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from users.permissions import IsResident, IsResidentOrPlatformAdmin, is_platform_admin



class EmergencyContactListCreateView(APIView):

    permission_classes = [IsAuthenticated, IsResidentOrPlatformAdmin]

    def get(self, request):

        contacts = EmergencyContact.objects.all()
        if not is_platform_admin(request.user):
            contacts = contacts.filter(user=request.user)
        elif request.query_params.get("user_id"):
            contacts = contacts.filter(user_id=request.query_params["user_id"])
        contacts = contacts.order_by("priority", "-created_at")

        serializer = EmergencyContactSerializer(
            contacts,
            many=True
        )

        return Response({
            "success": True,
            "data": serializer.data
        })

    def post(self, request):

        serializer = EmergencyContactSerializer(data=request.data)

        if serializer.is_valid():

            owner = request.user
            if is_platform_admin(request.user) and request.data.get("user_id"):
                owner = get_user_model().objects.filter(id=request.data["user_id"]).first()
                if owner is None:
                    return Response({"success": False, "message": "Target user not found."}, status=status.HTTP_404_NOT_FOUND)
            contact = serializer.save(user=owner)

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

    permission_classes = [IsAuthenticated, IsResidentOrPlatformAdmin]

    def get_contact(self, request, contact_id):

        try:

            query = {"id": contact_id}
            if not is_platform_admin(request.user):
                query["user"] = request.user
            return EmergencyContact.objects.get(**query)

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

    permission_classes = [IsAuthenticated, IsResidentOrPlatformAdmin]

    def post(self, request, contact_id):

        try:

            query = {"id": contact_id}
            if not is_platform_admin(request.user):
                query["user"] = request.user
            contact = EmergencyContact.objects.get(**query)

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
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[contact.email],
                fail_silently=False
            )

        except Exception:

            # Do not log OTP values. Delivery failures are handled generically.
            pass

        return Response({
            "success": True,
            "message": "Verification OTP sent to email."
        })
        
        
class EmergencyContactVerifyView(APIView):

    permission_classes = [IsAuthenticated, IsResidentOrPlatformAdmin]

    def post(self, request, contact_id):

        try:

            query = {"id": contact_id}
            if not is_platform_admin(request.user):
                query["user"] = request.user
            contact = EmergencyContact.objects.get(**query)

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

    permission_classes = [IsAuthenticated, IsResident]

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

    def post(self, request):
        if not is_platform_admin(request.user):
            return Response({'success': False, 'message': 'Administrator permission required.'}, status=403)
        category, created = EmergencyCategory.objects.get_or_create(
            code=str(request.data.get('code', '')).lower(),
            defaults={'name': request.data.get('name', ''), 'icon': request.data.get('icon', '')},
        )
        if not created:
            return Response({'success': False, 'message': 'Category already exists.'}, status=409)
        return Response({'success': True, 'data': {'id': category.id, 'code': category.code, 'name': category.name, 'is_active': category.is_active}}, status=201)


class EmergencyCategoryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, category_id):
        if not is_platform_admin(request.user):
            return Response({'success': False, 'message': 'Administrator permission required.'}, status=403)
        category = get_object_or_404(EmergencyCategory, id=category_id)
        for field in ('code', 'name', 'icon', 'is_active'):
            if field in request.data:
                setattr(category, field, request.data[field])
        category.save()
        return Response({'success': True, 'data': {'id': category.id, 'code': category.code, 'name': category.name, 'is_active': category.is_active}})


class SendSosSMSView(APIView):
    permission_classes = [IsAuthenticated]

    TRIAL_SMS_TEMPLATES = {
        "sms_2fa",
        "sms_appointment_reminders",
        "sms_order_confirmation",
        "sms_delivery_updates",
        "sms_customer_support",
        "sms_marketing_promotions",
        "sms_event_notifications",
        "sms_account_alerts",
        "sms_feedback_surveys",
        "sms_internal_alerts",
    }

    def post(self, request):
        phone = request.data.get("phone")
        message = request.data.get("message")
        content_sid = getattr(settings, "TWILIO_SMS_CONTENT_SID", None)

        # Validation for missing/empty phone
        if not phone or not str(phone).strip():
            return Response(
                {
                    "success": False,
                    "error": "Phone number is required"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # A custom body is required only when no Content API template is set.
        if not content_sid and (not message or not str(message).strip()):
            return Response(
                {
                    "success": False,
                    "error": "Message is required"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        phone = str(phone).strip()
        message = str(message or "").strip()

        # Normalize phone to E.164 if missing leading +
        if not phone.startswith("+"):
            if len(phone) == 10:
                phone = f"+91{phone}"
            else:
                phone = f"+{phone}"

        # Load credentials safely from settings or environment
        account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None) or os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None) or os.getenv("TWILIO_AUTH_TOKEN")
        twilio_number = getattr(settings, "TWILIO_PHONE_NUMBER", None) or os.getenv("TWILIO_PHONE_NUMBER")

        if not account_sid or not auth_token or not twilio_number:
            return Response(
                {
                    "success": False,
                    "error": "Twilio configuration is incomplete on server (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, or TWILIO_PHONE_NUMBER missing)."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            client = Client(account_sid, auth_token)

            message_options = {
                "from_": twilio_number,
                "to": phone,
            }
            if content_sid:
                message_options["content_sid"] = content_sid
                content_variables = request.data.get("content_variables")
                if content_variables is not None:
                    if not isinstance(content_variables, dict):
                        return Response(
                            {
                                "success": False,
                                "error": "content_variables must be a JSON object."
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    message_options["content_variables"] = json.dumps(
                        {str(key): str(value) for key, value in content_variables.items()}
                    )
            elif getattr(settings, "TWILIO_USE_TRIAL_TEMPLATES", False):
                configured_template = getattr(
                    settings, "TWILIO_TRIAL_SMS_TEMPLATE", "sms_internal_alerts"
                )
                requested_template = message.casefold()
                trial_template = (
                    requested_template
                    if requested_template in self.TRIAL_SMS_TEMPLATES
                    else configured_template
                )
                if trial_template not in self.TRIAL_SMS_TEMPLATES:
                    return Response(
                        {
                            "success": False,
                            "error": "Invalid Twilio trial SMS template configuration.",
                            "allowed_templates": sorted(self.TRIAL_SMS_TEMPLATES),
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
                message_options["body"] = trial_template
            else:
                message_options["body"] = message

            sms = client.messages.create(**message_options)

            return Response({
                "success": True,
                "message": "SOS SMS sent successfully",
                "sid": sms.sid
            }, status=status.HTTP_200_OK)

        except TwilioRestException as e:
            error_msg = str(getattr(e, 'msg', e))
            template_restriction = (
                e.code == 572006
                or "predefined sms templates" in error_msg.lower()
                or "invalid template name" in error_msg.lower()
            )
            is_trial = e.code in {21608, 572006} or "trial" in error_msg.lower()
            return Response({
                "success": False,
                "error": error_msg,
                "code": e.code,
                "is_trial_restriction": is_trial,
                "trial_note": (
                    "Twilio trial accounts do not allow custom SMS bodies. Use one of the predefined trial templates (for example sms_internal_alerts) or upgrade the Twilio account."
                    if template_restriction else
                    "Twilio Trial restriction: You can only send SMS to phone numbers verified on your Twilio Console under 'Verified Caller IDs'."
                    if is_trial else None
                )
            }, status=status.HTTP_400_BAD_REQUEST)

        except TwilioException as e:
            return Response({
                "success": False,
                "error": f"Twilio error: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({
                "success": False,
                "error": "Unexpected error while sending SMS",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
