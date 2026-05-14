"""
Custom exception handlers for RoadSoS API.
"""
import json
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "path": request.url.path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


async def validation_exception_handler(request: Request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "detail": json.dumps(exc.errors()) if hasattr(exc, "errors") else str(exc),
            "path": request.url.path,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error in {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error. Your incident is still being processed.",
            "incident_support": "Contact 108 for immediate assistance.",
            "path": request.url.path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )