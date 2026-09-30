# IBVAP Final Hardening Baseline Snapshot

**Document**: `docs/FINAL_HARDENING_BASELINE.md`  
**Problem Statement**: SIH26228 — Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines  
**Timestamp**: 2026-09-30T16:06:55+05:30  
**Audit Role**: Senior Principal Engineer & SIH Evaluation Jury Reviewer  

---

## 1. Baseline Git State

- **Current Branch**: `feature/tcvf-assurance-layer`
- **Current Commit (HEAD)**: `8f52258` (`docs(pitch): add SIH grand finale pitch deck, live demo playbook and judge qa`)
- **Safety Tag Created**: `ibvap-before-final-hardening` -> `8f52258`
- **Protected Immutable Baselines**:
  - `ibvap-preserved-base`: `25c05eba437058b07873ee9aba822ae173fdf1d2` (PROTECTED / FROZEN)
  - `ibvap-original-final`: `25c05eba437058b07873ee9aba822ae173fdf1d2` (PROTECTED / FROZEN)
- **Working Tree Status**: 100% Clean (0 modified, 0 untracked files).
- **Remote**: `origin https://github.com/bhupendersingh8/IBVAP_Final_Project.git`

---

## 2. Pre-Modification Test & Build Status

- **Python Environment**: `.venv_gpu` (Python 3.11.9, PyTorch 2.11.0+cu128, CUDA 12.8)
- **Pytest Suite (`pytest -q tests/`)**:
  - **Total Tests Executed**: 445
  - **Passed**: 443
  - **Failed**: 2 (both in `tests/test_cctv_discovery.py`: `test_check_tcp_port_local` and `test_scan_cctv_ports` due to offline environment where local MediaMTX RTSP server is not running on port 8554).
- **Frontend Build (`npm run build` in `apps/frontend`)**:
  - **Status**: PASSED (0 errors, 0 warnings, build completed in 3.53s, bundle: 586.66 kB).
- **Live Demo Runner (`python scripts/demo_tamper_assurance_cycle.py`)**:
  - **Status**: PASSED (Exit code 0, 6/6 stages completed in 2.8s).

---

## 3. Known Red Claims & Areas for Hardening

1. **Backdoor / Poisoning Scanner**: Must be formally qualified as empirical heuristic screening using prediction discrepancy and feature outliers; disclaim universal backdoor detection and Neural Cleanse trigger inversion.
2. **Post-Quantum Cryptography Wording**: Must refer to "dual cryptographic digest using SHA-256 and SHAKE-256"; clarify that SHAKE-256 is an extendable-output function from the SHA-3 family and does not confer post-quantum security to the entire platform.
3. **Model Authenticity vs. Safety (Ed25519)**: Clarify that Ed25519 signature guarantees manifest integrity and contributor identity, but does NOT guarantee the model is non-malicious (an authorized contributor could submit a trojaned model, which is why behavioral fingerprinting is mandatory).
4. **Legal / Evidence Scope**: Replace all instances of "Section 65B Legal Certificate" or "court admissible" with "Cryptographically verifiable electronic-evidence certificate supporting forensic and audit workflows under the applicable electronic-record provisions of the Bharatiya Sakshya Adhiniyam, 2023, including Section 63".
5. **NIST / ISO Compliance**: Use "Informed by NIST AI RMF trustworthiness principles" and "Conceptually mapped to AI governance principles; no certification claim".
6. **MediaMTX Port 8554 Isolation**: Make `test_cctv_discovery.py` deterministic by providing an automatic mock/fixture when MediaMTX is offline, reaching 0 test failures.
7. **Dataset Documentation**: Provide comprehensive `datasets/README.md` with explicit licenses, sources, and checksums.

---

## 4. Planned Hardening Sequence

1. `docs/FINAL_FORENSIC_AUDIT.md` (Complete repository audit across 32 security and engineering dimensions).
2. `docs/ARCHITECTURE_TRUTH_MAP.md` (Frontend / Backend / ML / Storage / Communication boundaries).
3. `docs/AI_CHANGE_FORENSIC_REPORT.md` (Safety checks for hidden calls, eval/exec, tokens, and serialization).
4. `docs/CLAIM_EVIDENCE_MATRIX.md` (GREEN / YELLOW / RED claim classification).
5. Code & doc hardening (Red claims correction, MediaMTX test fixture, legal terminology updates).
6. Security & Dependency audits (`docs/SECURITY_AUDIT_FINAL.md`, `docs/SUPPLY_CHAIN_AUDIT.md`).
7. Controlled reports generation (backdoor, distribution shift, one-bit substitution, benchmark).
8. Final end-to-end test execution & `FINAL_STATUS.md`.
