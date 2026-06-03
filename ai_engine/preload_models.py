import os
from pathlib import Path
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, TFAutoModelForTokenClassification

# Read environment variables
ner_base_model = os.getenv("NER_BASE_MODEL", "microsoft/deberta-v3-base")
embedding_model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
hf_cache_dir = os.getenv("HF_CACHE_DIR", "/opt/hf-cache")

print(f"Preloading NER model: {ner_base_model}")
print(f"Preloading Embedding model: {embedding_model}")
print(f"Cache directory: {hf_cache_dir}")

cache_dir = Path(hf_cache_dir)
cache_dir.mkdir(parents=True, exist_ok=True)

# Set env vars to ensure HuggingFace uses this cache dir during preloading
os.environ["HF_HOME"] = str(cache_dir)
os.environ["TRANSFORMERS_CACHE"] = str(cache_dir)
os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(cache_dir)
os.environ["HF_CACHE_DIR"] = str(cache_dir)

# 1. Preload and cache tokenizer
print("Loading tokenizer...")
AutoTokenizer.from_pretrained(
    ner_base_model,
    cache_dir=str(cache_dir),
    use_fast=False,
)

# 2. Preload, convert to TF, and cache native TF model
print("Loading TF Model for Token Classification...")
base_model = TFAutoModelForTokenClassification.from_pretrained(
    ner_base_model,
    from_pt=True,
    num_labels=23,
    ignore_mismatched_sizes=True,
    cache_dir=str(cache_dir),
)

# Save the pre-converted TF model weights to a dedicated directory so startup doesn't do from_pt=True conversion
tf_base_path = Path("/opt/deberta-tf-base")
print(f"Saving pre-converted TF weights to {tf_base_path}...")
base_model.save_pretrained(str(tf_base_path))

# 3. Preload SentenceTransformer
print("Loading SentenceTransformer...")
SentenceTransformer(embedding_model, cache_folder=str(cache_dir))

print("Model preloading completed successfully.")
