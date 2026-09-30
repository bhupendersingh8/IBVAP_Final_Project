# 🔬 FORENSIC RUNTIME VERIFICATION REPORT: YOLO26x STATUS IN IBVAP
**System:** Intelligent Border Video Analytics Platform (SIH26187)  
**Investigation Directive:** Independent Read-Only Forensic Runtime Audit  
**Target Query:** Verification of the claim *"YOLO26x is 100% active in the real IBVAP production pipeline"*  
**Audit Timestamp:** `2026-09-29T14:40:00Z` (`2026-09-29 20:10:00 IST`)  
**Hardware Environment:** NVIDIA GeForce RTX 5050 Laptop GPU (8.0 GB VRAM, CUDA 12.8, Driver 572.70)  

---

## 1. Checkpoint Physical Inspection & Architecture Dissection

A forensic inspection of the physical checkpoint files was conducted using PyTorch 2.6.0 and Ultralytics 8.4.163 with full tensor inspection (`weights_only=False`):

### 1.1 Metadata Extraction: `weights/yolo26x.pt` & `models/detection/yolo26x.pt`

```python
# Raw Checkpoint Header Telemetry
{
    "date": "2024-09-25T21:10:31.417215",
    "version": "8.2.100",
    "license": "AGPL-3.0 License (https://ultralytics.com/license)",
    "docs": "https://docs.ultralytics.com",
    "epoch": -1,
    "model_class": "DetectionModel",
    "model_type": "<class 'ultralytics.nn.tasks.DetectionModel'>",
    "yaml_file": "yolo11x.yaml",
    "backbone": [
        [-1, 1, "Conv", [64, 3, 2]],
        [-1, 1, "Conv", [128, 3, 2]],
        [-1, 2, "C3k2", [256, False, 0.25]]
    ],
    "total_parameters": 56966176
}
```

### 1.2 Cryptographic Hash Comparison (SHA-256)

| Target Checkpoint Path | File Size (Bytes) | SHA-256 Hex Digest | Internal Architecture |
|---|---|---|---|
| `yolo11x.pt` (Repository Root) | `114,636,239` | `7bc158aa95c0ebfdd87f70f01653c1131b93e92522dbe15c228bcd742e773a24` | `yolo11x.yaml` (YOLO11x) |
| `weights/yolo26x.pt` | `114,636,239` | `7bc158aa95c0ebfdd87f70f01653c1131b93e92522dbe15c228bcd742e773a24` | `yolo11x.yaml` (YOLO11x) |
| `models/detection/yolo26x.pt` | `114,636,239` | `7bc158aa95c0ebfdd87f70f01653c1131b93e92522dbe15c228bcd742e773a24` | `yolo11x.yaml` (YOLO11x) |
| `weights/yolo26n.pt` | `5,613,764` | `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1` | `yolo11n.yaml` (YOLO11n) |
| `weights/yolo11n.pt` | `5,613,764` | `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1` | `yolo11n.yaml` (YOLO11n) |

### 1.3 Forensic Determination on Model Identity
> **MISLABELED/RENAMED CHECKPOINT — NOT VERIFIED AS YOLO26**  
>
> The checkpoint file `yolo26x.pt` is **bit-for-bit identical to official Ultralytics `yolo11x.pt`** (SHA-256: `7bc158aa...`).  
> Internal model architecture metadata explicitly defines `yaml_file: yolo11x.yaml`, trained on `2024-09-25` with `56,966,176` parameters under Ultralytics version 8.2.100.  
> Similarly, `yolo26n.pt` is **bit-for-bit identical to official Ultralytics `yolo11n.pt`** (SHA-256: `0ebbc80d...`).  
> **No genuine YOLO26 architecture exists in Ultralytics or in the global computer vision ecosystem**; these checkpoints are renamed YOLO11 models.

---

## 2. Actual Runtime Code Path Trace

The actual execution flow from live physical camera / recorded video to dashboard:

