"""
Post-process existing ner_train.jsonl to fix entity spillage in Skills spans.

Problem: DataTurks annotators highlighted entire "Skills sections" as one entity.
This creates Skills spans of 50-350 tokens including commas, parentheses, and
experience info like "(Less than 1 year)".

Fix: Split long Skills spans at punctuation boundaries so each individual skill
gets its own B-Skills tag. Punctuation between skills becomes O.
"""
import json, re, sys, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# Tokens that must be O between skills
BOUNDARY_TOKENS = re.compile(
    r"^[,;/|&+:•·\-–—❖◦~*▪►■□●○→←↑↓★☆]+$"  # pure punctuation/bullets
    r"|^\($|^\)$"                                # standalone parens
    r"|^(?:and|or|AND|OR)$"                      # conjunctions
    r"|^https?://"                                # URLs
    r"|^www\."                                    # URLs
)

# Noise tokens inside skill spans (experience info, numbers+years, section headers, URLs)
NOISE_TOKEN = re.compile(
    r"^\d+\+?$"                      # bare numbers ("5", "10+")
    r"|^(?:Less|than|year|years|yr|yrs|month|months|mo|mos|experience|exp)$"
    r"|^ADDITIONAL$|^INFORMATION$|^TECHNICAL$|^SKILLS$"
    r"|^Technical$|^skills:?$|^Languages:?$|^Frameworks:?$|^Tools:?$"
    r"|^(?:proficiency|proficient|knowledge|familiar|expertise)$"
    r"|^(?:Environment|Operating|Database|Reporting|Tracking|Ticket)$"
    r"|^(?:Tool|Application|Servers|IDE|Web|Development|Language|Framework)$"
    r"|^(?:in|of|on|for|with|the|a|an|to|at|by)$"   # prepositions/articles
    r"|^(?:nature|Hardworking|Dedicated|towards|work|Efficient|Individual|Highly)$"
    r"|^https?://"
    r"|^www\."
    , re.IGNORECASE
)

# Token contains punctuation that signals a boundary (e.g., "Java," or "(Less" or "year)")
CONTAINS_PAREN = re.compile(r"[()]")


def is_boundary_or_noise(tok: str) -> bool:
    """Return True if this token should be O (not part of any skill)."""
    if BOUNDARY_TOKENS.match(tok):
        return True
    tok_clean = tok.strip(",.;:/()|&+*~")
    if not tok_clean or len(tok_clean) < 2:
        return True
    if NOISE_TOKEN.match(tok_clean):
        return True
    if CONTAINS_PAREN.search(tok) and NOISE_TOKEN.match(tok_clean):
        return True
    return False


def is_delimiter_suffix(tok: str) -> bool:
    """Token ends with a delimiter — tag as skill but break after."""
    return len(tok) > 1 and tok[-1] in (",", ";", "/", "|", ":")


def fix_skills_tags(tokens: list[str], tags: list[str]) -> list[str]:
    """Fix a single record's tags: split Skills spans at boundaries.

    Strategy: any Skills span > 4 tokens is suspicious. Re-scan it and:
    - Pure punctuation/noise tokens -> O
    - Tokens with trailing comma -> tag as skill but start new entity after
    - Otherwise -> continue current entity or start new one
    """
    new_tags = tags.copy()
    n = len(tokens)
    i = 0
    while i < n:
        if new_tags[i] not in ("B-Skills", "I-Skills"):
            i += 1
            continue
        span_start = i
        span_end = i + 1
        while span_end < n and new_tags[span_end] in ("B-Skills", "I-Skills"):
            span_end += 1

        # Short spans (1-4 tokens) are likely correct single skills
        if span_end - span_start <= 4:
            i = span_end
            continue

        # Re-tag the span
        in_entity = False
        for j in range(span_start, span_end):
            tok = tokens[j]
            if is_boundary_or_noise(tok):
                new_tags[j] = "O"
                in_entity = False
            elif is_delimiter_suffix(tok):
                # "Python," -> tag as B/I-Skills then break
                tok_clean = tok.rstrip(",.;:/|")
                if len(tok_clean) >= 2:
                    new_tags[j] = "B-Skills" if not in_entity else "I-Skills"
                else:
                    new_tags[j] = "O"
                in_entity = False
            else:
                if not in_entity:
                    new_tags[j] = "B-Skills"
                    in_entity = True
                else:
                    new_tags[j] = "I-Skills"

        i = span_end
    return new_tags


def main():
    base = Path("ai_engine/data_pipeline/kaggle_ready_dataset")
    jsonl_path = base / "ner_train.jsonl"

    records = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"Loaded {len(records)} records from {jsonl_path}")

    # Stats before
    def span_stats(recs):
        spans = []
        for r in recs:
            length = 0
            for t in r["ner_tags_str"]:
                if t in ("B-Skills", "I-Skills"):
                    length += 1
                elif length > 0:
                    spans.append(length)
                    length = 0
            if length > 0:
                spans.append(length)
        return spans

    before = span_stats(records)
    print(f"BEFORE: {len(before)} spans, mean={sum(before)/max(len(before),1):.1f}, "
          f"max={max(before) if before else 0}, >10tok={sum(1 for s in before if s > 10)}")

    # Apply fix
    for r in records:
        r["ner_tags_str"] = fix_skills_tags(r["tokens"], r["ner_tags_str"])

    after = span_stats(records)
    print(f"AFTER:  {len(after)} spans, mean={sum(after)/max(len(after),1):.1f}, "
          f"max={max(after) if after else 0}, >10tok={sum(1 for s in after if s > 10)}")

    # Backup and write
    backup = jsonl_path.with_suffix(".jsonl.bak")
    shutil.copy2(jsonl_path, backup)
    print(f"Backup saved: {backup}")

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Fixed dataset written: {jsonl_path}")

    # Also fix dataturks_resume_entities.jsonl
    dt_path = base / "dataturks_resume_entities.jsonl"
    if dt_path.exists():
        dt_records = []
        with open(dt_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    dt_records.append(json.loads(line))
        for r in dt_records:
            r["ner_tags_str"] = fix_skills_tags(r["tokens"], r["ner_tags_str"])
        shutil.copy2(dt_path, dt_path.with_suffix(".jsonl.bak"))
        with open(dt_path, "w", encoding="utf-8") as f:
            for r in dt_records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"Also fixed: {dt_path}")

    # Show sample fixed spans
    print("\n--- Sample fixed spans (first 10 multi-token) ---")
    shown = 0
    for r in records[:100]:
        tokens = r["tokens"]
        tags = r["ner_tags_str"]
        in_skill = False
        span_toks = []
        for j in range(len(tags)):
            if tags[j] in ("B-Skills", "I-Skills"):
                span_toks.append(f"{tokens[j]}({tags[j][:1]})")
                in_skill = True
            elif in_skill:
                if len(span_toks) >= 2:
                    print(f"  [{r['doc_id']}] {' '.join(span_toks[:15])}")
                    shown += 1
                span_toks = []
                in_skill = False
            if shown >= 10:
                break
        if shown >= 10:
            break


if __name__ == "__main__":
    main()
