"""
Ingestion Routes — Accept code from external agents and GitHub URLs
"""
import uuid
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from core.state import deployment_store

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

class AgentIngestRequest(BaseModel):
    source: str  # "github" or "zip_url"
    url: str
    project_name: Optional[str] = "untitled"
    auto_deploy: Optional[bool] = False
    target_platform: Optional[str] = "Vercel"

@router.post("/agent", status_code=202)
async def ingest_from_agent(req: AgentIngestRequest, background_tasks: BackgroundTasks):
    """Accept code from external code-gen agents or GitHub imports."""
    tracking_id = f"ingest_{uuid.uuid4().hex[:8]}"
    await deployment_store.create(tracking_id, {
        "status": "PENDING",
        "source": req.source,
        "url": req.url,
        "project_name": req.project_name,
        "auto_deploy": req.auto_deploy,
    })
    # Background: download, analyze, optionally deploy
    background_tasks.add_task(_ingest_worker, tracking_id, req)
    return {"tracking_id": tracking_id, "status": "PENDING", "message": "Ingestion started"}

async def _ingest_worker(tracking_id: str, req: AgentIngestRequest):
    await deployment_store.update(tracking_id, {"status": "ANALYZING"})
    # TODO: Download from GitHub/URL, run analyzer, optionally deploy
    import asyncio
    await asyncio.sleep(2)
    await deployment_store.update(tracking_id, {"status": "ANALYZED", "framework": "detected"})
