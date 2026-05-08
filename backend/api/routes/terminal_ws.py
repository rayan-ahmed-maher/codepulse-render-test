"""
WebSocket Terminal — Real-time structured log streaming
=========================================================
Emits real backend operation logs in real time. NEVER buffers. NEVER fakes.
Each event: { timestamp, level, message, evidence? }
"""
import asyncio
import logging
import json
import time
from datetime import datetime, timezone
from typing import Dict, Set, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["Terminal WebSocket"])
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  CONNECTION MANAGER
# ═══════════════════════════════════════════════════════════════

class ConnectionManager:
    """Manages WebSocket connections per session."""

    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._session_logs: Dict[str, list] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        if session_id not in self._connections:
            self._connections[session_id] = set()
        self._connections[session_id].add(ws)

        if session_id not in self._session_logs:
            self._session_logs[session_id] = []

        logger.info(f"[WS] Client connected: session={session_id} (total={len(self._connections[session_id])})")

    def disconnect(self, session_id: str, ws: WebSocket):
        if session_id in self._connections:
            self._connections[session_id].discard(ws)
            if not self._connections[session_id]:
                del self._connections[session_id]
        logger.info(f"[WS] Client disconnected: session={session_id}")

    async def emit(self, session_id: str, level: str, message: str, evidence: str = ""):
        """Emit a log event to all connected clients for a session. NEVER buffers."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "evidence": evidence,
        }

        # Store in session log history (max 500)
        if session_id in self._session_logs:
            self._session_logs[session_id].append(event)
            if len(self._session_logs[session_id]) > 500:
                self._session_logs[session_id] = self._session_logs[session_id][-500:]

        # Send to ALL connected WebSocket clients for this session
        if session_id in self._connections:
            dead = set()
            payload = json.dumps(event)
            for ws in self._connections[session_id]:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.add(ws)

            # Clean up dead connections
            for ws in dead:
                self._connections[session_id].discard(ws)

    async def broadcast(self, level: str, message: str, evidence: str = ""):
        """Emit to ALL sessions (for global events like server startup)."""
        for session_id in list(self._connections.keys()):
            await self.emit(session_id, level, message, evidence)

    def get_history(self, session_id: str) -> list:
        """Get stored log history for a session."""
        return self._session_logs.get(session_id, [])


# Singleton instance — imported by other modules to emit logs
terminal_manager = ConnectionManager()


# ═══════════════════════════════════════════════════════════════
#  WEBSOCKET ENDPOINT
# ═══════════════════════════════════════════════════════════════

@router.websocket("/ws/terminal/{session_id}")
async def terminal_websocket(ws: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time terminal logs.
    Client connects → receives all logs for this session in real time.
    """
    await terminal_manager.connect(session_id, ws)

    # Send stored history on connect (replay)
    history = terminal_manager.get_history(session_id)
    if history:
        try:
            await ws.send_text(json.dumps({
                "type": "history",
                "logs": history[-100:],  # Last 100 logs on reconnect
            }))
        except Exception:
            pass

    # Send connected confirmation
    try:
        await ws.send_text(json.dumps({
            "type": "status",
            "status": "connected",
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))
    except Exception:
        pass

    try:
        while True:
            # Keep connection alive — listen for pings/commands
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
                elif msg.get("type") == "clear":
                    if session_id in terminal_manager._session_logs:
                        terminal_manager._session_logs[session_id] = []
                    await ws.send_text(json.dumps({"type": "cleared"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        terminal_manager.disconnect(session_id, ws)
    except Exception as e:
        logger.debug(f"[WS] Connection error: {e}")
        terminal_manager.disconnect(session_id, ws)


# ═══════════════════════════════════════════════════════════════
#  REST ENDPOINT — Get stored terminal history
# ═══════════════════════════════════════════════════════════════

@router.get("/terminal/history/{session_id}")
async def get_terminal_history(session_id: str):
    """Return stored terminal log history for a session."""
    logs = terminal_manager.get_history(session_id)
    return {"session_id": session_id, "logs": logs, "count": len(logs)}
