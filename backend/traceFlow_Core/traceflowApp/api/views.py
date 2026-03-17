from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import Trace  # Modelo Django que mapea la tabla
from ..serializers import TraceSerializer

class TraceListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        trace_id = request.query_params.get('trace_id')
        service = request.query_params.get('service')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        # ... construir filtros
        traces = Trace.objects.filter(...).order_by('-created_at')[:100]
        serializer = TraceSerializer(traces, many=True)
        return Response(serializer.data)