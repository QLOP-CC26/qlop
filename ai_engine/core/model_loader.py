from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd

from core.config import settings

logger = logging.getLogger("qlop.model_loader")


def _safe_role_filename(role_name: str) -> str:
    return re.sub(r"[\\/]", "_", role_name)


class ModelRegistry:
    """Holds all loaded models & data artefacts. Populated once at startup."""

    def __init__(self) -> None:
        # NER
        self.ner_model = None
        self.tokenizer = None
        self.ner_available: bool = False
        self.ner_label2id: dict[str, int] = {}
        self.ner_id2label: dict[int, str] = {}
        self.skill_taxonomy: dict[str, list[str]] = {}
        self.skill_lookup: dict[str, str] = {}

        # Recommendation
        self.infer3 = None
        self.infer4 = None
        self.skill_to_idx_li: dict[str, int] = {}
        self.idx_to_skill_li: dict[str, str] = {}
        self.n_skills_li: int = 0
        self.skill_to_idx_cr: dict[str, int] = {}
        self.idx_to_skill_cr: dict[str, str] = {}
        self.n_skills_cr: int = 0
        self.linkedin_to_coursera: dict[str, list[str]] = {}
        self.df_coursera: pd.DataFrame | None = None
        self.course_vectors: np.ndarray | None = None
        self.num_courses: int = 0
        self.role_freq: dict[str, dict[str, float]] = {}
        self.role_to_idx: dict[str, int] = {}

        # Readiness
        self.sbert_model = None
        self.job_embeddings: dict[str, np.ndarray] = {}
        self.job_skills_list_all: dict[str, list] = {}

        # Career Pivot
        self.role_centroids: dict[str, np.ndarray] = {}

    # ------------------------------------------------------------------
    # NER
    # ------------------------------------------------------------------

    def load_ner(self) -> None:
        if not settings.ner_weights_path.exists():
            logger.warning("NER weights not found at %s — NER disabled", settings.ner_weights_path)
            self._load_ner_taxonomy()
            return

        try:
            import tensorflow as tf
            # Use tf_keras (Keras 2 backward-compat) to match training environment on Kaggle
            import tf_keras as keras
            from transformers import AutoTokenizer, TFAutoModelForTokenClassification

            with open(settings.ner_config_path, "r", encoding="utf-8") as f:
                model_cfg = json.load(f)

            label_schema = model_cfg.get("label_schema", {})
            self.ner_label2id = {v: int(k) for k, v in label_schema.items()}
            self.ner_id2label = {int(k): v for k, v in label_schema.items()}
            num_labels = model_cfg.get("num_labels", 23)

            self.tokenizer = AutoTokenizer.from_pretrained(str(settings.ner_tokenizer_path))

            # ── Reconstruct QLOPNERModelV2 exactly as trained in the notebook ──

            class ITSkillMultiHeadProjection(keras.layers.Layer):
                def __init__(self, n_labels, proj_size=384, dropout_rate=0.15, **kw):
                    super().__init__(**kw)
                    for head in ("skill", "career", "general"):
                        setattr(self, f"{head}_proj", keras.layers.Dense(proj_size, activation="gelu"))
                        setattr(self, f"{head}_drop", keras.layers.Dropout(dropout_rate))
                        setattr(self, f"{head}_out",  keras.layers.Dense(n_labels))
                    self.gate_dense = keras.layers.Dense(3, activation="softmax")
                    # tf_keras (Keras 2) supports add_weight in __init__
                    self.residual_weight = self.add_weight(
                        name="residual_weight", shape=(1,), initializer="ones", trainable=True)

                def build(self, input_shape):
                    super().build(input_shape)

                def call(self, hidden_states, base_logits, training=False):
                    heads = []
                    for head in ("skill", "career", "general"):
                        h = getattr(self, f"{head}_proj")(hidden_states)
                        h = getattr(self, f"{head}_drop")(h, training=training)
                        h = getattr(self, f"{head}_out")(h)
                        heads.append(h)
                    stacked = tf.stack(heads, axis=2)           # (B, S, 3, L)
                    # gate_dense call must match notebook exactly (output overridden below)
                    gate_input = hidden_states[:, :, :64]
                    _unused = self.gate_dense(
                        tf.reduce_mean(gate_input, axis=-1, keepdims=True))  # builds gate_dense
                    gate_weights = tf.nn.softmax(
                        tf.reduce_sum(stacked, axis=-1), axis=-1)  # (B, S, 3)
                    gate_weights = tf.expand_dims(gate_weights, -1)  # (B, S, 3, 1)
                    combined = tf.reduce_sum(stacked * gate_weights, axis=2)
                    return base_logits + self.residual_weight * combined

            class QLOPNERModelV2(keras.Model):
                def __init__(self, deberta_model, n_labels, dropout_rate=0.15, **kw):
                    super().__init__(**kw)
                    self.deberta = deberta_model
                    self.extra_dropout = keras.layers.Dropout(dropout_rate)
                    self.multi_head = ITSkillMultiHeadProjection(n_labels, dropout_rate=dropout_rate)
                    self.num_labels = n_labels

                def call(self, inputs, training=False):
                    outputs = self.deberta(
                        input_ids=inputs["input_ids"],
                        attention_mask=inputs["attention_mask"],
                        training=training,
                        output_hidden_states=True,
                    )
                    base_logits = outputs.logits
                    hidden = self.extra_dropout(outputs.hidden_states[-1], training=training)
                    return self.multi_head(hidden, base_logits, training=training)

            logger.info("Loading DeBERTa-v3-base from HuggingFace (from_pt=True)...")
            deberta_base = TFAutoModelForTokenClassification.from_pretrained(
                settings.ner_base_model,
                from_pt=True,
                num_labels=num_labels,
                ignore_mismatched_sizes=True,
            )

            model = QLOPNERModelV2(deberta_base, n_labels=num_labels,
                                   dropout_rate=0.10)

            dummy = self.tokenizer(
                "init", return_tensors="tf",
                padding="max_length", max_length=settings.ner_max_length, truncation=True,
            )
            model({"input_ids": dummy["input_ids"],
                   "attention_mask": dummy["attention_mask"]}, training=False)

            # The .weights.h5 file only contains ITSkillMultiHeadProjection weights
            # (DeBERTa base weights come from from_pretrained above)
            import h5py as _h5
            with _h5.File(str(settings.ner_weights_path), "r") as hf:
                mh = model.multi_head
                lg = hf["layers/it_skill_multi_head_projection"]

                for head in ("skill", "career", "general"):
                    getattr(mh, f"{head}_proj").set_weights([
                        lg[f"{head}_proj/vars/0"][()],
                        lg[f"{head}_proj/vars/1"][()],
                    ])
                    getattr(mh, f"{head}_out").set_weights([
                        lg[f"{head}_out/vars/0"][()],
                        lg[f"{head}_out/vars/1"][()],
                    ])

                mh.gate_dense.set_weights([
                    lg["gate_dense/vars/0"][()],
                    lg["gate_dense/vars/1"][()],
                ])
                mh.residual_weight.assign(lg["vars/0"][()])

            self.ner_model = model
            self.ner_available = True
            logger.info("NER model (QLOPNERModelV2) loaded successfully — %d labels", num_labels)

        except ImportError as e:
            logger.error(
                "NER requires transformers>=4.40,<5.0 but got a newer version. "
                "Run: pip install 'transformers>=4.40.0,<5.0.0'  (%s)", e)
            self.ner_available = False
        except Exception:
            logger.exception("Failed to load NER model — falling back to heuristic")
            self.ner_available = False

        self._load_ner_taxonomy()

    def _load_ner_taxonomy(self) -> None:
        if settings.ner_taxonomy_path.exists():
            with open(settings.ner_taxonomy_path, "r", encoding="utf-8") as f:
                self.skill_taxonomy = json.load(f)
            for category, skills in self.skill_taxonomy.items():
                for skill in skills:
                    self.skill_lookup[skill.lower()] = category

    # ------------------------------------------------------------------
    # Recommendation
    # ------------------------------------------------------------------

    def load_recommendation(self) -> None:
        import tensorflow as tf

        data_dir = settings.rec_data_dir

        # ── Model3 (Skill Gap) ──
        pb3 = settings.rec_model3_path / "saved_model.pb"
        if pb3.exists():
            loaded3 = tf.saved_model.load(str(settings.rec_model3_path))
            self.infer3 = loaded3.signatures["serving_default"]
            logger.info("Model3 (skill gap) loaded")
        else:
            logger.warning("Model3 saved_model.pb missing — skill gap will return empty results")

        # ── Model4 (Course Recommendation) ──
        pb4 = settings.rec_model4_path / "saved_model.pb"
        if pb4.exists():
            loaded4 = tf.saved_model.load(str(settings.rec_model4_path))
            self.infer4 = loaded4.signatures["serving_default"]
            logger.info("Model4 (course rec) loaded")
        else:
            logger.warning("Model4 saved_model.pb missing — course recommendations will be empty. "
                           "Run kaggle_train_model4.ipynb on Kaggle and copy the output here.")

        with open(data_dir / "skill_vocab_linkedin.json", "r", encoding="utf-8") as f:
            vocab_li = json.load(f)
        self.skill_to_idx_li = vocab_li["skill_to_idx"]
        self.idx_to_skill_li = vocab_li["idx_to_skill"]
        self.n_skills_li = vocab_li["vocab_size"]

        with open(data_dir / "skill_vocab_coursera.json", "r", encoding="utf-8") as f:
            vocab_cr = json.load(f)
        self.skill_to_idx_cr = vocab_cr["skill_to_idx"]
        self.idx_to_skill_cr = vocab_cr["idx_to_skill"]
        self.n_skills_cr = vocab_cr["vocab_size"]

        with open(data_dir / "linkedin_to_coursera_mapping.json", "r", encoding="utf-8") as f:
            self.linkedin_to_coursera = json.load(f)

        csv_path = data_dir / "coursera_cleaned.csv"
        if csv_path.exists():
            self.df_coursera = pd.read_csv(str(csv_path)).fillna("")
        else:
            logger.warning("coursera_cleaned.csv not found — course recommendations will be empty")
            self.df_coursera = pd.DataFrame()

        npz = np.load(str(data_dir / "synthetic_demand_course_model4.npz"))
        self.course_vectors = npz["course_vectors"]
        self.num_courses = len(self.course_vectors)

        with open(data_dir / "role_freq.json", "r", encoding="utf-8") as f:
            self.role_freq = json.load(f)
        role_list = sorted(self.role_freq.keys())
        self.role_to_idx = {role: i for i, role in enumerate(role_list)}

        logger.info("Recommendation models loaded (Model3 + Model4)")

    # ------------------------------------------------------------------
    # Readiness (SBERT)
    # ------------------------------------------------------------------

    def load_readiness(self) -> None:
        from sentence_transformers import SentenceTransformer

        self.sbert_model = SentenceTransformer("all-MiniLM-L6-v2")

        data_dir = settings.rec_data_dir
        with open(data_dir / "role_job_skills.json", "r", encoding="utf-8") as f:
            role_job_skills = json.load(f)

        emb_dir = data_dir / "embeddings"
        skills_list_path = emb_dir / "job_skills_list_all.json"

        with open(skills_list_path, "r", encoding="utf-8") as f:
            self.job_skills_list_all = json.load(f)

        for role in role_job_skills:
            safe = _safe_role_filename(role)
            emb_path = emb_dir / f"{safe}_job_embeddings.npy"
            if emb_path.exists():
                self.job_embeddings[role] = np.load(str(emb_path))
            else:
                logger.warning("Embedding file missing for role %s — skipping", role)

        logger.info("SBERT + %d role embeddings loaded", len(self.job_embeddings))

    # ------------------------------------------------------------------
    # Career Pivot — precompute role centroids
    # ------------------------------------------------------------------

    def compute_role_centroids(self) -> None:
        for role, emb_matrix in self.job_embeddings.items():
            self.role_centroids[role] = emb_matrix.mean(axis=0).astype(np.float32)
        logger.info("Computed %d role centroids for career pivot RAG", len(self.role_centroids))

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def load_all(self) -> None:
        logger.info("Loading all models ...")
        self.load_ner()
        try:
            self.load_recommendation()
        except Exception:
            logger.exception("load_recommendation failed — recommendation endpoints will return empty results")
        try:
            self.load_readiness()
        except Exception:
            logger.exception("load_readiness failed — readiness score will return 0.0")
        self.compute_role_centroids()
        logger.info("All models loaded (some may be degraded — check warnings above)")


registry = ModelRegistry()
