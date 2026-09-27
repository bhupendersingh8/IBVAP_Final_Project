"""
Authorized Personnel API Router
Provides endpoints to view, add, and query authorized personnel and their verification photos.
"""
import os
import time
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
import cv2
import structlog

from services.auth_personnel import AuthorizedPersonnelManager

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/authorized_people", tags=["Authorized Personnel"])


class AuthorizedPersonResponse(BaseModel):
    id: str
    name: str
    role: str
    department: str
    image_file: str
    status: str
    notes: Optional[str] = ""
    created_at: Optional[str] = ""


class AddPersonRequest(BaseModel):
    name: str
    role: str
    department: Optional[str] = "Border Security Division"
    notes: Optional[str] = ""


class CaptureWebcamRequest(BaseModel):
    name: str = "Authorized Officer"
    role: str = "Border Security Officer"
    department: Optional[str] = "BSF Sector Alpha"
    camera_id: Optional[str] = "WEBCAM-01"
    notes: Optional[str] = ""


@router.get("", response_model=List[AuthorizedPersonResponse])
async def list_authorized_people():
    """Retrieve all authorized personnel registered in the system."""
    mgr = AuthorizedPersonnelManager.get_instance()
    mgr.reload_registry()
    return mgr.get_all_personnel()


@router.post("")
async def add_authorized_person(
    name: str = Form(...),
    role: str = Form(...),
    department: str = Form("Border Security Division"),
    notes: str = Form(""),
    file: Optional[UploadFile] = File(None)
):
    """Register a new authorized person with optional photo upload."""
    mgr = AuthorizedPersonnelManager.get_instance()
    image_bytes = None
    filename = None
    if file:
        image_bytes = await file.read()
        filename = file.filename

    res = mgr.add_authorized_person(
        name=name,
        role=role,
        department=department,
        image_bytes=image_bytes,
        filename=filename,
        notes=notes
    )
    return {"status": "success", "person": res}


@router.get("/images/{filename}")
async def get_personnel_photo(filename: str):
    """Retrieve registered reference photo for an authorized person."""
    mgr = AuthorizedPersonnelManager.get_instance()
    safe_name = os.path.basename(filename)
    photo_path = os.path.join(mgr.images_dir, safe_name)
    if os.path.exists(photo_path):
        return FileResponse(photo_path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Photo not found")


@router.post("/capture_webcam")
async def capture_from_webcam(req: CaptureWebcamRequest):
    """
    Instantly registers the authorized person by capturing the current live frame from the webcam.
    Eliminates mobile photo vs. laptop webcam lighting/color divergence!
    """
    mgr = AuthorizedPersonnelManager.get_instance()
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    evidence_dir = os.path.join(project_root, "data", "evidence")

    # Try reading from live raw or annotated frame
    raw_path = os.path.join(evidence_dir, f"live_{req.camera_id}.jpg")
    ann_path = os.path.join(evidence_dir, f"live_annotated_{req.camera_id}.jpg")

    frame = None
    for p in [raw_path, ann_path]:
        if os.path.exists(p) and (time.time() - os.path.getmtime(p) < 15.0):
            frame = cv2.imread(p)
            if frame is not None and frame.size > 0:
                break

    if frame is None:
        raise HTTPException(
            status_code=400,
            detail=f"No active camera frame available for '{req.camera_id}'. Please ensure the camera is active."
        )

    person = mgr.register_from_frame(
        frame=frame,
        name=req.name,
        role=req.role,
        department=req.department or "BSF Sector Alpha",
        notes=req.notes or f"Registered directly from {req.camera_id} at {time.strftime('%H:%M:%S')}"
    )
    return {
        "status": "success",
        "message": f"Successfully registered '{req.name}' from live {req.camera_id} stream!",
        "person": person
    }

