"""
IBVAP NVIDIA NIM Surveillance AI Agent
SIH PS-26187: Hardware-Agnostic Intelligent Surveillance

Integrates NVIDIA NIM (Inference Microservices) free-tier vision and reasoning agents
for automated incident synthesis, threat escalation reports, and natural language
queries across multi-camera border outposts (BOPs).
"""

import os
import json
import httpx
import structlog
from typing import Dict, List, Any, Optional

logger = structlog.get_logger()

DEFAULT_NIM_MODEL = "meta/llama-3.2-11b-vision-instruct"
DEFAULT_NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

class NVIDIASurveillanceAgent:
    """
    NVIDIA AI Agent for border surveillance operations.
    Leverages NVIDIA NIM free endpoints with graceful local fallback.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = DEFAULT_NIM_MODEL,
        endpoint_url: str = DEFAULT_NIM_URL
    ):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY", "")
        self.model_name = model_name
        self.endpoint_url = endpoint_url

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 10)

    async def generate_incident_briefing(
        self,
        incidents: List[Dict[str, Any]],
        anpr_records: List[Dict[str, Any]],
        shift_notes: str = ""
    ) -> Dict[str, Any]:
        """
        Synthesizes recent perimeter breaches and ANPR sightings into a military-grade
        border outpost situational briefing.
        """
        # Build structured context
        context = {
            "total_incidents": len(incidents),
            "critical_breaches": [
                {
                    "camera": inc.get("camera_id"),
                    "type": inc.get("event_type"),
                    "severity": inc.get("severity"),
                    "explanation": inc.get("explanation"),
                    "timestamp": inc.get("timestamp")
                }
                for inc in incidents[:10]
            ],
            "vehicle_sightings": [
                {
                    "camera": rec.get("camera_id"),
                    "plate": rec.get("plate_number"),
                    "confidence": rec.get("confidence")
                }
                for rec in anpr_records[:10]
            ],
            "operator_notes": shift_notes
        }

        if not self.is_available():
            # Zero-dependency deterministic military briefing fallback
            return self._local_rule_briefing(context)

        system_prompt = (
            "You are the IBVAP Tactical AI Agent deployed at an Indian Border Security Force Outpost (BOP). "
            "Analyze the provided live sensor telemetry, restricted zone breaches, and vehicle ANPR sightings. "
            "Provide a concise, high-priority operational assessment covering: 1) Threat Level, 2) Key Perimeter Breaches, "
            "3) Vehicle & Number Plate Flagging, and 4) Recommended Defensive Actions."
        )

        user_content = f"Surveillance Telemetry Context:\n{json.dumps(context, indent=2)}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.1,
            "max_tokens": 450
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.endpoint_url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    briefing_text = data["choices"][0]["message"]["content"]
                    return {
                        "source": "nvidia_nim",
                        "model": self.model_name,
                        "briefing": briefing_text,
                        "status": "success"
                    }
                else:
                    logger.warning("NVIDIA NIM API returned non-200", status_code=resp.status_code, text=resp.text[:200])
        except Exception as e:
            logger.warning("Failed to contact NVIDIA NIM, using fallback briefing", error=str(e))

        return self._local_rule_briefing(context)

    def _local_rule_briefing(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic rule-based situational briefing when running offline at remote BOPs."""
        total_inc = context.get("total_incidents", 0)
        crit_count = sum(1 for b in context.get("critical_breaches", []) if b.get("severity") == "CRITICAL")
        vehicles = context.get("vehicle_sightings", [])

        threat_level = "ELEVATED" if crit_count > 0 else ("GUARDED" if total_inc > 0 else "LOW")
        
        plates = [v["plate"] for v in vehicles if v.get("plate")]
        plate_str = ", ".join(plates[:3]) if plates else "None logged"

        summary = (
            f"**TACTICAL SITUATION REPORT (BOP DEFENSE)**\n"
            f"- **Threat Assessment**: {threat_level} ({crit_count} Critical Breaches, {total_inc} Total Events)\n"
            f"- **Perimeter Integrity**: {'Multiple sector intrusions detected requiring immediate dispatch' if crit_count > 0 else 'Perimeter zones holding without verified breach'}.\n"
            f"- **Vehicle/ANPR Intel**: {len(vehicles)} vehicles tracked. Active Plates: {plate_str}.\n"
            f"- **Defensive Directive**: Maintain visual contact on active camera feeds; verify evidence hashes on immutable ledger before acknowledging."
        )

        return {
            "source": "local_tactical_engine",
            "model": "rule_based_fallback",
            "briefing": summary,
            "threat_level": threat_level,
            "status": "success"
        }
