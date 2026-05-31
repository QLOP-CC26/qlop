"""
clean_roles.py
==============
Pipeline pembersihan dataset untuk analisis skills gap per role IT.
Menggunakan dataset: JOBS_WITH_EXTRACTED_SKILLS.csv (hasil FlashText extraction)

Langkah-langkah:
  1. Parse kolom `extracted_skills` (format list string) → list Python.
  2. Filter/bersihkan skill noise (kata kerja generik, skill terlalu ambigu).
  3. Drop role Non-IT yang tidak relevan.
  4. Merge role kecil (<threshold) ke role IT terdekat.
  5. Drop loker dengan 0 skill setelah cleaning.
  6. Simpan hasil akhir siap modeling.
"""

import pandas as pd
import ast
import os
import re
from collections import Counter

# ===========================================================
# KONFIGURASI
# ===========================================================
THRESHOLD_DROP_ROLE = 100    # Role dengan loker < ini di-drop/merge

# ===========================================================
# SKILL NOISE — Kata-kata generik bukan skill nyata
# Diidentifikasi dari audit EDA (notebook EDA_Skill_Gap_Analysis)
# ===========================================================
NOISY_SKILLS = {
    # Kata kerja aksi generik (bukan skill spesifik)
    'Analyze', 'Analysis', 'Adapt', 'Develop', 'Development',
    'Create', 'Reduce', 'REDUCE', 'Make', 'Build', 'Design',
    'Support', 'Implement', 'Deploy', 'Monitor', 'Test',
    'Manage', 'Review', 'Ensure', 'Maintain', 'Use',
    'Post', 'POST',
    # Istilah terlalu generik
    'Programming languages', 'Programming Language',
    'Deadline', 'deadline',
    # False positive umum
    'MAGIC', 'Magic',
    'Google',       # Terlalu umum — Google Analytics/Ads/Sheets dll tetap lolos
    'LinkedIn',     # Bukan skill teknis
    # Single/double char yang bukan bahasa pemrograman valid
    'J', 'xv',
}

# Skills 1-2 karakter yang VALID (bahasa pemrograman nyata)
# Diidentifikasi dari audit EDA
VALID_SHORT_SKILLS = {'C', 'Go', 'R', 'C#', 'C++', '.NET'}

# ===========================================================
# NON-IT ROLES — Langsung di-drop dari dataset
# ===========================================================
NON_IT_ROLES = {
    'Sales Executive',
    'Operations Specialist',
    'Digital Marketing Specialist',
    'Risk & Compliance Analyst',
    'Finance Analyst',
    'Human Resources Specialist',
    'Customer Service',
    'Researcher',
    'Healthcare Professional',
    'Design/Creative Specialist',   # non-IT creative
    'Lecturer/Trainer',
    'Legal Specialist',
    'Technical Writer',
}

# ===========================================================
# ROLE MERGE MAP — Role kecil/niche → Role IT terdekat
# Urutan: spesifik dulu, kemudian yang lebih umum
# ===========================================================
ROLE_MERGE_MAP = {
    # ── Role kecil (<100 loker) berdasarkan temuan EDA ────────
    'Game Developer'            : 'Software Engineer',
    'UI/UX Designer'            : 'Frontend Developer',
    'Project Manager'           : 'Product Manager',
    'Data Governance Specialist': 'Data Engineer',
    'Data Architect'            : 'Data Engineer',
    'IT Support Specialist'     : 'General IT Specialist',
    'System Administrator'      : 'General IT Specialist',
    'Penetration Tester'        : 'Cyber Security Analyst',
    'Enterprise Architect'      : 'Solutions Architect',
    'Blockchain Developer'      : 'Software Engineer',
    # ── Role borderline yang masih IT tapi niche ──────────────
    'Cybersecurity Engineer'    : 'Security Engineer',
    'Product/Project Manager'   : 'Product Manager',
}


# ===========================================================
# FUNGSI-FUNGSI PIPELINE
# ===========================================================

def parse_skills_column(skills_str: str) -> list:
    """Parse kolom extracted_skills dari string-list ke list Python."""
    if pd.isna(skills_str) or skills_str in ('', '[]'):
        return []
    try:
        return ast.literal_eval(skills_str)
    except (ValueError, SyntaxError):
        return []


