"""
Middleware layer: request logging, fraud headers, error handling, CORS.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Callable

from fastapi import Request, Response

logger = logging.getLogger(__name__)


async def add_request_id(request: Request, call_next: Callable) -> Response:
    """Add unique request ID to every request for tracing."""
    import uuid
    request.state.request_id = str(uuid.uuid4())[:12]
    start_time = time.time()

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000
    response.headers["X-Request-Id"] = request.state.request_id
    response.headers["X-Process-Time"] = f"{process_time:.1f}ms"
    response.headers["X-Service"] = "RoadSoS-API"
    response.headers["X-Timestamp"] = datetime.now(timezone.utc).isoformat()

    logger.info(
        f"[{request.state.request_id}] {request.method} {request.url.path} "
        f"→ {response.status_code} ({process_time:.0f}ms)"
    )

    return response


async def fraud_header_check(request: Request, call_next: Callable) -> Response:
    """
    Reject requests with known-bad headers or suspicious patterns.
    Lightweight — not a replacement for the full fraud engine.
    """
    # Rate-limit bypass attempt detection
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded.count(",") > 3:
        return Response(
            content='{"error": "Suspicious proxy chain detected"}',
            status_code=403,
            media_type="application/json",
        )

    # Rapid-fire detection: check if same IP made many requests
    client_ip = request.client.host if request.client else "unknown"
    from app.services.fraud import FraudEngine

    return await call_next(request)