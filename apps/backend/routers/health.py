"""
Health and Observability endpoints — PHASE 19.

GET /health/live   — Liveness: always 200 if process is running
GET /health/ready  — Readiness: checks database connectivity
GET /api/v1/metrics — Inference + system metrics (no sensitive data)
GET /api/v1/cameras/health — Per-camera health state
"""
from fastapi import APIRouter
from typing import Dict, Any
import os
import time
import structlog

logger = structlog.get_logger()

router = APIRouter()

# Process start time for uptime calculation
_PROCESS_START = time.time()


@router.get("/health", tags=["Health"])
@router.get("/api/v1/health", tags=["Health"])
@router.get("/health/live", tags=["Health"])
async def liveness() -> Dict[str, Any]:
    """
    Kubernetes-style liveness probe.
    Returns 200 as long as the process is alive.
    """
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - _PROCESS_START, 1),
    }


@router.get("/health/ready", tags=["Health"])
async def readiness() -> Dict[str, Any]:
    """
    Kubernetes-style readiness probe.
    Checks database connectivity. Returns 200 if ready, 503 if not.
    """
    from apps.backend.database.connection import check_db_health
    from fastapi.responses import JSONResponse

    db = await check_db_health()
    db_ok = db.get("status") == "ok"

    payload = {
        "status": "ready" if db_ok else "not_ready",
        "checks": {
            "database": db_ok,
        },
        "uptime_seconds": round(time.time() - _PROCESS_START, 1),
    }
    status_code = 200 if db_ok else 503
    return JSONResponse(content=payload, status_code=status_code)


@router.get("/api/v1/metrics", tags=["Observability"])
async def get_metrics() -> Dict[str, Any]:
    """
    Returns current inference and system metrics.
    Metrics are sourced from the inference worker's in-memory counters.
    Returns zeros/defaults if inference worker is not running.
    NOTE: Does not expose secrets, PII, or raw frame data.
    """
    metrics: Dict[str, Any] = {
        "inference": {},
        "cameras": {},
        "system": {},
    }

    # Inference worker metrics (available if worker is running in same process)
    try:
        from services.inference.main_inference_worker import get_worker_metrics
        metrics["inference"] = get_worker_metrics()
    except (ImportError, Exception) as e:
        metrics["inference"] = {"status": "worker_not_running", "error": str(e)}

    # Camera health metrics
    try:
        from services.ingestion.camera_health import camera_health_monitor
        metrics["cameras"] = camera_health_monitor.get_all_health()
    except Exception as e:
        metrics["cameras"] = {"error": str(e)}

    # Basic system info (CPU/memory via psutil if available)
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        metrics["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_mb": round(proc.memory_info().rss / 1024 / 1024, 1),
            "uptime_seconds": round(time.time() - _PROCESS_START, 1),
        }
    except Exception:
        metrics["system"] = {"uptime_seconds": round(time.time() - _PROCESS_START, 1)}

    return metrics


@router.get("/api/v1/cameras/health", tags=["Cameras"])
async def cameras_health() -> Dict[str, Any]:
    """
    Returns per-camera health state: ONLINE / DEGRADED / OFFLINE / RECONNECTING.
    """
    try:
        from services.ingestion.camera_health import camera_health_monitor
        return {"cameras": camera_health_monitor.get_all_health()}
    except Exception as e:
        logger.warning("Could not fetch camera health", error=str(e))
        return {"cameras": {}, "error": str(e)}
