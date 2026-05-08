"""
Auth Middleware — Supabase JWT Verification
=============================================
Protects ALL API routes except whitelisted public endpoints.
Verifies JWT tokens from the Authorization header using Supabase.
"""
import logging
from typing import Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from core.config import settings

logger = logging.getLogger(__name__)

# ── Public endpoints (no auth required) ────────────────────
PUBLIC_PATHS = {
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    # Auth routes (user needs to be able to register/validate)
    "/api/v1/auth/validate-password",
    "/api/v1/auth/register-profile",
    # Webhooks (verified by their own signatures)
    "/api/v1/payments/webhook",
}

# Prefixes that are always public
PUBLIC_PREFIXES = (
    "/docs",
    "/redoc",
    "/openapi",
    "/ws/",  # WebSocket — auth handled at connection level
)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    JWT verification middleware using Supabase auth.
    Extracts user_id from the JWT and injects it into request.state.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip auth for public paths
        if path in PUBLIC_PATHS:
            return await call_next(request)

        # Skip auth for public prefixes
        if any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        # Skip auth for OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # ── If Supabase is not configured, allow all (dev mode) ──
        if not settings.has_supabase:
            request.state.user_id = "dev-user"
            request.state.user_email = "dev@deployai.local"
            request.state.auth_verified = False
            return await call_next(request)

        # ── Extract JWT from Authorization header ──
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            if settings.DEPLOY_ENV == "development":
                request.state.user_id = "dev-user"
                request.state.user_email = "dev@deployai.local"
                request.state.auth_verified = False
                return await call_next(request)
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "reason": "Authentication required",
                    "evidence": "Missing or invalid Authorization header. Expected: Bearer <token>",
                    "solution": "Include a valid Supabase JWT in the Authorization header.",
                },
            )

        token = auth_header.split("Bearer ", 1)[1].strip()
        if not token:
            if settings.DEPLOY_ENV == "development":
                request.state.user_id = "dev-user"
                request.state.user_email = "dev@deployai.local"
                request.state.auth_verified = False
                return await call_next(request)
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "reason": "Empty authentication token",
                    "evidence": "The Authorization header contained 'Bearer' but no token",
                    "solution": "Provide a valid Supabase JWT after 'Bearer '.",
                },
            )

        # ── Verify JWT with Supabase ──
        try:
            user = await self._verify_supabase_jwt(token)
            if not user:
                return JSONResponse(
                    status_code=401,
                    content={
                        "status": "error",
                        "reason": "Invalid or expired token",
                        "evidence": "Supabase JWT verification failed",
                        "solution": "Re-authenticate with Supabase and try again with a fresh token.",
                    },
                )

            # Inject user info into request state
            request.state.user_id = user.get("id", "")
            request.state.user_email = user.get("email", "")
            request.state.auth_verified = True

        except Exception as e:
            logger.error(f"[AUTH] JWT verification error: {e}")
            return JSONResponse(
                status_code=401,
                content={
                    "status": "error",
                    "reason": "Authentication verification failed",
                    "evidence": str(e)[:200],
                    "solution": "Check your Supabase configuration and try again.",
                },
            )

        return await call_next(request)

    @staticmethod
    async def _verify_supabase_jwt(token: str) -> Optional[dict]:
        """Verify a JWT token using the Supabase Admin client."""
        try:
            from core.supabase_client import get_supabase
            sb = get_supabase()
            if not sb:
                # Supabase not available — degrade gracefully in dev
                logger.warning("[AUTH] Supabase client not available — skipping JWT verification")
                return {"id": "unverified", "email": ""}

            # Use Supabase auth.get_user() to verify the JWT
            user_response = sb.auth.get_user(token)
            if user_response and user_response.user:
                return {
                    "id": user_response.user.id,
                    "email": user_response.user.email or "",
                    "role": user_response.user.role or "authenticated",
                }
            return None
        except Exception as e:
            logger.error(f"[AUTH] Supabase verify failed: {e}")
            return None


def get_current_user(request: Request) -> dict:
    """
    Utility to extract the authenticated user from request.state.
    Use in route handlers: user = get_current_user(request)
    """
    return {
        "user_id": getattr(request.state, "user_id", ""),
        "user_email": getattr(request.state, "user_email", ""),
        "verified": getattr(request.state, "auth_verified", False),
    }
