import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
# IMPORTANT: Use your actual project settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_backend_graphql_crm.settings')

# Create a Celery app instance
app = Celery('crm')

# Load Celery settings from Django settings.py, using the CELERY_ namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps (looks for tasks.py files)
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    """
    Simple debug task to verify Celery is working.
    Run with: celery -A crm worker -l info
    """
    print(f"Request: {self.request!r}")
