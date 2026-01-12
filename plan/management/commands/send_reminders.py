from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail

from plan.models import Reminder, Notification


class Command(BaseCommand):
    help = 'Send due reminders (email + in-app notification)'

    def handle(self, *args, **options):
        now = timezone.now()
        reminders = Reminder.objects.filter(sent=False, send_at__lte=now)
        sent_count = 0

        for r in reminders:
            user = r.created_for
            try:
                title = f"Reminder: {r.content_object}"
            except Exception:
                title = "Reminder"

            try:
                message = f"You have a reminder for {r.content_object}."
            except Exception:
                message = "You have a reminder."

            # send email
            if r.method_email and getattr(user, 'email', None):
                try:
                    send_mail(
                        title,
                        message,
                        getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com'),
                        [user.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    # log and continue -- don't block other reminders
                    self.stdout.write(self.style.WARNING(f"Failed sending email to {user.email}: {e}"))

            # create in-app notification
            if r.method_notification:
                try:
                    Notification.objects.create(user=user, title=title, message=message)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Failed creating notification for {user}: {e}"))

            r.sent = True
            r.sent_at = now
            r.save()
            sent_count += 1

        self.stdout.write(self.style.SUCCESS(f"Processed {sent_count} reminders"))
