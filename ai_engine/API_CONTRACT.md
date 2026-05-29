# QLOP AI Engine — API Contract v2.0

> **Base URL:** `http://<host>:8000`  
> **Interactive docs:** `http://<host>:8000/docs` (Swagger UI) · `http://<host>:8000/redoc`  
> **Content-Type:** `application/json` (all request & response bodies)  
> **Auth:** None (bearer token integration planned for v2.1)

---

## Architecture Overview

The API follows a **Human-in-the-Loop (HITL)** 3-phase pipeline:

```
PDF (Cloudinary URL)
      │
      ▼
┌─────────────────────┐
│  Phase 1 — Extract  │  POST /api/v1/cv/extract
│  NER CV Extraction  │
└──────────┬──────────┘
           │ CVProfile JSON
           ▼
    ╔══════════════╗
    ║  Human Review ║  ← User edits the CV profile in the frontend
    ╚══════════════╝
           │ (edited) CVProfile + target_role
           ▼
┌──────────────────────┐
│  Phase 2 — Analyze   │  POST /api/v1/cv/analyze
│  Skill Gap + Courses │  (3 sub-models run in parallel)
│  + Readiness Score   │
└──────────┬───────────┘
           │ Full analysis payload
           ▼
    ╔══════════════╗
    ║  Human Review ║  ← User sees full analysis
    ╚══════════════╝
           │ full analysis payload
           ▼
┌────────────────────────────┐
│  Phase 3 — Career Pivot    │  POST /api/v1/cv/career-pivot
│  RAG + Gemini 3-turn LLM   │
└────────────────────────────┘
```

---

## Standard Response Envelope

**All** endpoints return the same envelope structure.

### Success (2xx)

```json
{
  "status": "success",
  "code": 200,
  "data": { ... },
  "metadata": { ... }
}
```

| Field      | Type   | Description                              |
|------------|--------|------------------------------------------|
| `status`   | string | Always `"success"` on 2xx               |
| `code`     | int    | HTTP status code (e.g. 200)              |
| `data`     | object | The actual response payload              |
| `metadata` | object | Processing info (timing, model versions) |

### Error (4xx / 5xx)

```json
{
  "status": "error",
  "code": 422,
  "data": null,
  "detail": "Human-readable error message",
  "metadata": {
    "timestamp": "2026-05-29T08:00:00.000Z"
  }
}
```

| Field      | Type   | Description                        |
|------------|--------|------------------------------------|
| `status`   | string | Always `"error"`                   |
| `code`     | int    | HTTP status code                   |
| `data`     | null   | Always `null` on error             |
| `detail`   | string | Human-readable error message       |
| `metadata` | object | Includes `timestamp` + any extras  |

---

## Shared Data Models

### `CVProfile`

The core profile object exchanged between all phases.

```json
{
  "name": "Budi Santoso",
  "email": "budi@email.com",
  "phone": "+62 812 3456 7890",
  "location": "Jakarta, Indonesia",
  "total_experience_years": 4.5,
  "skills": {
    "programming_languages": ["Python", "JavaScript"],
    "frameworks":            ["FastAPI", "React"],
    "cloud_platforms":       ["AWS", "GCP"],
    "databases":             ["PostgreSQL", "Redis"],
    "devops_tools":          ["Docker", "Kubernetes"],
    "ml_ai_tools":           ["TensorFlow", "scikit-learn"],
    "other_tools":           ["Git", "Jira"]
  },
  "work_experience": [
    {
      "company":     "Tokopedia",
      "designation": "Data Engineer",
      "duration":    "2 years"
    }
  ],
  "education": [
    {
      "degree":      "S1 Teknik Informatika",
      "institution": "Universitas Indonesia",
      "year":        "2020"
    }
  ]
}
```

| Field                     | Type            | Required | Notes                                 |
|---------------------------|-----------------|----------|---------------------------------------|
| `name`                    | string          | no       | Full name extracted from CV           |
| `email`                   | string          | no       | Email address                         |
| `phone`                   | string          | no       | Phone number                          |
| `location`                | string          | no       | City / country                        |
| `total_experience_years`  | float           | no       | Sum of all work durations             |
| `skills`                  | `SkillsDict`    | no       | Nested skill categories (see below)   |
| `work_experience`         | `WorkExp[]`     | no       | List of job entries                   |
| `education`               | `Education[]`   | no       | List of education entries             |

#### `SkillsDict`

