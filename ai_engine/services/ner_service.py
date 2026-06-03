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
        r"(?:^|\n)\s*(?:technical|key|core|professional)?\s*skills?\s*(?:&\s*competenc\w*|&\s*expertise)?[\s:]*(?:\n|$)",
        re.IGNORECASE,
    ),
    "experience": re.compile(
        r"(?:^|\n)\s*(?:work|professional|employment|job|career)?\s*experiences?\s*(?:history|record)?[\s:]*(?:\n|$)",
        re.IGNORECASE,
    ),
    "education": re.compile(
        r"(?:^|\n)\s*education(?:al)?\s*(?:level|background|history|&\s*qualif\w*)?[\s:]*(?:\n|$)",
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

_VALID_DURATION_RE = re.compile(
    r"\b(?:20[0-3]\d|19\d\d)\b|"
    r"\b(?:present|now|current|today|aktif|sekarang|tahun|bulan|years?|months?)\b",
    re.IGNORECASE
)

def _is_valid_duration(text: str) -> bool:
    s = text.strip()
    if not s:
        return False
    return bool(_VALID_DURATION_RE.search(s))


def _group_entities_by_proximity(ents: list[dict], text: str, max_dist: int = 120) -> list[dict]:
    """Group sequential entities into job/education blocks based on text proximity.
    
    A new block is started if:
    1. The distance between the current entity and the previous entity is > max_dist characters.
    2. The current entity label is already present in the current block (duplicate field).
    """
    blocks = []
    current_block = {}
    last_end = 0
    
    ents_with_pos = []
    search_start = 0
    for ent in ents:
        ent_text = ent["text"]
        pos = text.find(ent_text, search_start)
        if pos == -1:
            pos = text.find(ent_text)
        if pos != -1:
            ents_with_pos.append({
                "label": ent["label"],
                "text": ent_text,
                "start": pos,
                "end": pos + len(ent_text)
            })
            search_start = pos + len(ent_text)
        else:
            ents_with_pos.append({
                "label": ent["label"],
                "text": ent_text,
                "start": last_end + 1,
                "end": last_end + 1 + len(ent_text)
            })
            search_start = last_end + 1 + len(ent_text)
        last_end = ents_with_pos[-1]["end"]

    for i, ent in enumerate(ents_with_pos):
        label = ent["label"]
        val = ent["text"]
        
        start_new = False
        if i == 0:
            start_new = True
        else:
            prev_ent = ents_with_pos[i - 1]
            dist = ent["start"] - prev_ent["end"]
            
            key_map = {
                "Company": "company",
                "Designation": "designation",
                "YearsExperience": "duration",
                "Degree": "degree",
                "Institution": "institution"
            }
            key = key_map.get(label)
            
            if key and key in current_block:
                start_new = True
            elif dist > max_dist:
                start_new = True
                
        if start_new:
            if current_block:
                blocks.append(current_block)
            current_block = {}
            
        key_map = {
            "Company": "company",
            "Designation": "designation",
            "YearsExperience": "duration",
            "Degree": "degree",
            "Institution": "institution"
        }
        key = key_map.get(label)
        if key:
            current_block[key] = val
            
    if current_block:
        blocks.append(current_block)
        
    return blocks


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

def _expand_to_full_words(ent_text: str, full_text: str) -> str:
    ent_text = ent_text.strip()
    if not ent_text:
        return ent_text
        
    pos = full_text.find(ent_text)
    if pos == -1:
        pos = full_text.lower().find(ent_text.lower())
        if pos == -1:
            return ent_text
            
    start = pos
    while start > 0 and full_text[start - 1].isalnum() and full_text[start - 1] not in "\n\r\t ":
        start -= 1
        
    end = pos + len(ent_text)
    while end < len(full_text) and full_text[end].isalnum() and full_text[end] not in "\n\r\t ":
        end += 1
        
    expanded = full_text[start:end].strip()
    if len(expanded) > len(ent_text) + 15:
        return ent_text
    return expanded


def extract_with_ner(raw_text: str, sections: dict[str, str]) -> dict:
    """Run full NER pipeline on text (section-aware)."""
    output: dict = {
        "name": "", "email": "", "phone": "", "location": "",
        "total_experience_years": 0.0,
        "skills": [],
        "work_experience": [], "education": [],
    }

    # 1. Name, Email, Phone, Location (run on header or first 15 lines)
    header_text = "\n".join(raw_text.split("\n")[:15])
    header_ents = _sliding_window_ner(header_text)
    for ent in header_ents:
        label, text = ent["label"], ent["text"].strip()
        if label == "Name" and not output["name"]:
            if len(text) >= 3 and not text.startswith(("http", "www")):
                if text.lower() not in _NAME_BLOCKLIST:
                    output["name"] = text
        elif label == "Location" and not output["location"]:
            if len(text) >= 3 and text.lower() not in _INVALID_LOCATION_WORDS:
                output["location"] = text

    # Expand DeBERTa location to full words if it is a fragment
    if output["location"]:
        output["location"] = _expand_to_full_words(output["location"], raw_text)

    # Location priority/fallback: unconditionally check first 5 lines (header) for a location regex match.
    # The header location (home address) always overrides any location from the body/experience section.
    header_lines = raw_text.split("\n")[:5]
    for line in header_lines:
        line = line.strip()
        loc_match = _LOCATION_RE.search(line)
        if loc_match:
            city = loc_match.group(1).strip()
            if city.lower() not in _NAME_BLOCKLIST:
                output["location"] = line
                break

    # Name fallback: regex on the first 10 lines
    if not output["name"] or len(output["name"].split()) < 2:
        header_lines = raw_text.split("\n")[:10]
        for line in header_lines:
            line = line.strip()
            if _NAME_RE.match(line) and len(line.split()) >= 2:
                if line.lower() not in _NAME_BLOCKLIST:
                    output["name"] = line
                    break

    # Email & Phone fallback (regex always wins)
    email_match = _EMAIL_RE.search(raw_text)
    if email_match:
        output["email"] = email_match.group(0)

    phone_match = _PHONE_RE.search(raw_text)
    if phone_match:
        candidate = phone_match.group(0).strip()
        if len(re.sub(r"\D", "", candidate)) >= 7:
            output["phone"] = candidate

    # 2. Skills (run on the skills section or the full text)
    skills_text = sections.get("skills", raw_text)
    skills_ents = _sliding_window_ner(skills_text)
    skills_seen = set()
    for ent in skills_ents:
        if ent["label"] == "Skill" and _is_valid_skill(ent["text"]):
            normalized, _ = _normalize_skill(ent["text"])
            key = normalized.lower()
            if key not in skills_seen:
                skills_seen.add(key)
                output["skills"].append(normalized)

    # 3. Work Experience (run ONLY on experience section if found)
    exp_text = sections.get("experience", "")
    if exp_text:
        exp_ents = _sliding_window_ner(exp_text)
    else:
        exp_text = raw_text
        exp_ents = _sliding_window_ner(raw_text)

    relevant_exp_ents = []
    for ent in exp_ents:
        label, text = ent["label"], ent["text"].strip()
        if label == "Company" and _is_valid_company(text):
            relevant_exp_ents.append(ent)
        elif label == "Designation" and len(text) >= 3:
            if text.lower() not in {"work", "job", "per", "member", "staff", "him"}:
                relevant_exp_ents.append(ent)
        elif label == "YearsExperience" and len(text) >= 3:
            if _is_valid_duration(text):
                relevant_exp_ents.append(ent)

    grouped_jobs = _group_entities_by_proximity(relevant_exp_ents, exp_text, max_dist=120)
    ner_jobs = []
    for job in grouped_jobs:
        company = job.get("company", "").strip()
        designation = job.get("designation", "").strip()
        duration = job.get("duration", "").strip()
        if company or designation:
            ner_jobs.append({
                "company": company,
                "designation": designation,
                "duration": duration
            })

    regex_jobs = _extract_experience_via_regex(exp_text)
    final_jobs = []
    for r_job in regex_jobs:
        matched_idx = -1
        for idx, n_job in enumerate(ner_jobs):
            r_dur = r_job["duration"].lower()
            n_dur = n_job["duration"].lower()
            r_co = r_job["company"].lower()
            n_co = n_job["company"].lower()
            
            dur_match = (r_dur in n_dur or n_dur in r_dur or (r_dur and n_dur and any(yr in n_dur for yr in re.findall(r"\b\d{4}\b", r_dur))))
            co_match = (r_co and n_co and (r_co in n_co or n_co in r_co))
            
            if dur_match or co_match:
                matched_idx = idx
                break
                
        if matched_idx != -1:
            n_job = ner_jobs.pop(matched_idx)
            merged_company = r_job["company"] if len(r_job["company"]) >= len(n_job["company"]) else n_job["company"]
            merged_designation = r_job["designation"] if len(r_job["designation"]) >= len(n_job["designation"]) else n_job["designation"]
            merged_duration = r_job["duration"] if len(r_job["duration"]) >= len(n_job["duration"]) else n_job["duration"]
            
            final_jobs.append({
                "company": merged_company,
                "designation": merged_designation,
                "duration": merged_duration
            })
        else:
            final_jobs.append(r_job)
            
    for n_job in ner_jobs:
        if not n_job["designation"] and len(n_job["company"]) < 8:
            continue
        final_jobs.append(n_job)
        
    cleaned_jobs = []
    for job in final_jobs:
        co = job["company"].strip()
        de = job["designation"].strip()
        du = job["duration"].strip()
        
        co = re.sub(r"^[-*•\s]+", "", co).strip(" ,.-")
        de = re.sub(r"^[-*•\s]+", "", de).strip(" ,.-")
        
        if not co and not de:
            continue
        if not de and not du:
            continue
        if co.lower() in _COMPANY_BLOCKLIST or de.lower() in {"work", "job", "per", "member", "staff", "him"}:
            continue
            
        cleaned_jobs.append({
            "company": co,
            "designation": de,
            "duration": du
        })
        
    output["work_experience"] = cleaned_jobs

    # 4. Education (run ONLY on education section if found)
    edu_text = sections.get("education", "")
    if edu_text:
        edu_ents = _sliding_window_ner(edu_text)
    else:
        edu_ents = _sliding_window_ner(raw_text)

    degrees = []
    institutions = []
    for ent in edu_ents:
        label, text = ent["label"], ent["text"].strip()
        if label == "Degree":
            words = text.split()
            if len(words) >= 2 or (len(text) >= 3 and text[:2].upper() in {"S1", "S2", "S3", "D3", "D4"}):
                degrees.append(text)
        elif label == "Institution" and len(text) >= 3:
            institutions.append(text)

    ner_edu = []
    for i in range(max(len(degrees), len(institutions))):
        deg = degrees[i] if i < len(degrees) else ""
        inst = institutions[i] if i < len(institutions) else ""
        if deg or inst:
            ner_edu.append({
                "degree": deg,
                "institution": inst,
                "year": ""
            })

    regex_edu = _extract_education_via_regex(edu_text if edu_text else raw_text)
    final_edu = []
    for r_ed in regex_edu:
        matched_idx = -1
        for idx, n_ed in enumerate(ner_edu):
            r_inst = r_ed["institution"].lower()
            n_inst = n_ed["institution"].lower()
            
            if r_inst and n_inst and (r_inst in n_inst or n_inst in r_inst):
                matched_idx = idx
                break
                
        if matched_idx != -1:
            n_ed = ner_edu.pop(matched_idx)
            merged_degree = r_ed["degree"] if len(r_ed["degree"]) >= len(n_ed["degree"]) else n_ed["degree"]
            merged_inst = r_ed["institution"] if len(r_ed["institution"]) >= len(n_ed["institution"]) else n_ed["institution"]
            merged_year = r_ed["year"] if r_ed["year"] else n_ed["year"]
            
            final_edu.append({
                "degree": merged_degree,
                "institution": merged_inst,
                "year": merged_year
            })
        else:
            final_edu.append(r_ed)
            
    for n_ed in ner_edu:
        inst = n_ed["institution"].strip()
        deg = n_ed["degree"].strip()
        
        has_univ_keyword = any(kw in inst.lower() for kw in ["university", "universitas", "institut", "institute", "college", "school", "politeknik", "academy", "sma", "smk"])
        if has_univ_keyword or (deg and len(inst) >= 5):
            final_edu.append(n_ed)
            
    cleaned_edu = []
    for ed in final_edu:
        inst = ed["institution"].strip(" ,.-")
        deg = ed["degree"].strip(" ,.-")
        yr = ed["year"].strip(" ,.-")
        
        if not inst and not deg:
            continue
            
        cleaned_edu.append({
            "degree": deg,
            "institution": inst,
            "year": yr
        })
        
    output["education"] = cleaned_edu

    output["total_experience_years"] = _extract_experience_years_from_text(raw_text)
    return output


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

# Reject common section headers from name extraction
_NAME_BLOCKLIST = {
    "education level", "education", "work experience", "work experiences",
    "technical skills", "skills", "experience", "contact", "summary",
    "about me", "projects", "certifications", "languages", "language",
    "coursework", "awards", "honors", "activities", "publications", "interests"
}

# Regex to match location candidates (e.g. City, Country or City, Province) in the header
_LOCATION_RE = re.compile(
    r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})\s*,\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})\b"
)

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
    # location false positives
    "jawa barat", "jawa", "barat", "sumatera", "utara", "sumatera utara", "indonesia", "bogor", "jakarta", "bandung", "surabaya", "medan",
    # institution/competition false positives
    "mage", "its", "ipb", "university", "universitas", "institut", "pertanian", "institut pertanian bogor", "ipb university", "proton catalyst", "proton", "catalyst", "career development", "assessment",
    # other noise
    "fr", "competition", "functionality", "multimedia", "game event", "event", "category",
    "student", "sixth-semester", "semester", "extensive", "new features", "system", "enhancements", "applications",
    "expected", "present", "tutor", "programmer", "developer", "intern", "junior programmer"
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
    # Reject if length is 2 and not in known 2-char skills list
    if len(s) == 2 and s.lower() not in {"go", "c", "r", "js", "ts", "ip", "ui", "ux", "qt", "db"}:
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

