from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from schemas.analyze import CourseRecommendation, ReadinessResult, SkillGap
from schemas.cv_profile import CVProfile


# ---------------------------------------------------------------------------
# LLM output normalisation helpers
# ---------------------------------------------------------------------------

# Template hints embedded in prompt placeholders, e.g. "(high|medium|low)",
# "(specific role from Turn 1 & 2 analysis)", "(e.g. 3-6 months)".
_HINT_RE = re.compile(r"\s*\([^)]*\)\s*$")

# Sentinel strings the LLM might leave verbatim from the JSON template.
_SENTINELS: frozenset[str] = frozenset({"__fill__", "...", "....", "placeholder"})


def _lower(v: Any) -> Any:
    """Normalise a Literal field: strip trailing hint text, then lowercase.

    Handles two LLM failure modes in one pass:
    - Title Case:  "Moderate"                        → "moderate"
    - Hint suffix: "adjacent (specialization|...)"   → "adjacent"
    - Both:        "High (high|medium|low)"           → "high"
    """
    if isinstance(v, str):
        return _HINT_RE.sub("", v).strip().lower()
    return v


def _strip_hint(v: Any) -> Any:
    """Strip trailing parenthetical hints from free-text string fields.

    Example: "3-6 months (e.g. 3-6 months)"  →  "3-6 months"
    Also removes a bare "__FILL__" sentinel, returning "" instead.
    """
    if isinstance(v, str):
        v = _HINT_RE.sub("", v).strip()
        if v.startswith("__FILL__"):
            return ""
    return v


def _clean_list(v: Any) -> Any:
    """Remove sentinel placeholder strings from LLM-generated list fields.

    The prompt template uses ["__FILL__", "..."] as placeholders. If the LLM
    partially fills a list it may leave those tokens in the output.
    """
    if isinstance(v, list):
        return [
            item for item in v
            if not (isinstance(item, str) and item.strip().lower() in _SENTINELS)
        ]
    return v


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class CareerPivotRequest(BaseModel):
    profile: CVProfile
    target_role: str
    skill_gap: SkillGap
    course_recommendations: list[CourseRecommendation] = Field(default_factory=list)
    readiness_score: ReadinessResult


# ---------------------------------------------------------------------------
# Structured Output — Pydantic-locked JSON from Groq json_object mode
# ---------------------------------------------------------------------------

class TransferableSkill(BaseModel):
    skill: str
    relevance: str = ""


class AlternativeRole(BaseModel):
    """Layer 1 — Data-backed roles from the 27-role dataset (SBERT + skill overlap metrics)."""
    role_name: str
    sbert_match_score: float = Field(ge=0.0, le=1.0)
    skill_overlap_pct: float = Field(ge=0.0, le=100.0)
    why_good_fit: str
    transferable_skills: list[TransferableSkill]
    gap_skills: list[str]
    transition_difficulty: Literal["easy", "moderate", "challenging"]
    estimated_transition_time: str
    first_step: str

    @field_validator("transition_difficulty", mode="before")
    @classmethod
    def normalize_difficulty(cls, v: Any) -> Any:
        return _lower(v)

    @field_validator("estimated_transition_time", mode="before")
    @classmethod
    def coerce_transition_time(cls, v: Any) -> Any:
        """Accept int/float from LLM (e.g. 6 → "6 months") and strip hint text."""
        if isinstance(v, (int, float)):
            return f"{int(v)} months"
        return _strip_hint(v)

    @field_validator("transferable_skills", mode="before")
    @classmethod
    def coerce_transferable_skills(cls, v: Any) -> Any:
        """Coerce plain strings → TransferableSkill; drop sentinel placeholders.

        When the LLM returns an object {"skill": "...", "relevance": "..."} it is
        passed through unchanged so the filled relevance is preserved.
        When it returns a plain string the relevance defaults to "".
        """
        if isinstance(v, list):
            cleaned = _clean_list(v)
            result = []
            for item in cleaned:
                if isinstance(item, str):
                    # Strip any sentinel from skill name too
                    skill_val = _strip_hint(item)
                    if skill_val and skill_val.lower() not in _SENTINELS:
                        result.append({"skill": skill_val, "relevance": ""})
                elif isinstance(item, dict):
                    # Preserve relevance if LLM filled it; strip sentinels
                    rel = _strip_hint(item.get("relevance", ""))
                    if rel and rel.lower() in _SENTINELS:
                        rel = ""
                    skill_val = _strip_hint(item.get("skill", ""))
                    if skill_val and skill_val.lower() not in _SENTINELS:
                        result.append({"skill": skill_val, "relevance": rel})
            return result
        return v


