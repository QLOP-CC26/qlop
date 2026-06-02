from pathlib import Path

from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, TFAutoModelForTokenClassification

cache_dir = Path('/opt/hf-cache')
cache_dir.mkdir(parents=True, exist_ok=True)

# 1. Preload and save tokenizer
AutoTokenizer.from_pretrained(
    'microsoft/deberta-v3-base',
    cache_dir=str(cache_dir),
    use_fast=False,
)

# 2. Preload, convert to TF, and save native TF model
base_model = TFAutoModelForTokenClassification.from_pretrained(
    'microsoft/deberta-v3-base',
    from_pt=True,
    num_labels=23,
    ignore_mismatched_sizes=True,
    cache_dir=str(cache_dir),
)
base_model.save_pretrained('/opt/deberta-tf-base')

# 3. Preload SentenceTransformer
SentenceTransformer('all-MiniLM-L6-v2', cache_folder=str(cache_dir))
