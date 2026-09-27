"""
IBVAP Tactical AI Copilot & SITREP Router
SIH PS-26187: Hardware-Agnostic Intelligent Surveillance

Provides real-time tactical situational reporting (SITREPs), natural language
surveillance queries, and interactive ChatGPT-level tactical assistance powered by:
1. OpenAI ChatGPT (GPT-4o, GPT-4o-mini)
2. NVIDIA NIM (Llama-3.3-70B, etc.)
3. Local Ollama (Llama 3.2, Phi-3)
4. Built-in Offline Tactical Intelligence Brain (Border Security SOPs & Live Grounding)
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import structlog
from sqlalchemy import select, desc

from services.nvidia.nim_surveillance_agent import NVIDIASurveillanceAgent
from services.tracking.remembrance_store import LongTermRemembranceStore
from services.agents.tactical_ai_engine import TacticalAIEngine
from apps.backend.database.connection import AsyncSessionLocal
from apps.backend.database.models import Incident, ANPRObservation

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/copilot", tags=["Tactical AI Copilot"])

# Instantiate surveillance agent and tactical AI engine
surveillance_agent = NVIDIASurveillanceAgent()
ai_engine = TacticalAIEngine.get_instance()

class QueryRequest(BaseModel):
    query: str = Field(..., description="Operator natural language question")
    camera_id: Optional[str] = Field(None, description="Optional target camera ID")

class SITREPRequest(BaseModel):
    shift_notes: Optional[str] = Field("", description="Optional operator shift notes")

class ChatMessage(BaseModel):
    role: str = Field(..., description="user or assistant")
    content: str = Field(..., description="Message text")

class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="Conversation history")
    camera_id: Optional[str] = Field(None, description="Active camera context")

class ProviderConfigRequest(BaseModel):
    provider: str = Field(..., description="offline, openai, nvidia_nim, or ollama")
    api_key: Optional[str] = Field(None, description="Optional API key")
    model: Optional[str] = Field(None, description="Optional model identifier")
    ollama_url: Optional[str] = Field(None, description="Optional local Ollama URL")


async def _fetch_live_context():
    """Helper to fetch recent incidents, ANPR records, and remembered entities."""
    inc_data = []
    anpr_data = []
    try:
        async with AsyncSessionLocal() as session:
            # Query recent incidents
            res = await session.execute(
                select(Incident).order_by(desc(Incident.timestamp)).limit(15)
            )
            incidents = res.scalars().all()
            inc_data = [
                {
                    "camera_id": i.camera_id,
                    "event_type": i.event_type,
                    "severity": i.severity.value if hasattr(i.severity, "value") else str(i.severity),
                    "explanation": getattr(i, "explanation", None) or f"{i.event_type} on {i.camera_id}",
                    "timestamp": i.timestamp.isoformat() if i.timestamp else ""
                }
                for i in incidents
            ]

            # Query recent ANPR observations
            anpr_res = await session.execute(
                select(ANPRObservation).order_by(desc(ANPRObservation.timestamp)).limit(15)
            )
            anpr_rows = anpr_res.scalars().all()
            anpr_data = [
                {
                    "camera_id": a.camera_id,
                    "plate_number": getattr(a, "plate_text", None) or getattr(a, "plate_number", ""),
                    "confidence": getattr(a, "plate_confidence", 0.0)
                }
                for a in anpr_rows
            ]
    except Exception as e:
        logger.warning("Failed to query database for copilot context", error=str(e))

    # Fetch remembered entities from RAM store
    store = LongTermRemembranceStore.get_instance()
    entities = store.get_all_profiles()
    return inc_data, anpr_data, entities


@router.post("/sitrep")
async def generate_sitrep(req: SITREPRequest):
    """
    Generate an operational tactical situation report (SITREP) synthesizing
    recent perimeter intrusions, license plate observations, and remembered vehicles.
    """
    try:
        inc_data, anpr_data, remembrance_profs = await _fetch_live_context()

        # Generate briefing via surveillance agent (with local rule-based fallback)
        briefing = await surveillance_agent.generate_incident_briefing(
            incidents=inc_data,
            anpr_records=anpr_data,
            shift_notes=req.shift_notes or ""
        )

        briefing["status"] = "success"
        briefing["remembered_entities_count"] = len(remembrance_profs)
        briefing["total_recent_incidents"] = len(inc_data)
        briefing["total_anpr_reads"] = len(anpr_data)
        return briefing

    except Exception as e:
        logger.error("Failed to generate SITREP", error=str(e))
        raise HTTPException(status_code=500, detail=f"SITREP generation failed: {str(e)}")


@router.post("/query")
async def answer_copilot_query(req: QueryRequest):
    """
    Answer an operator's operational question using live context from
    remembrance store, ANPR reads, and recent breach incidents.
    """
    inc_data, anpr_data, entities = await _fetch_live_context()
    
    # Delegate to TacticalAIEngine with full domain knowledge & provider switching
    result = await ai_engine.answer_query(
        query=req.query,
        camera_id=req.camera_id,
        context_incidents=inc_data,
        context_anpr=anpr_data,
        remembered_entities=entities
    )
    result["entities_in_memory"] = len(entities)
    return result


@router.post("/chat")
async def chat_with_copilot(req: ChatRequest):
    """
    Full multi-turn interactive conversational endpoint for ChatGPT-level dialogue.
    Takes message history and generates a context-aware response.
    """
    if not req.messages:
        raise HTTPException(status_code=400, detail="Messages array cannot be empty")

    last_user_message = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
    if not last_user_message:
        raise HTTPException(status_code=400, detail="No user message provided")

    inc_data, anpr_data, entities = await _fetch_live_context()

    result = await ai_engine.answer_query(
        query=last_user_message,
        camera_id=req.camera_id,
        context_incidents=inc_data,
        context_anpr=anpr_data,
        remembered_entities=entities
    )
    return {
        "reply": result["answer"],
        "source": result["source"],
        "model": result["model"],
        "telemetry": result.get("telemetry"),
        "action": result.get("action")
    }


@router.get("/config")
async def get_copilot_config():
    """Retrieve current AI Copilot engine configuration and status."""
    return ai_engine.get_status()


@router.post("/config")
async def update_copilot_config(req: ProviderConfigRequest):
    """Update active AI provider, model selection, or credentials."""
    ai_engine.update_config(
        provider=req.provider,
        api_key=req.api_key,
        model=req.model,
        ollama_url=req.ollama_url
    )
    return {
        "status": "updated",
        "current_config": ai_engine.get_status()
    }
