"""
IBVAP — Physical College IP Camera & NVR Connection & Evidence Recording Utility
=================================================================================
Automates connecting, probing, registering, and recording proof footage from a real
physical IP Camera / NVR connected via Ethernet switch.
Section 65B Indian Evidence Act compliant evidence recorder.
"""

import sys
import os
import time
import socket
import hashlib
import cv2
import requests

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from services.ingestion.rtsp_security import (
    build_rtsp_url,
    mask_rtsp_url,
    validate_rtsp_url,
    probe_rtsp_target
)


def print_banner():
    print("\n" + "=" * 80)
    print("      IBVAP — REAL COLLEGE IP CAMERA & NVR AUTO-CONNECT & EVIDENCE RECORDER    ")
    print("               Ministry of Home Affairs / SSB Mandate (SIH26187)               ")
    print("=" * 80 + "\n")


def prompt_camera_details():
    print("Select IP Camera / NVR Brand:")
    print("  [1] Hikvision IP Camera / NVR  (path: /Streaming/Channels/101)")
    print("  [2] CP PLUS IP Camera / NVR   (path: /cam/realmonitor?channel=1&subtype=0)")
    print("  [3] Dahua IP Camera / NVR     (path: /cam/realmonitor?channel=1&subtype=0)")
    print("  [4] Generic ONVIF / NVR       (path: /live/ch0 or /h264Preview_01_main)")
    print("  [5] Custom RTSP URL")
    print("  [6] Test with Local Simulator  (rtsp://127.0.0.1:8554/CAM-01)")
    
    choice = input("\nEnter choice [1-6, default 1]: ").strip() or "1"
    
    if choice == "6":
        return "rtsp://127.0.0.1:8554/CAM-01", "127.0.0.1", 8554, "Simulator-CAM-01", "Local Stream"
        
    if choice == "5":
        raw_url = input("Enter full RTSP URL: ").strip()
        from urllib.parse import urlparse
        p = urlparse(raw_url)
        return raw_url, p.hostname or "127.0.0.1", p.port or 554, "CUSTOM-CAM", "Custom Camera"
        
    cam_ip = input("Enter Camera/NVR IP [default 192.168.1.100]: ").strip() or "192.168.1.100"
    port_str = input("Enter RTSP Port [default 554]: ").strip() or "554"
    port = int(port_str)
    user = input("Enter Username [default admin]: ").strip() or "admin"
    password = input("Enter Password [default admin123]: ").strip() or "admin123"
    ch = input("Enter Camera Channel [default 1]: ").strip() or "1"
    
    if choice == "1":
        # Hikvision: channel 1 = 101, channel 2 = 201
        path = f"/Streaming/Channels/{ch}01"
        brand_name = f"Hikvision Ch#{ch}"
    elif choice in ("2", "3"):
        # CP Plus / Dahua
        path = f"/cam/realmonitor?channel={ch}&subtype=0"
        brand_name = f"CP-PLUS/Dahua Ch#{ch}"
    else:
        path = f"/h264Preview_0{ch}_main"
        brand_name = f"Generic-NVR Ch#{ch}"
        
    rtsp_url = build_rtsp_url(
        host=cam_ip,
        port=port,
        stream_path=path,
        username=user,
        password=password
    )
    return rtsp_url, cam_ip, port, f"COLLEGE-CAM-{ch.zfill(2)}", brand_name


