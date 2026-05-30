# QLOP Backend API

Backend service untuk **QLOP** (Platform Analisis Kesenjangan Keahlian) — sistem yang membantu pengguna menganalisis CV, mengidentifikasi skill gap, dan mendapatkan rekomendasi kursus serta role karier.

## Tech Stack

- **Runtime:** Node.js
- **Framework:** Express.js v5
- **Database:** PostgreSQL (via `pg`)
- **Auth:** JWT (`jsonwebtoken`), Bcrypt (`bcrypt`), Google OAuth (`google-auth-library`)
- **File Upload:** Multer + Cloudinary
- **HTTP Client:** Axios
- **Lainnya:** `dotenv`, `cors`

---

## Struktur Direktori

```
backend/
├── src/
│   ├── config/
│   │   ├── db.js               # Koneksi PostgreSQL + inisialisasi tabel
│   │   └── cloudinary.js       # Konfigurasi Cloudinary
│   ├── controllers/
│   │   ├── authController.js   # Logic register, login, Google OAuth
│   │   └── cvController.js     # Logic analisis CV & rekomendasi
│   ├── middlewares/
│   │   ├── authMiddleware.js   # Verifikasi JWT Bearer Token
│   │   └── uploadMiddleware.js # Multer memoryStorage (field: cv_file)
│   ├── routes/
│   │   ├── authRoutes.js       # /api/auth/*
│   │   └── cvRoutes.js         # /api/cv/*
│   ├── app.js                  # Setup Express, registrasi routes
│   └── server.js               # Entry point, inisialisasi DB & server
├── .env
├── .gitignore
└── package.json
```

---

## Setup & Instalasi

### Prasyarat

