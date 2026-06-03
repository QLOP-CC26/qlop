from __future__ import annotations
from pathlib import Path
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings

_BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # --- Security & Documentation ---
    internal_api_key: str = Field(default="", validation_alias=AliasChoices("internal_api_key", "INTERNAL_API_KEY"))
    enable_docs: bool = Field(default=True, validation_alias=AliasChoices("enable_docs", "ENABLE_DOCS"))

    # --- NER paths ---
    ner_weights_path: Path = _BASE_DIR / "model_assets" / "ner" / "best_weights.weights.h5"
    ner_tokenizer_path: Path = _BASE_DIR / "model_assets" / "ner" / "tokenizer"
    ner_config_path: Path = _BASE_DIR / "model_assets" / "ner" / "model_config.json"
    ner_taxonomy_path: Path = _BASE_DIR / "model_assets" / "ner" / "skill_taxonomy.json"

    # --- Recommendation paths ---
    rec_data_dir: Path = _BASE_DIR / "model_assets" / "recommendation"
    rec_skill_gap_priority_scorer_path: Path = _BASE_DIR / "model_assets" / "recommendation" / "skill_priority_scorer_savedmodel"
    rec_course_matching_two_tower_model_path: Path = _BASE_DIR / "model_assets" / "recommendation" / "two_tower_course_model_savedmodel"

    # --- NER model config ---
    ner_base_model: str = Field(default="microsoft/deberta-v3-base", validation_alias=AliasChoices("ner_base_model", "NER_BASE_MODEL"))
    ner_max_length: int = 256
    ner_confidence_threshold: float = 0.5
    ner_sliding_window_size: int = 200
    ner_sliding_window_stride: int = 100

    # --- HuggingFace model cache ---
    # All HuggingFace downloads (DeBERTa base + SBERT) are stored here.
    # Defaults to model_assets/hf_cache/ inside the project so the cache
    # survives restarts and doesn't depend on the OS user home directory.
    # Override with HF_CACHE_DIR=/path/to/shared/cache in .env for shared servers.
    hf_cache_dir: Path = Field(default=_BASE_DIR / "model_assets" / "hf_cache", validation_alias=AliasChoices("hf_cache_dir", "HF_CACHE_DIR"))

    # SBERT model name — change to a larger model if readiness quality needs improvement
    sbert_model_name: str = Field(default="all-MiniLM-L6-v2", validation_alias=AliasChoices("sbert_model_name", "EMBEDDING_MODEL", "embedding_model"))

    # --- LLM Provider Settings (Groq / Gemini) ---
    llm_provider: str = Field(default="gemini", validation_alias=AliasChoices("llm_provider", "LLM_PROVIDER"))

    # Groq (OpenAI-compatible, free tier)
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_max_tokens: int = Field(default=8192, validation_alias=AliasChoices("groq_max_tokens", "GROQ_MAX_TOKENS"))

    # Gemini (Vertex AI with ADC)
    vertex_region: str = Field(default="us-central1", validation_alias=AliasChoices("vertex_region", "VERTEX_REGION"))
    vertex_project_id: str = Field(default="", validation_alias=AliasChoices("vertex_project_id", "VERTEX_PROJECT_ID"))
    gemini_model: str = Field(default="gemini-2.5-flash-lite", validation_alias=AliasChoices("gemini_model", "GEMINI_MODEL"))

    career_pivot_top_k: int = 4

    model_config = {"env_file": str(_BASE_DIR / ".env"), "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()

