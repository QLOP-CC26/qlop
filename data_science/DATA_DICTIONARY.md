# Data Dictionary - QLOP Dataset

Dokumen ini menjelaskan struktur data yang digunakan dalam proyek **QLOP: Platform Analisis Kesenjangan Keahlian dan Rekomendasi Pembelajaran Berbasis NLP**.

## 1. RAW_DATA_SCRAPING_CAPSTONE_.csv / LinkedIn Jobs Dataset

Dataset ini berisi data lowongan kerja hasil scraping dari LinkedIn. Dataset digunakan sebagai sumber utama untuk mengetahui kebutuhan skill industri.

| Nama Kolom | Tipe Data | Deskripsi | Contoh Isi |
|---|---|---|---|
| applicantsCount | Integer / Float | Jumlah pelamar pada lowongan pekerjaan | 120 |
| applyMethod | String | Metode melamar pekerjaan | Easy Apply, External Apply |
| companyName | String | Nama perusahaan yang membuka lowongan | ABC Technology |
| country | String | Negara lokasi pekerjaan | Indonesia |
| descriptionText | String | Deskripsi lengkap pekerjaan | We are looking for a Data Analyst... |
| employmentType | String | Jenis pekerjaan | Full-time, Contract, Internship |
| industries | String | Industri perusahaan | IT Services, Software Development |
| jobFunction | String | Fungsi pekerjaan | Engineering, Data Science |
| postedAt | Datetime / String | Tanggal atau waktu lowongan diposting | 2026-01-10 |
| salary | String / Float | Informasi gaji jika tersedia | Rp8.000.000 - Rp12.000.000 |
| seniorityLevel | String | Tingkat senioritas pekerjaan | Entry Level, Associate, Mid-Senior |
| standardizedTitle | String | Judul pekerjaan yang sudah distandarisasi | Data Analyst |
| title | String | Judul pekerjaan asli dari sumber data | Junior Data Analyst |
| workRemoteAllowed | Boolean / Integer | Menunjukkan apakah pekerjaan dapat dilakukan secara remote | True / False |

## 2. Coursera Courses Dataset

Dataset ini digunakan sebagai sumber rekomendasi pembelajaran berdasarkan skill yang dibutuhkan industri.

| Nama Kolom | Tipe Data | Deskripsi | Contoh Isi |
|---|---|---|---|
| name | String | Nama kursus pembelajaran | Python for Everybody |
| partners | String | Institusi atau partner penyedia kursus | University of Michigan |
| skills | String | Skill yang dipelajari dalam kursus | Python, Data Analysis |
| url | String | Link menuju halaman kursus | https://coursera.org/... |
| job_category | String | Kategori pekerjaan yang relevan dengan kursus | Data Analyst |
| difficulty | String | Tingkat kesulitan kursus | Beginner, Intermediate, Advanced |
| duration | String | Durasi kursus | 4 weeks |

## 3. O*NET Skills Dataset

Dataset ini digunakan sebagai referensi standar keterampilan industri dan dasar pembangunan skill dictionary.

| Nama Kolom | Tipe Data | Deskripsi | Contoh Isi |
|---|---|---|---|
| example | String | Nama skill atau contoh keterampilan dari O*NET | Python, SQL, Project Management |

## 4. DATA_CAPSTONE_MAPPING_AI.csv

Dataset ini merupakan hasil proses role mapping dari data lowongan kerja. Tujuannya adalah menstandarisasi variasi judul pekerjaan menjadi label role yang lebih konsisten.

| Nama Kolom | Tipe Data | Deskripsi | Contoh Isi |
|---|---|---|---|
| role_label | String | Label pekerjaan hasil klasifikasi role mapping | Data Analyst |
| label_score | Integer / Float | Skor hasil pencocokan keyword berbobot | 9 |
| label_source | String | Kolom sumber yang menghasilkan kecocokan keyword | standardizedTitle |
| label_keyword | String | Keyword yang cocok dengan role tertentu | data analyst |
| label_method | String | Metode klasifikasi yang digunakan | weighted_keyword_matching |

## 5. JOBS_WITH_EXTRACTED_SKILLS.csv

Dataset ini merupakan hasil ekstraksi skill dari deskripsi pekerjaan.

| Nama Kolom | Tipe Data | Deskripsi | Contoh Isi |
|---|---|---|---|
| extracted_skills | List / String | Daftar skill yang berhasil diekstraksi dari deskripsi pekerjaan | ['python', 'sql', 'tableau'] |
| skill_count | Integer | Jumlah skill unik yang berhasil ditemukan pada satu lowongan | 3 |

## 6. MASTERED_DATA_FINAL_MODELING.csv

Dataset ini adalah dataset final yang sudah melalui proses cleaning, filtering, role merging, balancing, dan feature preparation. Dataset ini digunakan untuk EDA, analisis skill gap, dan pemodelan AI.

