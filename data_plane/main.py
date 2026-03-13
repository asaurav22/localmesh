import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from data_plane import routing_table as routing_store

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
    return JSONResponse(
        status_code=200,
        content={
            "status": "proxy received",
            "method": request.method,
            "path": f"/{path}"
        }
    )
