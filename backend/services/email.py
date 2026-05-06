"""
Email Service — Resend integration
====================================
Transactional emails for deployment success/failure. NEVER sends if key missing.
"""
import logging
from core.config import settings

logger = logging.getLogger(__name__)


async def send_deployment_success(email: str, project_name: str, url: str, platform: str) -> bool:
    if not settings.has_resend:
        logger.info(f"Resend not configured — skipping success email to {email}")
        return False
    try:
        import httpx
        async with httpx.AsyncClient() as http:
            resp = await http.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}", "Content-Type": "application/json"},
                json={
                    "from": "DeployAI <noreply@deployai.app>",
                    "to": [email],
                    "subject": f"✅ {project_name} deployed to {platform}",
                    "html": f"""
<div style="font-family:system-ui;max-width:500px;margin:0 auto;padding:24px">
  <h2 style="color:#10b981">Deployment Successful!</h2>
  <p><strong>{project_name}</strong> has been deployed to <strong>{platform}</strong>.</p>
  <p>Your site is live at:<br>
  <a href="{url}" style="color:#6366f1;font-weight:bold">{url}</a></p>
  <hr style="border-color:#e5e7eb">
  <p style="color:#9ca3af;font-size:12px">Sent by DeployAI</p>
</div>""",
                },
            )
            return resp.status_code < 300
    except Exception as e:
        logger.error(f"Resend error: {e}")
        return False


async def send_deployment_failure(email: str, project_name: str, error_summary: str, platform: str) -> bool:
    if not settings.has_resend:
        return False
    try:
        import httpx
        async with httpx.AsyncClient() as http:
            resp = await http.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}", "Content-Type": "application/json"},
                json={
                    "from": "DeployAI <noreply@deployai.app>",
                    "to": [email],
                    "subject": f"❌ {project_name} deployment failed on {platform}",
                    "html": f"""
<div style="font-family:system-ui;max-width:500px;margin:0 auto;padding:24px">
  <h2 style="color:#ef4444">Deployment Failed</h2>
  <p><strong>{project_name}</strong> failed to deploy on <strong>{platform}</strong>.</p>
  <p>Error: <code style="background:#fef2f2;padding:2px 6px;border-radius:4px;color:#ef4444">{error_summary}</code></p>
  <p>Check the build logs in your DeployAI dashboard for details.</p>
  <hr style="border-color:#e5e7eb">
  <p style="color:#9ca3af;font-size:12px">Sent by DeployAI</p>
</div>""",
                },
            )
            return resp.status_code < 300
    except Exception as e:
        logger.error(f"Resend error: {e}")
        return False
