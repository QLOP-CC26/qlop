"""Fase 2 — Parallel Analysis endpoint.

Receives edited CVProfile + target_role, runs Model 2+3 (gap + courses)
and Model 4 (readiness) in parallel via asyncio.gather, returns unified result.
"""

from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, HTTPException

from core.model_loader import registry
from schemas.analyze import AnalyzeData, AnalyzeRequest
from schemas.envelope import success_envelope
from services import recommendation_service, readiness_service
from utils.skill_normalizer import flatten_skills

logger = logging.getLogger("qlop.router.analyze")
router = APIRouter(prefix="/api/v1/cv", tags=["analyze"])


@router.post("/analyze")
async def analyze_endpoint(body: AnalyzeRequest):
    start = time.perf_counter()

    target_role = body.target_role.strip()
    if target_role not in registry.role_to_idx:
        # case-insensitive fallback: accept "data scientist" → canonical "Data Scientist"
        lower_map = {k.lower(): k for k in registry.role_to_idx}
        canonical = lower_map.get(target_role.lower())
        if canonical:
            target_role = canonical
        else:
            valid = ", ".join(sorted(registry.role_to_idx.keys()))
            raise HTTPException(status_code=400, detail=f"Role '{target_role}' tidak dikenali. Role yang valid: {valid}")

    cv_skills = flatten_skills(body.profile.skills)
    if not cv_skills:
        raise HTTPException(status_code=400, detail="Tidak ada skill yang terdeteksi dalam profil.")

    loop = asyncio.get_running_loop()

    async def run_recommendation():
        return await loop.run_in_executor(
            None, recommendation_service.analyze, cv_skills, target_role,
        )

    async def run_readiness():
        return await loop.run_in_executor(
            None, readiness_service.score, cv_skills, target_role,
        )

    try:
        (skill_gap, courses), readiness_result = await asyncio.gather(
            run_recommendation(),
            run_readiness(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Analysis pipeline failed")
        raise HTTPException(status_code=500, detail="Analisis gagal diproses.") from exc

    elapsed = int((time.perf_counter() - start) * 1000)

    data = AnalyzeData(
        profile=body.profile,
        target_role=target_role,
        skill_gap=skill_gap,
        course_recommendations=courses,
        readiness_score=readiness_result,
    )

    return success_envelope(
        data=data.model_dump(),
        metadata={
            "target_role": target_role,
            "cv_skills_count": len(cv_skills),
            "processing_time_ms": elapsed,
            "concurrency_strategy": "asyncio.gather",
        },
    )
