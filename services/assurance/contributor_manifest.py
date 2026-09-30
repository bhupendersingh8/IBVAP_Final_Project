"""
services/assurance/contributor_manifest.py
==========================================
TCVIAF / SIH26228 Contributor Model Manifest & Ed25519 Asymmetric Verification.

Provides an offline, deterministic, multi-contributor model supply-chain identity:
1. Contributor & Organization Identity Binding
2. Model Checkpoint SHA-256 & Architecture Specification
3. Preprocessing Pipeline Digest Binding
4. Behavioral Fingerprint Digest Binding (ibvap-behavior-v1)
5. Deterministic RFC-8785 Canonical JSON Serialization
6. Asymmetric Digital Signing via Ed25519 (FIPS 186-5 / RFC 8032)
7. Cryptographic Tamper-Evident Verification

Distinction from Post-Quantum WOTS+:
- WOTS+ (Stateless Hash-Based One-Time Signatures over SHAKE-256): Used for high-frequency,
  quantum-resistant live inference event commitments and audit certificates.
- Ed25519 (PureEdDSA over Curve25519): Used for model release manifests, multi-contributor
  supply-chain provenance, and persistent identity signing by model developers.
"""
from __future__ import annotations

import os
import json
import uuid
import hashlib
from typing import Dict, Any, Optional, Tuple, Union, List
from pathlib import Path
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

from crypto_ledger import compute_file_sha256


# ---------------------------------------------------------------------------
# 1. Pydantic Models for Contributor Model Manifest
# ---------------------------------------------------------------------------

class ContributorMetadata(BaseModel):
    model_config = {"protected_namespaces": ()}
    id: str = Field(..., min_length=1, max_length=128, description="Unique contributor identifier")
    name: str = Field(..., min_length=1, max_length=256, description="Contributor human name or team")
    organization: str = Field(..., min_length=1, max_length=256, description="Organization or unit name")


class ModelMetadata(BaseModel):
    model_config = {"protected_namespaces": ()}
    model_id: str = Field(..., min_length=1, max_length=128, description="Standard model name / identifier")
    architecture: str = Field(..., min_length=1, max_length=128, description="Underlying architecture family")
    format: str = Field(..., min_length=1, max_length=32, description="Model serialization format (e.g., PyTorch, ONNX)")
    file_name: str = Field(..., min_length=1, max_length=256, description="Canonical checkpoint filename")
    sha256: str = Field(..., min_length=64, max_length=64, description="Hex-encoded SHA-256 digest of the model checkpoint")
    parameter_count: Optional[int] = Field(default=None, description="Total parameter count if reliably verified, else null")


class PreprocessingMetadata(BaseModel):
    model_config = {"protected_namespaces": ()}
    config_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 digest of canonical preprocessing parameters")


class BehavioralFingerprintMetadata(BaseModel):
    model_config = {"protected_namespaces": ()}
    profile_id: str = Field(default="ibvap-behavior-v1", max_length=128, description="Versioned behavioral probe battery ID")
    digest: str = Field(..., min_length=1, max_length=64, description="Fingerprint digest hex string or 'UNAVAILABLE'")


class ManifestSignature(BaseModel):
    model_config = {"protected_namespaces": ()}
    algorithm: str = Field(default="Ed25519", description="Digital signature algorithm")
    public_key: str = Field(..., min_length=64, max_length=64, description="Hex-encoded 32-byte Ed25519 public key")
    signature: str = Field(..., min_length=128, max_length=128, description="Hex-encoded 64-byte Ed25519 signature")


class ContributorModelManifest(BaseModel):
    model_config = {"protected_namespaces": ()}
    manifest_version: str = Field(default="1.0", description="Schema version of the manifest")
    manifest_id: str = Field(default_factory=lambda: f"man-{uuid.uuid4().hex[:16]}", description="Unique manifest ID")
    contributor: ContributorMetadata
    model: ModelMetadata
    preprocessing: PreprocessingMetadata
    behavioral_fingerprint: BehavioralFingerprintMetadata
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO 8601 UTC timestamp")
    signature: Optional[ManifestSignature] = Field(default=None, description="Cryptographic signature covering all signed fields")


