# IBVAP — Team Work Allocation & Roadmap

> **5-Member Task Breakdown for SIH PS-26187 Final Delivery**

---

### 👤 Member 1: Computer Vision & ML Engineer
- **Current Foundation**: Pretrained YOLOv8n detector with ByteTrack tracking is verified. ML dataset pipeline & validator are ready.
- **Your Focus**:
  1. Use `python ml/dataset/collect_dataset_frames.py` to extract frames from domain footage in `data/raw/`.
  2. Annotate frames in YOLO format (0: person, 1: car, 2: motorcycle, 3: truck, 4: bus) into `dataset/images/` and `dataset/labels/`.
  3. Run `python ml/dataset/dataset_validator.py` to verify label integrity.
  4. Run `python ml/training/train_pipeline.py` to train domain weights and record real mAP50 in MLflow.

---

### 👤 Member 2: ANPR & Optical Character Recognition Specialist
- **Current Foundation**: `services/anpr/plate_pipeline.py` connects vehicle bounding box cropping with EasyOCR.
- **Your Focus**:
  1. Add high-resolution vehicle test samples (720p/1080p) showing clear Indian license plates.
  2. Implement contrast & sharpening preprocessing (adaptive thresholding) before feeding crops to EasyOCR.
  3. Integrate Indian state regex pattern matching (e.g. `^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$`).

---

### 👤 Member 3: Frontend & Operations UI Developer
- **Current Foundation**: React + Vite + Tailwind dashboard with live WebRTC player, webcam adapter, alert panel, and evidence viewer.
- **Your Focus**:
  1. Build an interactive Polygon Drawing tool on top of the live canvas so operators can configure new virtual fence coordinates in real-time.
  2. Add incident filter controls (filter by Camera, Date Range, Severity level).
  3. Implement CSV/PDF audit export report generator for security commanders.

---

### 👤 Member 4: Backend & Cybersecurity Engineer
- **Current Foundation**: FastAPI async backend with SQLite, JWT authentication, RBAC, and SHA-256 evidence hash chains.
- **Your Focus**:
  1. Provide PostgreSQL production migration via Alembic (`alembic upgrade head`).
  2. Add Redis caching and token revocation blacklist for production multi-worker deployment.
  3. Strengthen TLS/HTTPS and WebRTC SSL configuration for production IP cameras.

---

### 👤 Member 5: QA, Benchmarking & Documentation Lead
- **Current Foundation**: 75 pytest regression tests, MediaMTX RTSP simulator, mock camera sources.
- **Your Focus**:
  1. Benchmark CPU vs GPU latency (measure FPS on Intel i3 vs target deployment hardware).
  2. Create video demonstration recordings showcasing daytime intrusion, night CLAHE enhancement, and webcam testing.
  3. Compile final MHA presentation deck and compliance documentation.
