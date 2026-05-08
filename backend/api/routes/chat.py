"""
AI Chat Routes — Full Context Injection + NVIDIA NIM + Serper Search
=====================================================================
RULES:
1. Every message gets full project context injected
2. Error-related questions trigger Serper live doc search
3. NEVER give generic responses — always project-specific
4. Maintain conversation history per session (last 20 msgs)
"""
import logging
from typing import Optional, List, Dict
from fastapi import APIRouter
from pydantic import BaseModel

from services.ai_agent import NIMDiagnosticsAgent
from services.ai_chat_engine import ChatEngine

router = APIRouter(prefix="/chat", tags=["AI Chat"])
logger = logging.getLogger(__name__)

# Session-level conversation history (in-memory, keyed by session_id)
_session_history: Dict[str, list] = {}
MAX_HISTORY = 20

chat_engine = ChatEngine()
sre_agent = NIMDiagnosticsAgent()


class ChatMessageInput(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    # Full project context — injected by frontend on EVERY message
    context: Optional[dict] = None


class ChatContext(BaseModel):
    project_name: Optional[str] = ""
    project_type: Optional[str] = ""
    framework: Optional[str] = ""
    confidence_score: Optional[float] = 0
    health_score: Optional[float] = 0
    entry_point: Optional[str] = ""
    errors: Optional[list] = []
    deployment_status: Optional[str] = ""
    target_platform: Optional[str] = ""
    last_deploy_url: Optional[str] = ""
    terminal_logs: Optional[list] = []


@router.post("/message")
async def chat_message(data: ChatMessageInput):
    """
    Main chat endpoint. Injects full project context into every message.
    Routes to SRE agent for error analysis, Owl Guide for general questions.
    Uses Serper for live documentation search on error-related questions.
    """
    session_id = data.session_id or "default"
    message = data.message.strip()
    ctx = data.context or {}

    if not message:
        return {"status": "error", "response": "Message cannot be empty"}

    # Get/init session history
    if session_id not in _session_history:
        _session_history[session_id] = []

    history = _session_history[session_id]

    # Detect if this is an error/deployment-related question
    error_keywords = [
        "error", "fail", "crash", "bug", "debug", "fix", "broken",
        "500", "404", "timeout", "traceback", "exception", "build failed",
        "deploy failed", "not working", "why did", "how to fix",
    ]
    is_error_query = any(kw in message.lower() for kw in error_keywords)

    # Build full context string for injection
    context_block = _build_context_string(ctx)

    # Serper search for error-related questions
    serper_results = None
    if is_error_query:
        search_query = _build_search_query(message, ctx)
        serper_results = await chat_engine.search_docs(search_query)
        logger.info(f"[CHAT] Serper search triggered: '{search_query}' → {len(serper_results or [])} results")

    # Generate response
    if is_error_query:
        response_data = await chat_engine.answer_with_context(
            message=message,
            context=context_block,
            history=history[-MAX_HISTORY:],
            serper_results=serper_results,
            mode="sre",
        )
    else:
        response_data = await chat_engine.answer_with_context(
            message=message,
            context=context_block,
            history=history[-MAX_HISTORY:],
            serper_results=None,
            mode="guide",
        )

    # Update session history
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": response_data.get("response", "")})

    # Trim history to last 20
    if len(history) > MAX_HISTORY * 2:
        _session_history[session_id] = history[-(MAX_HISTORY * 2):]

    return {
        "status": "success",
        "agent": response_data.get("agent", "Owl Guide"),
        "response": response_data.get("response", ""),
        "diagnosis": response_data.get("diagnosis"),
        "serper_used": serper_results is not None and len(serper_results or []) > 0,
        "serper_results_count": len(serper_results or []),
        "context_injected": bool(context_block),
    }


# Also keep the legacy /ask endpoint for backward compatibility
@router.post("/ask")
async def ask_ai_legacy(data: ChatMessageInput):
    """Legacy endpoint — redirects to /message."""
    return await chat_message(data)


def _build_context_string(ctx: dict) -> str:
    """Build a structured context block from the project context dict."""
    if not ctx:
        return ""

    parts = []
    if ctx.get("project_name"):
        parts.append(f"Project: {ctx['project_name']}")
    if ctx.get("project_type"):
        parts.append(f"Type: {ctx['project_type']}")
    if ctx.get("framework"):
        parts.append(f"Framework: {ctx['framework']}")
    if ctx.get("confidence_score"):
        parts.append(f"Analysis Confidence: {ctx['confidence_score']}%")
    if ctx.get("health_score"):
        parts.append(f"Health Score: {ctx['health_score']}/100")
    if ctx.get("entry_point"):
        parts.append(f"Entry Point: {ctx['entry_point']}")
    if ctx.get("deployment_status"):
        parts.append(f"Deploy Status: {ctx['deployment_status']}")
    if ctx.get("target_platform"):
        parts.append(f"Target Platform: {ctx['target_platform']}")
    if ctx.get("last_deploy_url"):
        parts.append(f"Last Deploy URL: {ctx['last_deploy_url']}")

    # Errors
    errors = ctx.get("errors", [])
    if errors:
        parts.append("Detected Errors:")
        for err in errors[:10]:
            if isinstance(err, dict):
                parts.append(f"  - {err.get('reason', err.get('message', str(err)))}")
            else:
                parts.append(f"  - {err}")

    # Terminal logs (last 50 lines)
    logs = ctx.get("terminal_logs", [])
    if logs:
        parts.append(f"Terminal Logs (last {min(50, len(logs))} lines):")
        for line in logs[-50:]:
            parts.append(f"  {line}")

    return "\n".join(parts)


def _build_search_query(message: str, ctx: dict) -> str:
    """Build a smart search query for Serper based on the question + context."""
    platform = ctx.get("target_platform", "")
    framework = ctx.get("framework", "")
    query = message

    # Append platform/framework for more targeted results
    if platform and platform.lower() not in message.lower():
        query = f"{platform} {query}"
    if framework and framework.lower() not in message.lower():
        query = f"{framework} {query}"

    return query
