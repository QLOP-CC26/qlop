# AI Engine

FastAPI service for processing uploaded PDF CVs/resumes, extracting text in memory with PyMuPDF, classifying the content into structured groups, and returning a strictly validated JSON response.

## Features

- `POST /api/v1/cv/process` accepts a PDF file using `multipart/form-data`
- In-memory PDF extraction with PyMuPDF, no local disk write
- Structured output with Pydantic v2 models
- `GET /` serves a simple HTML mockup for manual testing

## Requirements

- Python 3.10+
- Dependencies listed in [requirements.txt](requirements.txt)

## Install

From the repository root or from inside `ai_engine`:

```powershell
cd D:\DBSCodingCamp\qlop\ai_engine
pip install -r requirements.txt
```

If you use the repository virtual environment:

```powershell
cd D:\DBSCodingCamp\qlop
& .\.venv\Scripts\Activate.ps1
cd D:\DBSCodingCamp\qlop\ai_engine
pip install -r requirements.txt
```

## Run

Start the API server from the `ai_engine` folder:

```powershell
cd D:\DBSCodingCamp\qlop\ai_engine
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Open in Browser

- Upload mockup: http://127.0.0.1:8000/
- OpenAPI docs: http://127.0.0.1:8000/docs

## API Endpoint

### `POST /api/v1/cv/process`

Form field:

- `file`: PDF resume/CV file

Example response groups:

- Personal information: name, email, phone, summary
- Work experience: raw text blocks
- Education: raw text blocks
- Skills: extracted keyword array
- Miscellaneous: remaining uncategorized blocks

## Files

- [main.py](main.py)
- [schemas/cv_schema.py](schemas/cv_schema.py)
- [services/pdf_extractor.py](services/pdf_extractor.py)
- [templates/index.html](templates/index.html)
- [requirements.txt](requirements.txt)
