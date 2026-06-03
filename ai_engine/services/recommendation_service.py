"""Skill Gap Analysis + Course Recommendation Service.

Uses the Skill Gap Priority Scorer (Model 3)
and the Course Matching Two-Tower Model (Model 4).
"""

from __future__ import annotations

import logging

import numpy as np

from core.model_loader import registry
from schemas.analyze import CourseRecommendation, MissingSkill, SkillGap
from utils.skill_normalizer import fuzzy_match_skill, safe_float

# Social-media / non-technical terms that appear in the LinkedIn skill vocabulary
# but should never surface as "missing skills" for a developer profile.
_SKILL_NOISE_BLOCKLIST: frozenset[str] = frozenset({
    "facebook", "twitter", "youtube", "instagram", "tiktok",
    "linkedin", "pinterest", "snapchat", "whatsapp", "telegram",
    "wechat", "line", "medium", "reddit",
})

logger = logging.getLogger("qlop.recommendation")


def analyze(cv_skills: list[str], target_role: str) -> tuple[SkillGap, list[CourseRecommendation]]:
    """
    Run Skill Gap Priority Scorer + Course Matching Two-Tower Model and return
    structured results.

    Parameters
    ----------
    cv_skills : flat lowercased skill list from CVProfile
    target_role : one of 27 valid roles
    """
    r = registry

    if target_role not in r.role_to_idx:
        raise ValueError(f"Role '{target_role}' not recognized.")

    if r.infer_skill_gap_priority_scorer is None:
        raise RuntimeError("Skill Gap Priority Scorer is not loaded — check skill_gap_priority_scorer_path in settings.")

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
            # Threshold 0.75 avoids false positives (e.g. "AWS" → "sap")
            best = fuzzy_match_skill(s_lower, vocab_keys, threshold=0.75)
            if best:
                user_vec[0, r.skill_to_idx_li[best]] = 1.0
                recognised_skills.append(best)

    # ── Skill Gap Priority Scorer ──
    role_idx = np.array([[r.role_to_idx[target_role]]], dtype=np.int32)
    out3 = r.infer_skill_gap_priority_scorer(
        user_skills=tf.constant(user_vec),
        role_index=tf.constant(role_idx),
    )
    pred_scores = out3["output_0"].numpy()[0]

    mask = user_vec[0] == 0
    pred_scores_masked = np.where(mask, pred_scores, -1.0)

    top_indices = np.argsort(pred_scores_masked)[::-1][:20]
    missing_skills: list[MissingSkill] = []
    for idx in top_indices:
        score = safe_float(pred_scores_masked[idx])
        skill_name = r.idx_to_skill_li[str(idx)]
        if score > 0 and skill_name.lower() not in _SKILL_NOISE_BLOCKLIST:
            missing_skills.append(MissingSkill(
                skill=skill_name,
                priority_score=round(score, 4),
            ))
    missing_skills = missing_skills[:15]

    # ── Matched skills (user skills relevant for the target role) ──
    role_skills = r.role_freq.get(target_role, {})
    matched_skills = [
        s for s in recognised_skills
        if role_skills.get(s, 0.0) >= 0.1
    ]

    skill_gap = SkillGap(matched_skills=matched_skills, missing_skills=missing_skills)

    # ── Course Matching Two-Tower Model (Model 4) ──
    courses = _recommend_courses(missing_skills)

    return skill_gap, courses


def _recommend_courses(missing_skills: list[MissingSkill]) -> list[CourseRecommendation]:
    import tensorflow as tf  # lazy import

    r = registry

    if r.infer_course_matching_two_tower_model is None:
        return []
    if r.df_coursera is None or r.df_coursera.empty:
        return []

    demand_vec_li = np.zeros(r.n_skills_li, dtype=np.float32)
    for item in missing_skills:
        sk = item.skill
        if sk in r.skill_to_idx_li:
            demand_vec_li[r.skill_to_idx_li[sk]] = 1.0

    demand_batch = np.tile(demand_vec_li.reshape(1, -1), (r.num_courses, 1)).astype(np.float32)
    if r.course_vectors is None:
        return []

    course_batch = r.course_vectors.astype(np.float32)

    demand_f16 = tf.cast(tf.constant(demand_batch), tf.float16)
    course_f16 = tf.cast(tf.constant(course_batch), tf.float16)

    out4 = r.infer_course_matching_two_tower_model(args_0=demand_f16, args_0_1=course_f16)
    match_scores = next(iter(out4.values())).numpy().flatten()

    top_course_idx = np.argsort(match_scores)[::-1][:20]

    demand_vec_cr = np.zeros(r.n_skills_cr, dtype=np.float32)
    for item in missing_skills:
        li_skill = item.skill
        if li_skill in r.linkedin_to_coursera:
            for cr_skill in r.linkedin_to_coursera[li_skill]:
                if cr_skill in r.skill_to_idx_cr:
                    demand_vec_cr[r.skill_to_idx_cr[cr_skill]] = 1.0

    seen_urls: set[str] = set()
    recommended: list[CourseRecommendation] = []
    for cid in top_course_idx:
        score = safe_float(match_scores[cid])
        if cid >= len(r.df_coursera):
            continue
        row = r.df_coursera.iloc[cid]
        url = str(row.get("Url", ""))

        # Skip exact-URL duplicates (same course listed multiple times in dataset)
        if url in seen_urls:
            continue
        seen_urls.add(url)

        course_vec = r.course_vectors[cid] if r.course_vectors is not None else None

        covered = [
            r.idx_to_skill_cr[str(k)]
            for k in range(r.n_skills_cr)
            if course_vec is not None and course_vec[k] > 0 and demand_vec_cr[k] > 0
        ]

        recommended.append(CourseRecommendation(
            name=str(row.get("Name", "")),
            url=url,
            match_score=round(score, 4),
            job_category=str(row.get("Job category", "")),
            difficulty=str(row.get("Difficulty", "")),
            duration=str(row.get("Duration", "")),
            covered_skills=covered,
        ))

    return recommended
