import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'water_break.settings')

app = Celery('water_break')

# read broker URL from settings via env
app.config_from_object('django.conf:settings', namespace='CELERY')

# autodiscover tasks from installed apps
# app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
