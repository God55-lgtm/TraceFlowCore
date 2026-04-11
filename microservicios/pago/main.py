import os
import uuid
import time
import random
import asyncio
import json
import httpx
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional, List, Dict
import asyncpg

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:12345@localhost/traceflow_db")
SERVICE_NAME = os.getenv("SERVICE_NAME", "pago-service")
SAMPLE_RATE = float(os.getenv("SAMPLE_RATE", "1.0"))
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8002"))

http_client = httpx.AsyncClient(timeout=10.0)
pg_pool = None

payment_methods = [
    {"id": 1, "type": "visa", "last4": "1234", "holder": "Ricardo Perez"},
    {"id": 2, "type": "mastercard", "last4": "5678", "holder": "Ana Garcia"},
    {"id": 3, "type": "amex", "last4": "9012", "holder": "Carlos Lopez"},
    {"id": 4, "type": "paypal", "email": "laura@email.com", "holder": "Laura Martin"},
]

balances = {1: 5000.0, 2: 1200.0, 3: 300.0, 4: 50.0, 5: 10000.0}
transactions = []

class PaymentRequest(BaseModel):
    amount: float
    user_id: int
    method: str = "card"
    card_last4: Optional[str] = None
    cvv: Optional[str] = None

class PaymentResponse(BaseModel):
    status: str
    transaction_id: str
    amount: float
    user_id: int
    method: str
    timestamp: float

def get_fake_ip_for_user(user_id: int = None) -> str:
    ip_map = {1: "192.168.1.10", 2: "192.168.1.20", 3: "192.168.1.30", 4: "192.168.1.40", 5: "192.168.1.50"}
    if user_id and user_id in ip_map:
        return ip_map[user_id]
    return f"192.168.1.{random.randint(2, 254)}"

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
    try:
        async with pg_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO traces (trace_id, span_id, parent_span_id, data) VALUES ($1, $2, $3, $4::jsonb)",
                span_data["trace_id"],
                span_data["span_id"],
                span_data.get("parent_span_id"),
                json.dumps(span_data)
            )
    except Exception as e:
        print(f"[ERROR] Error insertando traza: {e}")

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

    client_ip = request.headers.get("X-Forwarded-For")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = request.client.host

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
        "client_ip": client_ip,
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
    print(f"[OK] {SERVICE_NAME} iniciado en puerto {SERVICE_PORT}")
    task = asyncio.create_task(generate_payment_activity())
    yield
    task.cancel()
    await close_db()
    await http_client.aclose()

# ------------------------------------------------------------
# Crear aplicación
# ------------------------------------------------------------
app = FastAPI(title="Pago Microservicio", version="2.0", lifespan=lifespan)
app.middleware("http")(trace_middleware)

# ------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------
@app.post("/pay", response_model=PaymentResponse)
async def pay(request: Request, payment: PaymentRequest):
    await asyncio.sleep(random.uniform(0.1, 0.5))

    balance = balances.get(payment.user_id, 0)

    if payment.amount > 100 and random.random() < 0.3:
        raise HTTPException(status_code=402, detail="Saldo insuficiente")

    if random.random() < 0.2:
        raise HTTPException(status_code=502, detail="El banco rechazó la transacción")

    if random.random() < 0.1:
        await asyncio.sleep(5)
        raise HTTPException(status_code=504, detail="Timeout del gateway")

    transaction_id = str(uuid.uuid4())
    transactions.append({
        "id": transaction_id,
        "user_id": payment.user_id,
        "amount": payment.amount,
        "method": payment.method,
        "status": "completed",
        "timestamp": time.time()
    })

    return PaymentResponse(
        status="paid",
        transaction_id=transaction_id,
        amount=payment.amount,
        user_id=payment.user_id,
        method=payment.method,
        timestamp=time.time()
    )

@app.get("/methods")
async def get_payment_methods():
    return payment_methods

@app.get("/transactions/{user_id}")
async def get_user_transactions(user_id: int):
    return [t for t in transactions if t["user_id"] == user_id]

@app.post("/admin/balance/{user_id}")
async def adjust_balance(user_id: int, amount: float):
    balances[user_id] = balances.get(user_id, 0) + amount
    return {"message": "Saldo actualizado", "new_balance": balances[user_id]}

@app.get("/health")
async def health():
    return {"status": "ok", "service": SERVICE_NAME, "timestamp": time.time()}

# ------------------------------------------------------------
# Tarea de fondo para generar actividad automática
# ------------------------------------------------------------
async def generate_payment_activity():
    actions = ["pago_exitoso", "saldo_insuficiente", "error_banco", "timeout", "pago_rechazado"]
    while True:
        await asyncio.sleep(20)
        action = random.choice(actions)
        asyncio.create_task(simulate_payment(action))

async def simulate_payment(action: str):
    amount = round(random.uniform(10, 500), 2)
    user_id = random.randint(1, 5)
    method = random.choice(["visa", "mastercard", "paypal"])
    fake_ip = get_fake_ip_for_user(user_id)

    headers = {"X-Forwarded-For": fake_ip}

    print(f"[PAGO] Simulando {action} para usuario {user_id}, monto {amount} (IP {fake_ip})")

    async with httpx.AsyncClient(base_url=f"http://localhost:{SERVICE_PORT}") as client:
        try:
            if action == "pago_exitoso":
                await client.post("/pay", json={"amount": amount, "user_id": user_id, "method": method}, headers=headers)
            elif action == "saldo_insuficiente":
                await client.post("/pay", json={"amount": 10000, "user_id": user_id, "method": method}, headers=headers)
            elif action == "error_banco":
                await client.post("/pay", json={"amount": amount, "user_id": user_id, "method": "invalid"}, headers=headers)
            elif action == "timeout":
                await client.post("/pay", json={"amount": amount, "user_id": user_id, "method": method}, headers=headers)
            elif action == "pago_rechazado":
                await client.post("/pay", json={"amount": amount, "user_id": user_id, "method": method, "cvv": "000"}, headers=headers)
        except Exception as e:
            print(f"[WARN] Error en simulación: {e}")