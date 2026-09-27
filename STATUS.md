# IBVAP — Reality Status Matrix & Truth Disclosure

> **Authoritative System Status & Anti-Fabrication Declarations**
> Updated: March 2026

---

## 🛡️ Truth Disclosures & System Reality

To maintain 100% scientific and engineering honesty before deployment and review:
1. **Pretrained Baseline Model**:
   - The primary object detection engine utilizes pretrained `yolov8n.pt` weights (COCO dataset).
   - High-confidence detection is verified for classes: `person`, `car`, `truck`, `bus`, `motorcycle`.
2. **Domain Dataset Status**:
   - The ML data pipeline, dataset directory structures, schema validator (`dataset_validator.py`), and frame collector (`collect_dataset_frames.py`) are fully built and operational.
   - The curated domain dataset currently has **0 images / 0 human labels**.
   - No custom model fine-tuning or domain-specific accuracy gains (mAP50) are claimed.
3. **Hardware Context**:
   - The platform is tuned and verified for standard **CPU-only execution** (Intel Core i3 / 12GB RAM) without requiring an NVIDIA GPU.
4. **ANPR Scope**:
   - The vehicle crop and EasyOCR text extraction pipeline is structurally implemented.
   - Because standard 360p/480p surveillance video lacks optical resolution for small plate text, low-confidence OCR results are flagged as `UNREADABLE`. License plate numbers are **never fabricated**.
5. **Camera Hardware Story**:
   - The product is strictly **surveillance software for existing IP CCTV infrastructure (RTSP)**.
   - Laptop webcam mode (`WEBCAM-01`) is provided as an engineering adapter for convenient offline testing.

---

## 📋 MHA PS-26187 Requirement Status Matrix

| Requirement | Category | Implementation Status | Empirical Verification |
|---|---|---|---|
| **Multi-Camera Ingestion** | Video / CCTV | Complete (`RTSPSource`, `WebcamSource`, `FrameBuffer`) | Tested with MediaMTX loop & Webcam |
| **Edge / Local Processing** | Architecture | Complete (CPU-optimized, offline, zero cloud calls) | 100% Offline execution verified |
| **Object Detection & Classification** | AI / CV | Complete (`YOLOAdapter` using `yolov8n.pt`) | Real-time person & vehicle detections |
| **Multi-Object Tracking** | AI / CV | Complete (`ByteTrackAdapter` / IoU matching) | Trajectory tracking & track ID persistence |
| **Virtual Fencing & Spatial Rules** | Rules | Complete (`RuleEngine`, ray-casting polygons, lines) | Triggered alerts on zone intrusion |
| **Temporal Activity Analysis** | Rules | Complete (`ActivityEngine`, posture/standing/walking) | Verified in unit test suite |
| **Event Correlation & Alert Engine** | Incidents | Complete (`EventCorrelator`, severity calculation) | Deduplicated, real-time alerts |
| **Tamper-Evident Evidence** | Security | Complete (`EvidenceVault`, SHA-256 local hash chain) | Cryptographic hash ledger on disk |
| **Incident Lifecycle Management** | Operations | Complete (`NEW` -> `ACKNOWLEDGED` -> `RESOLVED`) | Verified via REST API & UI actions |
| **Role-Based Access Control (RBAC)** | Security | Complete (JWT tokens, ADMIN / OPERATOR / READ_ONLY) | Passwords hashed with bcrypt |
| **ANPR / Plate Recognition** | CV / OCR | Pipeline complete (`PlateDetector` + `EasyOCR`) | Low-res footage returns UNREADABLE |
| **Model Registry & Feedback Loop** | MLOps | Complete (MLflow schemas, candidate/canary states) | Schema & DB models tested |
| **Custom Model Fine-tuning** | ML Training | Pipeline complete; Domain dataset empty | Pending domain footage annotation |

---

## 📊 Automated Test Status
- Total Pytest Regression Tests: **75 / 75 PASSING**
- Frontend Production Build: **CLEAN (Vite v5.4.21 / TypeScript)**

---

## 🔍 Explicit System Classification

### VERIFIED (Tested with Real Execution & Empirical Evidence):
- Multi-camera RTSP ingestion (MediaMTX stream gateway)
- CPU-optimized YOLOv8n object detection (person & vehicle classes)
- Multi-object tracking (ByteTrack / IoU tracker)
- Virtual fencing & ray-casting spatial rule engine
- Real-time intrusion alerting & severity evaluation
- Complete incident lifecycle (NEW -> ACKNOWLEDGED -> RESOLVED)
- Tamper-evident evidence storage with local SHA-256 hash chains
- React + Vite operations dashboard with live WebRTC player
- Laptop webcam test adapter (`WEBCAM-01`)
- 75/75 automated pytest regression suite

### IMPLEMENTED BUT VALIDATION PENDING:
- Custom ML training & dataset curation pipeline (validator & splitter operational, awaiting human-labeled domain data)
- ANPR plate crop + EasyOCR pipeline (structural pipeline operational, awaiting high-resolution vehicle footage)
- Low-light CLAHE enhancement pipeline (implemented, awaiting night thermal/border sensor validation)
- Advanced temporal activity analytics (crouching, loitering candidate classification)
- NVIDIA Jetson / TensorRT deployment architecture (architecture designed, dev machine is CPU-only)

### NOT VERIFIED:
- Reliable real-world ANPR recognition on suitable high-resolution plate footage
- TensorRT / DeepStream production benchmarks
- Field deployment on edge embedded hardware (NVIDIA Jetson / Orin)
- Domain-trained border-specific model weights

### NOT IMPLEMENTED / OUT OF SCOPE:
- Facial recognition
- Cross-camera identity / person re-identification (ReID)
- Blockchain-based distributed evidence ledger (local SHA-256 chain used instead)

### KNOWN ARCHITECTURAL LIMITATIONS:
- **Dataset**: Curated domain dataset currently contains 0 images / 0 human labels.
- **ANPR Resolution**: Low-resolution footage (360p/480p) returns `UNREADABLE`; plate numbers are never fabricated.
- **Database Concurrency**: SQLite dev database is suitable for single-node / edge testing; high-concurrency multi-camera production requires PostgreSQL.
- **Hardware**: Testing performed on Intel Core i3 (CPU-only); high camera count deployments require dedicated GPU/VPU hardware.
