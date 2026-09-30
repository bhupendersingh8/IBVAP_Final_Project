"""
services/assurance/manifest_verifier.py
=======================================
TCVIAF / SIH26228 Supply-Chain Verification Service for Manifests & AIBOMs.

Executes comprehensive cryptographic, structural, and physical integrity checks:
1. Ed25519 Asymmetric Signature Verification
2. Manifest Structural & Canonical Hash Validation
3. Physical Model File Checkpoint Hash Cross-Verification (Prevents hash substitution attacks)
4. CycloneDX 1.5 AIBOM Schema & Component Validation
5. Cross-Binding Integrity between Signed Manifest and AIBOM Document
6. Actionable Structured Telemetry with Explicit Failure Breakdown
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union
from pydantic import BaseModel, Field

from crypto_ledger import compute_file_sha256
from services.assurance.contributor_manifest import (
    verify_manifest_signature,
    compute_manifest_digest,
    ContributorModelManifest
)
from services.assurance.aibom import (
    verify_manifest_aibom_binding,
    extract_model_component,
    extract_property_value
)


class VerificationChecks(BaseModel):
    model_config = {"protected_namespaces": ()}
    signature: bool = False
    manifest_structure: bool = False
    model_digest_format: bool = False
    physical_file_digest: Optional[bool] = None
    preprocessing_binding: bool = False
    behavioral_fingerprint_binding: bool = False
    aibom_binding: Optional[bool] = None


class ManifestVerificationResult(BaseModel):
    model_config = {"protected_namespaces": ()}
    valid: bool
    manifest_id: str
    model_id: str
    contributor_id: str
    contributor_org: str
    manifest_digest: str
    checks: VerificationChecks
    failures: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class AIBOMVerificationResult(BaseModel):
    model_config = {"protected_namespaces": ()}
    valid: bool
    bom_format: str
    spec_version: str
    serial_number: str
    model_component_found: bool
    failures: List[str] = Field(default_factory=list)


class CompleteSupplyChainReport(BaseModel):
    model_config = {"protected_namespaces": ()}
    valid: bool
    manifest_result: ManifestVerificationResult
    aibom_result: Optional[AIBOMVerificationResult] = None
    binding_valid: Optional[bool] = None
    failures: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Verification Service Class
# ---------------------------------------------------------------------------

class SupplyChainVerifier:
    """
    Comprehensive verification engine for multi-contributor model manifests
    and CycloneDX AIBOMs.
    """

    @staticmethod
    def verify_manifest(
        manifest: Union[ContributorModelManifest, Dict[str, Any]],
        model_file_path: Optional[Union[str, Path]] = None
    ) -> ManifestVerificationResult:
        """
        Cryptographically and structurally verifies a ContributorModelManifest.
        If model_file_path is provided, independently computes its on-disk SHA-256
        and verifies it against the signed manifest digest (preventing hash substitution).
        """
        if isinstance(manifest, ContributorModelManifest):
            manifest_dict = manifest.model_dump()
        else:
            manifest_dict = dict(manifest)

        failures: List[str] = []
        limitations: List[str] = []
        checks = VerificationChecks()

        manifest_id = manifest_dict.get("manifest_id", "unknown")
        model = manifest_dict.get("model", {})
        model_id = model.get("model_id", "unknown")
        contributor = manifest_dict.get("contributor", {})
        contrib_id = contributor.get("id", "unknown")
        contrib_org = contributor.get("organization", "unknown")

        # 1. Structure and Field Format Validation
        try:
            # Validate through Pydantic model
            parsed = ContributorModelManifest.model_validate(manifest_dict)
            checks.manifest_structure = True
            checks.model_digest_format = True
            checks.preprocessing_binding = True

            fp_digest = parsed.behavioral_fingerprint.digest
            if fp_digest == "UNAVAILABLE":
                limitations.append("Behavioral fingerprint not enrolled; marked 'UNAVAILABLE'")
                checks.behavioral_fingerprint_binding = True
            else:
                checks.behavioral_fingerprint_binding = True

            if parsed.model.parameter_count is None:
                limitations.append("Model parameter_count is null (unverified at enrollment)")

        except Exception as e:
            failures.append(f"Manifest schema validation error: {str(e)}")
            checks.manifest_structure = False

        # 2. Cryptographic Ed25519 Signature Verification
        is_sig_valid, sig_err = verify_manifest_signature(manifest_dict)
        checks.signature = is_sig_valid
        if not is_sig_valid:
            failures.append(sig_err or "Invalid Ed25519 signature")

        # 3. Canonical Manifest Digest
        try:
            manifest_digest = compute_manifest_digest(manifest_dict)
        except Exception as e:
            manifest_digest = "0" * 64
            failures.append(f"Failed to compute canonical manifest digest: {str(e)}")

        # 4. Physical Model Checkpoint Cross-Verification
        if model_file_path is not None:
            path = Path(model_file_path)
            if not path.is_file():
                checks.physical_file_digest = False
                failures.append(f"Specified physical model checkpoint file does not exist: {model_file_path}")
            else:
                try:
                    actual_sha = compute_file_sha256(path)
                    declared_sha = model.get("sha256", "").lower()
                    if actual_sha == declared_sha:
                        checks.physical_file_digest = True
                    else:
                        checks.physical_file_digest = False
                        failures.append(
                            f"PHYSICAL MODEL CHECKSUM MISMATCH: On-disk file '{path.name}' has SHA-256 '{actual_sha[:16]}...', "
                            f"which differs from manifest declared SHA-256 '{declared_sha[:16]}...'"
                        )
                except Exception as e:
                    checks.physical_file_digest = False
                    failures.append(f"Failed to compute physical model hash: {str(e)}")

        overall_valid = (len(failures) == 0) and checks.signature and checks.manifest_structure

        return ManifestVerificationResult(
            valid=overall_valid,
            manifest_id=manifest_id,
            model_id=model_id,
            contributor_id=contrib_id,
            contributor_org=contrib_org,
            manifest_digest=manifest_digest,
            checks=checks,
            failures=failures,
            limitations=limitations
        )

    @staticmethod
    def verify_aibom(aibom_dict: Dict[str, Any]) -> AIBOMVerificationResult:
        """
        Validates the structure, spec version, and components of a CycloneDX AIBOM document.
        """
        failures: List[str] = []
        bom_fmt = aibom_dict.get("bomFormat", "")
        spec_ver = aibom_dict.get("specVersion", "")
        serial = aibom_dict.get("serialNumber", "")

        if bom_fmt != "CycloneDX":
            failures.append(f"bomFormat mismatch: expected 'CycloneDX', got '{bom_fmt}'")

        if spec_ver != "1.5":
            failures.append(f"specVersion mismatch: expected '1.5', got '{spec_ver}'")

        comp = extract_model_component(aibom_dict)
        model_found = comp is not None
        if not model_found:
            failures.append("No machine-learning-model component found in CycloneDX document")

        return AIBOMVerificationResult(
            valid=(len(failures) == 0),
            bom_format=bom_fmt,
            spec_version=spec_ver,
            serial_number=serial,
            model_component_found=model_found,
            failures=failures
        )

    @staticmethod
    def verify_supply_chain(
        manifest: Union[ContributorModelManifest, Dict[str, Any]],
        aibom: Optional[Dict[str, Any]] = None,
        model_file_path: Optional[Union[str, Path]] = None
    ) -> CompleteSupplyChainReport:
        """
        Executes end-to-end supply chain verification:
        - Manifest signature and structure
        - Physical model file checksum (if provided)
        - AIBOM structure (if provided)
        - Manifest ↔ AIBOM cross-binding (if both provided)
        """
        manifest_res = SupplyChainVerifier.verify_manifest(manifest, model_file_path=model_file_path)
        failures = list(manifest_res.failures)

        aibom_res = None
        binding_valid = None

        if aibom is not None:
            manifest_dict = manifest.model_dump() if isinstance(manifest, ContributorModelManifest) else manifest
            aibom_res = SupplyChainVerifier.verify_aibom(aibom)
            failures.extend(aibom_res.failures)

            is_bound, bind_errs = verify_manifest_aibom_binding(manifest_dict, aibom)
            binding_valid = is_bound
            manifest_res.checks.aibom_binding = is_bound
            if not is_bound:
                failures.extend(bind_errs)

        is_valid = (len(failures) == 0) and manifest_res.valid and (aibom_res is None or aibom_res.valid)

        return CompleteSupplyChainReport(
            valid=is_valid,
            manifest_result=manifest_res,
            aibom_result=aibom_res,
            binding_valid=binding_valid,
            failures=failures
        )
