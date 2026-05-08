"""
Observability Service — PostHog + Sentry + New Relic (Fully Connected)
=======================================================================
Not just installed — actually CONNECTED and sending real events.
"""
import logging
import os
from typing import Optional, Dict, Any
from core.config import settings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  SENTRY — Error Tracking & Performance Monitoring
# ═══════════════════════════════════════════════════════════════

_sentry_initialized = False


def init_sentry():
    """Initialize Sentry SDK. Call once at app startup."""
    global _sentry_initialized
    sentry_dsn = os.getenv("SENTRY_DSN", "")
    if not sentry_dsn:
        logger.info("[SENTRY] SENTRY_DSN not set — error tracking disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=0.3,  # 30% of requests traced
            profiles_sample_rate=0.1,
            environment=os.getenv("DEPLOY_ENV", "development"),
            release=f"deployai@{settings.APP_VERSION}",
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                StarletteIntegration(transaction_style="endpoint"),
            ],
            send_default_pii=False,
        )
        _sentry_initialized = True
        logger.info("[SENTRY] ✓ Initialized — error tracking active")
    except ImportError:
        logger.warning("[SENTRY] sentry-sdk not installed — run: pip install sentry-sdk[fastapi]")
    except Exception as e:
        logger.error(f"[SENTRY] Init failed: {e}")


def capture_error(error: Exception, context: Dict[str, Any] = None):
    """Send an error event to Sentry."""
    if not _sentry_initialized:
        return
    try:
        import sentry_sdk
        if context:
            with sentry_sdk.push_scope() as scope:
                for k, v in context.items():
                    scope.set_extra(k, v)
                sentry_sdk.capture_exception(error)
        else:
            sentry_sdk.capture_exception(error)
    except Exception:
        pass


def capture_message(message: str, level: str = "info"):
    """Send a message event to Sentry."""
    if not _sentry_initialized:
        return
    try:
        import sentry_sdk
        sentry_sdk.capture_message(message, level=level)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
#  POSTHOG — Product Analytics & Feature Flags
# ═══════════════════════════════════════════════════════════════

_posthog_client = None


def init_posthog():
    """Initialize PostHog analytics. Call once at app startup."""
    global _posthog_client
    posthog_key = os.getenv("POSTHOG_API_KEY", "")
    posthog_host = os.getenv("POSTHOG_HOST", "https://app.posthog.com")

    if not posthog_key:
        logger.info("[POSTHOG] POSTHOG_API_KEY not set — analytics disabled")
        return

    try:
        import posthog
        posthog.project_api_key = posthog_key
        posthog.host = posthog_host
        posthog.debug = settings.DEBUG
        _posthog_client = posthog
        logger.info("[POSTHOG] ✓ Initialized — analytics active")
    except ImportError:
        logger.warning("[POSTHOG] posthog not installed — run: pip install posthog")
    except Exception as e:
        logger.error(f"[POSTHOG] Init failed: {e}")


def track_event(
    event: str,
    user_id: str = "anonymous",
    properties: Dict[str, Any] = None,
):
    """Track a product analytics event in PostHog."""
    if not _posthog_client:
        return
    try:
        _posthog_client.capture(
            distinct_id=user_id,
            event=event,
            properties=properties or {},
        )
    except Exception as e:
        logger.debug(f"[POSTHOG] Track failed: {e}")


def identify_user(user_id: str, traits: Dict[str, Any] = None):
    """Identify a user with properties in PostHog."""
    if not _posthog_client:
        return
    try:
        _posthog_client.identify(distinct_id=user_id, properties=traits or {})
    except Exception as e:
        logger.debug(f"[POSTHOG] Identify failed: {e}")


# ═══════════════════════════════════════════════════════════════
#  NEW RELIC — Infrastructure & APM (Enhanced)
# ═══════════════════════════════════════════════════════════════

_nr_initialized = False


def init_newrelic():
    """Initialize New Relic agent. Call once at app startup."""
    global _nr_initialized
    nr_key = settings.NEW_RELIC_LICENSE_KEY
    if not nr_key:
        logger.info("[NEWRELIC] NEW_RELIC_LICENSE_KEY not set — APM disabled")
        return

    try:
        # Set env var for New Relic agent
        os.environ["NEW_RELIC_LICENSE_KEY"] = nr_key
        os.environ["NEW_RELIC_APP_NAME"] = f"{settings.APP_NAME} Backend"
        os.environ["NEW_RELIC_ENVIRONMENT"] = os.getenv("DEPLOY_ENV", "development")

        # Try to import and initialize
        try:
            import newrelic.agent
            newrelic.agent.initialize()
            _nr_initialized = True
            logger.info("[NEWRELIC] ✓ Agent initialized — APM active")
        except ImportError:
            # New Relic Python agent not installed — use Events API fallback
            logger.info("[NEWRELIC] Agent not installed — using Events API for deployment tracking")
            _nr_initialized = True  # Events API via monitoring.py still works
    except Exception as e:
        logger.error(f"[NEWRELIC] Init failed: {e}")


# ═══════════════════════════════════════════════════════════════
#  UNIFIED INITIALIZATION — Call once from main.py
# ═══════════════════════════════════════════════════════════════

def init_observability():
    """Initialize ALL observability services. Call once at FastAPI startup."""
    logger.info("═" * 50)
    logger.info("[OBSERVABILITY] Initializing monitoring stack...")
    init_sentry()
    init_posthog()
    init_newrelic()
    logger.info("[OBSERVABILITY] Initialization complete")
    logger.info("═" * 50)


# ═══════════════════════════════════════════════════════════════
#  DEPLOYMENT EVENT TRACKING — Track across ALL services
# ═══════════════════════════════════════════════════════════════

async def track_deployment(
    user_id: str,
    project_name: str,
    platform: str,
    status: str,
    url: str = "",
    framework: str = "",
    error: str = "",
):
    """Track a deployment event across Sentry, PostHog, and New Relic."""
    # PostHog event
    track_event(
        event="deployment_completed" if status == "success" else "deployment_failed",
        user_id=user_id,
        properties={
            "project_name": project_name,
            "platform": platform,
            "status": status,
            "url": url,
            "framework": framework,
            "error": error[:200] if error else "",
        },
    )

    # Sentry breadcrumb
    if _sentry_initialized:
        try:
            import sentry_sdk
            sentry_sdk.add_breadcrumb(
                category="deployment",
                message=f"{platform}: {status} — {project_name}",
                level="info" if status == "success" else "error",
            )
            if status != "success" and error:
                capture_message(
                    f"Deployment failed: {platform}/{project_name}: {error[:100]}",
                    level="warning",
                )
        except Exception:
            pass

    # New Relic (via monitoring.py singleton)
    try:
        from services.monitoring import nr_monitor
        if nr_monitor.enabled and status == "success" and url:
            await nr_monitor.record_deployment(project_name, url, platform)
    except Exception:
        pass