- Node.js >= 18
- PostgreSQL >= 14
- Akun [Cloudinary](https://cloudinary.com)
- Google OAuth Client ID ([Google Cloud Console](https://console.cloud.google.com))

### Langkah Instalasi

**1. Clone dan masuk ke direktori backend**
```bash
cd backend
```

**2. Install dependencies**
```bash
npm install
```

**3. Konfigurasi environment variables**

Salin `.env` dan isi dengan nilai yang sesuai:
```bash
cp .env .env.local
```

**4. Buat database PostgreSQL**
```bash
createdb qlop
```

**5. Jalankan server**
```bash
# Development (auto-restart)
npm run start:dev

# Production
npm start
```

> Tabel `users` dan `cv_analyses` akan **otomatis dibuat** saat server pertama kali start.

---

## Environment Variables

| Variable | Keterangan | Contoh |
|---|---|---|
| `PGHOST` | Host PostgreSQL | `localhost` |
| `PGUSER` | Username PostgreSQL | `postgres` |
| `PGPASSWORD` | Password PostgreSQL | `admin123` |
| `PGDATABASE` | Nama database | `qlop` |
| `PGPORT` | Port PostgreSQL | `5432` |
| `HOST` | Host server | `localhost` |
| `PORT` | Port server | `5000` |
| `FRONTEND_URL` | URL frontend (untuk CORS) | `http://localhost:3000` |
| `ACCESS_TOKEN_KEY` | Secret key JWT (min. 32 karakter) | `your_secret_key` |
| `ACCESS_TOKEN_AGE` | Durasi token (detik) | `1800` |
| `GOOGLE_CLIENT_ID` | Client ID Google OAuth | `xxxx.apps.googleusercontent.com` |
| `CLOUDINARY_CLOUD_NAME` | Cloud name Cloudinary | `my_cloud` |
| `CLOUDINARY_API_KEY` | API key Cloudinary | `123456789` |
| `CLOUDINARY_API_SECRET` | API secret Cloudinary | `abcdef123` |
| `AI_API_URL` | Base URL AI Engineer service | `http://localhost:8000` |

---

## API Reference

### Base URL
```
http://localhost:5000
```

### Health Check

```http
GET /
```
```json
{
  "status": "success",
  "message": "QLOP API is running",
  "version": "2.0.0",
  "timestamp": "2026-05-28T12:00:00.000Z"
}
```

---

### Auth

#### Register
```http
POST /api/auth/register
Content-Type: application/json
```
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "secret123"
}
```
**Response `201`:**
```json
{
  "status": "success",
  "message": "Registrasi berhasil.",
  "data": {
    "token": "<jwt_token>",
    "user": { "id": "uuid", "name": "John Doe", "email": "john@example.com" }
  }
}
```

---

#### Login
```http
POST /api/auth/login
Content-Type: application/json
```
```json
{
  "email": "john@example.com",
  "password": "secret123"
}
```
**Response `200`:**
```json
{
  "status": "success",
  "message": "Login berhasil.",
  "data": {
    "token": "<jwt_token>",
    "user": { "id": "uuid", "name": "John Doe", "email": "john@example.com" }
  }
}
```

---

#### Google OAuth
```http
POST /api/auth/google
Content-Type: application/json
```
```json
{
  "id_token": "<google_id_token_dari_frontend>"
}
```
**Response `200`:**
```json
{
  "status": "success",
  "message": "Login dengan Google berhasil.",
  "data": {
    "token": "<jwt_token>",
    "user": { "id": "uuid", "name": "John Doe", "email": "john@example.com" }
  }
}
```

---

### CV Analytics

> Semua endpoint di bawah membutuhkan header:
> ```
> Authorization: Bearer <jwt_token>
> ```

---

#### Analyze CV
```http
POST /api/cv/analyze
Content-Type: multipart/form-data
```

| Field | Tipe | Keterangan |
|---|---|---|
| `cv_file` | File | PDF atau DOCX, maks. 5MB |

**Flow:**
1. File diupload ke Cloudinary, dapat `secure_url`
2. URL dikirim ke AI Engineer `POST /extract`
3. Hasil disimpan ke database

**Response `201`:**
```json
{
  "status": "success",
  "message": "CV berhasil dianalisis.",
  "data": {
    "id": "uuid-analysis",
    "cv_url": "https://res.cloudinary.com/...",
    "profile_entities": {
      "name": "John Doe",
      "email_address": "john@example.com",
      "phone": "+1-555-0100",
      "location": "San Francisco, CA"
    },
    "extracted_skills": [
      { "surface": "TensorFlow", "normalized_guess": "tensorflow", "confidence": 0.8142, "risk_level": "medium" }
    ],
    "created_at": "2026-05-28T12:00:00.000Z"
  }
}
```

---

#### Get Recommendations
```http
PUT /api/cv/recommend/:id
Content-Type: application/json
```
```json
{
  "target_role": "Machine Learning Engineer",
  "skills": [
    { "surface": "TensorFlow", "normalized_guess": "tensorflow", "confidence": 0.8142 }
  ]
}
```

**Flow:**
1. Validasi ownership row
2. Kirim ke AI Engineer `POST /recommend`
3. Simpan `top_skills` dan `recommended_courses` ke database

**Response `200`:**
```json
{
  "status": "success",
  "message": "Rekomendasi berhasil diambil dan disimpan.",
  "data": {
    "id": "uuid-analysis",
    "target_role": "Machine Learning Engineer",
    "top_skills": [
      { "skill_linkedin": "python", "priority_score": 0.9 }
    ],
    "recommended_courses": [
      {
        "name": "Modern Web Development",
        "url": "https://...",
        "match_score": 0.8751,
        "difficulty": "BEGINNER",
        "duration": "THREE_TO_SIX_MONTHS"
      }
    ],
    "updated_at": "2026-05-28T12:05:00.000Z"
  }
}
```

---

#### Get Career Pivot Recommendation
```http
POST /api/cv/career-pivot/:id
```

**Flow:**
1. Ambil data analisis dari database
2. Kirim ke AI Engineer `POST /api/v1/cv/career-pivot`
3. Simpan hasil ke kolom `career_pivot` dan `pivot_metadata`

**Response `200`:**
```json
{
  "status": "success",
  "message": "Analisis career pivot berhasil.",
  "data": {
    "alternative_roles": [],
    "ai_discovered_roles": [],
    "current_role_assessment": {},
    "suggested_certifications": [],
    "universal_advice": ""
  }
}
```

---

#### Get CV History
```http
GET /api/cv/history
```
**Response `200`:**
```json
{
  "status": "success",
  "data": {
    "count": 2,
    "analyses": [ { "id": "...", "cv_url": "...", "created_at": "..." } ]
  }
}
```

---

#### Get CV History by ID
```http
GET /api/cv/history/:id
```
**Response `200`:**
```json
{
  "status": "success",
  "data": {
    "id": "uuid",
    "cv_url": "https://...",
    "profile_entities": {},
    "extracted_skills": [],
    "target_role": "Machine Learning Engineer",
    "top_skills": [],
    "recommended_courses": [],
    "career_pivot": {},
    "created_at": "...",
    "updated_at": "..."
  }
}
```

---

## Skema Database

### Tabel `users`

| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | UUID | Primary key, auto-generated |
| `email` | VARCHAR | Unik, wajib |
| `password` | VARCHAR | Nullable (kosong untuk user OAuth) |
| `google_id` | VARCHAR | Unik, diisi saat login Google |
| `name` | VARCHAR | Nama lengkap |
| `created_at` | TIMESTAMP | Waktu dibuat |
| `updated_at` | TIMESTAMP | Waktu diperbarui |

### Tabel `cv_analyses`

| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | UUID | Primary key, auto-generated |
| `user_id` | UUID | FK ke `users.id` (cascade delete) |
| `cv_url` | VARCHAR | URL file CV di Cloudinary |
| `profile_entities` | JSONB | Profil hasil ekstraksi NER (name, email, dll.) |
| `extracted_skills` | JSONB | Array skill mentah hasil AI `/extract` |
| `target_role` | VARCHAR | Role yang dipilih user |
| `top_skills` | JSONB | Array skill prioritas dari AI `/recommend` |
| `recommended_courses` | JSONB | Array kursus rekomendasi dari AI `/recommend` |
| `career_pivot` | JSONB | Output hasil career pivot dari AI `/career-pivot` |
| `extract_metadata` | JSONB | Metadata hasil ekstraksi CV |
| `analyze_metadata` | JSONB | Metadata hasil analisis skill gap |
| `pivot_metadata` | JSONB | Metadata hasil career pivot |
| `created_at` | TIMESTAMP | Waktu dibuat |
| `updated_at` | TIMESTAMP | Waktu diperbarui |

---

## Integrasi AI Engineer

Backend berfungsi sebagai **orchestrator** — semua logika AI didelegasikan ke AI Engineer service.

| Endpoint Backend | Hit AI Engineer | Payload |
|---|---|---|
| `POST /api/cv/analyze` | `POST {AI_API_URL}/extract` | `{ url }` |
| `PUT /api/cv/recommend/:id` | `POST {AI_API_URL}/recommend` | `{ target_role, skills }` |
| `POST /api/cv/career-pivot/:id` | `POST {AI_API_URL}/api/v1/cv/career-pivot` | `{ profile, target_role, skill_gap, ... }` |

---

## Error Response

Semua error dikembalikan dalam format berikut:

```json
{
  "status": "fail",
  "message": "Pesan error yang deskriptif."
}
```

| Status Code | Keterangan |
|---|---|
| `400` | Bad request / validasi gagal |
| `401` | Unauthorized / token tidak valid |
| `404` | Data tidak ditemukan |
| `409` | Konflik (email sudah terdaftar) |
| `502` | AI Engineer service error |
| `500` | Internal server error |

---

## Scripts

```bash
npm start          # Jalankan server production
npm run start:dev  # Jalankan server development (nodemon)
npm test           # Jalankan unit test (Jest)
```