def clean_skill_list(skills: list) -> list:
    """
    Bersihkan list skill dari noise:
    - Buang kata kerja generik & false positive (dari NOISY_SKILLS).
    - Buang skill terlalu pendek (<= 1 karakter) kecuali yang valid.
    - Buang duplikat.
    - Pertahankan proper casing (sudah disimpan oleh FlashText).
    """
    cleaned = []
    for skill in skills:
        s = skill.strip()
        if not s:
            continue
        # Cek apakah noisy
        if s in NOISY_SKILLS:
            continue
        # Cek panjang: buang skill 1 char yang bukan bahasa pemrograman valid
        if len(s) == 1 and s not in VALID_SHORT_SKILLS:
            continue
        if len(s) == 2 and s.upper() not in {v.upper() for v in VALID_SHORT_SKILLS}:
            # Izinkan C# dideteksi sebagai 2 char
            if s not in VALID_SHORT_SKILLS:
                continue
        cleaned.append(s)
    # Deduplicate sambil pertahankan urutan
    seen = set()
    result = []
    for s in cleaned:
        if s.lower() not in seen:
            seen.add(s.lower())
            result.append(s)
    return result


def drop_non_it_roles(df: pd.DataFrame) -> pd.DataFrame:
    """Drop semua baris dengan role Non-IT."""
    initial = len(df)
    df_clean = df[~df['role_label'].isin(NON_IT_ROLES)].copy()
    dropped_rows = initial - len(df_clean)
    dropped_roles = [r for r in NON_IT_ROLES if r in df['role_label'].values]

    print(f"\n[DROP NON-IT ROLES]")
    print(f"  Role yang di-drop    : {dropped_roles}")
    print(f"  Baris terhapus       : {dropped_rows:,}")
    print(f"  Baris tersisa        : {len(df_clean):,}")
    return df_clean


def merge_small_roles(df: pd.DataFrame, threshold: int = THRESHOLD_DROP_ROLE) -> pd.DataFrame:
    """Merger role niche/kecil ke role IT terdekat, lalu drop yang tersisa di bawah threshold."""
    df_clean = df.copy()
    print(f"\n[MERGE SMALL ROLES — threshold < {threshold} loker]")

    # Terapkan merge map
    merged_summary = []
    for old_role, new_role in ROLE_MERGE_MAP.items():
        count = (df_clean['role_label'] == old_role).sum()
        if count > 0:
            df_clean.loc[df_clean['role_label'] == old_role, 'role_label'] = new_role
            merged_summary.append(f"'{old_role}' ({count}) -> '{new_role}'")

    if merged_summary:
        for m in merged_summary:
            print(f"  Merge: {m}")
    else:
        print("  Tidak ada role yang perlu di-merge.")

    # Drop role yang masih di bawah threshold setelah merge
    role_counts = df_clean['role_label'].value_counts()
    still_small = role_counts[role_counts < threshold].index.tolist()
    if still_small:
        print(f"\n  Role masih < {threshold} loker, di-drop: {still_small}")
        df_clean = df_clean[~df_clean['role_label'].isin(still_small)].copy()

    print(f"\n  Unique roles setelah : {df_clean['role_label'].nunique()}")
    return df_clean


