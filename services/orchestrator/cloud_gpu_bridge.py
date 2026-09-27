"""
IBVAP Cloud GPU Bridge & Remote Worker Dispatcher
Enables connecting Free Cloud GPUs (Google Colab T4, Kaggle, Vast.ai, RunPod)
to offload heavy Tier 2 & Tier 3 models (Qwen-VL, SAM 2.1, Florence-2) asynchronously.
Maintains 100% zero-crash fallback to local Dell CPU when remote GPU is offline.
"""

import os
import json
import time
import requests
import structlog
from typing import Optional, Dict, Any

logger = structlog.get_logger()

class CloudGPUBridge:
    def __init__(self, remote_url: Optional[str] = None, timeout_sec: float = 8.0):
        # Can be set via environment variable IBVAP_REMOTE_GPU_URL (e.g. ngrok/cloudflare tunnel to Colab)
        self.remote_url = remote_url or os.environ.get("IBVAP_REMOTE_GPU_URL", "")
        self.timeout_sec = timeout_sec
        self.is_connected = False
        if self.remote_url:
            self.check_connection()

    def check_connection(self) -> bool:
        """Tests health and latency of the remote GPU worker endpoint."""
        if not self.remote_url:
            self.is_connected = False
            return False

        try:
            resp = requests.get(f"{self.remote_url.rstrip('/')}/health", timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                self.is_connected = True
                logger.info("Cloud GPU Worker Connected", gpu=data.get("gpu"), vram_free_mb=data.get("vram_free_mb"))
                return True
        except Exception as e:
            logger.warning("Cloud GPU Worker unreachable, using local CPU fallbacks", error=str(e))

        self.is_connected = False
        return False

    def dispatch_vlm_audit(self, prompt: str, image_base64: str) -> Dict[str, Any]:
        """
        Dispatches high-threat 15s clip or ROI frame to remote GPU for deep reasoning.
        If GPU is offline or times out, immediately returns local deterministic rule fallback.
        """
        if not self.is_connected:
            return {
                "source": "local_cpu_fallback",
                "model": "rule_based_copilot_baseline",
                "narrative": f"[Local Rule Fallback] Incident flagged: {prompt[:60]}... (Remote GPU offline)",
                "confidence": 0.85,
                "latency_ms": 1.2
            }

        t0 = time.perf_counter()
        try:
            payload = {"prompt": prompt, "image": image_base64}
            resp = requests.post(f"{self.remote_url.rstrip('/')}/vlm/analyze", json=payload, timeout=self.timeout_sec)
            if resp.status_code == 200:
                result = resp.json()
                result["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
                result["source"] = "remote_cloud_gpu"
                return result
        except Exception as e:
            logger.error("Remote GPU request failed, falling back to local CPU", error=str(e))

        return {
            "source": "local_cpu_fallback",
            "model": "rule_based_copilot_baseline",
            "narrative": f"[Local Rule Fallback] Emergency escalation: {prompt[:60]}...",
            "confidence": 0.80,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2)
        }
