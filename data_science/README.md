# Komponen Data Science QLOP

Direktori ini berisi pipeline scraping data, notebook untuk Exploratory Data Analysis (EDA), A/B Testing, dan Streamlit Market Insight Dashboard yang digunakan untuk memvisualisasikan kebutuhan pekerjaan, tren perekrutan, dan suplai pembelajaran.

---

## Streamlit Market Insight Dashboard

Dashboard QLOP adalah platform analitik visual modern dengan kontras tinggi yang dibangun menggunakan Streamlit dan Plotly untuk menganalisis tren industri teknologi dan mencocokkan profil kurikulum dengan realitas pasar.

* Live Dashboard: [dashboard-qlop.streamlit.app](https://dashboard-qlop.streamlit.app)

### Cara Menjalankan Secara Lokal

1. **Setup Environment**: Pastikan virtual environment Anda aktif dan dependensi telah terinstal.
   ```bash
   pip install -r requirements.txt
   ```
2. **Jalankan Dashboard**:
   ```bash
   streamlit run dashboard.py
   ```
3. **Struktur Dashboard**:
   - **Overview**: Ringkasan global dari postingan pekerjaan, skill unik, proporsi kerja remote, dan distribusi kursus. Mencakup treemap interaktif dan grafik area tren postingan.
   - **Skill Demand**: Detail dari hard skill global teratas, skill yang dibutuhkan per target role, dan heatmap semantik.
   - **Hiring Trends**: Memvisualisasikan linimasa rekrutmen, komposisi tipe kontrak, dan kebutuhan tingkat senioritas.
   - **Course Supply**: Pemetaan kursus online (Coursera) vs. skill yang dibutuhkan oleh perekrut IT.

---

## Script & Pipeline Data

Script Python berikut menangani pemrosesan, pemetaan, dan pembersihan data mentah:

- **[clean_roles.py](./scripts/clean_roles.py)**: Membersihkan judul pekerjaan hasil scraping, menormalisasinya menjadi 27 target role IT kanonik, dan membersihkan string duplikat.
- **[skill_extraction_pipeline.py](./scripts/skill_extraction_pipeline.py)**: Pipeline berat yang memproses bidang teks untuk mengekstrak dan memfilter vektor skill teknologi menggunakan taksonomi kata kunci dan daftar pencocokan.
- **[download_data.py](./scripts/download_data.py)**: Script pembantu untuk mengelola ingest data mentah.

---

## Notebook Lokal

- **[EDA_Skill_Gap_Analysis.ipynb](./notebooks/EDA_Skill_Gap_Analysis.ipynb)**: Analisis eksplorasi mendalam pada dataset mentah hasil scraping yang memetakan kepadatan skill teknologi di berbagai role.
- **[AB_Testing.ipynb](./notebooks/AB_Testing.ipynb)**: Pengujian hipotesis dan analisis metrik untuk memvalidasi signifikansi rekomendasi dan distribusi skor kesiapan pengguna (user readiness score).

---

## Dataset yang Digunakan

| Dataset | Fungsi |
|---|---|
| LinkedIn Jobs | Sumber kebutuhan skill industri dari data lowongan kerja |
| Coursera Courses | Sumber rekomendasi pembelajaran/kursus |
| O*NET Skills | Referensi standar keterampilan untuk validasi dan skill dictionary |

## Sumber Dataset

- **LinkedIn Jobs**: Dataset hasil scraping lowongan kerja LinkedIn menggunakan Apify.
- **Coursera Courses**: Dataset kursus online yang berisi nama kursus, partner, skill, URL, kategori pekerjaan, tingkat kesulitan, dan durasi.
- **O*NET Skills**: Dataset referensi keterampilan standar industri yang digunakan untuk membangun skill dictionary.

## Alur Pengolahan Data

```text
Raw LinkedIn Jobs
        ↓
Role Mapping & Standardisasi Posisi
        ↓
Skill Extraction menggunakan FlashText + Skill Dictionary
        ↓
Skill Cleaning, Noise Removal, dan Deduplikasi
        ↓
Filtering Role IT
        ↓
Role Merging & Balancing
        ↓
MASTERED_DATA_FINAL_MODELING.csv
        ↓
EDA, Skill Gap Analysis, dan Rekomendasi Skill
```

## Metodologi

### 1. Role Mapping

Role mapping dilakukan untuk menstandarisasi variasi nama pekerjaan. Proses ini menggunakan pendekatan **rule-based classification** dengan **weighted keyword matching**.

Bobot kolom yang digunakan:

| Kolom | Bobot |
|---|---:|
| standardizedTitle | 5 |
| title | 4 |
| jobFunction | 2 |
| industries | 1 |
| descriptionText | 1 |

Role dengan skor tertinggi dipilih sebagai `role_label`. Jika tidak ada keyword yang cocok, data diberi label default `General IT Specialist`.

### 2. Skill Extraction

Skill extraction dilakukan menggunakan pendekatan **Dictionary-Based Skill Extraction** dengan algoritma **FlashText Keyword Matching**. Skill dictionary dibangun dari dataset O*NET dan tambahan skill teknis yang umum digunakan pada industri IT.

Output utama tahap ini:

| Kolom | Deskripsi |
|---|---|
| extracted_skills | Daftar skill yang berhasil diekstraksi dari deskripsi pekerjaan |
| skill_count | Jumlah skill unik yang ditemukan dalam satu lowongan |

### 3. Final Dataset Preparation

Tahap ini menghasilkan dataset final bernama `MASTERED_DATA_FINAL_MODELING.csv`. Proses yang dilakukan meliputi:

- Parsing kolom skill
- Skill noise removal
- Validasi skill pendek
- Deduplikasi skill
- Filtering role non-IT
- Role merging
- Role balancing
- Pembentukan fitur final

### 4. Exploratory Data Analysis

EDA dilakukan untuk memahami kebutuhan skill industri IT. Analisis yang dilakukan meliputi:

- Skill paling banyak dibutuhkan industri
- Skill inti berdasarkan role IT
- Missing skill
- Distribusi role
- Tingkat kompetisi lowongan kerja
- Distribusi seniority level
- Perbandingan skill Entry Level dan Mid-Senior Level
- Remote working
- Employment type
- Jumlah skill per lowongan

## Hasil Utama EDA

Beberapa temuan utama dari analisis:

- Skill yang paling banyak dicari industri adalah **Python**, diikuti oleh **React.js**, **JavaScript**, **Next.js**, dan **TypeScript**.
- Role dengan tingkat kompetisi tertinggi adalah **Data Analyst**, **Business Intelligence Analyst**, dan **Frontend Developer**.
- Mayoritas lowongan berada pada kategori **Mid-Senior Level**.
- Sebagian besar lowongan masih menerapkan sistem kerja **on-site**, tetapi role seperti AI Engineer, Machine Learning Engineer, dan Software Engineer memiliki peluang remote yang lebih tinggi.
- Rata-rata jumlah skill per lowongan adalah sekitar **4,9 skill**.

## Evaluasi Rekomendasi Skill Gap

Evaluasi dilakukan menggunakan A/B Testing dengan dua strategi:

| Strategi | Metode | Precision@1 |
|---|---|---:|
| Strategi A | Top-3 Heuristik | 12,96% |
| Strategi B | Cosine Similarity | 22,93% |

Strategi B memberikan peningkatan akurasi sebesar **9,97 poin persentase** dan dipilih sebagai pendekatan rekomendasi skill gap yang lebih efektif.

## Struktur File yang Disarankan

```text
qlop-data-science/
├── data/
│   ├── raw/
│   │   ├── RAW_DATA_SCRAPING_CAPSTONE_.csv
│   │   ├── coursera.csv
│   │   └── Skills_ONET.csv
│   ├── interim/
│   │   ├── DATA_CAPSTONE_MAPPING_AI.csv
│   ├── processed/
│   │   ├── JOBS_WITH_EXTRACTED_SKILLS.csv
│   │   └── MASTERED_DATA_FINAL_MODELING.csv
├── notebooks/
│   ├── EDA_Skill_Gap_Analysis.ipynb
│   └── AB_Testing.ipynb
├── scripts/
│   ├── mapping_role.py
│   ├── clean_roles.py
│   └── skill_extraction_pipeline.py
├── README.md
└── DATA_DICTIONARY.md
```

## Teknologi yang Digunakan

- Python
- Pandas
- FlashText
- NumPy
- Matplotlib / Seaborn
- Scikit-learn
- NLP preprocessing
- Cosine Similarity
- Bootstrap Evaluation
- McNemar Test

## Output Akhir

Output utama proyek ini adalah dataset final `MASTERED_DATA_FINAL_MODELING.csv` yang digunakan untuk:

- Analisis kebutuhan skill industri IT
- Analisis skill gap
- Skill matching
- Rekomendasi pembelajaran
- Pengembangan model AI pada platform QLOP

## Kesimpulan

QLOP berhasil membangun fondasi data untuk memahami kebutuhan skill industri IT. Melalui proses role mapping, skill extraction, cleaning, balancing, dan EDA, dataset menjadi lebih terstruktur dan siap digunakan untuk analisis skill gap serta rekomendasi pembelajaran. Hasil evaluasi menunjukkan bahwa pendekatan **Cosine Similarity** lebih efektif dibandingkan metode heuristik dalam menghasilkan rekomendasi skill yang relevan.
