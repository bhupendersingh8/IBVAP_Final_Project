import os
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import structlog
from contextlib import asynccontextmanager
from typing import List, Dict, Any
import json
import yaml

from .config import get_settings
from .database.connection import init_db
from .routers import cameras
from .routers import events
from .routers import anpr
from .routers import health as health_router
from .routers import auth_router
from .routers import settings_router
from .routers import dataset_router
from .routers import tracking_router
from .routers import copilot_router
from .routers import agents_router
from .routers import authorized_personnel_router
from .routers import assurance as assurance_router

logger = structlog.get_logger()
settings = get_settings()

class LiveTelemetryHub:
    """Manages active WebSocket connections for live telemetry (detections, tracks, metrics, and alerts)."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.latest_telemetry: Dict[str, Any] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket client connected", total=len(self.active_connections))
        # Send latest telemetry snapshot immediately upon connection if available
        if self.latest_telemetry:
            try:
                await websocket.send_text(json.dumps(self.latest_telemetry))
            except Exception:
                pass

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket client disconnected", total=len(self.active_connections))

    async def broadcast(self, message: Dict[str, Any]):
        msg_type = message.get("type")
        if msg_type in ("telemetry", "metrics"):
            self.latest_telemetry = message
        msg_str = json.dumps(message)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(msg_str)
            except Exception as e:
                logger.warning("Failed to send WS message, removing connection", error=str(e))
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

ws_manager = LiveTelemetryHub()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting IBVAP Backend...", env=settings.APP_ENV)
    await init_db()
    os.makedirs("./data/evidence", exist_ok=True)
    yield
    # Shutdown
    logger.info("Shutting down IBVAP Backend...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.API_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url=None
)

app.include_router(cameras.router)
app.include_router(events.router)
app.include_router(anpr.router, prefix="/api/v1")
app.include_router(health_router.router)
app.include_router(auth_router.router)
app.include_router(settings_router.router)
app.include_router(dataset_router.router)
app.include_router(tracking_router.router)
app.include_router(copilot_router.router)
app.include_router(agents_router.router)
app.include_router(authorized_personnel_router.router)
app.include_router(assurance_router.router)

# Resilient evidence delivery with automatic placeholder fallback for missing/archived references
os.makedirs("./data/evidence", exist_ok=True)

@app.get("/evidence/{filename}")
async def get_evidence_file(filename: str):
    safe_name = os.path.basename(filename)
    file_path = os.path.abspath(os.path.join("./data/evidence", safe_name))
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/jpeg")
    # Return clean placeholder JPEG if specific historical evidence image is not on disk
    placeholder = cameras._create_placeholder(f"Evidence: {safe_name[:24]}", 640, 480)
    return Response(content=placeholder, media_type="image/jpeg")

app.mount("/evidence", StaticFiles(directory="./data/evidence"), name="evidence")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next) -> Response:
    """Add security headers to every HTTP response — PHASE 13."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.websocket("/ws/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep-alive receive & heartbeat response
            msg = await websocket.receive_text()
            if "ping" in msg:
                await websocket.send_json({"type": "pong", "timestamp": time.time()})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        ws_manager.disconnect(websocket)

@app.post("/api/v1/internal/broadcast_alert")
async def broadcast_alert(alert_data: Dict[str, Any]):
    """Internal endpoint called by inference worker to push real-time alerts to connected operators."""
    if "type" not in alert_data:
        alert_data["type"] = "alert"
    await ws_manager.broadcast(alert_data)
    return {"status": "broadcast_sent", "clients": len(ws_manager.active_connections)}

@app.post("/api/v1/internal/telemetry")
async def broadcast_telemetry(telemetry_data: Dict[str, Any]):
    """Internal endpoint called by inference worker to push real live bounding boxes, tracks, and telemetry."""
    if "type" not in telemetry_data:
        telemetry_data["type"] = "telemetry"
    await ws_manager.broadcast(telemetry_data)
    return {"status": "telemetry_broadcasted", "clients": len(ws_manager.active_connections)}

@app.post("/api/v1/internal/anpr_event")
async def broadcast_anpr_event(anpr_data: Dict[str, Any]):
    """Internal endpoint called by inference worker to push verified ANPR license plate observations."""
    if "type" not in anpr_data:
        anpr_data["type"] = "vehicle_anpr"
    await ws_manager.broadcast(anpr_data)
    return {"status": "anpr_broadcasted", "clients": len(ws_manager.active_connections)}

