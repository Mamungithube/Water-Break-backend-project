# account/tasks.py
from celery import shared_task
from .models import User
from .fcm import send_push_to_tokens
import logging

logger = logging.getLogger(__name__)


@shared_task(name="send_fcm_notification")
def send_fcm_notification_task(user_id, title, body, data=None):
    try:
        user = User.objects.get(id=user_id)
        tokens = list(user.device_tokens.values_list('token', flat=True))
        if not tokens:
            return f"No tokens found for user {user.email}"
        response = send_push_to_tokens(tokens, title, body, data)
        return f"Push sent to {len(tokens)} devices for {user.email}"
    except User.DoesNotExist:
        return f"User with id {user_id} not found"
    except Exception as e:
        logger.error(f"FCM Task Error: {str(e)}")
        return str(e)


@shared_task(name="send_email_task")
def send_email_task(subject, body, recipient_list, is_html=True):
    from django.conf import settings
    import resend # type: ignore
    try:
        resend.api_key = settings.RESEND_API_KEY
        params = {
            "from": "Water Break <onboarding@resend.dev>",
            "to": recipient_list,
            "subject": subject,
            "html": body if is_html else f"<p>{body}</p>",
        }
        resend.Emails.send(params)
        return f"Email sent to {recipient_list}"
    except Exception as e:
        return f"Email failed: {str(e)}"


@shared_task(name="send_otp_email", max_retries=3)
def send_otp_email_task(user_email, otp):
    from django.template.loader import render_to_string
    from django.conf import settings
    import resend # type: ignore
    try:
        resend.api_key = settings.RESEND_API_KEY
        html_content = render_to_string(
            'send_code.html',
            {'otp': otp, 'user': {'email': user_email}}
        )
        params = {
            "from": "Water Break <onboarding@resend.dev>",
            "to": [user_email],
            "subject": "Your OTP Code - Verify Your Account",
            "html": html_content,
        }
        resend.Emails.send(params)
        logger.info(f"OTP email sent to {user_email}")
        return f"OTP email sent to {user_email}"
    except Exception as exc:
        logger.error(f"Failed to send OTP email to {user_email}: {str(exc)}")
        raise send_otp_email_task.retry(exc=exc, countdown=60)