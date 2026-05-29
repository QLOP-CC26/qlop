# QLOP AI Engine

FastAPI REST API for **QLOP** — a skill-gap analysis platform.  
Called by the main Express.js backend; implements a **Human-in-the-Loop (HITL)** flow in three phases.

---

## Architecture Overview

```
Express.js (main backend)
       │
       ├─ Phase 1 ──► POST /api/v1/cv/extract
       │               NER extraction from Cloudinary PDF URL
       │               ← Returns structured CVProfile
       │
       │    [User reviews & edits the profile in the frontend]
       │
       ├─ Phase 2 ──► POST /api/v1/cv/analyze
       │               Parallel: Skill Gap (Model3) + Courses (Model4) + Readiness Score (SBERT)
       │               ← Returns one combined JSON payload
       │
       │    [User optionally clicks "Explore Career Pivot"]
       │
       └─ Phase 3 ──► POST /api/v1/cv/career-pivot
                       SBERT RAG retrieval + 3-turn Gemini conversation
                       ← Returns structured CareerPivotOutput (Pydantic-locked JSON)
```

---

## Components

| # | Component | Technology |
|---|-----------|-----------|
| 1 | NER CV Extraction | DeBERTa-v3-base + custom `QLOPNERModelV2` (TF/Keras 2) |
| 2 | Readiness Scoring | SBERT cosine similarity (`all-MiniLM-L6-v2`) |
| 3 | Skill Gap Analysis | TensorFlow SavedModel (`model3_savedmodel`) |
| 4 | Course Recommendation | TensorFlow SavedModel (`model4_savedmodel`) + `coursera_cleaned.csv` |
| 5 | Career Pivot Radar | SBERT RAG + Gemini 2.0 Flash (3-turn multi-turn, structured output) |

---

## Project Structure

```
ai_engine/
├── app.py                    # FastAPI entry point, lifespan, CORS, exception handlers
├── requirements.txt
├── .env                      # GOOGLE_API_KEY, GEMINI_MODEL (not committed)
├── .env.example
├── API_CONTRACT.md           # Complete API contract for the Express.js team
│
├── core/
│   ├── config.py             # pydantic-settings configuration
│   └── model_loader.py       # ModelRegistry — loads all models at startup
│
├── routers/
│   ├── extract.py            # POST /api/v1/cv/extract
│   ├── analyze.py            # POST /api/v1/cv/analyze
│   └── career_pivot.py       # POST /api/v1/cv/career-pivot
│
├── services/
│   ├── ner_service.py        # PDF download, text extraction, NER inference
│   ├── recommendation_service.py  # Skill gap + course recommendation (Model3/4)
│   ├── readiness_service.py  # SBERT readiness scoring
│   └── career_pivot_service.py    # RAG retrieval + Gemini conversation
│
├── schemas/
│   ├── cv_profile.py         # CVProfile (skills = flat list[str])
│   ├── extract.py            # Phase 1 request/response
│   ├── analyze.py            # Phase 2 request/response
│   ├── career_pivot.py       # Phase 3 request/response + CareerPivotOutput
│   └── envelope.py           # Standard success/error envelope
│
├── utils/
│   └── skill_normalizer.py   # flatten_skills(), fuzzy_match_skill()
│
├── model_assets/             # Semua file model yang dipakai server saat runtime
│   ├── ner/                  # NER weights, tokenizer, config, taxonomy
│   └── recommendation/       # TF SavedModels + data (JSON, CSV, NPZ, embeddings/)
│       ├── model3_savedmodel/
│       ├── model4_savedmodel/
│       ├── coursera_cleaned.csv
│       └── embeddings/       # 27 role SBERT embeddings
│
├── research/                 # Training artifacts & notebooks (untuk penilaian)
│   ├── notebooks/
│   ├── data_pipeline/
│   └── ner_training/
│
└── _legacy/                  # Kode lama (sudah digantikan app.py)
```

---

## Requirements

- Python 3.10 or 3.11
- Dependencies in `requirements.txt`

Key packages and version constraints:

| Package | Constraint | Reason |
|---------|-----------|--------|
| `transformers` | `>=4.40.0,<5.0.0` | TF/Keras support dropped in v5 |
| `tf-keras` | `>=2.16.0` | Keras 2 backward-compat for TF 2.16+ |
| `tensorflow` | `>=2.16.0` | Model3/4 SavedModel loading |
| `sentence-transformers` | `>=3.0.0` | SBERT readiness scoring |
| `google-genai` | latest | Gemini 2.5 Flash Lite SDK |

