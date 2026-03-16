import os
import logging
import asyncio
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from services.payment_service.models import Payment

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://localhost:7000")
SERVICE_NAME = os.getenv("SERVICE_NAME", "payment-service")
SERVICE_HOST = os.getenv("SERVICE_HOST", "127.0.0.1")
SERVICE_PORT = os.getenv("SERVICE_PORT", "9002")


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

app = FastAPI(title="Payment Service", lifespan=lifespan)

PAYMENTS = [
    Payment(id=1, order_id=1, amount=120.00, currency="USD", status="completed"),
    Payment(id=2, order_id=2, amount=70.00, currency="USD", status="completed"),
    Payment(id=3, order_id=3, amount=45.00, currency="USD", status="refunded")
]


@app.get("/health")
def health():
    return {"status": "ok", "service_name": SERVICE_NAME}


@app.get("/payments", response_model=list[Payment])
def get_payments():
    logger.info(f"[{SERVICE_NAME}] GET /payments called")
    return PAYMENTS


@app.get("/payments/{payment_id}", response_model=Payment)
def get_payment(payment_id: int):
    payment = next((p for p in PAYMENTS if p.id == payment_id), None)
    if not payment:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
    return payment
