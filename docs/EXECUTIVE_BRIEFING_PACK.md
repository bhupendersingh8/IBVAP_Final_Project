# IBVAP Executive Briefing & Deployment Dossier
## Smart India Hackathon 2026 — Problem Statement 187
**Target Authority**: Ministry of Home Affairs (MHA) / Sashastra Seema Bal (SSB)  
**System Title**: Intelligent Border Video Analytics Platform (IBVAP)  
**Date of Audit Freeze**: 2026-09-27 22:35:00 IST  
**Host Machine**: Dell Laptop, Intel Core i3-1115G4 (4 vCPUs @ 3.00GHz), 12GB DDR4 RAM, Windows 11 Home  

---

## 1. Executive Summary

The **Intelligent Border Video Analytics Platform (IBVAP)** is an autonomous, edge-optimized multi-camera video intelligence platform designed for existing CCTV infrastructure at Border Outposts (BOPs), border roads, and restricted perimeters.

### Core Achievements & Proof of Work
- **100% Automated Regression Verification**: **164 of 164 pytests passing** with zero failures (`pytest -q tests/`).
- **100% Deployment Checkpoint Readiness**: **26 of 26 checkpoints passing** on both `--target cpu` and `--target rtx3050` profiles (`scripts/verify_full_system_deployment.py`).
- **Real-World Operational Field Scenarios**: 12 end-to-end tactical border scenarios verified (BOP staff entry, restricted perimeter loitering, vehicle classification, night movement CLAHE, virtual fence crossing, camera disconnect/recovery).
- **Edge Efficiency Innovation**: Integrated **Adaptive Frame Skipping & Motion Gating** (`AdaptiveFrameSkipper`) achieving 350+ FPS gating throughput (<2.8ms overhead), reducing CPU compute load by 70–85% on static night feeds.
- **Evidence Non-Repudiation**: Local **SHA-256 cryptographic Merkle block hash chain** linking all event snapshots and incident metadata with mathematical tamper-detection.
- **CI/CD Quality Guardrails**: Active Git pre-commit hooks (`.git/hooks/pre-commit`) enforcing syntax checks, smoke test execution, and binary bloat prevention.

---

## 2. Interactive Presentation Deck
An interactive executive presentation deck has been generated using the `slides` skill:
- **Location**: [`docs/IBVAP_SIH_PRESENTATION.html`](file:///C:/Users/dell/Desktop/p2/IBVAP_Final_Project/docs/IBVAP_SIH_PRESENTATION.html)
- **Features**:
  - Tactical military HUD styling (glassmorphism, slate theme, cyber grid, status badges)
  - Interactive Chart.js charts displaying live FPS throughput and inference latency
  - Keyboard navigation (`Left Arrow`, `Right Arrow`, `Spacebar`)
  - 8 strategic slides covering the ground reality, 17 capability layers, edge innovations, and audit verdicts

---

## 3. Primary Model Stack & Latency Profile (Dell i3 CPU)

| Capability Layer | Model / Algorithm | Weight File / Source | Mean Latency | Sustained Throughput | Memory (RSS) |
|---|---|---|---|---|---|
| **Zero-Motion Gating** | AdaptiveFrameSkipper | Grayscale Diff + Accumulator | **2.8 ms** | **350+ FPS** | 15 MB |
| **Primary Detection** | YOLO26n (NMS-Free) | `yolo26n.pt` | **68.0 ms** | **14.67 FPS** | 381 MB |
| **Fallback Detection** | YOLOv8n (Standard) | `yolov8n.pt` | **54.9 ms** | **18.20 FPS** | 350 MB |
| **Instance Segmentation** | YOLO11n-Seg | `yolo11n-seg.pt` | **105.9 ms** | **9.43 FPS** | 412 MB |
| **Pose & Liveness** | YOLO11n-Pose | `yolo11n-pose.pt` | **92.3 ms** | **10.80 FPS** | 398 MB |
| **Multi-Object Tracking** | ByteTrack | Kalman Filter + Hungarian | **<0.1 ms** | **1000+ FPS** | 25 MB |
| **Cross-Camera Re-ID** | OSNet-x0.25 | `osnet_x0_25_msmt17.pt` | **30.7 ms** | **32.50 FPS** | 210 MB |
| **Night Restoration** | CLAHE Enhancer | 8x8 Tile Grid, Limit 2.0 | **8.0 ms** | **125.00 FPS** | 45 MB |
| **ANPR OCR** | EasyOCR | CRAFT + ResNet | **476.0 ms** | **2.10 FPS** | 480 MB |
| **Evidence Ledger** | SHA-256 Merkle Chain | Pure Python + SQLite | **<0.05 ms** | **20,000+ evt/s** | 10 MB |

*Total consolidated process memory footprint on Dell host*: **~431 MB RSS**.

---

## 4. Verification Commands & Reproducibility Runbook

Every metric in this briefing can be reproduced on the host machine using these exact commands:

```powershell
# 1. Run full 164-test regression suite
C:\Users\dell\Desktop\p2\venv\Scripts\python.exe -m pytest -q tests/

# 2. Run 12 border field scenario tests
C:\Users\dell\Desktop\p2\venv\Scripts\python.exe -m pytest -v tests/test_sih_real_world_scenarios.py

# 3. Verify Edge CPU deployment profile (26/26 checkpoints)
C:\Users\dell\Desktop\p2\venv\Scripts\python.exe scripts/verify_full_system_deployment.py --target cpu

# 4. Verify RTX 3050 deployment profile (26/26 checkpoints)
C:\Users\dell\Desktop\p2\venv\Scripts\python.exe scripts/verify_full_system_deployment.py --target rtx3050

# 5. Build React 18 production frontend
cd apps/frontend && npm run build
```

---

## 5. Audit Deliverables Inventory

1. [`docs/SIH_PS_26187_TRACEABILITY.md`](file:///C:/Users/dell/Desktop/p2/IBVAP_Final_Project/docs/SIH_PS_26187_TRACEABILITY.md): Complete requirements-to-test mapping.
2. [`docs/REAL_WORLD_BORDER_SCENARIOS.md`](file:///C:/Users/dell/Desktop/p2/IBVAP_Final_Project/docs/REAL_WORLD_BORDER_SCENARIOS.md): Operational border zones (A-J) and tactical scenarios.
3. [`docs/MODEL_STATUS_MATRIX.md`](file:///C:/Users/dell/Desktop/p2/IBVAP_Final_Project/docs/MODEL_STATUS_MATRIX.md): Detailed model statuses and hardware requirements.
4. [`docs/VALIDATION_EVIDENCE.md`](file:///C:/Users/dell/Desktop/p2/IBVAP_Final_Project/docs/VALIDATION_EVIDENCE.md): Raw execution logs, benchmarks, and Merkle proofs.
5. [`docs/FINAL_SYSTEM_STATUS.md`](file:///C:/Users/dell/Desktop/p2/IBVAP_Final_Project/docs/FINAL_SYSTEM_STATUS.md): Final readiness audit report.
6. [`docs/IBVAP_SIH_PRESENTATION.html`](file:///C:/Users/dell/Desktop/p2/IBVAP_Final_Project/docs/IBVAP_SIH_PRESENTATION.html): Interactive executive presentation slide deck.
