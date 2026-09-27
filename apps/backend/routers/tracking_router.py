"""
IBVAP Tracking & Long-Term Remembrance Router
SIH PS-26187: Hardware-Agnostic Intelligent Surveillance
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
import structlog
from services.tracking.remembrance_store import LongTermRemembranceStore

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/tracking", tags=["Tracking & Remembrance"])

@router.get("/remembrance", response_model=List[Dict[str, Any]])
async def get_all_remembrance_profiles():
    """
    Retrieve all long-term remembered entity profiles (Vehicles, Trucks, Cars, Bikes, Persons).
    Includes recurring sightings, cameras visited, license plates, and global ReIDs.
    """
    store = LongTermRemembranceStore.get_instance()
    return store.get_all_profiles()

@router.get("/remembrance/stats")
async def get_remembrance_stats():
    """
    Aggregated remembrance intelligence summary for operations dashboard.
    """
    store = LongTermRemembranceStore.get_instance()
    profiles = store.get_all_profiles()
    
    total_vehicles = sum(1 for p in profiles if p.get("entity_type") == "vehicle")
    total_persons = sum(1 for p in profiles if p.get("entity_type") == "person")
    trucks = sum(1 for p in profiles if p.get("subclass") == "truck")
    cars = sum(1 for p in profiles if p.get("subclass") == "car")
    motorcycles = sum(1 for p in profiles if p.get("subclass") in ("motorcycle", "bicycle"))
    buses = sum(1 for p in profiles if p.get("subclass") == "bus")
    plates_resolved = sum(1 for p in profiles if p.get("license_plate"))

    return {
        "total_profiles": len(profiles),
        "total_vehicles": total_vehicles,
        "total_persons": total_persons,
        "vehicles_by_subclass": {
            "truck": trucks,
            "car": cars,
            "motorcycle": motorcycles,
            "bus": buses
        },
        "license_plates_remembered": plates_resolved
    }

@router.get("/remembrance/{global_id}")
async def get_remembrance_profile(global_id: str):
    """
    Get deep profile for a specific ReID entity.
    """
    store = LongTermRemembranceStore.get_instance()
    for p in store.get_all_profiles():
        if p.get("global_id") == global_id:
            return p
    raise HTTPException(status_code=404, detail="Entity profile not found")

@router.post("/remembrance/clear")
async def clear_remembrance_store():
    """
    Clear entity memory store.
    """
    store = LongTermRemembranceStore.get_instance()
    store.clear()
    return {"status": "cleared", "message": "Long-term remembrance store reset successfully."}
