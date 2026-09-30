"""
Reproducible Training Entry Point for IBVAP.
Supports configurable base models, datasets, hyperparameters, and device targets.
Emits candidate ModelMetadata into ModelRegistry upon successful execution.
Enforces validation gate checks before promotion.
"""
from __future__ import annotations

import os
import sys
import argparse
from datetime import datetime, timezone
import yaml
import structlog

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.registry.model_registry import ModelRegistry, ModelMetadata, ModelStatus
from ml.evaluation.validation_gate import ValidationGate, GateCriteria
from ml.adapters.mlflow_adapter import MLflowAdapter
from ml.adapters.dvc_adapter import DVCAdapter

logger = structlog.get_logger()


def train_model(
    model: str = "yolov8n.pt",
    data: str = "dataset/dataset.yaml",
    epochs: int = 50,
    batch: int = 16,
    imgsz: int = 640,
    device: str = "cpu",
    seed: int = 42,
    project: str = "ml/runs",
    name: str = "ibvap_candidate",
    dataset_version: str = "v1.0.0",
) -> Dict:
    """
    Executes reproducible model training.
    """
    logger.info(
        "Initiating IBVAP training run",
        model=model,
        dataset=data,
        epochs=epochs,
        batch=batch,
        device=device,
        seed=seed,
    )

    # 1. Verify dataset readiness
    if not os.path.isfile(data):
        raise FileNotFoundError(f"Dataset config YAML not found: {data}")

    with open(data, "r", encoding="utf-8") as f:
        data_cfg = yaml.safe_load(f)

    # Check that training directory exists and has images
    d_path = data_cfg.get("path", "")
    train_rel = data_cfg.get("train", "")
    train_dir = os.path.join(d_path, train_rel) if not os.path.isabs(train_rel) else train_rel

    image_files = []
    if os.path.isdir(train_dir):
        image_files = [f for f in os.listdir(train_dir) if f.lower().endswith((".jpg", ".png", ".jpeg"))]

    if not image_files:
        msg = f"Cannot train model: No images found in training split at {train_dir}. Anti-hallucination guard prevented execution."
        logger.error(msg)
        return {
            "status": "ABORTED_EMPTY_DATASET",
            "message": msg,
            "training_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # 2. Setup experiment tracking
    mlflow = MLflowAdapter(experiment_name="ibvap-training")
    mlflow.start_run(run_name=name)
    mlflow.log_param("base_model", model)
    mlflow.log_param("epochs", epochs)
    mlflow.log_param("batch", batch)
    mlflow.log_param("imgsz", imgsz)
    mlflow.log_param("device", device)
    mlflow.log_param("seed", seed)

    # 3. Execute training with Ultralytics
    from ultralytics import YOLO
    yolo_model = YOLO(model)
    results = yolo_model.train(
        data=data,
        epochs=epochs,
        batch=batch,
        imgsz=imgsz,
        device=device,
        seed=seed,
        project=project,
        name=name,
        verbose=True,
    )

    save_dir = str(results.save_dir) if hasattr(results, "save_dir") else os.path.join(project, name)
    best_weights = os.path.join(save_dir, "weights", "best.pt")

    # 4. Extract metrics
    metrics = {}
    if hasattr(results, "results_dict"):
        metrics = {
            "mAP50": float(results.results_dict.get("metrics/mAP50(B)", 0.0)),
            "mAP50_95": float(results.results_dict.get("metrics/mAP50-95(B)", 0.0)),
            "precision": float(results.results_dict.get("metrics/precision(B)", 0.0)),
            "recall": float(results.results_dict.get("metrics/recall(B)", 0.0)),
        }

    # 5. Validation Gate check
    gate = ValidationGate()
    passed, reasons = gate.evaluate(metrics)

    status = ModelStatus.VALIDATED if passed else ModelStatus.REJECTED

    # 6. Register Candidate in Registry
    registry = ModelRegistry()
    model_meta = ModelMetadata(
        model_id=name,
        model_version="1.0.0",
        dataset_version=dataset_version,
        training_config={
            "base_model": model,
            "epochs": epochs,
            "batch": batch,
            "imgsz": imgsz,
            "device": device,
            "seed": seed,
        },
        git_commit="training_run",
        training_timestamp=datetime.now(timezone.utc).isoformat(),
        classes=data_cfg.get("names", {0: "person", 1: "car", 2: "motorcycle", 3: "truck", 4: "bus"}),
        metrics=metrics,
        artifact_path=best_weights if os.path.isfile(best_weights) else model,
        status=status,
        notes=f"Gate evaluation: {'; '.join(reasons)}",
    )
    registry.register_model(model_meta)
    mlflow.end_run()

    return {
        "status": status.value,
        "model_id": name,
        "metrics": metrics,
        "gate_passed": passed,
        "reasons": reasons,
        "weights": best_weights,
    }
