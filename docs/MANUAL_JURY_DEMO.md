# IBVAP — Manual Jury Live Demonstration Runbook
## Smart India Hackathon 2026 | PS26228 | Team Trinetra

**Project**: IBVAP (Integrity-Bound Vision Assurance Platform)  
**Theme**: Blockchain & Cybersecurity  
**Target Duration**: 3 to 5 Minutes  

---

## 1. Quick Terminal Live Demo (Guaranteed 5-Second Physical Execution)

If the evaluation panel asks for an immediate, verifiable cryptographic proof of computer vision integrity assurance:

### Step 1: Open Terminal in Project Root
```powershell
cd C:\Users\anmol\.gemini\antigravity\scratch\IBVAP_Final_Project
.\.venv_gpu\Scripts\python.exe scripts\demo_tamper_assurance_cycle.py
```

### What Executes On Screen (Zero Crashes, < 5 Seconds):
1. **Stage 1 (Contributor Onboarding)**: Generates an Ed25519 contributor keypair, signs the YOLO11n weight hash (`0ebbc8...`), and outputs a valid CycloneDX v1.5 AIBOM.
2. **Stage 2 (Nominal Inference)**: Ingests an authentic surveillance frame, generates detection bounding boxes, computes the canonical SHA-256 digest, and links Block #1 (`ACCEPT`).
3. **Stage 3 & 4 (Tamper Injection & Quarantine)**: Flips 1 pixel in the input frame buffer. The assurance engine computes `input_hash`, detects the mismatch against the provenance record, triggers finding `INPUT_TAMPERING_DETECTED`, and routes the frame to `QUARANTINE`.
4. **Stage 5 (Replay Defense)**: Attempts to re-inject Block #1's nonce and timestamp. The engine detects nonce reuse, flags `PROVENANCE_REPLAY_DETECTED`, and drops the replayed block.
5. **Stage 6 (Electronic Certificate)**: Generates a technical electronic evidence certificate JSON capturing operating parameters and the unbroken hash chain.

---

## 2. Interactive Full-Stack GUI Demonstration

### Step 1: Launch Services (If not already running)
```powershell
# Terminal 1 - Backend API:
.\.venv_gpu\Scripts\python.exe -m uvicorn apps.backend.main:app --host 127.0.0.1 --port 8000

# Terminal 2 - Frontend UI:
cd apps\frontend
npm run dev
```

### Step 2: Open Browser
Navigate to `http://localhost:5173/`

### Step 3: Core Demonstration Flow for Evaluators

#### Minute 1: The Trust Deficit in Computer Vision
- **Navigate to**: `http://localhost:5173/c4isr` (Command & Assurance Console).
- **Point out to Jury**:
  - Top header badges: **Air-Gapped Edge Node**, **SHA-256 Merkle Ledger**, **DuckDB Block Counter**.
  - Explain: *"Most computer vision teams output raw bounding boxes. If an attacker tampers with camera frames or model weights, standard systems produce false alerts or miss critical events. IBVAP binds every detection cryptographically to its input pixels, model checkpoint, and hyperparameters in 0.562 ms."*

#### Minute 2: Live Cryptographic Chain Verification
- Click on the **`Ledger`** tab or click the **`[Verify SHA-256]`** button in the Incident Feed.
- Click **`Verify Chain Integrity`**:
  - The modal re-calculates the recursive SHA-256 chain from Genesis Block to current tip.
  - Green banner confirms: `CHAIN INTACT - 0 TAMPERING DETECTED`.
  - Point out: Every record stores `input_hash`, `model_digest`, `config_hash`, and `previous_record_hash`.

#### Minute 3: Answering the #1 Jury Trap: "Is a signed model safe?"
- Explain the **Signed $\neq$ Safe** breakthrough:
  - *"If a malicious insider or compromised supplier signs a backdoored model with a valid Ed25519 key, standard code signing passes it as authentic."*
  - *"IBVAP enforces Dual-Gated Admission: Ed25519 verifies author identity, while our Behavioral Fingerprint Engine independently probes activation and output distributions across 5 standardized test patterns. If a signed model exhibits divergence, it is sent to QUARANTINE."*

#### Minute 4: Legal Evidence Framing under Indian Law
- Show the **Technical Electronic Evidence Certificate**.
- Explain: *"We do not make the legally absurd claim that software automatically decides court admissibility. Our system produces the cryptographically verifiable electronic-evidence certificate designed to support evidence/audit workflows under applicable provisions of the Bharatiya Sakshya Adhiniyam, 2023."*

---

## 3. Fallback & Troubleshooting Matrix

| Scenario | Contingency Action |
| :--- | :--- |
| **No External Internet / Air-Gapped** | System is 100% offline. All model weights (`yolo11n.pt`, etc.) and dependencies are local in `.venv_gpu`. |
| **No GPU / CUDA Error** | The engine automatically falls back to CPU execution without crashing (`device = "cpu"`). |
| **Port 8000 or 5173 Busy** | Run the headless script: `.\.venv_gpu\Scripts\python.exe scripts\demo_tamper_assurance_cycle.py`. |
| **Live RTSP Camera Missing** | System automatically falls back to synthetic video frames or local MP4 loop in `data/sample_cctv.mp4`. |
