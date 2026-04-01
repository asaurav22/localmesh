import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from data_plane import routing_table as routing_store
from data_plane.resolver import parse_path, resolve, ServiceNotFoundError
from data_plane.routing_table import seed_route
from data_plane.forwarder import forward
from data_plane.syncer import sync_loop
from data_plane import breaker_registry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(sync_loop())
    logger.info("[STARTUP] Sidecar sync loop started")
    yield


app = FastAPI(title="LocalMesh Sidecar Proxy", lifespan=lifespan)


@app.get("/routing-table")
def get_routing_table():
    return routing_store.get_all_routes()


@app.get("/breakers")
def get_breakers():
    """Returns state of all circuit breakers - one per upstream service."""
    all_breakers = breaker_registry.get_all_breakers()
    logger.info(f"[BREAKERS] Returning state for {len(all_breakers)} breaker(s)")
    return all_breakers


@app.get("/dev/seed")
def seed(service_name: str, host, port):
    seed_route(service_name, host, port)
    return {"seeded": service_name, "host": host, "port": port}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    logger.info(f"[PROXY] Received: {request.method} /{path}")

    service_name, real_path = parse_path(path)

    # step 1: circuit breaker check
    cb = breaker_registry.get_breaker(service_name)
    logger.info(f"[PROXY] Breaker state for '{service_name}': {cb.state_info}")

    if not cb.can_pass():
        logger.warning(f"[PROXY] Breaker state for '{service_name}' - rejecting request")
        return JSONResponse(
            status_code=503,
            content={
                "error": "Circuit breaker open",
                "service": service_name,
                "state": cb.state.value,
                "retry_after": f"{int(cb.open_duration)}s"
            }
        )

    # step 2: resolve logical name
    try:
        real_url = resolve(service_name, real_path)
    except ServiceNotFoundError:
        cb.on_failure()  # count resolution failure too
        return JSONResponse(
            status_code=503,
            content={
                "error": "Service not registered",
                "service": service_name,
                "tip": "Check :7000/registry/services"
            }
        )

    # step 3: forward + update breaker
    try:
        response: Response = await forward(request, real_url)

        if response.status_code >= 500:
            cb.on_failure()
            logger.warning(
                f"[PROXY] Upstream '{service_name}' returned "
                f"{response.status_code} - failure recorded"
            )
        else:
            cb.on_success()
            logger.info(
                f"[PROXY] '{service_name}' responsed "
                f"{response.status_code} - success recorded"
            )

        return response

    except Exception as e:
        cb.on_failure()
        logger.error(f"[PROXY] Forward failed for '{service_name}': {e}")
        return JSONResponse(
            status_code=503,
            content={
                "error": "Upstream unreachable",
                "service": service_name,
                "detail": str(e)
            }
        )
