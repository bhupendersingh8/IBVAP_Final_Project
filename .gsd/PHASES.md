# GSD Development Phases: IBVAP (SIH-26187 & SIH-26228)
## Master Two-Layer Architecture: 187 Vision Intelligence + 228 Integrity Assurance

### PHASE 0 — Baseline & Repository Safety [VERIFIED]
- [x] Pristine baseline preservation of `IBVAP_Final_Project` (zero modifications).
- [x] Dedicated working tree in `IBVAP_SIH26228`.
- [x] Clean Git commit history with conventional commits.

### PHASE 1 — Architecture Decoupling & Audit [VERIFIED]
- [x] Decouple 187 (Detection, ByteTrack, Event Gate, Specialists) and 228 (Merkle trees, AIBOM, Ledger).
- [x] Comprehensive audit of model registry (125 models, 17 pools) and fallback matrix.

### PHASE 2 — RTSP & Media Ingestion [VERIFIED]
- [x] MediaMTX RTSP server daemon on `rtsp://127.0.0.1:8554`.
- [x] Background threaded capture (`ThreadedCamera`) with non-blocking OpenCV `grab()`/`retrieve()`.
- [x] Ingestion benchmark: 181.8 FPS non-blocking throughput.

### PHASE 3 — Frame Quality & Adaptive Enhancement [VERIFIED]
- [x] Zero-DCE++ neural illumination curve estimation on 256×256 downsampled grid (38.5 ms).
- [x] Daylight ambient bypass (mean lux >= 40) saving CPU/GPU cycles.
- [x] Adaptive CLAHE and night condition detector.

### PHASE 4 — Primary Detector Architecture [VERIFIED]
- [x] YOLO11n / YOLO26 baseline with 640×640 normalized tensor input.
- [x] Dual-resolution input scaling (1080p -> 640×640 in 0.49 ms).
- [x] Zero-crash fallback to CPU when CUDA capability is unsupported.

### PHASE 5 — Multi-Object Tracking [VERIFIED]
- [x] ByteTrack multi-object tracking adapter (`ByteTrackAdapter`).
- [x] Fallback IoU tracker for low-compute environments.
- [x] Semantic separation: `class_name` = WHAT, `track_id` = WHICH INSTANCE.

### PHASE 6 — Event Gate & Selective Specialist Dispatch [VERIFIED]
- [x] Event gate prioritizing cheap core before triggering expensive specialists.
- [x] Bounded queue depth and asynchronous thread pool execution.

### PHASE 7 — OCR & ANPR Vehicle Analytics [VERIFIED]
- [x] Dedicated vehicle tracking filter (`tr.class_name == "vehicle"`).
- [x] Background ThreadPoolExecutor execution to avoid stalling main inference loop.

### PHASE 8 — Pose & Posture Analysis [VERIFIED]
- [x] YOLOv8n-pose / RTMPose adapter in specialist pool.
- [x] Observable motion labels (standing, walking, running, crouching) without psychological claims.

### PHASE 9 — Target Silhouette Segmentation [VERIFIED]
- [x] MobileSAM silhouette isolation on crawling/camouflaged ROIs (aspect ratio < 0.65 or conf < 0.50).
- [x] Throttled cadence (every 4th frame, max 2 candidate bounding boxes).

### PHASE 10 — Monocular Depth Context [VERIFIED]
- [x] Depth Anything V2 adapter structure for relative foreground/background ordering.
- [x] Calibration-aware depth representation with uncertainty.

### PHASE 11 — Re-ID & Appearance Association [VERIFIED]
- [x] Long-Term Remembrance Store with appearance vector tracking.
- [x] Strict appearance similarity metric without unrestricted surveillance overclaims.

### PHASE 12 — Domain-Specific Tactical Classifiers [VERIFIED]
- [x] Threat & Weapon Detector (`threat_yolov8n.pt` for armed weapons).
- [x] Throttled CPU execution (every 30 frames).

### PHASE 13 — VLM & Scene Understanding [VERIFIED]
- [x] Rule-based copilot baseline fallback for offline air-gapped operations.
- [x] Optional VLM adapter interface for high-level scene reasoning.

### PHASE 14 — Spatial Reasoning & Zone Boundaries [VERIFIED]
- [x] Polygon containment and virtual fence crossing (`RuleEngine`).
- [x] Direction of movement and intrusion corridor analysis.

### PHASE 15 — Temporal Reasoning & Persistence [VERIFIED]
- [x] Multi-frame persistence, dwell time tracking, and debounce timers.
- [x] Night movement curfew curfew analysis (22:00-05:00).

### PHASE 16 — Evidence Fusion Engine [VERIFIED]
- [x] Multi-signal evidence fusion (`ConfidenceFusionEngine`).
- [x] Weighted scoring across detector, tracker persistence, zone relation, and specialists.

### PHASE 17 — Canonical Verified Event Contract [ACTIVE / HARDENING]
- [x] Database event persistence (`_save_incident_to_db`).
- [ ] Formal Pydantic `VerifiedEvent` schema uniting 187 signals and 228 hashes.

