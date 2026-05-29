# QLOP NER — Data Pipeline

Builds the `kaggle_ready_dataset/` artefacts used by the Kaggle training notebook.
**All preprocessing happens here.** The notebook only loads these files and trains.

## Requirements

```bash
pip install pandas
```

No TensorFlow, PyTorch, or spaCy needed.

## Input data

| File | Location | Notes |
|------|----------|-------|
| `MASTERED_DATA_AI_DROPPED_MISSING.csv` | QLOP Kaggle cache (auto-detected) | Skills + role labels |
| `coursera.csv` | QLOP Kaggle cache | Skill phrases |
| `Skills_ONET.csv` | QLOP Kaggle cache | Tool/skill names |
| `JOBS_WITH_EXTRACTED_SKILLS.csv` | QLOP Kaggle cache | Silver labels (optional) |
| `Entity Recognition in Resumes.json` | **Download manually** (see below) | DataTurks NER ground truth |

The QLOP cache default path is:
`C:/Users/hp/.cache/kagglehub/datasets/husniabdillah/dataset-qlop/versions/3`

### Download DataTurks file

1. Go to https://www.kaggle.com/datasets/dataturks/resume-entities-for-ner
2. Download `Entity Recognition in Resumes.json` (one JSON object per line)
3. Save anywhere; pass the path via `--dataturks-path`

## Run the build

```bash
# Minimal (no DataTurks, no silver — produces vocabulary/gazetteer artefacts only)
python ai_engine/data_pipeline/build_ner_dataset.py

# Full build with DataTurks ground-truth data
python ai_engine/data_pipeline/build_ner_dataset.py \
  --dataturks-path "path/to/Entity Recognition in Resumes.json"

# Full build + silver labels from job descriptions (~500 extra training docs)
python ai_engine/data_pipeline/build_ner_dataset.py \
  --dataturks-path "path/to/Entity Recognition in Resumes.json" \
  --silver

# Custom paths
python ai_engine/data_pipeline/build_ner_dataset.py \
  --qlop-root "C:/path/to/qlop/dataset" \
  --dataturks-path "path/to/Entity Recognition in Resumes.json" \
  --out-dir ai_engine/data_pipeline/kaggle_ready_dataset \
  --silver \
  --silver-max 500
```

The script will log each step and exit with a non-zero code if any quality gate fails.

## Output files (`kaggle_ready_dataset/`)

| File | Description |
|------|-------------|
| `dataturks_resume_entities.jsonl` | DataTurks docs with BIO tags (ground truth only) |
| `ner_train.jsonl` | All training docs (DataTurks + optional silver) |
| `ner_splits.json` | Document-level train/val/test split IDs |
| `qlop_skill_gazetteer.csv` | Merged skill gazetteer (LinkedIn + Coursera + O*NET) |
| `skill_vocab_linkedin.json` | ~582-skill canonical vocabulary (aligns with Model 2/3) |
| `role_labels.json` | 50 user-selectable target roles |
| `normalization_rules.json` | Skill alias map (raw → canonical) |
| `stop_skills.txt` | Noise tokens excluded from vocabulary |
| `dataset_card.md` | Source, license, usage instructions for Kaggle |
| `build_manifest.json` | File hashes, row counts, build timestamp |

Each line in `ner_train.jsonl` is a JSON object:
```json
{"doc_id": "dt_0001", "tokens": ["Python", "developer"], "ner_tags_str": ["B-Skills", "O"], "source": "dataturks"}
```

## Upload to Kaggle

```bash
# 1. Zip the output
cd ai_engine/data_pipeline
Compress-Archive -Path kaggle_ready_dataset -DestinationPath qlop-ner-dataset.zip  # PowerShell
# or: zip -r qlop-ner-dataset.zip kaggle_ready_dataset/                            # bash

# 2. Upload via Kaggle CLI
kaggle datasets create -p kaggle_ready_dataset --dir-mode zip

# 3. Or upload via Kaggle UI
#    → kaggle.com/datasets → New Dataset → upload qlop-ner-dataset.zip
#    → note the dataset slug (e.g. yourusername/qlop-ner-dataset)

# 4. In the training notebook, set:
#    BASE = Path("/kaggle/input/qlop-ner-dataset")
```

## Label schema (25 BIO labels)

Matches `yashpwr/resume-ner-bert-v2`:

```
O
B-Skills  I-Skills
B-Designation  I-Designation
B-Name  I-Name
B-Email Address  I-Email Address
B-Phone  I-Phone
B-Location  I-Location
B-Companies worked at  I-Companies worked at
B-Years of Experience  I-Years of Experience
B-Degree  I-Degree
B-College Name  I-College Name
B-Graduation Year  I-Graduation Year
B-UNKNOWN  I-UNKNOWN
```
