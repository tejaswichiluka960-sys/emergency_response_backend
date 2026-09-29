from .models import Notification
from firebase_admin import messaging
from config import firebase

def send_push_notification(device_token=None, topic=None, title="Emergency Alert", body="", data=None):
    """
    Send a push notification to either a specific Firebase device token or a topic.
    """
    sanitized_data = {str(k): str(v) for k, v in (data or {}).items()}

    if device_token and str(device_token).strip():
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=str(device_token).strip(),
            data=sanitized_data,
        )
    elif topic and str(topic).strip():
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            topic=str(topic).strip(),
            data=sanitized_data,
        )
    else:
        raise ValueError("Either device_token or topic must be provided.")

    response = messaging.send(message)
    return response

def create_notification(user, title, message, notification_type='SOS'):
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
