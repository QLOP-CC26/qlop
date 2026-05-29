#!/usr/bin/env python3
"""
build_ner_dataset.py — QLOP Model 1 NER dataset builder.

Run locally to produce kaggle_ready_dataset/ from raw CSVs + DataTurks JSON.
Requires only pandas + stdlib; no TensorFlow / PyTorch / spaCy needed.

Usage:
  python ai_engine/data_pipeline/build_ner_dataset.py \
    --qlop-root  "C:/Users/hp/.cache/kagglehub/datasets/husniabdillah/dataset-qlop/versions/3" \
    --dataturks-path  "path/to/Entity Recognition in Resumes.json" \
    --out-dir  ai_engine/data_pipeline/kaggle_ready_dataset

Silver labeling (optional, adds ~500 job-desc examples):
  ... --silver
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import logging
import os
import random
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("build_ner")

# ── BIO label schema (must match pretrained model yashpwr/resume-ner-bert-v2) ──
ENTITY_TYPES = [
    "Skills", "Designation", "Name", "Email Address", "Phone",
    "Location", "Companies worked at", "Years of Experience",
    "Degree", "College Name", "Graduation Year", "UNKNOWN",
]
BIO_LABELS: list[str] = ["O"]
for _et in ENTITY_TYPES:
    BIO_LABELS.append(f"B-{_et}")
    BIO_LABELS.append(f"I-{_et}")
LABEL2ID: dict[str, int] = {l: i for i, l in enumerate(BIO_LABELS)}
ID2LABEL: dict[int, str] = {i: l for l, i in LABEL2ID.items()}

# ── Stop-skills: soft/generic tokens that pollute the skill vocabulary ─────
STOP_SKILLS: set[str] = {
    "deadline", "adapt", "adaptable", "adaptability", "reduce", "post",
    "google", "linkedin", "facebook", "twitter", "instagram", "tiktok",
    "programming language", "magic", "tracking software", "analyze",
    "coordinate", "collaborate", "communicate", "team player", "teamwork",
    "leadership", "problem solving", "critical thinking", "analytical",
    "attention to detail", "time management", "multitask", "multitasking",
    "organization", "organizational", "self-motivated", "proactive", "creative",
    "innovative", "flexible", "work ethic", "interpersonal",
    "verbal", "written", "presentation", "negotiation", "persuasion",
    "conflict resolution", "decision making", "strategic thinking",
    "planning", "scheduling", "budgeting", "reporting",
    "ms office", "word", "powerpoint", "outlook",
    "detail-oriented", "fast learner", "quick learner", "willingness",
    "initiative", "integrity", "punctual", "responsible", "reliable",
    "honest", "diligent", "enthusiastic", "positive attitude",
    "slack", "zoom", "teams",
}

# ── Synonym / normalization map (raw -> canonical) ─────────────────────────
SYNONYM_MAP: dict[str, str] = {
    "kubernete": "kubernetes", "k8s": "kubernetes", "kube": "kubernetes",
    "nodejs": "node.js", "node js": "node.js",
    "reactjs": "react", "react.js": "react", "react js": "react",
    "vuejs": "vue.js", "vue js": "vue.js",
    "angularjs": "angular", "angular js": "angular",
    "postgres": "postgresql", "psql": "postgresql",
    "mongo": "mongodb", "mongod": "mongodb",
    "rest api": "restful api", "rest apis": "restful api",
    "graphql api": "graphql",
    "dotnet": ".net", ".net core": ".net",
    "spring": "spring boot",
    "scikit learn": "scikit-learn", "sklearn": "scikit-learn",
    "natural language processing": "nlp",
    "object oriented programming": "oop", "object-oriented programming": "oop",
    "microservice": "microservices", "microservice architecture": "microservices",
    "microservices architecture": "microservices",
    "version control": "git",
    "agile methodology": "agile", "agile scrum": "agile",
    "scrum methodology": "scrum",
    "test driven development": "tdd",
    "html5": "html", "html & css": "html/css", "html and css": "html/css",
    "css3": "css", "sass/scss": "sass", "scss": "sass",
    "tailwindcss": "tailwind css",
    "express.js": "express", "expressjs": "express",
    "nextjs": "next.js", "nestjs": "nest.js", "nuxtjs": "nuxt.js",
    "elasticsearch": "elasticsearch", "elastic search": "elasticsearch",
    "apache kafka": "kafka", "apache spark": "spark",
    "microsoft sql server": "sql server", "ms sql": "sql server", "mssql": "sql server",
    "nosql database": "nosql",
    "google cloud": "gcp", "google cloud platform": "gcp",
    "amazon web services": "aws", "amazon aws": "aws",
    "microsoft azure": "azure", "azure cloud": "azure",
    "bash scripting": "bash", "shell scripting": "bash",
    "python3": "python", "python 3": "python",
    "golang": "go",
    "c sharp": "c#",
    "kotlin android": "kotlin", "swift ios": "swift",
    "flutter dart": "flutter",
    "jupyter notebook": "jupyter",
    "tableau desktop": "tableau",
    "power bi": "power bi",
    "jira software": "jira",
    "material-ui": "material ui", "material ui": "material ui",
    "figma design": "figma",
    "react native": "react native",
    "unity3d": "unity",
    "github actions": "github actions",
    "gitlab ci": "gitlab",
    "ci/cd pipeline": "ci/cd",
    "continuous integration": "ci/cd", "continuous deployment": "ci/cd",
    "aws lambda": "aws lambda",
    "sqlite3": "sqlite",
    "oracle db": "oracle database",
    "redis cache": "redis",
    "message queue": "message queue",
    "windows server": "windows server",
    "linux server": "linux",
    "docker container": "docker", "docker containers": "docker",
}


# ─────────────────────────────────────────────────────────────────────────────
# Tokenization helpers (whitespace split, tracks char offsets)
# ─────────────────────────────────────────────────────────────────────────────

def ws_tokenize(text: str) -> list[tuple[str, int, int]]:
    """Split on whitespace, return (token, start_char, end_char) tuples."""
    return [(m.group(), m.start(), m.end()) for m in re.finditer(r"\S+", text)]


# Tokens that MUST be tagged O even inside a Skills span — they are delimiters
# between separate skills, not part of any skill name.
_SKILLS_BOUNDARY_RE = re.compile(
    r"^[,;/|&•·\-–—]+$"          # pure punctuation delimiters
    r"|^\($|^\)$"                  # standalone parens
    r"|^(?:and|or|AND|OR)$"        # conjunctions separating skill names
)
# Parenthetical noise like "(Less than 1 year)" or "(3 years)"
_PAREN_EXPERIENCE_RE = re.compile(
    r"\(.*?(?:year|yr|month|mo|experience|exp).*?\)", re.IGNORECASE
)


def _split_skills_span(
    text: str, span_s: int, span_e: int
) -> list[tuple[int, int]]:
    """Split a single large Skills char-span into individual skill sub-spans.

    DataTurks annotators often highlight an entire skills section as one entity.
    This function breaks it at commas, semicolons, parenthetical experience info,
    and other delimiters so each individual skill becomes its own B-Skills entity.
    """
    # First strip parenthetical experience annotations from the span text
    snippet = text[span_s:span_e]
    # Find sub-phrases by splitting on delimiters
    # Use regex to find continuous non-delimiter words
    sub_spans: list[tuple[int, int]] = []
    # Remove parenthetical patterns like "(Less than 1 year)" first
    cleaned = _PAREN_EXPERIENCE_RE.sub(",", snippet)
    # Split by commas, semicolons, pipes, colons, bullet points
    parts = re.split(r"[,;/|•·&:]+|\band\b|\bor\b", cleaned, flags=re.IGNORECASE)
    offset = 0
    for part in parts:
        # Find where this part starts in the original snippet
        stripped = part.strip()
        if not stripped or len(stripped) < 2:
            offset += len(part) + 1
            continue
        # Find the actual position in the original text
        idx = snippet.find(stripped, offset)
        if idx == -1:
            # Fallback: search case-insensitive from offset
            idx = snippet.lower().find(stripped.lower(), offset)
        if idx >= 0:
            abs_start = span_s + idx
            abs_end = abs_start + len(stripped)
            # Skip if it looks like experience/noise (e.g., "Less than 1 year")
            if not re.search(r"\d+\s*(?:year|yr|month|mo)", stripped, re.IGNORECASE):
                sub_spans.append((abs_start, abs_end))
            offset = idx + len(stripped)
        else:
            offset += len(part) + 1

    # If splitting produced nothing useful, keep the original span
    if not sub_spans:
        sub_spans = [(span_s, span_e)]
    return sub_spans


def spans_to_bio(
    tok_offsets: list[tuple[str, int, int]],
    spans: list[tuple[int, int, str]],
    keep_mega_spans: bool = False,
) -> list[str]:
    """Convert character-level spans to BIO string tags.

    When keep_mega_spans=False (default): splits large Skills spans at punctuation
    boundaries so each individual skill gets its own B-Skills tag. Punctuation tokens
    inside Skills spans are forced to O.

    When keep_mega_spans=True: preserves the original DataTurks mega-span format
    (entire skill section = B-Skills + I-Skills chain), matching the format that
    yashpwr/resume-ner-bert-v2 was trained on.

    Args:
        tok_offsets: list of (token_text, char_start, char_end_exclusive)
        spans: list of (char_start, char_end_exclusive, entity_label)
        keep_mega_spans: if True, do NOT split Skills spans at delimiters
    Returns:
        BIO label per token
    """
    tags = ["O"] * len(tok_offsets)
    for span_s, span_e, label in sorted(spans, key=lambda x: x[0]):
        b_label = f"B-{label}"
        i_label = f"I-{label}"
        first_in_span = True
        for idx, (tok_text, ts, te) in enumerate(tok_offsets):
            if ts < span_e and te > span_s:
                # For Skills: force punctuation/delimiters to O and restart B-tag
                # (only when NOT using mega-span format)
                if not keep_mega_spans and label == "Skills" and _SKILLS_BOUNDARY_RE.match(tok_text):
                    first_in_span = True  # next real token gets B-Skills
                    continue
                if tags[idx] == "O":
                    tags[idx] = b_label if first_in_span else i_label
                    first_in_span = False
                else:
                    first_in_span = False
    return tags


# ─────────────────────────────────────────────────────────────────────────────
# Loader modules
# ─────────────────────────────────────────────────────────────────────────────

def load_dataturks(path: str, keep_mega_spans: bool = False) -> list[dict]:
    """Load DataTurks NER JSON (one JSON object per line) -> BIO records.

    Each output record: {doc_id, tokens, ner_tags_str, source}.
    Drops documents with empty text or no annotations.

    When keep_mega_spans=True, preserves the original DataTurks annotation style
    where an entire "Skills:" section is one B-Skills + I-Skills... chain.
    This matches the training format of yashpwr/resume-ner-bert-v2 (90.87% F1).

    When keep_mega_spans=False (default), splits large spans at commas/semicolons
    so each individual skill becomes its own B-Skills entity.
    """
    records: list[dict] = []
    path_obj = Path(path)
    if not path_obj.exists():
        log.error("DataTurks file not found: %s", path)
        sys.exit(1)

    raw_lines = path_obj.read_text(encoding="utf-8").splitlines()
    log.info("DataTurks: reading %d lines from %s", len(raw_lines), path)

    skipped = 0
    for line_no, line in enumerate(raw_lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            log.warning("Line %d: JSON parse error (%s), skipping", line_no, exc)
            skipped += 1
            continue

        text: str = obj.get("content", "").strip()
        if not text:
            skipped += 1
            continue

        annotations = obj.get("annotation") or []
        spans: list[tuple[int, int, str]] = []
        for ann in annotations:
            label_list = ann.get("label", [])
            if not label_list:
                continue
            label = label_list[0]
            # DataTurks `end` is inclusive → convert to exclusive
            for pt in ann.get("points", []):
                s = int(pt.get("start", 0))
                e = int(pt.get("end", 0)) + 1  # inclusive→exclusive
                if e > s:
                    # Map DataTurks label to our BIO schema label
                    mapped = _map_dataturks_label(label)
                    if mapped:
                        spans.append((s, e, mapped))

        tok_offsets = ws_tokenize(text)
        if not tok_offsets:
            skipped += 1
            continue

        # Split large Skills spans into individual sub-skills at delimiters.
        # DataTurks annotators often highlight an entire "Skills:" section as one
        # span. When keep_mega_spans=False (default), we split at commas/semicolons
        # so each individual skill gets its own B-Skills entity.
        # When keep_mega_spans=True, we preserve the original mega-span format to
        # match the yashpwr/resume-ner-bert-v2 pretraining format.
        if keep_mega_spans:
            expanded_spans = spans
        else:
            expanded_spans = []
            for s, e, lbl in spans:
                if lbl == "Skills" and (e - s) > 30:
                    for sub_s, sub_e in _split_skills_span(text, s, e):
                        expanded_spans.append((sub_s, sub_e, "Skills"))
                else:
                    expanded_spans.append((s, e, lbl))

        tags = spans_to_bio(tok_offsets, expanded_spans, keep_mega_spans=keep_mega_spans)
        tokens = [t for t, _, _ in tok_offsets]

        records.append({
            "doc_id": f"dt_{line_no:04d}",
            "tokens": tokens,
            "ner_tags_str": tags,
            "source": "dataturks",
        })

    log.info("DataTurks: %d valid docs, %d skipped", len(records), skipped)
    return records


def _map_dataturks_label(raw: str) -> str | None:
    """Map DataTurks entity label to our BIO schema."""
    mapping = {
        "Skills": "Skills",
        "Designation": "Designation",
        "Name": "Name",
        "Email Address": "Email Address",
        "Email": "Email Address",
        "Phone": "Phone",
        "Location": "Location",
        "Companies worked at": "Companies worked at",
        "Companies Worked At": "Companies worked at",
        "Years of Experience": "Years of Experience",
        "Degree": "Degree",
        "College Name": "College Name",
        "Graduation Year": "Graduation Year",
        "UNKNOWN": "UNKNOWN",
    }
    return mapping.get(raw, "UNKNOWN" if raw else None)


def load_qlop_linkedin_skills(csv_path: str) -> tuple[list[str], list[str]]:
    """Load canonical skills + role labels from MASTERED_DATA_AI_DROPPED_MISSING.csv.

    Returns: (raw_skill_list, role_label_list)
    """
    df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    log.info("MASTERED_DATA: %d rows", len(df))

    # Skills: comma-separated lowercase field
    skill_counter: Counter = Counter()
    for cell in df["hard_skills"].dropna():
        for s in str(cell).split(","):
            s = s.strip().lower()
            if s:
                skill_counter[s] += 1

    # Roles
    roles = sorted(df["role_label"].dropna().str.strip().unique().tolist())
    log.info("LinkedIn: %d raw skill types, %d roles", len(skill_counter), len(roles))
    return list(skill_counter.keys()), roles


def load_coursera_skills(csv_path: str) -> list[str]:
    """Load skill phrases from coursera.csv (semicolon-separated)."""
    df = pd.read_csv(csv_path, sep=";", encoding="latin-1", low_memory=False)
    log.info("Coursera: %d rows", len(df))
    skill_cols = [c for c in df.columns if "skill" in c.lower()]
    log.info("Coursera skill columns: %s", skill_cols)
    skills: list[str] = []
    for col in skill_cols:
        for cell in df[col].dropna():
            s = str(cell).strip().lower()
            if s and s != "nan":
                skills.append(s)
    log.info("Coursera: %d raw skill instances", len(skills))
    return skills


def load_onet_examples(csv_path: str) -> list[str]:
    """Load skill/tool names from Skills_ONET.csv."""
    df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    log.info("O*NET: %d rows, columns: %s", len(df), list(df.columns))
    # QLOP O*NET file has columns: Commodity Code, Commodity Title, Example
    # 'Example' holds specific tool/product names (e.g. "Adobe Acrobat", "Git")
    # 'Commodity Title' holds broader category names — both are useful
    skills: list[str] = []
    for col in ["Example", "Commodity Title"]:
        if col in df.columns:
            skills.extend(df[col].dropna().str.strip().str.lower().unique().tolist())
    log.info("O*NET: %d skill/tool names loaded", len(skills))
    return skills


def load_jobs_silver(
    csv_path: str,
    max_docs: int = 500,
    seed: int = 42,
) -> list[dict]:
    """Build silver NER records from JOBS_WITH_EXTRACTED_SKILLS.csv.

    Strategy: parse extracted_skills list, find each skill phrase in
    translated_descriptionText via exact match (word-boundary safe),
    then annotate as B-/I-Skills. Only keeps docs where ≥1 skill is found.
    """
    df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
    df = df.dropna(subset=["translated_descriptionText", "extracted_skills"])
    log.info("JOBS silver: %d candidate rows", len(df))

    rng = random.Random(seed)
    indices = list(df.index)
    rng.shuffle(indices)

    records: list[dict] = []
    for idx in indices:
        if len(records) >= max_docs:
            break
        row = df.loc[idx]
        text = str(row["translated_descriptionText"]).strip()
        if len(text) < 50:
            continue
        try:
            raw_skills: list[str] = ast.literal_eval(str(row["extracted_skills"]))
        except (ValueError, SyntaxError):
            continue
        if not raw_skills:
            continue

        tok_offsets = ws_tokenize(text)
        if not tok_offsets:
            continue

        spans: list[tuple[int, int, str]] = []
        for skill in raw_skills:
            skill_clean = skill.strip()
            if not skill_clean or len(skill_clean) < 2:
                continue
            # case-insensitive whole-phrase search with word boundaries
            pattern = r"(?<!\w)" + re.escape(skill_clean) + r"(?!\w)"
            for m in re.finditer(pattern, text, re.IGNORECASE):
                spans.append((m.start(), m.end(), "Skills"))
                break  # one occurrence per skill is enough

        if not spans:
            continue

        tags = spans_to_bio(tok_offsets, spans, keep_mega_spans=False)
        if not any(t.startswith("B-") for t in tags):
            continue

        records.append({
            "doc_id": f"sv_{idx}",
            "tokens": [t for t, _, _ in tok_offsets],
            "ner_tags_str": tags,
            "source": "silver",
        })

    log.info("JOBS silver: %d docs produced (target %d)", len(records), max_docs)
    return records


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic CV generator (programmatic BIO annotation)
# ─────────────────────────────────────────────────────────────────────────────

_SYNTH_TEMPLATES = [
    "Skills: {skills_comma}",
    "Technical Skills: {skills_comma}",
    "Core Competencies: {skills_comma}",
    "Technologies: {skills_pipe}",
    "Proficient in {skills_and}",
    "Experienced with {skills_comma}",
    "Strong knowledge of {skills_and}",
    "Hands-on experience with {skills_comma}",
    "Key Skills: {skills_comma}",
    "Tools & Technologies: {skills_pipe}",
]

_SYNTH_CONTEXT_BEFORE = [
    "{name}\n{role}\n{company} | {location}\n\n",
    "{name}\nEmail: {email}\nPhone: +1-555-{phone}\n\n{role} at {company}\n\n",
    "{name}\n{location}\n\nProfessional Summary\n{years}+ years as {role} at {company}.\n\n",
    "{name} — {role}\n{company}, {location} ({years} years)\n\n",
]

_SYNTH_CONTEXT_AFTER = [
    "\n\nEducation\n{degree} in {field}, {university}, {grad_year}",
    "\n\nExperience\n{role} at {company} ({years} years)\n- Designed and deployed systems",
    "\n\nCertifications\nAWS Certified Solutions Architect\n{degree} - {university}",
    "",
]

_NAMES = [
    "John Smith", "Sarah Johnson", "Michael Chen", "Emily Davis", "David Kim",
    "Jessica Patel", "Robert Wilson", "Amanda Rodriguez", "James Lee", "Nicole Brown",
    "Andrew Thompson", "Maria Garcia", "Daniel Taylor", "Lisa Anderson", "Kevin Martinez",
    "Rachel Williams", "Christopher Moore", "Jennifer White", "Matthew Harris", "Ashley Clark",
]

_COMPANIES = [
    "Google", "Microsoft", "Amazon", "Apple", "Meta", "Netflix", "Uber", "Spotify",
    "Salesforce", "Adobe", "Intel", "IBM", "Oracle", "SAP", "Cisco", "VMware",
    "Shopify", "Stripe", "Square", "Palantir", "Databricks", "Snowflake",
]

_LOCATIONS = [
    "San Francisco, CA", "New York, NY", "Seattle, WA", "Austin, TX",
    "Boston, MA", "Denver, CO", "Chicago, IL", "Los Angeles, CA",
    "Portland, OR", "Atlanta, GA", "Toronto, Canada", "London, UK",
]

_DEGREES = ["B.Sc", "M.Sc", "B.Tech", "M.Tech", "B.Eng", "MBA"]
_FIELDS = [
    "Computer Science", "Software Engineering", "Information Technology",
    "Data Science", "Electrical Engineering", "Mathematics",
]
_UNIVERSITIES = [
    "Stanford University", "MIT", "UC Berkeley", "Carnegie Mellon",
    "Georgia Tech", "University of Michigan", "Cornell University",
]


def generate_synthetic_cvs(
    gazetteer_csv_path: str,
    roles: list[str],
    n_docs: int = 500,
    skills_per_doc: tuple[int, int] = (8, 18),
    seed: int = 42,
) -> list[dict]:
    """Generate template-based CV documents with programmatic BIO annotation.

    Uses the gazetteer (11K+ skill surfaces) and role labels to create realistic
    CV text with exact-match BIO annotations. Each skill token maps directly to
    B-Skills (single word) or B-Skills + I-Skills (multi-word skill).

    Returns records in the same format as load_dataturks/load_jobs_silver.
    """
    rng = random.Random(seed)

    # Load gazetteer skills (unique surfaces, >= 2 chars, <= 4 words)
    skill_pool: list[str] = []
    seen: set[str] = set()
    with open(gazetteer_csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            surface = row["surface"].strip()
            if surface.lower() in seen:
                continue
            if len(surface) < 2 or len(surface.split()) > 4:
                continue
            seen.add(surface.lower())
            skill_pool.append(surface)

    if not skill_pool:
        log.warning("Synthetic: gazetteer empty, cannot generate CVs")
        return []

    log.info("Synthetic: %d unique skills in pool", len(skill_pool))

    records: list[dict] = []
    for doc_idx in range(n_docs):
        n_skills = rng.randint(*skills_per_doc)
        chosen_skills = rng.sample(skill_pool, min(n_skills, len(skill_pool)))

        # Format skills in different list styles
        template = rng.choice(_SYNTH_TEMPLATES)
        skills_comma = ", ".join(chosen_skills)
        skills_pipe = " | ".join(chosen_skills)
        skills_and = ", ".join(chosen_skills[:-1]) + " and " + chosen_skills[-1] if len(chosen_skills) > 1 else chosen_skills[0]

        skills_line = template.format(
            skills_comma=skills_comma,
            skills_pipe=skills_pipe,
            skills_and=skills_and,
        )

        # Add context (name, company, role, etc.)
        role = rng.choice(roles)
        name = rng.choice(_NAMES)
        company = rng.choice(_COMPANIES)
        location = rng.choice(_LOCATIONS)
        years = str(rng.randint(1, 15))
        email = name.lower().replace(" ", ".") + "@email.com"
        phone = f"{rng.randint(100,999)}-{rng.randint(1000,9999)}"
        degree = rng.choice(_DEGREES)
        field = rng.choice(_FIELDS)
        university = rng.choice(_UNIVERSITIES)
        grad_year = str(rng.randint(2010, 2024))

        fmt_kwargs = dict(
            name=name, role=role, company=company, location=location,
            years=years, email=email, phone=phone, degree=degree,
            field=field, university=university, grad_year=grad_year,
        )

        before = rng.choice(_SYNTH_CONTEXT_BEFORE).format(**fmt_kwargs)
        after = rng.choice(_SYNTH_CONTEXT_AFTER).format(**fmt_kwargs)

        full_text = before + skills_line + after

        # Tokenize and annotate
        tok_offsets = ws_tokenize(full_text)
        if not tok_offsets:
            continue

        # Build spans: find each chosen skill in the text via exact match
        spans: list[tuple[int, int, str]] = []
        for skill in chosen_skills:
            pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
            for m in re.finditer(pattern, full_text):
                spans.append((m.start(), m.end(), "Skills"))
                break  # one occurrence per skill

        if not spans:
            continue

        tags = spans_to_bio(tok_offsets, spans, keep_mega_spans=False)
        if not any(t.startswith("B-") for t in tags):
            continue

        records.append({
            "doc_id": f"synth_{doc_idx:04d}",
            "tokens": [t for t, _, _ in tok_offsets],
            "ner_tags_str": tags,
            "source": "synthetic",
        })

    log.info("Synthetic: %d CV docs generated (target %d)", len(records), n_docs)
    return records


# ─────────────────────────────────────────────────────────────────────────────
# Skill vocabulary + gazetteer builders
# ─────────────────────────────────────────────────────────────────────────────

def clean_skill_token(raw: str) -> str:
    """Lowercase + strip + collapse whitespace."""
    return re.sub(r"\s+", " ", raw.strip().lower())


def apply_stop_skills(skills: list[str], extra_stops: set[str] | None = None) -> list[str]:
    stops = STOP_SKILLS | (extra_stops or set())
    return [s for s in skills if s not in stops and len(s) >= 2]


def apply_synonym_map(skills: list[str], extra_rules: dict[str, str] | None = None) -> list[str]:
    rules = {**SYNONYM_MAP, **(extra_rules or {})}
    return [rules.get(s, s) for s in skills]


def build_vocab_582(linkedin_raw: list[str]) -> list[str]:
    """Build the canonical ~582-skill LinkedIn vocabulary.

    Pipeline: clean → stop-filter → synonym-map → deduplicate → sort.
    The exact count may differ slightly from the notebook; we log the diff.
    """
    cleaned = [clean_skill_token(s) for s in linkedin_raw]
    filtered = apply_stop_skills(cleaned)
    mapped = apply_synonym_map(filtered)
    # Deduplicate preserving first occurrence order, then sort
    seen: set[str] = set()
    unique: list[str] = []
    for s in mapped:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    unique.sort()
    if abs(len(unique) - 582) > 30:
        log.warning(
            "skill_vocab size = %d (expected ~582). Check stop/synonym rules.",
            len(unique),
        )
    else:
        log.info("skill_vocab_linkedin: %d skills (target ~582)", len(unique))
    return unique


def build_gazetteer(
    linkedin: list[str],
    coursera: list[str],
    onet: list[str],
) -> list[dict]:
    """Merge skill sources into a unified gazetteer with provenance tags."""
    rows: list[dict] = []
    seen: set[str] = set()

    def _add(skills: list[str], source: str) -> None:
        for raw in skills:
            normed = clean_skill_token(raw)
            if not normed or len(normed) < 2:
                continue
            if normed in STOP_SKILLS:
                continue
            canonical = SYNONYM_MAP.get(normed, normed)
            if canonical not in seen:
                seen.add(canonical)
                rows.append({"surface": normed, "canonical": canonical, "source": source})
            else:
                # Add alias row even if canonical already present
                if normed != canonical:
                    rows.append({"surface": normed, "canonical": canonical, "source": source})

    _add(linkedin, "linkedin")
    _add(coursera, "coursera")
    _add(onet, "onet")
    log.info("Gazetteer: %d rows (%d unique canonical)", len(rows), len(seen))
    return rows


def build_role_labels(roles: list[str]) -> list[str]:
    """Return sorted unique role labels. Expects exactly 50."""
    unique = sorted(set(r.strip() for r in roles if r.strip()))
    if len(unique) != 50:
        log.warning("role_labels: got %d roles (expected 50)", len(unique))
    else:
        log.info("role_labels: %d roles", len(unique))
    return unique


# ─────────────────────────────────────────────────────────────────────────────
# Training data assembly
# ─────────────────────────────────────────────────────────────────────────────

def merge_training_records(
    dataturks: list[dict],
    silver: list[dict],
) -> list[dict]:
    """Combine DataTurks + silver records, tag each with source."""
    merged = dataturks + silver
    log.info(
        "Merged: %d dataturks + %d silver = %d total docs",
        len(dataturks), len(silver), len(merged),
    )
    return merged


def split_documents(
    records: list[dict],
    seed: int = 42,
    val_frac: float = 0.12,
    test_frac: float = 0.08,
) -> dict[str, list[str]]:
    """Document-level split (no doc_id overlap).

    DataTurks docs always go to train/val/test proportionally.
    Silver docs (if any) only go to train.
    """
    dt_ids = [r["doc_id"] for r in records if r["source"] == "dataturks"]
    sv_ids = [r["doc_id"] for r in records if r["source"] == "silver"]

    rng = random.Random(seed)
    rng.shuffle(dt_ids)

    n_val = max(1, round(len(dt_ids) * val_frac))
    n_test = max(1, round(len(dt_ids) * test_frac))
    n_train = len(dt_ids) - n_val - n_test

    train_ids = dt_ids[:n_train] + sv_ids
    val_ids = dt_ids[n_train: n_train + n_val]
    test_ids = dt_ids[n_train + n_val:]

    # Sanity check — no overlaps
    all_sets = [set(train_ids), set(val_ids), set(test_ids)]
    for i, a in enumerate(all_sets):
        for j, b in enumerate(all_sets):
            if i != j:
                overlap = a & b
                if overlap:
                    log.error("Split overlap between split %d and %d: %s", i, j, overlap)
                    sys.exit(1)

    log.info(
        "Splits: train=%d val=%d test=%d",
        len(train_ids), len(val_ids), len(test_ids),
    )
    return {"train": sorted(train_ids), "val": sorted(val_ids), "test": sorted(test_ids)}


# ─────────────────────────────────────────────────────────────────────────────
# Normalization rules output
# ─────────────────────────────────────────────────────────────────────────────

def build_normalization_rules() -> dict:
    """Export SYNONYM_MAP as the normalization_rules.json artifact."""
    return {"version": "1.0", "rules": SYNONYM_MAP}


# ─────────────────────────────────────────────────────────────────────────────
# Manifest + hashing
# ─────────────────────────────────────────────────────────────────────────────

def _md5_file(path: Path) -> str:
    h = hashlib.md5()
    h.update(path.read_bytes())
    return h.hexdigest()


def write_manifest(out_dir: Path, stats: dict) -> None:
    artifact_files = [
        "dataturks_resume_entities.jsonl",
        "ner_train.jsonl",
        "ner_splits.json",
        "qlop_skill_gazetteer.csv",
        "skill_vocab_linkedin.json",
        "role_labels.json",
        "normalization_rules.json",
        "stop_skills.txt",
    ]
    file_hashes: dict[str, str] = {}
    for fname in artifact_files:
        fpath = out_dir / fname
        if fpath.exists():
            file_hashes[fname] = _md5_file(fpath)
        else:
            file_hashes[fname] = "MISSING"

    manifest = {
        "build_timestamp": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "file_hashes": file_hashes,
        "label_schema": BIO_LABELS,
        "skill_label_ids": [LABEL2ID["B-Skills"], LABEL2ID["I-Skills"]],
    }
    (out_dir / "build_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Manifest written: build_manifest.json")


# ─────────────────────────────────────────────────────────────────────────────
# Dataset card
# ─────────────────────────────────────────────────────────────────────────────

DATASET_CARD_TEMPLATE = """# QLOP NER Dataset — kaggle_ready_dataset

