"""
Canonical Verified Event Contract (IBVAP / SIH26228)
=====================================================
Unified data contract bridging Layer 187 Vision Intelligence and Layer 228 Integrity Assurance.

Every downstream system (Evidence Ledger, Technical Evidence Certificates,
WebSocket Telemetry, and React Operations Dashboard) consumes this canonical schema.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class BoundingBox(BaseModel):
    """Normalized bounding box coordinates [x1, y1, x2, y2]."""
    x1: float
    y1: float
    x2: float
    y2: float


class SpecialistEvidence(BaseModel):
    """Specialist model observation output (ANPR, Pose, MobileSAM, Face, Threat)."""
    specialist_type: str = Field(description="Type of specialist (e.g. 'ANPR', 'POSE', 'SEGMENTATION', 'THREAT')")
    model_name: str
    model_version: str
    confidence: float
    attributes: Dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: float = 0.0


class TrajectorySummary(BaseModel):
    """Track movement trajectory and velocity characteristics."""
    track_id: int
    dwell_seconds: float
    direction: str = "UNKNOWN"
    velocity_mps: float = 0.0
    waypoints: List[List[float]] = Field(default_factory=list)


class BenchmarkEvidenceItem(BaseModel):
    """Reference attack or assurance benchmark finding."""
    asset: str
    attack_class: str
    source: str
    model: str
    input_hash: str
    model_hash: str
    output_hash: str
    benchmark_id: str
    benchmark_version: str
    evidence: str
    confidence: float
    severity: str = "MEDIUM"  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    governance: str = "REVIEW"  # "ACCEPT", "REVIEW", "QUARANTINE"
    provenance: Dict[str, Any] = Field(default_factory=dict)


class VerifiedEvent(BaseModel):
    """
    Canonical Verified Event Contract.
    Binds all Layer 187 Vision Intelligence signals with Layer 228 Cryptographic Assurance.
    """
    model_config = ConfigDict(extra="ignore")

    # Core Identifiers & Timing
    event_id: str = Field(description="Unique UUID for this verified event")
    camera_id: str = Field(description="Authoritative Camera ID (e.g. 'CAM-01')")
    timestamp: str = Field(description="ISO-8601 UTC timestamp")
    sequence_id: int = Field(description="Sequential monotonically increasing frame/block index")
    
    # 187 Vision Intelligence Attributes
    track_ids: List[int] = Field(default_factory=list, description="Associated track instances")
    object_classifications: List[str] = Field(default_factory=list, description="Tactical/domain classes")
    bounding_boxes: List[BoundingBox] = Field(default_factory=list, description="Target locations in frame")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall fused event confidence")
    zone_id: Optional[str] = Field(default=None, description="Restricted perimeter zone entered")
    event_type: str = Field(default="PERIMETER_INTRUSION", description="Operational event classification")
    severity: str = Field(default="MEDIUM", description="Severity (LOW, MEDIUM, HIGH, CRITICAL)")
    explanation: str = Field(default="", description="Human-interpretable rationale for event trigger")
    trajectory_summary: Optional[TrajectorySummary] = None
    specialist_evidence: List[SpecialistEvidence] = Field(default_factory=list)
    frame_references: List[str] = Field(default_factory=list, description="Relative paths to committed keyframes")

    # 228 Cryptographic Assurance & Provenance
    input_hash: str = Field(description="SHA-256 of raw frame buffer")
    model_hashes: Dict[str, str] = Field(default_factory=dict, description="Model weight SHA-256 digests")
    configuration_hash: str = Field(default="", description="SHA-256 of active detection & zone config")
    preprocessing_hash: str = Field(default="", description="SHA-256 of enhancement parameters (Zero-DCE/CLAHE)")
    previous_provenance_hash: str = Field(description="Recursive link H_{n-1}")
    nonce: str = Field(default_factory=lambda: secrets.token_hex(8), description="Entropy nonce")
    current_provenance_hash: str = Field(description="Computed Merkle block hash H_n")
    governance_decision: str = Field(default="ACCEPT", description="Governance status: ACCEPT, REVIEW, QUARANTINE")
    assurance_status: str = Field(default="VERIFIED", description="Cryptographic status: VERIFIED, FLAG_TAMPER")
    evidence_references: Dict[str, Any] = Field(default_factory=dict, description="Ledger block index and UUIDs")
    benchmark_evidence: List[BenchmarkEvidenceItem] = Field(default_factory=list, description="Attached reference attack/assurance benchmark findings")

    def compute_canonical_digest(self) -> str:
        """Returns deterministic SHA-256 digest of the entire verified event."""
        payload = {
            "event_id": self.event_id,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp,
            "sequence_id": self.sequence_id,
            "confidence": round(self.confidence, 4),
            "input_hash": self.input_hash,
            "previous_provenance_hash": self.previous_provenance_hash,
            "current_provenance_hash": self.current_provenance_hash,
            "governance_decision": self.governance_decision,
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