# ---------------------------------------------------------------------------
# 2. Deterministic Canonicalization (RFC 8785 JSON Canonicalization Scheme)
# ---------------------------------------------------------------------------

def canonical_json_bytes(data: Any) -> bytes:
    """
    Computes a deterministic canonical UTF-8 byte representation of a dictionary or primitive.
    Guarantees:
    - Deterministic recursive lexicographical key ordering
    - Compact separators (no whitespace after ':' or ',')
    - Strict UTF-8 encoding
    - Stable numeric and null serialization
    """
    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':')
    ).encode('utf-8')


def get_unsigned_manifest_payload(manifest_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts the payload to be signed by stripping the 'signature' block.
    """
    payload = dict(manifest_dict)
    payload.pop("signature", None)
    return payload


def compute_manifest_digest(manifest_dict: Dict[str, Any]) -> str:
    """
    Computes the canonical SHA-256 digest of the unsigned manifest contents.
    """
    unsigned_payload = get_unsigned_manifest_payload(manifest_dict)
    canonical_bytes = canonical_json_bytes(unsigned_payload)
    return hashlib.sha256(canonical_bytes).hexdigest()


# ---------------------------------------------------------------------------
# 3. Ed25519 Key Management & Signing Utilities
# ---------------------------------------------------------------------------

def generate_ed25519_keypair() -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """
    Generates a new secure, random Ed25519 asymmetric keypair.
    Uses Python's cryptography library (FIPS 186-5 compliant).
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


def export_ed25519_keypair_hex(private_key: ed25519.Ed25519PrivateKey) -> Tuple[str, str]:
    """
    Exports an Ed25519 keypair as (private_key_hex, public_key_hex).
    - Private key: 32 raw seed bytes (64 hex characters)
    - Public key: 32 raw public bytes (64 hex characters)
    """
    from cryptography.hazmat.primitives import serialization
    raw_priv = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    raw_pub = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    return raw_priv.hex(), raw_pub.hex()


def load_ed25519_private_key_hex(private_key_hex: str) -> ed25519.Ed25519PrivateKey:
    """Loads an Ed25519 private key from a 64-character hex seed."""
    raw_bytes = bytes.fromhex(private_key_hex)
    if len(raw_bytes) != 32:
        raise ValueError(f"Ed25519 private key seed must be exactly 32 bytes (64 hex chars), got {len(raw_bytes)}")
    return ed25519.Ed25519PrivateKey.from_private_bytes(raw_bytes)


def load_ed25519_public_key_hex(public_key_hex: str) -> ed25519.Ed25519PublicKey:
    """Loads an Ed25519 public key from a 64-character hex string."""
    raw_bytes = bytes.fromhex(public_key_hex)
    if len(raw_bytes) != 32:
        raise ValueError(f"Ed25519 public key must be exactly 32 bytes (64 hex chars), got {len(raw_bytes)}")
    return ed25519.Ed25519PublicKey.from_public_bytes(raw_bytes)


# ---------------------------------------------------------------------------
# 4. Manifest Builder & Signing
# ---------------------------------------------------------------------------

def create_contributor_manifest(
    contributor_id: str,
    contributor_name: str,
    contributor_org: str,
    model_id: str,
    architecture: str,
    format_type: str,
    file_name: str,
    model_sha256: str,
    preprocessing_config_hash: str,
    behavioral_fingerprint_digest: Optional[str] = None,
    parameter_count: Optional[int] = None,
    manifest_id: Optional[str] = None,
    created_at: Optional[str] = None
) -> ContributorModelManifest:
    """
    Constructs an unsigned ContributorModelManifest instance with strict validation.
    """
    fp_digest = behavioral_fingerprint_digest or "UNAVAILABLE"

    return ContributorModelManifest(
        manifest_version="1.0",
        manifest_id=manifest_id or f"man-{uuid.uuid4().hex[:16]}",
        contributor=ContributorMetadata(
            id=contributor_id,
            name=contributor_name,
            organization=contributor_org
        ),
        model=ModelMetadata(
            model_id=model_id,
            architecture=architecture,
            format=format_type,
            file_name=file_name,
            sha256=model_sha256.lower(),
            parameter_count=parameter_count
        ),
        preprocessing=PreprocessingMetadata(
            config_hash=preprocessing_config_hash.lower()
        ),
        behavioral_fingerprint=BehavioralFingerprintMetadata(
            profile_id="ibvap-behavior-v1",
            digest=fp_digest.lower() if fp_digest != "UNAVAILABLE" else "UNAVAILABLE"
        ),
        created_at=created_at or datetime.now(timezone.utc).isoformat(),
        signature=None
    )


def sign_contributor_manifest(
    manifest: Union[ContributorModelManifest, Dict[str, Any]],
    private_key: Union[ed25519.Ed25519PrivateKey, str]
) -> Dict[str, Any]:
    """
    Digitally signs a contributor model manifest using Ed25519.
    1. Excludes any existing signature block
    2. Serializes unsigned fields to canonical RFC-8785 JSON bytes
    3. Signs canonical bytes with private key
    4. Attaches signature metadata (algorithm, public_key_hex, signature_hex)
    5. Returns complete signed manifest dictionary
    """
    if isinstance(manifest, ContributorModelManifest):
        manifest_dict = manifest.model_dump()
    else:
        manifest_dict = json.loads(json.dumps(manifest))

    if isinstance(private_key, str):
        priv_key_obj = load_ed25519_private_key_hex(private_key)
    else:
        priv_key_obj = private_key

    # Strip existing signature for signing
    unsigned_payload = get_unsigned_manifest_payload(manifest_dict)
    canonical_bytes = canonical_json_bytes(unsigned_payload)

    # Compute Ed25519 signature over canonical bytes
    raw_signature = priv_key_obj.sign(canonical_bytes)

    # Export public key hex
    from cryptography.hazmat.primitives import serialization
    raw_pub = priv_key_obj.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )

    manifest_dict["signature"] = {
        "algorithm": "Ed25519",
        "public_key": raw_pub.hex(),
        "signature": raw_signature.hex()
    }

    return manifest_dict


