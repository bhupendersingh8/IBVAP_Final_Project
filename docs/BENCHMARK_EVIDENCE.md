# TCVIAF / IBVAP Reproducible Benchmark Evidence
**Problem Statement**: SIH26228 — Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines  
**Platform**: IBVAP (Integrity-Bound Vision Assurance Platform)  
**Branch**: `feature/tcvf-assurance-layer`  
**Preserved Baseline**: Commit `25c05eba437058b07873ee9aba822ae173fdf1d2`  
**Benchmark Date**: September 30, 2026  

---

> [!IMPORTANT]
> **Defensive Engineering Notice:**
> The benchmark results documented herein are engineering validation measurements conducted on specific physical test hardware under controlled, reproducible conditions. They are NOT a universal deployment guarantee across uncharacterized edge devices or unconstrained field environments.

---

## 1. Test Environment & Hardware Specification

All benchmarks were physically measured and logged via `benchmarks/run_benchmark.py` and stored in machine-readable JSON format at `benchmarks/results/latest.json`.

| Parameter | Measured Specification |
| :--- | :--- |
| **Operating System** | Windows 11 (Build 26200) |
| **Host Processor** | Intel(R) Core(TM) i7-13650HX (16 Cores, 24 Threads) |
| **Discrete GPU** | NVIDIA GeForce RTX 5050 Laptop GPU |
| **CUDA Version** | CUDA 12.8 (Driver 572.16) |
| **Python Runtime** | 3.11.9 (64-bit) |
| **PyTorch Framework** | 2.11.0+cu128 |
| **OpenCV Version** | 4.10.0 |
| **Primary Model Checkpoint** | Ultralytics YOLO11n (`weights/yolo11n.pt`) |
| **Model SHA-256 Digest** | `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1` |
| **Evaluation Input Source** | Synthetic RGB Frames (`synthetic_rgb_640x640`) |
| **Input Resolution** | $640 \times 640$ pixels |
| **Warmup Frames** | 10 frames (CUDA graph and memory pool stabilization) |
| **Measurement Frames** | 50 frames |

---

## 2. Latency & Throughput Benchmark (`benchmarks/results/latest.json`)

The benchmark compares the **Raw Baseline Pipeline** (YOLO11n inference + ByteTrack tracking without cryptographic assurance) against the **Secured Assurance Pipeline** (YOLO11n + ByteTrack + 8-field inference provenance canonicalization + dual classical-quantum hybrid hashing + SQLite ledger persistence).

### Empirical Performance Summary

| Metric | Raw Baseline | Secured Pipeline | Overhead / Delta |
| :--- | :---: | :---: | :---: |
| **Total Evaluation Time** | 0.7472 s | 0.9313 s | +0.1841 s |
| **Mean Latency** | **14.942 ms** | **18.134 ms** | **+3.191 ms (+21.36%)** |
| **Median Latency** | 14.620 ms | 16.471 ms | +1.851 ms |
| **95th Percentile Latency (p95)** | 17.674 ms | 24.622 ms | +6.948 ms |
| **99th Percentile Latency (p99)** | 18.541 ms | 25.720 ms | +7.179 ms |
| **Throughput (FPS)** | **66.92 FPS** | **53.69 FPS** | **-19.77%** |
| **Provenance Canonicalization & Hashing**| — | **0.562 ms** | — |
| **Ledger Disk Persistence (SQLite)** | — | **5.554 ms** | — |

### Key Engineering Insights:
1. **Real-Time Viability**: The secured pipeline sustains **53.69 FPS**, comfortably exceeding standard defense CCTV requirements (25–30 FPS).
2. **Computational Overhead**: Active provenance hashing adds only **0.562 ms** on CPU. The majority of the latency delta (+3.19 ms) stems from disk I/O during ledger commits.
3. **Decoupled Architecture**: In live surveillance mode, ledger commits and forensic MP4 exports are triggered exclusively upon perimeter tripwire breaches. Non-breaching background frames bypass disk writes, preserving maximum frame rates.

---

## 3. Controlled Fault-Injection Battery (`benchmarks/results/fault_injection_latest.json`)

Evaluated via `benchmarks/run_fault_injection.py` to systematically verify detection mechanisms across 17 distinct attack vectors and mutation types.

- **Battery Name**: TCVIAF Controlled Fault-Injection Battery
- **Total Cases**: 17
- **Passed Cases**: 17
- **Failed Cases**: 0
- **Controlled Battery Detection Rate**: **17 / 17 (100.0%)**

### Detailed Mutation Results Table

