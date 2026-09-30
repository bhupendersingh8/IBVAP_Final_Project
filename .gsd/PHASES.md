# GSD Development Phases: IBVAP (SIH-26187)

## Phase 1: Environment & Virtual Runtime Bootstrap
- [x] Check Python 3.11 and Node.js toolchains.
- [x] Verify NVIDIA GPU and driver capability (RTX 5050 Laptop GPU detected).
- [ ] Initialize Python virtual environment (venv_rtx or venv).
- [ ] Install base dependencies (requirements.txt, PyTorch with CUDA support).
- **Verification Gate**: `python run_tests_standalone.py` passes without module errors.

## Phase 2: Core Vision & Media Ingestion Pipeline
- [x] Local YOLO detection backbone (yolov8n.pt).
- [ ] MediaMTX RTSP ingestion server startup verification (infrastructure/mediamtx).
- [ ] Real-time frame queueing and multi-camera stream benchmark.
- **Verification Gate**: 4-stream concurrent processing maintaining >= 25 FPS without VRAM exhaustion.

## Phase 3: ANPR, Cryptographic Ledger & Evidence Binding
- [x] Real-time Merkle ledger integration (crypto_ledger.py).
- [x] Post-Quantum Cryptography (WOTS+-SHAKE256) validation router.
- [ ] Automated license plate extraction and OCR pipeline linking to ledger entries.
- **Verification Gate**: Every detected vehicle and intrusion event is cryptographically hashed, signed, and persisted into evidence_ledger.duckdb.

## Phase 4: Frontend Operations & Integrity Test Lab
- [x] React VMS Operations Dashboard UI built with Vite + TailwindCSS.
- [x] Installed @opengsd/gsd-core for Spec-Driven Development.
- [x] Live backend API endpoints wired for OOD (Mahalanobis, kNN) and Label Quality.
- [ ] Live WebSocket event streaming between FastAPI backend (apps/backend) and frontend.
- **Verification Gate**: Dashboard renders live event feed, telemetry stats, and interactive test lab without uncaught console errors.

## Phase 5: SIH Final Jury & Pitch Rehearsal
- [ ] End-to-end dry run using start_ibvap_rtx3050.bat.
- [ ] Offline demo runbook validation (docs/MONDAY_SIH_DEMO_RUNBOOK.md).
- **Verification Gate**: Zero-network 1-click startup executes cleanly in front of evaluators.
