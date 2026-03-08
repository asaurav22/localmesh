from pydantic import BaseModel, Field

class RegisterRequest(BaseModel):
    service_name: str
    host: str
    port: int
    ttl: int = Field(default=30, gt=0, description="Time-to-live in seconds")

class ServiceEntry(BaseModel):
    service_name: str
    host: str
    port: int
    registered_at: float
    ttl: int
    expires_at: float

class ServiceEntryWithExpiry(ServiceEntry):
    expires_in: float = Field(description="Seconds remaining before expiry")
