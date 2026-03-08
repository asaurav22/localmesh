from pydantic import BaseModel

class RegisterRequest(BaseModel):
    service_name: str
    host: str
    port: int

class ServiceEntry(BaseModel):
    service_name: str
    host: str
    port: int
    registered_at: float
