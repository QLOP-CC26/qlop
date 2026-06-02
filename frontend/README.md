# QLOP Frontend – Antarmuka Pengguna

Aplikasi Halaman Tunggal (SPA) modern yang dibangun menggunakan **React** dan **Vite** dengan **Tailwind CSS**. Halaman ini berfungsi sebagai antarmuka interaktif untuk **QLOP** (Platform Analisis Kesenjangan Keahlian), yang memungkinkan pengguna mengunggah CV, memvisualisasikan tingkat kesiapan kerja, dan mengidentifikasi jalur karir alternatif secara cerdas.

## Tech Stack

- **Framework:** React 18+ (Single Page Application)
- **Build Tool:** Vite (server development super cepat dan optimasi bundle produksi)
- **Styling:** Tailwind CSS (modern, utility-first CSS framework dengan gaya glassmorphism yang serasi)
- **Routing:** React Router DOM v6
- **Ikon:** Lucide React
- **Autentikasi Pihak Ketiga:** Google Identity Service GSI Client SDK (Google Sign-In)

---

## Struktur Direktori

```
frontend/
├── public/                 # Aset statis global (logo.png, dll.)
├── src/
│   ├── assets/             # Aset gambar lokal untuk proyek
│   ├── components/         # Komponen presentasi yang dapat digunakan kembali
│   │   ├── AlternativeRoleCard/
│   │   ├── AppNavbar/      # Navbar setelah login dengan dropdown seluler
│   │   ├── Badges/
│   │   ├── Button/         # Tombol aksi premium bersama (primary/outline)
│   │   ├── CourseCard/     # Kartu untuk daftar rekomendasi kursus
│   │   ├── Divider/
│   │   ├── Footer/         # Footer bersih yang digunakan bersama
│   │   ├── InputField/     # Input form dengan validasi bawaan
│   │   ├── Navbar/         # Navbar halaman landing & halaman auth
│   │   ├── PivotRadarChart/
│   │   ├── ProtectedRoute/ # Pelindung rute yang memeriksa token JWT localStorage
│   │   ├── RadarSection/   # Visualisasi radar karir alternatif
│   │   ├── ReadinessBar/   # Indikator skor kesiapan kerja
│   │   └── SectionCard/    # Pembungkus kartu modern
│   ├── pages/              # Komponen halaman yang dipetakan ke rute
│   │   ├── Analyze/        # Halaman unggah PDF CV dengan drag-and-drop
│   │   ├── Analyzing/      # Tracker ekstraksi real-time dengan status dinamis dari AI
│   │   ├── Auth/           # Form Login & Register premium dengan Google OAuth
│   │   ├── History/        # Halaman riwayat analisis dengan fitur sortir & hapus
│   │   └── Landing/        # Halaman utama pemasaran interaktif & About Us
│   ├── App.jsx             # Konfigurasi router utama & pelindung rute
│   ├── index.css           # Impor font global (Inter) & direktif Tailwind
│   └── main.jsx            # Titik masuk untuk merender DOM React
├── .env.example            # Contoh file variabel lingkungan
├── package.json            # Daftar pustaka dependencies & skrip proyek
└── vite.config.js          # Konfigurasi Vite dan server proxy
```

---

## Setup & Instalasi

### Prasyarat

- **Node.js** >= 18
- **Layanan Backend Express** sudah berjalan di `localhost:5000`

### Langkah-Langkah Instalasi

**1. Masuk ke direktori frontend:**
```bash
cd frontend
```

**2. Instal semua dependencies:**
```bash
npm install
```

**3. Konfigurasi variabel lingkungan lokal:**

Salin file `.env.example` menjadi `.env` dengan salah satu cara berikut:

* **Menggunakan Terminal / CLI (Direkomendasikan):**
  * **Windows (PowerShell):**
    ```powershell
    Copy-Item .env.example .env
    ```
  * **Windows (CMD):**
    ```cmd
    copy .env.example .env
    ```
  * **Linux / macOS / Git Bash:**
    ```bash
    cp .env.example .env
    ```
* **Secara Manual di VS Code:**
  * Klik kanan file `.env.example` ➔ Pilih **Copy** ➔ Klik kanan folder `frontend` ➔ Pilih **Paste**. 
  * Ganti nama file salinan tersebut menjadi **`.env`** (pastikan tanda titik di depannya ikut tertulis).

Setelah disalin, pastikan variabel di dalamnya sesuai:
```env
VITE_API_URL=http://localhost:5000
```

**4. Jalankan server development lokal:**
```bash
npm run dev
```
Buka peramban browser Anda dan akses `http://localhost:5173`.

**5. Build proyek untuk produksi:**
```bash
npm run build
```

---

## Sistem Desain & Detail Estetika

Tampilan frontend mengikuti **sistem desain premium yang seragam** di seluruh halaman:

* **Latar Belakang:** Seluruh halaman aplikasi menggunakan latar belakang abu-abu netral sangat terang yang konsisten (`bg-slate-50`) untuk memastikan transisi navigasi terasa mulus.
* **Tipografi:** Menggunakan font global **`Inter`** dari Google Fonts untuk tampilan sans-serif yang bersih, tajam, dan mudah dibaca.
* **Glassmorphism:** Semua Navbar menggunakan efek `backdrop-blur-md bg-white/90` dengan border tipis abu-abu yang elegan.
* **Warna Aksen:** Biru Royal (`#2563EB`) digunakan untuk tombol aksi utama, warna hijau emerald hangat untuk kecocokan tinggi, dan warna merah peringatan untuk indikasi skill yang kurang.
* **Mikro-interaksi:** Setiap elemen tombol dilengkapi dengan animasi mikro seperti `hover:scale-[1.02] active:scale-[0.97]` agar antarmuka terasa hidup dan interaktif.

---

## Konfigurasi Rute Halaman

| Rute | Tingkat Akses | Deskripsi |
|---|---|---|
| `/` | Publik | Halaman landing pemasaran interaktif dengan navigasi dinamis |
| `/about` | Publik | Halaman tentang kami dan visi platform QLOP |
| `/login` | Publik | Halaman masuk dengan kredensial & tombol Google OAuth |
| `/register` | Publik | Halaman pendaftaran akun baru |
| `/analyze` | **Dilindungi** | Halaman pengunggah file CV PDF dengan drag-and-drop |
| `/analyzing` | **Dilindungi** | Pelacak pemrosesan dokumen CV real-time dengan pembaruan dinamis dari AI |
| `/recommend/:id` | **Dilindungi** | Halaman pemilihan karir target untuk memicu analisis kesenjangan |
| `/history` | **Dilindungi** | Halaman daftar, sortir, dan penghapusan riwayat analisis CV |
| `/history/:id` | **Dilindungi** | Halaman laporan kesiapan kerja interaktif lengkap dengan rekomendasi kursus, pencocokan skill, dan Radar Pivot Karir bertenaga LLM |
