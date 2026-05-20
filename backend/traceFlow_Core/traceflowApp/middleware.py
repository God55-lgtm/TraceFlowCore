import uuid
import time
import logging
import random
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from .models import Trace
from . import context   # Importa el módulo para atributos personalizados

logger = logging.getLogger(__name__)

class TraceFlowMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Extraer traceparent y tracestate de cabeceras
        traceparent = request.headers.get('traceparent')
        tracestate = request.headers.get('tracestate')

        if traceparent:
            # Formato: version-traceId-spanId-flags
            parts = traceparent.split('-')
            if len(parts) == 4:
                trace_id = parts[1]
                parent_span_id = parts[2]
                # Crear nuevo span hijo
                span_id = self.generate_span_id()
                request.trace_context = {
                    'trace_id': trace_id,
                    'span_id': span_id,
                    'parent_span_id': parent_span_id,
                    'tracestate': tracestate
                }
            else:
                # Formato inválido, generar nuevo
                self.start_new_trace(request)
        else:
            self.start_new_trace(request)

        # Decidir si muestrear según tasa configurada
        request.should_sample = self.should_sample()
        if not request.should_sample:
            # Si no se muestrea, no hacemos nada más
            return

        # Inicializar atributos personalizados para este span
        context.clear_attributes()

        # Almacenar tiempo de inicio
        request._trace_start_time = time.time()

    def process_response(self, request, response):
        if hasattr(request, '_trace_start_time') and request.should_sample:
            duration = time.time() - request._trace_start_time
            # Guardar span directamente en BD (o enviar a Celery)
            self.record_span_direct(request, response, duration)
        # Limpiar atributos después de procesar la respuesta (por si acaso)
        context.clear_attributes()
        return response

    def start_new_trace(self, request):
        trace_id = self.generate_trace_id()
        span_id = self.generate_span_id()
        request.trace_context = {
            'trace_id': trace_id,
            'span_id': span_id,
            'parent_span_id': None,
            'tracestate': None
        }

    def generate_trace_id(self):
        return uuid.uuid4().hex[:32]

    def generate_span_id(self):
        return uuid.uuid4().hex[:16]

    def should_sample(self):
        sample_rate = getattr(settings, 'TRACE_SAMPLE_RATE', 1.0)
        return random.random() < sample_rate

    def record_span_direct(self, request, response, duration):
        """
        Guarda el span directamente en la base de datos (sin Celery).
        Para usar SOLO en desarrollo/pruebas.
        """
        # Obtener atributos personalizados desde el contexto
        custom_attrs = context.get_attributes()

        # Construir datos del span (incluyendo los personalizados)
        span_data = {
            'trace_id': request.trace_context['trace_id'],
            'span_id': request.trace_context['span_id'],
            'parent_span_id': request.trace_context['parent_span_id'],
            'service_name': request.META.get('SERVER_NAME', 'unknown'),
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'duration_ms': int(duration * 1000),
            'user_id': request.user.id if request.user.is_authenticated else None,
            'timestamp': time.time(),
            'tracestate': request.trace_context.get('tracestate'),
        }
        # Añadir todos los atributos personalizados al diccionario
        span_data.update(custom_attrs)

        try:
            Trace.objects.create(...)
            logger.debug(f"Span guardado directamente en BD: {span_data['trace_id']}")
        except Exception as e:
            logger.error(f"Error guardando span en BD: {e}, guardando en buffer local")
            from .buffer import save_to_buffer
            save_to_buffer(span_data)