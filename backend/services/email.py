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


async def send_domain_registration_email(email: str, domains: list, expiry_date: str) -> bool:
    """Send confirmation email after successful domain registration."""
    if not settings.has_resend:
        logger.info(f"Resend not configured — skipping domain email to {email}")
        return False
    try:
        domain_list_html = "".join(
            f'<li style="margin:4px 0"><strong>{d}</strong></li>' for d in domains
        )
        import httpx
        async with httpx.AsyncClient() as http:
            resp = await http.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}", "Content-Type": "application/json"},
                json={
                    "from": "DeployAI <noreply@deployai.app>",
                    "to": [email],
                    "subject": f"🌐 Domain{'s' if len(domains) > 1 else ''} registered successfully!",
                    "html": f"""
<div style="font-family:system-ui;max-width:500px;margin:0 auto;padding:24px">
  <h2 style="color:#10b981">Domain Registration Complete!</h2>
  <p>Your domain{'s have' if len(domains) > 1 else ' has'} been registered:</p>
  <ul style="list-style:none;padding:0">{domain_list_html}</ul>
  <p><strong>Expiry:</strong> {expiry_date[:10]}</p>
  <h3 style="color:#6366f1;margin-top:20px">Nameserver Configuration</h3>
  <p>Point your domain to these nameservers to connect with DeployAI:</p>
  <div style="background:#f3f4f6;padding:12px;border-radius:8px;font-family:monospace;font-size:13px">
    ns1.deployai.app<br>
    ns2.deployai.app
  </div>
  <p style="margin-top:16px">You can also connect your domain to any deployed site from the DeployAI dashboard.</p>
  <hr style="border-color:#e5e7eb">
  <p style="color:#9ca3af;font-size:12px">Sent by DeployAI</p>
</div>""",
                },
            )
            return resp.status_code < 300
    except Exception as e:
        logger.error(f"Resend domain email error: {e}")
        return False

