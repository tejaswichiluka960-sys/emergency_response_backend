from .models import Notification
from firebase_admin import messaging
from config import firebase

def send_push_notification(device_token, title, body, data=None):
    """
    Send a push notification to one Firebase device.
    """

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=device_token,
        data=data or {},
    )

    response = messaging.send(message)

    return response

def create_notification(user, title, message, notification_type=None):
    """
    Create a notification record for a user.
    """

    from .models import Notification

    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type
    )

    return notification