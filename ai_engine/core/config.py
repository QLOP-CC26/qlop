from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings

_BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # --- NER paths ---
    ner_weights_path: Path = _BASE_DIR / "model_assets" / "ner" / "best_weights.weights.h5"
    ner_tokenizer_path: Path = _BASE_DIR / "model_assets" / "ner" / "tokenizer"
    ner_config_path: Path = _BASE_DIR / "model_assets" / "ner" / "model_config.json"
    ner_taxonomy_path: Path = _BASE_DIR / "model_assets" / "ner" / "skill_taxonomy.json"

    # --- Recommendation paths ---
    rec_data_dir: Path = _BASE_DIR / "model_assets" / "recommendation"
    rec_model3_path: Path = _BASE_DIR / "model_assets" / "recommendation" / "model3_savedmodel"
    rec_model4_path: Path = _BASE_DIR / "model_assets" / "recommendation" / "model4_savedmodel"

    # --- NER model config ---
    ner_base_model: str = "microsoft/deberta-v3-base"
    ner_max_length: int = 256
    ner_confidence_threshold: float = 0.5
    ner_sliding_window_size: int = 200
    ner_sliding_window_stride: int = 100

    # --- HuggingFace model cache ---
    # All HuggingFace downloads (DeBERTa base + SBERT) are stored here.
    # Defaults to model_assets/hf_cache/ inside the project so the cache
    # survives restarts and doesn't depend on the OS user home directory.
    # Override with HF_CACHE_DIR=/path/to/shared/cache in .env for shared servers.
    hf_cache_dir: Path = _BASE_DIR / "model_assets" / "hf_cache"

    # SBERT model name — change to a larger model if readiness quality needs improvement
    sbert_model_name: str = "all-MiniLM-L6-v2"

    # --- Groq (OpenAI-compatible, free tier) ---
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    model_config = {"env_file": str(_BASE_DIR / ".env"), "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