```
[1. Ingestion]
    Physical RTSP / Local MP4 (data/raw/test_video.mp4)
    -> RTSPSource (services/ingestion/rtsp_source.py) or cv2.VideoCapture
    -> Decoded BGR Frame (np.ndarray)

[2. Preprocessing & Low-Light Enhancement]
    -> Luminance check via np.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    -> If mean < 40.0: Zero-DCE++ Deep Curve Estimator (models/enhancement/zero_dce.py)

[3. Stage-1 Primary Gating Detector]
    -> In main_pipeline.py: self.detector.track() using yolo11n / rtdetr-l (conf=0.20)
    -> In main_inference_worker.py: YOLOAdapter using ModelSelector().resolve() (models/detection/yolo26n.pt, conf=0.25)
    -> Yields raw candidate bounding boxes: [x1, y1, x2, y2, conf, class_id]

[4. Gating Decision Logic]
    -> In TwoStageYOLO26Pipeline.process_frame() & verify_tracks()
    -> Check: is_borderline = (0.25 <= conf <= 0.65) OR is_threat_class (person, car, truck, bus, motorcycle)
    -> If candidate is high-confidence non-threat (>0.65): tagged DIRECT_HIGH_CONF (Stage-2 bypassed)
    -> If candidate is threat or borderline: candidate bounding box cropped from frame (crop_w >= 8, crop_h >= 8)

[5. Stage-2 Heavy Verification (yolo26x.pt / 56.9M params)]
    -> Batched forward pass: self.heavy_verifier(crops_to_verify, conf=0.50, device="cuda")
    -> If heavy verifier detects object:
         tagged: verification_status = "VERIFIED_YOLO26X", yolo26x_verified = True, yolo26x_conf = best_conf
    -> If heavy verifier fails to detect object:
         tagged: verification_status = "REJECTED_FALSE_POSITIVE", yolo26x_verified = False

[6. Tracking & Trajectory State]
    -> ByteTrackAdapter (services/tracking/bytetrack_adapter.py) or FallbackIoUTracker
    -> Track ID assignment and 50-point trajectory maintenance

[7. Spatial & Temporal Reasoning]
    -> Spatial: RuleEngine.evaluate() against configured zone polygons and virtual fence (configs/zones.yaml)
    -> Temporal: TemporalEventEngine (services/analytics/temporal_engine.py) checks loitering dwell time & repeated entry

[8. Evidence & Cryptographic Commitment]
    -> CryptoEvidenceLedger.commit_event() (crypto_ledger.py) computes SHA-256 frame hash,
       chains Merkle root hash into evidence_ledger.duckdb, and triggers Section 65B forensic clip export

[9. Dashboard Broadcast]
    -> Telemetry payload includes track items with "verification_status" and "yolo26x_verified"
    -> WebSocket hub broadcasts to React C4ISR Dashboard (apps/frontend/src/pages/Dashboard.tsx)
```

---

## 3. Exact Code Path Loading `yolo26x.pt`

The checkpoint `yolo26x.pt` is explicitly loaded in three distinct files:

1. **`services/detection/two_stage_yolo26.py` (Line 125)**:
   ```python
   self.heavy_verifier = YOLO(f"{weights_dir}/yolo26x.pt")
   self.heavy_verifier.to(self.device)
   ```
2. **`main_pipeline.py` (Lines 183–199 & 740–750)**:
   ```python
   weights_x = self.cfg.weights_dir / "yolo26x.pt"
   if weights_x.exists() or (PROJECT_ROOT / "weights" / "yolo26x.pt").exists():
       self.yolo26_pipeline = TwoStageYOLO26Pipeline(weights_dir=self.cfg.weights_dir, device=str(self.device))
   ...
   if self.yolo26_pipeline is not None and parsed_tracks:
       parsed_tracks = self.yolo26_pipeline.verify_tracks(enhanced_frame, parsed_tracks, ...)
   ```
3. **`services/inference/main_inference_worker.py` (Lines 301–313 & 882–886)**:
   ```python
   two_stage_weights = os.path.join(PROJECT_ROOT, "weights")
   if _TWO_STAGE_AVAILABLE and os.path.exists(os.path.join(two_stage_weights, "yolo26x.pt")):
       self.two_stage_pipeline = TwoStageYOLO26Pipeline(weights_dir=two_stage_weights, device=target_device)
   ...
   if self.two_stage_pipeline and tracking_result.active_tracks:
       self.two_stage_pipeline.verify_tracks(frame, tracking_result.active_tracks)
   ```

---

## 4. Live Runtime vs Test/Audit Proof

| Context | Does it load `yolo26x.pt`? | Proof from Code / Process |
|---|---|---|
| **Live Camera Runtime (`main_inference_worker.py`)** | **YES** | Lines 304–310 instantiate `TwoStageYOLO26Pipeline` on startup if `weights/yolo26x.pt` exists. When active camera streams, line 884 invokes `verify_tracks` on active tracks. |
| **Unified Sentry Pipeline (`main_pipeline.py`)** | **YES** | Lines 1049–1058 check `has_yolo26` and enable `use_yolo26x_stack=True` by default, executing `verify_tracks` at line 742. |
| **Audit Script (`test_execution_audit.py`)** | **YES** | Module 6 instantiates `TwoStageYOLO26Pipeline` directly and runs 3 benchmark warmup and execution passes. |
| **Unit Test Suite (`tests/test_two_stage_yolo26.py`)** | **YES** | 5 unit tests test cascade loading, ROI cropping, and verification tags. |

