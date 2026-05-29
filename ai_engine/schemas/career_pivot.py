from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from schemas.analyze import CourseRecommendation, ReadinessResult, SkillGap
from schemas.cv_profile import CVProfile


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
# Structured Output — Pydantic-locked for OpenAI response_format
# ---------------------------------------------------------------------------

class TransferableSkill(BaseModel):
    skill: str
    relevance: str


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


class AIDiscoveredRole(BaseModel):
    """Layer 2 — Roles discovered by Gemini from the full CV context (not limited to dataset).

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


class SuggestedCertification(BaseModel):
    name: str
    relevance: str


class CurrentRoleAssessment(BaseModel):
    target_role: str
    readiness_score: float
    readiness_level: Literal["low", "moderate", "high", "excellent"]
    verdict: str


class CareerPivotOutput(BaseModel):
    current_role_assessment: CurrentRoleAssessment
    alternative_roles: list[AlternativeRole]
    """Layer 1: data-backed roles from the 27-role dataset with SBERT + skill overlap metrics."""
    ai_discovered_roles: list[AIDiscoveredRole]
    """Layer 2: AI-generated roles beyond the dataset, based on full CV analysis."""
    strongest_transferable_skills: list[str]
    suggested_certifications: list[SuggestedCertification]
    universal_advice: str


class CareerPivotMetadata(BaseModel):
    retrieval_method: str = "sbert_role_centroid_cosine"
    roles_evaluated: int = 0
    roles_returned: int = 0
    llm_model: str = ""
    llm_turns: int = 3
    processing_time_ms: int = 0
    timestamp: str = ""
