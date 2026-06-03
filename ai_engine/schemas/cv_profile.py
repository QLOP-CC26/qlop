from __future__ import annotations

from typing import Annotated
from pydantic import BaseModel, Field


class WorkExperience(BaseModel):
    company: str = Field(default="", max_length=255)
    designation: str = Field(default="", max_length=255)
    duration: str = Field(default="", max_length=100)


class Education(BaseModel):
    degree: str = Field(default="", max_length=255)
    institution: str = Field(default="", max_length=255)
    year: str = Field(default="", max_length=50)


class CVProfile(BaseModel):
    name: str = Field(default="", max_length=255)
    email: str = Field(default="", max_length=255)
    phone: str = Field(default="", max_length=50)
    location: str = Field(default="", max_length=255)
    total_experience_years: float = Field(default=0.0, ge=0.0, le=60.0)
    skills: list[Annotated[str, Field(max_length=100)]] = Field(
        default_factory=list,
        max_length=200,
        description="Flat list of all skills (merged from all categories)"
    )
    work_experience: list[WorkExperience] = Field(default_factory=list, max_length=50)
    education: list[Education] = Field(default_factory=list, max_length=20)

