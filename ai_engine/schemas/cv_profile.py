from __future__ import annotations

from pydantic import BaseModel, Field


class WorkExperience(BaseModel):
    company: str = ""
    designation: str = ""
    duration: str = ""


class Education(BaseModel):
    degree: str = ""
    institution: str = ""
    year: str = ""


class CVProfile(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    total_experience_years: float = 0.0
    skills: list[str] = Field(default_factory=list, description="Flat list of all skills (merged from all categories)")
    work_experience: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
