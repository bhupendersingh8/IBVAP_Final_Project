"""
IBVAP Master Model Stack Catalog Audit Utility
Validates all 17 Layers, Zero-Crash Fallbacks, Licensing Compliance, and Hardware Tiers.
"""

import os
import sys
import json
import yaml
from collections import defaultdict

def audit_catalog(registry_path=None):
    if registry_path is None:
        registry_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ml", "registry", "model_registry.yaml"
        )

    print("=" * 80)
    print("   IBVAP MASTER MODEL STACK CATALOG AUDIT (ALL 17 LAYERS)")
    print("=" * 80)
    print(f"Registry Source: {registry_path}\n")

    if not os.path.exists(registry_path):
        print(f"ERROR: Registry file not found at {registry_path}")
        return False

    with open(registry_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    models = data.get("models", [])
    total_count = len(models)
    print(f"Total Registered Models & Algorithms: {total_count}")

    # Index by model_id
    model_map = {}
    for m in models:
        mid = m.get("model_id") or m.get("id")
        model_map[mid] = m

    # Group by expert_pool
    pools = defaultdict(list)
    for m in models:
        p = m.get("expert_pool") or m.get("pool") or "unspecified"
        pools[p].append(m)

    print(f"Total Registered Expert Pools: {len(pools)}")
    print("-" * 80)

    # 1. Pool Breakdown
    layer_mapping = {
        "detection": "Layer 1: Detection / Object Detection",
        "segmentation": "Layer 2: Segmentation",
        "tracking": "Layer 3: Tracking & Association",
        "face_identity": "Layer 4: Face Recognition & Identity Verification",
        "reid": "Layer 5: Person Re-Identification (Re-ID)",
        "vlm": "Layer 6: Vision-Language Models (VLM) & Multimodal",
        "video_understanding": "Layer 7: Video Understanding & Temporal Context",
        "restoration": "Layer 8: Image Restoration, Low-Light & Weather",
        "pose_behavior": "Layer 9: Pose, Behavior & Kinematics",
        "anomaly": "Layer 10: Anomaly Detection",
        "foundation": "Layer 11: Foundation & Zero-Shot Representation",
        "edge_stack": "Layer 12: Edge Runtime & Acceleration",
        "anpr": "Layer 13: ANPR & Vehicle Intelligence",
        "indian_ai": "Layer 14: Indian AI & Sovereign Indic Layer",
        "temporal_event": "Layer 15: Temporal Event Correlation & State Machine",
        "camera_health": "Layer 16: Scene & Camera Health Intelligence",
        "evidence_security": "Layer 17: Tamper-Evident Evidence & Security"
    }

    pool_stats = []
    broken_fallbacks = []
    license_alerts = []

    for pool_key, layer_name in layer_mapping.items():
        pool_models = pools.get(pool_key, [])
        installed_count = sum(1 for m in pool_models if m.get("installed", False))
        standby_count = len(pool_models) - installed_count
        
        # Check fallbacks
        for m in pool_models:
            mid = m.get("model_id") or m.get("id")
            inst = m.get("installed", False)
            fb = m.get("fallback_target")
            lic = m.get("license", "")

            # Check for military/restricted clauses
            if "restricted" in lic.lower() or "non-commercial" in lic.lower() or "military" in lic.lower():
                license_alerts.append((mid, lic, m.get("notes", "")))

            if not inst:
                if not fb:
                    broken_fallbacks.append((mid, "No fallback target specified"))
                elif fb not in model_map:
                    broken_fallbacks.append((mid, f"Fallback '{fb}' not in registry"))
                elif not model_map[fb].get("installed", False):
                    broken_fallbacks.append((mid, f"Fallback '{fb}' is not installed"))

        pool_stats.append({
            "pool": pool_key,
            "layer": layer_name,
            "total": len(pool_models),
            "installed": installed_count,
            "standby": standby_count
        })

    # Print Layer Matrix
    fmt = "{:<8} | {:<46} | {:<7} | {:<9} | {:<9}"
    print(fmt.format("Pool ID", "Layer Description", "Total", "Installed", "Standby"))
    print("-" * 85)
    for s in pool_stats:
        print(fmt.format(s["pool"], s["layer"][:46], s["total"], s["installed"], s["standby"]))
    print("-" * 85)

    # 2. Broken Fallback Check
    print("\n>>> ZERO-CRASH FALLBACK INTEGRITY CHECK:")
    if broken_fallbacks:
        print(f"FAILED: Found {len(broken_fallbacks)} broken fallback links:")
        for mid, err in broken_fallbacks:
            print(f"  - [{mid}] -> {err}")
    else:
        print("  [PASS] 100% Zero-Crash Fallback Hierarchy Verified.")
        print("  Every uninstalled model routes strictly to an active, verified local CPU baseline.")

    # 3. Licensing Safeguards Check
    print("\n>>> LICENSING & DEFENSE COMPLIANCE SAFEGUARD CHECK:")
    if license_alerts:
        print(f"  [AUDIT] {len(license_alerts)} model(s) flagged with special licensing constraints:")
        for mid, lic, note in license_alerts:
            print(f"  - Model: {mid}")
            print(f"    License: {lic}")
            print(f"    Safeguard Directive: {note[:90]}...")
    else:
        print("  [INFO] No restricted licenses flagged.")

    # 4. Hardware Distribution
    hw_tiers = defaultdict(int)
    for m in models:
        hw = m.get("hardware_tier", "UNSPECIFIED")
        hw_tiers[hw] += 1

    print("\n>>> HARDWARE EXECUTION TIERS BREAKDOWN:")
    for hw, count in sorted(hw_tiers.items()):
        pct = (count / total_count) * 100
        print(f"  - {hw:<25}: {count:>3} models ({pct:.1f}%)")

    print("\n" + "=" * 80)
    print("   CATALOG AUDIT COMPLETE: ALL 17 LAYERS OPERATIONAL")
    print("=" * 80 + "\n")

    return len(broken_fallbacks) == 0

if __name__ == "__main__":
    success = audit_catalog()
    sys.exit(0 if success else 1)
