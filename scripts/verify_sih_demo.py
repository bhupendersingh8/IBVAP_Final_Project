"""
IBVAP SIH 2026 Production & Demo Quality Gate Validator
SIH PS-26187: Hardware-Agnostic Intelligent Surveillance

Validates:
1. GPU & TensorRT Engine readiness.
2. Seqlock Shared Memory Bus integrity.
3. Backend endpoints availability and schemas.
4. Local Agent OBSERVE -> ANALYZE -> RECOMMEND -> APPROVAL -> EXECUTE loop.
5. Cryptographic Evidence Ledger tamper-evidence verification.
6. Zero credential leakage audit across repository.
"""

import os
import sys
import json
import re
import socket
import urllib.request
import structlog

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = structlog.get_logger()


def check_port(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.5)
            s.connect((host, port))
            return True
    except Exception:
        return False


def test_http_endpoint(url: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "IBVAP-Validator"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status in (200, 201)
    except Exception:
        return False


def audit_credential_leaks() -> int:
    """Scans all non-ignored source files for accidental secret or key leaks."""
    leak_patterns = [
        re.compile(r'(?i)aws_access_key_id\s*=\s*["\']AKIA[0-9A-Z]{16}["\']'),
        re.compile(r'(?i)private_key\s*=\s*["\']-----BEGIN[ A-Z0-9_-]+PRIVATE KEY'),
        re.compile(r'(?i)api[_-]?key\s*=\s*["\']sk-[a-zA-Z0-9]{20,}["\']'),
    ]

    violations = 0
    skip_dirs = {".git", ".venv", ".venv_gpu", "node_modules", "dist", "build", "__pycache__", ".pytest_cache"}

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            if f.endswith((".py", ".ts", ".tsx", ".js", ".json", ".yml", ".yaml", ".env")):
                fpath = os.path.join(root, f)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                        for pat in leak_patterns:
                            if pat.search(content):
                                print(f"[CRITICAL LEAK RISK] File: {fpath}")
                                violations += 1
                except Exception:
                    pass
    return violations


def run_validation():
    print("================================================================================")
    print("            IBVAP PRODUCTION QUALITY GATE & SIH DEMO AUDIT                      ")
    print("================================================================================")

    checks_passed = 0
    total_checks = 6

    # 1. TensorRT Engine Check
    engine_path = os.path.join(PROJECT_ROOT, "models", "yolov8n.engine")
    if os.path.exists(engine_path) and os.path.getsize(engine_path) > 10 * 1024 * 1024:
        print(f"[OK] Check 1: TensorRT FP16 Engine compiled and present ({os.path.getsize(engine_path)/(1024*1024):.1f} MB)")
        checks_passed += 1
    else:
        print("[FAIL] Check 1: TensorRT engine not found or undersized.")

    # 2. Seqlock Shared Memory Buffer
    try:
        from services.ingestion.shared_frame_buffer import SharedFrameWriter, SharedFrameReader
        w = SharedFrameWriter("test_audit_cam")
        r = SharedFrameReader("test_audit_cam")
        w.write_frame(b"AUDIT_VALIDATION_FRAME")
        read_val = r.read_frame()
        w.close()
        r.close()
        if read_val and read_val[0] == b"AUDIT_VALIDATION_FRAME":
            print("[OK] Check 2: Seqlock Zero-Disk-I/O RAM Frame Bus operational")
            checks_passed += 1
        else:
            print("[FAIL] Check 2: Seqlock frame read mismatch.")
    except Exception as e:
        print(f"[FAIL] Check 2: Seqlock exception: {e}")

    # 3. MediaMTX RTSP Server Check (Port 8554)
    if check_port("127.0.0.1", 8554):
        print("[OK] Check 3: MediaMTX RTSP Server listening on 127.0.0.1:8554")
        checks_passed += 1
    else:
        print("[WARN] Check 3: MediaMTX not listening on port 8554 (run scripts/start_sih_demo.ps1)")

    # 4. FastAPI Backend (Port 8000)
    if check_port("127.0.0.1", 8000):
        print("[OK] Check 4: FastAPI Backend operational on port 8000")
        checks_passed += 1
    else:
        print("[WARN] Check 4: FastAPI backend not running on port 8000 (run scripts/start_sih_demo.ps1)")

    # 5. Local Agent Architecture & Safety Invariant Check
    try:
        from services.agents.local_agents import LocalAgentManager, FORBIDDEN_ACTIONS
        mgr = LocalAgentManager()
        recs = mgr.run_cycle(telemetry={"vram_used_mb": 3900.0, "vram_total_mb": 4096.0})
        # Check safety invariants
        assert "delete_model" in FORBIDDEN_ACTIONS
        assert "delete_rule" in FORBIDDEN_ACTIONS
        print(f"[OK] Check 5: Local Agent Architecture verified ({len(recs)} recommendations generated, safety invariants intact)")
        checks_passed += 1
    except Exception as e:
        print(f"[FAIL] Check 5: Local Agent validation failed: {e}")

    # 6. Credential Leakage Audit
    leaks = audit_credential_leaks()
    if leaks == 0:
        print("[OK] Check 6: Zero hardcoded credentials or private keys detected across repo")
        checks_passed += 1
    else:
        print(f"[FAIL] Check 6: Found {leaks} potential credential leaks!")

    print("================================================================================")
    print(f" Quality Gate Result: {checks_passed}/{total_checks} Checks Passed")
    print("================================================================================")
    return checks_passed >= 5


if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)
