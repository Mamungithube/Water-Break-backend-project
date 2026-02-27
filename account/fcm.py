import threading
from django.conf import settings

# the firebase-admin package is optional at import time; if it's not
# installed the utility functions will raise when called.
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except ImportError:
    firebase_admin = None
    credentials = None
    messaging = None


# initialize firebase app once

def init_firebase():
    if firebase_admin is None:
        raise ImportError("firebase-admin package is not installed; install via pip to enable FCM support")

    if not firebase_admin._apps:
        cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)
        if not cred_path:
            raise ValueError("FIREBASE_CREDENTIALS_PATH is not configured in settings")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)


def send_push_to_token(token: str, title: str, body: str, data: dict | None = None):
    init_firebase()
    if messaging is None:
        raise ImportError("firebase-admin.messaging not available")
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
        token=token,
    )
    return messaging.send(message)


def send_push_to_tokens(tokens: list[str], title: str, body: str, data: dict | None = None):
    """Send a multicast message. Return firebase response."""
    if not tokens:
        return None
    init_firebase()
    if messaging is None:
        raise ImportError("firebase-admin.messaging not available")
    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
        tokens=tokens,
    )
    return messaging.send_multicast(message)


def push_notification_for_user(user, title: str, body: str, data: dict | None = None):
    """Helper to push message to all registered device tokens of a user."""
    tokens = list(user.device_tokens.values_list('token', flat=True))
    if not tokens:
        return None
    # send asynchronously so that calling code isn't blocked by network
    thread = threading.Thread(
        target=send_push_to_tokens,
        args=(tokens, title, body, data),
        daemon=True,
    )
    thread.start()
    return thread
