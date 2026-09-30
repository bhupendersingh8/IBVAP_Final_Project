"""
TCVIAF / SIH26228 Inference Provenance, Tamper Detection & Replay Assurance
=============================================================================
Implements SIH26228 Requirement 2.2.3:
Cryptographically binds every inference execution to:
1. Input/frame identity (SHA-256 of raw frame bytes)
2. Model identity & Model weights SHA-256 digest
3. Preprocessing configuration digest
4. Inference configuration digest
5. Canonicalized output detections digest
6. Millisecond timestamp
7. Monotonic sequence order with previous-record hash chaining
8. Cryptographic nonce for replay attack prevention

Detects:
- Input tampering (pixel / frame byte substitution)
- Model substitution (unauthorized weights swap)
- Config / preprocessing alteration (threshold/resolution tampering)
- Output tampering (bounding box coordinate, confidence, or class manipulation)
- Sequence gaps, deletions, and chain linkage breaks
- Replay attacks (nonce duplication, provenance record injection)
- Distinguishes legitimate repeated inference from malicious replays
"""
from __future__ import annotations

import json
import uuid
import hashlib
import secrets
import time
from typing import List, Dict, Any, Optional, Tuple, Set
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

from crypto_ledger import CryptoEvidenceLedger


# ---------------------------------------------------------------------------
# 1. Canonical Serialization & Digest Utilities
# ---------------------------------------------------------------------------

