"""
IBVAP - Automated Physical CCTV & NVR Discovery and Auto-Connection Service
==========================================================================
Scans local network interfaces, Windows ARP cache, and standard CCTV factory IP
ranges (Hikvision, CP Plus, Dahua, Generic ONVIF) to automatically detect,
verify, register, and stream live footage without requiring manual user input.
"""

import os
import sys
import time
import socket
import re
import subprocess
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import cv2
import requests

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.ingestion.rtsp_security import (
    build_rtsp_url,
    mask_rtsp_url,
    validate_rtsp_url,
    probe_rtsp_target,
    RTSPCameraConfig,
    RTSPRuntimeRegistry
)

COMMON_CAMERA_FACTORY_IPS = [
    # Hikvision defaults
    "192.168.1.64",
    "192.168.0.64",
    # Dahua / CP Plus defaults
    "192.168.1.108",
    "192.168.0.108",
    # Common NVR / Lab / Router Assigned IPs
    "192.168.1.100",
    "192.168.0.100",
    "192.168.1.10",
    "192.168.1.200",
    "192.168.1.250",
    "192.168.0.10",
    "192.168.0.200",
    "192.168.1.101",
    "192.168.1.102",
    "192.168.1.2",
    "192.168.1.3",
    "192.168.1.4",
    "192.168.1.5",
]

COMMON_CREDENTIALS = [
    ("admin", "admin123"),
    ("admin", "12345"),
    ("admin", "admin"),
    ("admin", "123456"),
    ("admin", "password"),
    (None, None),  # Anonymous / open RTSP
]

BRAND_STREAM_TEMPLATES = [
    {
        "brand": "Hikvision",
        "paths": [
            "/Streaming/Channels/101",
            "/Streaming/Channels/1",
            "/h264/ch1/main/av_stream",
        ]
    },
    {
        "brand": "CP Plus / Dahua",
        "paths": [
            "/cam/realmonitor?channel=1&subtype=0",
            "/cam/realmonitor?channel=1&subtype=1",
            "/live",
        ]
    },
    {
        "brand": "Generic ONVIF / NVR",
        "paths": [
            "/h264Preview_01_main",
            "/live/ch0",
            "/onvif1",
            "/ch0_unicast_firststream",
            "/mpeg4/ch0",
            "/",
        ]
    }
]


