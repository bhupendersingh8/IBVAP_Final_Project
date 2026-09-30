"""
Model Selector for IBVAP Ingestion & Inference Workers.
Resolves model weights from registry or environment configuration.
Supports:
- 'production': Active production model from registry (fallback to 'yolov8n.pt')
- 'candidate': Latest validated candidate model
- '<model_id>:<version>': Specific pinned model
- '<file_path>': Direct file path
Default remains 'yolov8n.pt' with zero regression.
"""
from __future__ import annotations

import os
from typing import Tuple, Dict, Any, Optional
import structlog
from ml.registry.model_registry import ModelRegistry, ModelStatus

logger = structlog.get_logger()


class ModelSelector:
    """
    Resolves detector weights dynamically while maintaining safe fallbacks.
    """

    def __init__(
        self,
        selection_mode: Optional[str] = None,
        registry_path: Optional[str] = None,
        fallback_model: str = "yolov8n.pt",
    ):
        self.selection_mode = (
            selection_mode
            or os.environ.get("IBVAP_MODEL_SELECTION")
            or "production"
        )
        self.fallback_model = fallback_model
        self.registry = ModelRegistry(registry_file=registry_path)

    def resolve(self) -> Tuple[str, str, Dict[str, Any]]:
        """
        Returns: (model_path: str, model_version: str, metadata: Dict)
        """
        mode = self.selection_mode.strip()

        # Direct file path check
        if os.path.isfile(mode):
            logger.info("ModelSelector resolved direct file path", path=mode)
            return mode, "custom", {"source": "direct_path", "path": mode}

        # Production model
        if mode.lower() == "production":
            prod_meta = self.registry.get_production_model()
            if prod_meta and os.path.exists(prod_meta.artifact_path):
                logger.info(
                    "ModelSelector resolved active production model",
                    model_id=prod_meta.model_id,
                    version=prod_meta.model_version,
                )
                return prod_meta.artifact_path, prod_meta.model_version, prod_meta.to_dict()

            logger.info("No verified production model file found in registry; using standard baseline", fallback=self.fallback_model)
            return self.fallback_model, "1.0.0", {"source": "builtin_baseline", "model": self.fallback_model}

        # Candidate model
        if mode.lower() == "candidate":
            cand_meta = self.registry.get_active_candidate()
            if cand_meta and os.path.exists(cand_meta.artifact_path):
                logger.info(
                    "ModelSelector resolved active candidate model",
                    model_id=cand_meta.model_id,
                    version=cand_meta.model_version,
                )
                return cand_meta.artifact_path, cand_meta.model_version, cand_meta.to_dict()

            logger.warning("No active candidate model file found; falling back to baseline", fallback=self.fallback_model)
            return self.fallback_model, "1.0.0", {"source": "fallback_baseline", "model": self.fallback_model}

        # Specific model_id or model_id:version
        parts = mode.split(":")
        mid = parts[0]
        mver = parts[1] if len(parts) > 1 else None
        specific = self.registry.get_model(mid, mver)
        if specific and os.path.exists(specific.artifact_path):
            return specific.artifact_path, specific.model_version, specific.to_dict()

        logger.warning(
            "Specified model not found in registry; defaulting to baseline",
            requested=mode,
            fallback=self.fallback_model,
        )
        return self.fallback_model, "1.0.0", {"source": "fallback_baseline", "requested": mode}
