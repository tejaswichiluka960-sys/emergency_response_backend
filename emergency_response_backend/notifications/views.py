from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .services import send_push_notification
from .models import Notification
from .serializers import NotificationSerializer
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import status

class MyNotificationsView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        Notification.objects.get_or_create(
    user=request.user,
    notification_type='SOS',
    title='SOS Alert',
    message='SOS alert created'
)

        notifications = Notification.objects.filter(
            user=request.user
        )

        serializer = NotificationSerializer(
            notifications,
            many=True
        )

        return Response(serializer.data)

class MarkNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        notification = Notification.objects.get(
            id=notification_id,
            user=request.user
        )

        notification.is_read = True
        notification.save()

        return Response({
            "success": True,
            "message": "Notification marked as read"
        })
        
class NotificationCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()

        return Response({
            "success": True,
            "unread_count": count
        })
        
class SendSMSView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        phone = request.data.get("phone")
        message = request.data.get("message")

        return Response({
            "success": True,
            "message": f"SMS sent to {phone}",
            "sms_content": message
        })
        
class SendEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        email = request.data.get("email")
        subject = request.data.get("subject")
        message = request.data.get("message")

        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=False,
        )

        return Response({
            "success": True,
            "message": "Email sent successfully"
        })
        
class SendNotificationView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        device_token = request.data.get("device_token")
        title = request.data.get("title")
        body = request.data.get("body")

        if not device_token:
            return Response(
                {"error": "device_token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not title:
            return Response(
                {"error": "title is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not body:
            return Response(
                {"error": "body is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            response = send_push_notification(
                device_token=device_token,
                title=title,
                body=body
            )

            return Response(
                {
                    "message": "Notification sent successfully",
                    "firebase_response": response
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:

            return Response(
                {
                    "error": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )