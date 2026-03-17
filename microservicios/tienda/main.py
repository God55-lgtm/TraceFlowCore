import os
import uuid
import time
import random
import asyncio
import json
import bcrypt
import jwt
import httpx
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Depends, Header
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Any
import asyncpg

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:12345@localhost/traceflow_db")
SERVICE_NAME = os.getenv("SERVICE_NAME", "tienda-service")
SAMPLE_RATE = float(os.getenv("SAMPLE_RATE", "1.0"))
JWT_SECRET = os.getenv("JWT_SECRET", "mi-secreto-super-seguro-cambiar")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8001"))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8002")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8003")
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://localhost:8004")

http_client = httpx.AsyncClient(timeout=10.0)
pg_pool = None

products = [
    {"id": 1, "name": "MacBook Pro 14", "price": 1999.99, "stock": 10, "category": "Electrónica"},
    {"id": 2, "name": "Auriculares Sony WH-1000XM5", "price": 349.99, "stock": 25, "category": "Electrónica"},
    {"id": 3, "name": "Zapatillas Nike Air Max", "price": 129.99, "stock": 50, "category": "Ropa"},
    {"id": 4, "name": "Libro 'Clean Code'", "price": 45.50, "stock": 100, "category": "Libros"},
    {"id": 5, "name": "Samsung Galaxy S23", "price": 899.99, "stock": 15, "category": "Electrónica"},
    {"id": 6, "name": "Camiseta polo Lacoste", "price": 89.99, "stock": 30, "category": "Ropa"},
    {"id": 7, "name": "Monitor Dell 27", "price": 329.99, "stock": 8, "category": "Electrónica"},
    {"id": 8, "name": "Teclado mecánico Logitech", "price": 119.99, "stock": 20, "category": "Electrónica"},
    {"id": 9, "name": "Mochila North Face", "price": 79.99, "stock": 40, "category": "Accesorios"},
    {"id": 10, "name": "Tablet iPad Air", "price": 599.99, "stock": 12, "category": "Electrónica"},
]
products_by_id = {p["id"]: p for p in products}
next_product_id = max(p["id"] for p in products) + 1
carts: Dict[int, Dict[int, int]] = {}

login_attempts: Dict[str, List[float]] = {}
BLOCK_TIME = 300
MAX_ATTEMPTS = 5

default_users = [
    {"username": "ricardo.perez", "password": "Ricardo123!", "email": "ricardo@email.com"},
    {"username": "ana.garcia", "password": "AnaGarcia2024", "email": "ana.garcia@email.com"},
    {"username": "carlos.lopez", "password": "CarlosLopez99", "email": "carlos.l@email.com"},
    {"username": "laura.martin", "password": "LauraM2025", "email": "laura.m@email.com"},
    {"username": "jose.rodriguez", "password": "JoseR1234", "email": "jose.r@email.com"},
]

