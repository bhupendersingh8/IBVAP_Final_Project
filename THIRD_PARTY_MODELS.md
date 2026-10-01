# Third-Party Models & Model Supply-Chain Registry

## Project: TRINETRA / IBVAP (SIH26187 & SIH26228)
### Layer 187 Vision Intelligence & Layer 228 Integrity Assurance

Every external model integrated into IBVAP conforms to the Model Supply-Chain Admission Gate:
`Source Check -> License Verification -> Physical Checkpoint SHA-256 -> CycloneDX AIBOM -> Behavioral Probe -> Production Admission`.

---

| Model Identifier | Architecture / Variant | Primary Task | Official Checkpoint / Artifact | Checkpoint SHA-256 Digest | Software License | Commercial / Deployment Terms | Local Admission Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `yolo11n` | Ultralytics YOLO11 Nano | Primary 640x640 Object Detection | `weights/yolo11n.pt` | `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1` | AGPL-3.0 / Enterprise | Open-source evaluation / Local offline inference | **TRUSTED (Production Baseline)** |
| `yolo26n` | Ultralytics YOLO26 Nano | Multi-scale Primary Object Detection | `models/detection/yolo26n.pt` | `41fbb7538a7c1e5d36e2d14bc912301b1fe452093e9619a0a4c51480e6e73dbb` | AGPL-3.0 / Enterprise | High-throughput edge detection | **TRUSTED (Production Active)** |
| `threat_yolov8n` | Custom Military Threat Detector | Weapon, Blade & Explosive Detection | `weights/threat_yolov8n.pt` | `83906a5b78ff311c9704e67d26ba8c91350a41d00c35fce5a189f7831d04d805` | Proprietary / Defence Evaluation | Armed threat classification | **TRUSTED (Gated Specialist)** |
| `mobile_sam` | Mobile Segment Anything (Lightweight) | Target Silhouette Isolation & Camouflage Boundary | `weights/mobile_sam.pt` | `c0cf4e2221b6d19453c5186b5177893116d418bc00936bcce0b484ea0bc5cfcf` | Apache-2.0 | Permissive open-source | **TRUSTED (Conditional Gated)** |
| `zero_dce_pp` | Zero-Reference Deep Curve Estimation++ | Low-Light & Night Photometric Restoration | `ml/models/zero_dce.py` (Embedded PyTorch) | Dynamic Checksum Bound | MIT | Permissive open-source | **TRUSTED (Adaptive Gated)** |
| `bytetrack` | ByteTrack Multi-Object Tracker | Multi-Target Trajectory & ID Association | `services/tracking/bytetrack_adapter.py` | Algorithm Checksum Bound | MIT | Permissive open-source | **TRUSTED (Core Tracker)** |
| `paddleocr_mobile` | PaddleOCR Mobile v4 Engine | Vehicle License Plate Text Recognition | EasyOCR / Offline Rule-Based Fallback | Local Engine Bound | Apache-2.0 | Offline OCR execution | **TRUSTED (Specialist Gated)** |
| `haar_face_baseline` | OpenCV Haar Cascade Head Tracker | Zero-Hardware Face & Head Localization | Embedded OpenCV Cascade | Built-in OpenCV Checksum | BSD-3-Clause | Zero-constraint CPU fallback | **TRUSTED (Zero-Crash Fallback)** |
| `rule_based_copilot` | Deterministic Scene Context Engine | Operator Query & Spatial Reasoning Copilot | `services/copilot/rule_copilot.py` | Local Engine Bound | Apache-2.0 | 100% Offline Rule Engine | **TRUSTED (Offline Baseline)** |
| `ed25519_crypto` | RFC 8032 Ed25519 Signature Suite | Model Manifest & Evidence Signing | `services/assurance/manifest_verifier.py` | Standard RFC 8032 | Public Domain / OpenSSL | Cryptographic Primitive | **TRUSTED (Assurance Core)** |

---

### Supply-Chain Policy & Governance
1. **Air-Gapped & Offline Verification**: No model binary downloads or external API calls are made at runtime. All weights reside in `weights/` and `models/`.
2. **"Signed != Safe" Guarantee**: Cryptographic signature on model manifests proves origin authenticity; physical SHA-256 weight checksums ensure tamper-evidence; behavioral fingerprint probe sets detect runtime deviations before models are promoted to production.
3. **Graceful Fallback Hierarchy**: In accordance with the Zero-Crash design principle, if any secondary specialist model is unavailable on the local host, the system activates a deterministic lightweight fallback without failing the primary vision pipeline.
