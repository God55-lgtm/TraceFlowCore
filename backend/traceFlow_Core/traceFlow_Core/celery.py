import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'traceFlow_Core.settings')

app = Celery('traceFlow_Core')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()