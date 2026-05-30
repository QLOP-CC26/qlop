from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import tensorflow as tf
import numpy as np
import pandas as pd
import json
import os
from difflib import get_close_matches

def safe_float(value):
    try:
        val = float(value)
        if not np.isfinite(val):
            return 0.0
        return val
    except (ValueError, TypeError):
        return 0.0

app = FastAPI(title="QLOP API", version="1.0")

print("Loading models and data...")

loaded3 = tf.saved_model.load("models/model3_savedmodel")
infer3 = loaded3.signatures['serving_default']

loaded4 = tf.saved_model.load("models/model4_savedmodel")
infer4 = loaded4.signatures['serving_default']

with open("data/skill_vocab_linkedin.json", "r") as f:
    vocab_li = json.load(f)
skill_to_idx_li = vocab_li["skill_to_idx"]
idx_to_skill_li = vocab_li["idx_to_skill"]
N_SKILLS_LI = vocab_li["vocab_size"]

with open("data/skill_vocab_coursera.json", "r") as f:
    vocab_cr = json.load(f)
skill_to_idx_cr = vocab_cr["skill_to_idx"]
idx_to_skill_cr = vocab_cr["idx_to_skill"]
N_SKILLS_CR = vocab_cr["vocab_size"]

with open("data/linkedin_to_coursera_mapping.json", "r") as f:
    linkedin_to_coursera = json.load(f)

df_coursera = pd.read_csv("data/coursera_cleaned.csv").fillna('')

demand_npz = np.load("data/synthetic_demand_course_model4.npz")
course_vectors_all = demand_npz["course_vectors"]  
num_courses = len(course_vectors_all)

with open("data/role_freq.json", "r") as f:
    role_freq_data = json.load(f)
role_list = sorted(role_freq_data.keys())
role_to_idx = {role: i for i, role in enumerate(role_list)}

print("All components loaded successfully.")

def fuzzy_match_skill(skill, vocab_keys, threshold=0.6):
    matches = get_close_matches(skill, vocab_keys, n=1, cutoff=threshold)
    return matches[0] if matches else None

class AnalyzeRequest(BaseModel):
    cv_skills: list[str]
    role: str

@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    cv_skills = [s.lower().strip() for s in request.cv_skills if s.strip()]
    role_input = request.role.strip()

    if role_input not in role_to_idx:
        raise HTTPException(status_code=400, detail=f"Role '{role_input}' tidak dikenali.")

    user_vec = np.zeros((1, N_SKILLS_LI), dtype=np.float32)
    vocab_li_keys = list(skill_to_idx_li.keys())

    for s in cv_skills:
        if s in skill_to_idx_li:
            user_vec[0, skill_to_idx_li[s]] = 1.0
        else:
            best = fuzzy_match_skill(s, vocab_li_keys, threshold=0.6)
            if best:
                user_vec[0, skill_to_idx_li[best]] = 1.0

    role_idx = np.array([[role_to_idx[role_input]]], dtype=np.int32)
    out3 = infer3(
        user_skills=tf.constant(user_vec),
        role_index=tf.constant(role_idx)
    )
    pred_scores = out3['output_0'].numpy()[0]

    mask = user_vec[0] == 0
    pred_scores_masked = np.where(mask, pred_scores, -1.0)

    top_indices = np.argsort(pred_scores_masked)[::-1][:15]
    top_skills = []
    for idx in top_indices:
        score = safe_float(pred_scores_masked[idx])
        if score > 0:
            top_skills.append({
                "skill": idx_to_skill_li[str(idx)],
                "priority_score": score
            })

    demand_vec_li = np.zeros(N_SKILLS_LI, dtype=np.float32)
    for item in top_skills:
        sk = item['skill']
        if sk in skill_to_idx_li:
            demand_vec_li[skill_to_idx_li[sk]] = 1.0

    demand_batch = np.tile(demand_vec_li.reshape(1, -1), (num_courses, 1)).astype(np.float32)
    course_batch = course_vectors_all.astype(np.float32)

    demand_batch_f16 = tf.cast(tf.constant(demand_batch), tf.float16)
    course_batch_f16 = tf.cast(tf.constant(course_batch), tf.float16)

    kwargs4 = {
        'args_0': demand_batch_f16,
        'args_0_1': course_batch_f16
    }
    out4 = infer4(**kwargs4)
    match_scores = list(out4.values())[0].numpy().flatten()

    top_course_idx = np.argsort(match_scores)[::-1][:20]

    demand_vec_cr = np.zeros(N_SKILLS_CR, dtype=np.float32)
    for item in top_skills:
        li_skill = item['skill']
        if li_skill in linkedin_to_coursera:
            for cr_skill in linkedin_to_coursera[li_skill]:
                if cr_skill in skill_to_idx_cr:
                    demand_vec_cr[skill_to_idx_cr[cr_skill]] = 1.0

    recommended = []
    for cid in top_course_idx:
        score = safe_float(match_scores[cid])
        row = df_coursera.iloc[cid]
        name = row['Name']
        url = row['Url']
        job_category = row['Job category']
        difficulty = row['Difficulty']
        duration = row['Duration']

        all_skills = [idx_to_skill_cr[str(k)] for k in range(N_SKILLS_CR)
                      if course_vectors_all[cid][k] > 0]
        covered = [idx_to_skill_cr[str(k)] for k in range(N_SKILLS_CR)
                   if course_vectors_all[cid][k] > 0 and demand_vec_cr[k] > 0]

        recommended.append({
            "name": name,
            "url": url,
            "match_score": score,
            "job_category": job_category,
            "difficulty": difficulty,
            "duration": duration,
            "all_skills": all_skills,
            "covered_skills": covered
        })

    return {
        "top_skills": top_skills,
        "recommended_courses": recommended
    }


