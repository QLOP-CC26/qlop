from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

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


def _clean_literal(v: Any, allowed: list[str], default: str) -> str:
    if not isinstance(v, str):
        return default
    v_clean = _lower(v)
    # Check if exact match is in the clean string
    for val in allowed:
        if val in v_clean:
            return val
    # Check for synonyms or partials
    if "difficult" in v_clean or "hard" in v_clean:
        if "challenging" in allowed:
            return "challenging"
    if "moderate" in v_clean or "average" in v_clean:
        if "medium" in allowed:
            return "medium"
        if "moderate" in allowed:
            return "moderate"
    if "weak" in v_clean or "slow" in v_clean or "less" in v_clean:
        if "low" in allowed:
            return "low"
    # Fallback to default
    return default


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
    skill: str = ""
    relevance: str = ""


class AlternativeRole(BaseModel):
    """Layer 1 — Data-backed roles from the 27-role dataset (SBERT + skill overlap metrics)."""
    role_name: str = ""
    sbert_match_score: float = Field(default=0.0, ge=0.0, le=1.0)
    skill_overlap_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    why_good_fit: str = ""
    transferable_skills: list[TransferableSkill] = Field(default_factory=list)
    gap_skills: list[str] = Field(default_factory=list)
    transition_difficulty: Literal["easy", "moderate", "challenging"] = "moderate"
    estimated_transition_time: str = ""
    first_step: str = ""

    @field_validator("sbert_match_score", mode="before")
    @classmethod
    def coerce_sbert_score(cls, v: Any) -> float:
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        if isinstance(v, str):
            try:
                return max(0.0, min(1.0, float(v)))
            except ValueError:
                return 0.0
        return 0.0

    @field_validator("skill_overlap_pct", mode="before")
    @classmethod
    def coerce_skill_overlap(cls, v: Any) -> float:
        if isinstance(v, (int, float)):
            return max(0.0, min(100.0, float(v)))
        if isinstance(v, str):
            try:
                return max(0.0, min(100.0, float(v.replace("%", "").strip())))
            except ValueError:
                return 0.0
        return 0.0

    @field_validator("transition_difficulty", mode="before")
    @classmethod
    def normalize_difficulty(cls, v: Any) -> Any:
        return _clean_literal(v, ["easy", "moderate", "challenging"], "moderate")

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
        if v is None:
            return []
        return v


class AIDiscoveredRole(BaseModel):
    """Layer 2 — Roles discovered by Groq LLM from the full CV context (not limited to dataset).

    Metrics:
    - skill_readiness_pct: computed server-side as transferable / (transferable + to_develop) * 100
    - estimated_transition_months: AI estimate (numeric, sortable)
    - market_demand: AI knowledge of current job market
    - category: type of career move
    """
    role_name: str = ""
    category: Literal["specialization", "adjacent", "leadership", "pivot"] = "adjacent"
    why_good_fit: str = ""
    transferable_skills: list[str] = Field(default_factory=list)
    skills_to_develop: list[str] = Field(default_factory=list)
    transition_difficulty: Literal["easy", "moderate", "challenging"] = "moderate"
    estimated_transition_months: int = Field(default=6, ge=1, le=48)
    skill_readiness_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    first_step: str = ""
    market_demand: Literal["high", "medium", "low"] = "medium"

    @model_validator(mode="before")
    @classmethod
    def clean_role_dict(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Map estimated_transition_time -> estimated_transition_months if missing
            if "estimated_transition_months" not in data or data["estimated_transition_months"] is None:
                val = data.get("estimated_transition_time")
                if val:
                    # extract digits
                    match = re.search(r"\d+", str(val))
                    if match:
                        data["estimated_transition_months"] = int(match.group())
                    else:
                        data["estimated_transition_months"] = 6
                else:
                    data["estimated_transition_months"] = 6

            # Ensure estimated_transition_months is within bounds
            months = data.get("estimated_transition_months")
            if months is not None:
                try:
                    data["estimated_transition_months"] = max(1, min(48, int(months)))
                except (ValueError, TypeError):
                    data["estimated_transition_months"] = 6
            else:
                data["estimated_transition_months"] = 6

            # Ensure skill_readiness_pct is within bounds
            pct = data.get("skill_readiness_pct")
            if pct is not None:
                try:
                    data["skill_readiness_pct"] = max(0.0, min(100.0, float(pct)))
                except (ValueError, TypeError):
                    data["skill_readiness_pct"] = 0.0
            else:
                data["skill_readiness_pct"] = 0.0

            # Ensure skills_to_develop is present
            if "skills_to_develop" not in data or not data["skills_to_develop"]:
                # Fallback to skills / missing_skills if returned
                data["skills_to_develop"] = data.get("skills", data.get("missing_skills", []))

            # Ensure transition_difficulty is present
            if "transition_difficulty" not in data:
                data["transition_difficulty"] = "moderate"

            # Ensure first_step is present
            if "first_step" not in data:
                data["first_step"] = "Learn the essential skills for this role."

            # Ensure market_demand is present
            if "market_demand" not in data:
                data["market_demand"] = "medium"

        return data

    @field_validator("transition_difficulty", mode="before")
    @classmethod
    def normalize_difficulty(cls, v: Any) -> Any:
        return _clean_literal(v, ["easy", "moderate", "challenging"], "moderate")

    @field_validator("market_demand", mode="before")
    @classmethod
    def normalize_market_demand(cls, v: Any) -> Any:
        return _clean_literal(v, ["high", "medium", "low"], "medium")

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: Any) -> Any:
        return _clean_literal(v, ["specialization", "adjacent", "leadership", "pivot"], "adjacent")

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
        if v is None:
            return []
        return v


