# Ensure Firebase is initialized
import apps.notifications.firebase
from firebase_admin import messaging

def send_push_notification(
    token,
    title,
    body,
    data=None
):
    if not token:
        print("Notification Skip: Token is empty")
        return False
        
    try:
        # Convert all data keys and values to strings (FCM requirement)
        fcm_data = {}
        if data:
            fcm_data = {str(k): str(v) for k, v in data.items()}

        message = messaging.Message(
            token=token,
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=fcm_data
        )

        response = messaging.send(
            message
        )

        print(
            "Notification Sent:",
            response
        )

        return True

    except Exception as e:

        print(
            "Notification Error:",
            e
        )

        return False