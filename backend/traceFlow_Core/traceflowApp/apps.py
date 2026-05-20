from django.apps import AppConfig
import threading

class TraceflowConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'traceflowApp'

def ready(self):
        # Inicializar buffer SQLite
        from .buffer import init_buffer_db, start_buffer_replay_worker
        init_buffer_db()
        # Lanzar worker en un hilo (solo si no estamos en migraciones)
        import os
        if os.environ.get('RUN_MAIN') or not os.environ.get('DJANGO_AUTORELOAD'):
            start_buffer_replay_worker(interval=10)