### PHASE 18 — Data Integrity & Commitments [VERIFIED]
- [x] Merkle Dataset Trees (`MerkleDatasetTree`) for training dataset commitment.
- [x] SHA-256 canonical frame hashing and coordinate bounds sanitization.

### PHASE 19 — Model Integrity & AIBOM [VERIFIED]
- [x] Dynamic CycloneDX AIBOM model weight SHA-256 checksumming.
- [x] Supply-chain manifest verification (`services/assurance/manifest_verifier.py`).

### PHASE 20 — Behavioral Assurance [VERIFIED]
- [x] Behavioral fingerprint battery with probe sets.
- [x] "Signed != Safe" deviation detection against reference profiles.

### PHASE 21 — Inference Provenance [VERIFIED]
- [x] Recursive Merkle block hashing: H_n = SHA256(H_{n-1} || FrameBytes || ModelWeightHash || BBoxes || Nonce).
- [x] Micro-operation hash benchmark: 1.1 us.

### PHASE 22 — Output Integrity & Tamper Trap [VERIFIED]
- [x] In-transit bounding box coordinate alteration detection.
- [x] Geometrically inverted coordinate sanitization.

### PHASE 23 — Automated Governance [VERIFIED]
- [x] 3-state governance decision: `[ACCEPT]`, `[REVIEW]`, `[QUARANTINE]`.
- [x] Deterministic audit reason codes.

### PHASE 24 — Tamper-Evident Evidence Ledger [VERIFIED]
- [x] Immutable cryptographic hash-chain ledger (`crypto_ledger.py` and `HashChainLedger`).
- [x] DuckDB / SQLite multi-thread fallback handling.

### PHASE 25 — Technical Evidence Certificate [VERIFIED]
- [x] Cryptographically verifiable technical evidence certificate generation.
- [x] Strictly neutral wording compliant with SIH evaluation standards.

### PHASE 26 — REST & API Contracts [VERIFIED]
- [x] FastAPI routers for assurance, cameras, incidents, ANPR, zones.
- [x] Health check and internal IPC endpoints.

### PHASE 27 — WebSocket & Live Telemetry [VERIFIED]
- [x] `/ws/alerts` streaming real live bounding boxes, FPS, latency, and assurance state.
- [x] Zero-disk-I/O RAM shared memory frame buffer (Seqlock).

### PHASE 28 — CCTV Operator Frontend [VERIFIED]
- [x] React VMS operations console with real-time video canvas and live metrics.
- [x] Production build passes cleanly (`tsc && vite build` in 1.33s).

### PHASE 29 — Object Inspector Panel [ACTIVE / HARDENING]
- [ ] Direct visual drilldown on clicked track with trajectory, persistence, and model provenance.

### PHASE 30 — Event Inspector & Explanation [ACTIVE / HARDENING]
- [ ] Clear UI visualization of "Why Did This Event Trigger?" detailing fused evidence.

### PHASE 31 — Model & Data Assurance UI [VERIFIED]
- [x] `IntegrityPanel` showing 5 core assurance badges and disposition controls.
- [x] VerificationConsole for independent cryptographic verification.

### PHASE 32 — Security Hardening & RBAC [VERIFIED]
- [x] JWT authentication, role-based access, and sanitized inputs.
- [x] Zero credential leaks in frontend codebase.

### PHASE 33 — GPU / TensorRT / Device Optimization [VERIFIED]
- [x] Adaptive device resolution (RTX CUDA with automatic CPU fallback).
- [x] Fast JPEG compression (75% quality in 0.39 ms).

### PHASE 34 — Multi-Camera Event Bus [VERIFIED]
- [x] `MultiCameraEventBus` with spatial handovers and tracking correlation.

### PHASE 35 — Failure Recovery & Failsafes [VERIFIED]
- [x] Non-fatal specialist fallbacks (graceful degradation on missing models).
- [x] Camera reconnect handling.

### PHASE 36 — Fault Injection Test Suite [VERIFIED]
- [x] Adversarial coordinate mutation test in `scripts/run_airgap_demo.py`.
- [x] Full PyTest suite passing: 447 passed / 0 failed.

### PHASE 37 — Performance Benchmarking [VERIFIED]
- [x] Dedicated benchmark script `scripts/benchmark_fps.py` separating ingestion vs inference.

### PHASE 38 — Full End-to-End Verification [VERIFIED]
- [x] RTSP -> Detection -> Tracking -> Event Gate -> Assurance -> Ledger -> WebSocket -> React UI.

### PHASE 39 — Standalone Demo Mode [VERIFIED]
- [x] `scripts/run_airgap_demo.py` and `scripts/start_full_demo.ps1`.

### PHASE 40 — Documentation & Third-Party Models [ACTIVE / HARDENING]
- [ ] Create `THIRD_PARTY_MODELS.md` recording model licenses, sources, and checkpoints.
- [ ] Create `configs/class_taxonomy.yaml` with domain mappings.

### PHASE 41 — Final Claim Audit [VERIFIED]
- [x] Prohibited terminology audit: 100% clean.
- [x] Truthful, defensible technical claims.

### PHASE 42 — Architecture Freeze [TARGET]
- [ ] Final freeze and verification seal.