def get_arp_ips() -> List[str]:
    """Extracts active unicast private IPv4 addresses from Windows ARP table."""
    candidates = []
    try:
        out = subprocess.check_output("arp -a", shell=True, timeout=2.0).decode("utf-8", errors="ignore")
        found = re.findall(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", out)
        for ip in found:
            # Filter out broadcast (255), multicast (224-239), loopback (127), and link-local (169.254)
            parts = [int(p) for p in ip.split(".")]
            if parts[0] in (10, 172, 192) and parts[3] not in (0, 255):
                if parts[0] == 192 and parts[1] == 168:
                    candidates.append(ip)
                elif parts[0] == 10:
                    candidates.append(ip)
                elif parts[0] == 172 and (16 <= parts[1] <= 31):
                    candidates.append(ip)
    except Exception:
        pass
    return list(dict.fromkeys(candidates))


def get_local_adapter_ips() -> List[str]:
    """Retrieves all local IPv4 addresses assigned to the machine's adapters."""
    ips = []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                ips.append(ip)
    except Exception:
        pass
    return list(set(ips))


def get_subnet_sweep_ips(local_ips: List[str]) -> List[str]:
    """Generates candidate host IPs on the same /24 subnets as active local adapters."""
    sweep = []
    for lip in local_ips:
        parts = lip.split(".")
        if len(parts) == 4 and parts[0] in ("192", "10", "172"):
            prefix = f"{parts[0]}.{parts[1]}.{parts[2]}"
            # Add common lower and upper host IDs
            for host_id in [1, 2, 3, 4, 5, 10, 20, 50, 64, 100, 101, 102, 108, 120, 150, 200, 250]:
                target = f"{prefix}.{host_id}"
                if target != lip:
                    sweep.append(target)
    return sweep


def collect_target_candidates() -> List[str]:
    """Collects an ordered, deduplicated list of candidate camera IPs to scan."""
    candidates = []
    local_ips = get_local_adapter_ips()
    arp_ips = get_arp_ips()
    subnet_ips = get_subnet_sweep_ips(local_ips)

    # 1. ARP IPs first (highest probability because device has physically talked to switch/laptop)
    for ip in arp_ips:
        if ip not in candidates and ip not in local_ips:
            candidates.append(ip)

    # 2. Known factory default camera IPs
    for ip in COMMON_CAMERA_FACTORY_IPS:
        if ip not in candidates and ip not in local_ips:
            candidates.append(ip)

    # 3. Subnet sweep candidates
    for ip in subnet_ips:
        if ip not in candidates and ip not in local_ips:
            candidates.append(ip)

    return candidates


def check_tcp_port(ip: str, port: int = 554, timeout: float = 0.35) -> Tuple[str, int, bool]:
    """Quick socket check for open RTSP port."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        code = s.connect_ex((ip, port))
        s.close()
        return ip, port, (code == 0)
    except Exception:
        return ip, port, False


def scan_cctv_ports(candidates: List[str], ports: List[int] = [554, 8554], max_workers: int = 25) -> List[Tuple[str, int]]:
    """Concurrently scans candidate IPs for open RTSP ports."""
    open_targets = []
    tasks = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for ip in candidates:
            for port in ports:
                tasks.append(executor.submit(check_tcp_port, ip, port, 0.35))
        for future in as_completed(tasks):
            try:
                ip, port, is_open = future.result()
                if is_open:
                    open_targets.append((ip, port))
            except Exception:
                pass
    return open_targets


def verify_rtsp_stream_cv2(rtsp_url: str, timeout_seconds: float = 1.8) -> Tuple[bool, Optional[Any], Optional[str]]:
    """
    Attempts to read one real frame from the RTSP stream using OpenCV.
    Uses strict stimeout to avoid Windows socket hangs.
    """
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
        f"rtsp_transport;tcp|stimeout;{int(timeout_seconds * 1000000)}|timeout;{int(timeout_seconds * 1000000)}"
    )
    cap = None
    try:
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            cap = cv2.VideoCapture(rtsp_url)
        if not cap.isOpened():
            return False, None, "Could not open RTSP video capture"
        
        ret, frame = cap.read()
        if ret and frame is not None and frame.size > 0:
            h, w = frame.shape[:2]
            return True, frame, f"{w}x{h}"
        return False, None, "Frame read returned empty or False"
    except Exception as e:
        return False, None, str(e)
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass


def probe_and_verify_camera(host: str, port: int = 554) -> Optional[Dict[str, Any]]:
    """
    Tries brand presets and credentials against an open RTSP port to find a working stream.
    """
    # Test each brand template
    for tmpl in BRAND_STREAM_TEMPLATES:
        brand = tmpl["brand"]
        for path in tmpl["paths"]:
            for username, password in COMMON_CREDENTIALS:
                url = build_rtsp_url(
                    host=host,
                    port=port,
                    stream_path=path,
                    username=username,
                    password=password
                )
                is_safe, reason = validate_rtsp_url(url)
                if not is_safe:
                    continue

                ok, frame, res = verify_rtsp_stream_cv2(url, timeout_seconds=1.5)
                if ok and frame is not None:
                    # Found working camera!
                    # Save proof snapshot
                    proof_dir = os.path.join(PROJECT_ROOT, "data", "evidence")
                    os.makedirs(proof_dir, exist_ok=True)
                    proof_path = os.path.join(proof_dir, "college_cctv_connected_proof.jpg")
                    cv2.imwrite(proof_path, frame)
                    
                    with open(proof_path, "rb") as f:
                        frame_bytes = f.read()
                    sha256_hash = hashlib.sha256(frame_bytes).hexdigest()

                    return {
                        "brand": brand,
                        "host": host,
                        "port": port,
                        "path": path,
                        "username": username,
                        "password": password,
                        "rtsp_url": url,
                        "masked_url": mask_rtsp_url(url),
                        "resolution": res,
                        "sha256_proof": sha256_hash,
                        "proof_image": proof_path
                    }
    return None


def register_camera_with_backend(
    camera_data: Dict[str, Any],
    backend_url: str = "http://127.0.0.1:8000",
    camera_id: str = "COLLEGE-CAM-01"
) -> bool:
    """Registers discovered camera via FastAPI REST endpoint."""
    try:
        payload = {
            "camera_id": camera_id,
            "name": f"College {camera_data['brand']} ({camera_data['host']})",
            "host": camera_data["host"],
            "port": camera_data["port"],
            "stream_path": camera_data["path"],
            "username": camera_data.get("username"),
            "password": camera_data.get("password"),
            "direct_rtsp_url": camera_data["rtsp_url"],
            "scenario": "border_cctv",
            "activate_now": True
        }
        res = requests.post(f"{backend_url}/api/v1/cameras/cctv/connect", json=payload, timeout=4.0)
        return res.status_code in (200, 201)
    except Exception as e:
        # Fallback direct registration in runtime registry
        try:
            reg = RTSPRuntimeRegistry()
            cfg = RTSPCameraConfig(
                camera_id=camera_id,
                name=f"College {camera_data['brand']} ({camera_data['host']})",
                host=camera_data["host"],
                port=camera_data["port"],
                stream_path=camera_data["path"],
                username=camera_data.get("username"),
                password=camera_data.get("password"),
                scenario="border_cctv"
            )
            reg.register_camera(cfg)
            return True
        except Exception:
            return False


def discover_active_cctv(
    backend_url: str = "http://127.0.0.1:8000",
    auto_register: bool = True
) -> Dict[str, Any]:
    """
    Main entry point for automatic CCTV discovery.
    1. Collects candidate IPs from ARP and subnets.
    2. Concurrently probes port 554.
    3. Verifies video frame.
    4. Registers with backend.
    5. Returns structured status report.
    """
    candidates = collect_target_candidates()
    open_targets = scan_cctv_ports(candidates, ports=[554, 8554])

    discovered_camera = None
    for host, port in open_targets:
        # Skip local MediaMTX if scanning for external physical cameras
        if host in ("127.0.0.1", "localhost") and port == 8554:
            continue
        cam = probe_and_verify_camera(host, port)
        if cam:
            discovered_camera = cam
            break

    status_file = os.path.join(PROJECT_ROOT, "configs", "cctv_status.json")
    os.makedirs(os.path.dirname(status_file), exist_ok=True)

    if discovered_camera:
        cam_id = "COLLEGE-CAM-01"
        registered = False
        if auto_register:
            registered = register_camera_with_backend(discovered_camera, backend_url, camera_id=cam_id)
        
        status_data = {
            "status": "connected",
            "physical_cctv_detected": True,
            "camera_id": cam_id,
            "brand": discovered_camera["brand"],
            "host": discovered_camera["host"],
            "port": discovered_camera["port"],
            "masked_url": discovered_camera["masked_url"],
            "resolution": discovered_camera["resolution"],
            "sha256_proof": discovered_camera["sha256_proof"],
            "registered": registered,
            "timestamp": time.time()
        }
        import json
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2)
        return status_data

    else:
        # Fallback to local simulator CAM-01
        status_data = {
            "status": "fallback_simulator",
            "physical_cctv_detected": False,
            "camera_id": "CAM-01",
            "brand": "IBVAP Simulator",
            "host": "127.0.0.1",
            "port": 8554,
            "masked_url": "rtsp://127.0.0.1:8554/CAM-01",
            "resolution": "1920x1080",
            "message": "No physical CCTV detected on Ethernet switch. Active stream: CAM-01 simulator.",
            "timestamp": time.time()
        }
        import json
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2)
        return status_data
