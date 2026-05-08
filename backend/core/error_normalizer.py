"""
Error Response Normalizer
======================================
Applies error normalization as FastAPI exception handlers to avoid
Content-Length conflicts with Sentry SDK.
"""
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        reason = detail.get("reason", detail.get("message", detail.get("error", "An error occurred")))
        evidence = detail.get("evidence", detail.get("details", f"HTTP {exc.status_code}"))
        solution = detail.get("solution", "Check the error details and try again.")
    else:
        reason = str(detail)
        evidence = f"HTTP {exc.status_code}"
        solution = "Check the request parameters and try again."

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "reason": reason,
            "evidence": evidence,
            "solution": solution,
        }
    )

async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "reason": "Validation Error",
            "evidence": str(exc.errors()),
            "solution": "Ensure the request parameters match the required schema.",
        }
    )

async def custom_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception on {request.url.path}")
    exc_type = type(exc).__name__
    exc_msg = str(exc)[:300]
    
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "reason": "Internal server error",
            "evidence": f"{exc_type}: {exc_msg}",
            "solution": "This is a server-side issue. Check the backend logs for details.",
        }
    )

def setup_exception_handlers(app):
    app.add_exception_handler(StarletteHTTPException, custom_http_exception_handler)
    app.add_exception_handler(RequestValidationError, custom_validation_exception_handler)
    app.add_exception_handler(Exception, custom_exception_handler)
