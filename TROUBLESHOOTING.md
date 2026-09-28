# IBVAP Troubleshooting Guide

**System**: Intelligent Border Video Analytics Platform (IBVAP)  
**SIH Problem Statement**: 26187  

---

## 1. Common Issues & Quick Resolutions

### 1.1 Ingestion / Camera RTSP Connection Refused
- **Symptom**: Camera indicator shows RED; log outputs `ConnectionRefusedError: [Errno 111]`.
- **Cause**: MediaMTX RTSP server is not active or firewall blocks port 8554.
- **Resolution**:
  ```powershell
  # Check if MediaMTX is running
  Get-Process mediamtx -ErrorAction SilentlyContinue
  # Or start background RTSP feeder
  python scripts/start_sih_demo.ps1
  ```

### 1.2 Pipeline Latency Spike (>100 ms)
- **Symptom**: Operator HUD displays `LATENCY: HIGH`, dropped frame counter increments.
- **Cause**: Specialist heavy path or Tiled Detector running on high-resolution full frames on CPU.
- **Resolution**:
  - In `config/settings.py` or `.env`, ensure:
    ```env
    DETECTOR_BACKEND=yolov8
    ENABLE_ADAPTIVE_TILING=false
    MAX_SPECIALIST_WORKERS=2
    ```
  - The bounded frame queue will automatically drop old frames to restore sub-66ms latency.

### 1.3 WebSocket Disconnection / Reconnection Loop
- **Symptom**: Dashboard shows `WS: DISCONNECTED`, retrying every 3 seconds.
- **Cause**: Backend Uvicorn server stopped or CORS policy mismatch on port 8000.
- **Resolution**:
  - Verify FastAPI backend is running: `http://localhost:8000/api/v1/health`
  - Ensure frontend points to `ws://localhost:8000/api/v1/ws/telemetry`.

### 1.4 Section 65B Hash Verification Failure (`TAMPER_DETECTED`)
- **Symptom**: Calling `POST /api/v1/evidence/verify` returns `TAMPER_DETECTED`.
- **Cause**: The snapshot or video file on disk was modified, truncated, or rotated by an external process.
- **Resolution**:
  - Inspect audit log for unauthorized modifications: `GET /api/v1/audit/logs`.
  - Evidence integrity is cryptographically sealed; tampered files cannot be restored and must be flagged for security review.

---

## 2. Diagnostic Commands

```powershell
# 1. Run all unit & integration tests
pytest tests/ -q

# 2. Test Condition Preprocessor
pytest tests/test_condition_analyzer.py -v

# 3. Test Evidence Verification
pytest tests/test_evidence_verification_endpoint.py -v

# 4. Check system health endpoint
curl http://localhost:8000/api/v1/health
```