| Nama Kolom | Tipe Data | Deskripsi | Contoh Isi |
|---|---|---|---|
| role_label | String | Label pekerjaan final setelah role mapping, filtering, dan merging | Data Engineer |
| hard_skills | List / String | Daftar skill final setelah cleaning, noise removal, validasi, dan deduplikasi | ['python', 'sql', 'spark'] |
| skill_count | Integer | Jumlah skill unik pada satu lowongan setelah proses cleaning | 3 |
| standardizedTitle | String | Nama posisi pekerjaan yang sudah distandarisasi | Data Engineer |
| companyName | String | Nama perusahaan | XYZ Digital |
| employmentType | String | Jenis pekerjaan | Full-time |
| location | String | Lokasi pekerjaan | Jakarta, Indonesia |

## 7. Kolom Hasil Role Mapping

| Nama Kolom | Tipe Data | Deskripsi |
|---|---|---|
| role_label | String | Label pekerjaan hasil klasifikasi berdasarkan keyword dan bobot kolom |
| label_score | Numeric | Total skor pencocokan keyword untuk role terpilih |
| label_source | String | Sumber kolom tempat keyword ditemukan |
| label_keyword | String | Keyword yang menyebabkan data masuk ke role tertentu |
| label_method | String | Metode klasifikasi role, yaitu rule-based weighted keyword matching |

## 8. Kolom Hasil Skill Extraction dan Cleaning

| Nama Kolom | Tipe Data | Deskripsi |
|---|---|---|
| extracted_skills | List / String | Skill mentah hasil ekstraksi dari deskripsi pekerjaan |
| hard_skills | List / String | Skill final yang sudah dibersihkan dan distandarisasi |
| skill_count | Integer | Jumlah skill unik yang terdeteksi dalam satu lowongan |

## 9. Daftar Role Setelah Standardisasi

Role yang digunakan dalam proses mapping mencakup role IT dan digital seperti:

| Role Label | Deskripsi Umum |
|---|---|
| Data Analyst | Menganalisis data dan membuat insight bisnis |
| Data Scientist | Membangun model statistik, machine learning, dan analisis prediktif |
| Data Engineer | Mengelola pipeline data, ETL, data warehouse, dan big data |
| Machine Learning Engineer | Membangun, melatih, dan melakukan deployment model machine learning |
| AI Engineer | Mengembangkan solusi AI, LLM, RAG, dan generative AI |
| Business Intelligence Analyst | Membuat dashboard, visualisasi, dan analisis bisnis |
| Backend Developer | Mengembangkan server-side application dan API |
| Frontend Developer | Mengembangkan tampilan aplikasi web |
| Full Stack Developer | Mengembangkan frontend dan backend aplikasi |
| Mobile Developer | Mengembangkan aplikasi mobile Android/iOS |
| Software Engineer | Mengembangkan perangkat lunak secara umum |
| DevOps Engineer | Mengelola CI/CD, container, deployment, dan infrastruktur |
| Cloud Engineer | Mengelola infrastruktur cloud seperti AWS, Azure, dan GCP |
| Cyber Security Analyst | Menganalisis risiko keamanan dan ancaman siber |
| Security Engineer | Membangun dan mengelola sistem keamanan aplikasi/infrastruktur |
| Network Engineer | Mengelola jaringan komputer |
| QA Engineer | Melakukan pengujian kualitas perangkat lunak |
| Product Manager | Mengelola strategi dan pengembangan produk |
| Solutions Architect | Mendesain solusi teknis sesuai kebutuhan bisnis |
| IT Consultant | Memberikan konsultasi teknologi |
| Embedded/IoT Engineer | Mengembangkan sistem embedded dan IoT |
| Technical Writer | Membuat dokumentasi teknis |
| General IT Specialist | Role IT umum atau fallback jika role tidak terdeteksi jelas |

## 10. Role Merging

Beberapa role dengan jumlah data kecil digabungkan ke role yang lebih umum agar distribusi data lebih stabil.

| Role Awal | Role Hasil Merge |
|---|---|
| Game Developer | Software Engineer |
| Blockchain Developer | Software Engineer |
| UI/UX Designer | Frontend Developer |
| Project Manager | Product Manager |
| Product/Project Manager | Product Manager |
| Data Governance Specialist | Data Engineer |
| Data Architect | Data Engineer |
| IT Support Specialist | General IT Specialist |
| System Administrator | General IT Specialist |
| Penetration Tester | Cyber Security Analyst |
| Enterprise Architect | Solutions Architect |

## 11. Catatan Penggunaan Dataset

- Dataset LinkedIn digunakan untuk membaca kebutuhan skill industri.
- Dataset Coursera digunakan untuk rekomendasi pembelajaran.
- Dataset O*NET digunakan sebagai referensi standar skill.
- Dataset final `MASTERED_DATA_FINAL_MODELING.csv` digunakan untuk EDA, analisis skill gap, dan pemodelan AI.
- Kolom `role_label`, `hard_skills`, dan `skill_count` merupakan fitur utama untuk analisis kebutuhan kompetensi.