---

## Setup

```powershell
# From repo root
cd D:\DBSCodingCamp\qlop
python -m venv .venv
.\.venv\Scripts\Activate.ps1

cd ai_engine
pip install -r requirements.txt
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
# Google AI Studio API key — required for Career Pivot Radar (Phase 3)
# Get yours free at: https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=AIzaSy...

# Gemini model (default: gemini-2.0-flash)
GEMINI_MODEL=gemini-2.5-flash-lite

# NER confidence threshold (default: 0.5)
NER_CONFIDENCE_THRESHOLD=0.5
```

---

## Running the Server

```powershell
# Activate venv first
cd D:\DBSCodingCamp\qlop
.\.venv\Scripts\Activate.ps1
cd ai_engine

# Development (auto-reload)
uvicorn app:app --host 127.0.0.1 --port 8000 --reload

# Production (no reload)
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
```

> **Note:** Use `--workers 1` because TensorFlow models are not fork-safe.

Open in browser:
- **Interactive docs (Swagger UI):** http://127.0.0.1:8000/docs
- **OpenAPI schema:** http://127.0.0.1:8000/openapi.json
- **Health check:** http://127.0.0.1:8000/health

---

## API Endpoints

All responses follow a consistent envelope:

```json
{
  "status": "success" | "error",
  "code": 200,
  "data": { ... },
  "metadata": { "timestamp": "...", "processing_time_ms": 1234 },
  "detail": null
}
```

### `GET /health`

Returns model loading status.

```json
{
  "status": "ok",
  "ner_available": true,
  "roles_loaded": 27,
  "sbert_loaded": true,
  "role_centroids": 27,
  "model3_available": true,
  "model4_available": true
}
```

---

### `POST /api/v1/cv/extract` — Phase 1

**Request:**
```json
{ "cloudinary_url": "https://res.cloudinary.com/.../cv.pdf" }
```

**Response `data`:**
```json
{
  "profile": {
    "name": "Budi Santoso",
    "email": "budi@example.com",
    "phone": "08123456789",
    "location": "Jakarta",
    "total_experience_years": 3.0,
    "skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
    "work_experience": [
      { "company": "Tokopedia", "designation": "Backend Engineer", "duration": "2 years" }
    ],
    "education": [
      { "degree": "S1 Informatika", "institution": "UI", "year": "2021" }
    ]
  }
}
```

> `skills` is always a **flat list of strings** (all categories merged).

---

### `POST /api/v1/cv/analyze` — Phase 2

**Request:**
```json
{
  "profile": { ... CVProfile ... },
  "target_role": "Backend Developer"
}
```

**Response `data`:**
```json
{
  "profile": { ... CVProfile ... },
  "target_role": "Backend Developer",
  "skill_gap": {
    "matched_skills": ["python", "docker"],
    "missing_skills": [
      { "skill": "go", "priority_score": 0.6152 },
      { "skill": "kubernetes", "priority_score": 0.4801 }
    ],
    "match_score": 0.45
  },
  "course_recommendations": [
    {
      "name": "Go Programming Language",
      "url": "https://www.coursera.org/...",
      "match_score": 0.87,
      "reason": "Covers Go — a critical gap skill",
      "job_category": "Backend Development",
      "difficulty": "Beginner",
      "duration": "17 hours"
    }
  ],
  "readiness_score": {
    "score": 0.3155,
    "matched_skills": ["python", "docker"],
    "interpretation": "moderate fit",
    "experience_bonus": 0.05,
    "breadth_bonus": 0.02
  }
}
```

Valid `target_role` values (27 total):
`AI Engineer`, `Backend Developer`, `Business Analyst`, `Business Intelligence Analyst`,
`Cloud Engineer`, `Cyber Security Analyst`, `Data Analyst`, `Data Engineer`,
`Data Scientist`, `Database Administrator`, `DevOps Engineer`, `ERP Consultant`,
`Embedded/IoT Engineer`, `Frontend Developer`, `Full Stack Developer`,
`General IT Specialist`, `IT Consultant`, `Machine Learning Engineer`,
`Mobile Developer`, `Network Engineer`, `Product Manager`, `QA Engineer`,
`Robotics Engineer`, `Security Engineer`, `Site Reliability Engineer`,
`Software Engineer`, `Solutions Architect`

---

### `POST /api/v1/cv/career-pivot` — Phase 3

