"""
Supabase Admin Client (Service Role)
=====================================
Server-side client for DB operations. Uses service_role key — NEVER expose to frontend.
"""

import logging
from typing import Optional, List, Dict, Any
from core.config import settings

logger = logging.getLogger(__name__)

_client = None

def get_supabase():
    """Get Supabase admin client (lazy init)."""
    global _client
    if _client is not None:
        return _client
    if not settings.has_supabase:
        logger.warning("Supabase not configured — DB operations will fail")
        return None
    try:
        from supabase import create_client
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        return _client
    except Exception as e:
        logger.error(f"Supabase init failed: {e}")
        return None


class SupabaseDB:
    """Typed wrapper for Supabase DB operations."""

    @staticmethod
    async def upsert_user_profile(user_id: str, email: str, provider: str = "email",
                                   display_name: str = "", avatar_url: str = "") -> dict:
        sb = get_supabase()
        if not sb:
            return {"error": "Supabase not configured"}
        try:
            result = sb.table("user_profiles").upsert({
                "user_id": user_id,
                "email": email,
                "auth_provider": provider,
                "display_name": display_name or email.split("@")[0],
                "avatar_url": avatar_url,
            }).execute()
            return {"success": True, "data": result.data}
        except Exception as e:
            logger.error(f"upsert_user_profile: {e}")
            return {"error": str(e)}

    @staticmethod
    async def create_deployment(user_id: str, project_name: str, platform: str,
                                 framework: str = "", file_count: int = 0) -> Optional[str]:
        sb = get_supabase()
        if not sb:
            return None
        try:
            result = sb.table("deployments").insert({
                "user_id": user_id,
                "project_name": project_name,
                "platform": platform,
                "framework": framework,
                "file_count": file_count,
                "status": "pending",
            }).execute()
            return result.data[0]["id"] if result.data else None
        except Exception as e:
            logger.error(f"create_deployment: {e}")
            return None

    @staticmethod
    async def update_deployment(deploy_id: str, updates: Dict[str, Any]) -> bool:
        sb = get_supabase()
        if not sb:
            return False
        try:
            sb.table("deployments").update(updates).eq("id", deploy_id).execute()
            return True
        except Exception as e:
            logger.error(f"update_deployment: {e}")
            return False

    @staticmethod
    async def get_deployments(user_id: str = "") -> List[dict]:
        sb = get_supabase()
        if not sb:
            return []
        try:
            q = sb.table("deployments").select("*").order("created_at", desc=True).limit(50)
            if user_id:
                q = q.eq("user_id", user_id)
            result = q.execute()
            return result.data or []
        except Exception as e:
            logger.error(f"get_deployments: {e}")
            return []

    @staticmethod
    async def add_build_log(deployment_id: str, level: str, message: str) -> None:
        sb = get_supabase()
        if not sb:
            return
        try:
            sb.table("build_logs").insert({
                "deployment_id": deployment_id,
                "level": level,
                "message": message,
            }).execute()
        except Exception as e:
            logger.error(f"add_build_log: {e}")

    @staticmethod
    async def get_stats(user_id: str = "") -> dict:
        sb = get_supabase()
        if not sb:
            return {"total_deploys": 0, "active_sites": 0, "failed_deploys": 0}
        try:
            q = sb.table("deployments").select("status")
            if user_id:
                q = q.eq("user_id", user_id)
            result = q.execute()
            rows = result.data or []
            return {
                "total_deploys": len(rows),
                "active_sites": sum(1 for r in rows if r.get("status") == "ready"),
                "failed_deploys": sum(1 for r in rows if r.get("status") == "error"),
            }
        except Exception as e:
            logger.error(f"get_stats: {e}")
            return {"total_deploys": 0, "active_sites": 0, "failed_deploys": 0}

    # ── Code Quality Scan Storage ──────────────────────────

    @staticmethod
    async def store_quality_scan(project_id: str, scan_data: dict) -> bool:
        sb = get_supabase()
        if not sb:
            return False
        try:
            import json
            sb.table("quality_scans").upsert({
                "project_id": project_id,
                "score": scan_data.get("score", 0),
                "total_issues": scan_data.get("total_issues", 0),
                "scan_data": json.dumps(scan_data),
            }).execute()
            return True
        except Exception as e:
            logger.error(f"store_quality_scan: {e}")
            return False

    @staticmethod
    async def get_quality_scan(project_id: str) -> Optional[dict]:
        sb = get_supabase()
        if not sb:
            return None
        try:
            import json
            result = sb.table("quality_scans").select("*").eq("project_id", project_id).order("created_at", desc=True).limit(1).execute()
            if result.data:
                row = result.data[0]
                return json.loads(row.get("scan_data", "{}"))
            return None
        except Exception as e:
            logger.error(f"get_quality_scan: {e}")
            return None

    # ── Deployment Version History (Rollback) ──────────────

    @staticmethod
    async def get_deployment_versions(project_id: str) -> list:
        sb = get_supabase()
        if not sb:
            return []
        try:
            result = sb.table("deployment_versions").select("*").eq("project_id", project_id).order("version_number", desc=True).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"get_deployment_versions: {e}")
            return []

    @staticmethod
    async def save_deployment_version(snapshot: dict) -> bool:
        sb = get_supabase()
        if not sb:
            return False
        try:
            sb.table("deployment_versions").insert(snapshot).execute()
            return True
        except Exception as e:
            logger.error(f"save_deployment_version: {e}")
            return False

    @staticmethod
    async def delete_deployment_version(project_id: str, version_number: int) -> bool:
        sb = get_supabase()
        if not sb:
            return False
        try:
            sb.table("deployment_versions").delete().eq("project_id", project_id).eq("version_number", version_number).execute()
            return True
        except Exception as e:
            logger.error(f"delete_deployment_version: {e}")
            return False


db = SupabaseDB()
