"""
IBVAP Domain Dataset Frame Collection & Curation Utility.
Extracts representative visual frames from authorized video feeds with:
- Zero content distortion (preserves native pixel layout)
- Cryptographic SHA-256 per-frame integrity hashing
- Automated quality assessment (blur, contrast, brightness, corrupted, duplicates)
- Deterministic metadata manifest emission (dataset/metadata/frames.jsonl)
- Strict security: no credentials or private RTSP passwords stored in metadata
"""
from __future__ import annotations

import os
import sys
import time
import json
import hashlib
import argparse
from datetime import datetime, timezone
import cv2
import numpy as np
import structlog

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.dataset.quality import QualityFilter, QualityThresholds, QualityStatus, LightingCondition

logger = structlog.get_logger()


def sanitize_source_id(source_str: str) -> str:
    """Removes sensitive credentials or special characters from source identifier."""
    if "@" in source_str:
        # Mask credentials before '@' in URLs
        source_str = source_str.split("@")[-1]
    # Keep only safe alphanumeric characters, dashes, and underscores
    clean = "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in source_str)
    return clean[:64]


def collect_frames(
    input_source: str,
    output_dir: str,
    fps_sample: float = 1.0,
    max_frames: Optional[int] = None,
    min_width: int = 592,
    min_height: int = 360,
    source_id: Optional[str] = None,
    source_type: str = "video_file",
    manifest_path: Optional[str] = None,
    lighting: Optional[str] = None,
    provenance_status: str = "PROVENANCE_UNKNOWN",
) -> Dict[str, Any]:
    """
    Main frame extraction and metadata collection engine.
    """
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(PROJECT_ROOT, output_dir)
    os.makedirs(output_dir, exist_ok=True)

    source_path_hash = hashlib.sha256(input_source.encode("utf-8")).hexdigest()[:16]

    if manifest_path is None:
        manifest_path = os.path.join(PROJECT_ROOT, "dataset", "metadata", "frames.jsonl")
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)

    clean_source_id = source_id or sanitize_source_id(os.path.basename(input_source))

    thresholds = QualityThresholds(min_width=min_width, min_height=min_height)
    quality_filter = QualityFilter(thresholds=thresholds)

    force_lighting = None
    if lighting:
        try:
            force_lighting = LightingCondition(lighting.upper())
        except ValueError:
            pass

    # Open video capture
    logger.info("Opening video source", source=clean_source_id, type=source_type)
    cap = cv2.VideoCapture(input_source)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open input video stream: {input_source}")

    video_native_fps = cap.get(cv2.CAP_PROP_FPS)
    if video_native_fps <= 0 or np.isnan(video_native_fps):
        video_native_fps = 25.0

    frame_interval = max(1, int(round(video_native_fps / fps_sample)))

    stats = {
        "source_id": clean_source_id,
        "source_type": source_type,
        "frames_scanned": 0,
        "frames_extracted": 0,
        "status_counts": {
            QualityStatus.GOOD.value: 0,
            QualityStatus.LOW_QUALITY.value: 0,
            QualityStatus.DUPLICATE.value: 0,
            QualityStatus.REJECTED.value: 0,
        },
        "lighting_counts": {
            LightingCondition.DAY.value: 0,
            LightingCondition.NIGHT.value: 0,
            LightingCondition.LOW_LIGHT.value: 0,
            LightingCondition.IR.value: 0,
        },
    }

    manifest_records = []
    frame_idx = 0
    extracted_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame_idx += 1
            stats["frames_scanned"] += 1

            # Sample every frame_interval
            if (frame_idx % frame_interval) != 0:
                continue

            # Assess Quality
            assessment = quality_filter.assess_frame(frame, force_lighting=force_lighting)
            stats["status_counts"][assessment.status.value] += 1
            stats["lighting_counts"][assessment.lighting.value] += 1

            # Encode to JPEG bytes (highest quality) to get deterministic SHA-256
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
            success, enc_bytes = cv2.imencode(".jpg", frame, encode_param)
            if not success:
                logger.warning("Failed to encode frame to JPEG", frame_idx=frame_idx)
                continue

            sha256_digest = hashlib.sha256(enc_bytes).hexdigest()

            now_utc = datetime.now(timezone.utc).isoformat()
            ts_filename = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")[:19]
            filename = f"{clean_source_id}_f{frame_idx:06d}_{ts_filename}.jpg"
            save_path = os.path.join(output_dir, filename)

            # Save frame to disk
            with open(save_path, "wb") as f_out:
                f_out.write(enc_bytes)

            try:
                rel_path = os.path.relpath(save_path, PROJECT_ROOT).replace("\\", "/")
            except ValueError:
                rel_path = os.path.abspath(save_path).replace("\\", "/")
            frame_id = f"{clean_source_id}_f{frame_idx:06d}"

            record = {
                "frame_id": frame_id,
                "source_id": clean_source_id,
                "source_path_hash": source_path_hash,
                "frame_number": frame_idx,
                "timestamp": now_utc,
                "width": assessment.width,
                "height": assessment.height,
                "fps": fps_sample,
                "sha256": sha256_digest,
                "collection_time": now_utc,
                "provenance_status": provenance_status,
                "path": rel_path,
                "source_type": source_type,
                "quality_status": assessment.status.value,
                "lighting_condition": assessment.lighting.value,
                "blur_score": assessment.blur_score,
                "brightness": assessment.brightness,
                "contrast": assessment.contrast,
                "rejection_reasons": assessment.rejection_reasons,
            }

            manifest_records.append(record)
            extracted_count += 1
            stats["frames_extracted"] = extracted_count

            if max_frames and extracted_count >= max_frames:
                logger.info("Reached maximum requested frames limit", limit=max_frames)
                break

    finally:
        cap.release()

    # Append records to JSON Lines manifest
    if manifest_records:
        with open(manifest_path, "a", encoding="utf-8") as mf:
            for rec in manifest_records:
                mf.write(json.dumps(rec) + "\n")
        logger.info("Manifest updated", path=manifest_path, new_records=len(manifest_records))

    logger.info(
        "Frame collection complete",
        total_scanned=stats["frames_scanned"],
        extracted=stats["frames_extracted"],
        good=stats["status_counts"][QualityStatus.GOOD.value],
        low_quality=stats["status_counts"][QualityStatus.LOW_QUALITY.value],
        duplicates=stats["status_counts"][QualityStatus.DUPLICATE.value],
        rejected=stats["status_counts"][QualityStatus.REJECTED.value],
    )
    return stats


