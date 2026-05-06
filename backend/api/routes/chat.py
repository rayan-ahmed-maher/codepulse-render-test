"""
Chat Routes — AI-powered Q&A with the Owl Guide
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from services.ai_agent import AIAgentOrchestrator

router = APIRouter(prefix="/chat", tags=["AI Chat"])
orchestrator = AIAgentOrchestrator()

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = ""

@router.post("/ask")
async def ask_ai(req: ChatRequest):
    """Route a question to the appropriate AI agent."""
    result = orchestrator.route_query(req.message, req.context or "")
    return result
