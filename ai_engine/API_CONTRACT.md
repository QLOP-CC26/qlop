# QLOP AI Engine — API Contract v2.1

> **Base URL:** `http://<host>:8000`  
> **Interactive docs:** `http://<host>:8000/docs` (Swagger UI) · `http://<host>:8000/redoc`  
> **Content-Type:** `application/json` (all request & response bodies)  
> **Auth:** None (bearer token integration planned for v2.2)

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
│  SBERT RAG + Groq single-shot │
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
  "skills": ["Python", "JavaScript", "FastAPI", "React", "AWS", "PostgreSQL", "Docker", "Git"],
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

> **`skills` is always a flat `string[]`** — all skill categories are merged into one list. The frontend may display them grouped if needed, but the API always sends and receives a flat list.

| Field                     | Type        | Required | Notes                                 |
|---------------------------|-------------|----------|---------------------------------------|
| `name`                    | string      | no       | Full name extracted from CV           |
| `email`                   | string      | no       | Email address                         |
| `phone`                   | string      | no       | Phone number                          |
| `location`                | string      | no       | City / country                        |
| `total_experience_years`  | float       | no       | Sum of all work durations             |
| `skills`                  | `string[]`  | no       | Flat list of all skills (merged)      |
| `work_experience`         | `WorkExp[]` | no       | List of job entries                   |
| `education`               | `Education[]` | no     | List of education entries             |

#### `WorkExperience`

| Field         | Type   | Description                  |
|---------------|--------|------------------------------|
| `company`     | string | Employer name                |
| `designation` | string | Job title / role             |
| `duration`    | string | Free-text duration (e.g. `"2 years"`) |

#### `Education`

| Field         | Type   | Description                   |
|---------------|--------|-------------------------------|
| `degree`      | string | Degree name                   |
| `institution` | string | University / institution name |
| `year`        | string | Graduation year               |

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
    "skills": ["python", "sql", "fastapi", "tensorflow", "gcp", "postgresql", "docker", "git"],
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

While this endpoint processes, show sequential loading messages:

```
1s  → "Downloading document from Cloudinary…"
3s  → "Reading text from PDF…"
5s  → "AI model is extracting your CV information…"
8s  → "Almost done, validating extraction results…"
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
  "profile": { "...": "CVProfile object" },
  "target_role": "Data Scientist"
}
```

| Field         | Type        | Required | Description                                                             |
|---------------|-------------|----------|-------------------------------------------------------------------------|
| `profile`     | `CVProfile` | **yes**  | The (possibly edited) CVProfile from Phase 1                           |
| `target_role` | string      | **yes**  | The job role the user is targeting. Must be one of the 27 supported roles below. |

#### Supported `target_role` values (27 roles)

```
AI Engineer               Backend Developer         Business Analyst
Business Intelligence Analyst  Cloud Engineer        Cyber Security Analyst
Data Analyst              Data Engineer             Data Scientist
Database Administrator    DevOps Engineer           ERP Consultant
Embedded/IoT Engineer     Frontend Developer        Full Stack Developer
General IT Specialist     IT Consultant             Machine Learning Engineer
Mobile Developer          Network Engineer          Product Manager
QA Engineer               Robotics Engineer         Security Engineer
Site Reliability Engineer Software Engineer         Solutions Architect
```

> Sending an unknown role returns `HTTP 400` with the full list of valid roles in the error detail.

---

### Response `200 OK`

