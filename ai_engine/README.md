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
            SBERT RAG retrieval + single-shot Groq/Llama JSON generation
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
| 5 | Career Pivot Radar | SBERT RAG + Groq Llama via OpenAI-compatible SDK (single-shot structured JSON) |

---

## Project Structure

```
ai_engine/
├── app.py                    # FastAPI entry point, lifespan, CORS, exception handlers
├── requirements.txt
├── .env                      # GROQ_API_KEY, GROQ_MODEL (not committed)
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
│   └── career_pivot_service.py    # RAG retrieval + Groq/Llama single-shot generation
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
| `openai` | `>=1.30.0` | Groq API (OpenAI-compatible SDK) |

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
# Groq API key — required for Career Pivot Radar (Phase 3)
# Get yours FREE (no credit card) at: https://console.groq.com/keys
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Groq model (default: llama-3.3-70b-versatile)
# Other options: llama-3.1-8b-instant (faster), llama-4-scout-17b-16e-instruct (newer)
GROQ_MODEL=llama-3.3-70b-versatile

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

---

## Production Deployment

### Option A — Docker locally

Build the image from the `ai_engine/` directory:

```bash
cd ai_engine
docker build -t qlop-ai-engine .
```

Run it with your production env file:

```bash
docker run --rm -p 8000:8000 --env-file .env qlop-ai-engine
```

### Option B — Railway

Railway should deploy this service from `ai_engine/` as a Docker app.

1. Create a new Railway service from this repository.
2. Set the root directory to `ai_engine` so Railway picks up the Dockerfile.
3. Add the following environment variables in Railway Variables:
  - `GROQ_API_KEY`
  - `GROQ_MODEL` (optional; default is `llama-3.1-8b-instant`)
  - `GROQ_MAX_TOKENS` (optional; keep `2048` for the default model)
  - `CAREER_PIVOT_TOP_K` (optional; default `4`)
4. Do not set `PORT` manually unless Railway requires it. The Dockerfile already uses `PORT` when present.
5. After deploy, verify `GET /health` and `GET /docs` on the Railway public URL.

Recommended sizing: 2 GB RAM is borderline for this AI Engine because TensorFlow, SBERT, and the NER model are loaded at startup. If Railway lets you choose a larger instance, prefer 4 GB or higher.

### Runtime Notes

- The AI Engine is exposed publicly so the backend can reach it via `AI_API_URL`.
- Keep `AI_API_URL` in the backend pointed at the Railway public URL, for example `https://your-ai-engine.up.railway.app`.
- Use a single worker. Multiple workers can duplicate TensorFlow memory and cause crashes.
- The image preloads Hugging Face models during build, so first boot is faster and does not depend on a writable cache volume.

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

### `GET /api/v1/roles`

Returns the 27 valid `target_role` values. Frontend should use this to populate the role dropdown.

```json
{
  "data": {
    "roles": ["AI Engineer", "Backend Developer", "..."],
    "count": 27
  }
}
```

> Do not allow free-text role input — ML models are trained on these 27 roles only. Both `/analyze` and `/career-pivot` normalize case server-side.

---

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

**Response `data`:** *(CVProfile object directly — no wrapper)*
```json
{
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
    { "degree": "B.Sc. Computer Science", "institution": "University of Indonesia", "year": "2021" }
  ]
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
    ]
  },
  "course_recommendations": [
    {
      "name": "Go Programming Language",
      "url": "https://www.coursera.org/...",
      "match_score": 0.87,
      "job_category": "Backend Development",
      "difficulty": "Beginner",
      "duration": "17 hours",
      "covered_skills": ["go"]
    }
  ],
  "readiness_score": {
    "score": 0.3155,
    "matched_skills": ["python", "docker"],
    "interpretation": "moderate fit"
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
    "verdict": "Your profile fits Backend Developer with a few gaps to address."
  },
  "alternative_roles": [
    {
      "role_name": "Full Stack Developer",
      "sbert_match_score": 0.8234,
      "skill_overlap_pct": 60.0,
      "why_good_fit": "Your React and JavaScript skills are highly relevant for a full-stack role.",
      "transferable_skills": [
        { "skill": "JavaScript", "relevance": "Primary language for full-stack development" },
        { "skill": "React",      "relevance": "Directly applicable on the frontend side" }
      ],
      "gap_skills": ["vue.js", "node.js"],
      "transition_difficulty": "easy",
      "estimated_transition_time": "3-6 months",
      "first_step": "Take a Node.js course and build a full-stack portfolio project."
    }
  ],
  "ai_discovered_roles": [
    {
      "role_name": "API Platform Engineer",
      "category": "specialization",
      "why_good_fit": "Your backend experience in API design is directly relevant for building internal API platforms.",
      "transferable_skills": ["python", "fastapi", "docker", "postgresql"],
      "skills_to_develop": ["kong", "api gateway", "openapi spec"],
      "transition_difficulty": "moderate",
      "estimated_transition_months": 4,
      "skill_readiness_pct": 57.1,
      "first_step": "Build an API gateway project using Kong or AWS API Gateway for your portfolio.",
      "market_demand": "high"
    }
  ],
  "strongest_transferable_skills": ["python", "docker", "react"],
  "suggested_certifications": [
    { "name": "AWS Certified Developer", "relevance": "Validates your cloud skills and opens doors at tech startups." },
    { "name": "Google Professional Cloud Developer", "relevance": "Relevant for backend roles in the GCP ecosystem." }
  ],
  "universal_advice": "Focus on deepening one cloud platform (AWS or GCP) to differentiate yourself from other developers."
}
```

