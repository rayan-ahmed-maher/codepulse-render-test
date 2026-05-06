"""
Deployment Routes — Real API deploys with Supabase persistence
================================================================
NEVER returns fake URLs. Only returns url when status == READY from platform API.
"""
import os, uuid, asyncio, logging
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel
from typing import Optional
from services.deployment import DeploymentOrchestrator
from services.ai_agent import NIMDiagnosticsAgent
from services.email import send_deployment_success, send_deployment_failure
from services.monitoring import nr_monitor
from services.name_generator import generate_deploy_name, get_expected_url
from core.state import deployment_store
from core.supabase_client import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deploy", tags=["Deployment"])
sre = NIMDiagnosticsAgent()

DEPLOY_TIMEOUT_SEC = 300  # 5 minute max per deployment


class DeployRequest(BaseModel):
    project_path: str
    project_name: str
    platform: str  # Vercel, Netlify, Cloudflare, Render
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    framework: Optional[str] = None
    file_count: Optional[int] = 0
    site_name: Optional[str] = None  # Custom platform subdomain/site name supplied by the user


class DeployResponse(BaseModel):
    tracking_id: str
    status: str
    message: str


async def _deploy_worker(tracking_id: str, req: DeployRequest, db_deploy_id: Optional[str] = None):
    """Background deployment worker with timeout protection."""
    try:
        await asyncio.wait_for(
            _deploy_worker_inner(tracking_id, req, db_deploy_id),
            timeout=DEPLOY_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        err = f"Deployment timed out after {DEPLOY_TIMEOUT_SEC}s"
        logger.error(f"[DEPLOY] {err}")
        await deployment_store.update(tracking_id, {"status": "FAILED", "error": err})
        if db_deploy_id:
            await db.update_deployment(db_deploy_id, {"status": "error", "error_logs": err})
    except Exception as e:
        err = f"Deployment worker crashed: {str(e)}"
        logger.exception(f"[DEPLOY] {err}")
        await deployment_store.update(tracking_id, {"status": "FAILED", "error": err})
        if db_deploy_id:
            await db.update_deployment(db_deploy_id, {"status": "error", "error_logs": err})


async def _deploy_worker_inner(tracking_id: str, req: DeployRequest, db_deploy_id: Optional[str] = None):
    """Actual deployment logic."""
    logger.info(f"[DEPLOY] === Worker started: {req.platform} | {req.project_name} | tracking={tracking_id} ===")
    await deployment_store.update(tracking_id, {"status": "DEPLOYING"})
    if db_deploy_id:
        await db.update_deployment(db_deploy_id, {"status": "deploying"})
        await db.add_build_log(db_deploy_id, "INFO", f"Starting deployment to {req.platform}...")

    result = {}

    fw = req.framework or "static"
    logger.info(f"[DEPLOY] Step 1: Calling {req.platform} API (framework={fw})...")

    # Validate API keys before attempting deploy
    from core.config import settings as cfg
    key_check = {
        "Vercel": cfg.has_vercel,
        "Netlify": cfg.has_netlify,
        "Cloudflare": cfg.has_cloudflare,
        "Render": bool(cfg.RENDER_API_KEY),
    }
    if not key_check.get(req.platform, False):
        err = f"{req.platform} API key is not configured. Add {req.platform.upper()}_TOKEN to your .env file."
        logger.error(f"[DEPLOY] {err}")
        await deployment_store.update(tracking_id, {"status": "FAILED", "error": err})
        if db_deploy_id:
            await db.update_deployment(db_deploy_id, {"status": "error", "error_logs": err})
            await db.add_build_log(db_deploy_id, "ERROR", err)
        return

    # ── STRICT PLATFORM RESULT ISOLATION ──
    orchestrator = DeploymentOrchestrator()

    if req.platform.lower() == "vercel":
        result = await orchestrator.deploy_to_vercel(req.project_path, req.project_name, framework=fw)
    elif req.platform.lower() == "netlify":
        result = await orchestrator.deploy_to_netlify(req.project_path, req.site_name or req.project_name)
    elif req.platform.lower() == "cloudflare":
        result = await orchestrator.deploy_to_cloudflare(req.project_path, req.project_name)
    elif req.platform.lower() == "render":
        # ── RENDER: Requires GitHub repo URL ──
        # Step 1: Auto-generate render.yaml if it doesn't exist
        render_yaml_path = Path(req.project_path) / "render.yaml"
        if not render_yaml_path.exists():
            start_cmd = {
                "fastapi": "uvicorn main:app --host 0.0.0.0 --port $PORT",
                "flask": "python app.py",
                "django": "python manage.py runserver 0.0.0.0:$PORT",
                "nodejs": "npm start",
                "nextjs": "npm start",
                "react": "npx serve -s build -l $PORT",
                "static": "npx serve . -l $PORT",
            }.get(fw, "npm start")

            build_cmd = {
                "fastapi": "pip install -r requirements.txt",
                "flask": "pip install -r requirements.txt",
                "django": "pip install -r requirements.txt",
            }.get(fw, "npm install && npm run build")

            env_type = "python" if fw in ("fastapi", "flask", "django", "python") else "node"

            render_yaml = f"""services:
  - type: web
    name: {req.project_name}
    env: {env_type}
    buildCommand: "{build_cmd}"
    startCommand: "{start_cmd}"
    plan: free
    branch: main
"""
            try:
                render_yaml_path.write_text(render_yaml)
                logger.info(f"[DEPLOY] Generated render.yaml for {fw}")
                if db_deploy_id:
                    await db.add_build_log(db_deploy_id, "INFO", f"Auto-generated render.yaml (env={env_type})")
            except Exception as e:
                logger.warning(f"[DEPLOY] Failed to write render.yaml: {e}")
        # Step 1.5: Generate .gitignore if missing
        gitignore_path = Path(req.project_path) / ".gitignore"
        if not gitignore_path.exists():
            is_python = fw in ("fastapi", "flask", "django", "python")
            gitignore_content = "node_modules/\n.next/\ndist/\nbuild/\n.cache/\n.venv/\nvenv/\n__pycache__/\n*.pyc\n.env\n.DS_Store\n"
            if is_python:
                gitignore_content += "*.egg-info/\n*.egg\n"
            try:
                gitignore_path.write_text(gitignore_content)
                logger.info(f"[DEPLOY] Generated .gitignore")
            except Exception:
                pass

        # Step 1.6: Validate project has required files
        proj_path = Path(req.project_path)
        is_python = fw in ("fastapi", "flask", "django", "python")
        if is_python:
            if not (proj_path / "requirements.txt").exists():
                err = "Missing requirements.txt — Render cannot install Python dependencies without it."
                await deployment_store.update(tracking_id, {"status": "FAILED", "error": err})
                if db_deploy_id:
                    await db.update_deployment(db_deploy_id, {"status": "error", "error_logs": err})
                    await db.add_build_log(db_deploy_id, "ERROR", err)
                return
            if not any((proj_path / f).exists() for f in ["main.py", "app.py", "manage.py", "wsgi.py"]):
                err = "Missing entry point (main.py, app.py, or manage.py). Render needs an entry point to start your app."
                await deployment_store.update(tracking_id, {"status": "FAILED", "error": err})
                if db_deploy_id:
                    await db.update_deployment(db_deploy_id, {"status": "error", "error_logs": err})
                    await db.add_build_log(db_deploy_id, "ERROR", err)
                return

        # Step 2: Push project to GitHub
        from services.github_push import github_push
        if not github_push.is_configured:
            err = "Render requires a GitHub repository. Set GITHUB_TOKEN and GITHUB_USERNAME in your .env file."
            logger.error(f"[DEPLOY] {err}")
            await deployment_store.update(tracking_id, {"status": "FAILED", "error": err})
            if db_deploy_id:
                await db.update_deployment(db_deploy_id, {"status": "error", "error_logs": err})
                await db.add_build_log(db_deploy_id, "ERROR", err)
            return

        if db_deploy_id:
            await db.add_build_log(db_deploy_id, "INFO", "Pushing project to GitHub...")
        await deployment_store.update(tracking_id, {"status": "PUSHING_TO_GITHUB"})

        github_result = await github_push.push_project(req.project_path, req.project_name)
        if "error" in github_result:
            err = f"GitHub push failed: {github_result['error']}"
            logger.error(f"[DEPLOY] {err}")
            await deployment_store.update(tracking_id, {"status": "FAILED", "error": err})
            if db_deploy_id:
                await db.update_deployment(db_deploy_id, {"status": "error", "error_logs": err})
                await db.add_build_log(db_deploy_id, "ERROR", err)
            return

        repo_url = github_result["repo_url"]
        logger.info(f"[DEPLOY] GitHub push complete: {repo_url} ({github_result.get('files_pushed', 0)} files)")
        if db_deploy_id:
            await db.add_build_log(db_deploy_id, "SUCCESS", f"Pushed to GitHub: {repo_url}")
            await db.add_build_log(db_deploy_id, "INFO", f"Deploying to Render from {repo_url}...")

        # Step 3: Deploy to Render using the GitHub repo URL
        result = await orchestrator.deploy_to_render(
            project_name=req.project_name,
            repo_url=repo_url,
            framework=fw,
        )
    else:
        err = f"Unknown platform: {req.platform}. Choose Vercel, Netlify, Cloudflare, or Render."
        logger.error(f"[DEPLOY] {err}")
        await deployment_store.update(tracking_id, {"status": "FAILED", "error": err})
        if db_deploy_id:
            await db.update_deployment(db_deploy_id, {"status": "error", "error_logs": err})
            await db.add_build_log(db_deploy_id, "ERROR", err)
        return

    # ── LOG PLATFORM + URL ──
    logger.info(f"[DEPLOY] Platform: {req.platform}")
    logger.info(f"[DEPLOY] Result URL: {result.get('url', 'N/A')}")

    if result.get("status") == "success":
        final_url = result.get("url", "")
        
        # ── VALIDATE RESPONSE BEFORE RETURN ──
        if not final_url:
            raise Exception(f"Deployment failed: no URL returned by {req.platform}")

        # Poll for completion if Vercel
        if req.platform == "Vercel" and result.get("deployment_id"):
            if db_deploy_id:
                await db.add_build_log(db_deploy_id, "INFO", "Polling Vercel for ready state...")
            poll = await orchestrator.poll_status("Vercel", result["deployment_id"])
            result.update(poll)
            final_url = result.get("url", final_url)
            
            if not final_url:
                raise Exception("Deployment failed: Vercel returned success but no URL after polling")

        # STRICT: only set READY if we have a confirmed URL
        if final_url:
            # Verify the deployment URL is actually live
            if db_deploy_id:
                await db.add_build_log(db_deploy_id, "INFO", f"Verifying deployment URL: {final_url}")
            
            verification = await orchestrator.verify_deployment(final_url)
            
            if verification.get("verified"):
                await deployment_store.update(tracking_id, {
                    "status": "READY",
                    "url": final_url,
                    "deployment_id": result.get("deployment_id", ""),
                    "verified": True,
                    "verification_status_code": verification.get("status_code"),
                })
                if db_deploy_id:
                    await db.update_deployment(db_deploy_id, {"status": "ready", "url": final_url})
                    await db.add_build_log(db_deploy_id, "SUCCESS", f"Deployed and verified: {final_url} (HTTP {verification.get('status_code')})")

                # Send success email
                if req.user_email:
                    await send_deployment_success(req.user_email, req.project_name, final_url, req.platform)

                # New Relic: record deployment + create uptime monitor
                await nr_monitor.record_deployment(req.project_name, final_url, req.platform)
                await nr_monitor.create_uptime_monitor(req.project_name, final_url)
            else:
                # URL returned but not responding — mark as READY but unverified
                await deployment_store.update(tracking_id, {
                    "status": "READY",
                    "url": final_url,
                    "deployment_id": result.get("deployment_id", ""),
                    "verified": False,
                    "verification_warning": verification.get("reason", "URL may still be propagating"),
                })
                if db_deploy_id:
                    await db.update_deployment(db_deploy_id, {"status": "ready", "url": final_url})
                    await db.add_build_log(db_deploy_id, "WARNING", f"Deployed but not yet verified: {final_url}")
        else:
            await deployment_store.update(tracking_id, {
                "status": "FAILED",
                "error": "Deployment completed but no URL returned from platform API",
            })
            if db_deploy_id:
                await db.update_deployment(db_deploy_id, {
                    "status": "error",
                    "error_logs": "No URL returned from platform",
                })
    else:
        error_msg = result.get("message", str(result.get("raw", "")))
        diagnosis = sre.analyze_logs(error_msg)
        await deployment_store.update(tracking_id, {
            "status": "FAILED",
            "error": error_msg,
            "sre_fix": {
                "severity": diagnosis.severity,
                "human_fix": diagnosis.human_fix,
                "root_cause": diagnosis.root_cause,
                "steps": diagnosis.fix_steps,
                "ghost_command": diagnosis.ghost_command,
            },
        })
        if db_deploy_id:
            await db.update_deployment(db_deploy_id, {"status": "error", "error_logs": error_msg[:2000]})
            await db.add_build_log(db_deploy_id, "ERROR", error_msg[:500])

        # Send failure email
        if req.user_email:
            await send_deployment_failure(req.user_email, req.project_name, error_msg[:200], req.platform)


@router.post("/execute", response_model=DeployResponse, status_code=202)
async def execute_deployment(req: DeployRequest, background_tasks: BackgroundTasks):
    # ── Preprocess name using universal name generator ──
    # This generates a clean, platform-specific slug BEFORE deployment starts.
    # Does NOT modify any deployment logic — only the name passed in.
    generated_name = generate_deploy_name(
        project_name=req.project_name,
        platform=req.platform,
        custom_name=req.site_name,  # User-provided custom subdomain (optional)
    )
    req.project_name = generated_name
    # For Netlify, also set site_name to the generated name if user provided one
    if req.platform == "Netlify" and req.site_name:
        req.site_name = generated_name
    logger.info(f"[DEPLOY] Name: '{req.project_name}' for {req.platform} (expected: {get_expected_url(generated_name, req.platform)})")

    # Validate project path
    if not req.project_path or not req.project_path.strip():
        logger.error(f"[DEPLOY] Empty project_path received")
        return DeployResponse(
            tracking_id="", status="ERROR",
            message="project_path is empty. Please re-upload and analyze your project first."
        )

    if not os.path.isdir(req.project_path):
        logger.error(f"[DEPLOY] Project directory not found: {req.project_path}")
        return DeployResponse(
            tracking_id="", status="ERROR",
            message=f"Project directory not found: {req.project_path}. Please re-upload and analyze your project."
        )

    # Validate platform
    valid_platforms = {"Vercel", "Netlify", "Cloudflare", "Render"}
    if req.platform not in valid_platforms:
        return DeployResponse(
            tracking_id="", status="ERROR",
            message=f"Invalid platform '{req.platform}'. Choose: {', '.join(valid_platforms)}"
        )

    logger.info(f"[DEPLOY] === Execute request: platform={req.platform}, project={req.project_name}, path={req.project_path} ===")

    # Validate at least one file exists
    file_count = sum(1 for _ in Path(req.project_path).rglob("*") if _.is_file())
    if file_count == 0:
        return DeployResponse(
            tracking_id="", status="ERROR",
            message="Project directory is empty. No files to deploy."
        )

    tracking_id = f"deploy_{uuid.uuid4().hex[:8]}"

    # Create in-memory record
    await deployment_store.create(tracking_id, {
        "status": "PENDING",
        "platform": req.platform,
        "project_name": req.project_name,
    })

    # Create Supabase record
    db_deploy_id = None
    if req.user_id:
        db_deploy_id = await db.create_deployment(
            user_id=req.user_id,
            project_name=req.project_name,
            platform=req.platform,
            framework=req.framework or "",
            file_count=req.file_count or 0,
        )

    background_tasks.add_task(_deploy_worker, tracking_id, req, db_deploy_id)
    return DeployResponse(tracking_id=tracking_id, status="PENDING", message=f"Deployment queued to {req.platform}")


@router.get("/status/{tracking_id}")
async def get_deployment_status(tracking_id: str):
    record = await deployment_store.get(tracking_id)
    if not record:
        return {"error": "Tracking ID not found"}
    return record


@router.get("/list")
async def list_deployments(user_id: Optional[str] = Query(None)):
    # Try Supabase first
    if user_id:
        db_records = await db.get_deployments(user_id)
        if db_records:
            return db_records
    # Fallback to in-memory
    return await deployment_store.list_all()
