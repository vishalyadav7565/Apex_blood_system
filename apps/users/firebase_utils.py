import os
import firebase_admin

from firebase_admin import credentials, auth


# Initialize Firebase only once
if not firebase_admin._apps:

    FIREBASE_CREDENTIALS = os.getenv(
        "FIREBASE_CREDENTIALS",
        "/app/firebase-service-account.json"
    )

    # Check file exists
    if not os.path.exists(FIREBASE_CREDENTIALS):
        raise FileNotFoundError(
            f"Firebase credentials file not found: {FIREBASE_CREDENTIALS}"
        )

    cred = credentials.Certificate(FIREBASE_CREDENTIALS)

    firebase_admin.initialize_app(cred)


def verify_firebase_token(id_token):

    try:
        decoded_token = auth.verify_id_token(id_token, clock_skew_seconds=60)

        return decoded_token

    except Exception as e:

        print("Firebase Verify Error:", str(e))

        return None