import asyncio
import logging
from fastapi import FastAPI
from control_plane.routers import registry_router, dashboard_router
from control_plane.registry import sweep_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s"
)

app = FastAPI(title="LocalMesh Control Plane")

app.include_router(registry_router.router)
app.include_router(dashboard_router.router)


@app.on_event("startup")
async def start_background_tasks():
    asyncio.create_task(sweep_loop())
    logging.getLogger(__name__).info("[STARTUP] Sweep loop started - interval 5s")
