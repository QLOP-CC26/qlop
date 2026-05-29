"""
QLOP AI Engine — Endpoint Test Suite
=====================================
Jalankan dari folder ai_engine dengan venv aktif:

    python test_api.py                  # semua test, skip career-pivot (cepat)
    python test_api.py --full           # semua test termasuk career-pivot (LLM, ~30 detik)
    python test_api.py --host 0.0.0.0   # custom host
    python test_api.py --port 9000       # custom port
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any

import httpx

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="QLOP API test suite")
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", default="8000")
parser.add_argument("--full", action="store_true", help="Include career-pivot (calls Groq/Llama, ~30s)")
args = parser.parse_args()

BASE = f"http://{args.host}:{args.port}"

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
SKIP = "\033[93mSKIP\033[0m"
BOLD = "\033[1m"
END  = "\033[0m"

results: list[tuple[str, bool, str]] = []


def check(label: str, condition: bool, detail: str = "") -> bool:
    icon = PASS if condition else FAIL
    detail_str = f"  ({detail})" if detail else ""
    print(f"    [{icon}] {label}{detail_str}")
    results.append((label, condition, detail))
    return condition


def section(title: str) -> None:
    print(f"\n{BOLD}{'─'*60}{END}")
    print(f"{BOLD}  {title}{END}")
    print(f"{BOLD}{'─'*60}{END}")


def get(path: str, timeout: int = 10) -> httpx.Response:
    return httpx.get(f"{BASE}{path}", timeout=timeout)


def post(path: str, body: dict, timeout: int = 30) -> httpx.Response:
    return httpx.post(f"{BASE}{path}", json=body, timeout=timeout)


# ──────────────────────────────────────────────────────────────────────────────
# Shared payloads (realistic Indonesian IT profile)
# ──────────────────────────────────────────────────────────────────────────────

PROFILE = {
    "name": "Budi Santoso",
    "email": "budi.santoso@gmail.com",
    "phone": "08123456789",
    "location": "Jakarta",
    "total_experience_years": 3.0,
    "skills": ["Python", "JavaScript", "React", "Docker", "PostgreSQL", "Git", "FastAPI"],
    "work_experience": [
        {"company": "Tokopedia", "designation": "Backend Engineer", "duration": "2 years"},
        {"company": "Startup XYZ", "designation": "Junior Dev", "duration": "1 year"},
    ],
    "education": [
        {"degree": "S1 Informatika", "institution": "Universitas Indonesia", "year": "2021"}
    ],
}

SKILL_GAP = {
    "matched_skills": ["python", "docker", "git"],
    "missing_skills": [
        {"skill": "go", "priority_score": 0.6152},
        {"skill": "kubernetes", "priority_score": 0.4801},
        {"skill": "grpc", "priority_score": 0.3500},
    ],
}

COURSES = [
    {
        "name": "Go Programming Language",
        "url": "https://www.coursera.org/learn/golang",
        "match_score": 0.87,
        "reason": "Covers Go — a critical gap skill",
        "job_category": "Backend Development",
        "difficulty": "Beginner",
        "duration": "17 hours",
        "covered_skills": ["go"],
    }
]

READINESS = {
    "score": 0.3155,
    "matched_skills": ["python", "docker", "git"],
    "interpretation": "moderate fit",
}

# Full analyze response data (reused as career-pivot input)
ANALYZE_DATA: dict[str, Any] = {}


# ──────────────────────────────────────────────────────────────────────────────
# 1. Health
# ──────────────────────────────────────────────────────────────────────────────

section("GET /health")
r = get("/health")
d = r.json()

check("HTTP 200", r.status_code == 200, str(r.status_code))
check("status = ok", d.get("status") == "ok", d.get("status"))
check("ner_available is bool", isinstance(d.get("ner_available"), bool), str(d.get("ner_available")))
check("roles_loaded >= 27", d.get("roles_loaded", 0) >= 27, str(d.get("roles_loaded")))
check("sbert_loaded = True", d.get("sbert_loaded") is True)
check("role_centroids >= 27", d.get("role_centroids", 0) >= 27, str(d.get("role_centroids")))
check("model3_available = True", d.get("model3_available") is True)
check("model4_available = True", d.get("model4_available") is True)


# ──────────────────────────────────────────────────────────────────────────────
# 2. OpenAPI docs
# ──────────────────────────────────────────────────────────────────────────────

section("GET /api/v1/roles  (role list for frontend dropdown)")
r = get("/api/v1/roles")
d = r.json()
check("HTTP 200", r.status_code == 200, str(r.status_code))
check("envelope status=success", d.get("status") == "success")
roles = d.get("data", {}).get("roles", [])
check("roles is list", isinstance(roles, list))
check("count = 27", d.get("data", {}).get("count") == 27, str(d.get("data", {}).get("count")))
check("Data Scientist in roles", "Data Scientist" in roles)
check("Backend Developer in roles", "Backend Developer" in roles)


section("GET /docs  (Swagger UI)")
r = get("/docs")
check("HTTP 200", r.status_code == 200, str(r.status_code))

section("GET /openapi.json  (schema available)")
r = get("/openapi.json")
d = r.json()
check("HTTP 200", r.status_code == 200)
check("has paths", "paths" in d)
check("has /extract",  "/api/v1/cv/extract"       in d.get("paths", {}))
check("has /analyze",  "/api/v1/cv/analyze"        in d.get("paths", {}))
check("has /career-pivot", "/api/v1/cv/career-pivot" in d.get("paths", {}))


# ──────────────────────────────────────────────────────────────────────────────
# 3. POST /api/v1/cv/extract — validation errors (no real PDF URL needed)
# ──────────────────────────────────────────────────────────────────────────────

section("POST /api/v1/cv/extract — input validation")

r = post("/api/v1/cv/extract", {"cloudinary_url": "not_a_valid_url"})
check("bad URL → 400", r.status_code == 400, str(r.status_code))
check("envelope status=error", r.json().get("status") == "error")

r = post("/api/v1/cv/extract", {})
check("missing field → 422", r.status_code == 422, str(r.status_code))
check("envelope status=error", r.json().get("status") == "error")


# ──────────────────────────────────────────────────────────────────────────────
# 4. POST /api/v1/cv/analyze — happy path
# ──────────────────────────────────────────────────────────────────────────────

section("POST /api/v1/cv/analyze — happy path  (Backend Developer)")
t0 = time.perf_counter()
r = post("/api/v1/cv/analyze", {"profile": PROFILE, "target_role": "Backend Developer"}, timeout=60)
elapsed_ms = int((time.perf_counter() - t0) * 1000)

d = r.json()
data = d.get("data", {})
meta = d.get("metadata", {})

check("HTTP 200", r.status_code == 200, str(r.status_code))
check("envelope status=success", d.get("status") == "success")
check("has data + metadata", "data" in d and "metadata" in d)

# profile echo
profile_out = data.get("profile", {})
check("data.profile.name preserved", profile_out.get("name") == PROFILE["name"])
check("data.profile.skills is flat list", isinstance(profile_out.get("skills"), list))
check("data.profile.skills not empty", len(profile_out.get("skills", [])) > 0)
check("data.target_role = Backend Developer", data.get("target_role") == "Backend Developer")

# skill_gap
sg = data.get("skill_gap", {})
check("skill_gap.matched_skills is list", isinstance(sg.get("matched_skills"), list))
check("skill_gap.missing_skills is list", isinstance(sg.get("missing_skills"), list))
if sg.get("missing_skills"):
    m0 = sg["missing_skills"][0]
    check("missing_skill has 'skill' key", "skill" in m0, str(m0.keys()))
    check("missing_skill has 'priority_score' float", isinstance(m0.get("priority_score"), float))

# course_recommendations
courses = data.get("course_recommendations", [])
check("course_recommendations is list", isinstance(courses, list))
if courses:
    c0 = courses[0]
    check("course has name", bool(c0.get("name")), c0.get("name"))
    check("course has url", bool(c0.get("url")), c0.get("url"))
    check("course has match_score float", isinstance(c0.get("match_score"), float))
    check("course has job_category", "job_category" in c0)
    check("course has difficulty", "difficulty" in c0)
    check("course has duration", "duration" in c0)

# readiness_score
rs = data.get("readiness_score", {})
check("readiness_score.score is float", isinstance(rs.get("score"), float), str(rs.get("score")))
check("readiness_score 0..1 range", 0.0 <= rs.get("score", -1) <= 1.0)
check("readiness_score.matched_skills is list", isinstance(rs.get("matched_skills"), list))
check("readiness_score.interpretation is str", isinstance(rs.get("interpretation"), str))

# metadata
check("metadata.cv_skills_count > 0", meta.get("cv_skills_count", 0) > 0, str(meta.get("cv_skills_count")))
check("metadata.processing_time_ms > 0", meta.get("processing_time_ms", 0) > 0)
check(f"wall-clock < 30s", elapsed_ms < 30_000, f"{elapsed_ms}ms")

# Save for career-pivot
ANALYZE_DATA.update(data)


# ──────────────────────────────────────────────────────────────────────────────
# 5. POST /api/v1/cv/analyze — other valid roles
# ──────────────────────────────────────────────────────────────────────────────

section("POST /api/v1/cv/analyze — multiple valid roles")
for role in ["Data Scientist", "DevOps Engineer", "Frontend Developer", "Machine Learning Engineer"]:
    r2 = post("/api/v1/cv/analyze", {"profile": PROFILE, "target_role": role}, timeout=60)
    check(f"role '{role}' → 200", r2.status_code == 200, str(r2.status_code))


# ──────────────────────────────────────────────────────────────────────────────
# 6. POST /api/v1/cv/analyze — error cases
# ──────────────────────────────────────────────────────────────────────────────

section("POST /api/v1/cv/analyze — error cases")

r = post("/api/v1/cv/analyze", {"profile": PROFILE, "target_role": "Astronaut"})
check("unknown role → 400", r.status_code == 400, str(r.status_code))
check("error envelope (unknown role)", r.json().get("status") == "error")
detail = r.json().get("detail", "")
check("detail lists valid roles", "Role yang valid:" in detail)

r = post("/api/v1/cv/analyze", {
    "profile": {**PROFILE, "skills": []},
    "target_role": "Backend Developer",
})
check("empty skills → 400", r.status_code == 400, str(r.status_code))

r = post("/api/v1/cv/analyze", {})
check("missing body → 422", r.status_code == 422, str(r.status_code))

r = post("/api/v1/cv/analyze", {"profile": PROFILE})
check("missing target_role → 422", r.status_code == 422, str(r.status_code))


# ──────────────────────────────────────────────────────────────────────────────
# 7. POST /api/v1/cv/career-pivot — schema & error validation (no LLM call)
# ──────────────────────────────────────────────────────────────────────────────

section("POST /api/v1/cv/career-pivot — schema validation (no LLM)")

PIVOT_PAYLOAD = {
    "profile": PROFILE,
    "target_role": "Backend Developer",
    "skill_gap": SKILL_GAP,
    "course_recommendations": COURSES,
    "readiness_score": READINESS,
}

# missing required field
r = post("/api/v1/cv/career-pivot", {})
check("missing body → 422", r.status_code == 422, str(r.status_code))
check("error envelope", r.json().get("status") == "error")

r = post("/api/v1/cv/career-pivot", {k: v for k, v in PIVOT_PAYLOAD.items() if k != "target_role"})
check("missing target_role → 422", r.status_code == 422, str(r.status_code))

# empty skills
r = post("/api/v1/cv/career-pivot", {
    **PIVOT_PAYLOAD,
    "profile": {**PROFILE, "skills": []},
})
check("empty skills → 400", r.status_code == 400, str(r.status_code))


# ──────────────────────────────────────────────────────────────────────────────
# 8. POST /api/v1/cv/career-pivot — full LLM call (opt-in with --full)
# ──────────────────────────────────────────────────────────────────────────────

if args.full:
    section("POST /api/v1/cv/career-pivot — full LLM call  (--full flag)")

    pivot_input = {
        "profile": PROFILE,
        "target_role": ANALYZE_DATA.get("target_role", "Backend Developer"),
        "skill_gap": ANALYZE_DATA.get("skill_gap", SKILL_GAP),
        "course_recommendations": ANALYZE_DATA.get("course_recommendations", COURSES)[:3],
        "readiness_score": ANALYZE_DATA.get("readiness_score", READINESS),
    }

    print("    (calling Groq/Llama — mungkin 20–40 detik...)")
    t0 = time.perf_counter()
    r = post("/api/v1/cv/career-pivot", pivot_input, timeout=120)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    d = r.json()

    check("HTTP 200 or 503", r.status_code in (200, 503), str(r.status_code))

    if r.status_code == 200:
        data = d.get("data", {})
        meta = d.get("metadata", {})

        assessment = data.get("current_role_assessment", {})
        check("current_role_assessment.target_role", bool(assessment.get("target_role")))
        check("readiness_score is float", isinstance(assessment.get("readiness_score"), float))
        check("readiness_level valid", assessment.get("readiness_level") in ("low", "moderate", "high", "excellent"))
        check("verdict is non-empty string", bool(assessment.get("verdict")))

        # Layer 1: data-backed roles
        alt = data.get("alternative_roles", [])
        check("alternative_roles is list", isinstance(alt, list))
        check("alternative_roles count 1..5", 1 <= len(alt) <= 5, str(len(alt)))
        if alt:
            r0 = alt[0]
            check("role has role_name", bool(r0.get("role_name")))
            check("sbert_match_score 0..1", 0.0 <= r0.get("sbert_match_score", -1) <= 1.0)
            check("skill_overlap_pct 0..100", 0.0 <= r0.get("skill_overlap_pct", -1) <= 100.0)
            check("transition_difficulty valid",
                  r0.get("transition_difficulty") in ("easy", "moderate", "challenging"))
            check("why_good_fit non-empty", bool(r0.get("why_good_fit")))
            check("first_step non-empty", bool(r0.get("first_step")))

        # Layer 2: AI-discovered roles (not limited to dataset)
        ai_roles = data.get("ai_discovered_roles", [])
        check("ai_discovered_roles is list", isinstance(ai_roles, list))
        check("ai_discovered_roles count 1..6", 1 <= len(ai_roles) <= 6, str(len(ai_roles)))
        if ai_roles:
            ar0 = ai_roles[0]
            check("ai role has role_name", bool(ar0.get("role_name")))
            check("ai role category valid",
                  ar0.get("category") in ("specialization", "adjacent", "leadership", "pivot"),
                  str(ar0.get("category")))
            check("ai role skill_readiness_pct 0..100",
                  0.0 <= ar0.get("skill_readiness_pct", -1) <= 100.0,
                  str(ar0.get("skill_readiness_pct")))
            check("ai role estimated_transition_months int",
                  isinstance(ar0.get("estimated_transition_months"), int),
                  str(ar0.get("estimated_transition_months")))
            check("ai role market_demand valid",
                  ar0.get("market_demand") in ("high", "medium", "low"),
                  str(ar0.get("market_demand")))
            check("ai role why_good_fit non-empty", bool(ar0.get("why_good_fit")))
            check("ai role first_step non-empty", bool(ar0.get("first_step")))
            check("ai role transferable_skills is list", isinstance(ar0.get("transferable_skills"), list))
            check("ai role skills_to_develop is list", isinstance(ar0.get("skills_to_develop"), list))

        check("strongest_transferable_skills is list",
              isinstance(data.get("strongest_transferable_skills"), list))
        check("suggested_certifications is list",
              isinstance(data.get("suggested_certifications"), list))
        check("universal_advice non-empty", bool(data.get("universal_advice")))

        check("metadata.llm_turns = 3", meta.get("llm_turns") == 3, str(meta.get("llm_turns")))
        check("metadata.llm_model non-empty", bool(meta.get("llm_model")), meta.get("llm_model"))
        check(f"wall-clock < 90s", elapsed_ms < 90_000, f"{elapsed_ms}ms")

    elif r.status_code == 503:
        print("    (503 — Groq quota/key issue, bukan bug aplikasi)")
        check("503 envelope status=error", d.get("status") == "error")

else:
    section("POST /api/v1/cv/career-pivot — full LLM call  (dilewati)")
    print(f"    [{SKIP}] Jalankan dengan --full untuk test Groq/Llama LLM")


# ──────────────────────────────────────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────────────────────────────────────

total   = len(results)
passed  = sum(1 for _, ok, _ in results if ok)
failed  = total - passed

print(f"\n{'═'*60}")
print(f"{BOLD}  HASIL: {passed}/{total} pass", end="")
if failed:
    print(f"  |  {failed} GAGAL", end="")
print(f"{END}")
print(f"{'═'*60}")

if failed:
    print(f"\n{BOLD}  Test yang gagal:{END}")
    for label, ok, detail in results:
        if not ok:
            print(f"    [{FAIL}] {label}" + (f"  ({detail})" if detail else ""))
    print()
    sys.exit(1)
else:
    print(f"\n  Semua test lulus! Server siap digunakan.\n")
    sys.exit(0)
