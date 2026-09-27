"""
Dataset Capture, Management and Training Trigger Router for IBVAP.
Allows operators to capture real CCTV/webcam/phone frames, automatically crop 
vehicles, license plates, and faces, generate YOLO annotations, and train models.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import sys
import time
import uuid
import json
import cv2
import numpy as np
import structlog
import subprocess

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/dataset", tags=["Dataset"])

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
LABELED_DIR = os.path.join(PROJECT_ROOT, "data", "labeled")
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
ANPR_DIR = os.path.join(PROJECT_ROOT, "data", "anpr_validation")
FACES_DIR = os.path.join(PROJECT_ROOT, "data", "faces")
MANIFEST_FILE = os.path.join(PROJECT_ROOT, "data", "dataset_manifest.json")

for d in [LABELED_DIR, RAW_DIR, ANPR_DIR, FACES_DIR]:
    os.makedirs(d, exist_ok=True)
    os.makedirs(os.path.join(d, "images"), exist_ok=True)
    os.makedirs(os.path.join(d, "labels"), exist_ok=True)

class CaptureRequest(BaseModel):
    camera_id: str = "WEBCAM-01"
    notes: str = ""

@router.post("/capture")
async def capture_training_sample(req: CaptureRequest):
    """
    Captures current camera frame, extracts vehicles, plates, and faces, 
    and saves labeled YOLO training samples.
    """
    evidence_dir = os.path.join(PROJECT_ROOT, "data", "evidence")
    raw_frame_path = os.path.join(evidence_dir, f"live_{req.camera_id}.jpg")
    if not os.path.exists(raw_frame_path):
        raw_frame_path = os.path.join(evidence_dir, f"live_annotated_{req.camera_id}.jpg")
        
    if not os.path.exists(raw_frame_path):
        raise HTTPException(status_code=404, detail=f"No active video frame available for camera '{req.camera_id}'. Ensure camera is streaming.")

    frame = cv2.imread(raw_frame_path)
    if frame is None:
        raise HTTPException(status_code=500, detail="Failed to decode video frame.")

    sample_id = f"sample_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    h, w = frame.shape[:2]

    # Save raw frame
    img_filename = f"{sample_id}.jpg"
    img_dest = os.path.join(LABELED_DIR, "images", img_filename)
    cv2.imwrite(img_dest, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

    # Run quick YOLO inference to generate annotations
    annotations = []
    classes_found = []
    try:
        from ultralytics import YOLO
        model = YOLO("yolov8n.pt")
        results = model.predict(frame, conf=0.25, verbose=False)[0]
        label_filename = f"{sample_id}.txt"
        label_dest = os.path.join(LABELED_DIR, "labels", label_filename)

        with open(label_dest, "w") as lf:
            for box in results.boxes:
                cls_id = int(box.cls[0])
                cls_name = model.names[cls_id]
                classes_found.append(cls_name)
                # YOLO format: class_id cx cy w h (normalized)
                xywhn = box.xywhn[0].tolist()
                lf.write(f"{cls_id} {xywhn[0]:.6f} {xywhn[1]:.6f} {xywhn[2]:.6f} {xywhn[3]:.6f}\n")
                
                # If vehicle, crop to ANPR validation directory
                if cls_name in ["car", "truck", "bus", "motorcycle"]:
                    bx = box.xyxy[0].tolist()
                    vx1, vy1 = max(0, int(bx[0])), max(0, int(bx[1]))
                    vx2, vy2 = min(w, int(bx[2])), min(h, int(bx[3]))
                    vcrop = frame[vy1:vy2, vx1:vx2]
                    if vcrop.size > 0:
                        vcrop_path = os.path.join(ANPR_DIR, f"vehicle_{sample_id}_{len(classes_found)}.jpg")
                        cv2.imwrite(vcrop_path, vcrop)

    except Exception as e:
        logger.warning("Auto-label generation failed, image saved as unannotated", error=str(e))

    # Face detection crop
    try:
        from services.detection.face_detector import SoftwareFaceDetector
        fd = SoftwareFaceDetector()
        faces = fd.detect_faces(frame)
        for idx, face in enumerate(faces):
            classes_found.append("face")
            fb = face["bbox"]
            fx1, fy1 = max(0, int(fb["x1"] * w)), max(0, int(fb["y1"] * h))
            fx2, fy2 = min(w, int(fb["x2"] * w)), min(h, int(fb["y2"] * h))
            fcrop = frame[fy1:fy2, fx1:fx2]
            if fcrop.size > 0:
                fcrop_path = os.path.join(FACES_DIR, f"face_{sample_id}_{idx}.jpg")
                cv2.imwrite(fcrop_path, fcrop)
    except Exception:
        pass

    # Update manifest
    manifest_data = []
    if os.path.exists(MANIFEST_FILE):
        try:
            with open(MANIFEST_FILE, "r") as f:
                manifest_data = json.load(f)
        except Exception:
            manifest_data = []

    entry = {
        "sample_id": sample_id,
        "timestamp": time.time(),
        "camera_id": req.camera_id,
        "image_file": img_filename,
        "classes": list(set(classes_found)),
        "total_objects": len(classes_found),
        "notes": req.notes
    }
    manifest_data.append(entry)
    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest_data, f, indent=2)

    return {
        "status": "success",
        "sample_id": sample_id,
        "classes_detected": list(set(classes_found)),
        "total_objects": len(classes_found),
        "image_saved": img_dest
    }

@router.get("/stats")
async def get_dataset_stats():
    """Returns aggregated dataset statistics."""
    images_dir = os.path.join(LABELED_DIR, "images")
    anpr_dir = ANPR_DIR
    faces_dir = FACES_DIR

    total_images = len([f for f in os.listdir(images_dir) if f.endswith(".jpg")]) if os.path.exists(images_dir) else 0
    total_vehicles = len([f for f in os.listdir(anpr_dir) if f.startswith("vehicle_")]) if os.path.exists(anpr_dir) else 0
    total_faces = len([f for f in os.listdir(faces_dir) if f.startswith("face_")]) if os.path.exists(faces_dir) else 0

    return {
        "total_samples": total_images,
        "vehicle_crops": total_vehicles,
        "face_crops": total_faces,
        "training_ready": total_images > 0
    }

class SelfTrainRequest(BaseModel):
    force: bool = False
    epochs: int = 15
    batch: int = 8
    device: Optional[str] = None

@router.post("/auto-curate")
async def auto_curate_evidence():
    """
    Scans all captures in data/evidence/ and auto-curates them with YOLO annotations into the training pool.
    """
    from ml.continuous_learning.auto_curator import AutoCurator
    curator = AutoCurator(project_root=PROJECT_ROOT)
    res = curator.curate_all_evidence()
    return {"status": "success", "curation": res}

@router.get("/training-status")
async def get_training_status():
    """
    Returns live continuous self-training state, device availability, and active production model.
    """
    from ml.continuous_learning.auto_trainer import AutoTrainer
    trainer = AutoTrainer(project_root=PROJECT_ROOT)
    return trainer.get_status()

@router.post("/trigger-self-train")
@router.post("/train")
async def trigger_self_training(background_tasks: BackgroundTasks, req: Optional[SelfTrainRequest] = None):
    """
    Triggers automated continuous fine-tuning pipeline on GPU in the background.
    """
    from ml.continuous_learning.auto_trainer import AutoTrainer, ContinuousLearningConfig
    cfg = ContinuousLearningConfig(
        epochs=req.epochs if req else 15,
        batch=req.batch if req else 8,
        device=req.device if req and req.device else None
    )
    trainer = AutoTrainer(project_root=PROJECT_ROOT, config=cfg)
    force = req.force if req else False

    def run_training_cycle():
        trainer.run_self_training_cycle(force=force)

    background_tasks.add_task(run_training_cycle)
    detected_device = trainer._resolve_device()
    return {
        "status": "training_initiated",
        "device": detected_device,
        "epochs": cfg.epochs,
        "force": force
    }


class PruneEvidenceRequest(BaseModel):
    max_photos: int = 100
    auto_curate_first: bool = True


@router.get("/evidence-retention/status")
async def get_evidence_retention_status():
    """
    Returns diagnostic statistics about evidence photo storage and FIFO retention.
    """
    from services.evidence.retention_manager import EvidenceRetentionManager
    retention = EvidenceRetentionManager(
        evidence_dir="data/evidence",
        max_photos=100,
        project_root=PROJECT_ROOT
    )
    return retention.get_stats()


@router.post("/evidence-retention/prune")
async def prune_evidence_repository(req: Optional[PruneEvidenceRequest] = None):
    """
    Enforces evidence retention limit (default 100 photos).
    Optionally auto-curates unindexed frames before deleting.
    """
    max_photos = req.max_photos if req else 100
    auto_curate = req.auto_curate_first if req else True

    curation_summary = None
    if auto_curate:
        from ml.continuous_learning.auto_curator import AutoCurator
        curator = AutoCurator(project_root=PROJECT_ROOT)
        curation_summary = curator.curate_all_evidence()

    from services.evidence.retention_manager import EvidenceRetentionManager
    retention = EvidenceRetentionManager(
        evidence_dir="data/evidence",
        max_photos=max_photos,
        project_root=PROJECT_ROOT
    )
    deleted = retention.enforce_retention()
    stats = retention.get_stats()

    return {
        "status": "success",
        "deleted_count": deleted,
        "auto_curate_summary": curation_summary,
        "stats": stats
    }