class SuggestedCertification(BaseModel):
    name: str = ""
    relevance: str = ""


class CurrentRoleAssessment(BaseModel):
    target_role: str = ""
    readiness_score: float = 0.0
    readiness_level: Literal["low", "moderate", "high", "excellent"] = "moderate"
    verdict: str = ""

    @field_validator("readiness_score", mode="before")
    @classmethod
    def coerce_readiness_score(cls, v: Any) -> float:
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        if isinstance(v, str):
            v_clean = v.replace("%", "").strip()
            try:
                val = float(v_clean)
                if val > 1.0:
                    val = val / 100.0
                return max(0.0, min(1.0, val))
            except ValueError:
                return 0.0
        return 0.0

    @field_validator("readiness_level", mode="before")
    @classmethod
    def normalize_readiness_level(cls, v: Any) -> Any:
        return _clean_literal(v, ["low", "moderate", "high", "excellent"], "moderate")


class CareerPivotOutput(BaseModel):
    """
    Structured career pivot analysis output.

    alternative_roles  — Layer 1: data-backed roles from the 27-role dataset with SBERT + skill overlap metrics.
    ai_discovered_roles — Layer 2: AI-generated roles beyond the dataset, based on full CV analysis.
    """

    thinking_process: str = ""
    current_role_assessment: CurrentRoleAssessment = Field(default_factory=lambda: CurrentRoleAssessment())
    alternative_roles: list[AlternativeRole] = Field(default_factory=list)
    ai_discovered_roles: list[AIDiscoveredRole] = Field(default_factory=list)

    @field_validator("thinking_process", mode="before")
    @classmethod
    def coerce_thinking_process(cls, v: Any) -> Any:
        if isinstance(v, list):
            return " | ".join(str(item) for item in v)
        if v is None:
            return ""
        return str(v)

    @field_validator("current_role_assessment", mode="before")
    @classmethod
    def coerce_current_role_assessment(cls, v: Any) -> Any:
        if not isinstance(v, dict):
            return {}
        return v

    @field_validator("alternative_roles", mode="before")
    @classmethod
    def coerce_alternative_roles(cls, v: Any) -> Any:
        if not isinstance(v, list):
            return []
        return v

    @field_validator("ai_discovered_roles", mode="before")
    @classmethod
    def coerce_ai_discovered_roles(cls, v: Any) -> Any:
        if not isinstance(v, list):
            return []
        return v

    # These three fields appear at the END of the JSON template; when max_tokens is
    # exhausted mid-response the LLM omits them. Defaults let the response succeed
    # gracefully instead of returning a 503 to the user.
    strongest_transferable_skills: list[str] = Field(default_factory=list)
    suggested_certifications: list[SuggestedCertification] = Field(default_factory=list)
    universal_advice: str = ""

    @field_validator("strongest_transferable_skills", mode="before")
    @classmethod
    def clean_strongest_skills(cls, v: Any) -> Any:
        """Accept list[str] or list[dict] — extract skill name from dicts."""
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, str):
                    val = _strip_hint(item)
                    if val and val.lower() not in _SENTINELS:
                        result.append(val)
                elif isinstance(item, dict):
                    val = _strip_hint(item.get("skill", item.get("name", "")))
                    if val and val.lower() not in _SENTINELS:
                        result.append(val)
            return result
        return []

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
        return []

    @field_validator("universal_advice", mode="before")
    @classmethod
    def coerce_universal_advice(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)


class CareerPivotMetadata(BaseModel):
    retrieval_method: str = "sbert_role_centroid_cosine"
    roles_evaluated: int = 0
    roles_returned: int = 0
    llm_model: str = ""
    llm_turns: int = 3
    processing_time_ms: int = 0
    timestamp: str = ""
