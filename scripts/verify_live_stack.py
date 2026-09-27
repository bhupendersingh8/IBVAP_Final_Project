import requests
import json
import time
import cv2
import os

print("=== 1. BACKEND HEALTH CHECK ===")
try:
    r = requests.get("http://127.0.0.1:8000/health", timeout=3)
    print(f"Health status: {r.status_code}, response: {r.json()}")
except Exception as e:
    print(f"Health error: {e}")

print("\n=== 2. CAMERAS LIST ===")
try:
    r = requests.get("http://127.0.0.1:8000/api/v1/cameras", timeout=3)
    cams = r.json()
    print(f"Cameras count: {len(cams)}, items: {[c.get('id') for c in cams]}")
except Exception as e:
    print(f"Cameras error: {e}")

print("\n=== 3. LIVE RTSP FRAME CAPTURE (CAM-01) ===")
try:
    cap = cv2.VideoCapture("rtsp://127.0.0.1:8554/CAM-01")
    ret, frame = cap.read()
    if ret:
        print(f"RTSP Capture Success! Frame shape: {frame.shape}, Mean intensity: {frame.mean():.2f}")
        cv2.imwrite("scripts/real_rtsp_snapshot.jpg", frame)
        print("Saved raw frame snapshot to scripts/real_rtsp_snapshot.jpg")
    else:
        print("RTSP Capture returned False")
    cap.release()
except Exception as e:
    print(f"RTSP Capture error: {e}")

print("\n=== 4. SHARED MEMORY / LIVE JPEG ===")
live_jpg = "live_CAM-01.jpg"
if os.path.exists(live_jpg):
    sz = os.path.getsize(live_jpg)
    mtime = time.ctime(os.path.getmtime(live_jpg))
    print(f"{live_jpg} exists: {sz} bytes, mtime: {mtime}")
else:
    print(f"{live_jpg} not found on disk")

print("\n=== 5. EVIDENCE LEDGER INTEGRITY ===")
try:
    r = requests.get("http://127.0.0.1:8000/api/v1/evidence/verify_ledger", timeout=5)
    print(f"Ledger status: {r.status_code}, response: {r.json()}")
except Exception as e:
    print(f"Ledger error: {e}")