> Returns **503** if `GROQ_API_KEY` is not set, or if Groq quota/model is unavailable.  
> `alternative_roles` = Layer 1 dari dataset (metric data-backed). `ai_discovered_roles` = Layer 2 dari Groq LLM (tidak terbatas 27 role).

---

## Error Responses

All errors use the same envelope:

```json
{
  "status": "error",
  "code": 400,
  "data": null,
  "metadata": { "timestamp": "..." },
  "detail": "Role 'Astronaut' not recognized. Valid roles: ..."
}
```

| HTTP Code | Meaning |
|-----------|---------|
| 400 | Invalid request (unknown role, empty skills, bad URL) |
| 422 | Pydantic validation error (missing required fields) |
| 503 | Service unavailable (missing/invalid API key, Groq quota exceeded)   |
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
  "Analyzing your skill matrix...",
  "Matching against 27 roles in the database...",
  "Calculating readiness score...",
  "Searching for relevant Coursera courses...",
  "Compiling your skill gap report...",
];
```

Phase 3 (Career Pivot, 10–30 seconds) rotation:

```javascript
const pivotMessages = [
  "Loading Career Pivot Radar system...",
  "Analyzing your skill vectors...",
  "Discovering alternative career paths...",
  "Consulting AI career coach...",
  "Composing personalized recommendations...",
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
| Groq returns 503 | Check `GROQ_API_KEY` in `.env`; verify quota at console.groq.com |
| Model3/4 not found | Verify `model_assets/recommendation/model3_savedmodel/saved_model.pb` exists |
| NER loads but accuracy is low | Confirm `model_assets/ner/best_weights.weights.h5` is the fine-tuned weights file |

---

## Kaggle Research & Datasets

The machine learning core is built on the following Kaggle resources:

### Kaggle Notebooks
* **AI 1 (NER Skill Extractor)**: [qlop-ner-v2-it-skill-extraction-from-cvs](https://www.kaggle.com/code/husniabdillah/qlop-ner-v2-it-skill-extraction-from-cvs) — Fine-tuning code for DeBERTa-v3 on Indonesian IT resume entities.
* **AI 2 (Two-Tower Matcher & Gap Analysis)**: [qlop-two-tower-course-matcher-and-gap-analysis](https://www.kaggle.com/code/gilangagung/qlop-two-tower-course-matcher-and-gap-analysis) — TensorFlow implementation of the skill gap scoring model (Model 3) and Two-Tower Coursera recommender (Model 4).
* **Synthetic Profile Generator**: [qlop-synthethic-data-for-ai-training](https://www.kaggle.com/code/husniabdillah/qlop-synthethic-data-for-ai-training) — Creates virtual candidates to pre-train Model 3 and Model 4.

### Kaggle Datasets
* **QLOP NER Dataset**: [husniabdillah/qlop-ner-dataset](https://www.kaggle.com/datasets/husniabdillah/qlop-ner-dataset) — Annotated resume corpus for fine-tuning the DeBERTa extractor.
* **Intelligent Learning Recommendation Dataset**: [gilangagung/qlop-intelligent-learning-recommendation-dataset](https://www.kaggle.com/datasets/gilangagung/qlop-intelligent-learning-recommendation-dataset) — Coursera catalogs, skill vocabs, mapping JSONs, and pre-computed synthetic matrices.
* **Dataset QLOP (Mastered Jobs)**: [husniabdillah/dataset-qlop](https://www.kaggle.com/datasets/husniabdillah/dataset-qlop) — Baseline IT job vacancies crawled and mapped across Indonesian platforms.

