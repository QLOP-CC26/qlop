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
from utils.skill_normalizer import flatten_skills, fuzzy_match_skill, is_garbage

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

    def to_prompt_dict(self) -> dict[str, Any]:
        """Minimal payload for the LLM prompt — omits matched_skills to save tokens."""
        return {
            "role_name": self.role_name,
            "sbert_match_score": round(self.sbert_score, 4),
            "skill_overlap_pct": round(self.skill_overlap_pct, 2),
            "gap_skills": self.gap_skills[:3],
        }


# ──────────────────────────────────────────────────────────────────────
# Stage A — RAG Retrieval (pure Python, no LLM)
# ──────────────────────────────────────────────────────────────────────

def retrieve_alternative_roles(
    cv_skills: list[str],
    target_role: str,
    top_k: int = 5,
    designations: list[str] | None = None,
) -> list[RetrievedRole]:
    """
    Encode user skills and designations with SBERT → cosine similarity against all
    precomputed role centroids → return top-k alternative roles (excluding target_role).

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

    if not normalised and not designations:
        return []

    if not r.sbert_model:
        return []

    # Weighted Average embedding: 60% designations (experience), 40% skills
    if normalised and designations:
        skills_text = " ".join(normalised)
        designations_text = " ".join(designations)
        
        skills_emb = np.array(r.sbert_model.encode([skills_text], convert_to_tensor=False)[0]).astype(np.float32)
        designations_emb = np.array(r.sbert_model.encode([designations_text], convert_to_tensor=False)[0]).astype(np.float32)
        
        skills_norm = skills_emb / (np.linalg.norm(skills_emb) + 1e-9)
        designations_norm = designations_emb / (np.linalg.norm(designations_emb) + 1e-9)
        
        user_emb = 0.4 * skills_norm + 0.6 * designations_norm
    elif normalised:
        skills_text = " ".join(normalised)
        user_emb = np.array(r.sbert_model.encode([skills_text], convert_to_tensor=False)[0]).astype(np.float32)
    else:
        designations_text = " ".join(designations)
        user_emb = np.array(r.sbert_model.encode([designations_text], convert_to_tensor=False)[0]).astype(np.float32)

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
    "IT career coach, 2026. Use work history as primary signal. "
    "JSON only. Be specific, concise, non-generic. "
    "First perform step-by-step reasoning (under 100 words) in the 'thinking_process' field. "
    "Each skill relevance: evidence + role task + impact (≥12 words). "
    "No boilerplate like 'has experience with' or 'fundamental skill'. "
    "first_step = actionable within 1-2 weeks, unique per role."
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
    
    # Filter out garbage work experience
    work_entries = []
    for w in profile.work_experience:
        comp = w.company.strip() if w.company else ""
        desg = w.designation.strip() if w.designation else ""
        if not comp or is_garbage(comp):
            continue
        if is_garbage(desg):
            desg = ""
        work_entries.append((comp, desg))
    work_entries = work_entries[:4]

    work_str = "; ".join(
        f"{desg} @ {comp}" if desg else comp for comp, desg in work_entries
    ) or "not available"

    # Filter out garbage education
    edu_entries = []
    for e in profile.education:
        deg = e.degree.strip() if e.degree else ""
        inst = e.institution.strip() if e.institution else ""
        if not inst or is_garbage(inst):
            continue
        if is_garbage(deg):
            deg = ""
        edu_entries.append((inst, deg))
    edu_entries = edu_entries[:4]

    edu_str = "; ".join(
        f"{deg} — {inst}" if deg else inst for inst, deg in edu_entries
    ) or "not available"

    designations = [desg for comp, desg in work_entries if desg]
    traj_hint = " → ".join(designations[-3:]) if designations else "unknown"

    missing_str = ", ".join(m.skill for m in skill_gap.missing_skills[:4]) or "none"
    layer1_names = [r.role_name for r in retrieved_roles]
    roles_compact = json.dumps(
        [r.to_prompt_dict() for r in retrieved_roles], ensure_ascii=False, separators=(",", ":")
    )

    alt_role_template = [
        {
            "role_name": r.role_name,
            "sbert_match_score": round(r.sbert_score, 4),
            "skill_overlap_pct": round(r.skill_overlap_pct, 2),
            "why_good_fit": "__FILL__",
            "transferable_skills": [
                {"skill": "__FILL__", "relevance": "__FILL__"},
                {"skill": "__FILL__", "relevance": "__FILL__"},
            ],
            "gap_skills": r.gap_skills[:3],
            "transition_difficulty": "__FILL__",
            "estimated_transition_time": "__FILL__",
            "first_step": "__FILL__",
        }
        for r in retrieved_roles
    ]

    pre_filled = {
        "thinking_process": "Write step-by-step reasoning details here (e.g. analyzing candidate's background, skill gap, and why target role makes sense).",
        "current_role_assessment": {
            "target_role": target_role,
            "readiness_score": readiness.score,
            "readiness_level": _readiness_level(readiness.score),
            "verdict": "__FILL__",
        },
        "strongest_transferable_skills": ["__FILL__", "__FILL__", "__FILL__"],
        "suggested_certifications": [
            {"name": "__FILL__", "relevance": "__FILL__"},
            {"name": "__FILL__", "relevance": "__FILL__"},
        ],
        "universal_advice": "__FILL__",
        "alternative_roles": alt_role_template,
        "ai_discovered_roles": [
            {
                "role_name": "__FILL__",
                "category": "__FILL__",
                "why_good_fit": "__FILL__",
                "transferable_skills": ["__FILL__", "__FILL__"],
                "skills_to_develop": ["__FILL__", "__FILL__"],
                "transition_difficulty": "__FILL__",
                "estimated_transition_months": 0,
                "skill_readiness_pct": 0.0,
                "first_step": "__FILL__",
                "market_demand": "__FILL__",
            }
        ],
    }

    return (
        f"CANDIDATE: {profile.name} | {profile.total_experience_years}y | {profile.location}\n"
        f"Skills: {', '.join(skills_flat[:12])}\n"
        f"Trajectory: {traj_hint}\n"
        f"Work: {work_str}\n"
        f"Education: {edu_str}\n"
        f"Target: {target_role} | Readiness: {readiness.score:.2f} | Gap: {missing_str}\n\n"
        f"LAYER1_ROLES (keep numeric scores): {roles_compact}\n\n"
        "TASK: Fill JSON template. Replace __FILL__ with real content.\n"
        "- thinking_process: Write step-by-step reasoning analysis first\n"
        "- alternative_roles: role-specific skills (2 each) + unique first_step per role\n"
        "- ai_discovered_roles: 3 roles NOT in Layer1, category=specialization|adjacent|leadership|pivot\n"
        "- transition_difficulty: easy|moderate|challenging | estimated_transition_time: string e.g. '6 months'\n"
        "- skill_readiness_pct = transferable/(transferable+skills_to_develop)*100\n"
        f"- ai_discovered_roles must differ from: {layer1_names}\n\n"
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
    max_tokens: int,
) -> str:
    """Synchronous Groq call (json_object mode always on) — run in executor."""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
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
) -> tuple[CareerPivotOutput, str]:
    """Single-shot LLM call with chain-of-thought embedded in the prompt.

    Replaces the previous 3-turn approach. Token usage drops ~60% because
    accumulated assistant responses are no longer re-sent on every turn.
    API calls: 3 → 1, eliminating the main source of 429 rate-limit errors.
    """
    import openai  # lazy import — only needed when career pivot is called

    loop = asyncio.get_running_loop()

    use_gemini = (settings.llm_provider == "gemini")
    raw_json = ""
    used_model = ""

    if use_gemini:
        try:
            import google.auth
            import google.auth.transport.requests
        except ImportError as exc:
            logger.error("google-auth package not installed: %s", exc)
            raise RuntimeError("google-auth package is not installed. Run: pip install google-auth") from exc

        try:
            def _get_vertex_client():
                credentials, project_id = google.auth.default(
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                gcp_project = settings.vertex_project_id or project_id
                if not gcp_project:
                    raise ValueError("Could not determine Google Cloud project ID. Please set VERTEX_PROJECT_ID in .env")
                auth_req = google.auth.transport.requests.Request()
                credentials.refresh(auth_req)
                
                region = settings.vertex_region
                return openai.OpenAI(
                    api_key=credentials.token,
                    base_url=f"https://{region}-aiplatform.googleapis.com/v1/projects/{gcp_project}/locations/{region}/endpoints/openapi",
                )

            client = await loop.run_in_executor(None, _get_vertex_client)
            model = settings.gemini_model
            if not model.startswith("google/"):
                model = f"google/{model}"
            max_tokens = 8192
            used_model = model

            prompt = _build_single_shot_prompt(profile, target_role, readiness, retrieved_roles, skill_gap)
            messages: list[dict] = [
                {"role": "system", "content": _SYSTEM_INSTRUCTION},
                {"role": "user", "content": prompt},
            ]

            raw_json = await loop.run_in_executor(
                None,
                lambda: _groq_call(client, model, messages, temperature=0.15, max_tokens=max_tokens),
            )
            logger.info("Successfully received response from Gemini API model: %s", model)
        except Exception as exc:
            logger.warning("Gemini/Vertex AI call failed with error: %s. Falling back to Groq...", exc)
            if not settings.groq_api_key:
                logger.error("No Groq API key available for fallback.")
                raise exc
            use_gemini = False  # Trigger fallback below

    if not use_gemini:
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY not configured")

        client = openai.OpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
        )
        model = settings.groq_model
        max_tokens = settings.groq_max_tokens
        used_model = model

        prompt = _build_single_shot_prompt(profile, target_role, readiness, retrieved_roles, skill_gap)
        messages: list[dict] = [
            {"role": "system", "content": _SYSTEM_INSTRUCTION},
            {"role": "user", "content": prompt},
        ]

        raw_json = await loop.run_in_executor(
            None,
            lambda: _groq_call(client, model, messages, temperature=0.15, max_tokens=max_tokens),
        )
        logger.info("Successfully received response from Groq API model: %s", model)

    logger.debug("Single-shot response received (%d chars)", len(raw_json))

    # ── Parse pipeline: 3 layers of increasing tolerance ─────────────────
    #
    # Layer 1 — strict: model_validate_json on raw output (fast path, no overhead)
    # Layer 2 — lenient: extract first {...} block (handles leading/trailing text)
    # Layer 3 — repair: json_repair reconstructs truncated / malformed JSON
    #           (handles truncated strings, missing closing brackets, trailing
    #           commas, unquoted keys — the most common LLM failure modes)
    #
    parsed: CareerPivotOutput | None = None
    repair_used = False

    # Layer 1 — strict
    try:
        parsed = CareerPivotOutput.model_validate_json(raw_json)
    except Exception as primary_exc:
        logger.debug("Layer 1 (strict) failed: %s", primary_exc)

    # Layer 2 — extract JSON block first, then validate
    if parsed is None:
        try:
            start_idx = raw_json.find("{")
            end_idx = raw_json.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                parsed = CareerPivotOutput.model_validate_json(raw_json[start_idx:end_idx])
        except Exception as lenient_exc:
            logger.debug("Layer 2 (lenient extract) failed: %s", lenient_exc)

    # Layer 3 — json_repair reconstructs malformed / truncated output
    if parsed is None:
        try:
            from json_repair import repair_json
            repaired = repair_json(raw_json, return_objects=False, ensure_ascii=False)
            parsed = CareerPivotOutput.model_validate_json(repaired)
            repair_used = True
            logger.info("Layer 3 (json_repair) recovered the LLM response (%d chars)", len(raw_json))
        except Exception as repair_exc:
            logger.warning("All 3 parse layers failed. Raw (%d chars): %s", len(raw_json), raw_json[:300])
            raise RuntimeError(
                f"LLM returned unrecoverable output after json_repair. "
                f"Error: {repair_exc}. Raw ({len(raw_json)} chars): {raw_json[:400]}"
            ) from repair_exc

    if parsed is None:
        raise RuntimeError(f"No valid JSON found in LLM response: {raw_json[:400]}")

    if repair_used:
        logger.warning(
            "json_repair was needed — LLM output was malformed. "
            "Consider increasing max_tokens if this happens frequently."
        )

    # Post-process: recompute skill_readiness_pct server-side
    for ai_role in parsed.ai_discovered_roles:
        t = len(ai_role.transferable_skills)
        d = len(ai_role.skills_to_develop)
        total = t + d
        ai_role.skill_readiness_pct = round(t / total * 100, 1) if total > 0 else 0.0

    return parsed, used_model
