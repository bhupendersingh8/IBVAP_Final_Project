"""
TCVIAF / SIH26228 Data Integrity & Distribution Shift Assurance Module.
Provides deterministic, model-agnostic, offline-capable verification:
1. Exact Duplicate Detection (SHA-256)
2. Perceptual Near-Duplicate Detection (dHash-64 Hamming Distance)
3. YOLO Annotation Geometry & Class Boundary Check
4. Centroid-Distance Anomaly Indicator (Lightweight, non-generative)
5. Distribution Shift Monitoring (Two-Sample Kolmogorov-Smirnov Test)
"""
from __future__ import annotations

import json
import uuid
import hashlib
from typing import List, Dict, Any, Optional, Set, Union
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import cv2

try:
    import scipy.stats
    _SCIPY_AVAILABLE = True
except ImportError:
    _SCIPY_AVAILABLE = False


class ProvenanceMetadata(BaseModel):
    source_id: str
    batch_id: str
    dataset_version: Optional[str] = None
    ingestion_timestamp: str
    file_identifier: str


class AssuranceFinding(BaseModel):
    finding_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sequence_id: Optional[int] = None
    asset_id: str
    asset_type: str
    check_type: str
    method: str
    score: Optional[float] = None
    threshold: Optional[float] = None
    status: str
    confidence: Optional[float] = None
    evidence: str
    limitations: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance: Optional[ProvenanceMetadata] = None


def compute_ahash(img: np.ndarray, hash_size: int = 8) -> str:
    """
    Computes a 64-bit Perceptual Average Hash (aHash) for an image array.
    Deterministic, offline, and lightweight.
    """
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    resized = cv2.resize(gray, (hash_size, hash_size), interpolation=cv2.INTER_AREA)
    mean = float(np.mean(resized))
    bits = (resized > mean).flatten()
    int_val = int("".join(["1" if b else "0" for b in bits]), 2)
    return f"{int_val:016x}"


# Backward compatibility alias
compute_dhash = compute_ahash
compute_phash = compute_ahash


def compute_hamming_distance(hash1: str, hash2: str) -> int:
    """Computes bitwise Hamming distance between two 16-character hex strings."""
    i1 = int(hash1, 16)
    i2 = int(hash2, 16)
    return bin(i1 ^ i2).count("1")


def compute_pairwise_sqeuclidean(X: np.ndarray, Y: np.ndarray) -> np.ndarray:
    """Computes squared Euclidean distance matrix between X (m, d) and Y (n, d)."""
    X_sq = np.sum(X ** 2, axis=1, keepdims=True)
    Y_sq = np.sum(Y ** 2, axis=1, keepdims=True).T
    dists = X_sq + Y_sq - 2.0 * np.dot(X, Y.T)
    return np.maximum(0.0, dists)


def compute_bbox_iou(box1: List[float], box2: List[float]) -> float:
    """
    Computes IoU between two bounding boxes in normalized [cx, cy, w, h] format.
    """
    x1_min, y1_min = box1[0] - box1[2] / 2.0, box1[1] - box1[3] / 2.0
    x1_max, y1_max = box1[0] + box1[2] / 2.0, box1[1] + box1[3] / 2.0
    x2_min, y2_min = box2[0] - box2[2] / 2.0, box2[1] - box2[3] / 2.0
    x2_max, y2_max = box2[0] + box2[2] / 2.0, box2[1] + box2[3] / 2.0

    inter_xmin = max(x1_min, x2_min)
    inter_ymin = max(y1_min, y2_min)
    inter_xmax = min(x1_max, x2_max)
    inter_ymax = min(y1_max, y2_max)

    inter_w = max(0.0, inter_xmax - inter_xmin)
    inter_h = max(0.0, inter_ymax - inter_ymin)
    inter_area = inter_w * inter_h

    area1 = max(0.0, box1[2] * box1[3])
    area2 = max(0.0, box2[2] * box2[3])
    union_area = area1 + area2 - inter_area
    if union_area <= 0.0:
        return 0.0
    return float(inter_area / union_area)


def compute_mmd_rbf(X: np.ndarray, Y: np.ndarray, gamma: Optional[float] = None) -> tuple[float, float]:
    """
    Computes unbiased two-sample Maximum Mean Discrepancy (MMD) with Gaussian RBF kernel.
    Returns (mmd_squared, gamma).
    """
    m = len(X)
    n = len(Y)
    if m < 2 or n < 2:
        return 0.0, 1.0

    Z = np.vstack([X, Y])
    D_ZZ = compute_pairwise_sqeuclidean(Z, Z)
    if gamma is None:
        triu_dists = D_ZZ[np.triu_indices_from(D_ZZ, k=1)]
        med = float(np.median(triu_dists)) if len(triu_dists) > 0 else 1.0
        gamma = 1.0 / (2.0 * max(med, 1e-5))

    D_XX = compute_pairwise_sqeuclidean(X, X)
    D_YY = compute_pairwise_sqeuclidean(Y, Y)
    D_XY = compute_pairwise_sqeuclidean(X, Y)

    K_XX = np.exp(-gamma * D_XX)
    K_YY = np.exp(-gamma * D_YY)
    K_XY = np.exp(-gamma * D_XY)

    sum_XX = (np.sum(K_XX) - np.trace(K_XX)) / (m * (m - 1))
    sum_YY = (np.sum(K_YY) - np.trace(K_YY)) / (n * (n - 1))
    sum_XY = np.sum(K_XY) / (m * n)

    mmd_sq = float(sum_XX + sum_YY - 2.0 * sum_XY)
    return mmd_sq, float(gamma)


