from typing import List, Optional, Dict, Any
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import ANPRObservation

class ANPRRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_observation(self, data: Dict[str, Any]) -> ANPRObservation:
        obs = ANPRObservation(**data)
        self.db.add(obs)
        await self.db.commit()
        await self.db.refresh(obs)
        return obs

    async def get_observations(
        self,
        camera_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ANPRObservation]:
        query = select(ANPRObservation).order_by(desc(ANPRObservation.timestamp))
        if camera_id:
            query = query.where(ANPRObservation.camera_id == camera_id)
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, obs_id: str) -> Optional[ANPRObservation]:
        return await self.db.get(ANPRObservation, obs_id)

    async def get_by_plate(self, plate_text: str, limit: int = 20) -> List[ANPRObservation]:
        query = select(ANPRObservation).where(
            ANPRObservation.plate_text == plate_text
        ).order_by(desc(ANPRObservation.timestamp)).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
