import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from data_plane import routing_table as routing_store
from data_plane.routing_table import seed_route
from data_plane.resolver import parse_path, resolve, ServiceNotFoundError
from data_plane.forwarder import forward
from data_plane.syncer import sync_loop
from data_plane.breaker_registry import get_all_breakers, get_breaker
import asyncio

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(sync_loop())
    logger.info(f"[STARTUP] Sidecar sync loop started")
    yield

app = FastAPI(title="LocalMesh Sidecar Proxy", lifespan=lifespan)

@app.get("/routing-table")
def get_routing_table():
    return routing_store.get_all_routes()


@app.get("/breakers")
def get_breakers():
    """Returns state of all circuit breakers - one per upstream service"""
    return get_all_breakers()


@app.post("/dev/seed")
def seed(service_name: str, host: str, port: int):
    seed_route(service_name, host, port)
    return {
        "seeded": service_name,
        "host": host,
        "port": port
    }


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    logger.info(f"[PROXY] Received: {request.method} / {path}")
    
    service_name, real_path = parse_path(path)

    cb = get_breaker(service_name)
    if not cb.can_pass():
        logger.warning(f"[PROXY] Circuit breaker OPEN for '{service_name}' — rejecting")
        return JSONResponse(
            status_code=503,
            content={
                "error":       "Circuit breaker open",
                "service":     service_name,
                "state":       cb.state.value,
                "retry_after": f"{int(cb.open_duration)}s"
            }
        )
    try:
        real_url = resolve(service_name, real_path)
    except ServiceNotFoundError:
        return JSONResponse(
            status_code=503,
            content={
                "error": "Service not registered",
                "service": service_name,
                "tip": "Check :7000/registry/services"
            }
        )
    
    try:
        response = await forward(request, real_url)
        if response.status_code >= 500:
            cb.on_failure()
        else:
            cb.on_success()
        return response
    except Exception as e:
        cb.on_failure()
        logger.error(f"[PROXY] Forward failed for '{service_name}': {e}")
        return JSONResponse(
            status_code=503,
            content={
                "error":   "Upstream unreachable",
                "service": service_name
            }
        )
