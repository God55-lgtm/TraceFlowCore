import hashlib
import json
from .models import Trace, TraceHash

def compute_trace_hash(trace_id: str) -> str:
    """Calcula SHA-256 de la representación canónica de todos los spans de una traza."""
    spans = Trace.objects.filter(trace_id=trace_id).order_by('created_at', 'span_id')
    if not spans:
        raise ValueError(f"No spans found for trace_id {trace_id}")
    
    # Convertir cada span a un dict ordenado
    spans_data = []
    for span in spans:
        span_dict = {
            'span_id': span.span_id,
            'parent_span_id': span.parent_span_id,
            'data': span.data,  # ya es un dict
            'created_at': span.created_at.isoformat()
        }
        spans_data.append(span_dict)
    
    # Serializar a JSON canónico (ordenado, sin espacios)
    canonical = json.dumps(spans_data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()

def get_or_create_trace_hash(trace_id: str) -> str:
    """Obtiene el hash existente o lo calcula y guarda."""
    hash_obj, created = TraceHash.objects.get_or_create(trace_id=trace_id)
    if created:
        hash_obj.hash_sha256 = compute_trace_hash(trace_id)
        hash_obj.save()
    return hash_obj.hash_sha256