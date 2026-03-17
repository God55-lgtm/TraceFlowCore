from celery import shared_task
import logging
import json
from django.db import transaction
from .models import Trace

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=5, default_retry_delay=10)
def record_span_task(self, span_data):
    """
    Tarea Celery que guarda un span en PostgreSQL.
    Con reintentos en caso de error.
    """
    try:
        with transaction.atomic():
            Trace.objects.create(
                trace_id=span_data['trace_id'],
                span_id=span_data['span_id'],
                parent_span_id=span_data.get('parent_span_id'),
                data=span_data
            )
    except Exception as exc:
        logger.warning(f"Error guardando span, reintentando: {exc}")
        self.retry(exc=exc)