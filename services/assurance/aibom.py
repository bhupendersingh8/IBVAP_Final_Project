"""
services/assurance/aibom.py
===========================
TCVIAF / SIH26228 CycloneDX 1.5-Compatible AIBOM (AI Software Bill of Materials) Generator.

Provides an offline, machine-readable AI supply-chain bill of materials:
1. CycloneDX 1.5 Spec Compliance (bomFormat="CycloneDX", specVersion="1.5")
2. Machine-Learning Model Component Representation (type="machine-learning-model")
3. Multi-Hash Checkpoint Binding (SHA-256)
4. Contributor Supplier Attribution & Contact Metadata
5. IBVAP Behavioral Fingerprint & Preprocessing Property Extensions
6. Cryptographic Manifest ↔ AIBOM Integrity Binding & Cross-Verification

Disclaimer:
The generated document follows CycloneDX 1.5 schema conventions for AI models.
It does not claim external third-party proprietary certification.
"""
from __future__ import annotations

import json
import uuid
from typing import Dict, Any, Optional, Tuple, List, Union
from datetime import datetime, timezone


def generate_cyclonedx_aibom(
    manifest_dict: Dict[str, Any],
    serial_number: Optional[str] = None,
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates a CycloneDX 1.5-compatible AIBOM JSON document from a signed ContributorModelManifest.
    """
    contributor = manifest_dict.get("contributor", {})
    model = manifest_dict.get("model", {})
    prep = manifest_dict.get("preprocessing", {})
    fp = manifest_dict.get("behavioral_fingerprint", {})
    sig = manifest_dict.get("signature", {})

    manifest_id = manifest_dict.get("manifest_id", f"man-{uuid.uuid4().hex[:16]}")
    model_id = model.get("model_id", "unknown_model")
    model_sha256 = model.get("sha256", "").lower()
    prep_hash = prep.get("config_hash", "").lower()
    fp_digest = fp.get("digest", "UNAVAILABLE")
    fp_profile = fp.get("profile_id", "ibvap-behavior-v1")
    param_count = model.get("parameter_count")

    s_num = serial_number or f"urn:uuid:{uuid.uuid4()}"
    ts = timestamp or datetime.now(timezone.utc).isoformat()

    # Model component properties documenting IBVAP-specific assurance extensions
    properties = [
        {"name": "ibvap:manifest_id", "value": str(manifest_id)},
        {"name": "ibvap:model_id", "value": str(model_id)},
        {"name": "ibvap:architecture", "value": str(model.get("architecture", "generic_cv"))},
        {"name": "ibvap:format", "value": str(model.get("format", "PyTorch"))},
        {"name": "ibvap:file_name", "value": str(model.get("file_name", "weights.pt"))},
        {"name": "ibvap:parameter_count", "value": str(param_count) if param_count is not None else "null"},
        {"name": "ibvap:preprocessing_config_sha256", "value": str(prep_hash)},
        {"name": "ibvap:behavioral_fingerprint_id", "value": str(fp_profile)},
        {"name": "ibvap:behavioral_fingerprint_sha256", "value": str(fp_digest)},
        {"name": "ibvap:contributor_id", "value": str(contributor.get("id", "unknown"))},
        {"name": "ibvap:contributor_org", "value": str(contributor.get("organization", "unknown"))},
        {"name": "ibvap:signature_algorithm", "value": str(sig.get("algorithm", "Ed25519"))},
        {"name": "ibvap:signature_public_key", "value": str(sig.get("public_key", ""))}
    ]

    model_component = {
        "type": "machine-learning-model",
        "bom-ref": f"model-{model_id}",
        "name": model_id,
        "version": "1.0",
        "description": f"Edge Computer Vision model {model_id} enrolled in IBVAP defense surveillance pipeline.",
        "hashes": [
            {
                "alg": "SHA-256",
                "content": model_sha256
            }
        ],
        "supplier": {
            "name": contributor.get("organization", "Unknown Organization"),
            "contact": [
                {
                    "name": contributor.get("name", "Unknown Contributor"),
                    "email": f"{contributor.get('id', 'developer')}@ibvap.internal"
                }
            ]
        },
        "properties": properties
    }

    # CycloneDX 1.5 Top-level structure
    aibom_document: Dict[str, Any] = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": s_num,
        "version": 1,
        "metadata": {
            "timestamp": ts,
            "tools": [
                {
                    "vendor": "IBVAP / TCVIAF",
                    "name": "ibvap-cyclonedx-aibom-generator",
                    "version": "1.0.0"
                }
            ],
            "component": {
                "type": "application",
                "bom-ref": "ibvap-core-pipeline",
                "name": "IBVAP Tactical Surveillance Pipeline",
                "version": "1.0.0",
                "description": "Smart India Hackathon SIH26228 Trustworthy Computer Vision Pipeline"
            },
            "manufacture": {
                "name": contributor.get("organization", "Unknown Contributor Organization")
            }
        },
        "components": [
            model_component
        ],
        "dependencies": [
            {
                "ref": "ibvap-core-pipeline",
                "dependsOn": [
                    f"model-{model_id}"
                ]
            }
        ]
    }

    return aibom_document


# ---------------------------------------------------------------------------
# Integrity Verification: Manifest ↔ AIBOM Cross-Binding
# ---------------------------------------------------------------------------

def extract_model_component(aibom_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extracts the machine-learning-model component from a CycloneDX AIBOM.
    """
    components = aibom_dict.get("components", [])
    for comp in components:
        if comp.get("type") in ("machine-learning-model", "file", "library"):
            return comp
    return components[0] if components else None


def extract_property_value(component: Dict[str, Any], prop_name: str) -> Optional[str]:
    """
    Retrieves the value of a specific named property from a CycloneDX component.
    """
    for prop in component.get("properties", []):
        if prop.get("name") == prop_name:
            return prop.get("value")
    return None


def verify_manifest_aibom_binding(
    manifest_dict: Dict[str, Any],
    aibom_dict: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Verifies that a CycloneDX AIBOM is cryptographically and structurally bound
    to the given ContributorModelManifest.
    Checks:
    1. AIBOM specVersion is '1.5' and bomFormat is 'CycloneDX'
    2. Model component SHA-256 matches manifest.model.sha256
    3. Manifest ID property matches manifest.manifest_id
    4. Preprocessing property matches manifest.preprocessing.config_hash
    5. Behavioral fingerprint property matches manifest.behavioral_fingerprint.digest (if available)
    6. Contributor ID property matches manifest.contributor.id
    """
    failures: List[str] = []

    # 1. Spec compliance check
    if aibom_dict.get("bomFormat") != "CycloneDX":
        failures.append(f"AIBOM bomFormat mismatch: expected 'CycloneDX', got '{aibom_dict.get('bomFormat')}'")

    if aibom_dict.get("specVersion") != "1.5":
        failures.append(f"AIBOM specVersion mismatch: expected '1.5', got '{aibom_dict.get('specVersion')}'")

    comp = extract_model_component(aibom_dict)
    if not comp:
        failures.append("AIBOM does not contain any components")
        return False, failures

    # 2. Model Checkpoint SHA-256 match
    manifest_model_sha = manifest_dict.get("model", {}).get("sha256", "").lower()
    hashes = comp.get("hashes", [])
    aibom_model_sha = ""
    for h in hashes:
        if h.get("alg") == "SHA-256":
            aibom_model_sha = h.get("content", "").lower()
            break

    if not aibom_model_sha:
        failures.append("AIBOM model component is missing SHA-256 hash entry")
    elif aibom_model_sha != manifest_model_sha:
        failures.append(
            f"Model SHA-256 binding mismatch: manifest specifies '{manifest_model_sha[:16]}...', "
            f"but AIBOM component specifies '{aibom_model_sha[:16]}...'"
        )

    # 3. Manifest ID binding
    manifest_id = manifest_dict.get("manifest_id")
    aibom_manifest_id = extract_property_value(comp, "ibvap:manifest_id")
    if aibom_manifest_id != manifest_id:
        failures.append(
            f"Manifest ID property mismatch: manifest has '{manifest_id}', AIBOM has '{aibom_manifest_id}'"
        )

    # 4. Preprocessing Config Digest binding
    manifest_prep_hash = manifest_dict.get("preprocessing", {}).get("config_hash", "").lower()
    aibom_prep_hash = (extract_property_value(comp, "ibvap:preprocessing_config_sha256") or "").lower()
    if aibom_prep_hash != manifest_prep_hash:
        failures.append(
            f"Preprocessing config digest mismatch: manifest has '{manifest_prep_hash[:16]}...', "
            f"AIBOM has '{aibom_prep_hash[:16]}...'"
        )

    # 5. Behavioral Fingerprint Digest binding
    manifest_fp_digest = manifest_dict.get("behavioral_fingerprint", {}).get("digest", "")
    aibom_fp_digest = extract_property_value(comp, "ibvap:behavioral_fingerprint_sha256") or ""
    if manifest_fp_digest and manifest_fp_digest != "UNAVAILABLE":
        if aibom_fp_digest.lower() != manifest_fp_digest.lower():
            failures.append(
                f"Behavioral fingerprint digest mismatch: manifest has '{manifest_fp_digest[:16]}...', "
                f"AIBOM has '{aibom_fp_digest[:16]}...'"
            )

    # 6. Contributor ID binding
    manifest_contrib_id = manifest_dict.get("contributor", {}).get("id")
    aibom_contrib_id = extract_property_value(comp, "ibvap:contributor_id")
    if aibom_contrib_id != manifest_contrib_id:
        failures.append(
            f"Contributor ID mismatch: manifest has '{manifest_contrib_id}', AIBOM has '{aibom_contrib_id}'"
        )

    return (len(failures) == 0), failures
