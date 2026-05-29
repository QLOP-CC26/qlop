# QLOP NER Dataset — kaggle_ready_dataset

Built by `build_ner_dataset.py`. Do **not** edit manually.

## Sources
| File | Source | License |
|------|--------|---------|
| `dataturks_resume_entities.jsonl` | [DataTurks Resume NER](https://dataturks.com/projects/abhishek.narayanan/Entity%20Recognition%20in%20Resumes) | CC0 / public |
| `ner_train.jsonl` | DataTurks + optional silver labels | see above |
| `qlop_skill_gazetteer.csv` | LinkedIn QLOP + Coursera + O*NET | research use |
| `skill_vocab_linkedin.json` | LinkedIn job posts (QLOP dataset) | research use |
| `role_labels.json` | LinkedIn job posts (QLOP dataset) | research use |

## Format
Each line in `*.jsonl`:
```json
{{"doc_id": "dt_0001", "tokens": ["Python", "dev"], "ner_tags_str": ["B-Skills", "O"], "source": "dataturks"}}
```

## Notebook usage
```python
import json
from pathlib import Path

BASE = Path("/kaggle/input/<your-dataset-name>")
train = [json.loads(l) for l in (BASE / "ner_train.jsonl").read_text().splitlines() if l]
splits = json.loads((BASE / "ner_splits.json").read_text())
gazetteer = ...  # pd.read_csv(BASE / "qlop_skill_gazetteer.csv")
vocab_582 = json.loads((BASE / "skill_vocab_linkedin.json").read_text())
roles = json.loads((BASE / "role_labels.json").read_text())
```

## Label schema
25 BIO labels matching `yashpwr/resume-ner-bert-v2`:
O, B-Skills, I-Skills, B-Designation, I-Designation, B-Name, I-Name,
B-Email Address, I-Email Address, B-Phone, I-Phone, B-Location, I-Location,
B-Companies worked at, I-Companies worked at, B-Years of Experience, I-Years of Experience,
B-Degree, I-Degree, B-College Name, I-College Name, B-Graduation Year, I-Graduation Year,
B-UNKNOWN, I-UNKNOWN
