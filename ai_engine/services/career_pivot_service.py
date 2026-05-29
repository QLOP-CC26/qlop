"""Career Pivot Radar Service.

Stage A — Lightweight RAG: SBERT role centroid cosine similarity.
Stage B — Multi-turn Groq/Llama conversation (3 turns) with structured JSON output.

LLM Stack: openai SDK → Groq endpoint (llama-3.3-70b-versatile, free tier)
  Turn 1 : free-form profile analysis (temperature 0.4)
  Turn 2 : RAG context injection + role reasoning (temperature 0.3)
  Turn 3 : structured JSON output via json_object mode (temperature 0.1)

Multi-turn is simulated by accumulating the messages list manually,
since the openai SDK is stateless (unlike Gemini's chat sessions).
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
            best = fuzzy_match_skill(s_lower, vocab_keys, threshold=0.6)
            if best:
                normalised.append(best)

    if not normalised:
        return []

    user_text = " ".join(normalised)
    user_emb = r.sbert_model.encode([user_text], convert_to_tensor=False)[0].astype(np.float32)
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
    "Kamu adalah career coach IT Indonesia 2026. "
    "Analisis singkat, konkret, berbasis data. Jawab dalam bahasa Indonesia."
)


def _readiness_level(score: float) -> str:
    if score >= 0.75:
        return "excellent"
    if score >= 0.55:
        return "high"
    if score >= 0.35:
        return "moderate"
    return "low"


def _build_profile_prompt(profile: CVProfile, target_role: str, readiness: ReadinessResult) -> str:
    skills_flat = flatten_skills(profile.skills)
    work_entries = [w for w in profile.work_experience if w.company]
    work_str = "; ".join(
        f"{w.designation} @ {w.company} ({w.duration})" for w in work_entries
    ) or "tidak tersedia"
    edu_str = "; ".join(
        f"{e.degree} — {e.institution}" for e in profile.education if e.institution
    ) or "tidak tersedia"

    # Derive career trajectory hint for Gemini
    designations = [w.designation for w in work_entries if w.designation]
    traj_hint = " → ".join(designations[-3:]) if designations else "tidak diketahui"

    return (
        f"Kandidat: {profile.name} | Pengalaman: {profile.total_experience_years} tahun | Lokasi: {profile.location}\n"
        f"Skills ({len(skills_flat)}): {', '.join(skills_flat[:20])}\n"
        f"Riwayat karier: {traj_hint}\n"
        f"Detail kerja: {work_str}\n"
        f"Pendidikan: {edu_str}\n"
        f"Target saat ini: {target_role} | Readiness: {readiness.score:.2f} ({_readiness_level(readiness.score)})\n\n"
        "Lakukan analisis mendalam (bukan hanya daftar skills):\n"
        "1. Domain keahlian utama berdasarkan RIWAYAT KERJA (bukan hanya skills list)\n"
        "2. Pola karier: spesialisasi, leadership trajectory, atau pergeseran teknologi?\n"
        "3. Transferable domain: keahlian lintas industri/teknologi yang bisa diaplikasikan ke bidang lain\n"
        "4. Kekuatan unik yang tidak terlihat dari skills list (soft skills, domain knowledge, pola problem-solving)"
    )


def _build_rag_context_prompt(retrieved_roles: list[RetrievedRole], skill_gap: SkillGap) -> str:
    roles_compact = json.dumps(
        [r.to_dict() for r in retrieved_roles], ensure_ascii=False, separators=(",", ":")
    )
    missing_str = ", ".join(m.skill for m in skill_gap.missing_skills[:5])
    layer1_names = [r.role_name for r in retrieved_roles]

    return (
        f"=== LAYER 1: Role dari database IT (27 role) ===\n{roles_compact}\n"
        f"Skill gap saat ini: {missing_str or 'tidak ada'}\n"
        "Untuk setiap role Layer 1: alasan cocok, skill transferable, "
        "kesulitan transisi (easy/moderate/challenging), langkah pertama konkret.\n\n"
        "=== LAYER 2: Eksplorasi role DI LUAR database ===\n"
        "Berdasarkan analisis profil mendalam dari Turn 1 (riwayat kerja, pola karier, domain), "
        f"identifikasi 3-4 role potensial yang BERBEDA dari: {layer1_names}.\n"
        "Pertimbangkan:\n"
        "- Spesialisasi lebih dalam dari role saat ini (contoh: Fullstack → Frontend Architect)\n"
        "- Lateral move ke domain adjacent (contoh: Backend → DevOps/Platform Engineer)\n"
        "- Naik jabatan (contoh: Developer → Engineering Manager, Tech Lead)\n"
        "- Pivot ke domain baru yang sesuai background (contoh: Backend + FinTech exp → Fintech Engineer)\n"
        "Berikan reasoning kuat mengapa role ini cocok berdasarkan RIWAYAT KERJA, bukan hanya skills."
    )


def _build_structured_output_prompt(
    retrieved_roles: list[RetrievedRole],
    readiness: ReadinessResult,
    target_role: str,
) -> str:
    pre_filled = {
        "current_role_assessment": {
            "target_role": target_role,
            "readiness_score": readiness.score,
            "readiness_level": _readiness_level(readiness.score),
            "verdict": "__FILL__",
        },
        "alternative_roles": [
            {
                "role_name": r.role_name,
                "sbert_match_score": round(r.sbert_score, 4),
                "skill_overlap_pct": round(r.skill_overlap_pct, 2),
                "why_good_fit": "__FILL__",
                "transferable_skills": [],
                "gap_skills": r.gap_skills[:5],
                "transition_difficulty": "__FILL__",
                "estimated_transition_time": "__FILL__ (contoh: 3-6 bulan)",
                "first_step": "__FILL__",
            }
            for r in retrieved_roles
        ],
        "ai_discovered_roles": [
            {
                "role_name": "__FILL__ (role spesifik dari analisis Turn 1 & 2)",
                "category": "__FILL__ (specialization|adjacent|leadership|pivot)",
                "why_good_fit": "__FILL__ (berbasis riwayat kerja, bukan hanya skills)",
                "transferable_skills": ["__FILL__"],
                "skills_to_develop": ["__FILL__"],
                "transition_difficulty": "__FILL__",
                "estimated_transition_months": 0,
                "skill_readiness_pct": 0.0,
                "first_step": "__FILL__",
                "market_demand": "__FILL__ (high|medium|low)",
            }
        ],
        "strongest_transferable_skills": [],
        "suggested_certifications": [],
        "universal_advice": "__FILL__",
    }
    return (
        "Hasilkan JSON final sesuai schema. Ganti semua '__FILL__' dengan konten nyata.\n"
        "ATURAN:\n"
        "1. Jangan ubah nilai numerik (readiness_score, sbert_match_score, skill_overlap_pct).\n"
        "2. ai_discovered_roles: isi 3-4 role BERBEDA dari alternative_roles.\n"
        "   Pilih berdasarkan analisis riwayat kerja dari Turn 1 dan Turn 2, bukan hanya skills list.\n"
        "3. skill_readiness_pct di ai_discovered_roles: hitung sebagai "
        "   len(transferable_skills) / (len(transferable_skills) + len(skills_to_develop)) * 100.\n"
        "4. estimated_transition_months: angka integer (1-48).\n"
        "5. category: specialization|adjacent|leadership|pivot.\n"
        "6. market_demand: high|medium|low.\n"
        "7. transition_difficulty: easy|moderate|challenging.\n"
        f"Template: {json.dumps(pre_filled, ensure_ascii=False, separators=(',', ':'))}"
    )


# ──────────────────────────────────────────────────────────────────────
# Stage B — Multi-Turn Groq Conversation (openai-compatible SDK)
# ──────────────────────────────────────────────────────────────────────

def _groq_call(client: "openai.OpenAI", model: str, messages: list[dict], temperature: float, json_mode: bool = False) -> str:
    """Synchronous Groq call — to be run in executor."""
    kwargs: dict = dict(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=2000,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


async def generate_career_pivot(
    profile: CVProfile,
    target_role: str,
    skill_gap: SkillGap,
    readiness: ReadinessResult,
    retrieved_roles: list[RetrievedRole],
) -> CareerPivotOutput:
    """
    3-turn multi-turn conversation with Groq (Llama 3.3 70B).

    Multi-turn is simulated by manually accumulating the messages list
    (system + user/assistant pairs) — openai SDK is stateless.

    Turn 1 — free-form profile analysis (temperature 0.4)
    Turn 2 — RAG context injection + role exploration (temperature 0.3)
    Turn 3 — structured JSON output via json_object mode (temperature 0.1)
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

    # Accumulated messages list — grows across turns to preserve context
    messages: list[dict] = [{"role": "system", "content": _SYSTEM_INSTRUCTION}]

    # ── Turn 1: deep profile analysis ────────────────────────────────────
    turn1_prompt = _build_profile_prompt(profile, target_role, readiness)
    messages.append({"role": "user", "content": turn1_prompt})

    turn1_text = await loop.run_in_executor(
        None, lambda: _groq_call(client, model, messages, temperature=0.4)
    )
    messages.append({"role": "assistant", "content": turn1_text})
    logger.debug("Turn 1 profile analysis complete (%d chars)", len(turn1_text))

    # ── Turn 2: RAG context injection + beyond-dataset exploration ────────
    turn2_prompt = _build_rag_context_prompt(retrieved_roles, skill_gap)
    messages.append({"role": "user", "content": turn2_prompt})

    turn2_text = await loop.run_in_executor(
        None, lambda: _groq_call(client, model, messages, temperature=0.3)
    )
    messages.append({"role": "assistant", "content": turn2_text})
    logger.debug("Turn 2 RAG context analysis complete (%d chars)", len(turn2_text))

    # ── Turn 3: structured JSON output ───────────────────────────────────
    turn3_prompt = _build_structured_output_prompt(retrieved_roles, readiness, target_role)
    messages.append({"role": "user", "content": turn3_prompt})

    raw_json = await loop.run_in_executor(
        None, lambda: _groq_call(client, model, messages, temperature=0.1, json_mode=True)
    )
    logger.debug("Turn 3 structured output received (%d chars)", len(raw_json))

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
