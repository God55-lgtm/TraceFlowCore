from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.HealthCheckView.as_view(), name='health'),
    path('traces/', views.TraceListView.as_view(), name='trace-list'),
    path('traces/<str:trace_id>/', views.TraceDetailView.as_view(), name='trace-detail'),
    path('metrics/', views.MetricsView.as_view(), name='metrics'),
    path('traces-per-service/', views.TracesPerServiceView.as_view(), name='traces-per-service'),
    path('purge/', views.PurgeTracesView.as_view(), name='purge'),
]