def print_final_distribution(df: pd.DataFrame) -> None:
    """Tampilkan distribusi role akhir dengan indikator keseimbangan."""
    dist = df['role_label'].value_counts()
    max_count = dist.max()

    print("\n" + "=" * 60)
    print("  DISTRIBUSI ROLE AKHIR")
    print("=" * 60)
    for role, count in dist.items():
        if count >= 500:
            tag = '[OK ]'
        elif count >= 200:
            tag = '[MED]'
        elif count >= 100:
            tag = '[LOW]'
        else:
            tag = '[MIN]'
        bar = '#' * min(count // 100, 35)
        print(f"  {tag} {role:<40} {count:>5}  {bar}")
    print("=" * 60)

    ratio = max_count / dist.min() if dist.min() > 0 else float('inf')
    print(f"\n  Total baris     : {len(df):,}")
    print(f"  Total roles     : {df['role_label'].nunique()}")
    print(f"  Imbalance ratio : {ratio:.1f}x  ({dist.idxmax()} vs {dist.idxmin()})")
    print()
    print("  Rekomendasi: Gunakan class_weight='balanced' saat training model.")


def run_cleaning_pipeline(input_path: str, output_path: str) -> pd.DataFrame:
    """
    Pipeline lengkap:
    Load → Parse Skills → Clean Skills → Drop Non-IT → Merge Roles → Drop Missing → Save
    """
    print("\n" + "=" * 60)
    print("  PIPELINE: SKILL CLEANING & ROLE BALANCING")
    print("=" * 60)
    print(f"\n[*] Input  : {input_path}")
    print(f"[*] Output : {output_path}")

    # ── 1. Load ───────────────────────────────────────────────
    df = pd.read_csv(input_path)
    print(f"\n[LOAD] {len(df):,} baris | {df['role_label'].nunique()} roles unik")

    # ── 2. Parse extracted_skills (string-list → list Python) ─
    df['skills_list'] = df['extracted_skills'].apply(parse_skills_column)
    print(f"[PARSE] Kolom extracted_skills berhasil di-parse.")

    # ── 3. Clean skill noise ───────────────────────────────────
    df['skills_list'] = df['skills_list'].apply(clean_skill_list)
    df['skill_count'] = df['skills_list'].apply(len)

    # Ubah kembali ke string format untuk disimpan (comma-separated)
    df['hard_skills'] = df['skills_list'].apply(lambda lst: ', '.join(lst))

    zero_before = (df['skill_count'] == 0).sum()
    print(f"\n[CLEAN SKILLS]")
    print(f"  Skill noise dihapus (Analyze, REDUCE, Programming languages, dll.)")
    print(f"  Loker dengan 0 skill setelah cleaning : {zero_before:,} ({zero_before/len(df)*100:.2f}%)")

    # ── 4. Drop Non-IT Roles ───────────────────────────────────
    df = drop_non_it_roles(df)

    # ── 5. Merge small/niche roles ─────────────────────────────
    df = merge_small_roles(df, threshold=THRESHOLD_DROP_ROLE)

    # ── 6. Drop loker tanpa skill ──────────────────────────────
    df_final = df[df['skill_count'] > 0].copy()
    print(f"\n[DROP MISSING SKILLS]")
    print(f"  Loker tanpa skill dibuang : {len(df) - len(df_final):,}")
    print(f"  Baris final               : {len(df_final):,}")

    # ── 7. Pilih kolom output ──────────────────────────────────
    keep_cols = [
        'applicantsCount', 'applyMethod', 'companyName', 'country',
        'employmentType', 'industries', 'jobFunction', 'location',
        'postedAt', 'seniorityLevel', 'standardizedTitle', 'final_role',
        'role_label', 'workRemoteAllowed', 'hard_skills', 'skill_count',
    ]
    # Hanya ambil kolom yang tersedia
    available_cols = [c for c in keep_cols if c in df_final.columns]

    # Tambahkan final_role jika tidak ada (dari title/standardizedTitle)
    if 'final_role' not in df_final.columns:
        df_final['final_role'] = df_final.get('standardizedTitle', df_final.get('title', ''))

    df_output = df_final[available_cols].copy()

    # ── 8. Simpan ──────────────────────────────────────────────
    print_final_distribution(df_output)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_output.to_csv(output_path, index=False)
    print(f"\n[DONE] Dataset tersimpan: {output_path}")

    return df_output


if __name__ == "__main__":
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    INPUT_FILE  = os.path.join(BASE_DIR, "data", "processed", "JOBS_WITH_EXTRACTED_SKILLS.csv")
    OUTPUT_FILE = os.path.join(BASE_DIR, "data", "processed", "MASTERED_DATA_FINAL_MODELING.csv")

    if os.path.exists(INPUT_FILE):
        df_result = run_cleaning_pipeline(INPUT_FILE, OUTPUT_FILE)
    else:
        print(f"[ERROR] File tidak ditemukan: {INPUT_FILE}")
        print("Pastikan scripts/skill_extraction_pipeline.py sudah dijalankan terlebih dahulu.")
