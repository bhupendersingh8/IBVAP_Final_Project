from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib

from ..models import Camera

class CameraRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> List[Camera]:
        result = await self.db.execute(select(Camera))
        return list(result.scalars().all())

    async def get_by_id(self, camera_id: str) -> Optional[Camera]:
        result = await self.db.execute(select(Camera).where(Camera.id == camera_id))
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Camera:
        # Never store plaintext RTSP URL
        rtsp = data.pop("rtsp_url", "")
        if rtsp:
            data["rtsp_url_hash"] = hashlib.sha256(rtsp.encode()).hexdigest()
            
        cam = Camera(**data)
        self.db.add(cam)
        await self.db.commit()
        await self.db.refresh(cam)
        return cam

    async def delete(self, camera_id: str) -> bool:
        cam = await self.get_by_id(camera_id)
        if not cam:
            return False
        await self.db.delete(cam)
        await self.db.commit()
        return True
