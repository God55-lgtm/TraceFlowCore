from rest_framework import serializers
from .models import Trace

class TraceSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo Trace. 
    Expone los campos más relevantes y permite incluir atributos adicionales desde el campo JSON.
    """
    # Campos adicionales extraídos del JSON data (opcional)
    service = serializers.SerializerMethodField()
    duration_ms = serializers.SerializerMethodField()
    status_code = serializers.SerializerMethodField()
    client_ip = serializers.SerializerMethodField()

    class Meta:
        model = Trace
        fields = [
            'trace_id',
            'span_id',
            'parent_span_id',
            'service',
            'duration_ms',
            'status_code',
            'client_ip',
            'created_at',
            'data',
        ]
        read_only_fields = ['created_at']

    def get_service(self, obj):
        return obj.data.get('service_name', 'unknown')

    def get_duration_ms(self, obj):
        return obj.data.get('duration_ms', 0)

    def get_status_code(self, obj):
        return obj.data.get('status_code', 200)
    
    def get_client_ip(self, obj):
        return obj.data.get('client_ip', None)