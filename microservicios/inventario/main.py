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
SERVICE_NAME = os.getenv("SERVICE_NAME", "inventario-service")
SAMPLE_RATE = float(os.getenv("SAMPLE_RATE", "1.0"))
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8004"))

http_client = httpx.AsyncClient(timeout=10.0)
pg_pool = None

inventory = {
    1: {"name": "MacBook Pro 14", "stock": 10, "price": 1999.99, "category": "Electrónica", "reserved": 0},
    2: {"name": "Auriculares Sony WH-1000XM5", "stock": 25, "price": 349.99, "category": "Electrónica", "reserved": 0},
    3: {"name": "Zapatillas Nike Air Max", "stock": 50, "price": 129.99, "category": "Ropa", "reserved": 0},
    4: {"name": "Libro 'Clean Code'", "stock": 100, "price": 45.50, "category": "Libros", "reserved": 0},
    5: {"name": "Samsung Galaxy S23", "stock": 15, "price": 899.99, "category": "Electrónica", "reserved": 0},
    6: {"name": "Camiseta polo Lacoste", "stock": 30, "price": 89.99, "category": "Ropa", "reserved": 0},
    7: {"name": "Monitor Dell 27", "stock": 8, "price": 329.99, "category": "Electrónica", "reserved": 0},
    8: {"name": "Teclado mecánico Logitech", "stock": 20, "price": 119.99, "category": "Electrónica", "reserved": 0},
    9: {"name": "Mochila North Face", "stock": 40, "price": 79.99, "category": "Accesorios", "reserved": 0},
    10: {"name": "Tablet iPad Air", "stock": 12, "price": 599.99, "category": "Electrónica", "reserved": 0},
}

movement_log = []

class ReserveItem(BaseModel):
    product_id: int
    quantity: int

class ReserveRequest(BaseModel):
    items: List[ReserveItem]

class ReserveResponse(BaseModel):
    status: str
    reserved_items: List[dict]
    remaining_stock: Dict[int, int]

class StockUpdate(BaseModel):
    product_id: int
    new_stock: int
    reason: Optional[str] = None

class ProductCreate(BaseModel):
    name: str
    price: float
    stock: int
    category: str

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
        print(f"❌ [INVENTARIO] Error insertando traza: {e}")

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
    task = asyncio.create_task(generate_inventory_activity())
    yield
    task.cancel()
    await close_db()
    await http_client.aclose()

# ------------------------------------------------------------
# Crear aplicación
# ------------------------------------------------------------
app = FastAPI(title="Inventario Microservicio", version="2.0", lifespan=lifespan)
app.middleware("http")(trace_middleware)

# ------------------------------------------------------------
# Endpoints públicos
# ------------------------------------------------------------
@app.get("/stock")
async def get_all_stock():
    return {pid: {"name": data["name"], "stock": data["stock"], "reserved": data["reserved"]} for pid, data in inventory.items()}

@app.get("/stock/{product_id}")
async def get_stock(product_id: int):
    if product_id not in inventory:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"product_id": product_id, "name": inventory[product_id]["name"], "stock": inventory[product_id]["stock"], "reserved": inventory[product_id]["reserved"]}

# ------------------------------------------------------------
# Endpoints de reserva
# ------------------------------------------------------------
@app.post("/reserve", response_model=ReserveResponse)
async def reserve_items(request: Request, reserve_req: ReserveRequest):
    reserved_items = []

    for item in reserve_req.items:
        pid = item.product_id
        qty = item.quantity
        if pid not in inventory:
            raise HTTPException(status_code=404, detail=f"Producto {pid} no encontrado")
        if inventory[pid]["stock"] - inventory[pid]["reserved"] < qty:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente para producto {pid}")

    for item in reserve_req.items:
        pid = item.product_id
        qty = item.quantity
        inventory[pid]["reserved"] += qty
        reserved_items.append({"product_id": pid, "reserved": qty})
        movement_log.append({"type": "reserve", "product_id": pid, "quantity": qty, "timestamp": time.time()})

    remaining = {pid: inventory[pid]["stock"] - inventory[pid]["reserved"] for pid in inventory}
    return ReserveResponse(status="ok", reserved_items=reserved_items, remaining_stock=remaining)

