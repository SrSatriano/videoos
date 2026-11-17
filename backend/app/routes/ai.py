from __future__ import annotations

from fastapi import APIRouter

from ..schemas import StructuredAgentRequest
from ..services.llm import ollama_status, run_agent_structured

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/status")
def status():
    return ollama_status()


@router.post("/agents/run")
def run_structured_agent(payload: StructuredAgentRequest):
    return run_agent_structured(payload.agent_id, payload.role, payload.brief, model=payload.model)
