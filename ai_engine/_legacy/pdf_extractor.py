from __future__ import annotations

import re
from pathlib import Path

import fitz

from schemas.cv_schema import CvProcessResponse, PersonalInformation, TextBlockGroup

PERSONAL_ALIASES = {
    "personal information",
    "personal info",
    "profile",
    "summary",
    "professional summary",
    "about me",
    "objective",
    "contact",
    "contact information",
}

WORK_ALIASES = {
    "work experience",
    "professional experience",
    "employment history",
    "career history",
    "work history",
    "experience",
    "work experiences",
    "professional experiences",
}

EDUCATION_ALIASES = {
    "education",
    "academic history",
    "academic background",
    "qualifications",
    "training",
    "education level",
    "education & qualifications",
    "education and training",
}

SKILLS_ALIASES = {
    "skills",
    "technical skills",
    "core competencies",
    "competencies",
    "expertise",
}

NEUTRAL_BOUNDARY_ALIASES = {
    "achievements",
    "accomplishments",
    "projects",
    "project work",
    "organizational experience",
    "organisational experience",
    "volunteer experience",
    "extracurricular activities",
    "activities",
    "awards",
    "honors",
    "honours",
    "publications",
    "certifications",
    "leadership",
    "community involvement",
    "interests",
    "hobbies",
    "achievements & awards",
}

KNOWN_SKILLS = {
    "agile",
    "airflow",
    "angular",
    "aws",
    "azure",
    "blender",
    "bootstrap",
    "c#",
    "c++",
    "ci/cd",
    "communication",
    "critical thinking",
    "css",
    "data analysis",
    "data science",
    "django",
    "docker",
    "fastapi",
    "flask",
    "git",
    "github",
    "graphql",
    "html",
    "javascript",
    "kubernetes",
    "leadership",
    "linux",
    "machine learning",
    "mysql",
    "nlp",
    "node.js",
    "numpy",
    "pandas",
    "postgresql",
    "problem solving",
    "project management",
    "public speaking",
    "pytorch",
    "python",
    "react",
    "rest",
    "research",
    "scikit-learn",
    "scrum",
    "sql",
    "teamwork",
    "tensorflow",
    "testing",
    "typescript",
    "vue",
    "adaptability",
}

STOP_SKILL_TOKENS = {
    "and",
    "or",
    "with",
    "rest",
    "span",
    "spanning",
    "etc",
    "including",
}

EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4,6})")
DATE_RE = re.compile(
    r"\b(?:19|20)\d{2}\b|\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
    re.I,
)
HEADER_RE = re.compile(r"^[A-Z][A-Z0-9 &/.,'()-]{2,}$")
NUMERIC_ONLY_RE = re.compile(r"^\d+(?:[.,]\d+)?(?:/\d+(?:[.,]\d+)?)?%?$")
GRADE_RE = re.compile(r"\b(?:gpa|cgpa|grade|grades|percentage|percent|score|marks?)\b", re.I)
DATE_TOKEN_RE = re.compile(r"^(?:19|20)\d{2}$|^\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?$")
COMMON_PREFIXES = {
    "cv",
    "resume",
    "resumé",
    "curriculum",
    "vitae",
    "profile",
    "candidate",
    "final",
    "draft",
    "updated",
    "latest",
}

NAME_BLACKLIST_WORDS = {
    "education",
    "student",
    "university",
    "college",
    "institute",
    "school",
    "cv",
    "resume",
    "profile",
    "objective",
    "experience",
    "work",
    "intern",
    "internship",
}


def normalize_whitespace(text: str) -> str:
    return re.sub(r"[\s\u00a0]+", " ", text.replace("\r", " ")).strip()


def split_block_lines(block_text: str) -> list[str]:
    lines = [normalize_whitespace(line) for line in block_text.split("\n")]
    return [line for line in lines if line]


def clean_block_text(block_text: str) -> str:
    lines = split_block_lines(block_text)
    return "\n".join(lines)