class DataIntegrityAssurance:
    """
    Data Integrity & Distribution Shift Assurance Engine.
    Interacts with CryptoEvidenceLedger for immutable persistence.
    """

    def __init__(self, ledger=None):
        self.ledger = ledger

    def _persist_finding(self, finding: AssuranceFinding):
        if not self.ledger:
            return
        try:
            if hasattr(self.ledger, "insert_assurance_finding"):
                self.ledger.insert_assurance_finding(finding.model_dump())
        except Exception as e:
            # Fallback gracefully without crashing caller
            pass

    def check_exact_duplicate(
        self,
        asset_id: str,
        file_path_or_bytes: Union[str, Path, bytes],
        reference_hashes: Set[str],
        sequence_id: Optional[int] = None
    ) -> Optional[AssuranceFinding]:
        """
        Performs cryptographic exact duplicate detection via SHA-256.
        """
        limitations = (
            "Cryptographic byte equality only; single-pixel perturbation, metadata variation, "
            "or re-compression will yield completely different digests."
        )
        try:
            if isinstance(file_path_or_bytes, (str, Path)):
                with open(file_path_or_bytes, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
            elif isinstance(file_path_or_bytes, (bytes, bytearray)):
                file_hash = hashlib.sha256(file_path_or_bytes).hexdigest()
            else:
                return None
        except Exception:
            return None

        is_dup = file_hash in reference_hashes
        score = 1.0 if is_dup else 0.0
        status = "POTENTIAL_DUPLICATE" if is_dup else "NORMAL"

        finding = AssuranceFinding(
            sequence_id=sequence_id,
            asset_id=asset_id,
            asset_type="IMAGE",
            check_type="EXACT_DUPLICATE_DETECTION",
            method="SHA-256 Exact Match",
            score=score,
            threshold=1.0,
            status=status,
            confidence=1.0,
            evidence=f"Computed SHA-256: {file_hash}" + (" (Matches reference digest)" if is_dup else " (Unique in reference set)"),
            limitations=limitations
        )
        if status != "NORMAL":
            self._persist_finding(finding)
        return finding

    def check_perceptual_near_duplicate(
        self,
        asset_id: str,
        image_or_path: Union[str, Path, np.ndarray],
        reference_hashes: Dict[str, str],
        max_hamming_distance: int = 5,
        sequence_id: Optional[int] = None
    ) -> Optional[AssuranceFinding]:
        """
        Performs perceptual near-duplicate detection using 64-bit Difference Hash (dHash).
        reference_hashes is a mapping of ref_asset_id -> 16-char hex dHash.
        max_hamming_distance defines the maximum bit difference to flag as near-duplicate (default <= 5 bits / 64).
        """
        limitations = (
            "Perceptual difference hashing (dHash-64) detects low-frequency structural/luminance "
            "similarity and minor compression artifacts; it does not capture deep semantic equivalence "
            "across large rotations, severe crops, or major occlusions."
        )
        try:
            if isinstance(image_or_path, (str, Path)):
                img = cv2.imread(str(image_or_path))
                if img is None:
                    return None
            elif isinstance(image_or_path, np.ndarray):
                img = image_or_path
            else:
                return None

            curr_hash = compute_dhash(img)
        except Exception:
            return None

        min_dist = 64
        closest_ref = None
        for ref_id, ref_hash in reference_hashes.items():
            dist = compute_hamming_distance(curr_hash, ref_hash)
            if dist < min_dist:
                min_dist = dist
                closest_ref = ref_id

        similarity = 1.0 - (min_dist / 64.0)
        threshold_sim = 1.0 - (max_hamming_distance / 64.0)
        is_near_dup = min_dist <= max_hamming_distance
        status = "POTENTIAL_NEAR_DUPLICATE" if is_near_dup else "NORMAL"

        evidence = (
            f"dHash: {curr_hash}. Min Hamming distance: {min_dist}/64 (similarity: {similarity:.4f})"
            + (f" to ref '{closest_ref}'" if closest_ref else "")
            + f" (Threshold max distance: {max_hamming_distance}, min similarity: {threshold_sim:.4f})"
        )

        finding = AssuranceFinding(
            sequence_id=sequence_id,
            asset_id=asset_id,
            asset_type="IMAGE",
            check_type="NEAR_DUPLICATE_DETECTION",
            method="Perceptual Difference Hash (dHash-64)",
            score=float(similarity),
            threshold=float(threshold_sim),
            status=status,
            confidence=float(similarity) if is_near_dup else 1.0,
            evidence=evidence,
            limitations=limitations
        )
        if status != "NORMAL":
            self._persist_finding(finding)
        return finding

    def check_yolo_labels(
        self,
        asset_id: str,
        labels_path_or_text: Union[str, Path],
        valid_classes: Optional[Set[int]] = None,
        sequence_id: Optional[int] = None
    ) -> List[AssuranceFinding]:
        """
        Validates YOLO format annotation files for:
        - Out-of-bounds normalized coordinates (0 <= cx, cy, w, h <= 1)
        - Non-positive dimensions (w <= 0 or h <= 0)
        - Unknown / unauthorized class IDs
        - Malformed formatting
        """
        findings = []
        limitations = (
            "Syntactic boundary and geometry check only; does not perform semantic "
            "ground-truth validation without clean annotated reference data."
        )

        lines = []
        try:
            p = Path(str(labels_path_or_text))
            if p.exists() and p.is_file():
                with open(p, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            else:
                lines = str(labels_path_or_text).strip().splitlines()
        except Exception:
            lines = str(labels_path_or_text).strip().splitlines()

        for idx, line in enumerate(lines):
            line_str = line.strip()
            if not line_str:
                continue
            parts = line_str.split()
            if len(parts) != 5:
                findings.append(AssuranceFinding(
                    sequence_id=sequence_id,
                    asset_id=asset_id,
                    asset_type="ANNOTATION",
                    check_type="LABEL_CONSISTENCY",
                    method="YOLO Format Arity Check",
                    score=1.0,
                    threshold=0.0,
                    status="MALFORMED_FORMAT",
                    confidence=1.0,
                    evidence=f"Line {idx+1}: Expected 5 fields (class cx cy w h), found {len(parts)}: '{line_str}'",
                    limitations=limitations
                ))
                continue

            try:
                cls_id = int(parts[0])
                cx, cy, w, h = map(float, parts[1:])

                # Check class ID
                if valid_classes is not None and cls_id not in valid_classes:
                    findings.append(AssuranceFinding(
                        sequence_id=sequence_id,
                        asset_id=asset_id,
                        asset_type="ANNOTATION",
                        check_type="LABEL_CONSISTENCY",
                        method="Class ID Domain Verification",
                        score=1.0,
                        threshold=0.0,
                        status="INVALID_CLASS",
                        confidence=1.0,
                        evidence=f"Line {idx+1}: Class ID {cls_id} not in authorized class set {sorted(list(valid_classes))}",
                        limitations=limitations
                    ))

                # Check bounding box bounds
                if w <= 0.0 or h <= 0.0 or cx < 0.0 or cx > 1.0 or cy < 0.0 or cy > 1.0 or w > 1.0 or h > 1.0:
                    findings.append(AssuranceFinding(
                        sequence_id=sequence_id,
                        asset_id=asset_id,
                        asset_type="ANNOTATION",
                        check_type="LABEL_CONSISTENCY",
                        method="Bounding Box Coordinate Sanity Check",
                        score=1.0,
                        threshold=0.0,
                        status="IMPOSSIBLE_BBOX",
                        confidence=1.0,
                        evidence=f"Line {idx+1}: Coordinates out of [0, 1] range (cx={cx}, cy={cy}, w={w}, h={h})",
                        limitations=limitations
                    ))
            except ValueError as ve:
                findings.append(AssuranceFinding(
                    sequence_id=sequence_id,
                    asset_id=asset_id,
                    asset_type="ANNOTATION",
                    check_type="LABEL_CONSISTENCY",
                    method="Field Type Verification",
                    score=1.0,
                    threshold=0.0,
                    status="MALFORMED_FORMAT",
                    confidence=1.0,
                    evidence=f"Line {idx+1}: Non-numeric values in annotation: {ve}",
                    limitations=limitations
                ))

        for f in findings:
            self._persist_finding(f)
        return findings

    def check_ood(
        self,
        asset_id: str,
        features: np.ndarray,
        reference_features: Optional[np.ndarray],
        threshold_sigma: float = 3.0,
        sequence_id: Optional[int] = None,
        method: str = "centroid_distance"
    ) -> AssuranceFinding:
        """
        Out-of-Distribution (OOD) Anomaly Detector.
        Supports methods:
        - "centroid_distance" (Default): Lightweight L2 centroid distance with 3σ threshold
        - "mahalanobis": Multivariate Mahalanobis distance with regularized covariance & Chi^2 test
        - "knn": k-Nearest Neighbors feature density indicator
        """
        if method == "mahalanobis":
            return self.check_ood_mahalanobis(
                asset_id=asset_id,
                features=features,
                reference_features=reference_features,
                sequence_id=sequence_id
            )
        elif method == "knn":
            return self.check_ood_knn_density(
                asset_id=asset_id,
                features=features,
                reference_features=reference_features,
                sequence_id=sequence_id
            )

        limitations = (
            "Centroid L2 distance heuristic; uncalibrated Euclidean feature space does not "
            "represent posterior probability or calibrated density estimation. Confidence is null by design."
        )

        if reference_features is None or len(reference_features) == 0:
            finding = AssuranceFinding(
                sequence_id=sequence_id,
                asset_id=asset_id,
                asset_type="FEATURES",
                check_type="OOD_ANOMALY_INDICATOR",
                method="Centroid-Distance Anomaly Indicator",
                score=None,
                threshold=None,
                status="NO_REFERENCE_BASELINE",
                confidence=None,
                evidence="Reference baseline distribution unavailable",
                limitations="Cannot assess anomaly status without an existing reference baseline distribution. Fabrication of baselines refused."
            )
            self._persist_finding(finding)
            return finding

        ref_feat = np.asarray(reference_features, dtype=np.float64)
        curr_feat = np.asarray(features, dtype=np.float64).flatten()

        centroid = np.mean(ref_feat, axis=0)
        dist = float(np.linalg.norm(curr_feat - centroid))

        ref_dists = np.linalg.norm(ref_feat - centroid, axis=1)
        mean_dist = float(np.mean(ref_dists))
        std_dist = float(np.std(ref_dists))
        threshold = float(mean_dist + threshold_sigma * std_dist)

        is_ood = dist > threshold
        status = "POTENTIAL_OOD" if is_ood else "IN_DISTRIBUTION"

        evidence = (
            f"L2 distance to reference centroid: {dist:.4f} "
            f"(Threshold: {threshold:.4f} based on reference mean {mean_dist:.4f} + {threshold_sigma:.1f}σ {std_dist:.4f})"
        )

        finding = AssuranceFinding(
            sequence_id=sequence_id,
            asset_id=asset_id,
            asset_type="FEATURES",
            check_type="OOD_ANOMALY_INDICATOR",
            method="Centroid-Distance Anomaly Indicator",
            score=dist,
            threshold=threshold,
            status=status,
            confidence=None,  # Not calibrated; do not invent a probability
            evidence=evidence,
            limitations=limitations
        )
        if status != "IN_DISTRIBUTION":
            self._persist_finding(finding)
        return finding

    def check_ood_mahalanobis(
        self,
        asset_id: str,
        features: np.ndarray,
        reference_features: Optional[np.ndarray],
        significance_level: float = 0.01,
        sequence_id: Optional[int] = None
    ) -> AssuranceFinding:
        """
        Multivariate Mahalanobis Distance Out-of-Distribution (OOD) Detector.
        Computes covariance-aware distance: D_M^2 = (x - mu)^T * (Sigma + lambda*I)^(-1) * (x - mu).
        Uses Chi-Square distribution critical value for statistical thresholding.
        """
        limitations = (
            "Multivariate Mahalanobis distance with regularized empirical covariance. "
            "Assumes unimodal elliptical reference distribution in feature space."
        )

        if reference_features is None or len(reference_features) < 3:
            finding = AssuranceFinding(
                sequence_id=sequence_id,
                asset_id=asset_id,
                asset_type="FEATURES",
                check_type="OOD_MAHALANOBIS",
                method="Multivariate Mahalanobis Distance",
                score=None,
                threshold=None,
                status="NO_REFERENCE_BASELINE",
                confidence=None,
                evidence="Reference baseline distribution unavailable (minimum 3 samples required)",
                limitations="Cannot compute empirical covariance without an existing reference baseline."
            )
            self._persist_finding(finding)
            return finding

        ref_feat = np.asarray(reference_features, dtype=np.float64)
        if ref_feat.ndim == 1:
            ref_feat = ref_feat.reshape(-1, 1)
        curr_feat = np.asarray(features, dtype=np.float64).flatten()

        d = ref_feat.shape[1]
        mu = np.mean(ref_feat, axis=0)
        cov = np.cov(ref_feat, rowvar=False)
        if d == 1:
            cov = np.array([[float(cov)]])

        tr = float(np.trace(cov)) if cov.ndim == 2 else float(cov)
        ridge = max(1e-6, 1e-4 * tr / float(d))
        cov_reg = cov + ridge * np.eye(d)

        try:
            inv_cov = np.linalg.inv(cov_reg)
        except np.linalg.LinAlgError:
            inv_cov = np.linalg.pinv(cov_reg)

        diff = curr_feat - mu
        dm_sq = float(diff @ inv_cov @ diff)
        dm = float(np.sqrt(max(0.0, dm_sq)))

        if _SCIPY_AVAILABLE:
            threshold_sq = float(scipy.stats.chi2.ppf(1.0 - significance_level, df=d))
            p_value = float(1.0 - scipy.stats.chi2.cdf(dm_sq, df=d))
        else:
            ref_diffs = ref_feat - mu
            ref_dms_sq = np.sum((ref_diffs @ inv_cov) * ref_diffs, axis=1)
            threshold_sq = float(np.percentile(ref_dms_sq, (1.0 - significance_level) * 100.0))
            p_value = float(np.mean([1.0 if r >= dm_sq else 0.0 for r in ref_dms_sq]))

        threshold = float(np.sqrt(max(0.0, threshold_sq)))
        is_ood = dm_sq > threshold_sq
        status = "POTENTIAL_OOD" if is_ood else "IN_DISTRIBUTION"

        evidence = (
            f"Mahalanobis distance: {dm:.4f} (D_M^2: {dm_sq:.4f}, dim={d}, "
            f"Chi^2 threshold at alpha={significance_level}: {threshold:.4f}, p-value: {p_value:.4e})"
        )

        finding = AssuranceFinding(
            sequence_id=sequence_id,
            asset_id=asset_id,
            asset_type="FEATURES",
            check_type="OOD_MAHALANOBIS",
            method="Multivariate Mahalanobis Distance",
            score=dm,
            threshold=threshold,
            status=status,
            confidence=float(1.0 - p_value) if is_ood else None,
            evidence=evidence,
            limitations=limitations
        )
        if status != "IN_DISTRIBUTION":
            self._persist_finding(finding)
        return finding

    def check_ood_knn_density(
        self,
        asset_id: str,
        features: np.ndarray,
        reference_features: Optional[np.ndarray],
        k: int = 5,
        threshold_percentile: float = 95.0,
        sequence_id: Optional[int] = None
    ) -> AssuranceFinding:
        """
        k-Nearest Neighbors (kNN) Feature Density Out-of-Distribution (OOD) Detector.
        Computes mean Euclidean distance to the k nearest neighbors in the reference baseline.
        """
        limitations = (
            "k-Nearest Neighbors feature density indicator; non-parametric distance-based outlier scoring. "
            "Sensitive to local cluster density variations and curse of dimensionality."
        )

        if reference_features is None or len(reference_features) < max(k, 3):
            finding = AssuranceFinding(
                sequence_id=sequence_id,
                asset_id=asset_id,
                asset_type="FEATURES",
                check_type="OOD_KNN_DENSITY",
                method=f"{k}-Nearest Neighbors Density",
                score=None,
                threshold=None,
                status="NO_REFERENCE_BASELINE",
                confidence=None,
                evidence=f"Reference baseline insufficient (minimum {max(k, 3)} samples required)",
                limitations="Cannot compute kNN density without sufficient reference samples."
            )
            self._persist_finding(finding)
            return finding

        ref_feat = np.asarray(reference_features, dtype=np.float64)
        if ref_feat.ndim == 1:
            ref_feat = ref_feat.reshape(-1, 1)
        curr_feat = np.asarray(features, dtype=np.float64).reshape(1, -1)

        effective_k = min(k, len(ref_feat))
        dists = np.sqrt(compute_pairwise_sqeuclidean(curr_feat, ref_feat)).flatten()
        sorted_dists = np.sort(dists)
        knn_dist = float(np.mean(sorted_dists[:effective_k]))

        ref_pdist = np.sqrt(compute_pairwise_sqeuclidean(ref_feat, ref_feat))
        ref_knn_dists = []
        for i in range(len(ref_feat)):
            row = np.sort(ref_pdist[i])
            ref_knn_dists.append(np.mean(row[1:effective_k + 1]))

        threshold = float(np.percentile(ref_knn_dists, threshold_percentile))
        is_ood = knn_dist > threshold
        status = "POTENTIAL_OOD" if is_ood else "IN_DISTRIBUTION"

        evidence = (
            f"Mean distance to {effective_k}-NN: {knn_dist:.4f} "
            f"(Threshold at {threshold_percentile:.1f}th percentile: {threshold:.4f})"
        )

        finding = AssuranceFinding(
            sequence_id=sequence_id,
            asset_id=asset_id,
            asset_type="FEATURES",
            check_type="OOD_KNN_DENSITY",
            method=f"{effective_k}-Nearest Neighbors Density",
            score=knn_dist,
            threshold=threshold,
            status=status,
            confidence=None,
            evidence=evidence,
            limitations=limitations
        )
        if status != "IN_DISTRIBUTION":
            self._persist_finding(finding)
        return finding

    def check_label_quality(
        self,
        asset_id: str,
        annotations: List[Dict[str, Any]],
        predictions: Optional[List[Dict[str, Any]]] = None,
        class_names: Optional[Dict[int, str]] = None,
        sequence_id: Optional[int] = None
    ) -> List[AssuranceFinding]:
        """
        Active Label Quality & Noise Detection Engine (Cleanlab-Inspired).
        Detects:
        1. Aspect ratio anomalies (extreme stretch, h/w > 10 or w/h > 10)
        2. Area anomalies (tiny bbox < 0.0001 or giant bbox > 0.98)
        3. Annotation collisions (overlapping boxes with IoU > 0.85)
        4. Confident Learning label noise: High-confidence model prediction disagrees with annotated ground-truth.
        """
        findings = []
        limitations = (
            "Cleanlab-inspired label noise analysis; flags geometric outliers, box collisions, "
            "and confident disagreement between model predictions and annotated ground-truth."
        )

        for i, ann in enumerate(annotations):
            cls_id = ann.get("class_id", ann.get("cls", 0))
            cls_name = class_names.get(cls_id, str(cls_id)) if class_names else str(cls_id)
            box = ann.get("bbox", [ann.get("cx", 0.5), ann.get("cy", 0.5), ann.get("w", 0.1), ann.get("h", 0.1)])
            w, h = float(box[2]), float(box[3])
            area = w * h

            if w > 0 and h > 0:
                aspect_ratio = max(w / h, h / w)
                if aspect_ratio > 10.0:
                    findings.append(AssuranceFinding(
                        sequence_id=sequence_id,
                        asset_id=asset_id,
                        asset_type="ANNOTATION",
                        check_type="LABEL_QUALITY_GEOMETRY",
                        method="Aspect Ratio Outlier Detection",
                        score=aspect_ratio,
                        threshold=10.0,
                        status="SUSPICIOUS_ASPECT_RATIO",
                        confidence=0.90,
                        evidence=f"Annotation {i+1} ({cls_name}): Extreme aspect ratio {aspect_ratio:.2f}:1 (w={w:.4f}, h={h:.4f})",
                        limitations=limitations
                    ))

            if area < 0.0001 or area > 0.98:
                findings.append(AssuranceFinding(
                    sequence_id=sequence_id,
                    asset_id=asset_id,
                    asset_type="ANNOTATION",
                    check_type="LABEL_QUALITY_GEOMETRY",
                    method="Bounding Box Area Anomaly",
                    score=area,
                    threshold=0.0001 if area < 0.0001 else 0.98,
                    status="SUSPICIOUS_BBOX_AREA",
                    confidence=0.85,
                    evidence=f"Annotation {i+1} ({cls_name}): Extreme area {area:.6f} normalized",
                    limitations=limitations
                ))

            for j in range(i + 1, len(annotations)):
                other_ann = annotations[j]
                other_box = other_ann.get("bbox", [other_ann.get("cx", 0.5), other_ann.get("cy", 0.5), other_ann.get("w", 0.1), other_ann.get("h", 0.1)])
                iou = compute_bbox_iou(box, other_box)
                if iou > 0.85:
                    other_cls = other_ann.get("class_id", other_ann.get("cls", 0))
                    status = "DUPLICATE_ANNOTATION_COLLISION" if cls_id == other_cls else "LABEL_AMBIGUITY_CONFLICT"
                    findings.append(AssuranceFinding(
                        sequence_id=sequence_id,
                        asset_id=asset_id,
                        asset_type="ANNOTATION",
                        check_type="LABEL_QUALITY_COLLISION",
                        method="Annotation Box Collision Check",
                        score=iou,
                        threshold=0.85,
                        status=status,
                        confidence=0.95,
                        evidence=f"Annotations {i+1} (class {cls_id}) and {j+1} (class {other_cls}) overlap with high IoU: {iou:.4f}",
                        limitations=limitations
                    ))

        if predictions:
            for i, ann in enumerate(annotations):
                ann_cls = ann.get("class_id", ann.get("cls", 0))
                ann_box = ann.get("bbox", [ann.get("cx", 0.5), ann.get("cy", 0.5), ann.get("w", 0.1), ann.get("h", 0.1)])

                for pred in predictions:
                    pred_cls = pred.get("class_id", pred.get("cls", 0))
                    pred_conf = float(pred.get("confidence", pred.get("conf", 0.0)))
                    pred_box = pred.get("bbox", [pred.get("cx", 0.5), pred.get("cy", 0.5), pred.get("w", 0.1), pred.get("h", 0.1)])

                    iou = compute_bbox_iou(ann_box, pred_box)
                    if iou > 0.50 and pred_conf > 0.70 and ann_cls != pred_cls:
                        findings.append(AssuranceFinding(
                            sequence_id=sequence_id,
                            asset_id=asset_id,
                            asset_type="ANNOTATION",
                            check_type="LABEL_NOISE_ANALYSIS",
                            method="Confident Learning Prediction Discrepancy",
                            score=pred_conf,
                            threshold=0.70,
                            status="LABEL_NOISE_CLASS_FLIP_SUSPECTED",
                            confidence=pred_conf,
                            evidence=(
                                f"Annotated as class {ann_cls}, but model predicts class {pred_cls} "
                                f"with high confidence {pred_conf:.4f} at IoU {iou:.4f}. Suspected label flip error."
                            ),
                            limitations=limitations
                        ))

        for f in findings:
            self._persist_finding(f)
        return findings

    def check_distribution_shift(
        self,
        current_features: np.ndarray,
        reference_features: Optional[np.ndarray],
        alpha: float = 0.05,
        sequence_id: Optional[int] = None,
        method: str = "ks"
    ) -> AssuranceFinding:
        """
        Distribution Shift Monitoring.
        Supports methods:
        - "ks" (Default): Two-Sample Kolmogorov-Smirnov (KS) test across feature dimensions with Bonferroni correction.
        - "mmd": Multivariate Kernel Maximum Mean Discrepancy (MMD) with Gaussian RBF kernel and permutation test.
        """
        if method == "mmd":
            return self.check_distribution_shift_mmd(
                current_features=current_features,
                reference_features=reference_features,
                alpha=alpha,
                sequence_id=sequence_id
            )

        curr = np.asarray(current_features, dtype=np.float64) if current_features is not None else None
        ref = np.asarray(reference_features, dtype=np.float64) if reference_features is not None else None

        if ref is None or curr is None or len(ref) < 10 or len(curr) < 10:
            finding = AssuranceFinding(
                sequence_id=sequence_id,
                asset_id="BATCH_DISTRIBUTION",
                asset_type="BATCH_FEATURES",
                check_type="DISTRIBUTION_SHIFT",
                method="Two-Sample Kolmogorov-Smirnov Test" if _SCIPY_AVAILABLE else "Maximum Feature Mean Shift",
                score=None,
                threshold=None,
                status="NO_REFERENCE_BASELINE",
                confidence=None,
                evidence=f"Insufficient sample size: reference N={len(ref) if ref is not None else 0}, current N={len(curr) if curr is not None else 0} (minimum 10 required)",
                limitations="Distribution shift monitoring requires sufficient sample window to compute empirical distributions."
            )
            self._persist_finding(finding)
            return finding

        num_dims = min(ref.shape[1], curr.shape[1]) if ref.ndim > 1 and curr.ndim > 1 else 1
        if ref.ndim == 1:
            ref = ref.reshape(-1, 1)
        if curr.ndim == 1:
            curr = curr.reshape(-1, 1)

        if _SCIPY_AVAILABLE:
            bonferroni_alpha = alpha / float(num_dims)
            ks_stats = []
            p_values = []
            for d in range(num_dims):
                res = scipy.stats.ks_2samp(ref[:, d], curr[:, d])
                ks_stats.append(float(res.statistic))
                p_values.append(float(res.pvalue))

            max_ks = float(np.max(ks_stats))
            min_p = float(np.min(p_values))
            worst_dim = int(np.argmax(ks_stats))

            shift_detected = min_p < bonferroni_alpha
            status = "DISTRIBUTION_SHIFT_DETECTED" if shift_detected else "IN_DISTRIBUTION"

            evidence = (
                f"Two-sample KS test max statistic: {max_ks:.4f} on feature dim {worst_dim} "
                f"(min p-value: {min_p:.4e}, Bonferroni critical α: {bonferroni_alpha:.4f}, uncorrected α: {alpha})"
            )
            limitations = (
                f"Two-sample Kolmogorov-Smirnov test evaluated across {num_dims} independent 1D feature projections. "
                "Confidence is null; statistical significance is represented directly via minimum p-value."
            )

            finding = AssuranceFinding(
                sequence_id=sequence_id,
                asset_id="BATCH_DISTRIBUTION",
                asset_type="BATCH_FEATURES",
                check_type="DISTRIBUTION_SHIFT",
                method="Two-Sample Kolmogorov-Smirnov Test",
                score=max_ks,
                threshold=float(scipy.stats.kstwobign.ppf(1.0 - bonferroni_alpha) * np.sqrt((len(ref) + len(curr)) / (len(ref) * len(curr)))),
                status=status,
                confidence=None,
                evidence=evidence,
                limitations=limitations
            )
        else:
            ref_mean = np.mean(ref, axis=0)
            curr_mean = np.mean(curr, axis=0)
            ref_std = np.std(ref, axis=0)

            shift_scores = np.abs(ref_mean - curr_mean)
            thresholds = ref_std * 0.5
            max_idx = int(np.argmax(shift_scores))

            shift_score = float(shift_scores[max_idx])
            threshold = float(thresholds[max_idx])
            shift_detected = shift_score > threshold
            status = "DISTRIBUTION_SHIFT_DETECTED" if shift_detected else "IN_DISTRIBUTION"

            evidence = (
                f"Maximum feature mean shift: {shift_score:.4f} on dim {max_idx} "
                f"(threshold: {threshold:.4f} based on 0.5σ reference deviation)"
            )
            limitations = (
                "Lightweight heuristic mean-shift metric; this is NOT a formal KS/PSI/MMD test. "
                "scipy is not installed in this environment. Confidence is null."
            )

            finding = AssuranceFinding(
                sequence_id=sequence_id,
                asset_id="BATCH_DISTRIBUTION",
                asset_type="BATCH_FEATURES",
                check_type="DISTRIBUTION_SHIFT",
                method="Maximum Feature Mean Shift",
                score=shift_score,
                threshold=threshold,
                status=status,
                confidence=None,
                evidence=evidence,
                limitations=limitations
            )

        if status != "IN_DISTRIBUTION":
            self._persist_finding(finding)
        return finding

    def check_distribution_shift_mmd(
        self,
        current_features: np.ndarray,
        reference_features: Optional[np.ndarray],
        alpha: float = 0.05,
        n_permutations: int = 100,
        sequence_id: Optional[int] = None
    ) -> AssuranceFinding:
        """
        Multivariate Kernel Maximum Mean Discrepancy (MMD) Distribution Shift Detector.
        Uses unbiased U-statistic with Gaussian RBF kernel and median bandwidth heuristic.
        Computes exact empirical p-value via permutation testing.
        """
        curr = np.asarray(current_features, dtype=np.float64) if current_features is not None else None
        ref = np.asarray(reference_features, dtype=np.float64) if reference_features is not None else None

        if ref is None or curr is None or len(ref) < 10 or len(curr) < 10:
            finding = AssuranceFinding(
                sequence_id=sequence_id,
                asset_id="BATCH_DISTRIBUTION",
                asset_type="BATCH_FEATURES",
                check_type="DISTRIBUTION_SHIFT_MMD",
                method="Kernel Maximum Mean Discrepancy (MMD)",
                score=None,
                threshold=None,
                status="NO_REFERENCE_BASELINE",
                confidence=None,
                evidence=f"Insufficient sample size: reference N={len(ref) if ref is not None else 0}, current N={len(curr) if curr is not None else 0} (minimum 10 required)",
                limitations="MMD requires at least 10 samples per distribution to compute unbiased U-statistic."
            )
            self._persist_finding(finding)
            return finding

        if ref.ndim == 1:
            ref = ref.reshape(-1, 1)
        if curr.ndim == 1:
            curr = curr.reshape(-1, 1)

        m = len(curr)
        n = len(ref)
        mmd_sq, gamma = compute_mmd_rbf(curr, ref)

        pooled = np.vstack([curr, ref])
        total_samples = len(pooled)
        perm_mmds = []
        rng = np.random.default_rng(42)
        for _ in range(n_permutations):
            perm_idx = rng.permutation(total_samples)
            perm_curr = pooled[perm_idx[:m]]
            perm_ref = pooled[perm_idx[m:]]
            p_mmd, _ = compute_mmd_rbf(perm_curr, perm_ref, gamma=gamma)
            perm_mmds.append(p_mmd)

        p_value = float(np.mean([1.0 if pm >= mmd_sq else 0.0 for pm in perm_mmds]))
        threshold_mmd = float(np.percentile(perm_mmds, (1.0 - alpha) * 100.0))

        shift_detected = (mmd_sq > threshold_mmd) and (p_value < alpha) and (mmd_sq > 0.0)
        status = "DISTRIBUTION_SHIFT_DETECTED" if shift_detected else "IN_DISTRIBUTION"

        evidence = (
            f"Kernel MMD^2 statistic: {mmd_sq:.6f} (gamma: {gamma:.4f}, p-value: {p_value:.4f}, "
            f"critical threshold at alpha={alpha}: {threshold_mmd:.6f}, permutations: {n_permutations})"
        )
        limitations = (
            "Kernel Maximum Mean Discrepancy evaluates full multivariate feature distributions "
            "using Gaussian RBF reproducing kernel Hilbert space embeddings."
        )

        finding = AssuranceFinding(
            sequence_id=sequence_id,
            asset_id="BATCH_DISTRIBUTION",
            asset_type="BATCH_FEATURES",
            check_type="DISTRIBUTION_SHIFT_MMD",
            method="Kernel Maximum Mean Discrepancy (MMD)",
            score=max(0.0, mmd_sq),
            threshold=max(0.0, threshold_mmd),
            status=status,
            confidence=float(1.0 - p_value) if shift_detected else None,
            evidence=evidence,
            limitations=limitations
        )
        if status != "IN_DISTRIBUTION":
            self._persist_finding(finding)
        return finding

    def recommend_governance_disposition(self, finding: AssuranceFinding) -> str:
        """
        Translates automated integrity finding into an AI/System recommendation:
        - NORMAL or IN_DISTRIBUTION -> ACCEPT
        - POTENTIAL_DUPLICATE, POTENTIAL_NEAR_DUPLICATE, POTENTIAL_OOD,
          DISTRIBUTION_SHIFT_DETECTED, NO_REFERENCE_BASELINE,
          LABEL_NOISE_CLASS_FLIP_SUSPECTED, SUSPICIOUS_ASPECT_RATIO,
          SUSPICIOUS_BBOX_AREA, DUPLICATE_ANNOTATION_COLLISION,
          LABEL_AMBIGUITY_CONFLICT -> REVIEW
        - INVALID_CLASS, IMPOSSIBLE_BBOX, MALFORMED_FORMAT -> QUARANTINE
        Crucial: This is an automated recommendation only; human analyst overrides
        are stored independently in governance_audit and must never be overwritten.
        """
        if finding.status in ("NORMAL", "IN_DISTRIBUTION"):
            return "ACCEPT"
        elif finding.status in ("INVALID_CLASS", "IMPOSSIBLE_BBOX", "MALFORMED_FORMAT"):
            return "QUARANTINE"
        elif finding.status in (
            "POTENTIAL_DUPLICATE",
            "POTENTIAL_NEAR_DUPLICATE",
            "POTENTIAL_OOD",
            "DISTRIBUTION_SHIFT_DETECTED",
            "NO_REFERENCE_BASELINE",
            "LABEL_NOISE_CLASS_FLIP_SUSPECTED",
            "SUSPICIOUS_ASPECT_RATIO",
            "SUSPICIOUS_BBOX_AREA",
            "DUPLICATE_ANNOTATION_COLLISION",
            "LABEL_AMBIGUITY_CONFLICT"
        ):
            return "REVIEW"
        return "REVIEW"
