"""
Live Camera & Multi-Camera Reality Test for IBVAP.
Tests real camera streams (CAM-01 RTSP and PHONE-CAM-01 IP-Cam),
measures real resolution, source FPS, and verifies health state transitions.
"""
import sys
import time
import cv2
import urllib.request
import json

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from services.ingestion.camera_health import CameraHealthMonitor, CameraHealthState

results = {}

# 1. Test CAM-01 (MediaMTX RTSP stream)
rtsp_url = "rtsp://127.0.0.1:8554/CAM-01"
cap_rtsp = cv2.VideoCapture(rtsp_url)
t0 = time.time()
rtsp_frames = 0
w_rtsp, h_rtsp = 0, 0

if cap_rtsp.isOpened():
    for _ in range(15):
        ret, frame = cap_rtsp.read()
        if ret and frame is not None:
            rtsp_frames += 1
            h_rtsp, w_rtsp = frame.shape[:2]
    elapsed = time.time() - t0
    measured_fps = round(rtsp_frames / elapsed, 2) if elapsed > 0 else 0
    cap_rtsp.release()
    results["CAM-01"] = {
        "status": "ONLINE",
        "url": rtsp_url,
        "resolution": f"{w_rtsp}x{h_rtsp}",
        "frames_received": rtsp_frames,
        "elapsed_sec": round(elapsed, 2),
        "source_fps": measured_fps,
    }
else:
    results["CAM-01"] = {
        "status": "OFFLINE",
        "url": rtsp_url,
        "error": "Failed to open RTSP stream"
    }

# 2. Test PHONE-CAM-01 (Dynamic URL from system_settings.json)
settings_path = PROJECT_ROOT / "configs" / "system_settings.json"
phone_url = "http://192.168.1.5:8080/video"
if settings_path.exists():
    try:
        with open(settings_path, "r", encoding="utf-8") as f_s:
            s_data = json.load(f_s)
            phone_url = s_data.get("phone_camera_url", phone_url)
    except Exception:
        pass
phone_reachable = False
try:
    req = urllib.request.Request(phone_url, headers={"User-Agent": "IBVAP-Auditor/1.0"})
    with urllib.request.urlopen(req, timeout=1.0) as resp:
        phone_reachable = (resp.status == 200)
        phone_content_type = resp.headers.get("Content-Type")
except Exception as e:
    phone_reachable = False
    phone_error = str(e)

if phone_reachable:
    cap_phone = cv2.VideoCapture(phone_url)
    t0_p = time.time()
    phone_frames = 0
    w_p, h_p = 0, 0
    if cap_phone.isOpened():
        for _ in range(10):
            ret, frame = cap_phone.read()
            if ret and frame is not None:
                phone_frames += 1
                h_p, w_p = frame.shape[:2]
        elapsed_p = time.time() - t0_p
        cap_phone.release()
        results["PHONE-CAM-01"] = {
            "status": "ONLINE",
            "url": phone_url,
            "resolution": f"{w_p}x{h_p}",
            "frames_received": phone_frames,
            "elapsed_sec": round(elapsed_p, 2),
            "source_fps": round(phone_frames / elapsed_p, 2) if elapsed_p > 0 else 0
        }
    else:
        results["PHONE-CAM-01"] = {
            "status": "REACHABLE_BUT_CV2_FAILED",
            "url": phone_url,
        }
else:
    results["PHONE-CAM-01"] = {
        "status": "OFFLINE_OR_UNREACHABLE",
        "url": phone_url,
        "error": phone_error if 'phone_error' in locals() else "Timeout/ConnectionRefused"
    }

# 3. Test CameraHealthMonitor state machine transition under simulated interruption
monitor = CameraHealthMonitor()
monitor.register("CAM-01")
monitor.register("PHONE-CAM-01")

# Baseline ONLINE
monitor.update("CAM-01", frame_received=True, fps=15.0)
monitor.update("PHONE-CAM-01", frame_received=True, fps=10.0)
s1 = monitor.get_all_health()

# Interruption: PHONE-CAM-01 disconnects
monitor.mark_reconnecting("PHONE-CAM-01")
s2 = monitor.get_all_health()

# Recovery: PHONE-CAM-01 reconnects
monitor.update("PHONE-CAM-01", frame_received=True, fps=12.0)
s3 = monitor.get_all_health()

results["camera_health_state_machine"] = {
    "step1_baseline": {
        "CAM-01": s1["CAM-01"]["state"],
        "PHONE-CAM-01": s1["PHONE-CAM-01"]["state"]
    },
    "step2_interruption": {
        "CAM-01": s2["CAM-01"]["state"],
        "PHONE-CAM-01": s2["PHONE-CAM-01"]["state"]
    },
    "step3_recovery": {
        "CAM-01": s3["CAM-01"]["state"],
        "PHONE-CAM-01": s3["PHONE-CAM-01"]["state"]
    },
    "non_crashing_recovery": (
        s1["PHONE-CAM-01"]["state"] == "ONLINE" and
        s2["PHONE-CAM-01"]["state"] == "RECONNECTING" and
        s3["PHONE-CAM-01"]["state"] == "ONLINE"
    )
}

print(json.dumps(results, indent=2))
