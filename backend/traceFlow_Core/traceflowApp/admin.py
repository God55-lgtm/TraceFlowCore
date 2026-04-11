from django.contrib import admin
from .models import Trace

@admin.register(Trace)
class TraceAdmin(admin.ModelAdmin):
    list_display = ('trace_id', 'span_id', 'get_client_ip', 'created_at')
    search_fields = ('trace_id', 'span_id', 'data__client_ip')  # permite buscar por IP dentro del JSON
    list_filter = ('created_at',)

    def get_client_ip(self, obj):
        """Extrae la IP del cliente del campo data (JSON)."""
        return obj.data.get('client_ip', '—')
    get_client_ip.short_description = 'IP Cliente'