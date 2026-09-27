from pydantic import BaseModel
from typing import Generic, TypeVar, List, Optional

T = TypeVar("T")

class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int

class ErrorResponse(BaseModel):
    error: str
    message: str
    reference_id: Optional[str] = None

class SuccessResponse(BaseModel):
    success: bool
    message: str
