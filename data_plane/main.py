import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from data_plane import routing_table as routing_store
from data_plane.resolver import parse_path, resolve, ServiceNotFoundError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="LocalMesh Sidecar Proxy")

@app.get("/routing-table")
def get_routing_table():
    return routing_store.get_all_routes()


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    logger.info(f"[PROXY] Received: {request.method} / {path}")
    
    service_name, real_path = parse_path(path)

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
    
    return JSONResponse(
        status_code=200,
        content={
            "status": "resolved",
            "service": service_name,
            "real_url": real_url,
            "method": request.method
        }
    )
