"""
New Relic Monitoring — Post-deployment URL tracking
=====================================================
Sends deployment events and monitors URLs via New Relic API.
"""
import logging
import httpx
from core.config import settings

logger = logging.getLogger(__name__)


class NewRelicMonitor:
    """Sends deployment markers and synthetic monitors to New Relic."""

    BASE_URL = "https://api.newrelic.com"

    def __init__(self):
        self.key = settings.NEW_RELIC_LICENSE_KEY
        self.http = httpx.AsyncClient(timeout=30)

    @property
    def enabled(self):
        return bool(self.key)

    async def record_deployment(self, app_name: str, url: str, platform: str, revision: str = ""):
        """Record a deployment event in New Relic."""
        if not self.enabled:
            logger.warning("New Relic not configured — skipping deployment marker")
            return {"status": "skipped", "reason": "NEW_RELIC_LICENSE_KEY not set"}

        try:
            # Use New Relic Events API to record deployment
            event = {
                "eventType": "DeployAIDeployment",
                "appName": app_name,
                "deployUrl": url,
                "platform": platform,
                "revision": revision,
                "status": "deployed",
            }

            resp = await self.http.post(
                "https://insights-collector.newrelic.com/v1/accounts/events",
                headers={
                    "Api-Key": self.key,
                    "Content-Type": "application/json",
                },
                json=event,
            )

            if resp.status_code < 300:
                logger.info(f"New Relic: deployment recorded for {app_name}")
                return {"status": "recorded", "app_name": app_name}
            else:
                logger.error(f"New Relic API error: {resp.status_code} {resp.text[:200]}")
                return {"status": "error", "code": resp.status_code, "message": resp.text[:200]}

        except Exception as e:
            logger.error(f"New Relic integration failed: {e}")
            return {"status": "error", "message": str(e)}

    async def create_uptime_monitor(self, name: str, url: str):
        """Create a synthetic ping monitor to track uptime."""
        if not self.enabled:
            return {"status": "skipped", "reason": "NEW_RELIC_LICENSE_KEY not set"}

        try:
            resp = await self.http.post(
                f"{self.BASE_URL}/v3/monitors",
                headers={
                    "Api-Key": self.key,
                    "Content-Type": "application/json",
                },
                json={
                    "name": f"DeployAI — {name}",
                    "type": "SIMPLE",
                    "frequency": 5,  # Check every 5 minutes
                    "uri": url,
                    "locations": ["AWS_US_EAST_1"],
                    "status": "ENABLED",
                },
            )

            if resp.status_code < 300:
                monitor_id = resp.json().get("id", "")
                logger.info(f"New Relic: uptime monitor created for {url} (id: {monitor_id})")
                return {"status": "created", "monitor_id": monitor_id, "url": url}
            else:
                logger.error(f"New Relic Synthetics error: {resp.status_code}")
                return {"status": "error", "code": resp.status_code, "message": resp.text[:200]}

        except Exception as e:
            logger.error(f"New Relic synthetics failed: {e}")
            return {"status": "error", "message": str(e)}


# Singleton
nr_monitor = NewRelicMonitor()
