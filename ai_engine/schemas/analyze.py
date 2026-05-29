from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.cv_profile import CVProfile


class MissingSkill(BaseModel):
    skill: str
    priority_score: float


class SkillGap(BaseModel):
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[MissingSkill] = Field(default_factory=list)


class CourseRecommendation(BaseModel):
    name: str
    url: str
    match_score: float
    job_category: str = ""
    difficulty: str = ""
    duration: str = ""
    covered_skills: list[str] = Field(default_factory=list)


class ReadinessResult(BaseModel):
    score: float = 0.0
    matched_skills: list[str] = Field(default_factory=list)
    interpretation: str = ""


class AnalyzeRequest(BaseModel):
    profile: CVProfile
    target_role: str


class AnalyzeData(BaseModel):
    profile: CVProfile
    target_role: str
    skill_gap: SkillGap
    course_recommendations: list[CourseRecommendation] = Field(default_factory=list)
    readiness_score: ReadinessResult


class AnalyzeMetadata(BaseModel):
    target_role: str = ""
    cv_skills_count: int = 0
    processing_time_ms: int = 0
    concurrency_strategy: str = "asyncio.gather"
    timestamp: str = ""