```json
{
  "status": "success",
  "code": 200,
  "data": {
    "profile": { "name": "Budi Santoso", "skills": ["python", "sql", "..."], "...": "..." },
    "target_role": "Data Scientist",
    "skill_gap": {
      "matched_skills": ["python", "sql", "scikit-learn"],
      "missing_skills": [
        { "skill": "pytorch",        "priority_score": 0.92 },
        { "skill": "statistics",     "priority_score": 0.87 },
        { "skill": "deep learning",  "priority_score": 0.81 }
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
        "covered_skills":   ["deep learning", "neural networks", "pytorch"]
      }
    ],
    "readiness_score": {
      "score":           0.71,
      "matched_skills":  ["python", "sql", "scikit-learn", "gcp"],
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
| `matched_skills` | `string[]`       | Skills the candidate already has for the role |
| `missing_skills` | `MissingSkill[]` | Skills needed, ranked by `priority_score`     |

#### `MissingSkill`

| Field            | Type  | Range  | Description                                        |
|------------------|-------|--------|----------------------------------------------------|
| `skill`          | string| —      | Skill name (lowercase)                             |
| `priority_score` | float | 0–1    | How critical this skill is (1.0 = most critical)   |

#### `data.course_recommendations`

Array of up to 20 courses, ranked by `match_score`. Each item:

| Field             | Type       | Description                                    |
|-------------------|------------|------------------------------------------------|
| `name`            | string     | Course title                                   |
| `url`             | string     | Direct Coursera link                           |
| `match_score`     | float      | Relevance score (0–1)                          |
| `job_category`    | string     | Role this course targets                       |
| `difficulty`      | string     | `Beginner` / `Intermediate` / `Advanced`       |
| `duration`        | string     | Estimated completion time                      |
| `covered_skills`  | `string[]` | Skills this course teaches                     |

#### `data.readiness_score`

| Field             | Type       | Description                                              |
|-------------------|------------|----------------------------------------------------------|
| `score`           | float      | 0.0–1.0 SBERT semantic similarity score                  |
| `matched_skills`  | `string[]` | Skills that contributed to the score                     |
| `interpretation`  | string     | Plain-language verdict generated from the score range    |

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
| 400  | 400    | `target_role` is unknown or empty              |
| 400  | 400    | `profile.skills` is empty                      |
| 422  | 422    | Request body does not match schema             |
| 500  | 500    | Internal model inference error                 |

---

### Frontend UX Hint

```
1s  → "Processing your CV profile…"
2s  → "AI model is analyzing the skill gap for this role…"
4s  → "Searching for relevant course recommendations…"
6s  → "Calculating your readiness score…"
```

After response: display a **dashboard** with the skill gap, a course list, and the readiness score. User may then click "Generate Career Pivot" to proceed to Phase 3.

---

## Endpoint 3 — Career Pivot Radar

### `POST /api/v1/cv/career-pivot`

**Purpose:** Given the full Phase 2 analysis, use RAG (SBERT role centroid similarity) + Groq Llama 3.3 70B in a single-shot JSON call to recommend alternative career paths.

The response contains **two layers** of recommendations:
- **Layer 1 (`alternative_roles`)** — Data-backed roles from the 27-role dataset with real metrics (SBERT score, skill overlap %)
- **Layer 2 (`ai_discovered_roles`)** — Roles discovered by Groq LLM from full CV analysis, **not limited to the dataset**. Includes roles like specializations, lateral moves, leadership paths, and pivots that the static dataset cannot cover.

**Phase:** 3 of 3 (final output)

---

### Request

```http
POST /api/v1/cv/career-pivot
Content-Type: application/json
```

```json
{
  "profile": { "...": "CVProfile object" },
  "target_role": "Data Scientist",
  "skill_gap": {
    "matched_skills": ["python", "sql"],
    "missing_skills": [
      { "skill": "pytorch", "priority_score": 0.92 }
    ]
  },
  "course_recommendations": [ "..." ],
  "readiness_score": {
    "score": 0.71,
    "matched_skills": ["python", "sql"],
    "interpretation": "Good fit."
  }
}
```

> **Tip:** The `data` field returned by `POST /api/v1/cv/analyze` can be sent **as-is** as the body of this endpoint — no transformation needed.

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
      "verdict":          "Strong profile for Data Scientist. The deep learning gap can be closed in 2-3 months."
    },
    "alternative_roles": [
      {
        "role_name":                  "Machine Learning Engineer",
        "sbert_match_score":          0.8912,
        "skill_overlap_pct":          72.0,
        "why_good_fit":               "Your data pipeline and Python experience are directly relevant for MLOps.",
        "transferable_skills": [
          { "skill": "python",    "relevance": "Primary language for ML pipelines" },
          { "skill": "docker",    "relevance": "Essential for model containerization" }
        ],
        "gap_skills":                 ["mlflow", "kubernetes", "ci/cd for ml"],
        "transition_difficulty":      "moderate",
        "estimated_transition_time":  "3-6 months",
        "first_step":                 "Complete the MLOps Specialization on Coursera to bridge the deployment gap."
      }
    ],
    "ai_discovered_roles": [
      {
        "role_name":                  "ML Platform Engineer",
        "category":                   "specialization",
        "why_good_fit":               "Your background in data engineering combined with ML skills makes you an ideal candidate for building ML platform infrastructure.",
        "transferable_skills":        ["python", "docker", "gcp", "sql"],
        "skills_to_develop":          ["kubeflow", "mlflow", "terraform"],
        "transition_difficulty":      "moderate",
        "estimated_transition_months": 6,
        "skill_readiness_pct":        57.1,
        "first_step":                 "Deploy your first model using Kubeflow Pipelines on GCP.",
        "market_demand":              "high"
      },
      {
        "role_name":                  "AI/ML Tech Lead",
        "category":                   "leadership",
        "why_good_fit":               "With 4.5 years of experience and broad skill depth, you are ready to lead a small data/ML team.",
        "transferable_skills":        ["python", "tensorflow", "scikit-learn", "gcp"],
        "skills_to_develop":          ["team leadership", "system design", "stakeholder management"],
        "transition_difficulty":      "challenging",
        "estimated_transition_months": 18,
        "skill_readiness_pct":        57.1,
        "first_step":                 "Take on a senior engineer role first, then mentor juniors to build a leadership track record.",
        "market_demand":              "medium"
      }
    ],
    "strongest_transferable_skills": ["python", "sql", "gcp", "scikit-learn"],
    "suggested_certifications": [
      {
        "name":      "Google Professional Data Engineer",
        "relevance": "Validates your GCP skills and opens doors to data engineering roles."
      },
      {
        "name":      "TensorFlow Developer Certificate",
        "relevance": "Closes the deep learning gap for Data Scientist / MLE positions."
      }
    ],
    "universal_advice": "Your Python + cloud foundation is your biggest asset. Add one orchestration tool (Airflow) and one experiment tracking tool (MLflow) — just these two are enough to make you competitive for Data Engineer and MLE roles within 3 months."
  },
  "metadata": {
    "retrieval_method":    "sbert_role_centroid_cosine",
    "roles_evaluated":     27,
    "roles_returned":      5,
    "llm_model":           "llama-3.3-70b-versatile",
    "llm_turns":           3,
    "processing_time_ms":  18420,
    "timestamp":           "2026-05-29T08:00:05.789000+00:00"
  }
}
```

