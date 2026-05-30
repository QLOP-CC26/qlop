from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse

from schemas.cv_schema import CvProcessResponse
from services.pdf_extractor import process_pdf_cv

app = FastAPI(title="CV Processing Service", version="2.0.0")
router = APIRouter(prefix="/api/v1/cv", tags=["cv"])

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "index.html"
ALLOWED_PDF_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/octet-stream",
}


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(ValueError)
async def value_error_exception_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    if not TEMPLATE_PATH.exists():
        raise HTTPException(status_code=500, detail="Template file is missing.")
    return HTMLResponse(TEMPLATE_PATH.read_text(encoding="utf-8"))


@router.post("/process", response_model=CvProcessResponse)
async def process_cv(file: UploadFile = File(...)) -> CvProcessResponse:
    filename = file.filename or "uploaded.pdf"
    content_type = (file.content_type or "").lower()
    if not filename.lower().endswith(".pdf") and content_type not in ALLOWED_PDF_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        return process_pdf_cv(file_bytes=file_bytes, filename=filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - safety net for parser failures
        raise HTTPException(status_code=500, detail="Failed to process the uploaded PDF.") from exc


app.include_router(router)
