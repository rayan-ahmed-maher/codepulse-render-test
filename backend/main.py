"""
DeployAI — FastAPI Backend (Production)
=========================================
Production SaaS API server with:
  - Supabase JWT auth middleware on ALL protected routes
  - Standardized error reporting (reason/evidence/solution)
  - Full observability (Sentry, PostHog, New Relic)
  - Multi-platform deployment (Vercel, Netlify, Cloudflare, Render)
  - AI diagnostics via NVIDIA NIM + Serper
  - Domain intelligence (DomScan API)
  - Real-time WebSocket terminal
  - Payment processing (Razorpay)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered deployment SaaS — Analyze, Deploy, Monitor",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ═══════════════════════════════════════════════════════════════
#  MIDDLEWARE STACK (order matters — outermost first)
# ═══════════════════════════════════════════════════════════════

# 1. CORS — must be outermost to handle preflight OPTIONS requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        # Production origins (add your deployed frontend URL here)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 2. Auth middleware — verifies Supabase JWT on all protected routes
from core.auth_middleware import AuthMiddleware
app.add_middleware(AuthMiddleware)

# 3. Setup Exception Handlers (Replaces old ErrorNormalizerMiddleware and ErrorMiddleware)
from core.error_normalizer import setup_exception_handlers
setup_exception_handlers(app)



# ═══════════════════════════════════════════════════════════════
#  OBSERVABILITY — Initialize on startup
# ═══════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup_event():
    """Initialize all observability services at app startup."""
    from core.observability import init_observability
    init_observability()


# ═══════════════════════════════════════════════════════════════
#  HEALTH CHECKS (Public — no auth required)
# ═══════════════════════════════════════════════════════════════

@app.get("/", tags=["Health"])
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "services": {
            "supabase": "connected" if settings.has_supabase else "not_configured",
            "nvidia_nim": "connected" if settings.has_nvidia else "not_configured",
            "vercel": "connected" if settings.has_vercel else "not_configured",
            "netlify": "connected" if settings.has_netlify else "not_configured",
            "cloudflare": "connected" if settings.has_cloudflare else "not_configured",
            "serper": "connected" if settings.has_serper else "not_configured",
            "domscan": "connected" if settings.has_domscan else "not_configured",
            "resend": "connected" if settings.has_resend else "not_configured",
            "render": "connected" if settings.RENDER_API_KEY else "not_configured",
            "new_relic": "connected" if settings.NEW_RELIC_LICENSE_KEY else "not_configured",
            "razorpay": "connected" if settings.RAZORPAY_KEY_ID else "not_configured",
            "sentry": "connected" if os.getenv("SENTRY_DSN") else "not_configured",
            "posthog": "connected" if os.getenv("POSTHOG_API_KEY") else "not_configured",
        },
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}


# ═══════════════════════════════════════════════════════════════
#  ROUTE REGISTRATION
# ═══════════════════════════════════════════════════════════════

import os
from api.routes import analyze, deploy, chat, ingest, stats
from api.routes import auth, github_import, domain, local_deploy, validate
from api.routes import domains, payments, terminal_ws
from api.routes import code_quality, rollback

app.include_router(auth.router, prefix="/api/v1")
app.include_router(analyze.router, prefix="/api/v1")
app.include_router(github_import.router, prefix="/api/v1")
app.include_router(deploy.router, prefix="/api/v1")
app.include_router(local_deploy.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(ingest.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(domain.router, prefix="/api/v1")
app.include_router(validate.router, prefix="/api/v1")
app.include_router(domains.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(code_quality.router, prefix="/api/v1")
app.include_router(rollback.router, prefix="/api/v1")
app.include_router(terminal_ws.router)  # WebSocket — no prefix

