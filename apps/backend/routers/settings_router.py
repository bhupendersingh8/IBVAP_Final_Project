from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import os
import json
import re
import socket
import asyncio
import subprocess
import httpx
from typing import List, Dict, Any, Optional
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])

SETTINGS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "configs", "system_settings.json"))

class SystemSettings(BaseModel):
    phone_camera_url: str = Field(default="http://192.168.1.5:8080/video", description="Mobile WiFi Camera Stream URL")
    confidence_threshold: float = Field(default=0.25, ge=0.05, le=0.95)
    iou_threshold: float = Field(default=0.20, ge=0.05, le=0.90)
    face_detection_enabled: bool = Field(default=True)
    anpr_enabled: bool = Field(default=True)
    night_enhancement_enabled: bool = Field(default=True)
    loitering_threshold_seconds: int = Field(default=15, ge=5, le=120)
    auto_dataset_capture: bool = Field(default=False)

class DiscoveredCamera(BaseModel):
    ip: str
    port: int
    camera_type: str
    stream_url: str
    is_live: bool
    response_time_ms: float

def load_settings_from_disk() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load settings file, using defaults", error=str(e))
    return SystemSettings().model_dump()

@router.get("", response_model=SystemSettings, include_in_schema=False)
@router.get("/", response_model=SystemSettings)
async def get_settings():
    """Retrieve persisted system and AI settings."""
    data = load_settings_from_disk()
    return SystemSettings(**data)

@router.post("", response_model=SystemSettings, include_in_schema=False)
@router.post("/", response_model=SystemSettings)
async def update_settings(new_settings: SystemSettings):
    """Save updated settings to disk and apply across active pipeline."""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(new_settings.model_dump(), f, indent=2)
    logger.info("System settings updated and saved", settings=new_settings.model_dump())
    return new_settings

async def _probe_camera_endpoint(ip: str, port: int, path: str, cam_type: str) -> Optional[DiscoveredCamera]:
    """Test connection to candidate camera endpoint with strict timeout."""
    url = f"http://{ip}:{port}{path}"
    t0 = asyncio.get_event_loop().time()
    try:
        async with httpx.AsyncClient(timeout=0.6) as client:
            resp = await client.get(url, headers={"User-Agent": "IBVAP-Discovery/1.0"})
            t_ms = round((asyncio.get_event_loop().time() - t0) * 1000, 1)
            # Accept 200, 204, or streaming mjpeg/octet
            if resp.status_code in (200, 204, 206) or "image" in resp.headers.get("content-type", ""):
                return DiscoveredCamera(
                    ip=ip,
                    port=port,
                    camera_type=cam_type,
                    stream_url=url,
                    is_live=True,
                    response_time_ms=t_ms
                )
    except Exception:
        pass
    return None

@router.post("/discover-cameras", response_model=List[DiscoveredCamera])
async def discover_wifi_cameras():
    """
    Auto-discovers active mobile IP cameras (IP Webcam, DroidCam, etc.) across the local WiFi/hotspot network.
    Uses ARP table analysis and parallel asynchronous probing so team members on any device/network
    can connect instantly without manually entering IP addresses.
    """
    candidate_ips = set()

    # 1. Inspect ARP cache
    try:
        proc = await asyncio.create_subprocess_exec(
            "arp", "-a",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        lines = stdout.decode("utf-8", errors="ignore").splitlines()
        for line in lines:
            match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
            if match:
                ip = match.group(1)
                # Exclude loopback, multicast, and broadcast
                if not ip.startswith(("127.", "224.", "239.", "255.")) and not ip.endswith(".255"):
                    candidate_ips.add(ip)
    except Exception as e:
        logger.warning("ARP table scan failed", error=str(e))

    # 2. Add local host IP and current configured phone IP if set
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        candidate_ips.add(local_ip)
    except Exception:
        pass

    curr_settings = load_settings_from_disk()
    curr_url = curr_settings.get("phone_camera_url", "")
    url_match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", curr_url)
    if url_match:
        candidate_ips.add(url_match.group(1))

    tasks = []
    # Test ports 8080 (IP Webcam) and 4747 (DroidCam)
    for ip in candidate_ips:
        tasks.append(_probe_camera_endpoint(ip, 8080, "/video", "IP Webcam (Android/iOS)"))
        tasks.append(_probe_camera_endpoint(ip, 8080, "/video.mjpg", "IP Webcam Alternative"))
        tasks.append(_probe_camera_endpoint(ip, 4747, "/video", "DroidCam"))

    results = await asyncio.gather(*tasks)
    discovered = [r for r in results if r is not None]

    # Deduplicate by stream_url
    seen_urls = set()
    unique_discovered = []
    for d in discovered:
        if d.stream_url not in seen_urls:
            seen_urls.add(d.stream_url)
            unique_discovered.append(d)

    logger.info("WiFi camera auto-discovery completed", found_count=len(unique_discovered), ips_checked=len(candidate_ips))
    return unique_discovered
