FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf-cache \
    TRANSFORMERS_CACHE=/opt/hf-cache \
    SENTENCE_TRANSFORMERS_HOME=/opt/hf-cache \
    HF_CACHE_DIR=/opt/hf-cache

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./

RUN python -m pip install --upgrade pip \
    && pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.6.0+cpu" \
    && pip install -r requirements.txt

# Preload the Hugging Face models during image build so Railway does not need
# to download them on every cold start.
RUN python - <<'PY'
from pathlib import Path

from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, TFAutoModelForTokenClassification

cache_dir = Path('/opt/hf-cache')
cache_dir.mkdir(parents=True, exist_ok=True)

AutoTokenizer.from_pretrained(
    'microsoft/deberta-v3-base',
    cache_dir=str(cache_dir),
    use_fast=False,
)
base_model = TFAutoModelForTokenClassification.from_pretrained(
    'microsoft/deberta-v3-base',
    from_pt=True,
    num_labels=23,
    ignore_mismatched_sizes=True,
    cache_dir=str(cache_dir),
)
base_model.save_pretrained('/opt/deberta-tf-base')
SentenceTransformer('all-MiniLM-L6-v2', cache_folder=str(cache_dir))
PY

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]