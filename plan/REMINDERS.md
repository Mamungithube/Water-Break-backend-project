Reminder system — run & schedule
================================

Quick start
-----------
- Send due reminders once immediately:

```bash
python manage.py send_reminders
```

Configuration
-------------
- `REMINDER_DEFAULT_OFFSET_MINUTES` (optional) — default lead time in minutes (default: 60).
- `DEFAULT_FROM_EMAIL` — used by `send_mail` when sending emails.

Scheduling
----------
1) Cron (Linux/macOS): run every 5 minutes

```cron
*/5 * * * * cd /path/to/project && /path/to/venv/bin/python manage.py send_reminders
```

2) Windows Task Scheduler: create a task to run the same `python manage.py send_reminders` on a schedule.

3) Recommended: use Celery + Celery Beat for robust scheduling. Example beat task (periodic):

```python
from celery import shared_task
from django.core.management import call_command

@shared_task
def send_reminders_task():
    call_command('send_reminders')
```

Notes & next improvements
------------------------
- The management command uses Django `send_mail` — ensure email backend and `DEFAULT_FROM_EMAIL` are configured.
- Consider adding templated email content and retry/backoff for transient email failures.
- Optionally expose `Reminder` / `Notification` in admin or API for inspection and manual resend.

Files
-----
- Reminder models and signals: [plan/models.py](plan/models.py)
- Management command: [plan/management/commands/send_reminders.py](plan/management/commands/send_reminders.py)