def _extract_experience_via_regex(text: str) -> list[dict]:
    # Split text into lines
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    jobs = []
    
    # 1. Find all line indices that contain a date range
    date_indices = []
    for idx, line in enumerate(lines):
        if _DATE_RANGE_RE.search(line) or _is_valid_duration(line):
            # Make sure it's a date range, not just a random number
            if any(month in line.lower() for month in ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec", "present", "now", "current"]):
                date_indices.append(idx)
            elif re.search(r"\b\d{4}\s*[-–]\s*(?:\d{4}|present|now)\b", line, re.IGNORECASE):
                date_indices.append(idx)

    # 2. For each date line, extract company and designation from context
    for idx in date_indices:
        duration = lines[idx]
        company = ""
        designation = ""
        
        # Look above the date line
        if idx > 0:
            prev_line = lines[idx - 1]
            if " - " in prev_line or " – " in prev_line:
                parts = re.split(r"\s*[-–]\s*", prev_line, maxsplit=1)
                company = parts[0].strip()
                # The rest of the line is location, e.g., "Bogor, Indonesia"
            else:
                # If there's no dash, check if the line is short (designation) or long (company/desc)
                # Or check if line i-2 has dash
                if idx > 1 and (" - " in lines[idx - 2] or " – " in lines[idx - 2]):
                    parts = re.split(r"\s*[-–]\s*", lines[idx - 2], maxsplit=1)
                    company = parts[0].strip()
                    designation = prev_line
                else:
                    company = prev_line
                    
        # Look below the date line for designation if not found yet
        if not designation and idx < len(lines) - 1:
            next_line = lines[idx + 1]
            # Designation should be relatively short (not a bullet point or description)
            if len(next_line.split()) <= 5 and not next_line.startswith(("-", "*", "•")):
                designation = next_line
                
        # Clean up company name if it contains location details or section names
        if company:
            company = re.split(r"\s*[-–]\s*", company)[0].strip()
            company = re.sub(r"^[-*•\s]+", "", company)
            
        if designation:
            designation = re.sub(r"^[-*•\s]+", "", designation)

        # Validate that we have at least company or designation
        if company or designation:
            jobs.append({
                "company": company,
                "designation": designation,
                "duration": duration
            })
            
    return jobs


def _extract_education_via_regex(text: str) -> list[dict]:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    edu_list = []
    
    inst_keywords = ["university", "universitas", "institut", "institute", "college", "school", "politeknik", "academy", "sma", "smk"]
    degree_keywords = ["computer science", "information systems", "bachelor", "diploma", "master", "s1", "d3", "d4", "s2", "s3", "undergraduate", "graduate", "major", "studying", "student"]
    
    for idx, line in enumerate(lines):
        line_lower = line.lower()
        # Check if this line is an institution
        if any(keyword in line_lower for keyword in inst_keywords):
            # Clean institution name (e.g. split by dash if it contains location)
            inst_name = line
            if " - " in line or " – " in line:
                inst_name = re.split(r"\s*[-–]\s*", line)[0].strip()
            
            # Look for degree and year in surrounding lines (e.g. up to 3 lines below)
            degree = ""
            year = ""
            
            for offset in range(1, 4):
                if idx + offset < len(lines):
                    next_line = lines[idx + offset]
                    next_line_lower = next_line.lower()
                    
                    # If we hit another institution, stop looking
                    if any(keyword in next_line_lower for keyword in inst_keywords) and offset > 1:
                        break
                        
                    # Check for year
                    years = [int(y) for y in re.findall(r"\b(20[0-3]\d|19\d\d)\b", next_line)]
                    if years and not year:
                        year = str(max(years))
                        
                    # Check for degree keywords
                    if any(keyword in next_line_lower for keyword in degree_keywords) and not degree:
                        deg_candidate = next_line
                        if "," in next_line:
                            deg_candidate = next_line.split(",")[0].strip()
                        degree = deg_candidate
            
            # If no degree found below, check line above
            if not degree and idx > 0:
                prev_line = lines[idx - 1]
                if any(keyword in prev_line.lower() for keyword in degree_keywords):
                    degree = prev_line
                    
            # Extract year from the institution line itself if present
            if not year:
                years = [int(y) for y in re.findall(r"\b(20[0-3]\d|19\d\d)\b", line)]
                if years:
                    year = str(max(years))
                    
            edu_list.append({
                "institution": inst_name,
                "degree": degree,
                "year": year
            })
            
    return edu_list


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
# LLM-based CV parsing
# ──────────────────────────────────────────────────────────────────────

def extract_with_llm(raw_text: str) -> dict | None:
    """Extract profile using LLM (Gemini with Groq fallback)."""
    import openai
    import json
    from json_repair import repair_json
    from core.config import settings

    use_gemini = (settings.llm_provider == "gemini")
    client = None
    model = ""
    max_tokens = 2048

    if use_gemini:
        try:
            import google.auth
            import google.auth.transport.requests
            
            credentials, project_id = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            gcp_project = settings.vertex_project_id or project_id
            if not gcp_project:
                raise ValueError("Could not determine Google Cloud project ID.")
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)
            
            region = settings.vertex_region
            client = openai.OpenAI(
                api_key=credentials.token,
                base_url=f"https://{region}-aiplatform.googleapis.com/v1/projects/{gcp_project}/locations/{region}/endpoints/openapi",
            )
            model = settings.gemini_model
            if not model.startswith("google/"):
                model = f"google/{model}"
        except Exception as exc:
            logger.warning("Gemini initialization failed for CV extraction: %s. Falling back to Groq...", exc)
            use_gemini = False

    if not use_gemini:
        if not settings.groq_api_key:
            logger.warning("No Groq API key configured for fallback.")
            return None
        try:
            client = openai.OpenAI(
                api_key=settings.groq_api_key,
                base_url=settings.groq_base_url,
            )
            model = settings.groq_model
            max_tokens = settings.groq_max_tokens
        except Exception as exc:
            logger.warning("Groq initialization failed for CV extraction: %s", exc)
            return None

    if not client:
        return None

    system_instruction = (
        "You are an expert ATS (Applicant Tracking System) parser. "
        "Your task is to extract profile information from the raw CV text and format it strictly as JSON. "
        "Do not invent any information. "
        "Strictly filter out academic competitions, hackathons, medals (Gold/Silver/Bronze), "
        "high school level groups, and student organizations from work_experience. Only include actual professional jobs, roles, or internships. "
        "Ensure dates are clean and names are correct."
    )

    schema_format = {
        "name": "Full Name",
        "email": "email@example.com",
        "phone": "+6281...",
        "location": "City, Country",
        "total_experience_years": 4.5,
        "skills": ["Skill1", "Skill2"],
        "work_experience": [
            {
                "company": "Company Name",
                "designation": "Job Title / Role",
                "duration": "Duration / Date Range (e.g. Feb 2026 - Present)"
            }
        ],
        "education": [
            {
                "degree": "Degree (e.g. Bachelor of Computer Science)",
                "institution": "University / Institution Name",
                "year": "Graduation Year (e.g. 2027)"
            }
        ]
    }

    prompt = (
        f"Extract the candidate's profile from the following CV text:\n\n"
        f"--- START CV TEXT ---\n{raw_text}\n--- END CV TEXT ---\n\n"
        f"Return the profile as a JSON object matching this schema:\n"
        f"{json.dumps(schema_format, indent=2)}\n\n"
        f"Rules:\n"
        f"1. Only return the JSON object, do not wrap in markdown or backticks.\n"
        f"2. Exclude student organizations (e.g., Himpunan, Him, BEM), school clubs, high school levels, hackathons, competitions (like Multimedia and Game Event), and medals (like Gold/Silver/Bronze) from work_experience. Only actual internships or jobs should go in work_experience.\n"
        f"3. Make sure to extract actual skills."
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        
        try:
            parsed = json.loads(content)
        except Exception:
            repaired = repair_json(content, return_objects=False, ensure_ascii=False)
            parsed = json.loads(repaired)
        return parsed
    except Exception as exc:
        logger.error("LLM CV extraction execution failed: %s", exc)
        return None


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

    result = None
    mode = "unknown"
    
    # 1. Primary Model: custom DeBERTa NER
    if registry.ner_available:
        logger.info("Attempting NER-based CV extraction using: deberta")
        try:
            result = extract_with_ner(raw_text, sections)
            mode = "ner_deberta"
            logger.info("NER-based CV extraction succeeded.")
        except Exception as exc:
            logger.warning("NER-based CV extraction failed: %s. Falling back...", exc)

    # 2. Secondary/Fallback Model: LLM
    if not result and settings.llm_provider:
        logger.info("Attempting LLM-based CV extraction fallback using: %s", settings.llm_provider)
        try:
            result = extract_with_llm(raw_text)
            if result:
                mode = f"llm_{settings.llm_provider}_fallback"
                logger.info("LLM-based CV extraction fallback succeeded.")
        except Exception as exc:
            logger.warning("LLM-based CV extraction fallback failed: %s. Falling back to heuristic...", exc)

    # 3. Tertiary/Heuristic Fallback
    if not result:
        logger.info("Attempting heuristic fallback CV extraction.")
        result = extract_with_heuristic(raw_text)
        mode = "heuristic_fallback"

    profile = CVProfile(
        name=result.get("name", "") or "",
        email=result.get("email", "") or "",
        phone=result.get("phone", "") or "",
        location=result.get("location", "") or "",
        total_experience_years=float(result.get("total_experience_years", 0.0) or 0.0),
        skills=result.get("skills", []) or [],
        work_experience=[WorkExperience(**we) for we in result.get("work_experience", []) if we] if result.get("work_experience") else [],
        education=[Education(**ed) for ed in result.get("education", []) if ed] if result.get("education") else [],
    )

    meta = {
        "page_count": pages,
        "extraction_mode": mode,
        "ner_model_version": "llm" if "llm" in mode else ("qlop_ner_v2" if mode == "ner_deberta" else "heuristic"),
    }
    return profile, meta
