# QLOP
**AI-Driven Skill Gap Analysis & Career Navigation Platform**

---

## Project Description
QLOP is a web-based application designed to bridge the skill gap between new graduates and digital industry requirements. By leveraging Natural Language Processing (NLP) technology, the system automatically extracts skill entities from user Curriculum Vitae (CV) documents, compares them with actual job market trends obtained through web scraping, and provides personalized, objective learning recommendations.

## Tech Stack
This project utilizes a Monorepo architecture with the following technology stacks:
- **Frontend:** React.js, Vite, Tailwind CSS, Axios.
- **Backend:** Node.js, Express.js, PostgreSQL.
- **AI Engine:** Python, FastAPI, TensorFlow.
- **Data Science:** Python, Pandas, BeautifulSoup, Streamlit.

## Repository Structure (Monorepo)
```text
qlop/
├── frontend/             # User Interface (UI/UX)
├── backend/              # Main API Server & Business Logic
├── ai_engine/            # NLP Model Service & AI API
├── data_science/         # Scraping Scripts & Analytical Dashboard
└── docs/                 # Project Documentation & Final Deliverables
```

## Environment Setup Instructions

### Prerequisites
- Node.js (Version 18+)
- Python (Version 3.9+)
- PostgreSQL

### Installation Steps

#### 1. Clone the Repository
```bash
git clone [https://github.com/QLOP-CC26/qlop.git](https://github.com/QLOP-CC26/qlop.git)
cd qlop
```

#### 2. Backend & Frontend Configuration
Navigate to the respective folders (backend/ and frontend/), copy .env.example to .env, and install dependencies:
```bash
npm install
```

#### 3. AI Engine & Data Science Configuration
Navigate to the respective folders (ai_engine/ and data_science/), copy .env.example to .env, create a virtual environment, and install dependencies:
```bash
pip install -r requirements.txt
```

## How to Run the Application

1. **Start AI API:** Within the ai_engine/ folder, run: uvicorn app.main:app --reload
2. **Start Backend:** Within the backend/ folder, run: npm run dev
3. **Start Frontend:** Within the frontend/ folder, run: npm run dev
4. **Start DS Dashboard:** Within the data_science/ folder, run: streamlit run app.py

## Team Members (CC26-PSU101)
- Fauzan Arif Tricahya (Full-Stack Web Developer)
- Wandy Chandra Wijaya (Full-Stack Web Developer)
- Diko Duwi Saputra (Data Scientist)
- Dinaranaya Putri Hutauruk (Data Scientist)
- Husni Abdillah (AI Engineer)
- Gilang Agung Prakoso (AI Engineer)

---
© 2026 QLOP Team. MIT License.
---