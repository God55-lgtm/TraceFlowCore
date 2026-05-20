from django.db.models import Count
import logging
from datetime import timedelta  
from django.utils import timezone  
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.db.models import Q
from .models import Trace, TraceHash
from .serializers import TraceSerializer
from .permissions import IsAuditor, IsAdmin, IsAuditorOrAdmin
from django.db import connections
from django.db.utils import OperationalError
from datetime import datetime
from django.http import JsonResponse
from django.db import connection
from .utils import get_or_create_trace_hash, compute_trace_hash
import psutil


logger = logging.getLogger(__name__)

class HealthCheckView(APIView):
    """Endpoint para verificar el estado del servicio y conexión a BD."""
    permission_classes = [AllowAny]

    def get(self, request):
        db_connected = False
        try:
            # Intenta obtener un cursor de la base de datos por defecto
            connections['default'].cursor()
            db_connected = True
        except OperationalError:
            db_connected = False

        status_code = status.HTTP_200_OK if db_connected else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response({
            'status': 'ok' if db_connected else 'degraded',
            'database': 'connected' if db_connected else 'disconnected',
            'component': 'TraceFlowCore',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }, status=status_code)

class TraceListView(APIView):
    """
    Lista y filtra trazas. Accesible para roles Auditor y Admin.
    Si se pasa ?export=true, devuelve TODAS las trazas (sin límite) como archivo JSON descargable.
    """
    permission_classes = [IsAuthenticated, IsAuditorOrAdmin]

    def get(self, request):
        # Parámetros de filtrado
        trace_id = request.query_params.get('trace_id')
        service = request.query_params.get('service')
        client_ip = request.query_params.get('client_ip')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        limit = request.query_params.get('limit', 100)
        export = request.query_params.get('export', 'false').lower() == 'true'

        queryset = Trace.objects.all()

        # Filtros
        if trace_id:
            queryset = queryset.filter(trace_id=trace_id)
        if service:
            queryset = queryset.filter(data__service_name=service)
        if client_ip:
            queryset = queryset.filter(data__client_ip=client_ip)
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])

        # Orden descendente por fecha de creación
        queryset = queryset.order_by('-created_at')

        if export:
            # --- MODO EXPORTACIÓN: SIN LÍMITE, DEVUELVE JSON DESCARGABLE ---
            serializer = TraceSerializer(queryset, many=True)
            # Usamos JsonResponse con indent para legibilidad
            response = JsonResponse(serializer.data, safe=False, json_dumps_params={'indent': 2})
            # Forzar descarga como archivo .json
            filename = f"traces_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            # --- MODO NORMAL: RESPETA EL LÍMITE ---
            limit_int = int(limit)
            queryset = queryset[:limit_int]
            serializer = TraceSerializer(queryset, many=True)
            return Response(serializer.data)

class TraceDetailView(APIView):
    """
    Devuelve todos los spans de una traza específica (por traceId).
    """
    permission_classes = [IsAuthenticated, IsAuditorOrAdmin]

    def get(self, request, trace_id):
        traces = Trace.objects.filter(trace_id=trace_id).order_by('created_at')
        if not traces.exists():
            return Response({'error': 'Traza no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        serializer = TraceSerializer(traces, many=True)
        return Response(serializer.data)

class MetricsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        total_traces = Trace.objects.count()
        traces_last_hour = Trace.objects.filter(created_at__gte=timezone.now() - timedelta(hours=1)).count()
        
        # Spans por segundo (última hora)
        spans_per_second = traces_last_hour / 3600.0 if traces_last_hour > 0 else 0
        
        # Uso de almacenamiento (tamaño de la tabla en PostgreSQL)
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT pg_total_relation_size(%s)
            """, [Trace._meta.db_table])
            storage_bytes = cursor.fetchone()[0] or 0
        storage_mb = storage_bytes / (1024 * 1024.0)
        
        # Servicios únicos (mejor usando distinct de Django)
        unique_services = Trace.objects.exclude(data__service_name__isnull=True) \
                                       .values_list('data__service_name', flat=True) \
                                       .distinct()
        
        return Response({
            'total_traces': total_traces,
            'traces_last_hour': traces_last_hour,
            'spans_per_second': round(spans_per_second, 2),
            'storage_used_mb': round(storage_mb, 2),
            'services': list(unique_services),
        })

class TraceHashView(APIView):
    permission_classes = [IsAuthenticated, IsAuditorOrAdmin]
    
    def get(self, request, trace_id):
        """Devuelve el hash de la traza (lo genera si no existe)."""
        try:
            hash_value = get_or_create_trace_hash(trace_id)
            return Response({'trace_id': trace_id, 'hash': hash_value})
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request, trace_id):
        """Verifica la integridad recalculando el hash y comparando."""
        stored_hash_obj = TraceHash.objects.filter(trace_id=trace_id).first()
        if not stored_hash_obj:
            return Response({'error': 'Hash not found for this trace'}, status=status.HTTP_404_NOT_FOUND)
        
        current_hash = compute_trace_hash(trace_id)
        if current_hash == stored_hash_obj.hash_sha256:
            return Response({'trace_id': trace_id, 'valid': True, 'message': 'Integrity verified'})
        else:
            return Response({'trace_id': trace_id, 'valid': False, 'message': 'Trace has been modified!'},
                            status=status.HTTP_409_CONFLICT)


class PurgeTracesView(APIView):
    """
    Elimina trazas anteriores a una fecha (solo admin).
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def delete(self, request):
        date = request.query_params.get('before')
        if not date:
            return Response({'error': 'Parámetro "before" requerido (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
        deleted = Trace.objects.filter(created_at__date__lt=date).delete()
        return Response({'deleted': deleted[0]})
    
class TracesPerServiceView(APIView):
    """
    Devuelve el número de trazas por servicio.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        from django.db.models import Count
        
        # Obtener todos los servicios con su conteo, excluyendo nulos
        services_data = Trace.objects.exclude(data__service_name__isnull=True) \
                                      .exclude(data__service_name='') \
                                      .values('data__service_name') \
                                      .annotate(count=Count('id')) \
                                      .order_by('-count')
        
        # Convertir a lista de diccionarios
        result = [{'name': item['data__service_name'], 'count': item['count']} 
                  for item in services_data]
        
        return Response(result)