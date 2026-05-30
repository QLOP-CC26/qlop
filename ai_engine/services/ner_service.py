"""NER CV Extraction Service.

Downloads a PDF from a Cloudinary URL, extracts text, then runs the DeBERTa
NER model (or heuristic fallback) to produce a structured CVProfile.
"""

from __future__ import annotations

import logging
import re
from difflib import get_close_matches

import httpx
import numpy as np

from core.config import settings
from core.model_loader import registry
from schemas.cv_profile import CVProfile, Education, WorkExperience
from utils.skill_normalizer import SKILL_ALIASES

logger = logging.getLogger("qlop.ner_service")


# ──────────────────────────────────────────────────────────────────────
# Cloudinary download
# ──────────────────────────────────────────────────────────────────────

async def download_pdf_from_cloudinary(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type and not url.lower().endswith(".pdf"):
            raise ValueError("URL did not return a valid PDF file.")
        return response.content


# ──────────────────────────────────────────────────────────────────────
# PDF text extraction (PyMuPDF)
# ──────────────────────────────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> dict:
    """Extract raw text + sections from a PDF using PyMuPDF."""
    import fitz

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = len(doc)
    raw_blocks: list[str] = []

    for page_idx in range(pages):
        page = doc[page_idx]
        blocks = page.get_text("blocks")
        sorted_blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
        for block in sorted_blocks:
            if len(block) >= 5:
                text = str(block[4]).strip()
                if text:
                    raw_blocks.append(text)
    doc.close()

    raw_text = "\n".join(raw_blocks)
    sections = _detect_sections(raw_text)
    return {"raw_text": raw_text, "sections": sections, "pages": pages}


_SECTION_PATTERNS = {
    "skills": re.compile(
        r"(?:^|\n)\s*(?:technical\s+)?skills?\s*(?:&\s*competenc\w*)?[\s:]*\n",
        re.IGNORECASE,
    ),
    "experience": re.compile(
        r"(?:^|\n)\s*(?:work|professional|employment)?\s*experiences?\s*(?:history)?[\s:]*\n",
        re.IGNORECASE,
    ),
    "education": re.compile(
        r"(?:^|\n)\s*education\s*(?:&\s*qualif\w*|background)?[\s:]*\n",
        re.IGNORECASE,
    ),
}


def _detect_sections(text: str) -> dict[str, str]:
    """Best-effort section splitting. Returns dict with keys like 'skills'."""
    positions: list[tuple[int, str]] = []
    for name, pattern in _SECTION_PATTERNS.items():
        m = pattern.search(text)
        if m:
            positions.append((m.end(), name))
    positions.sort()

    sections: dict[str, str] = {}
    for i, (start, name) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        sections[name] = text[start:end].strip()
    return sections


# ──────────────────────────────────────────────────────────────────────
# NER span decoder (ported from notebook cell 14)
# ──────────────────────────────────────────────────────────────────────

def decode_predictions_to_spans(
    logits: np.ndarray,
    input_ids: np.ndarray,
    original_text: str,
    confidence_threshold: float,
) -> list[dict]:
    import tensorflow as tf

    tokenizer = registry.tokenizer
    id2label = registry.ner_id2label

    if tokenizer is None:
        return []

    probs = tf.nn.softmax(logits, axis=-1).numpy()
    preds = np.argmax(probs, axis=-1)
    confidences = np.max(probs, axis=-1)
    tokens = tokenizer.convert_ids_to_tokens(input_ids)

    spans: list[dict] = []
    current_entity: str | None = None
    current_tokens: list[str] = []
    current_conf: list[float] = []

    for token, pred_id, conf in zip(tokens, preds, confidences):
        if token in tokenizer.all_special_tokens:
            continue
        label = id2label.get(int(pred_id), "O")

        if label.startswith("B-"):
            if current_entity and current_tokens:
                entity_text = tokenizer.convert_tokens_to_string(current_tokens).strip()
                avg_conf = float(np.mean(current_conf))
                if avg_conf >= confidence_threshold and entity_text:
                    spans.append({"text": entity_text, "label": current_entity, "confidence": round(avg_conf, 4)})
            current_entity = label[2:]
            current_tokens = [token]
            current_conf = [conf]
        elif label.startswith("I-") and current_entity == label[2:]:
            current_tokens.append(token)
            current_conf.append(conf)
        else:
            if current_entity and current_tokens:
                entity_text = tokenizer.convert_tokens_to_string(current_tokens).strip()
                avg_conf = float(np.mean(current_conf))
                if avg_conf >= confidence_threshold and entity_text:
                    spans.append({"text": entity_text, "label": current_entity, "confidence": round(avg_conf, 4)})
            current_entity = None
            current_tokens = []
            current_conf = []

    if current_entity and current_tokens:
        entity_text = tokenizer.convert_tokens_to_string(current_tokens).strip()
        avg_conf = float(np.mean(current_conf))
        if avg_conf >= confidence_threshold and entity_text:
            spans.append({"text": entity_text, "label": current_entity, "confidence": round(avg_conf, 4)})

    return spans


# ──────────────────────────────────────────────────────────────────────
# NER-based extraction (ported from notebook cell 19 — ITSkillExtractor)
# ──────────────────────────────────────────────────────────────────────

def _run_ner_on_chunk(text: str) -> list[dict]:
    if not text.strip():
        return []

    if registry.tokenizer is None:
        raise RuntimeError("Tokenizer is not initialized")
    if registry.ner_model is None:
        raise RuntimeError("NER model is not initialized")

    encoded = registry.tokenizer(
        text,
        truncation=True,
        padding="max_length",
        max_length=settings.ner_max_length,
        return_tensors="tf",
    )
    inputs = {
        "input_ids": encoded["input_ids"],
        "attention_mask": encoded["attention_mask"],
    }
    logits = registry.ner_model(inputs, training=False)

    if hasattr(logits, "logits"):
        logits_np = logits.logits.numpy()[0]
    else:
        logits_np = logits.numpy()[0]

    return decode_predictions_to_spans(
        logits_np,
        encoded["input_ids"].numpy()[0],
        text,
        settings.ner_confidence_threshold,
    )


def _sliding_window_ner(text: str) -> list[dict]:
    words = text.split()
    window = settings.ner_sliding_window_size
    stride = settings.ner_sliding_window_stride

    if len(words) <= window:
        return _run_ner_on_chunk(text)

    seen: dict[tuple[str, str], dict] = {}
    for start in range(0, len(words), stride):
        end = min(start + window, len(words))
        chunk = " ".join(words[start:end])
        for ent in _run_ner_on_chunk(chunk):
            key = (ent["text"].lower(), ent["label"])
            if key not in seen or ent["confidence"] > seen[key]["confidence"]:
                seen[key] = ent
        if end >= len(words):
            break
    return list(seen.values())


def _normalize_skill(skill_text: str) -> tuple[str, str]:
    skill_lower = skill_text.lower().strip()

    if skill_lower in registry.skill_lookup:
        normalized = SKILL_ALIASES.get(skill_lower, skill_text.strip())
        return normalized, registry.skill_lookup[skill_lower]

    if skill_lower in SKILL_ALIASES:
        normalized = SKILL_ALIASES[skill_lower]
        return normalized, registry.skill_lookup.get(normalized.lower(), "other_tools")

    matches = get_close_matches(skill_lower, list(registry.skill_lookup.keys()), n=1, cutoff=0.8)
    if matches:
        return matches[0].title(), registry.skill_lookup[matches[0]]

    return skill_text.strip(), "other_tools"


# Common word fragments, location words, and generic terms that the NER
# mis-tags as Company entities (especially from sliding-window boundaries).
_COMPANY_BLOCKLIST: frozenset[str] = frozenset({
    # short fragments
    "full", "id", "be", "pb", "men", "port", "per", "edu", "bog",
    "anian", "camp", "the", "and", "of", "in", "at", "to", "for", "by",
    # cities / country words
    "remote", "bogor", "jakarta", "bandung", "surabaya", "indonesia",
    # job roles (mis-tagged when no company is present)
    "backend", "frontend", "mobile", "web", "cloud", "data", "intern",
    "staff", "engineer", "developer", "manager", "officer",
    # language names that bleed from the Languages section
    "english", "indonesian", "japanese", "mandarin", "chinese",
    # CV section / training cohort fragments
    "multi", "cohort", "competency", "relevant", "about",
    # standalone institution-type words that are fragments of full names
    "institut", "university", "institute", "college", "academy",
    "foundation", 
})


def _is_valid_company(text: str) -> bool:
    """Reject obvious NER fragments, single-char abbreviations, and generic words."""
    s = text.strip()
    if not s or len(s) < 3:
        return False
    if not re.search(r"[a-zA-Z]", s):
        return False
    # Fragments produced by sliding-window boundaries start with lowercase
    if not s[0].isupper():
        return False
    words = s.split()
    if len(words) == 1:
        # Allow known-valid 3-char all-caps abbreviations (e.g. "IPB", "DBS")
        if s.isupper() and len(s) >= 3:
            return s.lower() not in _COMPANY_BLOCKLIST
        # Single-word companies must have at least 5 chars (e.g. "Tokopedia")
        if len(s) < 5:
            return False
        if s.lower() in _COMPANY_BLOCKLIST:
            return False
    return True


def _structure_output(entities: list[dict], raw_text: str) -> dict:
    output: dict = {
        "name": "", "email": "", "phone": "", "location": "",
        "total_experience_years": 0.0,
        "skills": [],
        "work_experience": [], "education": [],
    }

    companies: list[str] = []
    designations: list[str] = []
    degrees: list[str] = []
    institutions: list[str] = []
    duration_texts: list[str] = []
    skills_seen: set[str] = set()

    for ent in entities:
        label, text, _ = ent["label"], ent["text"].strip(), ent["confidence"]

        if label == "Name" and not output["name"]:
            if len(text) >= 3 and not text.startswith(("http", "www")):
                output["name"] = text
        elif label == "Location" and not output["location"]:
            # Reject language names, proficiency levels, and section headers
            # mis-tagged as Location (e.g. "Indonesian", "Relevant")
            if len(text) >= 3 and text.lower() not in _INVALID_LOCATION_WORDS:
                output["location"] = text
        elif label == "Company":
            if _is_valid_company(text):
                companies.append(text)
        elif label == "Designation":
            if len(text) >= 3:
                designations.append(text)
        elif label == "YearsExperience":
            duration_texts.append(text)
        elif label == "Degree":
            # Require ≥2 words OR a known degree abbreviation (e.g. "S1", "B.Sc.")
            # Single generic words like "Multi", "Camp", "Full" are training fragments.
            words_in_degree = text.split()
            if len(words_in_degree) >= 2 or (len(text) >= 3 and text[:2].upper() in {
                "S1", "S2", "S3", "D3", "D4",
            }):
                degrees.append(text)
        elif label == "Institution":
            if len(text) >= 3:
                institutions.append(text)
        elif label == "Skill":
            if _is_valid_skill(text):
                normalized, _ = _normalize_skill(text)
                key = normalized.lower()
                if key not in skills_seen:
                    skills_seen.add(key)
                    output["skills"].append(normalized)

    # ── Name: if NER returned a single token, try regex on the first 10 lines ──
    # The DeBERTa model sometimes captures only the first token of a multi-word name
    # capitalized multi-word name in the document header.
    if not output["name"] or len(output["name"].split()) < 2:
        header_lines = raw_text.split("\n")[:10]
        for line in header_lines:
            line = line.strip()
            if _NAME_RE.match(line) and len(line.split()) >= 2:
                output["name"] = line
                break

    # ── Email & Phone: regex always wins (NER tags these unreliably) ──
    email_match = _EMAIL_RE.search(raw_text)
    if email_match:
        output["email"] = email_match.group(0)

    phone_match = _PHONE_RE.search(raw_text)
    if phone_match:
        candidate = phone_match.group(0).strip()
        # Must have at least 7 digits to be a real phone number
        if len(re.sub(r"\D", "", candidate)) >= 7:
            output["phone"] = candidate

    # ── Work experience: pair companies with designations positionally ──
    for i in range(max(len(companies), len(designations))):
        output["work_experience"].append({
            "company": companies[i] if i < len(companies) else "",
            "designation": designations[i] if i < len(designations) else "",
            "duration": duration_texts[i] if i < len(duration_texts) else "",
        })

    # Post-process: remove duplicate work entries and discard entries where
    # the company has no designation AND is very short (leftover NER fragments).
    seen_work: set[tuple[str, str]] = set()
    clean_work: list[dict] = []
    for entry in output["work_experience"]:
        company = entry["company"].strip()
        designation = entry["designation"].strip()
        if not designation and len(company) < 6:
            continue  # likely a fragment like "Camp", "Port", "ID"
        key = (company.lower(), designation.lower())
        if key not in seen_work:
            seen_work.add(key)
            clean_work.append(entry)
    output["work_experience"] = clean_work

    # ── Education ──
    for i in range(max(len(degrees), len(institutions))):
        output["education"].append({
            "degree": degrees[i] if i < len(degrees) else "",
            "institution": institutions[i] if i < len(institutions) else "",
            "year": "",
        })

    # ── total_experience_years: never use raw year numbers ──
    output["total_experience_years"] = _extract_experience_years_from_text(raw_text)

    return output


def extract_with_ner(raw_text: str, sections: dict[str, str]) -> dict:
    """Run full NER pipeline on text (section-aware + full-doc merge)."""
    # Accumulate entities from section pass first, then full-doc pass.
    # Deduplicate by (label, text.lower()), keeping the highest-confidence instance.
    seen: dict[tuple[str, str], dict] = {}

    if "skills" in sections:
        for ent in _sliding_window_ner(sections["skills"]):
            key = (ent["label"], ent["text"].lower())
            if key not in seen or ent["confidence"] > seen[key]["confidence"]:
                seen[key] = ent

    for ent in _sliding_window_ner(raw_text):
        key = (ent["label"], ent["text"].lower())
        if key not in seen or ent["confidence"] > seen[key]["confidence"]:
            seen[key] = ent

    return _structure_output(list(seen.values()), raw_text)


# ──────────────────────────────────────────────────────────────────────
# Heuristic fallback (simplified from existing pdf_extractor.py)
# ──────────────────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
_PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4,6}")
_DATE_RANGE_RE = re.compile(
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"(?:uary|ruary|ch|ril|e|y|ust|tember|ober|ember)?"
    r"\s+(\d{4})\s*[-–]\s*"
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"(?:uary|ruary|ch|ril|e|y|ust|tember|ober|ember)?"
    r"\s+(\d{4})|(?:Now|Present|Current))",
    re.IGNORECASE,
)
_NAME_RE = re.compile(r"^[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3}$")

