# QLOP Data Science Component

This directory contains the data scraping pipelines, notebooks for Exploratory Data Analysis (EDA), A/B Testing, and the Streamlit Market Insight Dashboard used to visualize job demand, hiring trends, and learning supply.

---

## Streamlit Market Insight Dashboard

The QLOP dashboard is a modern, high-contrast visual analytics platform built on Streamlit and Plotly to analyze tech industry trends and match curriculum profiles against market realities.

* Live Dashboard: [dashboard-qlop.streamlit.app](https://dashboard-qlop.streamlit.app/)

### How to Run Locally

1. **Setup Environment**: Ensure your virtual environment is active and dependencies are installed.
   ```bash
   pip install -r requirements.txt
   ```
2. **Launch Dashboard**:
   ```bash
   streamlit run dashboard.py
   ```
3. **Dashboard Structure**:
   * **Overview**: Global summaries of job listings, unique skills, remote work proportions, and course distribution. Includes interactive treemaps and area charts of posting trends.
   * **Skill Demand**: Details of top global hard skills, skills required per target role, and semantic heatmaps.
   * **Hiring Trends**: Visualizes recruitment timelines, contract type compositions, and seniority level demands.
   * **Course Supply**: Map of online courses (Coursera) vs. skills demanded by IT recruiters.

---

## Data Scripts & Pipelines

The following Python scripts handle raw data processing, mapping, and cleaning:

* **[clean_roles.py](./scripts/clean_roles.py)**: Cleans scraped job titles, normalizes them into 27 canonical IT target roles, and cleans duplicate strings.
* **[skill_extraction_pipeline.py](./scripts/skill_extraction_pipeline.py)**: Heavy pipeline that processes text fields to extract and filter tech skill vectors using keyword taxonomies and matcher lists.
* **[download_data.py](./scripts/download_data.py)**: Helper script to manage raw data ingestion.

---

## Local Notebooks

* **[EDA_Skill_Gap_Analysis.ipynb](./notebooks/EDA_Skill_Gap_Analysis.ipynb)**: Detailed exploratory analysis on raw scraped datasets mapping the density of tech skills across different roles.
* **[AB_Testing.ipynb](./notebooks/AB_Testing.ipynb)**: Hypothesis testing and metric analysis to validate the significance of recommendations and user readiness score distributions.

---

## Kaggle Research, Notebooks, & Datasets

The core machine learning models in QLOP were researched, modeled, and trained on Kaggle using GPU/TPU instances. Below is a deep analysis of the Kaggle assets used in the development of QLOP:

### 1. Kaggle Notebooks (AI Model Development)

#### [AI 1: DeBERTa-v3 NER CV Extraction](https://www.kaggle.com/code/husniabdillah/qlop-ner-v2-it-skill-extraction-from-cvs)
* **Description**: Contains the training, validation, and optimization code for the Phase 1 CV extraction model.
* **Model Base**: Fine-tuned on `microsoft/deberta-v3-base`.
* **Architecture Details**: Integrates a custom token classification head (`QLOPNERModelV2`) that utilizes a multi-head projection layer and gating mechanics. It maps tokens to BILOU labels for entities like Name, Email, Institution, Designation, Degree, and Skills.
* **Weights**: The resulting token classification head weights (`best_weights.weights.h5`) are deployed in `ai_engine/model_assets/ner/`.

#### [AI 2: Two-Tower Course Recommender & Scorer](https://www.kaggle.com/code/gilangagung/qlop-two-tower-course-matcher-and-gap-analysis)
* **Description**: Focuses on modeling and training the recommendation engines used in Phase 2.
* **Model 3 (Skill Scorer)**: A neural network classifier predicting the priority score of missing skills given user profiles and target role indices.
* **Model 4 (Course Matcher)**: A Two-Tower matching model that maps candidate demand profiles and Coursera course skill vectors to a shared embedding space, optimizing cosine similarity.
* **SavedModels**: Exported as TensorFlow SavedModels (`saved_model.pb`) and deployed in `ai_engine/model_assets/recommendation/`.

#### [AI Synthetic Profile Generator](https://www.kaggle.com/code/husniabdillah/qlop-synthethic-data-for-ai-training)
* **Description**: Script designed to generate synthetic candidate skill profiles and course enrollment patterns.
* **Purpose**: Solves cold-start and data sparsity problems, providing millions of virtual vector profiles to pre-train Model 3 and Model 4 before fine-tuning on real datasets.

---

### 2. Kaggle Datasets (Base Corpora & Annotated Data)

#### [Dataset QLOP (Mastered Job Postings)](https://www.kaggle.com/datasets/husniabdillah/dataset-qlop)
* **Contents**: Scraped jobs dataset containing raw job descriptions, requirements, and tags from major Indonesian job portals (Jobstreet, Kalibrr, etc.).
* **Role**: Represents the demand side of the industry, used to calculate role centroids and baseline skill frequencies.

#### [QLOP NER Dataset](https://www.kaggle.com/datasets/husniabdillah/qlop-ner-dataset)
* **Contents**: Annotated resume tokens labeled with entities (Name, Location, Degree, Company, Skill, etc.).
* **Role**: Used as the direct training and validation corpus for the custom DeBERTa-v3 NER model.

#### [Intelligent Learning Recommendation Dataset](https://www.kaggle.com/datasets/gilangagung/qlop-intelligent-learning-recommendation-dataset)
* **Contents**: Cleaned Coursera courses database, skill dictionaries, LinkedIn-to-Coursera mappings, and synthetic training vectors.
* **Role**: Serves as the training corpus for the Two-Tower matching neural networks.