| Field                  | Type       | Description                      |
|------------------------|------------|----------------------------------|
| `programming_languages`| string[]   | e.g. `["Python", "Go"]`          |
| `frameworks`           | string[]   | e.g. `["Django", "FastAPI"]`     |
| `cloud_platforms`      | string[]   | e.g. `["AWS", "GCP"]`           |
| `databases`            | string[]   | e.g. `["MySQL", "MongoDB"]`      |
| `devops_tools`         | string[]   | e.g. `["Docker", "Jenkins"]`     |
| `ml_ai_tools`          | string[]   | e.g. `["TensorFlow", "PyTorch"]` |
| `other_tools`          | string[]   | e.g. `["Git", "Postman"]`        |

---

## Endpoint 1 — CV Extraction

### `POST /api/v1/cv/extract`

**Purpose:** Download a PDF CV from a Cloudinary URL, run DeBERTa-v3 NER, and return a structured `CVProfile`.

**Phase:** 1 of 3 (HITL checkpoint after this)

---

### Request

```http
POST /api/v1/cv/extract
Content-Type: application/json
```

```json
{
  "cloudinary_url": "https://res.cloudinary.com/demo/raw/upload/cv_budi.pdf"
}
```

| Field            | Type   | Required | Description                                 |
|------------------|--------|----------|---------------------------------------------|
| `cloudinary_url` | string | **yes**  | Full HTTPS URL to a PDF on Cloudinary. Must end with `.pdf` or return `application/pdf`. |

---

### Response `200 OK`

```json
{
  "status": "success",
  "code": 200,
  "data": {
    "name": "Budi Santoso",
    "email": "budi@email.com",
    "phone": "+62 812 3456 7890",
    "location": "Jakarta, Indonesia",
    "total_experience_years": 4.5,
    "skills": {
      "programming_languages": ["Python", "SQL"],
      "frameworks":            ["FastAPI", "TensorFlow"],
      "cloud_platforms":       ["GCP"],
      "databases":             ["PostgreSQL"],
      "devops_tools":          ["Docker"],
      "ml_ai_tools":           ["scikit-learn"],
      "other_tools":           ["Git"]
    },
    "work_experience": [
      { "company": "Tokopedia", "designation": "Data Engineer", "duration": "2 years" }
    ],
    "education": [
      { "degree": "S1 Teknik Informatika", "institution": "Universitas Indonesia", "year": "2020" }
    ]
  },
  "metadata": {
    "filename": "cv_budi.pdf",
    "page_count": 2,
    "extraction_mode": "ner_deberta",
    "ner_model_version": "qlop_ner_v2",
    "processing_time_ms": 1842,
    "timestamp": "2026-05-29T08:00:00.123456+00:00"
  }
}
```

#### `data` fields (`CVProfile`)

