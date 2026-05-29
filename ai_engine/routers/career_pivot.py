"""Fase 3 — Career Pivot Radar endpoint.

Receives the full analysis payload from Fase 2, runs SBERT role retrieval
and 3-turn multi-turn LLM conversation, returns structured CareerPivotOutput.
"""

from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, HTTPException

from core.config import settings
from core.model_loader import registry
from schemas.career_pivot import CareerPivotRequest
from schemas.envelope import success_envelope
from services.career_pivot_service import generate_career_pivot, retrieve_alternative_roles
from utils.skill_normalizer import flatten_skills

logger = logging.getLogger("qlop.router.career_pivot")
router = APIRouter(prefix="/api/v1/cv", tags=["career-pivot"])


@router.post("/career-pivot")
async def career_pivot_endpoint(body: CareerPivotRequest):
    start = time.perf_counter()

    if not settings.groq_api_key:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY belum dikonfigurasi. Career Pivot Radar tidak tersedia.",
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
            raise HTTPException(status_code=400, detail=f"Role '{target_role}' tidak dikenali. Role yang valid: {valid}")

    cv_skills = flatten_skills(body.profile.skills)

    if not cv_skills:
        raise HTTPException(status_code=400, detail="Tidak ada skill yang terdeteksi dalam profil.")

    loop = asyncio.get_running_loop()

    # Stage A — RAG retrieval (synchronous SBERT, offloaded to executor)
    retrieved_roles = await loop.run_in_executor(
        None, retrieve_alternative_roles, cv_skills, target_role, 5,
    )

    if not retrieved_roles:
        raise HTTPException(status_code=400, detail="Tidak dapat menemukan role alternatif berdasarkan skill Anda.")

    # Stage B — Multi-turn LLM conversation (async)
    try:
        pivot_output = await generate_career_pivot(
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
            detail="openai package tidak terinstall. Jalankan: pip install openai>=1.30.0",
        ) from exc
    except Exception as exc:
        err_str = str(exc)
        # API key / auth / quota → 503
        if any(k in err_str for k in (
            "GROQ_API_KEY", "api_key", "invalid_api_key",
            "rate_limit_exceeded", "429", "401", "403",
            "model_not_found", "404",
        )):
            logger.error("Groq API error: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=f"Groq API tidak dapat diakses. Periksa GROQ_API_KEY di .env: {exc}",
            ) from exc
        # JSON parse failure → 503 (LLM output issue, retry)
        if any(k in err_str for k in ("malformed JSON", "validation error", "JSON", "parse")):
            logger.error("LLM returned invalid structured output: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=f"Model AI mengembalikan output yang tidak valid. Coba lagi: {exc}",
            ) from exc
        logger.exception("Career pivot LLM generation failed")
        raise HTTPException(status_code=500, detail=f"Gagal menghasilkan analisis karier: {exc}") from exc

    elapsed = int((time.perf_counter() - start) * 1000)

    return success_envelope(
        data=pivot_output.model_dump(),
        metadata={
            "retrieval_method": "sbert_role_centroid_cosine",
            "roles_evaluated": len(registry.role_centroids),
            "roles_returned": len(retrieved_roles),
            "llm_model": settings.groq_model,
            "llm_turns": 3,
            "processing_time_ms": elapsed,
        },
    )
