from django.contrib import admin
from .models import Trace

@admin.register(Trace)
class TraceAdmin(admin.ModelAdmin):
    list_display = ('trace_id', 'span_id', 'created_at')
    search_fields = ('trace_id',)
    list_filter = ('created_at',)