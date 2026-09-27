import asyncio
import uuid
import random
from datetime import datetime, timezone, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.backend.database.connection import engine, Base
from apps.backend.database.models import Camera, Incident, Event
from sqlalchemy import text

async def seed_border_data():
    async with engine.begin() as conn:
        # Clear existing tables for fresh border data
        await conn.execute(text("DELETE FROM incidents"))
        await conn.execute(text("DELETE FROM events"))
        await conn.execute(text("DELETE FROM cameras"))
        
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.asyncio import AsyncSession
    
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with SessionLocal() as db:
        print("Deploying Border Surveillance Cameras...")
        cams = [
            Camera(id="CAM-B-01", name="Border Fence Sector 7A", scenario="zone_intrusion", enabled=True, rtsp_url_hash="h1"),
            Camera(id="CAM-B-02", name="Checkpost Alpha (Night Vision)", scenario="night", enabled=True, rtsp_url_hash="h2"),
            Camera(id="CAM-B-03", name="No-Man's Land Drone View", scenario="daytime", enabled=True, rtsp_url_hash="h3")
        ]
        db.add_all(cams)
        await db.commit()
            
        print("Simulating Border Threats (Intrusions & Loitering)...")
        event_types = ["VIRTUAL_FENCE_BREACH", "SUSPICIOUS_LOITERING", "UNAUTHORIZED_VEHICLE"]
        explanations = [
            "Human detected crossing the virtual perimeter line in low-light conditions.",
            "Person loitering near the restricted border fence for >30 seconds.",
            "Unidentified vehicle approaching the checkpost barricade."
        ]
        
        for i in range(7):
            evt_id = str(uuid.uuid4())
            ts = datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 120))
            idx = random.randint(0, 2)
            
            evt = Event(
                id=evt_id,
                camera_id=random.choice(["CAM-B-01", "CAM-B-02", "CAM-B-03"]),
                event_type=event_types[idx],
                severity=random.choice(["HIGH", "CRITICAL"]) if idx == 0 else "MEDIUM",
                confidence=random.uniform(0.75, 0.99),
                explanation=explanations[idx],
                model_name="yolov8n-border-tuned",
                model_version="v2.1",
                timestamp=ts
            )
            
            inc = Incident(
                id=str(uuid.uuid4()),
                camera_id=evt.camera_id,
                event_id=evt.id,
                timestamp=ts,
                event_type=evt.event_type,
                severity=evt.severity,
                model_version=evt.model_version,
                confidence=evt.confidence,
                acknowledged=False
            )
            db.add_all([evt, inc])
            
        await db.commit()
        print("Border Security data injected! Refresh Dashboard.")

if __name__ == "__main__":
    asyncio.run(seed_border_data())
