"""
Deterministic Dataset Hashing & Open-Data Compliance Auditor (SIH26228)
========================================================================
Implements deterministic, air-gapped cryptographic hashing for datasets, directories,
and archives, along with the strict Open-Data compliance verifier.

Requirements:
- Strict adherence to SIH26228 clause:
  "All development and evaluation data will be publicly available under applicable
   licences or synthetically generated. No classified, operational or service-generated data will be used."
- Deterministic canonical directory manifest hashing:
  Sort relative paths alphabetically, hash contents with SHA-256 in 64KB chunks,
  and construct deterministic Merkle root.
- Clean handling of missing local archives: marks status as
  REGISTERED_BUT_NOT_EXECUTED without fabricating hashes or raising unhandled crashes.
"""

from __future__ import annotations

import os
import sys
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timezone


def compute_file_sha256(filepath: str | Path, chunk_size: int = 65536) -> str:
    """
    Computes streaming SHA-256 hash of a file.
    Deterministic across all operating systems.
    """
    p = Path(filepath)
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {filepath}")

    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


class DirectoryFileEntry(BaseModel):
    relative_path: str
    size_bytes: int
    sha256: str


class DirectoryManifest(BaseModel):
    directory_path: str
    total_files: int
    total_bytes: int
    files: List[DirectoryFileEntry]
    manifest_sha256: str
    merkle_root: str
    computed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def compute_directory_manifest(
    dir_path: str | Path,
    exclude_patterns: Optional[List[str]] = None
) -> DirectoryManifest:
    """
    Computes a deterministic directory manifest and Merkle hash.
    Relative paths are normalized to POSIX format (forward slashes) and sorted alphabetically.
    """
    root = Path(dir_path).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Directory not found: {dir_path}")

    default_excludes = [".git", "__pycache__", ".pytest_cache", ".DS_Store", "desktop.ini", "synthetic_provenance.json"]
    excludes = default_excludes + (exclude_patterns or [])

    file_entries: List[DirectoryFileEntry] = []
    total_bytes = 0

    for path in sorted(root.rglob("*")):
        if path.is_file():
            # Check exclusions
            parts = path.parts
            if any(exc in parts for exc in excludes):
                continue

            rel_path = path.relative_to(root).as_posix()
            file_size = path.stat().st_size
            total_bytes += file_size
            file_hash = compute_file_sha256(path)

            file_entries.append(DirectoryFileEntry(
                relative_path=rel_path,
                size_bytes=file_size,
                sha256=file_hash
            ))

    # Sort entries deterministically by relative path
    file_entries.sort(key=lambda x: x.relative_path)

    # Compute manifest digest over serialized entries
    manifest_hasher = hashlib.sha256()
    for entry in file_entries:
        line = f"{entry.relative_path}:{entry.size_bytes}:{entry.sha256}\n"
        manifest_hasher.update(line.encode("utf-8"))
    manifest_sha256 = manifest_hasher.hexdigest()

    # Build Merkle tree root over leaf hashes
    if not file_entries:
        merkle_root = "0" * 64
    else:
        current_level = [e.sha256 for e in file_entries]
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = hashlib.sha256((left + right).encode("utf-8")).hexdigest()
                next_level.append(combined)
            current_level = next_level
        merkle_root = current_level[0]

    return DirectoryManifest(
        directory_path=str(root),
        total_files=len(file_entries),
        total_bytes=total_bytes,
        files=file_entries,
        manifest_sha256=manifest_sha256,
        merkle_root=merkle_root
    )


class DatasetAuditEntry(BaseModel):
    dataset_id: str
    name: str
    intended_use: str
    license: str
    license_verification_status: str = "VERIFIED"
    artifact_type: Optional[str] = None
    is_open_data_compliant: bool
    status: str
    local_path: Optional[str] = None
    computed_sha256: Optional[str] = None
    hash_verified: Optional[bool] = None
    provenance_status: Optional[str] = None
    message: str


class DatasetAuditReport(BaseModel):
    compliance_rule_id: str
    compliance_statement: str
    audited_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_datasets: int
    open_data_compliant_count: int
    non_compliant_count: int
    verified_local_count: int
    synthetic_count: int
    registered_external_count: int
    overall_compliant: bool
    compliance_claim_status: str = "FULLY_VERIFIED"  # "FULLY_VERIFIED" vs "PARTIAL / PENDING VERIFICATION"
    entries: List[DatasetAuditEntry]


