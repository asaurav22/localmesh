from fastapi import APIRouter, HTTPException
from control_plane.models import RegisterRequest, ServiceEntry, ServiceEntryWithExpiry
from control_plane import registry as registry_store
from control_plane.registry import ConflictError

router = APIRouter(prefix="/registry", tags=["Registry"])


@router.post("/register", status_code=201, response_model=ServiceEntry)
def register(req: RegisterRequest):
    try:
        entry = registry_store.register_service(
            req.service_name, req.host, req.port, req.ttl
        )
        return entry
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/lookup/{service_name}", response_model=ServiceEntry)
def lookup(service_name: str):
    entry = registry_store.lookup_service(service_name)
    if not entry:
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service_name}' not found in registry"
        )
    return entry


@router.get("/services", response_model=list[ServiceEntryWithExpiry])
def services():
    return registry_store.get_all_services()
