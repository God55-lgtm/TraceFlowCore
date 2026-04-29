import pytest
from django.test import RequestFactory
from traceflowApp.middleware import TraceFlowMiddleware
from traceflowApp.models import Trace

@pytest.mark.django_db
def test_middleware_generates_trace_id():
    factory = RequestFactory()
    request = factory.get("/test-path")
    middleware = TraceFlowMiddleware(lambda req: None)
    middleware.process_request(request)
    # Verifica que se generó el contexto
    assert hasattr(request, 'trace_context')
    assert len(request.trace_context['trace_id']) == 32
    assert len(request.trace_context['span_id']) == 16