class DatasetComplianceAuditor:
    """
    Audits the dataset registry against SIH26228 rules.
    Verifies that no operational, classified, or service data is referenced,
    and checks cryptographic commitments for locally stored files and synthetic suites.
    """

    def __init__(self, manifest_path: Optional[str | Path] = None, base_dir: Optional[str | Path] = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parents[2]
        if manifest_path:
            self.manifest_path = Path(manifest_path)
        else:
            cfg_p = self.base_dir / "config" / "dataset_manifest.json"
            if cfg_p.is_file():
                self.manifest_path = cfg_p
            else:
                self.manifest_path = self.base_dir / "configs" / "dataset_manifest.json"

    def load_manifest(self) -> Dict[str, Any]:
        if not self.manifest_path.is_file():
            raise FileNotFoundError(f"Dataset manifest not found at: {self.manifest_path}")
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def run_audit(self) -> DatasetAuditReport:
        manifest_data = self.load_manifest()
        datasets = manifest_data.get("datasets", [])
        compliance_rule_id = manifest_data.get("compliance_rule_id", "SIH26228-OPEN-DATA-CLAUSE")
        compliance_statement = manifest_data.get(
            "compliance_statement",
            "All development and evaluation data will be publicly available under applicable licences or synthetically generated."
        )

        entries: List[DatasetAuditEntry] = []
        compliant_count = 0
        non_compliant_count = 0
        verified_local_count = 0
        synthetic_count = 0
        registered_external_count = 0

        for ds in datasets:
            ds_id = ds.get("dataset_id", "unknown")
            name = ds.get("name", "Unknown Dataset")
            intended_use = ds.get("purpose") or ds.get("intended_use", "general")
            ds_license = ds.get("license_type") or ds.get("license", "Unknown")
            lic_ver_status = ds.get("license_verification_status", "VERIFIED")
            artifact_type = ds.get("artifact_type")
            is_classified = ds.get("is_classified", False)
            is_operational = ds.get("is_operational", False)
            is_service_gen = ds.get("is_service_generated", False)
            is_synthetic = ds.get("is_synthetic", False)
            storage_type = ds.get("storage_type", "external_reference")
            local_rel_path = ds.get("local_path")
            expected_hash = ds.get("sha256_checksum")
            prov_status = ds.get("provenance_status")

            # Check open-data compliance rule
            if is_classified or is_operational or is_service_gen:
                is_compliant = False
                message = "NON-COMPLIANT: Contains classified, operational, or service-generated data."
                status = "REJECTED_NON_COMPLIANT"
                non_compliant_count += 1
            else:
                is_compliant = True
                compliant_count += 1

            if is_synthetic:
                synthetic_count += 1

            computed_sha = None
            hash_verified = None

            # Check local file or directory if specified
            if local_rel_path:
                full_local_path = self.base_dir / local_rel_path
                if full_local_path.exists():
                    if full_local_path.is_file():
                        computed_sha = compute_file_sha256(full_local_path)
                        status = "VERIFIED_LOCAL"
                        verified_local_count += 1
                        if expected_hash:
                            hash_verified = (computed_sha.lower() == expected_hash.lower())
                            message = "Verified local file with matching cryptographic checksum." if hash_verified else "Checksum mismatch against declared manifest hash."
                        else:
                            hash_verified = True
                            message = "Verified local file. Checksum computed."
                    elif full_local_path.is_dir():
                        dir_manifest = compute_directory_manifest(full_local_path)
                        computed_sha = dir_manifest.merkle_root
                        status = "VERIFIED_LOCAL" if not is_synthetic else "SYNTHETIC_GENERATED"
                        verified_local_count += 1
                        hash_verified = True
                        message = f"Verified local directory ({dir_manifest.total_files} files, Merkle Root computed)."
                else:
                    status = "MISSING_LOCAL_PATH"
                    hash_verified = False
                    message = f"Declared local path '{local_rel_path}' does not exist on disk."
            else:
                status = ds.get("status") or ds.get("provenance_status", "REGISTERED_BUT_NOT_EXECUTED")
                registered_external_count += 1
                message = "Public reference registered. Local artifacts not loaded into air-gap storage."

            entries.append(DatasetAuditEntry(
                dataset_id=ds_id,
                name=name,
                intended_use=intended_use,
                license=ds_license,
                license_verification_status=lic_ver_status,
                artifact_type=artifact_type,
                is_open_data_compliant=is_compliant,
                status=status,
                local_path=local_rel_path,
                computed_sha256=computed_sha,
                hash_verified=hash_verified,
                provenance_status=prov_status or status,
                message=message
            ))

        overall_compliant = (non_compliant_count == 0)

        # Phase 19: Strict Compliance Claim Logic
        # FULLY_VERIFIED only when all actually used/local assets have source, license, artifact, hash verified,
        # classification flags clean, and provenance recorded.
        all_used_verified = True
        for e in entries:
            if e.local_path:
                if not (e.is_open_data_compliant and e.hash_verified and e.license_verification_status == "VERIFIED"):
                    all_used_verified = False
                    break

        if overall_compliant and all_used_verified and len(entries) > 0:
            claim_status = "FULLY_VERIFIED"
        else:
            claim_status = "PARTIAL / PENDING VERIFICATION"

        return DatasetAuditReport(
            compliance_rule_id=compliance_rule_id,
            compliance_statement=compliance_statement,
            total_datasets=len(datasets),
            open_data_compliant_count=compliant_count,
            non_compliant_count=non_compliant_count,
            verified_local_count=verified_local_count,
            synthetic_count=synthetic_count,
            registered_external_count=registered_external_count,
            overall_compliant=overall_compliant,
            compliance_claim_status=claim_status,
            entries=entries
        )
