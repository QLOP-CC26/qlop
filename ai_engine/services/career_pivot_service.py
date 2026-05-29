"""Career Pivot Radar Service.

Stage A — Lightweight RAG: SBERT role centroid cosine similarity.
Stage B — Single-shot Groq/Llama call with chain-of-thought embedded in system prompt.

LLM Stack: openai SDK → Groq endpoint (llama-3.3-70b-versatile, free tier)
  Single call with json_object mode (temperature 0.15)

Single-shot replaced the previous 3-turn approach to reduce Groq token usage by ~60%
and eliminate 429 rate-limit retries caused by accumulated message context ballooning
across turns.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import openai

import numpy as np

from core.config import settings
from core.model_loader import registry
from schemas.analyze import ReadinessResult, SkillGap
from schemas.career_pivot import CareerPivotOutput
from schemas.cv_profile import CVProfile
from utils.skill_normalizer import flatten_skills, fuzzy_match_skill

logger = logging.getLogger("qlop.career_pivot")


# ──────────────────────────────────────────────────────────────────────
# Data class for retrieval stage
# ──────────────────────────────────────────────────────────────────────

class RetrievedRole:
    __slots__ = ("role_name", "sbert_score", "skill_overlap_pct", "matched_skills", "gap_skills")

    def __init__(
        self,
        role_name: str,
        sbert_score: float,
        skill_overlap_pct: float,
        matched_skills: list[str],
        gap_skills: list[str],
    ) -> None:
        self.role_name = role_name
        self.sbert_score = sbert_score
        self.skill_overlap_pct = skill_overlap_pct
        self.matched_skills = matched_skills
        self.gap_skills = gap_skills

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_name": self.role_name,
            "sbert_match_score": round(self.sbert_score, 4),
            "skill_overlap_pct": round(self.skill_overlap_pct, 2),
            "matched_skills": self.matched_skills,
            "gap_skills": self.gap_skills,
        }


# ──────────────────────────────────────────────────────────────────────
# Stage A — RAG Retrieval (pure Python, no LLM)
# ──────────────────────────────────────────────────────────────────────

def retrieve_alternative_roles(
    cv_skills: list[str],
    target_role: str,
    top_k: int = 5,
) -> list[RetrievedRole]:
    """
    Encode user skills with SBERT → cosine similarity against all precomputed
    role centroids → return top-k alternative roles (excluding target_role).

    role_centroids are computed once at startup in ModelRegistry.
    """
    r = registry

    if not r.role_centroids:
        return []

    vocab_keys = list(r.skill_to_idx_li.keys())
    normalised: list[str] = []
    for s in cv_skills:
        s_lower = s.lower().strip()
        if s_lower in r.skill_to_idx_li:
            normalised.append(s_lower)
        else:
            best = fuzzy_match_skill(s_lower, vocab_keys, threshold=0.75)
            if best:
                normalised.append(best)

    if not normalised:
        return []

    if not r.sbert_model:
        return []

    user_text = " ".join(normalised)
    user_emb = np.array(r.sbert_model.encode([user_text], convert_to_tensor=False)[0]).astype(np.float32)
    user_norm = user_emb / (np.linalg.norm(user_emb) + 1e-9)

    scored: list[tuple[str, float]] = []
    for role, centroid in r.role_centroids.items():
        if role == target_role:
            continue
        centroid_norm = centroid / (np.linalg.norm(centroid) + 1e-9)
        sim = float(np.dot(user_norm, centroid_norm))
        scored.append((role, sim))

    scored.sort(key=lambda x: x[1], reverse=True)

    results: list[RetrievedRole] = []
    for role_name, sbert_score in scored[:top_k]:
        role_skills_freq = r.role_freq.get(role_name, {})
        important_skills = {s for s, f in role_skills_freq.items() if f >= 0.1}

        matched = [s for s in normalised if s in important_skills]
        gap = [s for s in important_skills if s not in set(normalised)]

        overlap_pct = (len(matched) / len(important_skills) * 100) if important_skills else 0.0

        results.append(RetrievedRole(
            role_name=role_name,
            sbert_score=sbert_score,
            skill_overlap_pct=overlap_pct,
            matched_skills=matched,
            gap_skills=gap[:10],
        ))

    return results


# ──────────────────────────────────────────────────────────────────────
# Stage B helpers — prompt builders
# ──────────────────────────────────────────────────────────────────────

_SYSTEM_INSTRUCTION = (
    "You are an IT career coach for 2026. "
    "Analyse the candidate profile thoroughly using work history as primary signal, not just the skills list. "
    "Respond ONLY with valid JSON — no markdown, no extra text."
)


def _readiness_level(score: float) -> str:
    if score >= 0.75:
        return "excellent"
    if score >= 0.55:
        return "high"
    if score >= 0.35:
        return "moderate"
    return "low"


def _build_single_shot_prompt(
    profile: CVProfile,
    target_role: str,
    readiness: ReadinessResult,
    retrieved_roles: list[RetrievedRole],
    skill_gap: SkillGap,
) -> str:
    """Build a single self-contained prompt that replaces the previous 3-turn chain.

    Embedding chain-of-thought instructions directly into one prompt cuts token
    usage by ~60 % and eliminates the 429s caused by growing accumulated context.
    """
    skills_flat = flatten_skills(profile.skills)
    work_entries = [w for w in profile.work_experience if w.company]
    work_str = "; ".join(
        f"{w.designation} @ {w.company} ({w.duration})" for w in work_entries
    ) or "not available"
    edu_str = "; ".join(
        f"{e.degree} — {e.institution}" for e in profile.education if e.institution
    ) or "not available"
    designations = [w.designation for w in work_entries if w.designation]
    traj_hint = " → ".join(designations[-3:]) if designations else "unknown"

    missing_str = ", ".join(m.skill for m in skill_gap.missing_skills[:5]) or "none"
    layer1_names = [r.role_name for r in retrieved_roles]
    roles_compact = json.dumps(
        [r.to_dict() for r in retrieved_roles], ensure_ascii=False, separators=(",", ":")
    )

    # Build transferable_skills objects so the LLM fills relevance per role
    alt_role_template = [
        {
            "role_name": r.role_name,
            "sbert_match_score": round(r.sbert_score, 4),
            "skill_overlap_pct": round(r.skill_overlap_pct, 2),
            "why_good_fit": "__FILL__ (cite specific work history, not generic)",
            "transferable_skills": [
                {"skill": "__FILL_SKILL__", "relevance": "__FILL_WHY_THIS_SKILL_MATTERS_FOR_THIS_ROLE__"},
                {"skill": "__FILL_SKILL__", "relevance": "__FILL_WHY_THIS_SKILL_MATTERS_FOR_THIS_ROLE__"},
                {"skill": "__FILL_SKILL__", "relevance": "__FILL_WHY_THIS_SKILL_MATTERS_FOR_THIS_ROLE__"},
            ],
            "gap_skills": r.gap_skills[:5],
            "transition_difficulty": "__FILL__",
            "estimated_transition_time": "__FILL__",
            "first_step": f"__FILL__ (specific action to become {r.role_name}, NOT generic)",
        }
        for r in retrieved_roles
    ]

    pre_filled = {
        "current_role_assessment": {
            "target_role": target_role,
            "readiness_score": readiness.score,
            "readiness_level": _readiness_level(readiness.score),
            "verdict": "__FILL__",
        },
        "alternative_roles": alt_role_template,
        "ai_discovered_roles": [
            {
                "role_name": "__FILL__",
                "category": "__FILL__",
                "why_good_fit": "__FILL__ (cite work history)",
                "transferable_skills": ["__FILL__", "__FILL__"],
                "skills_to_develop": ["__FILL__", "__FILL__"],
                "transition_difficulty": "__FILL__",
                "estimated_transition_months": 0,
                "skill_readiness_pct": 0.0,
                "first_step": "__FILL__ (specific, actionable)",
                "market_demand": "__FILL__",
            }
        ],
        "strongest_transferable_skills": ["__FILL__", "__FILL__", "__FILL__"],
        "suggested_certifications": [
            {"name": "__FILL__", "relevance": "__FILL_WHY_THIS_CERT__"},
            {"name": "__FILL__", "relevance": "__FILL_WHY_THIS_CERT__"},
        ],
        "universal_advice": "__FILL__",
    }

    return (
        "## CANDIDATE PROFILE\n"
        f"Name: {profile.name} | Experience: {profile.total_experience_years} yrs | Location: {profile.location}\n"
        f"Skills ({len(skills_flat)}): {', '.join(skills_flat[:18])}\n"
        f"Career trajectory: {traj_hint}\n"
        f"Work history: {work_str}\n"
        f"Education: {edu_str}\n"
        f"Target role: {target_role} | Readiness: {readiness.score:.2f} ({_readiness_level(readiness.score)})\n"
        f"Skill gap (top missing): {missing_str}\n\n"
        "## LAYER 1 — Roles from IT database (SBERT-matched, do NOT change numeric scores)\n"
        f"{roles_compact}\n\n"
        "## TASK\n"
        "Step 1 — Analyse work history: primary domain, career pattern, unique strengths.\n"
        "Step 2 — For each Layer 1 role, fill all __FILL__ fields:\n"
        "  - why_good_fit: cite SPECIFIC work experience, not generic phrases.\n"
        "  - transferable_skills: pick 3-5 skills from the candidate's profile that are MOST relevant "
        "    to THIS specific role. Each must have a relevance explaining why that skill applies to THIS role.\n"
        "  - first_step: a concrete, role-specific action (different for each role).\n"
        "  - transition_difficulty: easy|moderate|challenging\n"
        f"Step 3 — Identify 3 roles DIFFERENT from {layer1_names} (from work history analysis). "
        "category: specialization|adjacent|leadership|pivot. market_demand: high|medium|low.\n"
        "Step 4 — suggested_certifications: 2-4 specific certs with relevance explaining why each cert helps.\n"
        "Step 5 — skill_readiness_pct = len(transferable_skills)/(len(transferable_skills)+len(skills_to_develop))*100.\n\n"
        "## CRITICAL RULES\n"
        "- transferable_skills must be role-specific — DO NOT copy the same list to every role.\n"
        "- first_step must be different and specific for each role.\n"
        "- relevance fields must NOT be empty.\n"
        "- Do not change any numeric values (readiness_score, sbert_match_score, skill_overlap_pct).\n\n"
        "## OUTPUT\n"
        "Return ONLY the completed JSON. Replace every __FILL__ token with real content.\n"
        f"{json.dumps(pre_filled, ensure_ascii=False, separators=(',', ':'))}"
    )


# ──────────────────────────────────────────────────────────────────────
# Stage B — Single-Shot Groq Call
# ──────────────────────────────────────────────────────────────────────

_GROQ_CALL_TIMEOUT = 90.0  # seconds — prevents hung Groq connections


def _groq_call(
    client: "openai.OpenAI",
    model: str,
    messages: list[dict],
    temperature: float,
) -> str:
    """Synchronous Groq call (json_object mode always on) — run in executor."""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=2500,
        timeout=_GROQ_CALL_TIMEOUT,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or ""


async def generate_career_pivot(
    profile: CVProfile,
    target_role: str,
    skill_gap: SkillGap,
    readiness: ReadinessResult,
    retrieved_roles: list[RetrievedRole],
) -> CareerPivotOutput:
    """Single-shot Groq call with chain-of-thought embedded in the prompt.

    Replaces the previous 3-turn approach. Token usage drops ~60% because
    accumulated assistant responses are no longer re-sent on every turn.
    API calls: 3 → 1, eliminating the main source of 429 rate-limit errors.
    """
    import openai  # lazy import — only needed when career pivot is called

    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY not configured")

    client = openai.OpenAI(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
    )
    model = settings.groq_model
    loop = asyncio.get_running_loop()

    prompt = _build_single_shot_prompt(profile, target_role, readiness, retrieved_roles, skill_gap)
    messages: list[dict] = [
        {"role": "system", "content": _SYSTEM_INSTRUCTION},
        {"role": "user", "content": prompt},
    ]

    raw_json = await loop.run_in_executor(
        None, lambda: _groq_call(client, model, messages, temperature=0.15)
    )
    logger.debug("Single-shot response received (%d chars)", len(raw_json))

    # Parse into Pydantic with fallback
    parsed: CareerPivotOutput | None = None
    try:
        parsed = CareerPivotOutput.model_validate_json(raw_json)
    except Exception as primary_exc:
        logger.warning("Strict JSON parse failed (%s), trying lenient fallback", primary_exc)
        try:
            start_idx = raw_json.find("{")
            end_idx = raw_json.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                parsed = CareerPivotOutput.model_validate_json(raw_json[start_idx:end_idx])
        except Exception as fallback_exc:
            logger.warning("Lenient JSON parse also failed (%s)", fallback_exc)
            raise RuntimeError(
                f"LLM returned malformed JSON. Primary: {primary_exc}. "
                f"Fallback: {fallback_exc}. Raw ({len(raw_json)} chars): {raw_json[:400]}"
            ) from fallback_exc

    if parsed is None:
        raise RuntimeError(f"No valid JSON found in LLM response: {raw_json[:400]}")

    # Post-process: recompute skill_readiness_pct server-side
    for ai_role in parsed.ai_discovered_roles:
        t = len(ai_role.transferable_skills)
        d = len(ai_role.skills_to_develop)
        total = t + d
        ai_role.skill_readiness_pct = round(t / total * 100, 1) if total > 0 else 0.0

    return parsed