def expand_blocks_to_lines(blocks: list[str]) -> list[str]:
    lines: list[str] = []
    for block in blocks:
        lines.extend(split_block_lines(block))
    return lines


def is_name_candidate(text: str) -> bool:
    candidate = normalize_whitespace(text).strip(" :,-")
    if not candidate or EMAIL_RE.search(candidate) or PHONE_RE.search(candidate) or DATE_RE.search(candidate):
        return False
    lower = candidate.lower()
    # reject obvious header/section lines as potential names
    if any(word in lower for word in NAME_BLACKLIST_WORDS):
        return False
    words = [word for word in re.split(r"\s+", candidate) if word]
    if not 2 <= len(words) <= 5:
        return False
    if not all(re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", word) for word in words):
        return False
    capitalized_words = sum(1 for word in words if word[:1].isupper())
    return capitalized_words >= max(2, len(words) - 1)


def classify_header_line(text: str, *, allow_generic_boundary: bool = True) -> str | None:
    normalized = normalize_whitespace(text).lower().strip(" :.-")
    if not normalized:
        return None
    # direct matches
    if any(alias == normalized for alias in PERSONAL_ALIASES):
        return "personal"
    if any(alias == normalized for alias in SKILLS_ALIASES):
        return "skills"

    # keyword-based detection for work (prefer short header-like lines)
    if (re.search(r"\b(work|professional|employment|career)\b", normalized) and re.search(r"\b(experience|experiences|history)\b", normalized)) or any(alias == normalized for alias in WORK_ALIASES):
        if len(normalized.split()) <= 5 or any(alias == normalized for alias in WORK_ALIASES):
            return "work"

    # education detection (prefer short header-like lines)
    if re.search(r"\b(education|academic|qualification|degree|training|school|university)\b", normalized) or any(alias == normalized for alias in EDUCATION_ALIASES):
        if len(normalized.split()) <= 5 or any(alias == normalized for alias in EDUCATION_ALIASES):
            return "education"

    # neutral boundaries and projects/achievements
    if any(alias == normalized for alias in NEUTRAL_BOUNDARY_ALIASES) or re.search(r"\b(projects?|achievements?|awards?|honors?|certifications?)\b", normalized):
        return "misc"

    # fallback to generic header pattern
    if allow_generic_boundary and HEADER_RE.match(normalize_whitespace(text)) and len(normalized.split()) <= 6:
        return "misc"

    return None


def extract_layout_blocks(file_bytes: bytes) -> tuple[list[str], int]:
    if not file_bytes.startswith(b"%PDF"):
        raise ValueError("Only PDF files are accepted.")

    try:
        document = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:  # pragma: no cover - defensive guard for malformed PDFs
        raise ValueError("The uploaded file could not be opened as a PDF.") from exc

    try:
        ordered_blocks: list[str] = []
        for page_index in range(len(document)):
            page = document[page_index]
            sortable_blocks: list[tuple[int, float, float, str]] = []
            for block in page.get_text("blocks"):
                if len(block) < 5:
                    continue
                x0, y0 = float(block[0]), float(block[1])
                block_text = clean_block_text(str(block[4]))
                if block_text:
                    sortable_blocks.append((page_index, y0, x0, block_text))
            sortable_blocks.sort(key=lambda item: (item[0], item[1], item[2]))
            ordered_blocks.extend(block_text for _, _, _, block_text in sortable_blocks)

        if not ordered_blocks:
            raise ValueError("No extractable text was found in the PDF.")

        return ordered_blocks, len(document)
    finally:
        document.close()


def extract_name_from_blocks(blocks: list[str]) -> str | None:
    for block in blocks[:5]:
        for line in split_block_lines(block)[:6]:
            if is_name_candidate(line):
                words = [word.capitalize() for word in normalize_whitespace(line).split()]
                return " ".join(words)
    return None


def extract_name_from_filename(filename: str | None) -> str | None:
    if not filename:
        return None

    stem = Path(filename).stem
    stem = re.sub(r"(?i)^(?:cv|resume|resum[eé]|curriculum(?:[\s_-]*vitae)?)[:\s_-]*", "", stem)
    stem = stem.replace("_", " ").replace("-", " ")
    stem = re.sub(r"(?i)\b(?:final|draft|updated|latest|candidate|profile)\b", " ", stem)
    stem = re.sub(r"\b(?:19|20)\d{2}\b", " ", stem)
    stem = re.sub(r"\b\d+(?:[.,]\d+)?(?:/\d+(?:[.,]\d+)?)?\b", " ", stem)
    stem = re.sub(r"[^A-Za-z\s'.]", " ", stem)

    tokens = [token for token in re.split(r"\s+", stem) if token]
    tokens = [token for token in tokens if token.lower() not in COMMON_PREFIXES]
    if len(tokens) < 2:
        return None

    selected_tokens: list[str] = []
    for token in tokens:
        if len(selected_tokens) == 4:
            break
        if len(token) == 1:
            continue
        selected_tokens.append(token.capitalize())

    if len(selected_tokens) < 2:
        return None

    return " ".join(selected_tokens)


def extract_email_and_phone(blocks: list[str]) -> tuple[str | None, str | None]:
    email: str | None = None
    phone: str | None = None

    for block in blocks:
        for line in split_block_lines(block):
            if not email:
                email_match = EMAIL_RE.search(line)
                if email_match:
                    email = email_match.group(0)
            if not phone:
                phone_match = PHONE_RE.search(line)
                if phone_match:
                    phone = normalize_whitespace(phone_match.group(0))
            if email and phone:
                return email, phone

    return email, phone


def looks_like_summary_text(text: str) -> bool:
    candidate = normalize_whitespace(text)
    if len(candidate.split()) < 8:
        return False
    if EMAIL_RE.search(candidate) or PHONE_RE.search(candidate) or DATE_RE.search(candidate):
        return False
    if classify_header_line(candidate, allow_generic_boundary=False):
        return False
    return True


def extract_summary(blocks: list[str]) -> str | None:
    for block in blocks[:8]:
        lines = split_block_lines(block)
        if not lines:
            continue
        header = classify_header_line(lines[0], allow_generic_boundary=not is_name_candidate(lines[0]))
        if header == "personal" and len(lines) > 1:
            candidate = " ".join(lines[1:])
            if looks_like_summary_text(candidate):
                return candidate
            continue
        if header in {"work", "education", "skills"}:
            break
        if header == "misc":
            continue
        candidate = " ".join(lines)
        if looks_like_summary_text(candidate):
            return candidate
    return None


def extract_skill_candidates(text: str) -> list[str]:
    lowered = text.lower()
    candidates: list[str] = []

    for skill in sorted(KNOWN_SKILLS, key=len, reverse=True):
        if skill in lowered:
            candidates.append(skill)

    for token in re.split(r"[\n,;|/•*\-]+", text):
        candidate = normalize_whitespace(token).strip(" .,:;()[]{}")
        if not candidate:
            continue
        lower_candidate = candidate.lower()
        if lower_candidate in KNOWN_SKILLS:
            candidates.append(lower_candidate)
            continue
        if re.fullmatch(r"[A-Z0-9+#.-]{2,12}", candidate) and candidate.lower() not in COMMON_PREFIXES:
            candidates.append(candidate.lower())

    return candidates


def sanitize_skills(skills: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()

    for skill in skills:
        candidate = normalize_whitespace(skill).strip(" .,:;()[]{}")
        if not candidate:
            continue
        lowered = candidate.lower()
        if lowered in seen:
            continue
        if lowered in STOP_SKILL_TOKENS:
            continue
        if NUMERIC_ONLY_RE.match(candidate):
            continue
        if DATE_TOKEN_RE.match(candidate):
            continue
        if GRADE_RE.search(candidate):
            continue
        if DATE_RE.search(candidate):
            continue
        if re.fullmatch(r"\d+(?:[.,]\d+)?", candidate):
            continue
        if re.fullmatch(r"\d+(?:[.,]\d+)?/\d+(?:[.,]\d+)?", candidate):
            continue
        if re.fullmatch(r"\d+(?:[.,]\d+)?%", candidate):
            continue
        if lowered in {"gpa", "cgpa", "grade", "grades", "percentage", "percent", "score", "marks"}:
            continue
        seen.add(lowered)
        cleaned.append(candidate)

    return cleaned


def block_contains_contact_only(block: str) -> bool:
    lines = split_block_lines(block)
    if not lines:
        return True
    content_lines = [line for line in lines if not EMAIL_RE.search(line) and not PHONE_RE.search(line) and not is_name_candidate(line)]
    return not content_lines


def block_looks_like_work(block: str) -> bool:
    lowered = block.lower()
    work_markers = [
        "work experience",
        "professional experience",
        "employment history",
        "career history",
        "responsible for",
        "managed",
        "developed",
        "implemented",
        "built",
        "deployed",
        "software engineer",
        "developer",
        "analyst",
        "consultant",
        "engineer",
        "intern",
        "tutor",
        "programmer",
        "manager",
        "director",
    ]
    # require either explicit job title markers, or date together with a job marker
    has_job_marker = any(marker in lowered for marker in work_markers)
    has_date = bool(DATE_RE.search(block))
    return has_job_marker or (has_date and has_job_marker)


def block_looks_like_education(block: str) -> bool:
    lowered = block.lower()
    education_markers = [
        "education",
        "academic",
        "university",
        "college",
        "school",
        "bachelor",
        "master",
        "mba",
        "phd",
        "degree",
        "diploma",
        "certificate",
        "graduation",
        "gpa",
        "cgpa",
    ]
    return any(marker in lowered for marker in education_markers)


def is_contact_line(line: str, personal_name: str | None) -> bool:
    candidate = normalize_whitespace(line)
    if not candidate:
        return True
    if EMAIL_RE.search(candidate) or PHONE_RE.search(candidate):
        return True
    if personal_name and candidate.lower() == normalize_whitespace(personal_name).lower():
        return True
    return False


def classify_cv_blocks(blocks: list[str], filename: str | None, page_count: int) -> CvProcessResponse:
    personal = PersonalInformation()
    work_blocks: list[str] = []
    education_blocks: list[str] = []
    misc_blocks: list[str] = []
    skills: list[str] = []
    current_section: str | None = None
    personal_buffer: list[str] = []
    work_buffer: list[str] = []
    education_buffer: list[str] = []
    misc_buffer: list[str] = []

    email, phone = extract_email_and_phone(blocks)
    personal.email = email
    personal.phone = phone
    personal.name = extract_name_from_blocks(blocks) or extract_name_from_filename(filename)
    personal.summary = extract_summary(blocks)

    def flush_buffer(section: str) -> None:
        nonlocal work_buffer, education_buffer, misc_buffer
        if section == "work" and work_buffer:
            work_blocks.append("\n".join(work_buffer).strip())
            work_buffer = []
        elif section == "education" and education_buffer:
            education_blocks.append("\n".join(education_buffer).strip())
            education_buffer = []
        elif section == "misc" and misc_buffer:
            misc_blocks.append("\n".join(misc_buffer).strip())
            misc_buffer = []

    def append_to_active_buffer(section: str, line: str) -> None:
        nonlocal work_buffer, education_buffer, misc_buffer, skills
        if section == "work":
            work_buffer.append(line)
            skills.extend(extract_skill_candidates(line))
        elif section == "education":
            education_buffer.append(line)
            skills.extend(extract_skill_candidates(line))
        elif section == "misc":
            misc_buffer.append(line)
            skills.extend(extract_skill_candidates(line))

    lines = expand_blocks_to_lines(blocks)
    for idx, line in enumerate(lines):
        next_line = lines[idx + 1] if idx + 1 < len(lines) else None
        header_section = classify_header_line(line, allow_generic_boundary=not is_name_candidate(line))
        if header_section:
            if current_section in {"work", "education", "misc"}:
                flush_buffer(current_section)
            if current_section == "personal" and personal_buffer and not personal.summary:
                candidate_summary = " ".join(personal_buffer).strip()
                if looks_like_summary_text(candidate_summary):
                    personal.summary = candidate_summary
            current_section = header_section
            personal_buffer = []
            continue

        if is_contact_line(line, personal.name):
            continue

        if current_section == "personal":
            personal_buffer.append(line)
            if not personal.summary:
                candidate_summary = " ".join(personal_buffer).strip()
                if looks_like_summary_text(candidate_summary):
                    personal.summary = candidate_summary
            continue

        if current_section in {"work", "education", "misc"}:
            # detect cross-over: an education section that actually contains work entries
            if current_section == "education" and block_looks_like_work(line):
                flush_buffer("education")
                current_section = "work"
                work_buffer.append(line)
                skills.extend(extract_skill_candidates(line))
                continue

            # detect cross-over: a work section that actually contains education entries
            if current_section == "work" and block_looks_like_education(line):
                # if the next line looks like a job/date, assume this is still a work entry
                if next_line and (block_looks_like_work(next_line) or re.search(r"\b(intern|engineer|developer|programmer|tutor|consultant|manager|director|assistant)\b", next_line.lower()) or DATE_RE.search(next_line)):
                    work_buffer.append(line)
                    skills.extend(extract_skill_candidates(line))
                    continue
                flush_buffer("work")
                current_section = "education"
                education_buffer.append(line)
                skills.extend(extract_skill_candidates(line))
                continue

            append_to_active_buffer(current_section, line)
            continue

        if current_section == "skills":
            skills.extend(extract_skill_candidates(line))
            continue

        if block_looks_like_work(line):
            current_section = "work"
            work_buffer.append(line)
            skills.extend(extract_skill_candidates(line))
            continue

        if block_looks_like_education(line):
            # lookahead: treat organization lines (e.g., containing 'university') as work
            # if the next line looks like a job title or contains a date
            if next_line and (block_looks_like_work(next_line) or re.search(r"\b(intern|engineer|developer|programmer|tutor|consultant|manager|director|assistant)\b", next_line.lower()) or DATE_RE.search(next_line)):
                current_section = "work"
                work_buffer.append(line)
                skills.extend(extract_skill_candidates(line))
                continue

            current_section = "education"
            education_buffer.append(line)
            skills.extend(extract_skill_candidates(line))
            continue

        if not personal.summary and looks_like_summary_text(line):
            personal.summary = line

        current_section = "misc"
        misc_buffer.append(line)
        skills.extend(extract_skill_candidates(line))

    if current_section in {"work", "education", "misc"}:
        flush_buffer(current_section)

    if personal_buffer and not personal.summary:
        candidate_summary = " ".join(personal_buffer).strip()
        if looks_like_summary_text(candidate_summary):
            personal.summary = candidate_summary

    return CvProcessResponse(
        filename=filename or "uploaded.pdf",
        page_count=page_count,
        personal_information=personal,
        work_experience=TextBlockGroup(raw_text_blocks=work_blocks),
        education=TextBlockGroup(raw_text_blocks=education_blocks),
        skills=sanitize_skills(skills),
        miscellaneous=TextBlockGroup(raw_text_blocks=misc_blocks),
    )


def process_pdf_cv(file_bytes: bytes, filename: str | None = None) -> CvProcessResponse:
    blocks, page_count = extract_layout_blocks(file_bytes)
    return classify_cv_blocks(blocks, filename, page_count)
