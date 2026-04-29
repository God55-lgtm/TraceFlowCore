import pytest
from django.utils import timezone
from traceflowApp.models import Trace

@pytest.mark.django_db
def test_trace_creation():
    trace = Trace.objects.create(
        trace_id="abc123",
        span_id="span456",
        parent_span_id=None,
        data={"service_name": "test", "duration_ms": 100},
        created_at=timezone.now()
    )
    assert trace.trace_id == "abc123"
    assert trace.span_id == "span456"
    assert trace.data["service_name"] == "test"