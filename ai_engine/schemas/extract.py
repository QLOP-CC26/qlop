from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractRequest(BaseModel):
    cloudinary_url: str = Field(..., description="Cloudinary URL pointing to a PDF file")


class ExtractMetadata(BaseModel):
    filename: str = ""
    page_count: int = 0
    extraction_mode: str = "ner_deberta"
    ner_model_version: str = "qlop_ner_v2"
    processing_time_ms: int = 0
    timestamp: str = ""