# Words that should never be accepted as a Location entity.
# Covers language names mis-tagged from the "Languages:" section,
# proficiency levels, and common CV section headers the NER confuses with locations.
_INVALID_LOCATION_WORDS: frozenset[str] = frozenset({
    # language names / nationality adjectives
    "indonesian", "english", "japanese", "mandarin", "chinese", "korean",
    "arabic", "french", "german", "spanish", "portuguese", "malay",
    "javanese", "sundanese",
    # proficiency levels
    "native", "fluent", "moderate", "basic", "intermediate", "advanced", "bilingual",
    # CV section headers / adjectives that bleed into location fields
    "relevant", "courses", "certifications", "certification", "training",
    "education", "skills", "experience", "about", "summary", "profile",
    "contact", "references", "technical",
})

_KNOWN_SKILLS = {
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
    "react", "angular", "vue", "django", "flask", "fastapi", "node.js",
    "docker", "kubernetes", "aws", "azure", "gcp", "git", "linux",
    "sql", "mysql", "postgresql", "mongodb", "redis",
    "tensorflow", "pytorch", "pandas", "numpy", "scikit-learn",
    "html", "css", "bootstrap", "tailwind",
}

# Words / phrases that the NER frequently mis-tags as skills but are clearly not.
# Keys are lowercased full strings (exact match on skill_text.lower()).
_SKILL_BLOCKLIST: frozenset[str] = frozenset({
    # language / proficiency words
    "english", "indonesian", "moderate", "native", "fluent",
    "basic", "intermediate", "advanced",
    # URL/contact fragments
    "www", "gmail", "linkedin", "github", "http", "https", "com", "id", "io",
    # CV section headers
    "certifications", "certification", "training", "education", "experience",
    "about", "profile", "summary", "contact", "references",
    # generic/too-broad terms
    "programming", "data", "structures", "software", "cloud",
    "databases", "algorithms", "debugging", "distribution", "modern", "rule",
    # activity / role words (not skills)
    "lecturers", "teaching", "assistants", "teaching assistants",
    "response collection", "programming courses", "coding camp",
    "academic", "deployment",
    # NER fragment noise
    "al", "linked", "full", "replica", "ssl",
    "backup", "incremental", "differential", "replication",
    # redundant compound phrases (the base skill is already extracted)
    "scala programming", "basic programming", "core programming",
    "modern web development", "replica database", "disaster recovery",
    # other common false positives from Indonesian CV text
    "proffesion", "profession", "web applications",
})

