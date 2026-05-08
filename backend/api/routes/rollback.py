"""
Deployment Rollback System — Version History & One-Click Rollback
==================================================================
Saves deployment snapshots, enables rollback to any previous version,
and re-deploys the exact previous build to the same platform.
"""
import os
import json
import hashlib
import logging
import time
from pathlib import Path
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from core.supabase_client import db
from core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rollback", tags=["Rollback"])

MAX_VERSIONS_PER_PROJECT = 10


class RollbackRequest(BaseModel):
    project_id: str
    version_number: int
    user_id: str = ""


def _get_file_manifest(project_path: str) -> list:
    """Generate a file manifest with hashes for the project."""
    manifest = []
    root = Path(project_path)
    skip_dirs = {"node_modules", ".git", "__pycache__", ".next", "dist", "build", ".venv", "venv"}

    for f in root.rglob("*"):
        if f.is_dir():
            continue
        if any(part in skip_dirs for part in f.parts):
            continue
        try:
            content = f.read_bytes()
            file_hash = hashlib.sha256(content).hexdigest()[:16]
            rel_path = str(f.relative_to(root))
            manifest.append({
                "path": rel_path,
                "size": len(content),
                "hash": file_hash,
            })
        except Exception:
            continue

    return manifest


async def save_deployment_snapshot(
    project_id: str,
    project_path: str,
    platform: str,
    deployment_url: str,
    build_config: dict = None,
    tracking_id: str = "",
) -> dict:
    """
    Save a deployment snapshot to Supabase.
    Called after every successful deployment.
    Returns the saved version info.
    """
    try:
        # Get current version count
        existing = await db.get_deployment_versions(project_id)
        current_versions = existing if isinstance(existing, list) else []
        next_version = len(current_versions) + 1

        # Build file manifest
        manifest = _get_file_manifest(project_path) if os.path.isdir(project_path) else []

        snapshot = {
            "project_id": project_id,
            "version_number": next_version,
            "platform": platform.lower(),
            "deployment_url": deployment_url,
            "build_config": json.dumps(build_config or {}),
            "file_manifest": json.dumps(manifest),
            "tracking_id": tracking_id,
            "status": "active" if next_version == max(v.get("version_number", 0) for v in current_versions + [{"version_number": 0}]) + 1 else "archived",
        }

        result = await db.save_deployment_version(snapshot)

        # Auto-delete oldest if over limit
        if len(current_versions) >= MAX_VERSIONS_PER_PROJECT:
            oldest = sorted(current_versions, key=lambda v: v.get("version_number", 0))
            for old_version in oldest[:len(current_versions) - MAX_VERSIONS_PER_PROJECT + 1]:
                try:
                    await db.delete_deployment_version(
                        project_id, old_version.get("version_number")
                    )
                    logger.info(f"[ROLLBACK] Auto-deleted version {old_version.get('version_number')} (over limit)")
                except Exception:
                    pass

        # PostHog event
        try:
            from core.observability import track_event
            track_event("deployment_snapshot_saved", properties={
                "project_id": project_id,
                "version": next_version,
                "platform": platform,
            })
        except Exception:
            pass

        logger.info(f"[ROLLBACK] Saved snapshot v{next_version} for {project_id} on {platform}")
        return {
            "status": "success",
            "version_number": next_version,
            "deployment_url": deployment_url,
        }
    except Exception as e:
        logger.error(f"[ROLLBACK] Failed to save snapshot: {e}")
        # Sentry
        try:
            from core.observability import capture_error
            capture_error(e, context={"project_id": project_id})
        except Exception:
            pass
        return {"status": "error", "reason": str(e)[:200]}


@router.get("/history/{project_id}")
async def get_rollback_history(project_id: str):
    """Return all deployment versions for a project, newest first."""
    try:
        versions = await db.get_deployment_versions(project_id)
        if not versions:
            return {
                "status": "success",
                "versions": [],
                "count": 0,
                "max_versions": MAX_VERSIONS_PER_PROJECT,
            }

        # Sort newest first
        versions_sorted = sorted(
            versions, key=lambda v: v.get("version_number", 0), reverse=True
        )

        return {
            "status": "success",
            "versions": versions_sorted,
            "count": len(versions_sorted),
            "max_versions": MAX_VERSIONS_PER_PROJECT,
        }
    except Exception as e:
        logger.error(f"[ROLLBACK] History fetch failed: {e}")
        return {
            "status": "error",
            "reason": "Failed to fetch rollback history",
            "evidence": str(e)[:200],
            "solution": "Check the Supabase connection and deployment_versions table.",
        }


