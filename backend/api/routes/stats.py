"""
Stats Routes — Live metrics from Supabase DB
"""
from fastapi import APIRouter, Query
from typing import Optional
from core.supabase_client import db
from core.state import deployment_store

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("")
async def get_stats(user_id: Optional[str] = Query(None)):
    """Return real metrics from Supabase DB, fallback to in-memory store."""
    # Try Supabase first
    stats = await db.get_stats(user_id or "")
    if stats.get("total_deploys", 0) > 0:
        return stats

    # Fallback to in-memory
    all_deploys = await deployment_store.list_all()
    return {
        "total_deploys": len(all_deploys),
        "active_sites": sum(1 for d in all_deploys if d.get("status") == "READY"),
        "failed_deploys": sum(1 for d in all_deploys if d.get("status") == "FAILED"),
    }