Accepts the full payload from Phase 2 plus the profile.

**Request:**
```json
{
  "profile": { ... CVProfile ... },
  "target_role": "Backend Developer",
  "skill_gap": { ... from Phase 2 ... },
  "course_recommendations": [ ... ],
  "readiness_score": { ... }
}
```

**Response `data`:**
```json
{
  "current_role_assessment": {
    "target_role": "Backend Developer",
    "readiness_score": 0.3155,
    "readiness_level": "moderate",
    "verdict": "Profil Anda cocok untuk Backend Developer..."
  },
  "alternative_roles": [
    {
      "role_name": "Full Stack Developer",
      "sbert_match_score": 0.82,
      "skill_overlap_pct": 60.0,
      "why_good_fit": "Keahlian React dan JavaScript sangat relevan...",
      "transferable_skills": ["JavaScript", "React", "Git"],
      "gap_skills": ["Vue.js", "Node.js"],
      "transition_difficulty": "easy",
      "estimated_transition_time": "3-6 bulan",
      "first_step": "Ikuti kursus Node.js dan bangun proyek full-stack portfolio"
    }
  ],
  "strongest_transferable_skills": ["Python", "Docker", "React"],
  "suggested_certifications": ["AWS Certified Developer", "Google Professional Cloud Developer"],
  "universal_advice": "Fokus pada..."
}
```

> Returns **503** if `GOOGLE_API_KEY` is not set, or if Gemini quota/model is unavailable.

---

## Error Responses

All errors use the same envelope:

```json
{
  "status": "error",
  "code": 400,
  "data": null,
  "metadata": { "timestamp": "..." },
  "detail": "Role 'Astronaut' tidak dikenali. Role yang valid: ..."
}
```

| HTTP Code | Meaning |
|-----------|---------|
| 400 | Invalid request (unknown role, empty skills, bad URL) |
| 422 | Pydantic validation error (missing required fields) |
| 503 | Service unavailable (missing/invalid API key, Gemini quota exceeded) |
| 500 | Internal server error (unexpected failure) |

---

## Model Files Required

| File | Description |
|------|-------------|
| `model_assets/ner/best_weights.weights.h5` | Custom NER head weights (ITSkillMultiHeadProjection) |
| `model_assets/ner/tokenizer/` | DeBERTa-v3-base tokenizer files |
| `model_assets/ner/model_config.json` | NER label schema + config |
| `model_assets/recommendation/model3_savedmodel/` | Skill gap TF SavedModel |
| `model_assets/recommendation/model4_savedmodel/` | Course recommendation TF SavedModel |
| `model_assets/recommendation/*.npz` | Role skill embeddings and frequency data |
| `model_assets/recommendation/coursera_cleaned.csv` | Coursera course metadata |

The NER DeBERTa base weights are downloaded automatically from HuggingFace (`microsoft/deberta-v3-base`) on first startup.  
If NER weights are missing, the server starts in **heuristic fallback mode** (regex-based extraction).

---

## Frontend UX — Loading State

While waiting for Phase 2 (typically 1–5 seconds), rotate these messages every 2 seconds:

```javascript
const loadingMessages = [
  "Menganalisis matriks skill kamu...",
  "Mencocokkan dengan 27 role di database...",
  "Menghitung readiness score...",
  "Mencari kursus Coursera yang relevan...",
  "Menyusun laporan skill gap...",
];
```

Phase 3 (Career Pivot, 10–30 seconds) rotation:

```javascript
const pivotMessages = [
  "Memuat sistem Career Pivot Radar...",
  "Menganalisis vektor keahlian kamu...",
  "Menemukan jalur karier alternatif...",
  "Berkonsultasi dengan AI career coach...",
  "Menyusun rekomendasi personal...",
];
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Attribute 'app' not found` | Make sure you run `uvicorn app:app` from inside `ai_engine/`, not the repo root |
| `No module named 'tf_keras'` | `pip install tf-keras>=2.16.0` |
| `ImportError: cannot import TFAutoModel...` | `pip install 'transformers>=4.40.0,<5.0.0'` |
| Port 8000 already in use | `Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force` |
| Gemini returns 503 | Check `GOOGLE_API_KEY` in `.env`; upgrade plan if quota is 0 |
| Model3/4 not found | Verify `model_assets/recommendation/model3_savedmodel/saved_model.pb` exists |
| NER loads but accuracy is low | Confirm `model_assets/ner/best_weights.weights.h5` is the fine-tuned weights file |
