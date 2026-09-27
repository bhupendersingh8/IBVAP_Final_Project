# IBVAP Monday SIH Demonstration Runbook

**Document Type**: Operator Live Execution Guide  
**Target Duration**: 5–8 minutes live demonstration  
**Audience**: SIH Evaluators, Ministry Observers, Technical Jury  

---

## 1. Pre-Demo Environment Check (T - 5 Minutes)

1. **Verify Python & Network**:
   - Machine: Windows 11 AMD64 (Intel Core i3, 12GB RAM).
   - If using Android Phone Camera (`PHONE-CAM-01`): Ensure phone is on the same local Wi-Fi and IP Webcam server is running at `http://10.63.26.249:8080/video`.
2. **Verify System Health**:
   ```powershell
   cd C:\Users\dell\Projects\IBVAP
   python -m pytest tests/ -v
   ```
   *Expected*: All 54 tests pass in ~5 seconds.

---

## 2. One-Command Master Start (T - 0)

Execute the master launcher in PowerShell:
```powershell
.\scripts\ibvap.ps1 demo
```

### What This Automates:
1. Cleans stale demonstration alerts and temporary evidence caches.
2. Checks and boots MediaMTX (RTSP port 8554, WebRTC port 8889).
3. Launches FFmpeg RTSP loop publisher for `CAM-01`.
4. Starts FastAPI backend (`http://localhost:8000`).
5. Starts the Main YOLO Inference Worker (`main_inference_worker.py`).
6. Starts the React Frontend dev server (`http://localhost:5173`).
7. Automatically launches Microsoft Edge to `http://localhost:5173`.

---

## 3. Live Demonstration Script (Step-by-Step)

### Step A: System Overview & Live Telemetry
- **Show Evaluators**: The top metric cards displaying real-time FPS, inference latency (~140ms on CPU), CPU/RAM load, and active tracks count.
- **Key Talking Point**: *"Notice the video display is completely decoupled from neural inference, providing smooth 30 FPS operator viewing without browser stutter."*

### Step B: Multi-Object Tracking & Ground-Contact Virtual Fence
- **Point out Viewport**: Real bounding boxes (Blue for Person, Green for Vehicle), persistent Track IDs, and dotted trajectory trails.
- **Show Ground Contact Anchor**: Yellow dot at the bottom-center of the person's feet ($x=\text{center\_x}, y=y_2$).
- **Key Talking Point**: *"Unlike naive solutions that trigger false alarms when an intruder's arm or upper body leans over a fence, IBVAP strictly anchors intrusion logic to ground contact points."*

### Step C: Real Zone Breach & Live Alerting
- **Observe Breach**: When Track crosses into `RESTRICTED_ZONE_01`, watch the top notification banner flash red (`CRITICAL ALERT: RESTRICTED_ZONE_INTRUSION`).
- **Show Deduplication**: Note that the system doesn't flood 30 alerts per second; it generates one transition alert with a 15-second track cooldown.

### Step D: Incident Lifecycle & Cryptographic Evidence Ledger
- **Navigate to**: `Incidents` tab in the top navigation bar.
- **Demonstrate Lifecycle**:
  - Show status badge: `NEW`.
  - Click `Acknowledge` -> transitions to `ACKNOWLEDGED`.
  - Click `Investigate` -> transitions to `INVESTIGATING`.
  - Click `Resolve` -> transitions to `RESOLVED` / Closed.
- **Show Cryptographic Proof**:
  - Point out SHA-256 evidence snapshot hash.
  - Explain local hash chain ledger: Each incident is cryptographically linked to the previous incident hash (`RecordHash_n = SHA256(PrevHash + IncidentID + EvidenceHash + Timestamp + Payload)`).
  - Open terminal or browser to `http://localhost:8000/api/v1/evidence/verify_ledger` to prove chain integrity.

### Step E: Dual Camera Source (Phone Camera Demonstration)
- In the dashboard camera selector, switch from `CAM-01` to `PHONE-CAM-01`.
- Move an object or hand in front of the phone camera to show live real-world mobile stream detection.

---

## 4. Emergency Recovery Commands

- If any service hangs or port conflict occurs:
  ```powershell
  .\scripts\ibvap.ps1 restart
  ```
- To stop all background services cleanly:
  ```powershell
  .\scripts\ibvap.ps1 stop
  ```
- To inspect running processes and PIDs:
  ```powershell
  .\scripts\ibvap.ps1 status
  ```
