# _legacy — Archived Code

Folder ini berisi kode lama yang sudah **digantikan** oleh unified API (`app.py`).
Tidak ada file di sini yang di-import oleh server yang berjalan sekarang.
Disimpan untuk referensi dan dokumentasi evolusi arsitektur.

## Isi

| File / Folder | Keterangan |
|---|---|
| `main.py` | FastAPI app lama — PDF upload via multipart/form-data |
| `pdf_extractor.py` | Service lama untuk `main.py` — rule-based PDF extraction |
| `cv_schema.py` | Schema Pydantic lama untuk `main.py` (`CvProcessResponse`, dll.) |
| `smoke_test_cv.py` | Script test manual untuk `pdf_extractor.py` |
| `templates/index.html` | UI upload HTML untuk `main.py` |
| `api_recommendation_standalone/app.py` | Standalone FastAPI original dari teman — Model2/3/4 dalam 1 file |
| `api_recommendation_standalone/requirements.txt` | Deps untuk standalone API |
| `app_legacy/` | Re-export shim yang dulu ada di `_app_legacy/` |

## Arsitektur Sekarang

Semua logika di atas sudah diintegrasikan ke:
- `app.py` — FastAPI unified entry point
- `services/ner_service.py` — pengganti `pdf_extractor.py` (NER + regex + sliding window)
- `services/recommendation_service.py` — pengganti endpoint skill gap di standalone
- `services/readiness_service.py` — pengganti readiness score di standalone
- `services/career_pivot_service.py` — tambahan baru (Gemini RAG)