#### `data.current_role_assessment`

| Field             | Type                                                        | Description                             |
|-------------------|-------------------------------------------------------------|-----------------------------------------|
| `target_role`     | string                                                      | Echoes the requested role               |
| `readiness_score` | float (0.0–1.0)                                             | From Phase 2, not modified              |
| `readiness_level` | `"low"` \| `"moderate"` \| `"high"` \| `"excellent"`       | Derived from score server-side          |
| `verdict`         | string                                                      | LLM-generated plain-language assessment |

#### `data.alternative_roles[]` — Layer 1 (data-backed)

| Field                        | Type                                          | Source        | Description                                     |
|------------------------------|-----------------------------------------------|---------------|-------------------------------------------------|
| `role_name`                  | string                                        | dataset       | Role from the 27-role dataset                   |
| `sbert_match_score`          | float (0.0–1.0)                               | server-computed | SBERT cosine similarity of user skills vs role  |
| `skill_overlap_pct`          | float (0.0–100.0)                             | server-computed | % of user skills matching role requirements     |
| `why_good_fit`               | string                                        | AI-generated  | LLM explanation based on profile analysis       |
| `transferable_skills`        | `TransferableSkill[]`                         | AI-generated  | Skills that transfer with explanation           |
| `gap_skills`                 | `string[]`                                    | server-computed | Skills still needed from the dataset            |
| `transition_difficulty`      | `"easy"` \| `"moderate"` \| `"challenging"`   | AI-generated  | LLM assessment                                  |
| `estimated_transition_time`  | string                                        | AI-generated  | e.g. `"3-6 bulan"`                              |
| `first_step`                 | string                                        | AI-generated  | Actionable first recommendation                  |

#### `TransferableSkill`

| Field       | Type   | Description                     |
|-------------|--------|---------------------------------|
| `skill`     | string | Skill name                      |
| `relevance` | string | Why this skill matters for role |

#### `data.ai_discovered_roles[]` — Layer 2 (AI-discovered, not limited to dataset)

