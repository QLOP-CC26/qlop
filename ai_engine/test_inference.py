"""
Jalankan dari folder ai_engine/:
    python test_inference.py

Script ini memverifikasi:
1. Vocab consistency (MD5 + spot check)
2. Inference Skill Gap Priority Scorer
3. Inference Two-Tower Course Model
Tanpa menyentuh FastAPI / registry sama sekali.
"""

from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf
from difflib import get_close_matches

# ── Paths (sesuai config.py) ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent  # ai_engine/
DATA_DIR  = BASE_DIR / "model_assets" / "recommendation"
MODEL3_DIR = DATA_DIR / "skill_priority_scorer_savedmodel"
MODEL4_DIR = DATA_DIR / "two_tower_course_model_savedmodel"

# ── Test role & skills ────────────────────────────────────────────────────────
TEST_ROLE   = "Business Intelligence Analyst"
TEST_SKILLS = ["python", "tableau", "r", "bigquery", "snowflake"]

# Nilai MD5 ini diisi dari output sel Kaggle kamu
EXPECTED_MD5_LI = ""   # contoh: "a1b2c3d4e5f6..."
EXPECTED_MD5_CR = ""   # contoh: "f6e5d4c3b2a1..."

# ─────────────────────────────────────────────────────────────────────────────

def md5_file(path: Path) -> str:
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def fuzzy_match(skill: str, vocab_keys: list[str], threshold: float = 0.75) -> str | None:
    matches = get_close_matches(skill, vocab_keys, n=1, cutoff=threshold)
    return matches[0] if matches else None


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


# ── 1. Vocab verification ─────────────────────────────────────────────────────
section("1. VOCAB VERIFICATION")

vocab_li_path = DATA_DIR / "skill_vocab_linkedin.json"
vocab_cr_path = DATA_DIR / "skill_vocab_coursera.json"

for label, path, expected_md5 in [
    ("LinkedIn vocab", vocab_li_path, EXPECTED_MD5_LI),
    ("Coursera vocab", vocab_cr_path, EXPECTED_MD5_CR),
]:
    actual_md5 = md5_file(path)
    status = ""
    if expected_md5:
        match = actual_md5 == expected_md5
        status = "✅ MATCH" if match else "❌ MISMATCH — vocab beda dari Kaggle!"
    else:
        status = "(skip — isi EXPECTED_MD5_* dulu dari Kaggle)"
    print(f"{label}: {actual_md5}  {status}")

with open(vocab_li_path, "r") as f:
    vocab_li = json.load(f)
skill_to_idx_li: dict[str, int] = vocab_li["skill_to_idx"]
idx_to_skill_li: dict[str, str] = vocab_li["idx_to_skill"]
N_SKILLS_LI: int = vocab_li["vocab_size"]

with open(vocab_cr_path, "r") as f:
    vocab_cr = json.load(f)
skill_to_idx_cr: dict[str, int] = vocab_cr["skill_to_idx"]
idx_to_skill_cr: dict[str, str] = vocab_cr["idx_to_skill"]
N_SKILLS_CR: int = vocab_cr["vocab_size"]

print(f"\nN_SKILLS_LI : {N_SKILLS_LI}")
print(f"N_SKILLS_CR : {N_SKILLS_CR}")
print(f"idx_to_skill_li['0'] : {idx_to_skill_li['0']}")
print(f"idx_to_skill_li['1'] : {idx_to_skill_li['1']}")
print(f"'python' index       : {skill_to_idx_li.get('python', 'NOT FOUND')}")
print(f"'microsoft excel' idx: {skill_to_idx_li.get('microsoft excel', 'NOT FOUND')}")
print(f"'tableau' index      : {skill_to_idx_li.get('tableau', 'NOT FOUND')}")

# ── 2. Load models ─────────────────────────────────────────────────────────────
section("2. LOAD MODELS")

if not (MODEL3_DIR / "saved_model.pb").exists():
    print(f"❌ saved_model.pb tidak ada di {MODEL3_DIR}")
    sys.exit(1)
if not (MODEL4_DIR / "saved_model.pb").exists():
    print(f"❌ saved_model.pb tidak ada di {MODEL4_DIR}")
    sys.exit(1)

loaded3 = tf.saved_model.load(str(MODEL3_DIR))
infer3 = loaded3.signatures["serving_default"]
print(f"✅ Model 3 loaded dari: {MODEL3_DIR}")
print(f"   Input keys : {list(infer3.structured_input_signature[1].keys())}")
print(f"   Output keys: {list(infer3.structured_outputs.keys())}")

loaded4 = tf.saved_model.load(str(MODEL4_DIR))
infer4 = loaded4.signatures["serving_default"]
print(f"\n✅ Model 4 loaded dari: {MODEL4_DIR}")
print(f"   Input keys : {list(infer4.structured_input_signature[1].keys())}")
print(f"   Output keys: {list(infer4.structured_outputs.keys())}")