**Verdict:** The model is **not merely registered in YAML or audited in tests**; it is physically instantiated and invoked in both `main_inference_worker.py` (live RTSP worker) and `main_pipeline.py` (standalone sentry). However, the underlying checkpoint being executed is YOLO11x.

---

## 5. Inspection of `services/detection/two_stage_yolo26.py`

- **Actual Stage-1 Model:** `YOLO(f"{weights_dir}/yolo26n.pt")` (YOLO11n architecture, 2,624,080 parameters).
- **Actual Stage-2 Model:** `YOLO(f"{weights_dir}/yolo26x.pt")` (YOLO11x architecture, 56,966,176 parameters).
- **Confidence Thresholds:**
  - `conf_primary`: `0.25` (Gating detector sensitivity)
  - `conf_borderline_max`: `0.65` (Upper threshold for borderline gating)
  - `conf_verifier`: `0.50` (Heavy model verification threshold)
- **Conditions Triggering Stage-2:**
  - `(0.25 <= confidence <= 0.65)` (Borderline detections) **OR**
  - Target class belongs to `THREAT_CLASSES`: `{"person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "van", "suv"}`.
  - Bounding box dimension must satisfy `width >= 8` pixels and `height >= 8` pixels.
- **Does every frame go through Stage-2?**
  - **NO.** Only frames containing detected candidates matching the above conditions trigger Stage-2. Frames with no detections or only non-threat objects above `0.65` confidence completely bypass the heavy model.
- **Is Stage-2 output consumed downstream?**
  - **YES, in telemetry and evidence:** Tags `tr.verification_status = "VERIFIED_YOLO26X"` and `tr.yolo26x_verified = True`. These fields are serialized into the WebSocket telemetry stream and recorded in DuckDB.
  - **PARTIAL in spatial rules:** `rule_engine.py` currently computes perimeter breaches based on bounding box geometry of active tracks, regardless of whether `verification_status` is `VERIFIED_YOLO26X` or `DIRECT_HIGH_CONF`.

---

## 6. Execution Audit Observation (Module 6)

Direct unedited output from `test_execution_audit.py` on local RTX hardware:

```text
[*] Auditing Module 6: Two-Stage YOLO26x Stack Cascade Verifier...
  [PASS]  Two-Stage YOLO26x Stack Verifier         |  165.11 ms | Two-stage cascade @ 165.1ms (6.1 FPS) | Gating: 17.9ms | Verified: 1 threats | Heavy: 57.0M params
```

- Hardware: `NVIDIA GeForce RTX 5050 Laptop GPU (8.0 GB VRAM, CUDA 12.8)`
- Primary Gating Latency: `17.9 ms` (YOLO26n / YOLO11n)
- Heavy Verifier Latency: `147.2 ms` (YOLO26x / YOLO11x batched crop pass)
- Total Cascade Latency: `165.11 ms`
- Heavy Model Parameter Count: `56,966,176` (57.0M)

---

## 7. Controlled Recorded-Video Test Benchmark

Executed on `data/raw/test_video.mp4` across **20 consecutive frames** on `cuda`:

### 7.1 Per-Stage Latency Breakdown (Mean over 20 Frames)

| Processing Stage | Mean Latency (ms) | Min (ms) | Max (ms) | Notes |
|---|---|---|---|---|
| **Capture / Decode** | `4.34 ms` | `0.27` | `72.66` | OpenCV MP4 Demux & Decode |
| **Preprocessing / Zero-DCE** | `0.24 ms` | `0.20` | `0.39` | Luminance calculation (mean > 40, no lift needed) |
| **Stage-1 Primary Inference** | `39.80 ms` | `18.23` | `151.78` | Full-frame YOLO11n gating on CUDA FP16 |
| **Tracking (ByteTrack)** | `42.67 ms` | `19.77` | `157.47` | Multi-object Kalman filter & trajectory association |
| **Stage-2 YOLO26x Verifier** | `214.89 ms` | `140.83` | `336.18` | Heavy 56.9M model forward pass on candidate crops |
| **Spatial Reasoning (Virtual Fence)** | `< 0.05 ms` | `0.00` | `0.01` | Polygon intersection & virtual fence line checks |
| **Temporal Reasoning & SAM** | `< 0.05 ms` | `0.00` | `0.01` | Dwell time & movement velocity checks |
| **Event / Crypto Evidence Ledger** | `< 0.05 ms` | `0.00` | `0.01` | Merkle hash chaining (triggered on breaches) |
| **Total End-to-End Latency** | **`455.60 ms`** | **`236.87`** | **`2915.32`** | Full 7-layer unified chain latency |

