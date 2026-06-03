"""Fase 3 — Career Pivot Radar endpoint.

Receives the full analysis payload from Fase 2, runs SBERT role retrieval
and 3-turn multi-turn LLM conversation, returns structured CareerPivotOutput.
"""

from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, HTTPException, Request
from utils.rate_limiter import limiter

from core.config import settings
from core.model_loader import registry
from schemas.career_pivot import CareerPivotRequest
from schemas.envelope import success_envelope
from services.career_pivot_service import generate_career_pivot, retrieve_alternative_roles
from utils.skill_normalizer import flatten_skills

logger = logging.getLogger("qlop.router.career_pivot")
router = APIRouter(prefix="/api/v1/cv", tags=["career-pivot"])


@router.post("/career-pivot")
@limiter.limit("60/minute")
async def career_pivot_endpoint(request: Request, body: CareerPivotRequest):
    start = time.perf_counter()


    if settings.llm_provider == "groq" and not settings.groq_api_key:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY is not configured. Career Pivot Radar is unavailable.",
        )

    target_role = body.target_role.strip()

    # case-insensitive role normalisation (mirrors /analyze behaviour)
    if target_role not in registry.role_centroids:
        lower_map = {k.lower(): k for k in registry.role_centroids}
        canonical = lower_map.get(target_role.lower())
        if canonical:
            target_role = canonical
        else:
            valid = ", ".join(sorted(registry.role_centroids.keys()))
            raise HTTPException(status_code=400, detail=f"Role '{target_role}' not recognized. Valid roles: {valid}")

    cv_skills = flatten_skills(body.profile.skills)
    designations = [w.designation for w in body.profile.work_experience if w.designation]

    if not cv_skills:
        raise HTTPException(status_code=400, detail="No skills detected in the profile.")

    loop = asyncio.get_running_loop()

    # Stage A — RAG retrieval (synchronous SBERT, offloaded to executor)
    retrieved_roles = await loop.run_in_executor(
        None, retrieve_alternative_roles, cv_skills, target_role, settings.career_pivot_top_k, designations,
    )

    if not retrieved_roles:
        raise HTTPException(status_code=400, detail="No alternative roles found based on your profile.")

    # Stage B — Multi-turn LLM conversation (async)
    try:
        pivot_output, used_model = await generate_career_pivot(
            profile=body.profile,
            target_role=target_role,
            skill_gap=body.skill_gap,
            readiness=body.readiness_score,
            retrieved_roles=retrieved_roles,
        )
    except ImportError as exc:
        logger.error("openai package not installed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="openai package is not installed. Run: pip install openai>=1.30.0",
        ) from exc
    except Exception as exc:
        err_str = str(exc)
        # API key / auth / quota → 503
        if any(k in err_str for k in (
            "GROQ_API_KEY", "api_key", "invalid_api_key",
            "rate_limit_exceeded", "429", "401", "403", "413",
            "Request too large", "Payload Too Large",
            "model_not_found", "404", "Application Default Credentials",
            "gcloud", "google-auth"
        )):
            logger.error("LLM API error: %s", exc)
            if "413" in err_str or "Request too large" in err_str or "Payload Too Large" in err_str:
                detail = (
                    "Request exceeds model token limit (prompt + max_tokens). "
                    "Reduce MAX_TOKENS, or lower CAREER_PIVOT_TOP_K."
                )
            else:
                detail = f"LLM API is unreachable. Check LLM provider configuration in .env: {exc}"
            raise HTTPException(status_code=503, detail=detail) from exc
        # JSON parse failure → 503 (LLM output issue, retry)
        if any(k in err_str for k in ("malformed JSON", "validation error", "JSON", "parse")):
            logger.error("LLM returned invalid structured output: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=f"AI model returned invalid output. Please try again: {exc}",
            ) from exc
        logger.exception("Career pivot LLM generation failed")
        raise HTTPException(status_code=500, detail=f"Failed to generate career analysis: {exc}") from exc

    elapsed = int((time.perf_counter() - start) * 1000)

    return success_envelope(
        data=pivot_output.model_dump(),
        metadata={
            "retrieval_method": "sbert_role_centroid_cosine",
            "roles_evaluated": len(registry.role_centroids),
            "roles_returned": len(retrieved_roles),
            "llm_model": used_model,
            "llm_turns": 1,
            "processing_time_ms": elapsed,
        },
    )
