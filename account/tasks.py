# account/tasks.py
from celery import shared_task
from .models import User
from .fcm import send_push_to_tokens  # আপনার existing FCM logic
import logging
from django.core.mail import EmailMessage
from django.conf import settings

logger = logging.getLogger(__name__)

@shared_task(name="send_fcm_notification")
def send_fcm_notification_task(user_id, title, body, data=None):
    """
    ইউজারের সব ডিভাইসে পুশ নটিফিকেশন পাঠানোর ব্যাকগ্রাউন্ড টাস্ক।
    """
    try:
        user = User.objects.get(id=user_id)
        tokens = list(user.device_tokens.values_list('token', flat=True))
        
        if not tokens:
            return f"No tokens found for user {user.email}"

        # FCM এর মাধ্যমে নটিফিকেশন পাঠানো
        response = send_push_to_tokens(tokens, title, body, data)
        return f"Push sent to {len(tokens)} devices for {user.email}"
        
    except User.DoesNotExist:
        return f"User with id {user_id} not found"
    except Exception as e:
        logger.error(f"FCM Task Error: {str(e)}")
        return str(e)
    

@shared_task(name="send_email_task")
def send_email_task(subject, body, recipient_list, is_html=True):
    try:
        msg = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_list,
        )
        if is_html:
            msg.content_subtype = "html"
        msg.send()
        return f"Email sent to {recipient_list}"
    except Exception as e:
        return f"Email failed: {str(e)}"
    

@shared_task(name="send_otp_email")
def send_otp_email_task(user_email, otp):
    from django.template.loader import render_to_string
    subject = 'Your OTP Code - Verify Your Account'
    html_content = render_to_string('send_code.html', {'otp': otp, 'user': {'email': user_email}})
    
    msg = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user_email],
    )
    msg.content_subtype = "html"
    msg.send()
    return f"OTP email sent to {user_email}"