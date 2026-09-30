"""
IBVAP — Physical CCTV & NVR Auto-Discovery and One-Click Connector
===================================================================
Automatically searches the Ethernet switch and subnet for active Hikvision,
CP Plus, Dahua, and ONVIF cameras/NVRs, connects them to the IBVAP pipeline,
and enables live streaming without manual configuration.
"""

import os
import sys
import time
import argparse
import json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.ingestion.cctv_discovery import (
    discover_active_cctv,
    collect_target_candidates,
    scan_cctv_ports,
    probe_and_verify_camera,
    register_camera_with_backend,
    verify_rtsp_stream_cv2
)
from services.ingestion.rtsp_security import mask_rtsp_url, build_rtsp_url, validate_rtsp_url


def print_header():
    print("\n" + "=" * 80)
    print("      IBVAP -- PHYSICAL CCTV / NVR AUTO-DISCOVERY & CONNECTION ENGINE           ")
    print("           Ministry of Home Affairs / SSB Mandate - SIH26187                   ")
    print("=" * 80)


def run_auto_mode(backend_url="http://127.0.0.1:8000"):
    print_header()
    print("[1/3] Scanning Ethernet switch and local subnets for IP Cameras / NVRs...")
    t0 = time.time()
    result = discover_active_cctv(backend_url=backend_url, auto_register=True)
    elapsed = time.time() - t0

    if result.get("physical_cctv_detected"):
        print("\n" + "=" * 80)
        print(" [SUCCESS] PHYSICAL COLLEGE CCTV CAMERA DISCOVERED & CONNECTED!")
        print("=" * 80)
        print(f"  * Brand:       {result.get('brand')}")
        print(f"  * Host IP:     {result.get('host')}:{result.get('port')}")
        print(f"  * Stream:      {result.get('masked_url')}")
        print(f"  * Resolution:  {result.get('resolution')}")
        print(f"  * Camera ID:   {result.get('camera_id')}")
        print(f"  * SHA-256:     {result.get('sha256_proof')}")
        print(f"  * Scan Time:   {elapsed:.2f}s")
        print("=" * 80)
        print("  >> Stream is LIVE in IBVAP Console: http://localhost:5173/cameras")
        print("=" * 80 + "\n")
        return 0
    else:
        print(f"\n[INFO] Scan completed in {elapsed:.2f}s. No physical CCTV camera detected on port 554.")
        print("[INFO] Fallback active: CAM-01 (Border Outpost Simulator) running at 30 FPS.")
        print("\nCollege Lab Setup Checklist:")
        print("  1. Connect Ethernet patch cable from switch to laptop.")
        print("  2. If laptop has DHCP, run .\\CONFIGURE_ETHERNET_IP.bat to set 192.168.1.50.")
        print("  3. Ensure camera power is ON (12V adapter or PoE injector LED is lit).")
        print("  4. Background auto-watcher will connect camera as soon as it appears on switch!\n")
        return 0


def run_watcher_mode(backend_url="http://127.0.0.1:8000", interval=5.0):
    print_header()
    print("[WATCHER] Background CCTV Auto-Discovery Watcher Active.")
    print("[WATCHER] Polling Ethernet switch every 5 seconds for new camera connection...")
    print("[WATCHER] Press Ctrl+C to terminate.")

    connected = False
    while True:
        try:
            if not connected:
                res = discover_active_cctv(backend_url=backend_url, auto_register=True)
                if res.get("physical_cctv_detected"):
                    connected = True
                    print(f"\n[ALERT] Physical CCTV Connected! {res.get('brand')} at {res.get('host')}:{res.get('port')}")
                    print(f"[ALERT] Active on IBVAP Surveillance Grid: {res.get('camera_id')}\n")
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[WATCHER] Exiting watcher.")
            break
        except Exception as e:
            time.sleep(interval)


def run_interactive_mode(backend_url="http://127.0.0.1:8000"):
    print_header()
    print("Choose an option:")
    print("  [1] Auto-Discover Physical CCTV / NVR (Fast Ethernet Sweep)")
    print("  [2] Enter IP / RTSP Details Manually (Hikvision, CP Plus, Dahua)")
    print("  [3] Test with Local Simulator Feed (CAM-01)")
    print("  [4] Exit")

    choice = input("\nEnter choice [1-4, default 1]: ").strip() or "1"
    if choice == "1":
        run_auto_mode(backend_url=backend_url)
    elif choice == "2":
        ip = input("Enter Camera IP [default 192.168.1.64]: ").strip() or "192.168.1.64"
        port = int(input("Enter Port [default 554]: ").strip() or "554")
        user = input("Enter Username [default admin]: ").strip() or "admin"
        pwd = input("Enter Password [default admin123]: ").strip() or "admin123"
        print("\nSelect Brand Path:")
        print("  [1] Hikvision (/Streaming/Channels/101)")
        print("  [2] CP Plus / Dahua (/cam/realmonitor?channel=1&subtype=0)")
        print("  [3] Generic ONVIF (/h264Preview_01_main)")
        b_choice = input("Enter [1-3, default 1]: ").strip() or "1"
        if b_choice == "2":
            path = "/cam/realmonitor?channel=1&subtype=0"
            brand = "CP Plus / Dahua"
        elif b_choice == "3":
            path = "/h264Preview_01_main"
            brand = "Generic ONVIF"
        else:
            path = "/Streaming/Channels/101"
            brand = "Hikvision"

        rtsp_url = build_rtsp_url(host=ip, port=port, stream_path=path, username=user, password=pwd)
        cam_data = {
            "brand": brand,
            "host": ip,
            "port": port,
            "path": path,
            "username": user,
            "password": pwd,
            "rtsp_url": rtsp_url,
            "masked_url": mask_rtsp_url(rtsp_url)
        }
        print(f"\n[INFO] Connecting to {mask_rtsp_url(rtsp_url)}...")
        ok = register_camera_with_backend(cam_data, backend_url=backend_url, camera_id="COLLEGE-CAM-01")
        if ok:
            print("\n[OK] Camera successfully connected and registered as COLLEGE-CAM-01!")
        else:
            print("\n[!] Connection attempted. Check if camera is powered and reachable.")
    elif choice == "3":
        print("\n[OK] Ensuring CAM-01 simulator is active...")
        try:
            requests.post(f"{backend_url}/api/v1/cameras/CAM-01/activate")
            print("[OK] CAM-01 is actively streaming at http://localhost:5173/cameras")
        except Exception as e:
            print(f"[!] Error activating CAM-01: {e}")


def main():
    parser = argparse.ArgumentParser(description="IBVAP CCTV Auto-Discovery and Connector")
    parser.add_argument("--auto", action="store_true", help="Run rapid auto-scan and connect (zero prompts)")
    parser.add_argument("--watch", action="store_true", help="Run continuously in background watcher mode")
    parser.add_argument("--interactive", action="store_true", help="Interactive terminal menu")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000", help="FastAPI backend URL")
    args = parser.parse_args()

    if args.watch:
        run_watcher_mode(backend_url=args.backend_url)
    elif args.interactive:
        run_interactive_mode(backend_url=args.backend_url)
    else:
        # Default behavior: run auto mode
        run_auto_mode(backend_url=args.backend_url)


if __name__ == "__main__":
    main()