@app.post("/confirm")
async def confirm_reservation(items: List[ReserveItem]):
    for item in items:
        pid = item.product_id
        qty = item.quantity
        if pid in inventory:
            inventory[pid]["stock"] -= qty
            inventory[pid]["reserved"] -= qty
            movement_log.append({"type": "sale", "product_id": pid, "quantity": qty, "timestamp": time.time()})
    return {"status": "confirmed"}

@app.post("/cancel")
async def cancel_reservation(items: List[ReserveItem]):
    for item in items:
        pid = item.product_id
        qty = item.quantity
        if pid in inventory:
            inventory[pid]["reserved"] -= qty
            movement_log.append({"type": "cancel", "product_id": pid, "quantity": qty, "timestamp": time.time()})
    return {"status": "cancelled"}

# ------------------------------------------------------------
# Endpoints de administración
# ------------------------------------------------------------
@app.post("/admin/products")
async def create_product(product: ProductCreate):
    new_id = max(inventory.keys()) + 1 if inventory else 1
    inventory[new_id] = {"name": product.name, "stock": product.stock, "price": product.price, "category": product.category, "reserved": 0}
    movement_log.append({"type": "create", "product_id": new_id, "timestamp": time.time()})
    return {"message": "Producto creado", "product_id": new_id}

@app.put("/admin/products/{product_id}/stock")
async def update_stock(update: StockUpdate):
    pid = update.product_id
    if pid not in inventory:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    old_stock = inventory[pid]["stock"]
    inventory[pid]["stock"] = update.new_stock
    movement_log.append({"type": "update", "product_id": pid, "old_stock": old_stock, "new_stock": update.new_stock, "reason": update.reason, "timestamp": time.time()})
    return {"message": "Stock actualizado"}

@app.get("/admin/movements")
async def get_movements(limit: int = 100):
    return movement_log[-limit:]

@app.get("/health")
async def health():
    return {"status": "ok", "service": SERVICE_NAME, "timestamp": time.time()}

# ------------------------------------------------------------
# Tarea de fondo para generar actividad automática
# ------------------------------------------------------------
async def generate_inventory_activity():
    actions = ["consulta_stock", "reserva_exitosa", "stock_insuficiente", "crear_producto", "actualizar_stock", "cancelar_reserva"]
    while True:
        await asyncio.sleep(25)
        action = random.choice(actions)
        asyncio.create_task(simulate_inventory(action))

async def simulate_inventory(action: str):
    product_id = random.randint(1, 10)
    quantity = random.randint(1, 5)

    print(f"📦 [INVENTARIO] Simulando {action} para producto {product_id}")

    async with httpx.AsyncClient(base_url=f"http://localhost:{SERVICE_PORT}") as client:
        try:
            if action == "consulta_stock":
                await client.get(f"/stock/{product_id}")
            elif action == "reserva_exitosa":
                await client.post("/reserve", json={"items": [{"product_id": product_id, "quantity": quantity}]})
            elif action == "stock_insuficiente":
                await client.post("/reserve", json={"items": [{"product_id": product_id, "quantity": 100}]})
            elif action == "crear_producto":
                new_product = {"name": f"Producto Test {random.randint(100,999)}", "price": round(random.uniform(10, 200), 2), "stock": random.randint(5, 50), "category": random.choice(["Electrónica", "Ropa", "Libros"])}
                await client.post("/admin/products", json=new_product)
            elif action == "actualizar_stock":
                new_stock = random.randint(10, 100)
                await client.put(f"/admin/products/{product_id}/stock", json={"product_id": product_id, "new_stock": new_stock})
            elif action == "cancelar_reserva":
                await client.post("/cancel", json=[{"product_id": product_id, "quantity": quantity}])
        except Exception as e:
            print(f"⚠️ [INVENTARIO] Error en simulación: {e}")

