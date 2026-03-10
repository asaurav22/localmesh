from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    service_name: str
    host: str
    port: int
    ttl: int = Field(default=30, gt=0, description="Time-to-live in seconds")
    expected_version: int = Field(default=0, ge=0, description="Expected current version for optimistic locking")


class ServiceEntry(BaseModel):
    service_name: str
    host: str
    port: int
    registered_at: float
    ttl: int
    expires_at: float
    version: int


class ServiceEntryWithExpiry(ServiceEntry):
    expires_in: float = Field(description="Seconds remaining before expiry")


class ServiceDashboardEntry(BaseModel):
    name: str
    host: str
    port: int
    version: int
    expires_in_seconds: int
    status: str


class MeshSummary(BaseModel):
    total_services: int
    healthy: int
    expiring_soon: int


class DashboardResponse(BaseModel):
    mesh_summary: MeshSummary
    services: list[ServiceDashboardEntry]