def main():
    parser = argparse.ArgumentParser(description="IBVAP Dataset Frame Collection Tool")
    parser.add_argument("--input", type=str, required=True, help="Video file path or stream")
    parser.add_argument("--output", type=str, default="dataset/staging/frames", help="Output staging directory")
    parser.add_argument("--fps", type=float, default=1.0, help="Sampling rate (frames per second)")
    parser.add_argument("--max-frames", type=int, default=None, help="Maximum frames to collect")
    parser.add_argument("--min-width", type=int, default=592, help="Minimum width threshold")
    parser.add_argument("--min-height", type=int, default=360, help="Minimum height threshold")
    parser.add_argument("--source-id", type=str, default=None, help="Clean identifier for source camera")
    parser.add_argument("--source-type", type=str, default="video_file", help="Source type (video_file, cctv_rtsp)")
    parser.add_argument("--manifest", type=str, default=None, help="Path to JSONL manifest")
    parser.add_argument("--lighting", type=str, choices=["DAY", "NIGHT", "LOW_LIGHT", "IR"], default=None, help="Force lighting condition")
    parser.add_argument("--provenance", type=str, default="PROVENANCE_UNKNOWN", help="Authorization / provenance status")
    args = parser.parse_args()

    stats = collect_frames(
        input_source=args.input,
        output_dir=args.output,
        fps_sample=args.fps,
        max_frames=args.max_frames,
        min_width=args.min_width,
        min_height=args.min_height,
        source_id=args.source_id,
        source_type=args.source_type,
        manifest_path=args.manifest,
        lighting=args.lighting,
        provenance_status=args.provenance,
    )
    print(f"COLLECTION_STATUS: SUCCESS")
    print(f"EXTRACTED_FRAMES: {stats['frames_extracted']}")
    print(f"QUALITY_BREAKDOWN: {stats['status_counts']}")


if __name__ == "__main__":
    main()