See [Shared Data Models → CVProfile](#cvprofile).

#### `metadata` fields

| Field                 | Type   | Description                                              |
|-----------------------|--------|----------------------------------------------------------|
| `filename`            | string | Filename extracted from the URL                          |
| `page_count`          | int    | Number of pages in the PDF                               |
| `extraction_mode`     | string | `"ner_deberta"` (model active) or `"heuristic"` (fallback) |
| `ner_model_version`   | string | Always `"qlop_ner_v2"` when model is active              |
| `processing_time_ms`  | int    | Total wall-clock time including PDF download             |
| `timestamp`           | string | ISO-8601 UTC timestamp                                   |

---

### Error Responses

| HTTP | `code` | Scenario                                          |
|------|--------|---------------------------------------------------|
| 400  | 400    | `cloudinary_url` is empty / not a valid URL       |
| 400  | 400    | Downloaded file is not a PDF (wrong content-type) |
| 400  | 400    | PDF is corrupt or has no extractable text         |
| 422  | 422    | Request body does not match schema                |
| 502  | 502    | Cannot reach Cloudinary (network error)           |
| 500  | 500    | Unhandled internal server error                   |

---

### Frontend UX Hint

While this endpoint processes, show sequential loading messages to manage user expectations:

```
1s  → "Mengunduh dokumen dari Cloudinary…"
3s  → "Membaca teks dari PDF…"
5s  → "Model AI sedang mengekstrak informasi CV Anda…"
8s  → "Hampir selesai, memvalidasi hasil ekstraksi…"
```

After response: open an **editable form** pre-filled with `data`. User can correct any field before proceeding to Phase 2.

---

## Endpoint 2 — Skill Gap Analysis

### `POST /api/v1/cv/analyze`

**Purpose:** Given a (possibly user-edited) `CVProfile` and a `target_role`, run Skill Gap Analysis, Course Recommendation, and Readiness Scoring **in parallel** and return comprehensive results.

**Phase:** 2 of 3 (HITL checkpoint after this)

---

### Request

```http
POST /api/v1/cv/analyze
Content-Type: application/json
```

```json
{
  "profile": { ... },
  "target_role": "Data Scientist"
}
```

| Field         | Type        | Required | Description                                                             |
|---------------|-------------|----------|-------------------------------------------------------------------------|
| `profile`     | `CVProfile` | **yes**  | The (possibly edited) CVProfile from Phase 1                           |
| `target_role` | string      | **yes**  | The job role the user is targeting. Must match a known role in the system (see supported roles below). |

#### Supported `target_role` values

> The list below is defined by the training data. Unknown roles receive zero scores.

```
Backend Engineer, Data Analyst, Data Engineer, Data Scientist, DevOps Engineer,
Embedded/IoT Engineer, Frontend Engineer, Full Stack Engineer, Machine Learning Engineer,
Mobile Developer, QA Engineer, Security Engineer, UI/UX Designer, Cloud Architect,
Database Administrator
```

---

### Response `200 OK`

```json
{
  "status": "success",
  "code": 200,
  "data": {
    "profile": { "name": "Budi Santoso", "..." : "..." },
    "target_role": "Data Scientist",
    "skill_gap": {
      "matched_skills": ["Python", "SQL", "scikit-learn"],
      "missing_skills": [
        { "skill": "PyTorch",        "priority_score": 0.92 },
        { "skill": "Statistics",     "priority_score": 0.87 },
        { "skill": "Deep Learning",  "priority_score": 0.81 }
      ]
    },
    "course_recommendations": [
      {
        "name":             "Deep Learning Specialization",
        "url":              "https://www.coursera.org/specializations/deep-learning",
        "match_score":      0.94,
        "job_category":     "Data Scientist",
        "difficulty":       "Intermediate",
        "duration":         "3 months",
        "covered_skills":   ["Deep Learning", "Neural Networks", "PyTorch"]
      }
    ],
    "readiness_score": {
      "score":           0.71,
      "matched_skills":  ["Python", "SQL", "scikit-learn", "GCP"],
      "interpretation":  "Good fit — you have the core skills but need to deepen ML knowledge."
    }
  },
  "metadata": {
    "target_role":          "Data Scientist",
    "cv_skills_count":      12,
    "processing_time_ms":   780,
    "concurrency_strategy": "asyncio.gather",
    "timestamp":            "2026-05-29T08:00:01.456789+00:00"
  }
}
```

#### `data.skill_gap`

| Field            | Type             | Description                                   |
|------------------|------------------|-----------------------------------------------|
| `matched_skills` | string[]         | Skills the candidate already has for the role |
| `missing_skills` | `MissingSkill[]` | Skills needed, ranked by `priority_score`     |

#### `MissingSkill`

| Field            | Type  | Range  | Description                                        |
|------------------|-------|--------|----------------------------------------------------|
| `skill`          | string| —      | Skill name                                         |
| `priority_score` | float | 0–1    | How critical this skill is (1.0 = most critical)   |

#### `data.course_recommendations`

Array of up to 5 courses. Each item:

| Field             | Type     | Description                                    |
|-------------------|----------|------------------------------------------------|
| `name`            | string   | Course title                                   |
| `url`             | string   | Direct Coursera link                           |
| `match_score`     | float    | Relevance score (0–1)                          |
| `job_category`    | string   | Role this course targets                       |
| `difficulty`      | string   | `Beginner` / `Intermediate` / `Advanced`       |
| `duration`        | string   | Estimated completion time                      |
| `covered_skills`  | string[] | Skills this course teaches                     |

#### `data.readiness_score`

| Field             | Type     | Description                                              |
|-------------------|----------|----------------------------------------------------------|
| `score`           | float    | 0.0–1.0 semantic similarity score (SBERT-based)          |
| `matched_skills`  | string[] | Skills that contributed to the score                     |
| `interpretation`  | string   | Plain-language verdict generated from the score range    |

#### Interpretation scale

| Score range | Label       | Interpretation example                          |
|-------------|-------------|-------------------------------------------------|
| 0.0 – 0.40  | Low         | Significant skill gaps — major reskilling needed |
| 0.40 – 0.60 | Moderate    | Some foundation but missing core skills          |
| 0.60 – 0.80 | Good        | Strong match, narrow gaps to fill               |
| 0.80 – 1.00 | Excellent   | Ready to apply — minimal to no gaps             |

#### `metadata` fields

| Field                  | Type   | Description                                |
|------------------------|--------|--------------------------------------------|
| `target_role`          | string | Echo of requested role                     |
| `cv_skills_count`      | int    | Total flattened skills in the CV           |
| `processing_time_ms`   | int    | Wall-clock time (3 models ran in parallel) |
| `concurrency_strategy` | string | Always `"asyncio.gather"`                  |
| `timestamp`            | string | ISO-8601 UTC                               |

---

### Error Responses

| HTTP | `code` | Scenario                                       |
|------|--------|------------------------------------------------|
| 400  | 400    | `target_role` is an empty string               |
| 422  | 422    | Request body does not match schema             |
| 500  | 500    | Internal model inference error                 |

---

### Frontend UX Hint

```
1s  → "Memproses profil CV Anda…"
2s  → "Model AI menganalisis skill gap untuk peran ini…"
4s  → "Mencari rekomendasi kursus yang relevan…"
6s  → "Menghitung skor kesiapan Anda…"
```

After response: display a **dashboard** with the skill gap, a course list, and the readiness score. User may then click "Generate Career Pivot" to proceed to Phase 3.

---

## Endpoint 3 — Career Pivot Radar

### `POST /api/v1/cv/career-pivot`

**Purpose:** Given the full Phase 2 analysis, use RAG (SBERT role centroid similarity) + Google Gemini 1.5 Flash (3-turn chain-of-thought) to recommend the best alternative career paths.

**Phase:** 3 of 3 (final output)

---

### Request

```http
POST /api/v1/cv/career-pivot
Content-Type: application/json
```

```json
{
  "profile": { ... },
  "target_role": "Data Scientist",
  "skill_gap": {
    "matched_skills": ["Python", "SQL"],
    "missing_skills": [
      { "skill": "PyTorch", "priority_score": 0.92 }
    ]
  },
  "course_recommendations": [ ... ],
  "readiness_score": {
    "score": 0.71,
    "matched_skills": ["Python", "SQL"],
    "interpretation": "Good fit."
  }
}
```

> **Tip:** The `data` field returned by `POST /api/v1/cv/analyze` can be sent **as-is** as the body of this endpoint.

| Field                   | Type                       | Required | Description                                 |
|-------------------------|----------------------------|----------|---------------------------------------------|
| `profile`               | `CVProfile`                | **yes**  | The candidate's profile                     |
| `target_role`           | string                     | **yes**  | The originally targeted role                |
| `skill_gap`             | `SkillGap`                 | **yes**  | Output from Phase 2                         |
| `course_recommendations`| `CourseRecommendation[]`   | no       | Output from Phase 2 (enriches LLM context)  |
| `readiness_score`       | `ReadinessResult`          | **yes**  | Output from Phase 2                         |

---

### Response `200 OK`

```json
{
  "status": "success",
  "code": 200,
  "data": {
    "current_role_assessment": {
      "target_role":      "Data Scientist",
      "readiness_score":  0.71,
      "readiness_level":  "high",
      "verdict":          "You're a strong candidate for Data Scientist. A few gaps in deep learning can be closed with targeted courses."
    },
    "alternative_roles": [
      {
        "role_name":                  "Machine Learning Engineer",
        "sbert_match_score":          0.89,
        "skill_overlap_pct":          72.0,
        "why_good_fit":               "Your Python and data pipeline experience maps directly to MLOps workflows.",
        "transferable_skills": [
          { "skill": "Python",    "relevance": "Core language for ML pipelines" },
          { "skill": "Docker",    "relevance": "Essential for model containerization" }
        ],
        "gap_skills":                 ["MLflow", "Kubernetes", "CI/CD for ML"],
        "transition_difficulty":      "moderate",
        "estimated_transition_time":  "3-6 months",
        "first_step":                 "Complete the MLOps Specialization on Coursera to bridge the deployment gap."
      },
      {
        "role_name":                  "Data Engineer",
        "sbert_match_score":          0.85,
        "skill_overlap_pct":          65.0,
        "why_good_fit":               "Strong SQL and cloud skills are exactly what data engineering demands.",
        "transferable_skills": [
          { "skill": "SQL",        "relevance": "Core for ETL query building" },
          { "skill": "GCP",        "relevance": "BigQuery and Dataflow are widely used" }
        ],
        "gap_skills":                 ["Apache Spark", "Airflow", "dbt"],
        "transition_difficulty":      "easy",
        "estimated_transition_time":  "1-2 months",
        "first_step":                 "Build a portfolio project using Airflow + BigQuery on GCP Free Tier."
      }
    ],
    "strongest_transferable_skills": ["Python", "SQL", "GCP", "scikit-learn"],
    "suggested_certifications": [
      {
        "name":      "Google Professional Data Engineer",
        "relevance": "Validates your GCP skills and opens data engineering doors."
      },
      {
        "name":      "TensorFlow Developer Certificate",
        "relevance": "Fills your deep learning gap for Data Scientist / MLE roles."
      }
    ],
    "universal_advice": "Your cross-domain Python + cloud foundation is your biggest asset. Double down on it by adding one orchestration tool (Airflow) and one experiment tracking tool (MLflow) — these two alone will make you a competitive candidate for both Data Engineer and ML Engineer roles within 3 months."
  },
  "metadata": {
    "retrieval_method":    "sbert_role_centroid_cosine",
    "roles_evaluated":     15,
    "roles_returned":      3,
    "llm_model":           "gemini-1.5-flash",
    "llm_turns":           3,
    "processing_time_ms":  4230,
    "timestamp":           "2026-05-29T08:00:05.789000+00:00"
  }
}
```

#### `data.current_role_assessment`

| Field             | Type                                         | Description                             |
|-------------------|----------------------------------------------|-----------------------------------------|
| `target_role`     | string                                       | Echoes the requested role               |
| `readiness_score` | float (0.0–1.0)                              | From Phase 2                            |
| `readiness_level` | `"low"` \| `"moderate"` \| `"high"` \| `"excellent"` | Semantic label              |
| `verdict`         | string                                       | LLM-generated plain-language verdict    |

#### `data.alternative_roles` (array)

| Field                        | Type                                          | Description                                     |
|------------------------------|-----------------------------------------------|-------------------------------------------------|
| `role_name`                  | string                                        | Suggested alternative role                      |
| `sbert_match_score`          | float (0.0–1.0)                               | SBERT cosine similarity — how close skills are  |
| `skill_overlap_pct`          | float (0.0–100.0)                             | % of candidate skills matching role requirements|
| `why_good_fit`               | string                                        | LLM explanation                                 |
| `transferable_skills`        | `TransferableSkill[]`                         | Skills that transfer with explanation            |
| `gap_skills`                 | string[]                                      | Skills still needed for this alternative role    |
| `transition_difficulty`      | `"easy"` \| `"moderate"` \| `"challenging"`   | LLM assessment                                  |
| `estimated_transition_time`  | string                                        | e.g. `"3-6 months"`                             |
| `first_step`                 | string                                        | Actionable first recommendation                  |

#### `TransferableSkill`

| Field       | Type   | Description                     |
|-------------|--------|---------------------------------|
| `skill`     | string | Skill name                      |
| `relevance` | string | Why this skill matters for role |

#### `data.suggested_certifications` (array)

| Field       | Type   | Description                          |
|-------------|--------|--------------------------------------|
| `name`      | string | Certification / course name          |
| `relevance` | string | Why this cert helps the candidate    |

#### `metadata` fields

| Field                 | Type   | Description                                          |
|-----------------------|--------|------------------------------------------------------|
| `retrieval_method`    | string | Always `"sbert_role_centroid_cosine"`                |
| `roles_evaluated`     | int    | Total roles compared using SBERT similarity          |
| `roles_returned`      | int    | Number of alternative roles in `alternative_roles`   |
| `llm_model`           | string | Active Gemini model (from `GEMINI_MODEL` env var)    |
| `llm_turns`           | int    | Number of LLM conversation turns used (always 3)     |
| `processing_time_ms`  | int    | Total wall-clock time including LLM latency          |
| `timestamp`           | string | ISO-8601 UTC                                         |

---

### Error Responses

| HTTP | `code` | Scenario                                              |
|------|--------|-------------------------------------------------------|
| 400  | 400    | `target_role` is empty                                |
| 503  | 503    | `GOOGLE_API_KEY` not configured on server             |
| 422  | 422    | Request body does not match schema                    |
| 500  | 500    | Gemini API error or malformed structured output       |

---

### Frontend UX Hint

```
2s  → "Model AI sedang mengambil peran alternatif yang sesuai…"
4s  → "Menganalisis kesesuaian dan transferable skills Anda…"
8s  → "AI sedang merangkum rekomendasi karier terbaik untuk Anda…"
12s → "Hampir selesai — memformat hasil rekomendasi…"
```

After response: display a **Career Pivot Radar** visualization — a radar/spider chart plotting skill overlap for each alternative role, with collapsible detail cards for each role.

---

## Health Check

### `GET /health`

**Purpose:** Readiness probe — confirms all models are loaded and the server is ready to accept requests.

```http
GET /health
```

### Response `200 OK`

```json
{
  "status": "ok",
  "ner_available": true,
  "roles_loaded": 15,
  "sbert_loaded": true,
  "role_centroids": 15
}
```

| Field             | Type    | Description                                             |
|-------------------|---------|---------------------------------------------------------|
| `status`          | string  | `"ok"` when healthy                                     |
| `ner_available`   | boolean | `true` if DeBERTa NER model loaded successfully         |
| `roles_loaded`    | int     | Number of role indexes loaded (expected: 15)            |
| `sbert_loaded`    | boolean | `true` if Sentence-BERT model is in memory              |
| `role_centroids`  | int     | Number of precomputed role centroids for Career Pivot   |

> **Frontend guidance:** Poll this endpoint once on app startup. If `sbert_loaded` is `false` or `roles_loaded` is 0, show a "AI service is warming up…" banner and retry after 5 seconds.

---

## Starting the Server

```bash
# From d:\DBSCodingCamp\qlop\ai_engine\ (with .venv activated)

# Development (auto-reload)
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# Production
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
```

> Use `--workers 1` in production because TensorFlow and PyTorch models are held in process memory. Multi-worker spawning would multiply RAM usage and may cause CUDA conflicts.

### Required Environment Variables (`.env`)

```ini
# --- NER Model ---
NER_MODEL_DIR=assets/ner/qlop_ner_v2
NER_VOCAB_FILE=assets/ner/qlop_ner_v2/vocab.txt
NER_LABELS_FILE=assets/ner/qlop_ner_v2/label_list.txt

# --- Recommendation Models ---
REC_MODEL3_DIR=assets/recommendation/model3_skillgap
REC_MODEL4_DIR=assets/recommendation/model4_courses
REC_SKILL_VOCAB_LI=assets/recommendation/skill_vocab_linkedin.json
REC_SKILL_VOCAB_CO=assets/recommendation/skill_vocab_coursera.json
REC_COURSERA_CSV=assets/recommendation/coursera_courses.csv
REC_JOB_EMBEDDINGS_DIR=assets/recommendation/job_embeddings

# --- Gemini (Google AI Studio) ---
GOOGLE_API_KEY=your_google_ai_studio_api_key_here
GEMINI_MODEL=gemini-1.5-flash
```

---

## Error Code Reference

| HTTP | Meaning                         | Common Causes                                    |
|------|---------------------------------|--------------------------------------------------|
| 400  | Bad Request                     | Invalid URL, empty field, non-PDF file           |
| 422  | Unprocessable Entity            | JSON schema mismatch (wrong types, missing keys) |
| 500  | Internal Server Error           | ML model crash, unexpected exception             |
| 502  | Bad Gateway                     | Cannot reach Cloudinary (Phase 1 only)           |
| 503  | Service Unavailable             | API key missing (Phase 3 only)                   |

---

## Integration Sequence (Frontend → Backend)

```
Frontend                         QLOP AI Engine
    │                                  │
    │──── POST /api/v1/cv/extract ─────►│  (Phase 1)
    │◄─── 200 CVProfile JSON ───────────│
    │                                  │
    │  [User edits profile in UI]       │
    │                                  │
    │──── POST /api/v1/cv/analyze ─────►│  (Phase 2)
    │◄─── 200 AnalyzeData JSON ─────────│
    │                                  │
    │  [User reviews analysis]          │
    │  [Clicks "Career Pivot"]          │
    │                                  │
    │──── POST /api/v1/cv/career-pivot ►│  (Phase 3)
    │◄─── 200 CareerPivotOutput JSON ───│
    │                                  │
    │  [Display radar + detail cards]   │
```

> **Important for frontend:** The body of `POST /api/v1/cv/career-pivot` is exactly the `data` field from the `POST /api/v1/cv/analyze` response — no transformation needed.

---

*Document version: 2.0 · Last updated: 2026-05-29 · Maintained by QLOP AI Team*
