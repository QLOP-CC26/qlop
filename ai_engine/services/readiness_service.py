"""Readiness Scoring Service.

Ported from api_recommendation/app.py — SBERT `all-MiniLM-L6-v2`
cosine similarity against precomputed job posting embeddings.
"""

from __future__ import annotations

import logging
from collections import defaultdict

import numpy as np

from core.model_loader import registry
from schemas.analyze import ReadinessResult
from utils.skill_normalizer import fuzzy_match_skill, safe_float

logger = logging.getLogger("qlop.readiness")


def score(cv_skills: list[str], target_role: str) -> ReadinessResult:
    """
    Compute readiness score for *target_role* given the user's flat skill list.

    score = (user contribution mass) / (total contribution mass across all skills)
    """
    r = registry

    if target_role not in r.job_embeddings:
        raise ValueError(f"Role '{target_role}' not recognized.")

    vocab_keys = list(r.skill_to_idx_li.keys())
    user_skills: list[str] = []
    for s in cv_skills:
        s_lower = s.lower().strip()
        if s_lower in r.skill_to_idx_li:
            user_skills.append(s_lower)
        else:
            # Threshold 0.75 avoids false positives (e.g. "Postman" → "kicad")
            best = fuzzy_match_skill(s_lower, vocab_keys, threshold=0.75)
            if best:
                user_skills.append(best)

    if not user_skills:
        return ReadinessResult(
            score=0.0,
            matched_skills=[],
            interpretation="No skills could be recognized.",
        )

    user_text = " ".join(user_skills)
    user_emb = r.sbert_model.encode([user_text], convert_to_tensor=False)[0].astype(np.float32)

    job_embeds = r.job_embeddings[target_role]
    job_skill_lists = r.job_skills_list_all.get(target_role, [])

    user_norm = user_emb / (np.linalg.norm(user_emb) + 1e-9)
    job_norms = np.linalg.norm(job_embeds, axis=1, keepdims=True)
    job_embeds_norm = job_embeds / (job_norms + 1e-9)
    sims = np.dot(job_embeds_norm, user_norm)

    skill_contrib: dict[str, float] = defaultdict(float)
    for i, job_skills in enumerate(job_skill_lists):
        sim = float(sims[i])
        for skill in job_skills:
            skill_contrib[skill] += sim

    total_contrib = sum(skill_contrib.values())
    if total_contrib == 0:
        return ReadinessResult(
            score=0.0,
            matched_skills=user_skills,
            interpretation="No job posting data available for this role.",
        )

    user_contrib = sum(skill_contrib.get(skill, 0) for skill in user_skills)
    final_score = user_contrib / total_contrib

    return ReadinessResult(
        score=round(safe_float(final_score), 4),
        matched_skills=user_skills,
        interpretation=(
            "This score indicates how well your skills align with overall market demand. "
            "The higher the score (closer to 1), the more market-ready you are."
        ),
    )