| Field                        | Type                                                          | Source        | Description                                       |
|------------------------------|---------------------------------------------------------------|---------------|---------------------------------------------------|
| `role_name`                  | string                                                        | AI-generated  | Role suggested by Groq LLM from full CV analysis  |
| `category`                   | `"specialization"` \| `"adjacent"` \| `"leadership"` \| `"pivot"` | AI-generated | Type of career move |
| `why_good_fit`               | string                                                        | AI-generated  | Reasoning based on work history, not just skills  |
| `transferable_skills`        | `string[]`                                                    | AI-generated  | User's existing skills relevant to this role      |
| `skills_to_develop`          | `string[]`                                                    | AI-generated  | Top skills to learn for the transition            |
| `transition_difficulty`      | `"easy"` \| `"moderate"` \| `"challenging"`                   | AI-generated  | Effort estimate                                   |
| `estimated_transition_months`| int (1–48)                                                    | AI-generated  | Numeric months estimate (sortable)                |
| `skill_readiness_pct`        | float (0.0–100.0)                                             | server-computed | `len(transferable) / (transferable + to_develop) * 100` |
| `first_step`                 | string                                                        | AI-generated  | Concrete first action to take                     |
| `market_demand`              | `"high"` \| `"medium"` \| `"low"`                             | AI-generated  | LLM assessment of current job market demand       |

> **Note on metrics trust:** `sbert_match_score`, `skill_overlap_pct` (Layer 1), and `skill_readiness_pct` (Layer 2) are all computed server-side from real data — they are **not** AI estimates. Only text fields and `estimated_transition_months` are AI-generated.

#### `data.suggested_certifications[]`

| Field       | Type   | Description                          |
|-------------|--------|--------------------------------------|
| `name`      | string | Certification / course name          |
| `relevance` | string | Why this cert helps the candidate    |

#### `metadata` fields

| Field                 | Type   | Description                                          |
|-----------------------|--------|------------------------------------------------------|
| `retrieval_method`    | string | Always `"sbert_role_centroid_cosine"`                |
| `roles_evaluated`     | int    | Total roles compared using SBERT similarity (27)     |
| `roles_returned`      | int    | Number of roles in `alternative_roles` (up to 5)    |
| `llm_model`           | string | Active Groq model (from `GROQ_MODEL` env var)        |
| `llm_turns`           | int    | LLM conversation turns used (always 3)               |
| `processing_time_ms`  | int    | Total wall-clock time including LLM latency          |
| `timestamp`           | string | ISO-8601 UTC                                         |

---

### Error Responses

| HTTP | `code` | Scenario                                              |
|------|--------|-------------------------------------------------------|
| 400  | 400    | `target_role` is empty or `skills` is empty           |
| 422  | 422    | Request body does not match schema                    |
| 503  | 503    | `GROQ_API_KEY` not configured, or Groq quota exceeded     |
| 500  | 500    | Unexpected internal error                             |

---

### Frontend UX Hint

```
2s  → "AI model is retrieving matching alternative roles…"
4s  → "Analyzing fit and your transferable skills…"
8s  → "AI is exploring career paths outside the database…"
12s → "Almost done — formatting your personalized career recommendations…"
```

After response: display a **Career Pivot Radar** visualization — show Layer 1 roles on a radar/spider chart (real skill overlap data), and Layer 2 roles as AI suggestion cards with category badge (specialization / adjacent / leadership / pivot).

---

## Roles List

### `GET /api/v1/roles`

**Purpose:** Returns the complete list of 27 supported `target_role` values. Frontend should call this once on startup to populate the role dropdown — avoids hardcoding the list.

```http
GET /api/v1/roles
```

### Response `200 OK`

```json
{
  "status": "success",
  "code": 200,
  "data": {
    "roles": [
      "AI Engineer",
      "Backend Developer",
      "Business Analyst",
      "Business Intelligence Analyst",
      "Cloud Engineer",
      "Cyber Security Analyst",
      "Data Analyst",
      "Data Engineer",
      "Data Scientist",
      "Database Administrator",
      "DevOps Engineer",
      "ERP Consultant",
      "Embedded/IoT Engineer",
      "Frontend Developer",
      "Full Stack Developer",
      "General IT Specialist",
      "IT Consultant",
      "Machine Learning Engineer",
      "Mobile Developer",
      "Network Engineer",
      "Product Manager",
      "QA Engineer",
      "Robotics Engineer",
      "Security Engineer",
      "Site Reliability Engineer",
      "Software Engineer",
      "Solutions Architect"
    ],
    "count": 27
  },
  "metadata": {
    "timestamp": "2026-05-29T08:00:00.000Z"
  }
}
```

