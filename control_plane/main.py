from fastapi import FastAPI
from control_plane.routers.registry_router import router

app = FastAPI(title="LocalMesh Control Plane")

app.include_router(router)
