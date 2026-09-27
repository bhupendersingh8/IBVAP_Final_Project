"""
Live Webcam Demo: Real-Time Instance Segmentation + Re-ID Authorization
Runs RT-DETR-R18-Seg + Zero-Copy GPU Bridge + OSNet-x0.25 on Live Camera Feed.

Interactive Controls:
  - 'q' or ESC : Exit webcam demo
  - 'e'        : Enroll the primary detected person into the Authorized Gallery
  - 'm'        : Toggle segmentation mask overlay on/off
  - 's'        : Toggle soft background attenuation vs pure blackout
  - 'c'        : Clear/reset enrolled gallery
"""

import argparse
import os
import sys
import time

import cv2
import numpy as np
import torch
import torch.nn.functional as F

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.models.rtdetr_seg import build_rtdetr_r18_seg
from ml.models.reid_osnet import build_osnet_x0_25, ReIDGalleryManager
from services.inference.realtime_pipeline import RealTimeSegReIDPipeline


def run_webcam(
    camera_id: int = 0,
    video_path: str = "",
    width: int = 640,
    height: int = 640,
    conf_threshold: float = 0.45,
    sim_threshold: float = 0.70,
    device_str: str = "cuda"
):
    device = torch.device(device_str if torch.cuda.is_available() and device_str == "cuda" else "cpu")
    print(f"\n=======================================================")
    print(f" Initializing Real-Time Seg + Re-ID Pipeline")
    print(f" Target Device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")
    print(f"=======================================================\n")

    # Build Pipeline
    gallery = ReIDGalleryManager(similarity_threshold=sim_threshold, device=device)
    
    # Pre-enroll a default authorized identity for demonstration
    dummy_auth_emb = F.normalize(torch.randn(1, 512, device=device), p=2, dim=1)
    gallery.enroll("Authorized_Admin", dummy_auth_emb)

    pipeline = RealTimeSegReIDPipeline(
        person_class_id=0,
        det_conf_threshold=conf_threshold,
        reid_sim_threshold=sim_threshold,
        soft_mask_alpha=0.15,  # Soft dimming preserves edge gradients
        device=device
    )

    # Open Video Capture
    source = video_path if video_path and os.path.exists(video_path) else camera_id
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[Error] Could not open video source: {source}")
        print("Tip: If you do not have an active camera connected, you can specify a video file:")
        print("     python scripts/run_webcam_demo.py --video path/to/video.mp4")
        return

    # Set camera resolution if using hardware camera
    if isinstance(source, int):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("\nLive Webcam Stream Started!")
    print("Press 'e' to ENROLL detected person into Authorized Gallery.")
    print("Press 'm' to TOGGLE mask visualization.")
    print("Press 's' to TOGGLE soft background dimming vs hard blackout.")
    print("Press 'q' to QUIT.\n")

    show_mask = True
    enroll_count = 1
    fps_smooth = 0.0

    while True:
        ret, frame_bgr = cap.read()
        if not ret:
            print("[Info] Video stream ended or frame could not be read.")
            break

        orig_h, orig_w = frame_bgr.shape[:2]

        # Preprocess frame to 640x640 tensor directly for RT-DETR
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        resized_rgb = cv2.resize(rgb, (width, height))
        img_tensor = torch.from_numpy(resized_rgb).permute(2, 0, 1).unsqueeze(0).float() / 255.0
        img_tensor = img_tensor.to(device)

        # Process through end-to-end pipeline
        t0 = time.perf_counter()
        results = pipeline.process_frame(img_tensor)
        dt = (time.perf_counter() - t0) * 1000.0

        current_fps = 1000.0 / max(dt, 1e-3)
        fps_smooth = 0.9 * fps_smooth + 0.1 * current_fps if fps_smooth > 0 else current_fps

        # Visual Canvas
        canvas = frame_bgr.copy()
        scale_x = orig_w / float(width)
        scale_y = orig_h / float(height)

        persons = results["persons"]
        for p in persons:
            # Scale box coordinates back to original frame size
            bx1 = int(p["bbox"][0] * scale_x)
            by1 = int(p["bbox"][1] * scale_y)
            bx2 = int(p["bbox"][2] * scale_x)
            by2 = int(p["bbox"][3] * scale_y)

            is_auth = p["authorized"]
            name = p["identity"]
            score = p["reid_similarity"]
            det_score = p["det_score"]

            color = (0, 220, 0) if is_auth else (0, 0, 240)  # Green for Auth, Red for Unauth
            status_text = f"AUTHORIZED: {name} ({score:.2f})" if is_auth else f"UNAUTHORIZED ({score:.2f})"

            # Draw Bounding Box
            cv2.rectangle(canvas, (bx1, by1), (bx2, by2), color, 2)

            # Draw Label Header
            label_bg_y = max(0, by1 - 25)
            cv2.rectangle(canvas, (bx1, label_bg_y), (bx1 + 280, by1), color, -1)
            cv2.putText(canvas, status_text, (bx1 + 5, by1 - 7),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2)

        # Draw HUD Telemetry Header
        hud_bg = canvas.copy()
        cv2.rectangle(hud_bg, (10, 10), (450, 125), (20, 20, 20), -1)
        canvas = cv2.addWeighted(hud_bg, 0.75, canvas, 0.25, 0)

        timings = results["timings_ms"]
        cv2.putText(canvas, f"FPS: {fps_smooth:.1f}  |  Total: {timings['total']:.1f}ms",
                    (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 200), 2)
        cv2.putText(canvas, f"Seg: {timings['seg']:.1f}ms | Bridge: {timings['bridge']:.1f}ms | Re-ID: {timings['reid']:.1f}ms",
                    (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 200, 200), 1)
        cv2.putText(canvas, f"People Detected: {len(persons)} | Enrolled IDs: {len(gallery.names)}",
                    (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 1)
        cv2.putText(canvas, f"[E] Enroll Face | [S] SoftMask: {pipeline.soft_mask_alpha > 0} | [Q] Quit",
                    (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 230, 255), 1)

        # Show Output Window
        cv2.imshow("RT-DETR-Seg + Re-ID Live Authorization Pipeline", canvas)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('e') or key == ord('E'):
            # Live Enrollment: Extract crops from primary detection and enroll into gallery
            if len(persons) > 0:
                print(f"[Enrollment] Enrolling Person as 'Authorized_User_{enroll_count}'...")
                # Re-extract crop and generate embedding
                primary_box = torch.tensor([persons[0]["bbox"]], device=device, dtype=torch.float32)
                # Quick crop for enrollment
                x1, y1, x2, y2 = [int(v) for v in persons[0]["bbox"]]
                crop = frame_bgr[max(0, y1):min(orig_h, y2), max(0, x1):min(orig_w, x2)]
                if crop.size > 0:
                    crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                    crop_res = cv2.resize(crop_rgb, (128, 256))
                    crop_t = torch.from_numpy(crop_res).permute(2, 0, 1).unsqueeze(0).float() / 255.0
                    crop_t = ((crop_t.to(device) - pipeline.mean) / pipeline.std)
                    with torch.no_grad():
                        emb = pipeline.reid_model(crop_t)
                    gallery.enroll(f"Authorized_User_{enroll_count}", emb)
                    print(f" -> Enrolled 'Authorized_User_{enroll_count}'! Total Gallery: {len(gallery.names)}")
                    enroll_count += 1
            else:
                print("[Enrollment Warning] No person detected in frame to enroll.")
        elif key == ord('s') or key == ord('S'):
            pipeline.soft_mask_alpha = 0.0 if pipeline.soft_mask_alpha > 0.0 else 0.15
            print(f"[Settings] Soft mask alpha set to: {pipeline.soft_mask_alpha}")
        elif key == ord('c') or key == ord('C'):
            gallery.names = []
            gallery.embeddings = None
            print("[Settings] Gallery cleared!")

    cap.release()
    cv2.destroyAllWindows()
    print("[Shutdown] Webcam stream terminated cleanly.")


def main():
    parser = argparse.ArgumentParser(description="Live Webcam Demo for RT-DETR-Seg + Re-ID")
    parser.add_argument("--camera", type=int, default=0, help="Camera device index (default: 0)")
    parser.add_argument("--video", type=str, default="", help="Path to video file instead of live camera")
    parser.add_argument("--conf", type=float, default=0.45, help="Detection confidence threshold")
    parser.add_argument("--sim", type=float, default=0.70, help="Re-ID cosine similarity threshold")
    parser.add_argument("--device", type=str, default="cuda", choices=["cuda", "cpu"], help="Inference device")
    args = parser.parse_args()

    run_webcam(
        camera_id=args.camera,
        video_path=args.video,
        conf_threshold=args.conf,
        sim_threshold=args.sim,
        device_str=args.device
    )


if __name__ == "__main__":
    main()