| Case | Scenario | Expected Detection | Actual Result | Finding Code | Recommended Disposition | Status |
| :---: | :--- | :--- | :--- | :--- | :--- | :---: |
| **1** | Input bytes modified (pixel tampering) | `INPUT_TAMPERING_DETECTED` | Flagged `TAMPERED` | `INPUT_TAMPERING_DETECTED` | `QUARANTINE` | **PASS** |
| **2** | Input hash modified in record | `PROVENANCE_HASH_MISMATCH` | Flagged `TAMPERED` | `PROVENANCE_HASH_MISMATCH` | `QUARANTINE` | **PASS** |
| **3** | Model weight digest modified (weights swap) | `MODEL_TAMPERING_DETECTED` | Flagged `TAMPERED` | `MODEL_TAMPERING_DETECTED` | `QUARANTINE` | **PASS** |
| **4** | Model ID / architecture modified | `MODEL_NAME_MISMATCH` | Flagged `TAMPERED` | `MODEL_NAME_MISMATCH` | `QUARANTINE` | **PASS** |
| **5** | Preprocessing config modified (resolution altered) | `PREPROCESSING_TAMPERING_DETECTED` | Flagged `TAMPERED` | `PREPROCESSING_TAMPERING_DETECTED` | `QUARANTINE` | **PASS** |
| **6** | Inference config modified (threshold altered) | `CONFIG_TAMPERING_DETECTED` | Flagged `TAMPERED` | `CONFIG_TAMPERING_DETECTED` | `QUARANTINE` | **PASS** |
| **7** | Detection class modified | `OUTPUT_TAMPERING_DETECTED` | Flagged `TAMPERED` | `OUTPUT_TAMPERING_DETECTED` | `QUARANTINE` | **PASS** |
| **8** | Detection confidence score modified | `OUTPUT_TAMPERING_DETECTED` | Flagged `TAMPERED` | `OUTPUT_TAMPERING_DETECTED` | `QUARANTINE` | **PASS** |
| **9** | Bounding box geometry modified | `OUTPUT_TAMPERING_DETECTED` | Flagged `TAMPERED` | `OUTPUT_TAMPERING_DETECTED` | `QUARANTINE` | **PASS** |
| **10** | Timestamp modified in record | `PROVENANCE_HASH_MISMATCH` | Flagged `TAMPERED` | `PROVENANCE_HASH_MISMATCH` | `QUARANTINE` | **PASS** |
| **11** | Sequence ID modified in record | `PROVENANCE_HASH_MISMATCH` | Flagged `TAMPERED` | `PROVENANCE_HASH_MISMATCH` | `QUARANTINE` | **PASS** |
| **12** | Nonce modified in record | `PROVENANCE_HASH_MISMATCH` | Flagged `TAMPERED` | `PROVENANCE_HASH_MISMATCH` | `QUARANTINE` | **PASS** |
| **13** | Previous record hash modified | `PROVENANCE_HASH_MISMATCH` | Flagged `TAMPERED` | `PROVENANCE_HASH_MISMATCH` | `QUARANTINE` | **PASS** |
| **14** | Entire record substituted with foreign data | `PROVENANCE_CHAIN_MISMATCH` | Flagged `NOT_VALID` | `SEQ_2_PROVENANCE_HASH_MISMATCH` | `QUARANTINE` | **PASS** |
| **15** | Record replay (duplicate nonce / hash reused) | `PROVENANCE_REPLAY_DETECTED` | Flagged `REPLAY_DETECTED` | `PROVENANCE_REPLAY_DETECTED: Duplicate nonce` | `QUARANTINE` | **PASS** |
| **16** | Chain break (downstream hash linkage broken) | `PROVENANCE_CHAIN_MISMATCH` | Flagged `CHAIN_BROKEN` | `PROVENANCE_CHAIN_MISMATCH: previous_record_hash != provenance_hash` | `QUARANTINE` | **PASS** |
| **17** | Valid unchanged authentic record | `VERIFIED` | Flagged `VERIFIED` | `NONE` | `ACCEPT` | **PASS** |

---

## 4. Threat Model Boundaries & Limitations

To ensure absolute transparency and defensibility during technical review, the operational boundaries of these benchmarks must be understood:

1. **Controlled Battery Scope**: The 17/17 detection rate represents pass/fail validation on a controlled synthetic mutation test harness with known modification vectors. It proves that the mathematical canonicalization, hash comparisons, and sequence validations function as designed; it is **NOT** an empirical detection rate against unconstrained, zero-day adversarial machine learning attacks in the wild.
2. **Local Root Compromise Boundary**: Sequential Merkle hash chaining provides mathematical **tamper evidence**, not physical or cryptographic **tamper prevention**. An adversary who obtains local OS administrative/root privileges and simultaneously overwrites the SQLite database file and all historic logs cannot be stopped by software alone; however, discrepancies with exported Section 65B verification certificates will immediately expose the tampering.
3. **Sensor Authentication Boundary**: Frame byte hashing verifies integrity from ingestion buffer to inference output. It does not authenticate the optical lens against physical laser dazzling, analog lens spoofing, or adversarial physical stickers in the scene.
4. **Baseline Enrollment Prerequisite**: Statistical distribution shift and OOD detection require an enrolled reference baseline ($N \ge 10$ for MMD, $N \ge 3$ for Mahalanobis). In cold-start deployments where no baseline has been established, the system conservatively reports `NO_REFERENCE_BASELINE` rather than fabricating synthetic confidence.

---

## 5. Reproduction Runbook

To reproduce these exact benchmarks independently on any CUDA-capable machine:

```powershell
# 1. Activate isolated Python environment
.\.venv_gpu\Scripts\Activate.ps1

# 2. Execute latency and throughput benchmark (50 measurement frames + 10 warmup)
python benchmarks/run_benchmark.py --frames 50 --warmup 10 --device cuda --model weights/yolo11n.pt

# 3. Execute 17-scenario controlled fault-injection battery
python benchmarks/run_fault_injection.py

# 4. Inspect generated machine-readable outputs
type benchmarks/results/latest.json
type benchmarks/results/fault_injection_latest.json
```
