from celery import shared_task
import logging
from django.db import transaction
from .models import Trace

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=5)
def record_span_task(self, span_data):
    try:
        with transaction.atomic():
            Trace.objects.create(
                trace_id=span_data['trace_id'],
                span_id=span_data['span_id'],
                parent_span_id=span_data.get('parent_span_id'),
                data=span_data
            )
    except Exception as exc:
        # Backoff exponencial: 2^retry_count segundos (2,4,8,16,32)
        countdown = 2 ** self.request.retries
        logger.warning(f"Error guardando span, reintento {self.request.retries+1}/5 en {countdown}s: {exc}")
        self.retry(exc=exc, countdown=countdown)