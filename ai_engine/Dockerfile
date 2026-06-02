FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf-cache \
    TRANSFORMERS_CACHE=/opt/hf-cache \
    SENTENCE_TRANSFORMERS_HOME=/opt/hf-cache \
    HF_CACHE_DIR=/opt/hf-cache \
    CUDA_VISIBLE_DEVICES="" \
    TF_CPP_MIN_LOG_LEVEL="3" \
    TF_ENABLE_ONEDNN_OPTS="0" \
    OMP_NUM_THREADS="1" \
    TF_NUM_INTRAOP_THREADS="1" \
    TF_NUM_INTEROP_THREADS="1"

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./

RUN python -m pip install --upgrade pip \
    && pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.6.0+cpu" \
    && pip install -r requirements.txt

# Copy only preload.py first to keep layer cache optimized
COPY preload.py ./

# Preload the Hugging Face models during image build so we don't download them on every cold start.
# This runs as a separate clean python script, preventing any Dockerfile parser bugs!
RUN python preload.py

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]