# ── 3. Inference Model 3 ───────────────────────────────────────────────────────
section(f"3. INFERENCE MODEL 3 — role: {TEST_ROLE}")

role_list_path = DATA_DIR / "role_list.json"
if role_list_path.exists():
    with open(role_list_path, "r") as f:
        role_list_ordered = json.load(f)
    role_to_idx = {role: i for i, role in enumerate(role_list_ordered)}
    print("✅ Menggunakan role_list.json")
else:
    # Fallback (hanya untuk test, sebaiknya file ada)
    with open(DATA_DIR / "role_freq.json", "r") as f:
        role_freq = json.load(f)
    role_to_idx = {role: i for i, role in enumerate(sorted(role_freq.keys()))}
    print("⚠️  role_list.json tidak ada — hasil mungkin salah")
    
if TEST_ROLE not in role_to_idx:
    print(f"❌ Role '{TEST_ROLE}' tidak ada di role_freq.json")
    print(f"   Available: {list(role_to_idx.keys())[:5]} ...")
    sys.exit(1)

vocab_keys = list(skill_to_idx_li.keys())
user_vec = np.zeros((1, N_SKILLS_LI), dtype=np.float32)
recognised = []
for s in TEST_SKILLS:
    s = s.lower().strip()
    if s in skill_to_idx_li:
        user_vec[0, skill_to_idx_li[s]] = 1.0
        recognised.append(s)
    else:
        best = fuzzy_match(s, vocab_keys)
        if best:
            user_vec[0, skill_to_idx_li[best]] = 1.0
            recognised.append(best)

print(f"Input skills   : {TEST_SKILLS}")
print(f"Recognised     : {recognised}")
print(f"role_to_idx['{TEST_ROLE}'] = {role_to_idx[TEST_ROLE]}")

role_idx = np.array([[role_to_idx[TEST_ROLE]]], dtype=np.int32)
out3 = infer3(
    user_skills=tf.constant(user_vec),
    role_index=tf.constant(role_idx),
)
output_key = list(out3.keys())[0]
pred_scores = out3[output_key].numpy()[0]

mask = user_vec[0] == 0
pred_scores_masked = np.where(mask, pred_scores, -1.0)
top_indices = np.argsort(pred_scores_masked)[::-1][:15]

print(f"\nTop 15 missing skills untuk '{TEST_ROLE}':")
missing_skills = []
for i, idx in enumerate(top_indices, 1):
    score = pred_scores_masked[idx]
    if score > 0:
        name = idx_to_skill_li[str(idx)]
        missing_skills.append((name, score))
        print(f"  {i:2d}. {name:<30s} {score:.4f}")

# ── 4. Inference Model 4 ───────────────────────────────────────────────────────
section("4. INFERENCE MODEL 4 — course recommendations")

npz = np.load(str(DATA_DIR / "synthetic_demand_course_two_tower.npz"))
course_vectors_all = np.asarray(npz["course_vectors"])
num_courses = course_vectors_all.shape[0]
print(f"course_vectors shape: {course_vectors_all.shape}")

demand_vec_li = np.zeros(N_SKILLS_LI, dtype=np.float32)
for skill, _ in missing_skills:
    if skill in skill_to_idx_li:
        demand_vec_li[skill_to_idx_li[skill]] = 1.0

demand_batch = np.tile(demand_vec_li.reshape(1, -1), (num_courses, 1)).astype(np.float32)
course_batch = course_vectors_all.astype(np.float32)

demand_f16 = tf.cast(tf.constant(demand_batch), tf.float16)
course_f16  = tf.cast(tf.constant(course_batch), tf.float16)

out4 = infer4(args_0=demand_f16, args_0_1=course_f16)
match_scores = next(iter(out4.values())).numpy().flatten()
top5 = np.argsort(match_scores)[::-1][:5]

import pandas as pd
df_coursera = pd.read_csv(str(DATA_DIR / "coursera_cleaned.csv")).fillna("")
print("\nTop 5 courses (raw match_score tanpa category affinity):")
for i, cid in enumerate(top5, 1):
    name = df_coursera.iloc[cid].get("Name", "")
    cat  = df_coursera.iloc[cid].get("Job category", "")
    print(f"  {i}. [{cat}] {name}  score={match_scores[cid]:.4f}")

# ── 5. Summary ─────────────────────────────────────────────────────────────────
section("5. SUMMARY")
print("Kalau missing skills di atas masuk akal (excel, power bi, dll.) → model & vocab OK.")
print("Kalau muncul vue/spring boot/css → vocab index mismatch atau model file salah.")
print("\nBandingkan output bagian 3 dengan hasil Kaggle notebook kamu.")