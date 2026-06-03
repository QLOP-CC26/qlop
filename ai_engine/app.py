"""QLOP Unified AI REST API — FastAPI Entry Point.

Three endpoints served through a single app:
  POST /api/v1/cv/extract      — Fase 1: NER extraction from Cloudinary URL
  POST /api/v1/cv/analyze      — Fase 2: parallel skill gap + courses + readiness
  POST /api/v1/cv/career-pivot  — Fase 3: Career Pivot Radar (RAG + multi-turn LLM)
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.model_loader import registry
from schemas.envelope import error_envelope
from utils.security import verify_api_key
from utils.rate_limiter import limiter
from slowapi.errors import RateLimitExceeded

# ──────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-28s  %(levelname)-5s  %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("qlop")


# ──────────────────────────────────────────────────────────────────────
# Lifespan — load all models once at startup
# ──────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting QLOP AI Engine — loading models …")
    registry.load_all()
    logger.info("All models loaded. API ready.")

    from core.config import settings as _s
    if not _s.groq_api_key:
        logger.warning(
            "GROQ_API_KEY is not set in .env — "
            "POST /api/v1/cv/career-pivot will return 503 until the key is configured."
        )

    yield
    logger.info("Shutting down QLOP AI Engine.")


# ──────────────────────────────────────────────────────────────────────
# App factory
# ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="QLOP AI Engine",
    version="2.1.0",
    description="Unified CV analysis API with NER, skill gap, course recommendations, readiness scoring, and career pivot radar.",
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)

# Register rate limiter on FastAPI application state
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # must be False when allow_origins=["*"]; set specific origins when auth is added (v2.2)
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────
# Global middleware
# ──────────────────────────────────────────────────────────────────────

@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Rejects POST requests exceeding 10MB to prevent denial of service."""
    if request.method == "POST":
        content_length = request.headers.get("content-length")
        if content_length:
            if int(content_length) > 10 * 1024 * 1024:  # 10MB limit
                return JSONResponse(
                    status_code=413,
                    content=error_envelope(detail="Request payload too large.", code=413),
                )
    return await call_next(request)


# ──────────────────────────────────────────────────────────────────────
# Global exception handlers
# ──────────────────────────────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_envelope(detail=exc.detail, code=exc.status_code),
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_envelope(detail="Validation error", code=422, metadata={"errors": exc.errors()}),
    )


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content=error_envelope(detail=str(exc), code=400),
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(_: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content=error_envelope(detail="Rate limit exceeded. Please try again later.", code=429),
    )


@app.exception_handler(Exception)
async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content=error_envelope(detail="Internal server error.", code=500),
    )


# ──────────────────────────────────────────────────────────────────────
# Register routers
# ──────────────────────────────────────────────────────────────────────

from routers.extract import router as extract_router  # noqa: E402
from routers.analyze import router as analyze_router  # noqa: E402
from routers.career_pivot import router as career_pivot_router  # noqa: E402

# Enforce verify_api_key on all API routers
app.include_router(extract_router, dependencies=[Depends(verify_api_key)])
app.include_router(analyze_router, dependencies=[Depends(verify_api_key)])
app.include_router(career_pivot_router, dependencies=[Depends(verify_api_key)])


# ──────────────────────────────────────────────────────────────────────
# Roles list
# ──────────────────────────────────────────────────────────────────────

@app.get("/api/v1/roles", dependencies=[Depends(verify_api_key)])
async def get_roles():
    roles = sorted(registry.role_to_idx.keys())
    from schemas.envelope import success_envelope
    return success_envelope(data={"roles": roles, "count": len(roles)})


# ──────────────────────────────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "ner_available": registry.ner_available,
        "model3_available": registry.infer3 is not None,
        "model4_available": registry.infer4 is not None,
        "roles_loaded": len(registry.role_to_idx),
        "sbert_loaded": registry.sbert_model is not None,
        "role_centroids": len(registry.role_centroids),
    }