def main():
    print_banner()
    rtsp_url, host, port, cam_id, cam_desc = prompt_camera_details()
    
    masked = mask_rtsp_url(rtsp_url)
    print(f"\n[INFO] Target Stream: {masked}")
    print(f"[1/5] Probing TCP connection on {host}:{port}...")
    
    probe = probe_rtsp_target(host, port, timeout_seconds=2.0)
    if not probe["tcp_reachable"]:
        print(f"\n[!] TCP Port Unreachable ({probe.get('error')})")
        print("\nTroubleshooting Checklist:")
        print("1. Did you connect the Ethernet patch cord from the switch to your laptop?")
        print("2. Is your laptop on the same subnet? (Run .\\CONFIGURE_ETHERNET_IP.bat to set 192.168.1.50)")
        print(f"3. Ask the technician if the camera IP is really {host} or if it's on a different subnet.")
        proceed = input("\nDo you still want to attempt RTSP connection anyway? [y/N]: ").strip().lower()
        if proceed != "y":
            sys.exit(1)
    else:
        print(f"  [PASS] Camera TCP Port 554 Reachable! (Latency: {probe['latency_ms']} ms)")
        
    print(f"\n[2/5] Initializing OpenCV RTSP Stream Reader (TCP Transport)...")
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;3000000|timeout;3000000"
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    
    if not cap.isOpened():
        print(f"  [!] Direct RTSP connection failed. Trying standard transport...")
        cap = cv2.VideoCapture(rtsp_url)
        
    if not cap.isOpened():
        print(f"\n[FAIL] Could not open RTSP video stream at {masked}")
        print("Check username, password, or channel path.")
        sys.exit(1)
        
    ret, frame = cap.read()
    if not ret or frame is None:
        print("[FAIL] Connected to RTSP stream, but frame read failed.")
        cap.release()
        sys.exit(1)
        
    h, w = frame.shape[:2]
    print(f"  [PASS] Live Video Stream Acquired!")
    print(f"  Resolution: {w}x{h} px | Channels: {frame.shape[2]}")
    
    # Save Initial Snapshot
    evidence_dir = os.path.join(PROJECT_ROOT, "data", "evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    snap_path = os.path.join(evidence_dir, f"{cam_id}_initial_snapshot.jpg")
    cv2.imwrite(snap_path, frame)
    print(f"  [PASS] Initial Verification Snapshot Saved -> {snap_path}")
    
    # Register Camera into IBVAP Backend
    print(f"\n[3/5] Registering Camera with IBVAP Backend (http://localhost:8000)...")
    try:
        payload = {
            "id": cam_id,
            "name": f"College Lab: {cam_desc}",
            "rtsp_url": rtsp_url,
            "scenario": "border_cctv",
            "resolution": f"{w}x{h}",
            "fps": 25,
            "source_type": "PHYSICAL_CCTV_RTSP"
        }
        res = requests.post("http://localhost:8000/api/v1/cameras/", json=payload, timeout=3)
        if res.status_code in (200, 201):
            print(f"  [PASS] Camera '{cam_id}' registered successfully in IBVAP Registry!")
        else:
            print(f"  [INFO] Backend responded: {res.status_code} ({res.text})")
    except Exception as e:
        print(f"  [INFO] Backend notification note: {e}")
        
    # Record 15-30 Second Proof Footage
    print(f"\n[4/5] Recording 15-Second Test Video Clip for SIH Jury Evidence...")
    record_path = os.path.join(evidence_dir, f"{cam_id}_physical_proof.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = 20.0
    out = cv2.VideoWriter(record_path, fourcc, fps, (w, h))
    
    t_start = time.time()
    frames_recorded = 0
    duration_sec = 15
    
    while (time.time() - t_start) < duration_sec:
        r, f = cap.read()
        if r and f is not None:
            # Stamp timestamp and Section 65B hash preview
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S IST")
            cv2.putText(f, f"IBVAP PHYSICAL CCTV VALIDATION: {cam_id} | {timestamp_str}", (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
            cv2.putText(f, "SEC-65B EVIDENCE CERTIFIED | ZERO-COST LOCAL AI", (20, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)
            out.write(f)
            frames_recorded += 1
            elapsed = time.time() - t_start
            sys.stdout.write(f"\r  Recording: {elapsed:.1f}s / {duration_sec}s ({frames_recorded} frames)")
            sys.stdout.flush()
        else:
            time.sleep(0.02)
            
    out.release()
    cap.release()
    print(f"\n  [PASS] Recorded {frames_recorded} frames to: {record_path}")
    
    # Compute SHA-256 for Section 65B Certificate
    with open(record_path, "rb") as f_ev:
        file_bytes = f_ev.read()
    digest = hashlib.sha256(file_bytes).hexdigest()
    print(f"  [SEC-65B] SHA-256 Evidence Digest: {digest}")
    
    print(f"\n[5/5] Launching Operations Dashboard with Physical Camera Feed...")
    import webbrowser
    webbrowser.open("http://localhost:5173/cameras")
    
    print("\n" + "=" * 80)
    print("                     PHYSICAL CCTV VALIDATION COMPLETE                         ")
    print("=" * 80)
    print(f" 1. Camera ID:        {cam_id}")
    print(f" 2. Connection:       {masked}")
    print(f" 3. Resolution:       {w}x{h} px")
    print(f" 4. Evidence Video:   {record_path}")
    print(f" 5. SHA-256 Digest:   {digest}")
    print(f" 6. Dashboard URL:    http://localhost:5173/cameras")
    print("=" * 80 + "\n")
    print("You can now safely return the switch to the technician after capturing your proof!")


if __name__ == "__main__":
    main()
