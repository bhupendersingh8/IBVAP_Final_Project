# EDGE_DEPLOYMENT.md — Edge Hardware & Embedded Systems Architecture

> **Status: ARCHITECTURAL DESIGN (PLANNED)**
> Current execution validated on standard x86 CPU hardware. This specification defines embedded deployment parameters for remote border surveillance outposts.

---

## 1. Edge Target Devices

Border surveillance posts often operate in bandwidth-constrained, offline, and thermally severe environments. The primary target platforms are:

| Tier | Hardware | Compute Capability | Target Cameras | Power Consumption |
|---|---|---|---|---|
| **Tier 1 (High Density)** | NVIDIA Jetson AGX Orin (64GB) | 275 TOPS (INT8) | 8–16 1080p RTSP feeds | 15W–60W |
| **Tier 2 (Medium Post)** | NVIDIA Jetson Orin NX (16GB) | 100 TOPS (INT8) | 4–8 1080p RTSP feeds | 10W–25W |
| **Tier 3 (Minimal Post)** | Intel N100 / Core i3 Industrial PC | CPU Only (OpenVINO) | 1–2 720p RTSP feeds | 15W–35W |

---

## 2. Offline-First Topology

```
             ┌──────────────────────────────────────────────┐
             │       Border Outpost Edge Node               │
             │                                              │
IP Cameras ─►│ MediaMTX ─► GStreamer Decode ─► TensorRT/YOLO│
(Isolated    │                                       │      │
VLAN)        │                                       ▼      │
             │ Operator Console ◄── FastAPI ◄── Rule Engine │
             │ (Local React UI)      SQLite     Hash Ledger │
             └───────────────────────┬──────────────────────┘
                                     │ (Opportunistic Sync)
                                     ▼
                    Headquarters Central C2 Center
                    (Alerts, Digest, Chain Replication)
```

1. **Zero External Internet Requirement**: The entire stack (ingestion, AI inference, rule processing, alerting, dashboard) operates in a standalone, air-gapped local subnet.
2. **Local Cryptographic Ledger**: All incidents and evidence hashes are maintained in local SQLite, verifiable independently without reaching out to an external server.
3. **Opportunistic Synchronization**: When satellite or cellular backhaul is available, incident metadata and cryptographic ledger blocks are pushed to HQ via authenticated batched TLS transfers.

---

## 3. Power Management & Thermal Throttling

- **Adaptive Frame Skipping**: When temperature exceeds 75°C or battery backup triggers, the ingestion worker down-samples processing from 15 FPS to 5 FPS while maintaining persistent tracking.
- **Night-Vision Energy Mode**: Deactivates high-resolution secondary passes (ANPR) during hours where vehicle access roads are physically gated, focusing thermal/IR budget on person perimeter detection.

---

## 4. Verification Checklist for Physical Edge Units

- [x] Architecture supports single-node self-contained deployment.
- [x] Storage bounded by circular retention strategies.
- [ ] JetPack 6.x packaging and systemd service descriptors (Planned).
- [ ] Hardware watchdog integration for automatic cold reboot (Planned).
- [ ] Benchmarking under industrial thermal chamber (Planned).
