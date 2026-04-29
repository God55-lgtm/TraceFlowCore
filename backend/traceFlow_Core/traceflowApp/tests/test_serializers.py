import pytest
from traceflowApp.models import Trace
from traceflowApp.serializers import TraceSerializer

@pytest.mark.django_db
def test_trace_serializer():
    trace = Trace.objects.create(
        trace_id="abc123",
        span_id="span456",
        parent_span_id=None,
        data={"service_name": "mi-servicio", "duration_ms": 200, "status_code": 200, "client_ip": "192.168.1.1"}
    )
    serializer = TraceSerializer(trace)
    data = serializer.data
    assert data["trace_id"] == "abc123"
    assert data["service"] == "mi-servicio"
    assert data["duration_ms"] == 200
    assert data["status_code"] == 200
    assert data["client_ip"] == "192.168.1.1"