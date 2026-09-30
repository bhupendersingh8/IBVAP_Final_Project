# IBVAP Test Datasets & Open-Source Benchmark Sources

**Directory**: `datasets/`  
**Problem Statement**: SIH26228 — Trustworthy Computer Vision Integrity Assurance for Data, Models and Inference Outputs in Multi-Contributor Pipelines  
**Governance**: Open-Source / Academic Defense Datasets Only (Zero Copyrighted / Proprietary Data)  

---

## 1. Supported Reference Datasets

IBVAP integrates and supports 3 primary open-source computer-vision benchmark datasets specifically selected for border surveillance, low-light visibility, and environmental fog conditions:

### 1. ExDark (Exclusively Dark Image Dataset)
- **Official Repository**: `https://github.com/cs-chan/Exclusively-Dark-Image-Dataset.git`
- **License**: Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Intended Purpose**: Evaluation of low-light detection, Zero-DCE++ photometric restoration, and extreme underexposure robustness.
- **Classes (12)**: Bicycle, Boat, Bottle, Bus, Car, Cat, Chair, Cup, Dog, Motorbike, People, Table.
- **Sample Count**: 7,363 low-light images across 10 low-light conditions.
- **Why Selected**: Simulates night-time border patrol and low-lux outpost camera feeds without infrared illumination.
- **Limitations**: Visible RGB spectrum only; does not provide thermal infrared pairing.

### 2. LLVIP (Visible-Infrared Paired Dataset for Low-Light Surveillance)
- **Official Repository**: `https://github.com/bupt-ai-cz/LLVIP.git`
- **License**: Academic Research Use Only (Non-Commercial)
- **Intended Purpose**: Evaluation of multi-modal bimodal surveillance, cross-spectral alignment, and camouflage detection.
- **Classes**: Person (Pedestrian detection under dark conditions).
- **Sample Count**: 30,976 strictly aligned visible RGB and long-wave infrared (LWIR) image pairs.
- **Why Selected**: Directly mimics Sashastra Seema Bal (SSB) day/night thermal camera checkposts.
- **Limitations**: Fixed camera viewpoints (surveillance poles); limited vehicular diversity.

### 3. RESIDE-RTTS (Real-World Task-Driven Testing Set for Haze & Fog)
- **Official Source**: `https://github.com/Boyiliee/RESIDE-dataset-link.git`
- **License**: Research & Educational Use
- **Intended Purpose**: Assessment of atmospheric scattering, fog degradation, and CLAHE contrast restoration.
- **Classes (5)**: Person, Bicycle, Car, Bus, Motorbike.
- **Sample Count**: 4,322 real-world outdoor hazy images.
- **Why Selected**: Simulates riverine and mountain fog along border perimeters.
- **Limitations**: Variable camera resolutions and uncontrolled real-world haze densities.

---

## 2. Ingestion & Preprocessing Guidelines
- **YOLO Format**: All annotations must be converted or validated in YOLO normalized coordinates: `<class_id> <x_center> <y_center> <width> <height>` where all values $\in [0.0, 1.0]$.
- **Data Integrity Assurance**: Before any dataset is enrolled into the pipeline, `services/assurance/data_integrity.py` validates:
  1. Exact duplicates via SHA-256 byte hashing.
  2. Near-duplicates via 64-bit Average Hash (`aHash-64`) with Hamming distance threshold $\le 10$.
  3. Bounding box syntax (aspect ratio $\le 10:1$, bounding box collision IoU $\le 0.85$, non-negative area).
  4. Label discrepancy screening using Confident Learning prediction discrepancy thresholds ($p > 0.70, \text{IoU} > 0.50, \hat{y} \neq y$).

---

## 3. Automated Setup Script
To download or verify test datasets from official open repositories:
```powershell
python download_weights_and_datasets.py --print-datasets
```
*Note: Large raw image archives are excluded from Git via `.gitignore` to maintain clean repository hygiene.*
