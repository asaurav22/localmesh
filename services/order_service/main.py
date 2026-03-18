import os
import logging
import asyncio
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from services.order_service.models import Order

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://localhost:7000")
SIDECAR_URL = os.getenv("SIDECAR_URL", "http://localhost:8001")
SERVICE_NAME = os.getenv("SERVICE_NAME", "order-service")
SERVICE_HOST = os.getenv("SERVICE_HOST", "127.0.0.1")
SERVICE_PORT = os.getenv("SERVICE_PORT", "9001")


current_version: int = 0


async def register_with_control_plane():
    global current_version
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{CONTROL_PLANE_URL}/registry/register",
                json={
                    "service_name": SERVICE_NAME,
                    "host": SERVICE_HOST,
                    "port": SERVICE_PORT,
                    "ttl": 30,
                    "expected_version": current_version
                }
            )
            response.raise_for_status()
            data = response.json()
            current_version = data["version"]
            logger.info(f"[STARTUP] Registered '{SERVICE_NAME}' successfully - version {current_version}")
        except Exception as e:
            logger.error(f"[STARTUP] Failed to register with control plane: {e}")


async def heartbeat():
    """Re-register with control plane every 20s to prevent TTL eviction."""
    global current_version
    async with httpx.AsyncClient() as client:
        while True:
            await asyncio.sleep(20)
            try:
                response = await client.post(
                    f"{CONTROL_PLANE_URL}/registry/register",
                    json={
                        "service_name": SERVICE_NAME,
                        "host": SERVICE_HOST,
                        "port": SERVICE_PORT,
                        "ttl": 30,
                        "expected_version": current_version
                    }
                )
                response.raise_for_status()
                data = response.json()
                current_version = data["version"]
                logger.info(f"[HEARTBEAT] Renewed '{SERVICE_NAME}' - version {current_version}")
            except Exception as e:
                logger.error(f"[HEARTBEAT] Failed to renew: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await register_with_control_plane()
    asyncio.create_task(heartbeat())
    yield

app = FastAPI(title="Order Service", lifespan=lifespan)

ORDERS = [
    Order(id=1, item="Mechanical Keyboard", quantity=1, price=120.00, status="confirmed"),
    Order(id=2, item="USB-C Hub", quantity=2, price=35.00, status="shipped"),
    Order(id=3, item="Monitor Stand", quantity=1, price=45.00, status="delivered")
]


@app.get("/health")
def health(request: Request):
    corr_id = request.headers.get("x-correlation-id", "none")
    logger.info(f"[{corr_id}] [{SERVICE_NAME}] GET /health")
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/orders", response_model=list[Order])
def get_orders(request: Request):
    corr_id = request.headers.get("x-correlation-id", "none")
    logger.info(f"[{corr_id}] [{SERVICE_NAME}] GET /orders")
    return ORDERS


@app.get("/orders/create")
async def create_order(request: Request):
    """
    Calls payment-service via sidecar using logical name.
    No hardcoded ports - location transparent.
    """
    corr_id = request.headers.get("x-correlation-id", "none")
    logger.info(f"[{corr_id}] [{SERVICE_NAME}] GET /orders/create - calling payment-service via sidecar")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SIDECAR_URL}/payment-service/payments",
                timeout=5.0,
                headers={"x-correlation-id": corr_id}  # propagate downstream
            )
            response.raise_for_status()
            payments = response.json()
            logger.info(f"[{corr_id}] [{SERVICE_NAME}] Got {len(payments)} payments from payment-service.")
            return {
                "order": {
                    "id": 99,
                    "item": "New Order",
                    "status": "created"
                },
                "payments_verified": payments
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"[{corr_id}] [{SERVICE_NAME}] payment-service returned {e.response.status_code}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"payment-service error: {e.response.text}"
            )
        except Exception as e:
            logger.error(f"[{corr_id}] [{SERVICE_NAME}] Failed to reach payment-service: {e}")
            raise HTTPException(
                status=503,
                detail="payment-service unreachable"
            )


@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: int, request: Request):
    corr_id = request.headers.get("x-correlation-id", "none")
    logger.info(f"[{corr_id}] [{SERVICE_NAME}] GET /orders/{order_id}")
    order = next((o for o in ORDERS if o.id == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order