> **Frontend guidance:** Render `data.roles` as a searchable `<select>` / combobox. Do not allow free-text input — the ML models are trained exclusively on these 27 roles.  
> Both `/analyze` and `/career-pivot` accept the role **case-insensitively** (`"data scientist"` → normalized to `"Data Scientist"` server-side), but using the exact values from this endpoint is recommended.

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
  "roles_loaded": 27,
  "sbert_loaded": true,
  "role_centroids": 27,
  "model3_available": true,
  "model4_available": true
}
```

| Field               | Type    | Description                                             |
|---------------------|---------|---------------------------------------------------------|
| `status`            | string  | `"ok"` when healthy                                     |
| `ner_available`     | boolean | `true` if DeBERTa NER model loaded successfully         |
| `roles_loaded`      | int     | Number of role indexes loaded (expected: 27)            |
| `sbert_loaded`      | boolean | `true` if Sentence-BERT model is in memory              |
| `role_centroids`    | int     | Number of precomputed role centroids (expected: 27)     |
| `model3_available`  | boolean | `true` if Skill Gap TF SavedModel loaded                |
| `model4_available`  | boolean | `true` if Course Recommendation TF SavedModel loaded    |

> **Frontend guidance:** Poll this endpoint once on app startup. If `sbert_loaded` is `false` or `roles_loaded` is 0, show a "AI service is warming up…" banner and retry after 5 seconds.

---

## Starting the Server

```bash
# From ai_engine/ directory (with .venv activated)

# Development (auto-reload)
uvicorn app:app --host 127.0.0.1 --port 8000 --reload

# Production
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
```

> Use `--workers 1` because TensorFlow and PyTorch models are held in process memory. Multi-worker spawning would multiply RAM usage.

### Required Environment Variables (`.env`)

```ini
# Groq API key — required for Career Pivot Radar (Phase 3)
# Get yours FREE (no credit card) at: https://console.groq.com/keys
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Groq model (default: llama-3.3-70b-versatile)
# Other options: llama-3.1-8b-instant (faster), llama-4-scout-17b-16e-instruct (newer)
GROQ_MODEL=llama-3.3-70b-versatile

# Optional overrides (defaults shown — relative to ai_engine/)
NER_CONFIDENCE_THRESHOLD=0.5
NER_BASE_MODEL=microsoft/deberta-v3-base
```

All model file paths are resolved automatically from `model_assets/` — no manual path configuration needed.

---

## Error Code Reference

| HTTP | Meaning                         | Common Causes                                    |
|------|---------------------------------|--------------------------------------------------|
| 400  | Bad Request                     | Invalid URL, empty field, unknown role           |
| 422  | Unprocessable Entity            | JSON schema mismatch (wrong types, missing keys) |
| 500  | Internal Server Error           | ML model crash, unexpected exception             |
| 502  | Bad Gateway                     | Cannot reach Cloudinary (Phase 1 only)           |
| 503  | Service Unavailable             | API key missing or Groq quota exceeded (Phase 3)   |

---

## Integration Sequence (Frontend → Backend → AI Engine)

> **Architecture:** The frontend never calls the AI Engine directly. All AI requests are proxied through the Express.js backend (`backend/`), which holds auth middleware, DB persistence, and business logic.

```
Frontend (React)          Backend (Express.js)       QLOP AI Engine (FastAPI)
     │                           │                           │
     │── POST /api/cv/upload ───►│                           │
     │                           │── POST /api/v1/cv/extract►│  (Phase 1)
     │                           │◄── 200 CVProfile JSON ────│
     │◄── CVProfile JSON ────────│                           │
     │                           │                           │
     │  [User edits profile]     │                           │
     │                           │                           │
     │── POST /api/cv/analyze ──►│                           │
     │                           │── POST /api/v1/cv/analyze►│  (Phase 2)
     │                           │◄── 200 AnalyzeData JSON ──│
     │◄── AnalyzeData JSON ──────│  (saved to DB)            │
     │                           │                           │
     │  [User clicks Career Pivot]│                          │
     │                           │                           │
     │── POST /api/cv/pivot ────►│                           │
     │                           │── POST /api/v1/cv/career-pivot►│  (Phase 3)
     │                           │◄── 200 CareerPivotOutput ─│
     │◄── CareerPivotOutput ─────│  (saved to DB)            │
     │                           │                           │
     │  [Display radar + cards]  │                           │
```

> **For the Express.js backend team:** The body of `POST /api/v1/cv/career-pivot` (sent to the AI Engine) is exactly the `data` field from the `POST /api/v1/cv/analyze` response — no transformation needed. Store the full AI response in the database before forwarding the result to the frontend.

---

*Document version: 2.1 · Last updated: 2026-05-29 · Maintained by QLOP AI Team*
