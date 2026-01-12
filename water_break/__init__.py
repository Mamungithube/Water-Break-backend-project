
# Default Django settings module for the 'water_break' project.
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'water_break.settings')

# ensure celery app is loaded when Django starts
try:
	from .celery import app as celery_app  # noqa
except Exception:
	pass

