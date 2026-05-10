"""
DeployAI — Backend Configuration
=================================
Typed access to all API keys. Zero defaults — missing keys return empty string.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)


class Settings:
    APP_NAME: str = "DeployAI"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    DEPLOY_ENV: str = os.getenv("DEPLOY_ENV", "development")
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:3001"]

    # ── AI ────────────────────────────────────────────────
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    # ── Supabase ──────────────────────────────────────────
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # ── Deployment Platforms ──────────────────────────────
    VERCEL_TOKEN: str = os.getenv("VERCEL_TOKEN", "")
    NETLIFY_TOKEN: str = os.getenv("NETLIFY_TOKEN", "")
    CLOUDFLARE_API_TOKEN: str = os.getenv("CLOUDFLARE_API_TOKEN", "")
    CLOUDFLARE_ACCOUNT_ID: str = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
    RENDER_API_KEY: str = os.getenv("RENDER_API_KEY", "")
    RENDER_OWNER_ID: str = os.getenv("RENDER_OWNER_ID", "")

    # ── Intelligence ──────────────────────────────────────
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
    DOMSCAN_API_KEY: str = os.getenv("DOMSCAN_API_KEY", "")

    # ── Email ─────────────────────────────────────────────
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")

    # ── Monitoring ────────────────────────────────────────
    NEW_RELIC_LICENSE_KEY: str = os.getenv("NEW_RELIC_LICENSE_KEY", "")

    # ── Payments ──────────────────────────────────────────
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

    # ── GitHub ────────────────────────────────────────────
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_USERNAME: str = os.getenv("GITHUB_USERNAME", "")

    @property
    def has_nvidia(self) -> bool:
        return bool(self.NVIDIA_API_KEY)

    @property
    def has_supabase(self) -> bool:
        return bool(self.SUPABASE_URL and self.SUPABASE_SERVICE_ROLE_KEY)

    @property
    def has_vercel(self) -> bool:
        return bool(self.VERCEL_TOKEN)

    @property
    def has_netlify(self) -> bool:
        return bool(self.NETLIFY_TOKEN)

    @property
    def has_cloudflare(self) -> bool:
        return bool(self.CLOUDFLARE_API_TOKEN and self.CLOUDFLARE_ACCOUNT_ID)

    @property
    def has_serper(self) -> bool:
        return bool(self.SERPER_API_KEY)

    @property
    def has_domscan(self) -> bool:
        return bool(self.DOMSCAN_API_KEY)

    @property
    def has_resend(self) -> bool:
        return bool(self.RESEND_API_KEY)

    @property
    def has_github_token(self) -> bool:
        return bool(self.GITHUB_TOKEN)


settings = Settings()