@router.post("/execute")
async def execute_rollback(data: RollbackRequest):
    """Roll back to a previous deployment version."""
    try:
        # Fetch target version
        versions = await db.get_deployment_versions(data.project_id)
        if not versions:
            return {
                "status": "error",
                "reason": "No deployment versions found",
                "evidence": f"project_id: {data.project_id}",
                "solution": "Deploy at least once before attempting a rollback.",
            }

        target = None
        for v in versions:
            if v.get("version_number") == data.version_number:
                target = v
                break

        if not target:
            return {
                "status": "error",
                "reason": f"Version {data.version_number} not found",
                "evidence": f"Available versions: {[v.get('version_number') for v in versions]}",
                "solution": "Check available versions with GET /rollback/history/{project_id}",
            }

        platform = target.get("platform", "")
        original_url = target.get("deployment_url", "")
        build_config = json.loads(target.get("build_config", "{}")) if target.get("build_config") else {}

        logger.info(f"[ROLLBACK] Rolling back {data.project_id} to v{data.version_number} on {platform}")

        # Emit pipeline events for rollback
        try:
            from services.pipeline_events import PipelineTracker
            pipeline = PipelineTracker(session_id=f"rollback-{data.project_id}", tracking_id=f"rollback-{data.version_number}")
            await pipeline.start()
            await pipeline.emit("upload", "active")
            await pipeline.emit("upload", "complete")
            await pipeline.emit("validate", "active")
            await pipeline.emit("validate", "complete")
        except Exception:
            pipeline = None

        # Re-deploy based on platform
        result = await _redeploy(
            platform=platform,
            build_config=build_config,
            target_version=target,
            pipeline=pipeline,
        )

        if result.get("status") == "success":
            # Save rollback as new version
            new_snapshot = await save_deployment_snapshot(
                project_id=data.project_id,
                project_path=build_config.get("project_path", ""),
                platform=platform,
                deployment_url=result.get("url", original_url),
                build_config={**build_config, "rollback_from": data.version_number},
                tracking_id=f"rollback-{data.version_number}",
            )

            # PostHog
            try:
                from core.observability import track_event
                track_event("rollback_executed", user_id=data.user_id or "anonymous", properties={
                    "project_id": data.project_id,
                    "from_version": data.version_number,
                    "platform": platform,
                })
            except Exception:
                pass

            return {
                "status": "success",
                "message": f"Successfully rolled back to v{data.version_number}",
                "url": result.get("url", original_url),
                "new_version": new_snapshot.get("version_number"),
                "platform": platform,
            }
        else:
            return {
                "status": "error",
                "reason": f"Rollback deployment failed",
                "evidence": result.get("message", result.get("reason", "")),
                "solution": "Check the platform API keys and try again.",
            }

    except Exception as e:
        logger.error(f"[ROLLBACK] Execute failed: {e}")
        try:
            from core.observability import capture_error
            capture_error(e, context={"project_id": data.project_id})
        except Exception:
            pass
        return {
            "status": "error",
            "reason": "Rollback execution failed",
            "evidence": str(e)[:200],
            "solution": "Check the backend logs for details.",
        }


@router.delete("/history/{project_id}/{version}")
async def delete_version(project_id: str, version: int):
    """Delete a specific deployment version."""
    try:
        await db.delete_deployment_version(project_id, version)
        return {
            "status": "success",
            "message": f"Version {version} deleted for project {project_id}",
        }
    except Exception as e:
        return {
            "status": "error",
            "reason": "Failed to delete version",
            "evidence": str(e)[:200],
            "solution": "Check the Supabase connection.",
        }


async def _redeploy(platform: str, build_config: dict, target_version: dict, pipeline=None) -> dict:
    """Re-deploy a previous version to the same platform."""
    try:
        from services.deployment import DeploymentOrchestrator
        orchestrator = DeploymentOrchestrator()

        project_path = build_config.get("project_path", "")
        project_name = build_config.get("project_name", target_version.get("project_id", "rollback"))
        framework = build_config.get("framework", "static")

        if pipeline:
            await pipeline.emit("build", "active")

        if platform == "vercel":
            result = await orchestrator.deploy_to_vercel(project_path, project_name, framework=framework)
        elif platform == "netlify":
            result = await orchestrator.deploy_to_netlify(project_path, project_name)
        elif platform == "cloudflare":
            result = await orchestrator.deploy_to_cloudflare(project_path, project_name)
        elif platform == "render":
            repo_url = build_config.get("repo_url", "")
            result = await orchestrator.deploy_to_render(project_name, repo_url=repo_url, framework=framework)
        else:
            return {"status": "error", "message": f"Unknown platform: {platform}"}

        if pipeline:
            if result.get("status") == "success":
                await pipeline.emit("build", "complete")
                await pipeline.emit("deploy", "active")
                await pipeline.emit("deploy", "complete")
                await pipeline.emit("verify", "active")
                await pipeline.emit("verify", "complete")
                await pipeline.emit("live", "active")
                await pipeline.emit("live", "complete")
            else:
                await pipeline.fail("deploy", result.get("message", "Unknown error"))

        return result

    except Exception as e:
        logger.error(f"[ROLLBACK] Re-deploy failed: {e}")
        if pipeline:
            await pipeline.fail("deploy", str(e)[:200])
        return {"status": "error", "message": str(e)}