@app.get("/api/v1/zones")
async def get_zones():
    """Returns authoritative zones loaded directly from configs/zones.yaml."""
    zones_path = os.path.join(os.path.dirname(__file__), "..", "..", "configs", "zones.yaml")
    if not os.path.exists(zones_path):
        return {"zones": []}
    with open(zones_path, "r") as f:
        data = yaml.safe_load(f) or {}
    return data

@app.post("/api/v1/zones")
async def save_zones(payload: Dict[str, Any]):
    """Persists updated zones list to configs/zones.yaml."""
    zones_path = os.path.join(os.path.dirname(__file__), "..", "..", "configs", "zones.yaml")
    zones = payload.get("zones", [])
    os.makedirs(os.path.dirname(zones_path), exist_ok=True)
    with open(zones_path, "w") as f:
        yaml.safe_dump({"zones": zones}, f, sort_keys=False)
    return {"status": "success", "zones_count": len(zones), "zones": zones}

@app.delete("/api/v1/zones/{zone_id}")
async def delete_zone(zone_id: str):
    """Deletes a zone by zone_id from configs/zones.yaml."""
    zones_path = os.path.join(os.path.dirname(__file__), "..", "..", "configs", "zones.yaml")
    if not os.path.exists(zones_path):
        raise HTTPException(status_code=404, detail="Zones configuration file not found")
    with open(zones_path, "r") as f:
        data = yaml.safe_load(f) or {}
    zones = [z for z in data.get("zones", []) if z.get("zone_id") != zone_id]
    with open(zones_path, "w") as f:
        yaml.safe_dump({"zones": zones}, f, sort_keys=False)
    return {"status": "success", "deleted_zone_id": zone_id, "remaining_count": len(zones)}

@app.get("/api/v1", tags=["System"])
@app.get("/api", tags=["System"])
async def api_index(request: Request):
    """Dynamic directory of all system endpoints, live streams, and interfaces."""
    base_url = str(request.base_url).rstrip("/")
    ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
    return {
        "system": "IBVAP - Intelligent Border Video Analytics Platform",
        "version": settings.API_VERSION,
        "status": "online",
        "web_dashboard": f"{base_url}/",
        "documentation": {
            "swagger_ui": f"{base_url}/docs",
            "redoc": f"{base_url}/redoc",
            "openapi_json": f"{base_url}/openapi.json"
        },
        "camera_streams": {
            "CAM-01_cctv": f"{base_url}/api/v1/cameras/CAM-01/stream",
            "WEBCAM-01_laptop": f"{base_url}/api/v1/cameras/WEBCAM-01/stream",
            "PHONE-CAM-01_mobile": f"{base_url}/api/v1/cameras/PHONE-CAM-01/stream"
        },
        "api_endpoints": {
            "cameras": f"{base_url}/api/v1/cameras",
            "incidents": f"{base_url}/api/v1/incidents",
            "anpr_observations": f"{base_url}/api/v1/anpr/observations",
            "zones": f"{base_url}/api/v1/zones",
            "settings": f"{base_url}/api/v1/settings",
            "remembrance": f"{base_url}/api/v1/tracking/remembrance",
            "copilot_query": f"{base_url}/api/v1/copilot/query",
            "copilot_sitrep": f"{base_url}/api/v1/copilot/sitrep",
            "health": f"{base_url}/health"
        },
        "websocket": {
            "alerts_and_telemetry": f"{ws_url}/ws/alerts"
        }
    }

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    from .database.connection import check_db_health
    db_health = await check_db_health()
    return {
        "status": "ok" if db_health["status"] == "ok" else "degraded",
        "version": settings.API_VERSION,
        "services": {
            "database": db_health
        }
    }

# Mount compiled production frontend at root for single-port access
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="spa_assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Exclude reserved backend paths
        for reserved in ("api", "docs", "redoc", "openapi.json", "evidence", "ws", "health"):
            if full_path == reserved or full_path.startswith(f"{reserved}/"):
                raise HTTPException(status_code=404, detail="Not Found")
        
        target = os.path.abspath(os.path.join(frontend_dist, full_path))
        if not target.startswith(frontend_dist):
            raise HTTPException(status_code=403, detail="Forbidden")
        if full_path and os.path.isfile(target):
            return FileResponse(target)
        
        index_html = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_html):
            return FileResponse(index_html)
        raise HTTPException(status_code=404, detail="Frontend build index.html not found")
