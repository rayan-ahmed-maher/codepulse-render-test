"""
Pipeline Event Emitter — Real-Time Deployment Stage Tracking
==============================================================
Emits structured pipeline stage events through the terminal WebSocket.
Hook into deploy routes to emit events at each deployment stage.
"""
import time
import logging
from typing import Optional
from api.routes.terminal_ws import terminal_manager

logger = logging.getLogger(__name__)

STAGES = ["upload", "validate", "analyze", "build", "deploy", "verify", "live"]


class PipelineTracker:
    """Tracks a single deployment pipeline's stage progression."""

    def __init__(self, session_id: str, tracking_id: str = ""):
        self.session_id = session_id
        self.tracking_id = tracking_id
        self.start_time = time.time()
        self.stage_times = {}

    async def emit(self, stage: str, status: str, error: str = ""):
        """
        Emit a pipeline stage event via WebSocket.
        stage: upload | validate | analyze | build | deploy | verify | live
        status: pending | active | complete | failed
        """
        elapsed = round(time.time() - self.start_time, 2)

        if status == "active":
            self.stage_times[stage] = time.time()

        stage_elapsed = 0
        if status in ("complete", "failed") and stage in self.stage_times:
            stage_elapsed = round(time.time() - self.stage_times[stage], 2)

        event = {
            "type": "pipeline",
            "stage": stage,
            "status": status,
            "elapsed": elapsed,
            "stage_elapsed": stage_elapsed,
            "tracking_id": self.tracking_id,
            "error": error,
        }

        await terminal_manager.emit(
            self.session_id,
            "INFO" if status != "failed" else "ERROR",
            f"pipeline:{stage} — {status}" + (f" ({error})" if error else ""),
            evidence=f"elapsed={elapsed}s",
        )

        # Also send the structured pipeline event directly
        import json
        if self.session_id in terminal_manager._connections:
            payload = json.dumps(event)
            dead = set()
            for ws in terminal_manager._connections[self.session_id]:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.add(ws)
            for ws in dead:
                terminal_manager._connections[self.session_id].discard(ws)

        # Track in PostHog
        try:
            from core.observability import track_event
            track_event("pipeline_stage_complete", properties={
                "stage": stage, "status": status, "elapsed": elapsed,
            })
        except Exception:
            pass

        logger.info(f"[PIPELINE] {stage}:{status} | elapsed={elapsed}s | tracking={self.tracking_id}")

    async def start(self):
        """Emit initial pending states for all stages."""
        for stage in STAGES:
            await self.emit(stage, "pending")

    async def fail(self, stage: str, error: str):
        """Mark a stage as failed."""
        await self.emit(stage, "failed", error=error)
        # Sentry capture
        try:
            from core.observability import capture_message
            capture_message(f"Pipeline failed at {stage}: {error}", level="error")
        except Exception:
            pass
