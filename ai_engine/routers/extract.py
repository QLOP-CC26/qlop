"""Fase 1 — CV Extraction endpoint.

Receives a Cloudinary URL, downloads the PDF, runs NER extraction,
and returns a CVProfile for the user to review/edit.
"""

from __future__ import annotations

import asyncio
import logging
import time
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException

from schemas.envelope import success_envelope
from schemas.extract import ExtractRequest
from services.ner_service import download_pdf_from_cloudinary, extract_cv

logger = logging.getLogger("qlop.router.extract")
router = APIRouter(prefix="/api/v1/cv", tags=["extract"])


@router.post("/extract")
async def extract_endpoint(body: ExtractRequest):
    start = time.perf_counter()

    parsed = urlparse(body.cloudinary_url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not parsed.netloc or not (
        host == "res.cloudinary.com" or host.endswith(".cloudinary.com")
    ):
        raise HTTPException(status_code=400, detail="Invalid URL. Must be an HTTPS Cloudinary URL.")

    try:
        pdf_bytes = await download_pdf_from_cloudinary(body.cloudinary_url)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=400, detail=f"Failed to download file: HTTP {exc.response.status_code}") from exc
    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
        raise HTTPException(status_code=502, detail=f"Unable to reach Cloudinary: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to download file from URL: {exc}") from exc

    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Downloaded file is empty.")

    loop = asyncio.get_running_loop()
    try:
        profile, meta = await loop.run_in_executor(None, extract_cv, pdf_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("NER extraction failed")
        raise HTTPException(status_code=500, detail="Failed to process PDF.") from exc

    filename = parsed.path.rsplit("/", 1)[-1] if parsed.path else "uploaded.pdf"
    elapsed = int((time.perf_counter() - start) * 1000)

    return success_envelope(
        data=profile.model_dump(),
        metadata={
            "filename": filename,
            "page_count": meta.get("page_count", 0),
            "extraction_mode": meta.get("extraction_mode", "unknown"),
            "ner_model_version": meta.get("ner_model_version", ""),
            "processing_time_ms": elapsed,
        },
    )
