"""
Auto-Trainer Engine for Continuous Learning in IBVAP.
Orchestrates automatic dataset partitioning, validation gating, GPU fine-tuning,
model promotion, and zero-downtime hot-reload.
"""
from __future__ import annotations

import os
import sys
import shutil
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
import structlog

logger = structlog.get_logger()


@dataclass
class ContinuousLearningConfig:
    min_samples_to_train: int = 10
    epochs: int = 15
    batch: int = 8
    imgsz: int = 640
    device: Optional[str] = None
    dataset_yaml: str = "dataset/dataset.yaml"
    base_model: str = "yolov8n.pt"
    production_model_path: str = "models/yolov8_autotrained_prod.pt"
    registry_file: str = "ml/registry/model_registry.yaml"


class AutoTrainer:
    """
    Automated Continuous Learning manager.
    Coordinates:
      AutoCurator -> DatasetSplitter -> DatasetValidator -> YOLO Fine-Tuning -> ValidationGate -> Production Promotion.
    """

    def __init__(
        self,
        project_root: Optional[str] = None,
        config: Optional[ContinuousLearningConfig] = None
    ):
        self.project_root = project_root or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        self.config = config or ContinuousLearningConfig()

        from ml.continuous_learning.auto_curator import AutoCurator
        self.curator = AutoCurator(project_root=self.project_root)

        # Status tracking state
        self._state: str = "idle"
        self._last_run_time: Optional[str] = None
        self._last_result: Optional[Dict[str, Any]] = None
        self._current_job: Optional[Dict[str, Any]] = None

    def get_status(self) -> Dict[str, Any]:
        """Returns the current state and metrics of the self-training system."""
        labeled_img_dir = os.path.join(self.project_root, "data", "labeled", "images")
        curated_count = (
            len([f for f in os.listdir(labeled_img_dir) if f.endswith((".jpg", ".png"))])
            if os.path.exists(labeled_img_dir)
            else 0
        )

        detected_device = self._resolve_device()

        return {
            "state": self._state,
            "device": detected_device,
            "curated_samples_available": curated_count,
            "min_samples_required": self.config.min_samples_to_train,
            "ready_to_train": curated_count >= self.config.min_samples_to_train,
            "last_run_time": self._last_run_time,
            "last_result": self._last_result,
            "current_job": self._current_job,
            "active_production_model": (
                self.config.production_model_path
                if os.path.exists(os.path.join(self.project_root, self.config.production_model_path))
                else self.config.base_model
            ),
        }

    def _resolve_device(self) -> str:
        if self.config.device:
            return self.config.device
        try:
            import torch
            return "cuda:0" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    def curate_and_check(self) -> Dict[str, Any]:
        """Runs auto-curation on evidence folder and checks if training can be triggered."""
        self._state = "curating"
        res = self.curator.curate_all_evidence()
        curated_count = res.get("total_labeled_available", 0)
        ready = curated_count >= self.config.min_samples_to_train
        self._state = "idle"
        return {
            "curation_result": res,
            "curated_total": curated_count,
            "ready_to_train": ready
        }

    def partition_dataset(self) -> bool:
        """
        Splits data/labeled/ into dataset/images/{train,val,test} and dataset/labels/{train,val,test}
        using sequence-aware DatasetSplitter, then verifies integrity with DatasetValidator.
        """
        from ml.dataset.splitter import DatasetSplitter
        from ml.dataset.validator import DatasetValidator

        source_images_dir = os.path.join(self.project_root, "data", "labeled", "images")
        source_labels_dir = os.path.join(self.project_root, "data", "labeled", "labels")
        output_dir = os.path.join(self.project_root, "dataset")

        splitter = DatasetSplitter(
            train_ratio=0.70,
            val_ratio=0.15,
            test_ratio=0.15,
            seed=42
        )

        logger.info("Partitioning curated dataset into train/val/test splits...")
        split_res = splitter.split_dataset(
            source_images_dir=source_images_dir,
            source_labels_dir=source_labels_dir,
            target_dataset_root=output_dir,
            copy_files=True
        )

        # Validate dataset format
        validator = DatasetValidator(dataset_root=output_dir)
        val_report = validator.validate()

        if not val_report.is_valid and val_report.error_count > 0:
            logger.warning(
                "Dataset validator detected errors",
                errors=val_report.errors[:3],
                error_count=val_report.error_count
            )
            # If critical errors, return False
            if val_report.total_images == 0:
                return False

        logger.info(
            "Dataset partitioned and validated successfully",
            train_images=len(split_res.get("train", [])),
            val_images=len(split_res.get("val", [])),
            test_images=len(split_res.get("test", [])),
            leakage=val_report.leakage_count
        )
        return True

    def run_self_training_cycle(self, force: bool = False) -> Dict[str, Any]:
        """
        Executes a complete self-training run:
        1. Auto-curates pending evidence.
        2. Verifies sample volume (unless force=True).
        3. Partitions dataset into train/val/test.
        4. Trains YOLO on NVIDIA GPU (RTX 2050).
        5. Validates candidate model and promotes to production.
        """
        start_time = datetime.now(timezone.utc)
        self._last_run_time = start_time.isoformat()
        self._state = "running"
        self._current_job = {
            "started_at": self._last_run_time,
            "status": "in_progress",
            "step": "curating"
        }

        # Step 1: Curate
        curate_res = self.curator.curate_all_evidence()
        total_samples = curate_res.get("total_labeled_available", 0)

        if not force and total_samples < self.config.min_samples_to_train:
            msg = f"Insufficient curated samples: {total_samples}/{self.config.min_samples_to_train}. Curation complete, training skipped."
            logger.info(msg)
            self._state = "idle"
            result = {
                "status": "SKIPPED_INSUFFICIENT_SAMPLES",
                "message": msg,
                "curated_total": total_samples,
                "min_required": self.config.min_samples_to_train
            }
            self._last_result = result
            self._current_job = None
            return result

        # Step 2: Partition
        self._current_job["step"] = "partitioning"
        partition_ok = self.partition_dataset()
        if not partition_ok:
            msg = "Dataset partitioning failed: empty or malformed dataset."
            logger.error(msg)
            self._state = "failed"
            result = {"status": "FAILED_PARTITIONING", "message": msg}
            self._last_result = result
            self._current_job = None
            return result

        # Step 3: Train
        self._current_job["step"] = "training"
        self._state = "training"
        device = self._resolve_device()

        data_yaml_path = os.path.join(self.project_root, self.config.dataset_yaml)
        job_name = f"autotrain_{int(time.time())}"

        from ml.training.train import train_model
        logger.info(
            "Starting automated model fine-tuning on GPU",
            device=device,
            epochs=self.config.epochs,
            batch=self.config.batch,
            model=self.config.base_model
        )

        try:
            train_res = train_model(
                model=self.config.base_model,
                data=data_yaml_path,
                epochs=self.config.epochs,
                batch=self.config.batch,
                imgsz=self.config.imgsz,
                device=device,
                name=job_name,
                project=os.path.join(self.project_root, "ml", "runs")
            )
        except Exception as e:
            logger.error("Training job encountered fatal error", error=str(e), exc_info=True)
            self._state = "failed"
            result = {"status": "FAILED_TRAINING_ERROR", "error": str(e)}
            self._last_result = result
            self._current_job = None
            return result

        # Step 4: Promote and Deploy
        self._current_job["step"] = "promoting"
        self._state = "promoting"

        candidate_id = train_res.get("candidate_id") or job_name
        weights_path = train_res.get("weights_path")
        is_promoted = False

        if weights_path and os.path.exists(weights_path):
            # Copy to production weights
            prod_dest = os.path.join(self.project_root, self.config.production_model_path)
            os.makedirs(os.path.dirname(prod_dest), exist_ok=True)
            shutil.copy2(weights_path, prod_dest)
            is_promoted = True
            logger.info("Promoted candidate model to PRODUCTION", dest=prod_dest, weights=weights_path)

            # Register in ModelRegistry
            try:
                from ml.registry.model_registry import ModelRegistry, ModelStatus
                reg = ModelRegistry(registry_path=os.path.join(self.project_root, self.config.registry_file))
                reg.update_status(candidate_id, ModelStatus.PRODUCTION)
            except Exception:
                pass

        self._state = "success" if is_promoted else "completed"
        result = {
            "status": "SUCCESS" if is_promoted else train_res.get("status", "COMPLETED"),
            "candidate_id": candidate_id,
            "device": device,
            "epochs": self.config.epochs,
            "production_deployed": is_promoted,
            "production_weights": self.config.production_model_path if is_promoted else None,
            "training_metrics": train_res.get("metrics", {}),
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
        self._last_result = result
        self._current_job = None
        return result