Built by `build_ner_dataset.py`. Do **not** edit manually.

## Sources
| File | Source | License |
|------|--------|---------|
| `dataturks_resume_entities.jsonl` | [DataTurks Resume NER](https://dataturks.com/projects/abhishek.narayanan/Entity%20Recognition%20in%20Resumes) | CC0 / public |
| `ner_train.jsonl` | DataTurks + optional silver labels | see above |
| `qlop_skill_gazetteer.csv` | LinkedIn QLOP + Coursera + O*NET | research use |
| `skill_vocab_linkedin.json` | LinkedIn job posts (QLOP dataset) | research use |
| `role_labels.json` | LinkedIn job posts (QLOP dataset) | research use |

## Format
Each line in `*.jsonl`:
```json
{{"doc_id": "dt_0001", "tokens": ["Python", "dev"], "ner_tags_str": ["B-Skills", "O"], "source": "dataturks"}}
```

## Notebook usage
```python
import json
from pathlib import Path

BASE = Path("/kaggle/input/<your-dataset-name>")
train = [json.loads(l) for l in (BASE / "ner_train.jsonl").read_text().splitlines() if l]
splits = json.loads((BASE / "ner_splits.json").read_text())
gazetteer = ...  # pd.read_csv(BASE / "qlop_skill_gazetteer.csv")
vocab_582 = json.loads((BASE / "skill_vocab_linkedin.json").read_text())
roles = json.loads((BASE / "role_labels.json").read_text())
```

## Label schema
25 BIO labels matching `yashpwr/resume-ner-bert-v2`:
O, B-Skills, I-Skills, B-Designation, I-Designation, B-Name, I-Name,
B-Email Address, I-Email Address, B-Phone, I-Phone, B-Location, I-Location,
B-Companies worked at, I-Companies worked at, B-Years of Experience, I-Years of Experience,
B-Degree, I-Degree, B-College Name, I-College Name, B-Graduation Year, I-Graduation Year,
B-UNKNOWN, I-UNKNOWN
"""


# ─────────────────────────────────────────────────────────────────────────────
# Quality gates
# ─────────────────────────────────────────────────────────────────────────────

def quality_gates(out_dir: Path, vocab: list[str], roles: list[str], splits: dict) -> None:
    """Fail fast if any output is missing or obviously malformed."""
    required = [
        "dataturks_resume_entities.jsonl",
        "ner_train.jsonl",
        "ner_splits.json",
        "qlop_skill_gazetteer.csv",
        "skill_vocab_linkedin.json",
        "role_labels.json",
        "normalization_rules.json",
        "stop_skills.txt",
        "dataset_card.md",
        "build_manifest.json",
    ]
    missing = [f for f in required if not (out_dir / f).exists()]
    if missing:
        log.error("Quality gate FAIL — missing files: %s", missing)
        sys.exit(1)

    if not (500 <= len(vocab) <= 650):
        log.warning("skill_vocab size %d outside expected 500–650 range", len(vocab))

    if len(roles) != 50:
        log.error("Quality gate FAIL — role_labels has %d roles (expected 50)", len(roles))
        sys.exit(1)

    # No doc_id overlap across splits
    all_ids = splits["train"] + splits["val"] + splits["test"]
    if len(all_ids) != len(set(all_ids)):
        log.error("Quality gate FAIL — doc_id overlap in splits")
        sys.exit(1)

    # ner_train.jsonl parseable
    train_lines = (out_dir / "ner_train.jsonl").read_text(encoding="utf-8").splitlines()
    try:
        for line in train_lines[:5]:
            if line.strip():
                json.loads(line)
    except json.JSONDecodeError as e:
        log.error("Quality gate FAIL — ner_train.jsonl not valid JSON: %s", e)
        sys.exit(1)

    log.info("Quality gates PASSED")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main(args: argparse.Namespace) -> None:
    qlop_root = Path(args.qlop_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Fase A.1: DataTurks ────────────────────────────────────────────────
    dataturks_records: list[dict] = []
    if args.dataturks_path:
        dataturks_records = load_dataturks(
            args.dataturks_path,
            keep_mega_spans=args.keep_mega_spans,
        )
    else:
        log.warning(
            "--dataturks-path not provided. "
            "DataTurks records will be empty — NER training quality will be poor.\n"
            "Download from: https://dataturks.com/projects/abhishek.narayanan/"
            "Entity%%20Recognition%%20in%%20Resumes"
        )

    # Write dataturks_resume_entities.jsonl (DataTurks only, no silver)
    dt_path = out_dir / "dataturks_resume_entities.jsonl"
    dt_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in dataturks_records),
        encoding="utf-8",
    )
    log.info("Written: dataturks_resume_entities.jsonl (%d docs)", len(dataturks_records))

    # ── Fase A.2: LinkedIn skills + roles ─────────────────────────────────
    mastered_csv = qlop_root / "MASTERED_DATA_AI_DROPPED_MISSING.csv"
    linkedin_raw, roles = load_qlop_linkedin_skills(str(mastered_csv))

    # ── Fase A.3: Coursera skills ─────────────────────────────────────────
    coursera_csv = qlop_root / "coursera.csv"
    coursera_skills = load_coursera_skills(str(coursera_csv))

    # ── Fase A.4: O*NET gazetteer ─────────────────────────────────────────
    onet_csv = qlop_root / "Skills_ONET.csv"
    onet_skills = load_onet_examples(str(onet_csv))

    # ── Fase A.5: Silver labels (optional) ───────────────────────────────
    silver_records: list[dict] = []
    if args.silver:
        jobs_csv = qlop_root / "JOBS_WITH_EXTRACTED_SKILLS.csv"
        silver_records = load_jobs_silver(str(jobs_csv), max_docs=args.silver_max)

    # ── Fase A.5b: Synthetic CVs (optional) ──────────────────────────────
    synthetic_records: list[dict] = []
    # (deferred until after gazetteer is built in Fase A.6)

    # ── Fase A.6: Build vocabulary + gazetteer ────────────────────────────
    vocab_582 = build_vocab_582(linkedin_raw)
    gazetteer_rows = build_gazetteer(linkedin_raw, coursera_skills, onet_skills)
    role_labels = build_role_labels(roles)
    norm_rules = build_normalization_rules()

    # ── Fase A.7: Write reference artefacts ───────────────────────────────
    (out_dir / "skill_vocab_linkedin.json").write_text(
        json.dumps(vocab_582, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Written: skill_vocab_linkedin.json (%d skills)", len(vocab_582))

    # Gazetteer CSV
    gaz_df = pd.DataFrame(gazetteer_rows)
    gaz_df.to_csv(out_dir / "qlop_skill_gazetteer.csv", index=False, encoding="utf-8")
    log.info("Written: qlop_skill_gazetteer.csv (%d rows)", len(gaz_df))

    (out_dir / "role_labels.json").write_text(
        json.dumps(role_labels, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Written: role_labels.json (%d roles)", len(role_labels))

    (out_dir / "normalization_rules.json").write_text(
        json.dumps(norm_rules, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Written: normalization_rules.json")

    (out_dir / "stop_skills.txt").write_text(
        "\n".join(sorted(STOP_SKILLS)), encoding="utf-8"
    )
    log.info("Written: stop_skills.txt (%d tokens)", len(STOP_SKILLS))

    # ── Fase A.7b: Synthetic CVs (optional, needs gazetteer from A.7) ────
    if args.synthetic:
        gaz_csv = out_dir / "qlop_skill_gazetteer.csv"
        synthetic_records = generate_synthetic_cvs(
            gazetteer_csv_path=str(gaz_csv),
            roles=role_labels,
            n_docs=args.synthetic_max,
            seed=42,
        )

    # ── Fase A.8: Merge + split ───────────────────────────────────────────
    all_records = merge_training_records(dataturks_records, silver_records)
    # Synthetic docs go directly into training (not val/test) so add AFTER split
    splits = split_documents(all_records, seed=42)
    if synthetic_records:
        all_records.extend(synthetic_records)
        # All synthetic docs go into training split
        splits["train"].extend(r["doc_id"] for r in synthetic_records)
        log.info("Added %d synthetic docs to training split", len(synthetic_records))

    (out_dir / "ner_train.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in all_records),
        encoding="utf-8",
    )
    log.info("Written: ner_train.jsonl (%d docs)", len(all_records))

    (out_dir / "ner_splits.json").write_text(
        json.dumps(splits, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Written: ner_splits.json (train=%d val=%d test=%d)",
             len(splits["train"]), len(splits["val"]), len(splits["test"]))

    # ── Fase A.9: Docs ────────────────────────────────────────────────────
    (out_dir / "dataset_card.md").write_text(DATASET_CARD_TEMPLATE, encoding="utf-8")
    log.info("Written: dataset_card.md")

    # ── Fase A.10: Manifest + quality gates ──────────────────────────────
    stats = {
        "dataturks_docs": len(dataturks_records),
        "silver_docs": len(silver_records),
        "synthetic_docs": len(synthetic_records),
        "total_docs": len(all_records),
        "vocab_582_count": len(vocab_582),
        "gazetteer_rows": len(gaz_df),
        "role_count": len(role_labels),
        "split_train": len(splits["train"]),
        "split_val": len(splits["val"]),
        "split_test": len(splits["test"]),
    }
    write_manifest(out_dir, stats)
    quality_gates(out_dir, vocab_582, role_labels, splits)

    log.info("\n✓  Build complete → %s", out_dir.resolve())
    log.info("  Next step: zip kaggle_ready_dataset/ and upload to Kaggle.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build QLOP NER kaggle_ready_dataset/")
    p.add_argument(
        "--qlop-root",
        default=r"C:/Users/hp/.cache/kagglehub/datasets/husniabdillah/dataset-qlop/versions/3",
        help="Root directory of the local QLOP Kaggle dataset cache",
    )
    p.add_argument(
        "--dataturks-path",
        default=None,
        help="Path to the DataTurks 'Entity Recognition in Resumes.json' file",
    )
    p.add_argument(
        "--out-dir",
        default="ai_engine/data_pipeline/kaggle_ready_dataset",
        help="Output directory for kaggle_ready_dataset/ artefacts",
    )
    p.add_argument(
        "--silver",
        action="store_true",
        default=False,
        help="Include silver-labeled job description examples in ner_train.jsonl",
    )
    p.add_argument(
        "--silver-max",
        type=int,
        default=500,
        help="Max number of silver examples to include (default: 500)",
    )
    p.add_argument(
        "--keep-mega-spans",
        action="store_true",
        default=False,
        help=(
            "Preserve original DataTurks mega-span format: entire 'Skills:' sections "
            "become B-Skills + I-Skills chains. "
            "USE THIS FLAG to match the yashpwr/resume-ner-bert-v2 pretraining format "
            "and avoid annotation-format mismatch during fine-tuning. "
            "Default (False) splits each skill into its own B-Skills entity."
        ),
    )
    p.add_argument(
        "--synthetic",
        action="store_true",
        default=False,
        help="Generate synthetic CV documents using gazetteer skills + role templates",
    )
    p.add_argument(
        "--synthetic-max",
        type=int,
        default=500,
        help="Number of synthetic CV documents to generate (default: 500)",
    )
    return p.parse_args()


if __name__ == "__main__":
    main(parse_args())