from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import os
import re

print("Loading SBERT model")
sbert_model = SentenceTransformer('all-MiniLM-L6-v2')
print("SBERT model loaded.")

EMBEDDING_DIR = "./data/embeddings"
os.makedirs(EMBEDDING_DIR, exist_ok=True)

with open("data/role_job_skills.json", "r") as f:
    role_job_skills = json.load(f)

def safe_filename(role_name):
    return re.sub(r'[\\/]', '_', role_name)

embedding_ready = True
for role in role_job_skills.keys():
    safe_role = safe_filename(role)
    emb_path = os.path.join(EMBEDDING_DIR, f"{safe_role}_job_embeddings.npy")
    if not os.path.exists(emb_path):
        embedding_ready = False
        break

skills_list_path = os.path.join(EMBEDDING_DIR, "job_skills_list_all.json")
if not os.path.exists(skills_list_path):
    embedding_ready = False

if embedding_ready:
    print("Pre-computed embeddings found. Loading from files.")
    job_embeddings = {}
    for role in role_job_skills.keys():
        safe_role = safe_filename(role)
        emb_path = os.path.join(EMBEDDING_DIR, f"{safe_role}_job_embeddings.npy")
        job_embeddings[role] = np.load(emb_path)

    with open(skills_list_path, 'r') as f:
        job_skills_list_all = json.load(f)
    print("Job embeddings loaded from files.")

else:
    print("Pre-computing job embeddings")
    job_embeddings = {}
    job_skills_list_all = {}

    for role, list_of_skill_lists in role_job_skills.items():
        role_job_embeds = []
        batch_size = 64
        for i in range(0, len(list_of_skill_lists), batch_size):
            batch = list_of_skill_lists[i:i+batch_size]
            texts = [' '.join(skills) if skills else '.' for skills in batch]
            embeds = sbert_model.encode(texts, convert_to_tensor=False)
            role_job_embeds.extend(embeds)
        job_embeddings[role] = np.array(role_job_embeds, dtype=np.float32)
        job_skills_list_all[role] = list_of_skill_lists

    for role, emb_array in job_embeddings.items():
        safe_role = safe_filename(role)
        emb_path = os.path.join(EMBEDDING_DIR, f"{safe_role}_job_embeddings.npy")
        os.makedirs(os.path.dirname(emb_path), exist_ok=True)
        np.save(emb_path, emb_array)

    with open(skills_list_path, 'w') as f:
        json.dump(job_skills_list_all, f)

    print("Job embeddings computed and saved to files.")

print("Readiness scoring system ready.")

def cosine_sim(a, b):
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b) + 1e-9
    return dot / norm

class ReadinessRequest(BaseModel):
    cv_skills: list[str]
    role: str


@app.post("/readiness_score")
def readiness_score(request: ReadinessRequest):
    raw_skills = [s.lower().strip() for s in request.cv_skills if s.strip()]
    role = request.role.strip()

    if role not in role_job_skills:
        raise HTTPException(status_code=400, detail=f"Role '{role}' tidak dikenali.")

    user_skills = []
    vocab_li_keys = list(skill_to_idx_li.keys())
    for s in raw_skills:
        if s in skill_to_idx_li:
            user_skills.append(s)
        else:
            best = fuzzy_match_skill(s, vocab_li_keys, threshold=0.6)
            if best:
                user_skills.append(best)

    if not user_skills:
        return {
            "score": 0.0,
            "matched_skills": [],
            "interpretation": "Tidak ada skill yang berhasil dikenali."
        }

    user_text = ' '.join(user_skills)
    user_emb = sbert_model.encode([user_text], convert_to_tensor=False)[0].astype(np.float32)

    job_embeds = job_embeddings[role]              
    job_skill_lists = job_skills_list_all[role]    
    total_jobs = len(job_skill_lists)

    user_norm = user_emb / (np.linalg.norm(user_emb) + 1e-9)
    job_norms = np.linalg.norm(job_embeds, axis=1, keepdims=True)
    job_embeds_norm = job_embeds / (job_norms + 1e-9)
    sims = np.dot(job_embeds_norm, user_norm)      

    skill_contrib = defaultdict(float)
    for i, job_skills in enumerate(job_skill_lists):
        sim = float(sims[i])
        for skill in job_skills:
            skill_contrib[skill] += sim

    total_contrib = sum(skill_contrib.values())
    if total_contrib == 0:
        return {
            "score": 0.0,
            "matched_skills": user_skills,
            "interpretation": "Tidak ada data lowongan untuk role ini."
        }

    user_contrib = sum(skill_contrib.get(skill, 0) for skill in user_skills)
    score = user_contrib / total_contrib

    return {
        "score": round(safe_float(score), 4),
        "matched_skills": user_skills,
        "interpretation": "Skor ini menunjukkan seberapa selaras skill Anda dengan kebutuhan pasar secara keseluruhan. Semakin tinggi (mendekati 1), semakin siap Anda."
    }