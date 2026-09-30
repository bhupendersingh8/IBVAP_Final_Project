"""
IBVAP Tactical Knowledge Base
Comprehensive domain knowledge covering:
1. Border Security Force (BSF) & Defense Tactical SOPs
2. Threat Assessment, Perimeter Escalation, and Triage Matrices
3. Computer Vision, YOLOv8, ByteTrack, TensorRT, and Edge Acceleration
4. Autonomous Border Outpost (BOP) Surveillance Operations
"""

TACTICAL_SOPS = {
    "night_intrusion": {
        "title": "Standard Operating Procedure: Night Perimeter Breach & Intrusion",
        "category": "Perimeter Security",
        "urgency": "CRITICAL",
        "steps": [
            "1. **Instant Sensor Cross-Verification**: Correlate YOLO person detection with thermal/infrared and PIR motion sensors to rule out false triggers (wildlife, swaying vegetation).",
            "2. **Zone Illumination & PTZ Slew-to-Cue**: Automatically slew PTZ floodlights and high-zoom thermal camera to coordinates of intrusion.",
            "3. **Audio Deterrent & Alarm Trigger**: Sound directional acoustic deterrent (110dB hooters) at breach sector; notify Quick Reaction Team (QRT).",
            "4. **Deploy QRT Cord-and-Search**: Deploy 4-man QRT section in tactical formation to seal secondary boundary gates.",
            "5. **Escalate to Battalion HQ**: Dispatch automated digital SITREP with timestamped evidence snapshot and GPS sector coordinates."
        ]
    },
    "drone_uav": {
        "title": "Standard Operating Procedure: Low-Altitude Drone / UAV Intrusion",
        "category": "Aerial Defense",
        "urgency": "CRITICAL",
        "steps": [
            "1. **Detection & Vector Tracking**: Lock optical tracking onto UAV flight path; estimate altitude (<100m AGL indicates payload drop).",
            "2. **Electronic Countermeasure (RF Jamming)**: Activate directional anti-drone RF jammer covering 2.4 GHz, 5.8 GHz, and GNSS L1/L2 bands.",
            "3. **Payload Drop Site Mark**: Record GPS coordinates of any dropped object (narcotics, weapons, ammunition).",
            "4. **Ground Patrol Mobilization**: Vector closest mobile patrol to intercept drop zone; establish 500m security perimeter.",
            "5. **Blackout Protocol**: Dim surface lighting at BOP to prevent adversary camera recon."
        ]
    },
    "fence_tampering": {
        "title": "Standard Operating Procedure: Anti-Cut Fence & Border Wall Tampering",
        "category": "Physical Barrier Integrity",
        "urgency": "HIGH",
        "steps": [
            "1. **Vibration / Tension Sensor Check**: Verify taut-wire or fiber-optic fence vibration alarms alongside video analytics.",
            "2. **Multi-Camera Handover**: Verify whether intruder is crawling, cutting wire, or placing ladder across fence.",
            "3. **Direct QRT Interception**: Direct armed patrol to point-of-breach within 120 seconds.",
            "4. **Evidence Preservation**: Tag forensic video clip with cryptographic SHA-256 hash for judicial evidence."
        ]
    },
    "vehicle_anpr_checkpoint": {
        "title": "Standard Operating Procedure: ANPR Checkpoint & Vehicle Watchlist Alert",
        "category": "Vehicle & Access Control",
        "urgency": "HIGH",
        "steps": [
            "1. **Watchlist Plate Match**: Automated lookup against National Crime Records / Stolen Vehicle / Watchlist DB.",
            "2. **Hydraulic Barrier Deployment**: Deploy automated tire-shredding spike strips and bollards at BOP exit gate.",
            "3. **Driver Isolation & Verification**: Direct vehicle into secondary inspection bay; verify biometric and vehicular RC.",
            "4. **Under-Vehicle Surveillance (UVIS)**: Scan vehicle undercarriage for concealed compartments or magnetic IED attachments."
        ]
    },
    "tunneling_subterranean": {
        "title": "Standard Operating Procedure: Subterranean Tunneling Detection",
        "category": "Subterranean Defense",
        "urgency": "CRITICAL",
        "steps": [
            "1. **Seismic / Acoustic Geophone Array**: Monitor low-frequency acoustic vibrations (10Hz - 80Hz) indicative of manual or machine digging.",
            "2. **Ground Penetrating Radar (GPR)**: Conduct weekly GPR scan along 100m border buffer zone.",
            "3. **Soil Subsidence Inspection**: Inspect surface drainage dips, unusual freshly dug soil mounds, or hollow acoustic feedback."
        ]
    }
}

