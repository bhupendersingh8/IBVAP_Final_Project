from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CameraCreate(BaseModel):
    id: str
    name: str
    rtsp_url: str  # Accepted in creation, but never returned
    scenario: str
    enabled: bool = True

class CameraResponse(BaseModel):
    id: str
    name: str
    scenario: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

class CameraStatusResponse(BaseModel):
    id: str
    name: str
    health: str
    fps_measured: float
    last_frame_at: Optional[datetime]
    active_incidents_count: int = 0
