import cv2
import time

cap = cv2.VideoCapture("rtsp://127.0.0.1:8554/CAM-01")
t0 = time.time()
frames = 0
res = "unknown"

while time.time() - t0 < 3.0:
    ret, f = cap.read()
    if ret and f is not None:
        frames += 1
        res = f"{f.shape[1]}x{f.shape[0]}"

elapsed = time.time() - t0
cap.release()
print(f"CAM-01 Decoded: {frames} frames in {elapsed:.2f}s | Resolution: {res} | Effective FPS: {frames/elapsed:.2f}")
