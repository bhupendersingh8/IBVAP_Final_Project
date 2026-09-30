"""
MLflow adapter stub — PHASE 11.

Status: PLANNED
Install: pip install mlflow
Configure: set MLFLOW_TRACKING_URI environment variable

This stub is forward-compatible — replace method bodies with real MLflow calls
when a training run is ready. The interface is intentionally identical to MLflow's API.
"""
from __future__ import annotations
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MLflowAdapter:
    """
    Thin wrapper around MLflow for IBVAP experiment tracking.
    Currently a no-op stub. Activate by installing mlflow and setting MLFLOW_TRACKING_URI.
    """
    _available = False

    def __init__(self, tracking_uri: Optional[str] = None, experiment_name: str = "ibvap"):
        try:
            import mlflow  # type: ignore
            if tracking_uri:
                mlflow.set_tracking_uri(tracking_uri)
            mlflow.set_experiment(experiment_name)
            self._mlflow = mlflow
            self._available = True
            logger.info("MLflow adapter initialized", uri=tracking_uri)
        except ImportError:
            logger.warning("MLflow not installed — tracking disabled. Install: pip install mlflow")

    def log_metric(self, key: str, value: float, step: Optional[int] = None) -> None:
        if self._available:
            self._mlflow.log_metric(key, value, step=step)

    def log_param(self, key: str, value: Any) -> None:
        if self._available:
            self._mlflow.log_param(key, value)

    def log_model(self, model_path: str, artifact_path: str = "model") -> None:
        if self._available:
            self._mlflow.log_artifact(model_path, artifact_path)

    def start_run(self, run_name: Optional[str] = None):
        if self._available:
            return self._mlflow.start_run(run_name=run_name)
        return None

    def end_run(self) -> None:
        if self._available:
            self._mlflow.end_run()
