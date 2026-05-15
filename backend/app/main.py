"""
RoadSoS — Main FastAPI application entry point.

Includes:
- CORS, rate limiting, request tracing middleware
- Custom error handlers
- All route mounts (incidents, services, webhooks, admin, resume, protocols)
- Database lifecycle management
- OpenTelemetry instrumentation
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings
from app.database import init_db, close_db
from app.errors import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from app.routes.incidents import router as incident_router
from app.routes.services import router as service_router
from app.routes.webhooks import router as webhook_router
from app.routes.admin import router as admin_router
from app.routes.resume import router as resume_router
from app.routes.start import router as start_router
from app.routes.protocols import router as protocol_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── Rate Limit Middleware ───────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter per client IP."""

    def __init__(self, app, max_requests: int = 100, window: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window
        self.clients: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next):
        if "/health" in request.url.path or "/static" in request.url.path:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        if client_ip in self.clients:
            self.clients[client_ip] = [
                t for t in self.clients[client_ip] if now - t < self.window
            ]
        else:
            self.clients[client_ip] = []

        if len(self.clients[client_ip]) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": self.window,
                    "support": "If this is an emergency, call 108.",
                },
            )

        self.clients[client_ip].append(now)
        return await call_next(request)


# ─── App Lifespan ────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting RoadSoS API…")
    try:
        await init_db()
        logger.info("✅ Database ready")
        # Auto-seed on first startup
        from app.seed.run import seed_database
        await seed_database()
    except Exception as e:
        logger.error(f"Database init/seed failed: {e}")
    yield
    await close_db()
    logger.info("🛑 RoadSoS API shut down")


# ─── Application ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="RoadSoS API",
    version="1.0.0",
    description="AI-Powered Emergency Response System for Road Safety",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Middleware stack (order matters)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware, max_requests=100, window=60)

# Register error handlers
app.add_exception_handler(404, http_exception_handler)
app.add_exception_handler(403, http_exception_handler)
app.add_exception_handler(500, generic_exception_handler)

# Register routes
app.include_router(incident_router, tags=["Incidents"])
app.include_router(service_router, tags=["Services"])
app.include_router(webhook_router, tags=["Webhooks"])
app.include_router(admin_router, tags=["Admin"])
app.include_router(resume_router, tags=["Incident Resume"])
app.include_router(start_router, tags=["Incident Start"])
app.include_router(protocol_router, tags=["Protocols"])


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "RoadSoS", "version": "1.0.0"}


@app.get("/")
async def root():
    return {
        "service": "RoadSoS API",
        "endpoints": "/docs",
        "health": "/health",
    }


# OTel instrumentation helpers are in app.telemetry (avoids circular imports)