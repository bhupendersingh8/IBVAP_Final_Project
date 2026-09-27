# IBVAP AIR-GAPPED OFFLINE OPERATION SPECIFICATION
**Platform:** Intelligent Border Video Analytics Platform (IBVAP)  
**Security Classification:** Air-Gapped Tactical Autonomous System  
**Canonical Directory:** `C:\Users\dell\Desktop\p2\IBVAP_Final_Project`  

---

## 1. Zero Cloud Dependency Guarantee

The IBVAP architecture is engineered from the ground up for **100% offline, air-gapped sovereign deployment**. The system does **not require**:
- Internet connectivity
- Cloud API keys or external SaaS endpoints (OpenAI, Anthropic, AWS, etc.)
- Remote database connections
- Online license verification servers

All components—from camera ingestion to inference, multi-tracking, rule evaluation, database persistence, evidence hashing, and browser UI rendering—execute strictly on the local host machine.

---

## 2. Local Asset Inventory

| Asset Category | File Path | Offline Verification Status | Notes |
|:---|:---|:---:|:---|
| **AI Model Weights** | `models/yolov8n.pt` | **VERIFIED LOCAL** | Ultralytics COCO baseline model (6.2 MB) |
| **AI Model ONNX** | `models/yolov8n.onnx` | **VERIFIED LOCAL** | Cross-platform ONNX runtime weight |
| **Pose Keypoints** | `yolov8n-pose.pt` | **VERIFIED LOCAL** | 17-keypoint skeleton detector (6.8 MB) |
| **Face Haar XML** | `services/detection/haarcascade_frontalface_default.xml` | **VERIFIED LOCAL** | OpenCV offline Haar feature cascade |
| **RTSP Daemon** | `infrastructure/mediamtx/mediamtx.exe` | **VERIFIED LOCAL** | Self-contained zero-dependency RTSP server |
| **FFmpeg Suite** | `infrastructure/ffmpeg/bin/ffmpeg.exe` | **VERIFIED LOCAL** | Offline video transcode & stream injector |
| **Database** | `data/ibvap_dev.db` | **VERIFIED LOCAL** | SQLite database with 30,867 historical records |
| **Frontend UI** | `apps/frontend/dist/` | **VERIFIED LOCAL** | Single-page application compiled bundle |
| **Python Packages** | `C:\Users\dell\Desktop\p2\venv` | **VERIFIED LOCAL** | Standalone pre-cached virtualenv |

---

## 3. Disconnected Network Verification Procedure

To audit that IBVAP operates seamlessly without internet access:

1. **Disconnect Network Adapters:**
   - Disconnect Wi-Fi and unplug Ethernet cables from the Dell host laptop.
   - Alternatively, toggle Airplane Mode in Windows 11.
2. **Execute Local Startup:**
   ```powershell
   cd C:\Users\dell\Desktop\p2\IBVAP_Final_Project
   .\START_CCTV_DEMO.bat
   ```
3. **Verify Local Endpoints:**
   - Open browser to `http://localhost:8000`.
   - Observe live clean camera video feed from `CAM-01`.
   - Observe WebSocket real-time detections and SVG overlays.
   - Trigger incident rules; observe database persistence in `data/ibvap_dev.db`.
   - Check browser developer tools (F12) Network tab: confirm 100% of network requests target `localhost` or `127.0.0.1`. **Zero external DNS resolutions or outbound HTTP requests.**
