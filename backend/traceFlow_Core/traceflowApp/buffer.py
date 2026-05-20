# traceflowApp/buffer.py
import sqlite3
import json
import logging
import threading
import time
from django.conf import settings
from django.db import connections, OperationalError
from .models import Trace

logger = logging.getLogger(__name__)

DB_PATH = settings.BASE_DIR / 'trace_buffer.sqlite3'

def init_buffer_db():
    """Crea la tabla buffer si no existe."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS span_buffer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            span_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_to_buffer(span_data):
    """Guarda un span en el buffer local (SQLite)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO span_buffer (span_data) VALUES (?)', (json.dumps(span_data),))
        conn.commit()
        conn.close()
        logger.warning(f"Span guardado en buffer local (PostgreSQL no disponible). Trace: {span_data.get('trace_id')}")
    except Exception as e:
        logger.error(f"Error guardando span en buffer local: {e}")

def replay_buffer():
    """Intenta reenviar todos los spans del buffer a PostgreSQL."""
    if not is_postgres_available():
        return 0
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, span_data FROM span_buffer ORDER BY created_at')
    rows = cursor.fetchall()
    success_count = 0
    for row_id, span_data_json in rows:
        span_data = json.loads(span_data_json)
        try:
            Trace.objects.create(
                trace_id=span_data['trace_id'],
                span_id=span_data['span_id'],
                parent_span_id=span_data.get('parent_span_id'),
                data=span_data
            )
            cursor.execute('DELETE FROM span_buffer WHERE id = ?', (row_id,))
            conn.commit()
            success_count += 1
            logger.info(f"Span reenviado desde buffer: {span_data['trace_id']}")
        except Exception as e:
            logger.error(f"Error reenviando span desde buffer: {e}")
    conn.close()
    return success_count

def is_postgres_available():
    """Verifica si PostgreSQL está disponible."""
    try:
        connections['default'].cursor()
        return True
    except OperationalError:
        return False

def start_buffer_replay_worker(interval=10, max_interval=60):
    def worker():
        current_interval = interval
        while True:
            if is_postgres_available():
                replayed = replay_buffer()
                if replayed > 0:
                    logger.info(f"Reenviados {replayed} spans desde buffer")
                current_interval = interval  # reset tras éxito
            else:
                # PostgreSQL no disponible, incrementar intervalo (backoff)
                current_interval = min(current_interval * 2, max_interval)
                logger.debug(f"PostgreSQL no disponible, próximo reintento en {current_interval}s")
            time.sleep(current_interval)
    threading.Thread(target=worker, daemon=True).start()