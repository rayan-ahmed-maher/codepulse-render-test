"""
DeployAI — FastAPI Backend
============================
Production SaaS API server for:
  - Supabase auth validation
  - Deterministic project analysis + GitHub import
  - Multi-platform deployment (Vercel, Netlify, Cloudflare)
  - AI diagnostics via NVIDIA NIM
  - Domain intelligence (DomScan + Serper)
  - Deployment email notifications (Resend)
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health Check ──────────────────────────────────────────────

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
        },
    }

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}

# ── Route Registration ────────────────────────────────────────

from api.routes import analyze, deploy, chat, ingest, stats
from api.routes import auth, github_import, domain, local_deploy

app.include_router(auth.router, prefix="/api/v1")
app.include_router(analyze.router, prefix="/api/v1")
app.include_router(github_import.router, prefix="/api/v1")
app.include_router(deploy.router, prefix="/api/v1")
app.include_router(local_deploy.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(ingest.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(domain.router, prefix="/api/v1")
