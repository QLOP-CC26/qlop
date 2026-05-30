from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PersonalInformation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    summary: str | None = None


class TextBlockGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_text_blocks: list[str] = Field(default_factory=list)


class CvProcessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    page_count: int
    personal_information: PersonalInformation
    work_experience: TextBlockGroup
    education: TextBlockGroup
    skills: list[str] = Field(default_factory=list)
    miscellaneous: TextBlockGroup