# A skill token must pass all these checks
def _is_valid_skill(text: str) -> bool:
    s = text.strip()
    if not s:
        return False
    # Must contain at least one letter
    if not re.search(r"[a-zA-Z]", s):
        return False
    # Reject single chars (even uppercase)
    if len(s) <= 1:
        return False
    # Reject overly long phrases (>30 chars) — these are usually descriptions,
    # not skill names (e.g. "modern web development through academic projects")
    if len(s) > 30:
        return False
    # Reject trailing open brackets/quotes (e.g. "English (")
    if re.search(r"[({[\<\"']$", s):
        return False
    # Reject trailing closing chars that indicate a fragment (e.g. "C/", "differential)")
    if re.search(r"[/)\]>}]$", s):
        return False
    # Reject if >40% non-alphanumeric
    alnum_ratio = sum(c.isalnum() or c in "-+#./_ " for c in s) / len(s)
    if alnum_ratio < 0.6:
        return False
    # Reject if in blocklist (exact lowercase match)
    if s.lower() in _SKILL_BLOCKLIST:
        return False
    # Reject if looks like an email fragment or URL fragment
    if re.match(r"^[\w.+-]+@|^https?://|^www\.", s, re.IGNORECASE):
        return False
    return True


def _extract_experience_years_from_text(raw_text: str) -> float:
    """
    Two-stage experience extraction:
    1. Explicit pattern: 'X years', 'X tahun', 'X+ years'
    2. Fallback: compute from the earliest - latest date range in the text
    """
    explicit = re.findall(r"(\d+\.?\d*)\s*\+?\s*(?:years?|tahun)", raw_text, re.IGNORECASE)
    if explicit:
        candidates = [float(v) for v in explicit if float(v) < 50]
        if candidates:
            return max(candidates)

    # Parse all 4-digit years in the range 2000-2039 from the raw text
    years_found = [int(y) for y in re.findall(r"\b(20[0-3]\d)\b", raw_text)]
    if len(years_found) >= 2:
        import datetime
        current_year = datetime.datetime.now().year
        earliest = min(years_found)
        delta = current_year - earliest
        if 0 < delta <= 40:
            return round(delta * 0.8, 1)  # conservative estimate (80% of range)

    return 0.0


