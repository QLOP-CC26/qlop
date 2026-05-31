# Anda perlu menginstal flashtext dan pandas terlebih dahulu jika belum:
# pip install flashtext pandas openpyxl

import pandas as pd
from flashtext import KeywordProcessor
import time
import os

def setup_keyword_processor(onet_file_path):
    """
    Fungsi untuk membaca data ONET dan memasukkannya ke dalam FlashText KeywordProcessor.
    """
    print(f"[*] Membaca referensi skill dari: {onet_file_path} ...")
    df_onet = pd.read_excel(onet_file_path)
    
    # Mengambil kolom 'Example' sebagai daftar skill. 
    # Pastikan menyesuaikan nama kolom jika ada kolom lain yang juga berisi nama skill.
    if 'Example' not in df_onet.columns:
        raise ValueError("Kolom 'Example' tidak ditemukan di dataset ONET.")
        
    # Membersihkan data (drop missing values, ubah ke string, dan hilangkan duplikat)
    onet_skills = df_onet['Example'].dropna().astype(str).str.strip().unique().tolist()
    
    # Inisialisasi FlashText (case_insensitive=True agar "c++" atau "C++" sama-sama terbaca)
    kp = KeywordProcessor(case_sensitive=False)
    
    # Menambahkan skill ke processor
    for skill in onet_skills:
        kp.add_keyword(skill)
        
    # [OPSIONAL] menambahkan skill penting secara manual
    custom_tech_skills = [
        "C++", "C#", ".NET", "Node.js", "React.js", "Next.js", "Vue.js", 
        "CSS", 'HTML'
    ]
    for skill in custom_tech_skills:
        # Menambahkan custom skill agar outputnya konsisten menggunakan casing dari list di atas
        kp.add_keyword(skill, skill) 
        
    # Memetakan typo umum ke skill yang benar
    typo_aliases = {
        "SQL": ["SLQ", "SLQ librabry", "SLQ Library"],
        "JavaScript": ["Javascript", "Javascritp", "JS"],
        "TypeScript": ["Typescript", "TS"],
        "Python": ["Phython", "Pyton"],
        "React.js": ["React", "ReactJS", "React js"],
        "Node.js": ["Node", "NodeJS", "Node js"],
        "Vue.js": ["Vue", "VueJS", "Vue js"],
        "Next.js": ["Next", "NextJS", "Next js"],
        "C++": ["C ++", "cpp"],
        "C#": ["C #", "CSharp", "C-Sharp"]
    }
    for correct_skill, typos in typo_aliases.items():
        for typo in typos:
            kp.add_keyword(typo, correct_skill)
        
    print(f"[*] Berhasil memuat {len(onet_skills) + len(custom_tech_skills)} skill ke dalam sistem Ekstraktor.")
    return kp

def extract_skills_from_dataset(jobs_file_path, keyword_processor, output_file_path):
    """
    Fungsi untuk membaca dataset Loker, mengekstrak skill, dan menyimpannya.
    """
    print(f"\n[*] Membaca dataset Loker dari: {jobs_file_path} ...")
    df_jobs = pd.read_csv(jobs_file_path)
    
    target_column = 'translated_descriptionText'
    if target_column not in df_jobs.columns:
        raise ValueError(f"Kolom '{target_column}' tidak ditemukan di dataset Loker.")
    
    # Membersihkan NaN pada deskripsi agar tidak error saat diekstrak
    df_jobs[target_column] = df_jobs[target_column].fillna("")
    
    print("[*] Memulai proses ekstraksi skill (Ini hanya butuh waktu beberapa detik menggunakan FlashText)...")
    start_time = time.time()
    
    # Fungsi lambda untuk mengekstrak skill dan menghilangkan duplikat per baris (menggunakan set)
    df_jobs['extracted_skills'] = df_jobs[target_column].apply(
        lambda text: list(set(keyword_processor.extract_keywords(text)))
    )
    
    # Menghitung jumlah skill yang diekstrak per baris
    df_jobs['skill_count'] = df_jobs['extracted_skills'].apply(len)
    
    end_time = time.time()
    print(f"[*] Ekstraksi selesai dalam {end_time - start_time:.2f} detik!")
    
    # Menyimpan hasil
    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
    df_jobs.to_csv(output_file_path, index=False)
    print(f"[*] Hasil berhasil disimpan ke: {output_file_path}")
    
    return df_jobs

# ==========================================
# BAGIAN EKSEKUSI
# ==========================================
if __name__ == "__main__":
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    ONET_FILE = os.path.join(BASE_DIR, "data", "raw", "Skills_ONET.xlsx")
    JOBS_FILE = os.path.join(BASE_DIR, "data", "interim", "DATA_CAPSTONE_MAPPING_AI.csv")
    OUTPUT_FILE = os.path.join(BASE_DIR, "data", "processed", "JOBS_WITH_EXTRACTED_SKILLS.csv")
    
    try:
        # 1. Siapkan extractor
        extractor = setup_keyword_processor(ONET_FILE)
        
        # 2. Lakukan ekstraksi pada dataset
        df_result = extract_skills_from_dataset(JOBS_FILE, extractor, OUTPUT_FILE)
        
        # 3. Tampilkan 5 baris pertama hasilnya
        print("\n=== Cuplikan Hasil Ekstraksi ===")
        print(df_result[['translated_descriptionText', 'extracted_skills', 'skill_count']].head())
        
    except Exception as e:
        print(f"Terjadi kesalahan: {e}")