class AIDiscoveredRole(BaseModel):
    """Layer 2 — Roles discovered by Groq LLM from the full CV context (not limited to dataset).

    Metrics:
    - skill_readiness_pct: computed server-side as transferable / (transferable + to_develop) * 100
    - estimated_transition_months: AI estimate (numeric, sortable)
    - market_demand: AI knowledge of current job market
    - category: type of career move
    """
    role_name: str
    category: Literal["specialization", "adjacent", "leadership", "pivot"]
    why_good_fit: str
    transferable_skills: list[str]
    skills_to_develop: list[str]
    transition_difficulty: Literal["easy", "moderate", "challenging"]
    estimated_transition_months: int = Field(ge=1, le=48)
    skill_readiness_pct: float = Field(ge=0.0, le=100.0, default=0.0)
    first_step: str
    market_demand: Literal["high", "medium", "low"]

    @field_validator("transition_difficulty", "category", "market_demand", mode="before")
    @classmethod
    def normalize_literals(cls, v: Any) -> Any:
        return _lower(v)

    @field_validator("role_name", "why_good_fit", mode="before")
    @classmethod
    def strip_ai_role_hints(cls, v: Any) -> Any:
        return _strip_hint(v)

    @field_validator("transferable_skills", "skills_to_develop", mode="before")
    @classmethod
    def clean_skill_lists(cls, v: Any) -> Any:
        """Accept list[str] or list[dict] — extract skill name from dicts."""
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, str):
                    val = _strip_hint(item)
                    if val and val.lower() not in _SENTINELS:
                        result.append(val)
                elif isinstance(item, dict):
                    # LLM returned {"skill": "...", "relevance": "..."} — keep name only
                    val = _strip_hint(item.get("skill", item.get("name", "")))
                    if val and val.lower() not in _SENTINELS:
                        result.append(val)
            return result
        return v


class SuggestedCertification(BaseModel):
    name: str
    relevance: str = ""


class CurrentRoleAssessment(BaseModel):
    target_role: str
    readiness_score: float
    readiness_level: Literal["low", "moderate", "high", "excellent"]
    verdict: str

    @field_validator("readiness_level", mode="before")
    @classmethod
    def normalize_readiness_level(cls, v: Any) -> Any:
        return _lower(v)


class CareerPivotOutput(BaseModel):
    """
    Structured career pivot analysis output.

    alternative_roles  — Layer 1: data-backed roles from the 27-role dataset with SBERT + skill overlap metrics.
    ai_discovered_roles — Layer 2: AI-generated roles beyond the dataset, based on full CV analysis.
    """

    current_role_assessment: CurrentRoleAssessment
    alternative_roles: list[AlternativeRole]
    ai_discovered_roles: list[AIDiscoveredRole]
    strongest_transferable_skills: list[str]
    suggested_certifications: list[SuggestedCertification]
    universal_advice: str

    @field_validator("strongest_transferable_skills", mode="before")
    @classmethod
    def clean_strongest_skills(cls, v: Any) -> Any:
        return _clean_list(v)

    @field_validator("suggested_certifications", mode="before")
    @classmethod
    def coerce_certifications(cls, v: Any) -> Any:
        """Coerce plain strings → SuggestedCertification; preserve relevance when LLM fills it."""
        if isinstance(v, list):
            cleaned = _clean_list(v)
            result = []
            for item in cleaned:
                if isinstance(item, str):
                    name_val = _strip_hint(item)
                    if name_val and name_val.lower() not in _SENTINELS:
                        result.append({"name": name_val, "relevance": ""})
                elif isinstance(item, dict):
                    rel = _strip_hint(item.get("relevance", ""))
                    if rel and rel.lower() in _SENTINELS:
                        rel = ""
                    name_val = _strip_hint(item.get("name", ""))
                    if name_val and name_val.lower() not in _SENTINELS:
                        result.append({"name": name_val, "relevance": rel})
            return result
        return v


class CareerPivotMetadata(BaseModel):
    retrieval_method: str = "sbert_role_centroid_cosine"
    roles_evaluated: int = 0
    roles_returned: int = 0
    llm_model: str = ""
    llm_turns: int = 3
    processing_time_ms: int = 0
    timestamp: str = ""
