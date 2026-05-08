"""
Standardized Error Response Utility
======================================
ALL error responses across the entire codebase MUST use this format:
{
    "status": "error",
    "reason": "Clear human-readable reason",
    "evidence": "Exact technical details — what was found/tried",
    "solution": "Actionable fix instruction"
}

Use `error_response()` for all API-level errors.
Use `ErrorMiddleware` to catch unhandled exceptions.
"""
import logging
import traceback
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


def error_response(
    reason: str,
    evidence: str = "",
    solution: str = "",
    error_code: str = "",
    http_status: int = 400,
) -> dict:
    """
    Create a standardized error response dict.
    Use this for ALL error returns from route handlers.
    """
    resp = {
        "status": "error",
        "reason": reason,
        "evidence": evidence,
        "solution": solution,
    }
    if error_code:
        resp["error"] = error_code
    return resp


def error_json(
    reason: str,
    evidence: str = "",
    solution: str = "",
    http_status: int = 400,
) -> JSONResponse:
    """Create a standardized JSONResponse for use in middleware/exception handlers."""
    return JSONResponse(
        status_code=http_status,
        content={
            "status": "error",
            "reason": reason,
            "evidence": evidence,
            "solution": solution,
        },
    )


class ErrorMiddleware(BaseHTTPMiddleware):
    """
    Global middleware that catches ALL unhandled exceptions and returns
    them in the standard reason/evidence/solution format.
    This is the LAST safety net — no raw 500 errors should ever reach the client.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            tb = traceback.format_exc()
            logger.exception(f"[ERROR_MIDDLEWARE] Unhandled exception on {request.url.path}")

            # Classify the error
            exc_type = type(exc).__name__
            exc_msg = str(exc)[:300]

            if "timeout" in exc_msg.lower() or "timedout" in exc_type.lower():
                return error_json(
                    reason="Request timed out",
                    evidence=f"Operation exceeded the time limit on {request.url.path}",
                    solution="Try again. If the issue persists, check the server logs for bottlenecks.",
                    http_status=504,
                )
            elif "permission" in exc_msg.lower() or "forbidden" in exc_msg.lower():
                return error_json(
                    reason="Permission denied",
                    evidence=exc_msg,
                    solution="Check your API key permissions or contact support.",
                    http_status=403,
                )
            elif "not found" in exc_msg.lower():
                return error_json(
                    reason="Resource not found",
                    evidence=exc_msg,
                    solution="Verify the resource path and try again.",
                    http_status=404,
                )
            else:
                return error_json(
                    reason="Internal server error",
                    evidence=f"{exc_type}: {exc_msg}",
                    solution="This is a server-side issue. Check the backend logs for details.",
                    http_status=500,
                )
