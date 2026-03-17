import os
import uuid
import time
import random
import asyncio
import json
import httpx
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncpg

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:12345@localhost/traceflow_db")
SERVICE_NAME = os.getenv("SERVICE_NAME", "notificacion-service")
SAMPLE_RATE = float(os.getenv("SAMPLE_RATE", "1.0"))
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8005"))

http_client = httpx.AsyncClient(timeout=10.0)
pg_pool = None

class NotificationRequest(BaseModel):
    user_id: int
    type: str
    data: Dict[str, Any]
    channels: Optional[List[str]] = None

class NotificationResponse(BaseModel):
    id: str
    user_id: int
    type: str
    status: str
    channels_sent: List[str]
    timestamp: float

# ------------------------------------------------------------
# Funciones de base de datos y trazabilidad
# ------------------------------------------------------------
async def init_db():
    global pg_pool
    pg_pool = await asyncpg.create_pool(DATABASE_URL)

async def close_db():
    if pg_pool:
        await pg_pool.close()

async def insert_span(span_data: dict):
    print(f"📝 [NOTIFICACION] Intentando insertar traza {span_data['trace_id']}...")
    try:
        async with pg_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO traces (trace_id, span_id, parent_span_id, data) VALUES ($1, $2, $3, $4::jsonb)",
                span_data["trace_id"],
                span_data["span_id"],
                span_data.get("parent_span_id"),
                json.dumps(span_data)
            )
        print("✅ [NOTIFICACION] Inserción exitosa")
    except Exception as e:
        print(f"❌ [NOTIFICACION] Error insertando traza: {e}")

def generate_trace_id():
    return uuid.uuid4().hex[:32]

def generate_span_id():
    return uuid.uuid4().hex[:16]

def should_sample():
    return random.random() < SAMPLE_RATE

def inject_trace_headers(trace_context: dict, headers: dict) -> dict:
    if trace_context:
        traceparent = f"00-{trace_context['trace_id']}-{trace_context['span_id']}-01"
        headers["traceparent"] = traceparent
        if trace_context.get("tracestate"):
            headers["tracestate"] = trace_context["tracestate"]
    return headers

# ------------------------------------------------------------
# Middleware de trazabilidad
# ------------------------------------------------------------
async def trace_middleware(request: Request, call_next):
    print(f"🔍 [NOTIFICACION] Middleware ejecutándose para {request.method} {request.url.path}")
    traceparent = request.headers.get("traceparent")
    tracestate = request.headers.get("tracestate")

    if traceparent and len(traceparent.split("-")) == 4:
        parts = traceparent.split("-")
        trace_id = parts[1]
        parent_span_id = parts[2]
        span_id = generate_span_id()
        trace_context = {
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "tracestate": tracestate
        }
    else:
        trace_context = {
            "trace_id": generate_trace_id(),
            "span_id": generate_span_id(),
            "parent_span_id": None,
            "tracestate": None
        }

    if not should_sample():
        return await call_next(request)

    request.state.trace_context = trace_context
    request.state.span_start = time.time()

    response = await call_next(request)

    duration = time.time() - request.state.span_start
    span_data = {
        "trace_id": trace_context["trace_id"],
        "span_id": trace_context["span_id"],
        "parent_span_id": trace_context.get("parent_span_id"),
        "service_name": SERVICE_NAME,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": int(duration * 1000),
        "user_id": None,
        "timestamp": time.time(),
        "tracestate": trace_context.get("tracestate"),
    }

    asyncio.create_task(insert_span(span_data))
    return response

# ------------------------------------------------------------
# Lifespan
# ------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print(f"✅ {SERVICE_NAME} iniciado en puerto {SERVICE_PORT}")
    task = asyncio.create_task(generate_notification_activity())
    yield
    task.cancel()
    await close_db()
    await http_client.aclose()

# ------------------------------------------------------------
# Crear aplicación
# ------------------------------------------------------------
app = FastAPI(title="Notificacion Microservicio", version="2.0", lifespan=lifespan)
app.middleware("http")(trace_middleware)

# ------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------
@app.post("/notify", response_model=NotificationResponse)
async def notify(request: Request, notification: NotificationRequest):
    user_id = notification.user_id
    notif_type = notification.type
    data = notification.data

    await asyncio.sleep(random.uniform(0.1, 0.3))

    if random.random() < 0.15:
        raise HTTPException(status_code=500, detail="Error simulado en notificación")

    notification_id = str(uuid.uuid4())
    print(f"📧 [NOTIFICACION] Enviada a usuario {user_id}: {notif_type} - {data}")

    return NotificationResponse(
        id=notification_id,
        user_id=user_id,
        type=notif_type,
        status="sent",
        channels_sent=["email"],
        timestamp=time.time()
    )

@app.get("/health")
async def health():
    return {"status": "ok", "service": SERVICE_NAME, "timestamp": time.time()}

# ------------------------------------------------------------
# Tarea de fondo para generar actividad automática
# ------------------------------------------------------------
async def generate_notification_activity():
    types = ["compra", "promocion", "alerta", "pago_recibido"]
    while True:
        await asyncio.sleep(18)
        action = random.choice(types)
        asyncio.create_task(simulate_notification(action))

async def simulate_notification(notif_type: str):
    user_id = random.randint(1, 5)
    data = {}
    if notif_type == "compra":
        data = {"name": f"Usuario{user_id}", "total": round(random.uniform(50, 500), 2)}
    elif notif_type == "promocion":
        data = {"product": f"Producto {random.randint(1,10)}", "discount": random.randint(10, 50)}
    elif notif_type == "alerta":
        data = {"ip": f"192.168.1.{random.randint(2,254)}", "location": random.choice(["Madrid", "Barcelona"])}
    elif notif_type == "pago_recibido":
        data = {"amount": round(random.uniform(10, 200), 2)}

    print(f"📧 [NOTIFICACION] Simulando {notif_type} para usuario {user_id}")
    async with httpx.AsyncClient(base_url=f"http://localhost:{SERVICE_PORT}") as client:
        try:
            await client.post("/notify", json={"user_id": user_id, "type": notif_type, "data": data})
        except Exception as e:
            print(f"⚠️ [NOTIFICACION] Error en simulación: {e}")

