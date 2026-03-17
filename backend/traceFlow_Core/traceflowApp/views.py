from django.db.models import Count
import logging
from datetime import timedelta  
from django.utils import timezone  
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.db.models import Q
from .models import Trace
from .serializers import TraceSerializer
from .permissions import IsAuditor, IsAdmin, IsAuditorOrAdmin

logger = logging.getLogger(__name__)

class HealthCheckView(APIView):
    """Endpoint para verificar el estado del servicio."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'status': 'ok', 'database': 'connected'}, status=status.HTTP_200_OK)

class TraceListView(APIView):
    """
    Lista y filtra trazas. Accesible para roles Auditor y Admin.
    """
    permission_classes = [IsAuthenticated, IsAuditorOrAdmin]  # Usa el permiso compuesto

    def get(self, request):
        trace_id = request.query_params.get('trace_id')
        service = request.query_params.get('service')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        limit = int(request.query_params.get('limit', 100))

        queryset = Trace.objects.all()

        if trace_id:
            queryset = queryset.filter(trace_id=trace_id)
        if service:
            # Filtrar dentro del campo JSON
            queryset = queryset.filter(data__service_name=service)
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])

        queryset = queryset.order_by('-created_at')[:limit]
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
        
        # Obtener servicios únicos (sin duplicados)
        service_names = Trace.objects.exclude(data__service_name__isnull=True) \
                                      .values_list('data__service_name', flat=True)
        unique_services = list(set(service_names))
        
        return Response({
            'total_traces': total_traces,
            'traces_last_hour': traces_last_hour,
            'services': unique_services,
        })
    
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