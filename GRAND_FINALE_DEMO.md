# IBVAP GRAND FINALE DEMONSTRATION SCRIPT
**Platform:** Intelligent Border Video Analytics Platform (IBVAP)  
**Host Target:** Dell Inspiron / Vostro Laptop (Intel Core i3-1115G4, 12GB RAM, Windows 11)  
**Evaluator Audience:** SIH Evaluation Committee / Ministry Defense Evaluators  

---

## 1. Pre-Flight Verification Checklist

Before starting the live demonstration, confirm system readiness:
1. Canonical directory: `C:\Users\dell\Desktop\p2\IBVAP_Final_Project`.
2. Python 3.11 virtualenv: `C:\Users\dell\Desktop\p2\venv\Scripts\python.exe`.
3. Historical database preserved: `data/ibvap_dev.db` (30,867 historical records intact).
4. No background zombie processes (`STOP_ALL_SERVICES.bat`).

---

## 2. Step-by-Step Live Demonstration Walkthrough

### Step 1: Launch the Canonical CCTV Simulation Demo
Open Command Prompt / PowerShell in the project directory and run:
```cmd
START_CCTV_DEMO.bat
```
*What happens under the hood:*
- MediaMTX lightweight RTSP daemon starts on port 8554.
- Bundled FFmpeg begins looping `data/raw/test_video.mp4` onto `rtsp://127.0.0.1:8554/CAM-01`.
- The FastAPI backend starts on port 8000 with 76 active API routes.
- The Autonomous AI Orchestrator initializes with CPU-first YOLOv8n + ByteTrack.

---

### Step 2: Open the Interactive React Dashboard
Open Google Chrome or Microsoft Edge and navigate to:
```
http://localhost:8000
```

### Key Demonstrations in the Web UI:
1. **Zero Ghost / Duplicate Bounding Boxes:**
   - Observe the live video feed.
   - The backend serves a **clean raw video frame**.
   - The frontend renders a **single, responsive SVG overlay** from WebSocket telemetry.
   - Point out that there are **zero duplicate or burned-in OpenCV boxes**, solving the high-priority bug.
2. **Instant Hotkey Camera Switching:**
   - Press **Hotkey [1]**: Switches to `CAM-01` (RTSP Canonical Demo feed).
   - Press **Hotkey [2]**: Switches to `WEBCAM-01` (DirectShow Laptop Webcam).
   - Press **Hotkey [3]**: Switches to `PHONE-CAM-01` (Secondary Sector Stream).
   - Press **Hotkey [4]**: Switches to `CAM-02` (Checkpoint Stream).
   - Toggle **[2x2 Grid View]** to view all feeds concurrently.
3. **Temporal Validation State Machine:**
   - Point to the target telemetry badge.
   - Show how a newly entered target starts in `DETECTED (1 frame)`, progresses through `TENTATIVE (5 frames)` and `STABLE (15 frames)`, reaches `VERIFIED (30 frames)`, and only becomes `ALERT_ELIGIBLE` after ~45 consecutive frames ($\approx 1.5\text{s}$).
   - Fleeting shadows, birds, or camera jitter that vanish within 10 frames are discarded without triggering false alarms.
4. **Identity Safety & 4-State Machine:**
   - Point to the identity badge: `UNKNOWN`, `UNVERIFIED`, `AUTHORIZED`, `UNAUTHORIZED`.
   - Explain that **detection is NOT identity**. An unidentified face defaults to `UNKNOWN` or `UNVERIFIED`; it is never falsely identified as an authorized officer, nor does an unknown person trigger an immediate critical alert unless breach rules are violated.
5. **Indic Language Tactical Dispatch:**
   - Trigger an alert or view recent incident logs.
   - Display the multi-lingual broadcast in **English, Hindi, and Punjabi**.
6. **Tamper-Evident SHA-256 Ledger Audit:**
   - In the dashboard or via API (`http://localhost:8000/api/v1/evidence/verify_ledger`), run the cryptographic audit.
   - Show all **7,694 blocks** verified with zero corruption.

---

### Step 3: Switch to Live Laptop Webcam Demo
To demonstrate live webcam capture:
1. Stop the current demo:
   ```cmd
   STOP_ALL_SERVICES.bat
   ```
2. Start the webcam demo:
   ```cmd
   START_WEBCAM_DEMO.bat
   ```
3. Refresh `http://localhost:8000`. The laptop webcam captures the room in real-time, performing live person detection and face tracking on the Dell Intel Core i3 at ~15 FPS.

---

### Step 4: Clean Shutdown
To stop all services after the demonstration:
```cmd
STOP_ALL_SERVICES.bat
```
All ports (8000, 8554) and processes are cleanly released.
