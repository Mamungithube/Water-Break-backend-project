import random

def generate_otp():
    return str(random.randint(1000, 9999))



from django.core.mail import send_mail
from django.conf import settings

def send_join_request_email(coach, user, team):
    send_mail(
        subject="New Team Join Request",
        message=(
            f"{user.email} wants to join your team '{team.name}'.\n\n"
            "Please login to approve or reject the request."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[coach.email],
        fail_silently=False,
    )
