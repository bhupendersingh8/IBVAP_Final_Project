# Failure Recovery

---

## Failure Scenarios and Recovery Behavior

### 1. Camera Disconnect / RTSP Stream Loss

**Symptom:** RTSPSource fails to grab frame; `cv2.VideoCapture.read()` returns `False`.

**Recovery behavior:**
- `RTSPSource` retries connection with `reconnect_delay_seconds` (default 2s)
- `CameraHealthMonitor` transitions state: `ONLINE → RECONNECTING → ONLINE`
- `reconnect_count[camera_id]` incremented (visible in `/api/v1/metrics`)
- Tracker state is **preserved** — tracks resume on reconnect
- Inference worker does **not crash** — logs warning and retries
- If `max_reconnect_attempts` exceeded → state: `OFFLINE`

**Status: PARTIAL** — reconnect loop exists; max-retry limit and `OFFLINE` transition added in Phase 2.

**Recovery runbook:**
```
1. Check camera power and network connectivity
2. Check MediaMTX logs: scripts/mediamtx_logs.sh
3. Restart FFmpeg relay: scripts/ibvap.ps1 restart-cam
4. Inference worker auto-reconnects within 2–30s
```

---

### 2. Backend (FastAPI) Restart

**Symptom:** API returns connection refused; WebSocket drops.

**Recovery behavior:**
- All data is persisted in SQLite (`data/ibvap_dev.db`) — no data loss
- Inference worker WebSocket client reconnects automatically on next alert broadcast attempt
- Frontend React app shows "Disconnected" and polls on reconnect

**Status: PARTIAL** — database persistence verified; frontend reconnect not formally tested.

**Recovery runbook:**
```powershell
# Check if backend is running:
Get-Process -Name python | Where-Object {$_.CommandLine -like "*uvicorn*"}
# Restart:
.\scripts\ibvap.ps1 start-backend
```

---

### 3. Inference Worker Crash / Restart

**Symptom:** No new incidents in DB; WebSocket telemetry stops.

**Recovery behavior:**
- All existing evidence and incidents remain intact in SQLite
- Hash chain remains valid for events recorded before crash
- Restart worker with: `.\scripts\ibvap.ps1 start-inference`
- Worker re-registers with `camera_health_monitor` on startup

**Status: PARTIAL** — database durability verified; auto-restart not implemented (manual restart required).

---

### 4. WebSocket Disconnect (Operator Dashboard)

**Symptom:** Dashboard shows "Connecting..." or stale telemetry.

**Recovery behavior:**
- React frontend auto-reconnects WebSocket on close event
- On reconnect, backend sends latest telemetry snapshot immediately
- No alert data is lost (alerts are logged to SQLite regardless of WS state)

**Status: PASS** — WebSocket reconnect observed in testing.

---

### 5. Database Corruption

**Symptom:** SQLAlchemy async session throws integrity errors.

**Recovery behavior:**
- IBVAP does not currently implement automatic DB repair
- Evidence files are unaffected (stored as JPEGs in `data/evidence/`)
- Hash chain can be re-verified independently of the DB

**Recovery runbook:**
```
1. Stop all services: .\scripts\ibvap.ps1 stop
2. Backup corrupt DB: copy data\ibvap_dev.db data\ibvap_dev.db.bak
3. Re-initialize DB: python -c "import asyncio; from apps.backend.database.connection import init_db; asyncio.run(init_db())"
4. Evidence files remain intact in data/evidence/
5. Restart all services: .\scripts\ibvap.ps1 demo
```

**Status: NOT_DONE** — no automated DB repair or backup mechanism implemented.

---

### 6. Disk Space Warning

**Detection:** Not currently monitored.

**Planned:** Add disk usage to `/api/v1/metrics` output and alert when < 10% free.

**Status: PLANNED**

---

### 7. Invalid / Corrupt RTSP Frame

**Symptom:** OpenCV decode returns garbage frame; YOLO inference gets nonsense input.

**Recovery behavior:**
- `YOLOAdapter` catches inference exceptions and returns empty `DetectionBatch`
- Worker logs warning and continues to next frame
- No crash; no spurious alert

**Status: PASS** — exception handling in place.

---

## Graceful Shutdown

When inference worker receives SIGINT/SIGTERM (Ctrl+C):
- `running = False` flag set
- Current frame processing completes
- Any pending DB commit completes
- Worker exits cleanly

**Status: PARTIAL** — signal handling implemented; drain-and-flush not formally tested.

---

## Failure Testing Status

| Scenario | Tested | Result | Notes |
|----------|--------|--------|-------|
| Camera disconnect | Manual observation | PARTIAL | Reconnects; formal test not automated |
| Backend restart | Manual | PARTIAL | DB intact; WS reconnect observed |
| Inference worker restart | Manual | PARTIAL | DB intact; manual restart needed |
| WebSocket disconnect | Manual | PASS | Frontend auto-reconnects |
| DB corruption | NOT_TESTED | — | Recovery runbook documented |
| Corrupt frame | Code review | PASS | Empty DetectionBatch returned |
| Disk full | NOT_TESTED | — | Not monitored |

*Formal automated failure testing (chaos engineering) is NOT_DONE for this prototype.*