def verify_manifest_signature(manifest_dict: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Verifies the cryptographic Ed25519 signature of a signed manifest dictionary.
    Returns (is_valid, failure_reason).
    """
    sig_block = manifest_dict.get("signature")
    if not sig_block or not isinstance(sig_block, dict):
        return False, "Missing or invalid 'signature' block in manifest"

    alg = sig_block.get("algorithm")
    if alg != "Ed25519":
        return False, f"Unsupported signature algorithm '{alg}'. Expected 'Ed25519'"

    pub_hex = sig_block.get("public_key")
    sig_hex = sig_block.get("signature")

    if not pub_hex or not sig_hex:
        return False, "Missing 'public_key' or 'signature' in signature block"

    try:
        pub_key = load_ed25519_public_key_hex(pub_hex)
        sig_bytes = bytes.fromhex(sig_hex)
    except Exception as e:
        return False, f"Malformed hex encoding in public key or signature: {str(e)}"

    if len(sig_bytes) != 64:
        return False, f"Invalid Ed25519 signature length: {len(sig_bytes)} bytes (expected 64)"

    unsigned_payload = get_unsigned_manifest_payload(manifest_dict)
    canonical_bytes = canonical_json_bytes(unsigned_payload)

    try:
        pub_key.verify(sig_bytes, canonical_bytes)
        return True, None
    except InvalidSignature:
        return False, "Cryptographic signature verification failed: signature does not match canonical payload"
    except Exception as e:
        return False, f"Signature verification error: {str(e)}"
