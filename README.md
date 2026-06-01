<div align="center">
  <img src="frontend/src/assets/logo.png" alt="QLOP Logo" width="130" />
  <h1>QLOP</h1>
  <p><strong>AI-Driven Skill Gap Analysis & Career Navigation Platform</strong></p>
  <p>Bridge the gap between talent and opportunity — powered by NLP, ML, and Generative AI.</p>
</div>

---

<div align="center">

### Frontend
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)
![Axios](https://img.shields.io/badge/Axios-5A29E4?style=for-the-badge&logo=axios&logoColor=white)

### Backend
![Node.js](https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=nodedotjs&logoColor=white)
![Express.js](https://img.shields.io/badge/Express.js-000000?style=for-the-badge&logo=express&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-black?style=for-the-badge&logo=JSON%20web%20tokens)

### AI Engine
![Python](https://img.shields.io/badge/Python_3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)
![HuggingFace](https://img.shields.io/badge/HuggingFace-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)
![Groq](https://img.shields.io/badge/Groq_Llama_3.3-F54F29?style=for-the-badge&logo=groq&logoColor=white)

### Data Science
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-4-green?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)

### Infrastructure
![Cloudinary](https://img.shields.io/badge/Cloudinary-3448C5?style=for-the-badge&logo=cloudinary&logoColor=white)
![Git](https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white)

</div>

---

## Project Description

QLOP is a web-based application designed to bridge the skill gap between new graduates and digital industry requirements. By leveraging Natural Language Processing (NLP) technology, the system automatically extracts skill entities from user Curriculum Vitae (CV) documents, compares them with actual job market trends obtained through web scraping, and provides personalized, objective learning recommendations.

The AI pipeline runs in **three phases**:
1. **Extract** — DeBERTa-v3 NER model parses a CV PDF into a structured profile
2. **Analyze** — TensorFlow models compute skill gap, course recommendations, and SBERT readiness score in parallel
3. **Career Pivot Radar** — SBERT RAG + Groq Llama 3.3 70B (3-turn chain-of-thought) suggests personalized career paths

## Repository Structure (Monorepo)

```text
qlop/
├── frontend/             # User Interface (React + Vite + Tailwind)
├── backend/              # Main API Server & Business Logic (Express.js)
├── ai_engine/            # NLP Model Service & AI API (FastAPI)
├── data_science/         # Scraping Scripts & Analytical Dashboard (Streamlit)
└── docs/                 # Project Documentation & Final Deliverables
```

## Environment Setup Instructions

### Prerequisites

- Node.js (Version 18+)
- Python (Version 3.10 or 3.11)
- PostgreSQL

### Installation Steps

#### 1. Clone the Repository

```bash
git clone https://github.com/QLOP-CC26/qlop.git
cd qlop
```

#### 2. Backend & Frontend Configuration

Navigate to the respective folders (`backend/` and `frontend/`), copy `.env.example` to `.env`, and install dependencies:

```bash
npm install
```

#### 3. AI Engine & Data Science Configuration

Navigate to the respective folders (`ai_engine/` and `data_science/`), copy `.env.example` to `.env`, create a virtual environment, and install dependencies:

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## How to Run the Application

| Service | Directory | Command |
|---------|-----------|---------|
| AI Engine | `ai_engine/` | `uvicorn app:app --reload` |
| Backend | `backend/` | `npm run dev` |
| Frontend | `frontend/` | `npm run dev` |
| DS Dashboard | `data_science/` | `streamlit run app.py` |

> **Start order:** AI Engine → Backend → Frontend

## Production Deployment

Recommended split for production:

| Service | Recommended host | Notes |
|---------|------------------|-------|
| AI Engine | Railway Docker service | Best for TensorFlow + Hugging Face model loading |
| Backend | Railway or VPS | Must point `AI_API_URL` to the AI Engine public URL |
| Frontend | Netlify / Vercel / static hosting | Set `VITE_API_URL` to the backend public URL |
| Database | Managed PostgreSQL | Use a hosted Postgres for reliability |

If you deploy AI Engine separately, the backend does not need private network access. It only needs the public `AI_API_URL` value. For a low-RAM VPS, do not host the AI Engine there unless you are willing to accept slow startup and possible memory pressure.

## Team Members (CC26-PSU101)

| Name | Role |
|------|------|
| Fauzan Arif Tricahya | Full-Stack Web Developer |
| Wandy Chandra Wijaya | Full-Stack Web Developer |
| Diko Duwi Saputra | Data Scientist |
| Dinaranaya Putri Hutauruk | Data Scientist |
| Husni Abdillah | AI Engineer |
| Gilang Agung Prakoso | AI Engineer |

---

<div align="center">
  © 2026 QLOP Team · MIT License · DBS Foundation Coding Camp CC26-PSU101
</div>
