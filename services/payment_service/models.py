from pydantic import BaseModel

class Payment(BaseModel):
    id: int
    order_id: int
    amount: float
    currency: str
    status: str