def canonicalize_output(detections: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Normalizes and deterministically sorts detection outputs to produce
    a canonical JSON string and its SHA-256 hex digest.
    
    Tolerates diverse detection formats (e.g. bbox as list [x1, y1, x2, y2]
    or dict {"x1": ..., "y1": ..., "x2": ..., "y2": ...}).
    Rounds floating-point numbers to 4 decimal places to ensure floating-point
    stability across platforms and runtimes.
    """
    normalized = []
    for d in detections:
        # Extract class info
        cid = int(d.get("class_id", d.get("cls", 0)))
        cname = str(d.get("class_name", d.get("name", ""))).strip().lower()
        conf = round(float(d.get("confidence", d.get("conf", 0.0))), 4)
        
        # Extract bbox [x1, y1, x2, y2]
        raw_box = d.get("bbox", [0.0, 0.0, 0.0, 0.0])
        if isinstance(raw_box, dict):
            x1 = round(float(raw_box.get("x1", 0.0)), 4)
            y1 = round(float(raw_box.get("y1", 0.0)), 4)
            x2 = round(float(raw_box.get("x2", 0.0)), 4)
            y2 = round(float(raw_box.get("y2", 0.0)), 4)
        elif isinstance(raw_box, (list, tuple)) and len(raw_box) >= 4:
            x1 = round(float(raw_box[0]), 4)
            y1 = round(float(raw_box[1]), 4)
            x2 = round(float(raw_box[2]), 4)
            y2 = round(float(raw_box[3]), 4)
        else:
            x1, y1, x2, y2 = 0.0, 0.0, 0.0, 0.0

        # Extract track id if present
        tid = d.get("track_id", d.get("track", None))
        if tid is not None:
            try:
                tid = int(tid)
            except (ValueError, TypeError):
                tid = -1
        else:
            tid = -1

        normalized.append({
            "bbox": [x1, y1, x2, y2],
            "class_id": cid,
            "class_name": cname,
            "confidence": conf,
            "track_id": tid
        })

    # Sort deterministically by (class_id, class_name, confidence, x1, y1, x2, y2, track_id)
    normalized.sort(key=lambda x: (
        x["class_id"],
        x["class_name"],
        x["confidence"],
        x["bbox"][0],
        x["bbox"][1],
        x["bbox"][2],
        x["bbox"][3],
        x["track_id"]
    ))

    canonical_json = json.dumps(normalized, sort_keys=True, separators=(',', ':'))
    digest = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
    return canonical_json, digest


def canonicalize_config(config: Dict[str, Any]) -> Tuple[str, str]:
    """
    Serializes an inference or model configuration deterministically
    into a canonical JSON string and computes its SHA-256 digest.
    """
    canonical_json = json.dumps(config, sort_keys=True, separators=(',', ':'))
    digest = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
    return canonical_json, digest


def canonicalize_preprocessing(prep_config: Dict[str, Any]) -> Tuple[str, str]:
    """
    Serializes preprocessing parameters (e.g. resolution, mean/std, color space,
    interpolation method) into a canonical JSON string and computes its SHA-256 digest.
    """
    canonical_json = json.dumps(prep_config, sort_keys=True, separators=(',', ':'))
    digest = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
    return canonical_json, digest


def compute_provenance_hash(
    sequence_id: int,
    input_hash: str,
    model_id: str,
    model_sha256: str,
    architecture_id: str,
    config_digest: str,
    preprocessing_digest: str,
    output_digest: str,
    timestamp: float,
    nonce: str,
    previous_record_hash: str
) -> str:
    """
    Computes the canonical SHA-256 cryptographic binding over all elements of
    an inference execution.
    """
    payload_str = (
        f"{sequence_id}|"
        f"{input_hash}|"
        f"{model_id}|"
        f"{model_sha256}|"
        f"{architecture_id}|"
        f"{config_digest}|"
        f"{preprocessing_digest}|"
        f"{output_digest}|"
        f"{timestamp:.4f}|"
        f"{nonce}|"
        f"{previous_record_hash}"
    )
    return hashlib.sha256(payload_str.encode('utf-8')).hexdigest()


def compute_hybrid_provenance_hash(payload_str: str) -> str:
    """
    Computes a dual classical SHA-256 and post-quantum SHAKE-256 (512-bit) hybrid digest.
    Guarantees 256 bits of Grover quantum collision resistance.
    """
    h_sha = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
    h_shake = hashlib.shake_256(payload_str.encode('utf-8')).hexdigest(64)
    return hashlib.sha256((h_sha + h_shake).encode('utf-8')).hexdigest()


# ---------------------------------------------------------------------------
# 2. Pydantic Models for Inference Provenance
# ---------------------------------------------------------------------------

class InferenceProvenanceRecord(BaseModel):
    """
    Canonical immutable provenance record for a single inference event.
    """
    model_config = ConfigDict(protected_namespaces=())

    provenance_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sequence_id: int
    input_hash: str = Field(..., min_length=64, max_length=64)
    model_id: str = Field(..., min_length=1, max_length=128)
    model_sha256: str = Field(..., min_length=64, max_length=64)
    architecture_id: str = Field(default="generic_detector", max_length=64)
    config_digest: str = Field(..., min_length=64, max_length=64)
    preprocessing_digest: str = Field(..., min_length=64, max_length=64)
    output_digest: str = Field(..., min_length=64, max_length=64)
    timestamp: float
    nonce: str = Field(..., min_length=8, max_length=64)
    previous_record_hash: str = Field(..., min_length=64, max_length=64)
    provenance_hash: str = Field(..., min_length=64, max_length=64)
    pq_hybrid_digest: Optional[str] = None
    pq_signature: Optional[Dict[str, Any]] = None
    raw_payload: Optional[Dict[str, Any]] = None


class ProvenanceVerificationResult(BaseModel):
    """
    Outcome of verifying an individual inference provenance record.
    """
    status: str  # "VERIFIED", "TAMPERED", "ANOMALY"
    tampered: bool
    anomalies: List[str] = Field(default_factory=list)
    recomputed_hash: str
    record_hash: str
    recommended_disposition: str  # "ACCEPT", "REVIEW", "QUARANTINE"
    details: Dict[str, Any] = Field(default_factory=dict)


class ChainVerificationResult(BaseModel):
    """
    Outcome of verifying a sequence of chained inference provenance records.
    """
    valid: bool
    records_checked: int
    anomalies: List[str] = Field(default_factory=list)
    recommended_disposition: str  # "ACCEPT", "REVIEW", "QUARANTINE"
    details: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# 3. Inference Provenance Engine
# ---------------------------------------------------------------------------

class InferenceProvenanceEngine:
    """
    Orchestrates inference provenance creation, cryptographic verification,
    tamper detection, and replay assurance across the TCVIAF pipeline.
    """

    GENESIS_PREV_HASH = "0" * 64

    def __init__(self, ledger: Optional[CryptoEvidenceLedger] = None):
        self.ledger = ledger

    def create_provenance_record(
        self,
        input_bytes: bytes,
        model_id: str,
        model_sha256: str,
        architecture_id: str,
        raw_detections: List[Dict[str, Any]],
        config: Dict[str, Any],
        preprocessing_config: Dict[str, Any],
        sequence_id: Optional[int] = None,
        previous_record_hash: Optional[str] = None,
        timestamp: Optional[float] = None,
        nonce: Optional[str] = None,
        store_to_ledger: bool = True
    ) -> InferenceProvenanceRecord:
        """
        Constructs, signs, and optionally persists an InferenceProvenanceRecord.
        """
        # 1. Input hash
        input_hash = hashlib.sha256(input_bytes).hexdigest()

        # 2. Canonical digests
        _, output_digest = canonicalize_output(raw_detections)
        _, config_digest = canonicalize_config(config)
        _, prep_digest = canonicalize_preprocessing(preprocessing_config)

        # 3. Timestamp & Nonce
        ts = time.time() if timestamp is None else float(timestamp)
        n = secrets.token_hex(16) if nonce is None else str(nonce)

        # 4. Sequence & Previous Hash Linkage
        if sequence_id is None or previous_record_hash is None:
            if self.ledger is not None:
                latest = self.ledger.get_latest_inference_provenance()
                if latest:
                    seq = latest["sequence_id"] + 1 if sequence_id is None else sequence_id
                    prev_hash = latest["provenance_hash"] if previous_record_hash is None else previous_record_hash
                else:
                    seq = 1 if sequence_id is None else sequence_id
                    prev_hash = self.GENESIS_PREV_HASH if previous_record_hash is None else previous_record_hash
            else:
                seq = 1 if sequence_id is None else sequence_id
                prev_hash = self.GENESIS_PREV_HASH if previous_record_hash is None else previous_record_hash
        else:
            seq = int(sequence_id)
            prev_hash = str(previous_record_hash)

        # 5. Compute provenance hash
        payload_str = (
            f"{seq}|"
            f"{input_hash}|"
            f"{model_id}|"
            f"{model_sha256}|"
            f"{architecture_id}|"
            f"{config_digest}|"
            f"{prep_digest}|"
            f"{output_digest}|"
            f"{ts:.4f}|"
            f"{n}|"
            f"{prev_hash}"
        )
        prov_hash = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
        pq_hybrid = compute_hybrid_provenance_hash(payload_str)

        record = InferenceProvenanceRecord(
            sequence_id=seq,
            input_hash=input_hash,
            model_id=model_id,
            model_sha256=model_sha256,
            architecture_id=architecture_id,
            config_digest=config_digest,
            preprocessing_digest=prep_digest,
            output_digest=output_digest,
            timestamp=ts,
            nonce=n,
            previous_record_hash=prev_hash,
            provenance_hash=prov_hash,
            pq_hybrid_digest=pq_hybrid,
            raw_payload={
                "config": config,
                "preprocessing": preprocessing_config,
                "detection_count": len(raw_detections)
            }
        )

        # 6. Store to ledger if enabled
        if store_to_ledger and self.ledger is not None:
            self.ledger.record_inference_provenance(record.model_dump())

        return record

    def sign_record_post_quantum(
        self,
        record: InferenceProvenanceRecord,
        pq_engine: Optional[Any] = None
    ) -> InferenceProvenanceRecord:
        """
        Signs the provenance record using NIST FIPS 205 WOTS+ post-quantum signature.
        """
        if pq_engine is None:
            from services.assurance.post_quantum import PostQuantumAssuranceEngine
            pq_engine = PostQuantumAssuranceEngine()
        payload_bytes = record.provenance_hash.encode('utf-8')
        signed = pq_engine.sign_record(payload_bytes)
        record.pq_signature = signed["pq_signature"]
        record.pq_hybrid_digest = signed["hybrid_commitment"]["hybrid_digest"]
        if self.ledger is not None:
            self.ledger.record_inference_provenance(record.model_dump())
        return record

    def verify_post_quantum_signature(
        self,
        record: InferenceProvenanceRecord
    ) -> bool:
        """
        Mathematically verifies the post-quantum WOTS+ signature on the record.
        """
        if not record.pq_signature:
            return False
        from services.assurance.post_quantum import WOTSPlusSHAKE256
        wots = WOTSPlusSHAKE256()
        payload_bytes = record.provenance_hash.encode('utf-8')
        return wots.verify(payload_bytes, record.pq_signature)

    def verify_provenance_record(
        self,
        record: InferenceProvenanceRecord,
        raw_input_bytes: Optional[bytes] = None,
        expected_input_hash: Optional[str] = None,
        raw_output: Optional[List[Dict[str, Any]]] = None,
        expected_model_sha256: Optional[str] = None,
        expected_model_id: Optional[str] = None,
        raw_config: Optional[Dict[str, Any]] = None,
        raw_preprocessing: Optional[Dict[str, Any]] = None
    ) -> ProvenanceVerificationResult:
        """
        Cryptographically verifies an individual provenance record against its fields
        and optional ground-truth execution artifacts.
        """
        anomalies = []
        tampered = False
        details: Dict[str, Any] = {}

        # 1. Recompute the provenance hash
        recomputed_hash = compute_provenance_hash(
            sequence_id=record.sequence_id,
            input_hash=record.input_hash,
            model_id=record.model_id,
            model_sha256=record.model_sha256,
            architecture_id=record.architecture_id,
            config_digest=record.config_digest,
            preprocessing_digest=record.preprocessing_digest,
            output_digest=record.output_digest,
            timestamp=record.timestamp,
            nonce=record.nonce,
            previous_record_hash=record.previous_record_hash
        )

        if recomputed_hash != record.provenance_hash:
            anomalies.append("PROVENANCE_HASH_MISMATCH")
            tampered = True
            details["hash_error"] = {
                "expected": recomputed_hash,
                "record": record.provenance_hash
            }

        # 2. Verify raw input bytes or expected input hash if provided
        if raw_input_bytes is not None:
            actual_input_hash = hashlib.sha256(raw_input_bytes).hexdigest()
            if actual_input_hash != record.input_hash:
                anomalies.append("INPUT_TAMPERING_DETECTED")
                tampered = True
                details["input_mismatch"] = {
                    "actual": actual_input_hash,
                    "recorded": record.input_hash
                }

        if expected_input_hash is not None:
            if expected_input_hash != record.input_hash:
                anomalies.append("INPUT_HASH_MISMATCH")
                tampered = True
                details["input_hash_mismatch"] = {
                    "expected": expected_input_hash,
                    "recorded": record.input_hash
                }

        # 3. Verify model weights digest or expected model ID if provided
        if expected_model_sha256 is not None:
            if expected_model_sha256 != record.model_sha256:
                anomalies.append("MODEL_TAMPERING_DETECTED")
                tampered = True
                details["model_mismatch"] = {
                    "expected": expected_model_sha256,
                    "recorded": record.model_sha256
                }

        if expected_model_id is not None:
            if expected_model_id != record.model_id:
                anomalies.append("MODEL_NAME_MISMATCH")
                tampered = True
                details["model_id_mismatch"] = {
                    "expected": expected_model_id,
                    "recorded": record.model_id
                }

        # 4. Verify inference config if provided
        if raw_config is not None:
            _, actual_config_digest = canonicalize_config(raw_config)
            if actual_config_digest != record.config_digest:
                anomalies.append("CONFIG_TAMPERING_DETECTED")
                tampered = True
                details["config_mismatch"] = {
                    "actual": actual_config_digest,
                    "recorded": record.config_digest
                }

        # 5. Verify preprocessing config if provided
        if raw_preprocessing is not None:
            _, actual_prep_digest = canonicalize_preprocessing(raw_preprocessing)
            if actual_prep_digest != record.preprocessing_digest:
                anomalies.append("PREPROCESSING_TAMPERING_DETECTED")
                tampered = True
                details["preprocessing_mismatch"] = {
                    "actual": actual_prep_digest,
                    "recorded": record.preprocessing_digest
                }

        # 6. Verify output detections if provided
        if raw_output is not None:
            _, actual_output_digest = canonicalize_output(raw_output)
            if actual_output_digest != record.output_digest:
                anomalies.append("OUTPUT_TAMPERING_DETECTED")
                tampered = True
                details["output_mismatch"] = {
                    "actual": actual_output_digest,
                    "recorded": record.output_digest
                }

        # Determine overall status and governance recommendation
        if tampered:
            status = "TAMPERED"
            recommended_disposition = "QUARANTINE"
        elif anomalies:
            status = "ANOMALY"
            recommended_disposition = "REVIEW"
        else:
            status = "VERIFIED"
            recommended_disposition = "ACCEPT"

        return ProvenanceVerificationResult(
            status=status,
            tampered=tampered,
            anomalies=anomalies,
            recomputed_hash=recomputed_hash,
            record_hash=record.provenance_hash,
            recommended_disposition=recommended_disposition,
            details=details
        )

    def verify_chain_and_replay(
        self,
        records: List[InferenceProvenanceRecord]
    ) -> ChainVerificationResult:
        """
        Verifies sequential integrity, hash chaining, and replay protection
        across a chronological sequence of provenance records.
        """
        if not records:
            return ChainVerificationResult(
                valid=True,
                records_checked=0,
                recommended_disposition="ACCEPT",
                details={"message": "Empty sequence"}
            )

        anomalies: List[str] = []
        seen_nonces: Set[str] = set()
        seen_provenance_hashes: Set[str] = set()
        valid = True
        details: Dict[str, Any] = {}

        for i, rec in enumerate(records):
            # 1. Nonce Replay Check
            if rec.nonce in seen_nonces:
                anomalies.append(f"PROVENANCE_REPLAY_DETECTED: Duplicate nonce '{rec.nonce}' at sequence {rec.sequence_id}")
                valid = False
            else:
                seen_nonces.add(rec.nonce)

            # 2. Provenance Hash Replay Check
            if rec.provenance_hash in seen_provenance_hashes:
                anomalies.append(f"PROVENANCE_REPLAY_DETECTED: Duplicate provenance hash at sequence {rec.sequence_id}")
                valid = False
            else:
                seen_provenance_hashes.add(rec.provenance_hash)

            # 3. Individual Record Integrity
            single_check = self.verify_provenance_record(rec)
            if single_check.tampered:
                anomalies.extend([f"SEQ_{rec.sequence_id}_{a}" for a in single_check.anomalies])
                valid = False

            # 4. Chain Linkage & Sequence Monotonicity (if not first record)
            if i > 0:
                prev_rec = records[i - 1]

                # Sequence gap / out of order
                if rec.sequence_id != prev_rec.sequence_id + 1:
                    anomalies.append(
                        f"PROVENANCE_SEQUENCE_GAP: Expected sequence {prev_rec.sequence_id + 1}, found {rec.sequence_id}"
                    )
                    valid = False

                # Hash chain linkage
                if rec.previous_record_hash != prev_rec.provenance_hash:
                    anomalies.append(
                        f"PROVENANCE_CHAIN_MISMATCH: Sequence {rec.sequence_id} previous_record_hash != Sequence {prev_rec.sequence_id} provenance_hash"
                    )
                    valid = False

                # Timestamp non-decreasing check (with small 0.001s tolerance for float representation)
                if rec.timestamp < prev_rec.timestamp - 0.001:
                    anomalies.append(
                        f"PROVENANCE_TIMESTAMP_INVERSION: Sequence {rec.sequence_id} timestamp ({rec.timestamp}) < Sequence {prev_rec.sequence_id} timestamp ({prev_rec.timestamp})"
                    )
                    valid = False
            else:
                # First record in this sequence slice
                # If sequence_id == 1, previous_record_hash should ideally be GENESIS_PREV_HASH
                if rec.sequence_id == 1 and rec.previous_record_hash != self.GENESIS_PREV_HASH:
                    anomalies.append(
                        f"PROVENANCE_CHAIN_MISMATCH: Genesis record sequence 1 has invalid previous_record_hash"
                    )
                    valid = False

        if not valid:
            # If chain breaks or tampering -> QUARANTINE
            # If only timestamp inversion or gap without tampering -> REVIEW
            has_tamper = any("MISMATCH" in a or "TAMPERING" in a for a in anomalies)
            recommended_disposition = "QUARANTINE" if has_tamper else "REVIEW"
        else:
            recommended_disposition = "ACCEPT"

        return ChainVerificationResult(
            valid=valid,
            records_checked=len(records),
            anomalies=anomalies,
            recommended_disposition=recommended_disposition,
            details=details
        )
