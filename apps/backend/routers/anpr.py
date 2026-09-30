from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ..database.connection import get_db
from ..database.repositories.anpr_repo import ANPRRepository
from ..schemas.anpr import ANPRObservationResponse, ANPRObservationCreate

router = APIRouter(prefix="/anpr", tags=["ANPR & Vehicle Analytics"])

@router.get("/observations", response_model=List[ANPRObservationResponse])
@router.get("/observations/", response_model=List[ANPRObservationResponse], include_in_schema=False)
async def list_observations(
    camera_id: Optional[str] = Query(None, description="Filter by Camera ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve paginated ANPR vehicle observations with plate text and status."""
    repo = ANPRRepository(db)
    return await repo.get_observations(camera_id=camera_id, limit=limit, offset=offset)

@router.get("/observations/{obs_id}", response_model=ANPRObservationResponse)
async def get_observation(
    obs_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve specific ANPR observation by ID."""
    repo = ANPRRepository(db)
    obs = await repo.get_by_id(obs_id)
    if not obs:
        raise HTTPException(status_code=404, detail="ANPR observation not found")
    return obs
