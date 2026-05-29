"""Skill Gap Analysis + Course Recommendation Service.

Ported from api_recommendation/app.py — Model3 (skill gap scorer)
and Model4 (two-tower course matcher).
"""

from __future__ import annotations

import logging

import numpy as np

from core.model_loader import registry
from schemas.analyze import CourseRecommendation, MissingSkill, SkillGap
from utils.skill_normalizer import fuzzy_match_skill, safe_float

logger = logging.getLogger("qlop.recommendation")


def analyze(cv_skills: list[str], target_role: str) -> tuple[SkillGap, list[CourseRecommendation]]:
    """
    Run Model3 (gap priority) + Model4 (course matching) and return
    structured results.

    Parameters
    ----------
    cv_skills : flat lowercased skill list from CVProfile
    target_role : one of 27 valid roles
    """
    r = registry

    if target_role not in r.role_to_idx:
        raise ValueError(f"Role '{target_role}' tidak dikenali.")

    import tensorflow as tf  # lazy import — tensorflow loads at startup via registry

    # ── Build user multi-hot vector (LinkedIn vocab) ──
    user_vec = np.zeros((1, r.n_skills_li), dtype=np.float32)
    vocab_keys = list(r.skill_to_idx_li.keys())
    recognised_skills: list[str] = []

    for s in cv_skills:
        s_lower = s.lower().strip()
        if s_lower in r.skill_to_idx_li:
            user_vec[0, r.skill_to_idx_li[s_lower]] = 1.0
            recognised_skills.append(s_lower)
        else:
            best = fuzzy_match_skill(s_lower, vocab_keys, threshold=0.6)
            if best:
                user_vec[0, r.skill_to_idx_li[best]] = 1.0
                recognised_skills.append(best)

    # ── Model3: gap priority scorer ──
    role_idx = np.array([[r.role_to_idx[target_role]]], dtype=np.int32)
    out3 = r.infer3(
        user_skills=tf.constant(user_vec),
        role_index=tf.constant(role_idx),
    )
    pred_scores = out3["output_0"].numpy()[0]

    mask = user_vec[0] == 0
    pred_scores_masked = np.where(mask, pred_scores, -1.0)

    top_indices = np.argsort(pred_scores_masked)[::-1][:15]
    missing_skills: list[MissingSkill] = []
    for idx in top_indices:
        score = safe_float(pred_scores_masked[idx])
        if score > 0:
            missing_skills.append(MissingSkill(
                skill=r.idx_to_skill_li[str(idx)],
                priority_score=round(score, 4),
            ))

    # ── Matched skills (user skills relevant for the target role) ──
    role_skills = r.role_freq.get(target_role, {})
    matched_skills = [
        s for s in recognised_skills
        if role_skills.get(s, 0.0) >= 0.1
    ]

    skill_gap = SkillGap(matched_skills=matched_skills, missing_skills=missing_skills)

    # ── Model4: course recommendation ──
    courses = _recommend_courses(missing_skills)

    return skill_gap, courses


def _recommend_courses(missing_skills: list[MissingSkill]) -> list[CourseRecommendation]:
    import tensorflow as tf  # lazy import

    r = registry

    if r.df_coursera is None or r.df_coursera.empty:
        return []

    demand_vec_li = np.zeros(r.n_skills_li, dtype=np.float32)
    for item in missing_skills:
        sk = item.skill
        if sk in r.skill_to_idx_li:
            demand_vec_li[r.skill_to_idx_li[sk]] = 1.0

    demand_batch = np.tile(demand_vec_li.reshape(1, -1), (r.num_courses, 1)).astype(np.float32)
    course_batch = r.course_vectors.astype(np.float32)

    demand_f16 = tf.cast(tf.constant(demand_batch), tf.float16)
    course_f16 = tf.cast(tf.constant(course_batch), tf.float16)

    out4 = r.infer4(args_0=demand_f16, args_0_1=course_f16)
    match_scores = list(out4.values())[0].numpy().flatten()

    top_course_idx = np.argsort(match_scores)[::-1][:20]

    demand_vec_cr = np.zeros(r.n_skills_cr, dtype=np.float32)
    for item in missing_skills:
        li_skill = item.skill
        if li_skill in r.linkedin_to_coursera:
            for cr_skill in r.linkedin_to_coursera[li_skill]:
                if cr_skill in r.skill_to_idx_cr:
                    demand_vec_cr[r.skill_to_idx_cr[cr_skill]] = 1.0

    recommended: list[CourseRecommendation] = []
    for cid in top_course_idx:
        score = safe_float(match_scores[cid])
        if cid >= len(r.df_coursera):
            continue
        row = r.df_coursera.iloc[cid]

        covered = [
            r.idx_to_skill_cr[str(k)]
            for k in range(r.n_skills_cr)
            if r.course_vectors[cid][k] > 0 and demand_vec_cr[k] > 0
        ]

        recommended.append(CourseRecommendation(
            name=str(row.get("Name", "")),
            url=str(row.get("Url", "")),
            match_score=round(score, 4),
            job_category=str(row.get("Job category", "")),
            difficulty=str(row.get("Difficulty", "")),
            duration=str(row.get("Duration", "")),
            covered_skills=covered,
        ))

    return recommended