# Modelos
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    email: Optional[str] = None

    @validator('password')
    def validate_password(cls, v):
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Contraseña demasiado larga (max 72 bytes)')
        if not any(c.isupper() for c in v):
            raise ValueError('Debe contener mayúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('Debe contener número')
        if not any(c in '!@#$%^&*(),.?":{}|<>' for c in v):
            raise ValueError('Debe contener carácter especial')
        return v

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class CartItem(BaseModel):
    product_id: int
    quantity: int

class OrderRequest(BaseModel):
    payment_method: str = "card"
    card_last4: Optional[str] = None

class ProductCreate(BaseModel):
    name: str
    price: float
    stock: int
    category: str

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    category: Optional[str] = None

# ------------------------------------------------------------
# Funciones de base de datos
# ------------------------------------------------------------
async def init_db():
    global pg_pool
    pg_pool = await asyncpg.create_pool(DATABASE_URL)

    async with pg_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email VARCHAR(100),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                last_login TIMESTAMP WITH TIME ZONE
            )
        """)

        for user in default_users:
            exists = await conn.fetchval("SELECT COUNT(*) FROM users WHERE username = $1", user["username"])
            if exists == 0:
                password_hash = bcrypt.hashpw(user["password"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                await conn.execute(
                    "INSERT INTO users (username, password_hash, email) VALUES ($1, $2, $3)",
                    user["username"], password_hash, user["email"]
                )
                print(f"✅ Usuario '{user['username']}' creado")

async def close_db():
    if pg_pool:
        await pg_pool.close()

async def get_user_by_username(username: str) -> Optional[Dict]:
    async with pg_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id, username, password_hash, email FROM users WHERE username = $1", username)
        if row:
            return {"id": row["id"], "username": row["username"], "password_hash": row["password_hash"], "email": row["email"]}
        return None

async def create_user(username: str, password: str, email: Optional[str] = None) -> Optional[int]:
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    async with pg_pool.acquire() as conn:
        try:
            user_id = await conn.fetchval(
                "INSERT INTO users (username, password_hash, email) VALUES ($1, $2, $3) RETURNING id",
                username, password_hash, email
            )
            return user_id
        except asyncpg.UniqueViolationError:
            return None

async def update_last_login(user_id: int):
    async with pg_pool.acquire() as conn:
        await conn.execute("UPDATE users SET last_login = NOW() WHERE id = $1", user_id)

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
        print(f"❌ Error insertando traza: {e}")

# ------------------------------------------------------------
# Utilidades de trazabilidad
# ------------------------------------------------------------
def generate_trace_id() -> str:
    return uuid.uuid4().hex[:32]

def generate_span_id() -> str:
    return uuid.uuid4().hex[:16]

def should_sample() -> bool:
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
# Dependencia para usuario actual desde JWT
# ------------------------------------------------------------
async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado")
    token = authorization[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")
        return int(user_id)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

# ------------------------------------------------------------
# Funciones auxiliares para carrito y productos
# ------------------------------------------------------------
def _get_product(product_id: int):
    return products_by_id.get(product_id)

def _get_cart(user_id: int):
    cart = carts.get(user_id, {})
    items = []
    total = 0.0
    for pid, qty in cart.items():
        prod = products_by_id.get(pid)
        if prod:
            subtotal = prod["price"] * qty
            items.append({
                "product_id": pid,
                "name": prod["name"],
                "price": prod["price"],
                "quantity": qty,
                "subtotal": subtotal
            })
            total += subtotal
    return items, total

def _add_to_cart(user_id: int, product_id: int, quantity: int):
    if user_id not in carts:
        carts[user_id] = {}
    carts[user_id][product_id] = carts[user_id].get(product_id, 0) + quantity

def _clear_cart(user_id: int):
    if user_id in carts:
        del carts[user_id]


# ------------------------------------------------------------
# Lifespan
# ------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print(f"✅ {SERVICE_NAME} iniciado en puerto {SERVICE_PORT}")
    print(f"   Generando flujos automáticos cada 30 segundos")

    task = asyncio.create_task(generate_auto_flows())
    yield
    task.cancel()
    await close_db()
    await http_client.aclose()

# ------------------------------------------------------------
# Crear aplicación
# ------------------------------------------------------------
app = FastAPI(title="Tienda Microservicio", version="2.0", lifespan=lifespan)
app.middleware("http")(trace_middleware)

# ------------------------------------------------------------
# Endpoints de autenticación
# ------------------------------------------------------------
@app.post("/register", response_model=TokenResponse)
async def register(user: UserRegister):
    user_id = await create_user(user.username, user.password, user.email)
    if not user_id:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")

    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    token = jwt.encode({"sub": str(user_id), "exp": expire}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/login", response_model=TokenResponse)
async def login(request: Request, user: UserLogin):
    client_ip = request.client.host
    now = time.time()

    if client_ip in login_attempts:
        login_attempts[client_ip] = [t for t in login_attempts[client_ip] if now - t < BLOCK_TIME]
        if len(login_attempts[client_ip]) >= MAX_ATTEMPTS:
            raise HTTPException(status_code=429, detail="Demasiados intentos. IP bloqueada.")

    try:
        db_user = await get_user_by_username(user.username)

        if not db_user:
            login_attempts.setdefault(client_ip, []).append(now)
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

        password_valid = bcrypt.checkpw(user.password.encode('utf-8'), db_user["password_hash"].encode('utf-8'))

        if not password_valid:
            login_attempts.setdefault(client_ip, []).append(now)
            raise HTTPException(status_code=401, detail="Credenciales inválidas")

        if client_ip in login_attempts:
            del login_attempts[client_ip]

        await update_last_login(db_user["id"])

        expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
        token = jwt.encode({"sub": str(db_user["id"]), "exp": expire, "username": db_user["username"]}, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return {"access_token": token, "token_type": "bearer"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error en login: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# ------------------------------------------------------------
# Endpoints de productos
# ------------------------------------------------------------
@app.get("/products")
async def list_products(category: Optional[str] = None):
    if category:
        return [p for p in products if p["category"].lower() == category.lower()]
    return products

@app.get("/products/{product_id}")
async def get_product_detail(product_id: int):
    prod = _get_product(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return prod

# ------------------------------------------------------------
# Endpoints de gestión de inventario (admin)
# ------------------------------------------------------------
@app.post("/admin/products", status_code=201)
async def create_product(product: ProductCreate, user_id: int = Depends(get_current_user)):
    global next_product_id
    new_id = next_product_id
    new_product = {
        "id": new_id,
        "name": product.name,
        "price": product.price,
        "stock": product.stock,
        "category": product.category
    }
    products.append(new_product)
    products_by_id[new_id] = new_product
    next_product_id += 1
    return {"message": "Producto creado", "product": new_product}

@app.put("/admin/products/{product_id}")
async def update_product(product_id: int, update: ProductUpdate, user_id: int = Depends(get_current_user)):
    prod = _get_product(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if update.name is not None:
        prod["name"] = update.name
    if update.price is not None:
        prod["price"] = update.price
    if update.stock is not None:
        prod["stock"] = update.stock
    if update.category is not None:
        prod["category"] = update.category
    return {"message": "Producto actualizado", "product": prod}

@app.delete("/admin/products/{product_id}")
async def delete_product(product_id: int, user_id: int = Depends(get_current_user)):
    global products, products_by_id
    prod = _get_product(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    products = [p for p in products if p["id"] != product_id]
    del products_by_id[product_id]
    return {"message": "Producto eliminado"}

# ------------------------------------------------------------
# Endpoints de carrito
# ------------------------------------------------------------
@app.post("/cart/add")
async def add_to_cart_endpoint(item: CartItem, user_id: int = Depends(get_current_user)):
    product = _get_product(item.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if product["stock"] < item.quantity:
        raise HTTPException(status_code=400, detail="Stock insuficiente")
    _add_to_cart(user_id, item.product_id, item.quantity)
    return {"message": "Producto agregado al carrito"}

@app.get("/cart")
async def view_cart(user_id: int = Depends(get_current_user)):
    items, total = _get_cart(user_id)
    return {"items": items, "total": total}

@app.post("/checkout")
async def checkout(request: Request, order: OrderRequest, user_id: int = Depends(get_current_user)):
    items, total = _get_cart(user_id)
    if not items:
        raise HTTPException(status_code=400, detail="Carrito vacío")

    trace_ctx = getattr(request.state, "trace_context", None)
    headers = {}
    if trace_ctx:
        inject_trace_headers(trace_ctx, headers)

    results = {}
    security_alert = None

    if random.random() < 0.3:
        security_alert = "saldo_insuficiente"
        raise HTTPException(status_code=402, detail="Saldo insuficiente")

    if random.random() < 0.2:
        security_alert = "error_pago"
        raise HTTPException(status_code=502, detail="Error en el servicio de pago")

    try:
        if INVENTORY_SERVICE_URL:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{INVENTORY_SERVICE_URL}/reserve", json={"items": items}, headers=headers)
                resp.raise_for_status()
                results["inventory"] = resp.json()
    except Exception as e:
        print(f"Error en inventario: {e}")
        results["inventory"] = {"status": "error", "detail": str(e)}

    try:
        if PAYMENT_SERVICE_URL:
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{PAYMENT_SERVICE_URL}/pay", json={"amount": total, "user_id": user_id, "method": order.payment_method}, headers=headers)
                resp.raise_for_status()
                results["payment"] = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error en pago: {str(e)}")

    try:
        if NOTIFICATION_SERVICE_URL:
            async with httpx.AsyncClient() as client:
                await client.post(f"{NOTIFICATION_SERVICE_URL}/notify", json={"user_id": user_id, "message": "Compra realizada", "total": total, "items": [{"name": it["name"], "qty": it["quantity"]} for it in items]}, headers=headers)
                results["notification"] = {"status": "sent"}
    except Exception as e:
        print(f"Error notificando: {e}")
        results["notification"] = {"status": "error", "detail": str(e)}

    _clear_cart(user_id)
    order_id = random.randint(1000, 9999)

    return {"order_id": order_id, "total": total, "status": "completed", "services_results": results, "security_alert": security_alert}

# ------------------------------------------------------------
# Endpoint para simular ataques de seguridad
# ------------------------------------------------------------
@app.get("/simulate/sql-injection")
async def simulate_sql_injection(request: Request):
    client_ip = request.client.host
    suspicious_param = request.query_params.get("id", "")
    if "'" in suspicious_param or ";" in suspicious_param or "--" in suspicious_param:
        security_alert = {"type": "sql_injection_attempt", "ip": client_ip, "payload": suspicious_param, "timestamp": time.time()}
        asyncio.create_task(insert_span({"trace_id": generate_trace_id(), "span_id": generate_span_id(), "parent_span_id": None, "service_name": SERVICE_NAME, "method": "GET", "path": "/simulate/sql-injection", "status_code": 400, "duration_ms": 10, "user_id": None, "timestamp": time.time(), "security_alert": security_alert}))
        raise HTTPException(status_code=400, detail="Solicitud maliciosa detectada")
    return {"message": "Parámetro seguro"}

# ------------------------------------------------------------
# Endpoints para otros servicios (simulados)
# ------------------------------------------------------------
@app.post("/pay")
async def pay_endpoint(request: Request):
    data = await request.json()
    amount = data.get("amount")
    user_id = data.get("user_id")
    method = data.get("method", "card")

    await asyncio.sleep(random.uniform(0.1, 0.5))

    if random.random() < 0.2:
        raise HTTPException(status_code=500, detail="Error procesando pago")

    return {"status": "paid", "transaction_id": str(uuid.uuid4()), "amount": amount, "user_id": user_id, "method": method}

@app.post("/notify")
async def notify_endpoint(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    message = data.get("message")
    total = data.get("total")
    items = data.get("items", [])

    print(f"📧 Notificación enviada al usuario {user_id}: {message} (total: {total})")
    for it in items:
        print(f"   - {it['name']} x{it['qty']}")

    if random.random() < 0.15:
        raise HTTPException(status_code=500, detail="Error enviando notificación")

    return {"status": "sent", "notification_id": str(uuid.uuid4())}

@app.post("/reserve")
async def reserve_endpoint(request: Request):
    data = await request.json()
    items = data.get("items", [])

    for item in items:
        product_id = item.get("product_id")
        quantity = item.get("quantity", 0)
        product = _get_product(product_id)
        if not product or product["stock"] < quantity:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente para producto {product_id}")

    return {"status": "reserved", "items": items}

@app.get("/error")
async def error_endpoint():
    raise RuntimeError("Error simulado para probar trazas")

@app.get("/health")
async def health():
    return {"status": "ok", "service": SERVICE_NAME, "timestamp": time.time()}

# ------------------------------------------------------------
# Tarea de fondo para generar flujos automáticos
# ------------------------------------------------------------
async def generate_auto_flows():
    users_list = ["ricardo.perez", "ana.garcia", "carlos.lopez", "laura.martin", "jose.rodriguez"]
    flow_types = ["compra_exitosa", "saldo_insuficiente", "stock_insuficiente", "error_pago", "intentos_fallidos"]

    while True:
        await asyncio.sleep(30)
        username = random.choice(users_list)
        flow = random.choice(flow_types)
        print(f"🔄 Generando flujo automático: {username} - {flow}")
        tasks = []
        tasks.append(generate_flow(username, flow))
        await asyncio.gather(*tasks, return_exceptions=True)

async def generate_flow(username: str, flow_type: str):
    base_url = f"http://localhost:{SERVICE_PORT}"
    headers = {}

    async with httpx.AsyncClient(base_url=base_url) as client:
        try:
            # Intentos de login
            await client.post("/login", json={"username": username, "password": "wrong"})

            if username == "ricardo.perez":
                pwd = "Ricardo123!"
            elif username == "ana.garcia":
                pwd = "AnaGarcia2024"
            elif username == "carlos.lopez":
                pwd = "CarlosLopez99"
            elif username == "laura.martin":
                pwd = "LauraM2025"
            else:
                pwd = "JoseR1234"

            login_resp = await client.post("/login", json={"username": username, "password": pwd})
            if login_resp.status_code != 200:
                print(f"❌ Error login en flujo automático: {login_resp.status_code}")
                return
            token = login_resp.json().get("access_token")
            headers["Authorization"] = f"Bearer {token}"

            await client.get("/products", headers=headers)

            num_items = random.randint(1, 3)
            for _ in range(num_items):
                prod_id = random.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
                qty = random.randint(1, 2)
                await client.post("/cart/add", json={"product_id": prod_id, "quantity": qty}, headers=headers)

            await client.get("/cart", headers=headers)

            if flow_type == "saldo_insuficiente":
                await client.post("/checkout", json={"payment_method": "card"}, headers=headers)
            elif flow_type == "stock_insuficiente":
                prod = random.choice([1, 2, 3])
                await client.post("/cart/add", json={"product_id": prod, "quantity": 100}, headers=headers)
                await client.post("/checkout", json={}, headers=headers)
            elif flow_type == "error_pago":
                await client.post("/checkout", json={}, headers=headers)
            else:
                await client.post("/checkout", json={}, headers=headers)

            headers.pop("Authorization", None)

        except Exception as e:
            print(f"Error en flujo automático: {e}")

