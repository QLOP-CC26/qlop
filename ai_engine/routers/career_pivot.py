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

    if not settings.google_api_key:
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_API_KEY belum dikonfigurasi. Career Pivot Radar tidak tersedia.",
        )

    target_role = body.target_role.strip()
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
        logger.error("google-genai not installed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="google-genai package tidak terinstall. Jalankan: pip install google-genai",
        ) from exc
    except Exception as exc:
        err_str = str(exc)
        # API config / quota / auth → 503
        if any(k in err_str for k in (
            "API_KEY", "NOT_FOUND", "PERMISSION_DENIED", "UNAUTHENTICATED",
            "RESOURCE_EXHAUSTED", "401", "403", "404", "429",
        )):
            logger.error("Gemini API config error: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=f"Gemini API tidak dapat diakses. Periksa GOOGLE_API_KEY dan GEMINI_MODEL di .env: {exc}",
            ) from exc
        # Pydantic/JSON parse failure after Gemini call → 503 (not our bug, LLM output problem)
        if any(k in err_str for k in ("validation error", "malformed JSON", "JSON", "parse")):
            logger.error("Gemini returned invalid structured output: %s", exc)
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
            "llm_model": settings.gemini_model,
            "llm_turns": 3,
            "processing_time_ms": elapsed,
        },
    )