### 7.2 Throughput Performance
- **Sustained End-to-End Throughput:** `2.2 FPS` (with heavy 56.9M parameter verifier evaluating multiple crops per frame on laptop GPU).
- **Stage-1 Alone Throughput:** `25.1 FPS` (without Stage-2 verifier).

---

## 8. Runtime Logs and System Counters

Runtime counters verified during the 20-frame test:

| Counter Name | Measured Value | Meaning |
|---|---|---|
| **Total Frames Ingested** | `20` | Total video frames read from disk |
| **Stage-1 Full Frames Processed** | `20` | Frames evaluated by primary gating model |
| **Stage-2 Cascade Invocations** | `20` | Frames where at least 1 candidate triggered Stage-2 |
| **Actual YOLO26x/yolo11x Crop Inferences** | `37` | Cumulative candidate ROIs cropped and forwarded to 56.9M model |
| **Cumulative Tracks Maintained** | `110` | Active track states across the 20 frames |
| **Cumulative Perimeter Breaches Logged** | `3` | Targets crossing virtual boundary |
| **SHA-256 Ledger Blocks Committed** | `88` | Total immutable blocks committed to DuckDB |

---

## 9. Expected vs. Actual Comparison

| Evaluation Dimension | Expected Claim | Actual Runtime Evidence |
|---|---|---|
| **Model Family** | YOLO26x (New architecture) | **YOLO11x** (`yolo11x.yaml`, released Sept 2024 by Ultralytics) |
| **File Checkpoint** | `yolo26x.pt` | Renamed exact copy of `yolo11x.pt` (SHA-256 matches bit-for-bit) |
| **Parameter Count** | ~56.9M Parameters | **56,966,176 Parameters** (Exact match for YOLO11x) |
| **Two-Stage Execution** | Fast gating + Heavy verifier | **VERIFIED ACTIVE** (YOLO11n gates -> YOLO11x verifies on CUDA) |
| **Conditional Triggering** | Only borderline / threat ROIs | **VERIFIED ACTIVE** (Only crops of threats/borderline enter Stage 2) |
| **Downstream Telemetry** | Tagged as `VERIFIED_YOLO26X` | **VERIFIED ACTIVE** (Streamed over WebSocket to React UI) |
| **Hardware Compute** | CUDA GPU Acceleration | **VERIFIED ACTIVE** (Runs on RTX 5050 Laptop GPU @ 147–214ms) |

---

## 10. Final Verification Verdict Table

| Claim | Evidence | Verified? |
|---|---|---|
| **YOLO26x checkpoint physically exists** | `weights/yolo26x.pt` & `models/detection/yolo26x.pt` exist on disk (114.6 MB) | **YES** |
| **Actual architecture is YOLO26** | Checkpoint header has `yaml_file: yolo11x.yaml`, date `2024-09-25`. Identical hash to `yolo11x.pt`. **MISLABELED/RENAMED CHECKPOINT — NOT VERIFIED AS YOLO26**. | **NO** |
| **Stage-1 gating is active** | `main_pipeline.py` & `main_inference_worker.py` execute primary gating pass on every frame. | **YES** |
| **Stage-2 heavy model is active** | `TwoStageYOLO26Pipeline.heavy_verifier` is loaded on CUDA and executed. | **YES** |
| **Stage-2 is triggered conditionally** | Only crops satisfying `(0.25 <= conf <= 0.65)` or threat classes are passed to Stage-2. | **YES** |
| **Stage-2 output reaches tracker/events** | `tr.verification_status` and `tr.yolo26x_verified` are attached to tracks and sent over WebSocket. | **YES** |
| **Live/recorded pipeline uses it** | Both `main_inference_worker.py` (live CCTV) and `main_pipeline.py` invoke `verify_tracks()`. | **YES** |
| **GPU acceleration is active** | Both Stage 1 and Stage 2 execute on `cuda` (NVIDIA GeForce RTX 5050 Laptop GPU). | **YES** |
| **End-to-end cascade works** | Frame -> Preprocessing -> Stage 1 -> Crop Gating -> Stage 2 -> ByteTrack -> DuckDB -> UI. | **YES** |
