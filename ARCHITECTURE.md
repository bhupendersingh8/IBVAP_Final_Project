# IBVAP SYSTEM ARCHITECTURE
**Platform:** Intelligent Border Video Analytics Platform (IBVAP)  
**Host Target:** Dell Laptop (Intel Core i3-1115G4, 12GB RAM, Intel UHD Graphics)  
**Hardware Strategy:** CPU-First Primary Execution with Optional CUDA/TensorRT Acceleration  

---

## 1. High-Level Architecture

```
                    ┌────────────────────────────┐
                    │      VIDEO INGESTION       │
                    │   test_video.mp4 / Webcam  │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │    FFmpeg / MediaMTX       │
                    │   rtsp://127.0.0.1:8554    │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │    Bounded Frame Buffer    │
                    │    (drop-oldest queue)     │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │     AI RUNTIME (CPU)       │
                    │  YOLOv8n + ByteTrack (lap) │
                    └──────┬──────────────┬──────┘
                           │              │
       Clean Raw Video Frame              │ Telemetry (BBoxes, Tracks,
                           │              │ Confidence, Badges)
                           ▼              ▼
                    ┌──────────────┐ ┌────────────────┐
                    │ SharedMemory │ │  WebSocket     │
                    │   (Seqlock)  │ │  (/ws/alerts)  │
                    └──────┬───────┘ └───────┬────────┘
                           │                 │
                           ▼                 ▼
                 ┌──────────────────────────────────────┐
                 │       REACT DASHBOARD VIEWPORT       │
                 │   - <img> Tag: Clean Raw Video Feed  │
                 │   - <svg> Layer: Interactive Overlay │
                 │   * ZERO GHOST / DUPLICATE BOXES *   │
                 └──────────────────┬───────────────────┘
                                    │
                                    ▼
                 ┌──────────────────────────────────────┐
                 │          INCIDENT PIPELINE           │
                 │  Rule Engine -> Temporal Engine      │
                 │  -> SQLite (ibvap_dev.db: 7,708 rec) │
                 │  -> SHA-256 Tamper-Evident Ledger    │
                 └──────────────────────────────────────┘
```

---

## 2. Core Architectural Decisions

### A. Decoupled Single-Overlay Rendering (Fixing the Ghost Box Bug)
- **Problem Solved:** Previously, backend OpenCV burned bounding boxes into the video frames while the frontend concurrently rendered SVG bounding boxes from WebSocket telemetry, causing jarring double boxes and jitter.
- **Canonical Architecture:**
  - **Backend Stream:** Serves clean raw camera frames into the SharedMemory buffer (`live_{camera_id}.jpg` / `/api/v1/cameras/{camera_id}/stream`).
  - **Frontend Overlay:** Serves as the single, canonical interactive SVG overlay layer, driven in real-time by WebSocket telemetry.
  - **Forensic Evidence:** Annotated frames are captured only when an incident is triggered or periodically saved to `live_annotated_{camera_id}.jpg` for forensic audit trails without polluting the live browser view.

### B. CPU-First AI Engine with Graceful CUDA Fallback
- **Default Device:** `IBVAP_DEVICE=cpu`. Runs YOLOv8n object detection on Intel Core i3 with 2 threads.
- **Optional Acceleration:** `IBVAP_DEVICE=cuda`. If an NVIDIA GPU (e.g., RTX 3050) is detected via `torch.cuda.is_available()`, the system engages CUDA half-precision FP16. If requested but unavailable, it automatically logs a warning and falls back to CPU without crashing.

### C. Multi-Object Tracking & Association
- Uses `ByteTrackAdapter` backed by `lap` (`lapx` prebuilt C++ wheel) for optimal Hungarian matching and IoU association across occlusions and temporary track loss.

### D. Identity Safety & 4-State Lifecycle
- Explicit states: `UNKNOWN`, `UNVERIFIED`, `AUTHORIZED`, `UNAUTHORIZED`.
- Detection is strictly separated from identification.
- Face crops with low resolution or occluded features default to `UNKNOWN`.
- Unrecognized individuals default to `UNAUTHORIZED`. Identities are never fabricated.

### E. Tamper-Evident Evidence Integrity Ledger
- Every incident produces an evidence block linked via SHA-256 hash chains.
- Terminology: **Tamper-Evident Integrity Verification** (no misleading "tamper-proof" or "unhackable" claims).
- Validated across all 7,694 historical blocks in `data/ibvap_dev.db`.