CV_AI_KNOWLEDGE = {
    "yolov8": {
        "title": "YOLOv8 Real-Time Object Detection Architecture",
        "details": (
            "YOLOv8 is an anchor-free single-stage object detector designed by Ultralytics. "
            "Key architectural improvements include: "
            "1) C2f (Cross-Stage Partial with 2 convolutions) module replacing C3 for richer gradient flow; "
            "2) Decoupled head separating classification and bounding box regression tasks; "
            "3) Task-Aligned Assigner for optimal positive sample assignment; "
            "4) DFL (Distribution Focal Loss) and CIoU loss for pinpoint bounding box regression."
        )
    },
    "bytetrack": {
        "title": "ByteTrack Multi-Object Tracking (MOT)",
        "details": (
            "ByteTrack associates detections with tracklets using both high-confidence and low-confidence boxes: "
            "1) First association matches high-score detections (e.g. conf >= 0.5) to existing tracklets using Kalman filter predictions and IoU distance; "
            "2) Second association matches remaining unmatched tracklets with low-score detections (e.g. 0.1 <= conf < 0.5) to recover partially occluded targets; "
            "3) Drastically reduces ID switches under heavy occlusion and motion blur at border fence gates."
        )
    },
    "tensorrt": {
        "title": "NVIDIA TensorRT GPU Acceleration & FP16 Precision",
        "details": (
            "NVIDIA TensorRT optimizes neural network inference for NVIDIA GPUs: "
            "1) Layer and Tensor Fusion: Fuses multiple layers (Conv + Bias + ReLU) into single CUDA kernels; "
            "2) FP16 Reduced Precision: Executes operations using native FP16 Tensor Cores on RTX 3050 (Compute 8.6), doubling throughput with zero noticeable accuracy degradation; "
            "3) Kernel Auto-Tuning: Benchmarks diverse CUDA kernels during engine build to select the fastest hardware execution path."
        )
    },
    "seqlock_buffer": {
        "title": "Atomic Seqlock Shared Memory Frame Buffer",
        "details": (
            "IBVAP's zero-copy Seqlock shared memory architecture provides concurrent frame streaming between Python inference processes and FastAPI HTTP endpoints: "
            "1) Sequence Lock (Seqlock): Writers increment a monotonic sequence counter before and after memory copy; "
            "2) Readers verify sequence parity and consistency, preventing torn or partially written frames without heavy mutex locks; "
            "3) Zero Disk I/O: Video frames are streamed entirely from shared RAM, eliminating SSD wear and IOPS bottlenecks."
        )
    }
}

TACTICAL_FAQ = {
    "threat_levels": (
        "**IBVAP Threat Level Hierarchy**:\n"
        "- 🟢 **GREEN (Normal)**: All sectors clear, camera feeds nominal, no restricted zone intrusions.\n"
        "- 🟡 **YELLOW (Elevated)**: Loitering near perimeter boundary, unrecognized vehicle at checkpoint, or single camera degradation.\n"
        "- 🟠 **ORANGE (High)**: Confirmed restricted zone intrusion, wire approach within 5 meters, or watchlist ANPR hit.\n"
        "- 🔴 **RED (Critical)**: Active physical fence breach, weapon/contraband detected, multiple coordinated intrusions, or low-altitude drone penetration."
    ),
    "camera_specs": (
        "**Border Outpost Camera Layout**:\n"
        "- **CAM-01**: Perimeter North Gate — High-definition RTSP stream (1080p@30fps), restricted zone intrusion detection, automated PTZ tracker.\n"
        "- **CAM-02**: Perimeter North Fence — Long-range optical/thermal sensor, fence approach detection.\n"
        "- **WEBCAM-01**: Mobile Command / Laptop Optical Adapter — Direct USB video adapter for local tactical operation.\n"
        "- **PHONE-CAM-01**: Android/iOS Mobile Tactical Streamer — Wi-Fi/4G field patrol camera (IP Webcam / DroidCam)."
    ),
    "system_specs": (
        "**Edge Station Hardware Specs**:\n"
        "- **GPU**: NVIDIA GeForce RTX 3050 Laptop GPU (4 GB VRAM, Compute 8.6, Ampere architecture)\n"
        "- **CUDA & Runtime**: CUDA 12.1 + PyTorch 2.5.1 + TensorRT 11.2.1.2\n"
        "- **Inference Speed**: ~105 FPS (TensorRT FP16 pure engine) / ~40 FPS (End-to-End full pipeline)\n"
        "- **Autonomy**: 100% Offline-Capable, Air-Gapped, Zero Mandatory Cloud Dependence."
    )
}
