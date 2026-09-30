# IBVAP SIH Problem Statement Requirement Mapping

**Problem Statement Title**: AI-Powered Video Analytics Platform for Border Security & Perimeter Surveillance  
**Document Version**: 1.0.0 (Freeze Specification)  
**Target Evaluation**: Monday SIH Demonstration  

---

| # | SIH PS Requirement | Current Implementation Status | Evidence / Verification Method | Real-World Limitation | Next Step / Production Roadmap |
| :---: | :--- | :---: | :--- | :--- | :--- |
| **1** | **Human Detection** | **`PASS`** | YOLOv8n detector with `person` class mapping. `tests/test_detection.py` and live inference worker. | Pretrained COCO model; prone to false positives on camouflaged clothing at long range. | Fine-tune on border perimeter dataset with thermal/IR augmentation. |
| **2** | **Human Tracking** | **`PASS`** | `FallbackIoUTracker` / ByteTrack maintaining persistent track IDs and trajectory points. `tests/test_tracking.py` (34/34 pass). | ID switches can occur during long occlusions (>30 frames). | Integrate deep appearance Re-ID feature embeddings (OSNet). |
| **3** | **Vehicle Detection** | **`PASS`** | Mapped classes (`car`, `truck`, `bus`, `motorcycle`, `bicycle`) unified as `class_name='vehicle'`. `tests/test_detection.py`. | Distant low-angle vehicles may have low confidence. | Multi-scale test-time augmentation (TTA). |
| **4** | **Vehicle Classification** | **`PASS`** | Subclass preserved in detection and track attributes (`subclass='car'`, etc.). `tests/test_anpr.py`. | Ambiguity between light commercial vans and small trucks. | Domain-specific commercial vehicle fine-tuning. |
| **5** | **Face Detection** | **`PLANNED`** | Architecture ready for secondary biometric crop pipeline. | Not prioritized for wide-area border perimeter cameras (>20m distance). | Integrate RetinaFace/SCRFD for checkpoint cameras. |
| **6** | **ANPR (License Plate)** | **`PARTIAL`** | Architecture ready: `PlateDetector` (`ContourPlateDetector`) + `EasyOCREngine` with multi-frame consensus. Real plate recognition is **`NOT_VERIFIED`** on 592x360 CCTV test footage. | License plates on wide-angle perimeter CCTV are sub-pixel (<35px) and correctly marked UNREADABLE. | Deploy dedicated telephoto / 4K LPR optical lane cameras. |
| **7** | **Virtual Fence Intrusion** | **`PASS`** | Ray-casting polygon evaluation using **bottom-center ground contact point** (`x=center_x, y=y2`). `tests/test_rules.py`. | Does not calculate 3D terrain elevation/topography. | Calibrate camera homography for ground-plane projection. |
| **8** | **Suspicious Activity Analysis** | **`PARTIAL`** | `ActivityEngine` detecting `STANDING`, `WALKING`, and `LOITERING_CANDIDATE` based on temporal displacement. | Rule-based heuristics without 3D pose estimation. | Integrate YOLOv8-pose keypoint estimation for crawl/climb detection. |
| **9** | **Night Analytics** | **`PARTIAL`** | Dynamic CLAHE contrast enhancement in `services/preprocessing/clahe_enhancer.py`. | Real thermal / low-light field benchmark not evaluated. | Benchmark against LLVIP / ExDark thermal border datasets. |
| **10** | **Real-Time Alerts** | **`PASS`** | FastAPI WebSocket hub broadcasting incident payloads to React dashboard with audio-visual notifications. | WebSocket requires active network connection. | Add local SMS/GSM gateway or SIP siren trigger relay. |
| **11** | **Event Logging** | **`PASS`** | Append-only event table in SQLite with UTC timestamps, zone metadata, and explanations. | SQLite dev database single-writer throughput limit. | Migrate to PostgreSQL in multi-server enterprise deployment. |
| **12** | **Evidence Capture** | **`PASS`** | Atomic JPEG snapshot saved to `data/evidence/` with SHA-256 hash stored in DB record. `tests/test_anpr.py`. | Local disk storage requires rotation/retention policy. | Configure automated tiered cold storage / NAS archiving. |
| **13** | **Existing IP CCTV Integration** | **`PASS`** | Direct RTSP/MJPEG camera ingestion via OpenCV and MediaMTX. Dual active inputs (`PHONE-CAM-01` and `CAM-01`). | High network packet jitter can drop RTP packets over UDP. | Enforce TCP transport for RTSP streams (`rtsp_transport tcp`). |
| **14** | **Cost-Effective Architecture** | **`PASS`** | Full pipeline runs on commodity Intel Core i3 CPU without expensive GPU hardware. Zero paid proprietary software. | CPU throughput caps out at 2–3 concurrent 1080p AI channels. | Add Intel OpenVINO / NPU runtime acceleration. |
| **15** | **Command/Control Integration** | **`PASS`** | REST API (`/api/v1/incidents`, `/api/v1/cameras`, `/api/v1/zones`) and WebSocket telemetry for VMS/C2 integration. | Authentication is basic JWT; needs single-sign-on (SSO). | Implement OAuth2/OIDC and SAML integration for defense C2. |
| **16** | **Cybersecurity & Hardening** | **`PASS`** | Zero committed secrets (verified by regex audit), CORS restriction, parameterized SQL queries, path traversal guards. | Local HTTP/WS without TLS in local prototype. | Enforce HTTPS/WSS with local PKI certificates in production. |
| **17** | **Offline / Edge Operation** | **`PASS`** | Air-gapped capable; zero cloud dependencies, zero external telemetry calls. | Edge node must be physically secured. | Enable full-disk BitLocker encryption and TPM attestation. |
| **18** | **Continuous Feedback Loop** | **`PASS`** | Operator feedback API (`/api/v1/feedback`) records true intrusion vs false alarm labels with model version for active learning. | Human review currently manual via dashboard. | Automate weekly active learning fine-tuning trigger. |
