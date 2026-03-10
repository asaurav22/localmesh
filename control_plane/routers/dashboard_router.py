from fastapi import APIRouter
from control_plane.models import DashboardResponse
from control_plane import registry as registry_store

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
def dashboard():
    return registry_store.get_dashboard_data()
