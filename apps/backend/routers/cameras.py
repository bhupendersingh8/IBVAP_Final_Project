from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import os
import sys
import time
import asyncio
import subprocess
import psutil
import cv2
import numpy as np
import json
from pydantic import BaseModel
from ..database.connection import get_db
from ..database.repositories.camera_repo import CameraRepository
from ..schemas.camera import CameraResponse, CameraCreate
from ..auth.jwt_auth import require_auth, require_permission, require_role
from ..auth.rbac import Role, Permission

router = APIRouter(prefix="/api/v1/cameras", tags=["Cameras"])

from services.ingestion.shared_frame_buffer import SharedFrameReader

_placeholder_cache: dict = {}

def _create_placeholder(text: str, w: int = 640, h: int = 480) -> bytes:
    if text in _placeholder_cache:
        return _placeholder_cache[text]
    img = np.full((h, w, 3), 24, dtype=np.uint8)
    cv2.putText(img, text, (30, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (220, 220, 220), 2)
    cv2.putText(img, "Initializing AI pipeline...", (30, h // 2 + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 100), 1)
    _, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    data = buf.tobytes()
    _placeholder_cache[text] = data
    return data

@router.get("/{camera_id}/stream")
async def stream_camera(request: Request, camera_id: str, annotated: bool = False):
    """
    Continuous MJPEG video stream for direct browser viewport embedding.
    Works natively in standard <img> tags without hardware lock conflicts or WebRTC complexity.
    Ultra-low latency RAM SharedMemory streaming with zero disk I/O.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    evidence_dir = os.path.join(project_root, "data", "evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    
    annotated_file = os.path.join(evidence_dir, f"live_annotated_{camera_id}.jpg")
    raw_file = os.path.join(evidence_dir, f"live_{camera_id}.jpg")

    async def frame_generator():
        shm_reader = SharedFrameReader(camera_id)
        last_mtime = 0.0
        cached_frame = None
        try:
            while True:
                if await request.is_disconnected():
                    break

                fresh = False
                # 1. Primary: Ultra-low latency in-memory SharedMemory frame read (<0.1ms)
                shm_result = shm_reader.read_frame(max_age_seconds=3.0)
                if shm_result is not None:
                    cached_frame, _ = shm_result
                    fresh = True
                else:
                    # 2. Secondary Fallback: Disk frame read
                    target = None
                    if annotated:
                        if os.path.exists(annotated_file):
                            target = annotated_file
                        elif os.path.exists(raw_file):
                            target = raw_file
                    else:
                        # Clean stream: strictly prioritize raw frame to prevent ghost bounding boxes with SVG overlay
                        if os.path.exists(raw_file):
                            target = raw_file

                    if target and os.path.exists(target):
                        try:
                            mtime = os.path.getmtime(target)
                            age = time.time() - mtime
                            if age < 3.5:
                                fresh = True
                                if mtime != last_mtime or cached_frame is None:
                                    with open(target, "rb") as f:
                                        cached_frame = f.read()
                                    last_mtime = mtime
                        except Exception:
                            pass

                if not fresh or cached_frame is None or not cached_frame.startswith(b"\xff\xd8"):
                    cached_frame = _create_placeholder(f"IBVAP: {camera_id} [Connecting / Initializing...]")

                header = (
                    f"--frame\r\n"
                    f"Content-Type: image/jpeg\r\n"
                    f"Content-Length: {len(cached_frame)}\r\n\r\n"
                ).encode("ascii")
                yield header + cached_frame + b"\r\n"
                await asyncio.sleep(0.033)  # ~30 FPS ultra-smooth video playback
        finally:
            shm_reader.close()

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

def normalize_phone_url(raw: str) -> str:
    """Intelligently parses and normalizes user input into a valid video stream URL."""
    url = (raw or "").strip()
    if not url:
        return "http://192.168.1.5:8080/video"
    if not (url.startswith("http://") or url.startswith("https://") or url.startswith("rtsp://")):
        url = f"http://{url}"
    # Android IP Webcam app (default port 8080)
    if ":8080" in url and not any(url.endswith(x) for x in ("/video", "/shot.jpg", "/videofeed", ".m3u8")):
        url = url.rstrip("/") + "/video"
    # DroidCam app (default port 4747)
    elif ":4747" in url and not any(url.endswith(x) for x in ("/video", "/mjpegfeed")):
        url = url.rstrip("/") + "/video"
    return url

class PhoneConnectPayload(BaseModel):
    url: str

@router.post("/phone/connect")
async def connect_phone(payload: PhoneConnectPayload):
    """One-click easy phone camera connector with automatic format normalization."""
    norm_url = normalize_phone_url(payload.url)
    result = await activate_camera(camera_id="PHONE-CAM-01", force=True, phone_url=norm_url)
    return {"status": "connected", "camera_id": "PHONE-CAM-01", "stream_url": norm_url}

@router.post("/{camera_id}/activate")
async def activate_camera(camera_id: str, force: bool = False, phone_url: Optional[str] = None):
    """
    Dynamically switches or starts the inference worker for the selected camera.
    Supports instant on-the-fly phone camera URL updates.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    worker_script = os.path.join(project_root, "services", "inference", "main_inference_worker.py")
    settings_file = os.path.join(project_root, "configs", "system_settings.json")
    
    if camera_id.startswith("WEBCAM"):
        rtsp_target = "webcam:0"
    elif camera_id.startswith("PHONE"):
        if phone_url:
            rtsp_target = normalize_phone_url(phone_url)
            force = True
            try:
                data = {}
                if os.path.exists(settings_file):
                    with open(settings_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                data["phone_camera_url"] = rtsp_target
                with open(settings_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass
        else:
            rtsp_target = "http://192.168.1.5:8080/video"
            if os.path.exists(settings_file):
                try:
                    with open(settings_file, "r", encoding="utf-8") as f:
                        saved = json.load(f).get("phone_camera_url")
                        if saved:
                            rtsp_target = normalize_phone_url(saved)
                except Exception:
                    pass
    else:
        rtsp_target = f"rtsp://127.0.0.1:8554/{camera_id}"

    # Terminate any conflicting or stale inference worker
    evidence_dir = os.path.join(project_root, "data", "evidence")
    ann_file = os.path.join(evidence_dir, f"live_annotated_{camera_id}.jpg")
    raw_file = os.path.join(evidence_dir, f"live_{camera_id}.jpg")
    target_preview = ann_file if os.path.exists(ann_file) else raw_file
    is_actively_writing = os.path.exists(target_preview) and (time.time() - os.path.getmtime(target_preview) < 4.0)

    def _manage_workers_sync():
        already_running_and_fresh = False
        for proc in psutil.process_iter(['pid', 'name', 'create_time']):
            try:
                pname = (proc.info.get('name') or '').lower()
                if 'python' not in pname:
                    continue
                cmd = " ".join(proc.cmdline() or []).lower()
                if "main_inference_worker.py" in cmd:
                    try:
                        is_recently_started = (time.time() - proc.create_time() < 25.0)
                    except Exception:
                        is_recently_started = False

                    if not force and f"--camera {camera_id.lower()}" in cmd and (is_actively_writing or is_recently_started):
                        already_running_and_fresh = True
                        continue
                    
                    try:
                        proc.terminate()
                        proc.wait(timeout=1.5)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass
            except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
                pass
        return already_running_and_fresh

    already_running = await asyncio.to_thread(_manage_workers_sync)
    if already_running:
        return {"status": "already_active", "camera_id": camera_id, "rtsp": rtsp_target}

    # Launch dedicated worker
    log_dir = os.path.join(project_root, "data", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = open(os.path.join(log_dir, f"worker_{camera_id}.log"), "a", encoding="utf-8")
    gpu_python = os.path.join(project_root, ".venv_gpu", "Scripts", "python.exe")
    worker_python = gpu_python if os.path.exists(gpu_python) else sys.executable

    subprocess.Popen(
        [worker_python, "-u", worker_script, "--camera", camera_id, "--rtsp", rtsp_target, "--input-size", "640"],
        cwd=project_root,
        stdout=log_file,
        stderr=log_file,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    return {"status": "activated", "camera_id": camera_id, "rtsp": rtsp_target}

@router.get("", response_model=List[CameraResponse], include_in_schema=False)
@router.get("/", response_model=List[CameraResponse])
async def list_cameras(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission(Permission.VIEW_CAMERAS))
):
    """Retrieve all configured cameras."""
    repo = CameraRepository(db)
    cameras = await repo.get_all()
    return cameras

@router.get("/{camera_id}", response_model=CameraResponse)
async def get_camera(
    camera_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission(Permission.VIEW_CAMERAS))
):
    """Retrieve details for a specific camera."""
    repo = CameraRepository(db)
    cam = await repo.get_by_id(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    return cam

@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(
    camera_in: CameraCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission(Permission.MANAGE_CAMERAS))
):
    """Add a new camera. Note: RTSP URLs are securely hashed before storage."""
    repo = CameraRepository(db)
    existing = await repo.get_by_id(camera_in.id)
    if existing:
        raise HTTPException(status_code=400, detail="Camera ID already exists")
        
    cam = await repo.create(camera_in.model_dump())
    return cam

@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission(Permission.MANAGE_CAMERAS))
):
    """Delete a camera configuration."""
    repo = CameraRepository(db)
    success = await repo.delete(camera_id)
    if not success:
        raise HTTPException(status_code=404, detail="Camera not found")