def extract_with_heuristic(raw_text: str) -> dict:
    """Fallback extraction using regex + keyword matching."""
    output: dict = {
        "name": "", "email": "", "phone": "", "location": "",
        "total_experience_years": 0.0,
        "skills": [],
        "work_experience": [], "education": [],
    }

    email_match = _EMAIL_RE.search(raw_text)
    if email_match:
        output["email"] = email_match.group(0)

    phone_match = _PHONE_RE.search(raw_text)
    if phone_match:
        output["phone"] = phone_match.group(0).strip()

    lines = raw_text.split("\n")
    for line in lines[:6]:
        line = line.strip()
        if _NAME_RE.match(line):
            output["name"] = line
            break

    text_lower = raw_text.lower()
    output["skills"] = [skill for skill in _KNOWN_SKILLS if skill in text_lower]

    return output


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────

def extract_cv(file_bytes: bytes) -> tuple[CVProfile, dict]:
    """
    Main entry point: PDF bytes → (CVProfile, extraction_meta).
    Returns the profile and metadata dict with extraction_mode, page_count, etc.
    """
    pdf_data = extract_text_from_pdf(file_bytes)
    raw_text = pdf_data["raw_text"]
    sections = pdf_data["sections"]
    pages = pdf_data["pages"]

    if not raw_text.strip():
        raise ValueError("No text could be extracted from the PDF.")

    if registry.ner_available:
        result = extract_with_ner(raw_text, sections)
        mode = "ner_deberta"
    else:
        result = extract_with_heuristic(raw_text)
        mode = "heuristic_fallback"

    profile = CVProfile(
        name=result.get("name", ""),
        email=result.get("email", ""),
        phone=result.get("phone", ""),
        location=result.get("location", ""),
        total_experience_years=result.get("total_experience_years", 0.0),
        skills=result.get("skills", []),
        work_experience=[WorkExperience(**we) for we in result.get("work_experience", [])],
        education=[Education(**ed) for ed in result.get("education", [])],
    )

    meta = {
        "page_count": pages,
        "extraction_mode": mode,
        "ner_model_version": "qlop_ner_v2" if mode == "ner_deberta" else "heuristic",
    }
    return profile, meta
