"""
make_notebook.py — generate a clean qlop-ner-cv-extraction.ipynb.
Run once locally; output is committed as the canonical notebook.

Usage:
    python ai_engine/data_pipeline/make_notebook.py
"""
import json, uuid
from pathlib import Path

def cell(cell_type, source, metadata=None):
    c = {
        "cell_type": cell_type,
        "id": str(uuid.uuid4())[:8],
        "metadata": metadata or {},
        "source": source if isinstance(source, list) else source.splitlines(keepends=True),
    }
    if cell_type == "code":
        c["execution_count"] = None
        c["outputs"] = []
    return c

md  = lambda s, **kw: cell("markdown", s, **kw)
cod = lambda s, **kw: cell("code",     s, **kw)

# ─────────────────────────────────────────────────────────────────────────────
CELLS = []

# ── 0: Header ────────────────────────────────────────────────────────────────
CELLS.append(md("""\
# QLOP — Model 1 NER: IT Hard-Skill Extraction

**Team CC26-PSU101 | Capstone Project**

Key facts for this notebook:
- **Input data**: `/kaggle/input/<qlop-ner-dataset>/` (upload from `kaggle_ready_dataset/`)
- **Primary metric**: `val_skills_f1` (seqeval F1 on B-Skills / I-Skills only)
- **Export path**: `/kaggle/working/qlop_ner_model/` (SavedModel + tokenizer + `model_meta.json`)
- **Hardware**: Kaggle T4 ×2 → `MirroredStrategy`; falls back to single GPU / CPU
- **Training**: top-4 BERT layers unfrozen from epoch 1; conservative LR (1e-5); 2× upweight on Skills only; early-stop on `val_skills_f1`
- **Handoff to Model 2/3**: `validated_skills` (list[str]) + `target_role` (str from `role_labels.json`)

| Requirement | Status |
|---|---|
| TF Subclassing / Functional API | ✅ |
| Heavy fine-tune (top-4 BERT layers) | ✅ |
| Custom Loss (`MaskedSparseCCELoss`) | ✅ |
| Custom Callback (`QLOPTrainingCallback`) | ✅ |
| Custom Layer (`ITSkillAttentionHead`) | ✅ |
| Custom Training Loop (`tf.GradientTape`) | ✅ |
| Export SavedModel + `.keras` weights | ✅ |
"""))

# ── 1: Install ────────────────────────────────────────────────────────────────
CELLS.append(cod("""\
import subprocess, sys
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q",
     "transformers==4.40.2", "datasets", "seqeval", "tensorboard", "scikit-learn"],
    check=True,
)
print("deps installed")
"""))

# ── 2: Imports ────────────────────────────────────────────────────────────────
CELLS.append(cod("""\
import os, json, time, datetime, warnings, collections
warnings.filterwarnings("ignore")

import numpy as np
import tensorflow as tf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from transformers import AutoTokenizer, AutoConfig, TFBertForTokenClassification
from datasets import Dataset, DatasetDict
from seqeval.metrics import (
    classification_report,
    f1_score      as seq_f1,
    precision_score as seq_precision,
    recall_score    as seq_recall,
)

print(f"TensorFlow : {tf.__version__}")
print(f"GPU count  : {len(tf.config.list_physical_devices('GPU'))}")
"""))

# ── 3: Strategy ───────────────────────────────────────────────────────────────
CELLS.append(cod("""\
gpus = tf.config.list_physical_devices("GPU")
if len(gpus) >= 2:
    strategy = tf.distribute.MirroredStrategy()
    print(f"MirroredStrategy — {strategy.num_replicas_in_sync} GPUs")
elif len(gpus) == 1:
    strategy = tf.distribute.OneDeviceStrategy("/GPU:0")
    print("Single GPU")
else:
    strategy = tf.distribute.OneDeviceStrategy("/CPU:0")
    print("CPU only")

NUM_REPLICAS = strategy.num_replicas_in_sync
"""))

# ── 4: CFG ────────────────────────────────────────────────────────────────────
CELLS.append(cod("""\
# ── Change BASE_DATASET to match your Kaggle dataset slug ──
BASE_DATASET = "/kaggle/input/qlop-ner-dataset"

CFG = {
    "base_model"       : "yashpwr/resume-ner-bert-v2",
    # CVs average 550 words. 256 truncates skills-section away entirely.
    # 384 fits on T4x2 and covers ~80% of docs without truncation.
    "max_length"       : 384,
    # Docs are split into overlapping word windows so ALL skills are seen.
    "chunk_words"      : 200,          # words per chunk (~300 subwords after BPE)
    "chunk_stride"     : 50,           # word overlap between chunks

    "epochs"           : 5,
    "batch_size"       : 8 * NUM_REPLICAS,   # 8 per replica → 16 total on T4×2
    # Very conservative LRs: pretrained model is 90.87% F1 -- we must NOT destroy it.
    "lr_head"          : 5e-6,         # classifier head LR
    "lr_bert"          : 5e-6,         # BERT backbone LR
    "warmup_ratio"     : 0.1,
    "clipnorm"         : 1.0,
    "dropout_rate"     : 0.1,
    # FIX: separate B-tag vs I-tag weighting to prevent entity spillage.
    # B-Skills=5.0 (detect new skills aggressively), I-Skills=1.5 (penalize chains lightly).
    "b_skill_weight"   : 5.0,
    "i_skill_weight"   : 1.5,
    "unfreeze_epoch"   : 1,            # unfreeze top-4 BERT layers from epoch 1
    "unfreeze_n_layers": 4,
    "chunk_stride_eval": 0,

    "log_dir"          : "/kaggle/working/logs",
    "ckpt_path"        : "/kaggle/working/best_weights.weights.h5",
    "savedmodel_path"  : "/kaggle/working/qlop_ner_model",
    "weights_path"     : "/kaggle/working/qlop_ner_final.weights.h5",

    # Dataset artefact paths (inside BASE_DATASET)
    "train_jsonl"      : f"{BASE_DATASET}/ner_train.jsonl",
    "splits_json"      : f"{BASE_DATASET}/ner_splits.json",
    "vocab_json"       : f"{BASE_DATASET}/skill_vocab_linkedin.json",
    "roles_json"       : f"{BASE_DATASET}/role_labels.json",
    "gazetteer_csv"    : f"{BASE_DATASET}/qlop_skill_gazetteer.csv",
}

os.makedirs(CFG["log_dir"],         exist_ok=True)
os.makedirs(CFG["savedmodel_path"], exist_ok=True)
print("CFG ready")
"""))

# ── 5: Label schema (must be before loss_fn) ──────────────────────────────────
CELLS.append(cod("""\
# ── BIO label schema matching yashpwr/resume-ner-bert-v2
RAW_LABELS = [
    "Name", "Email Address", "Phone", "Location",
    "Companies worked at", "Designation", "Skills",
    "Years of Experience", "Degree", "College Name",
    "Graduation Year", "UNKNOWN",
]
BIO_LABELS = ["O"]
for lbl in RAW_LABELS:
    BIO_LABELS.append(f"B-{lbl}")
    BIO_LABELS.append(f"I-{lbl}")

LOCAL_LABEL2ID = {l: i for i, l in enumerate(BIO_LABELS)}
LOCAL_ID2LABEL = {i: l for l, i in LOCAL_LABEL2ID.items()}
NUM_LABELS_LOCAL = len(BIO_LABELS)

# IT entity types we care most about (used for upweighting and skills F1)
IT_SKILL_ENTITY_TYPES = {
    "Skills", "Designation", "Companies worked at",
    "Degree", "College Name", "Years of Experience",
}
print(f"Local label count: {NUM_LABELS_LOCAL}")
"""))

# ── 6: Load dataset ───────────────────────────────────────────────────────────
CELLS.append(md("## Load Dataset from `kaggle_ready_dataset/`"))

CELLS.append(cod("""\
# ── Load artefacts produced by build_ner_dataset.py ──────────────────────────
# This cell is the ONLY data-loading step; no CSV merging or spaCy preprocessing.

def load_ner_jsonl(path: str) -> list[dict]:
    \"\"\"Load newline-delimited JSON file, each line = one NER document.\"\"\"
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records

# Load training docs
all_records = load_ner_jsonl(CFG["train_jsonl"])
splits      = json.loads(open(CFG["splits_json"], encoding="utf-8").read())
vocab_582   = json.loads(open(CFG["vocab_json"],  encoding="utf-8").read())
roles       = json.loads(open(CFG["roles_json"],  encoding="utf-8").read())

print(f"Total docs   : {len(all_records)}")
print(f"Train ids    : {len(splits['train'])}")
print(f"Val   ids    : {len(splits['val'])}")
print(f"Test  ids    : {len(splits['test'])}")
print(f"Vocab size   : {len(vocab_582)} skills")
print(f"Roles        : {len(roles)}")

# Map doc_id → record for quick lookup
id2record = {r["doc_id"]: r for r in all_records}

def records_by_ids(ids: list[str]) -> list[dict]:
    return [id2record[i] for i in ids if i in id2record]

train_records = records_by_ids(splits["train"])
val_records   = records_by_ids(splits["val"])
test_records  = records_by_ids(splits["test"])
print(f"Effective train/val/test: {len(train_records)} / {len(val_records)} / {len(test_records)}")

# Convert ner_tags_str → ner_tags_int using local schema
# (will be remapped to pretrained schema during tokenisation)
def chunk_records(records: list[dict],
                  max_words: int = 200,
                  stride: int = 50) -> list[dict]:
    """Split long documents into overlapping word-level windows.

    Root-cause fix: CVs average 550 tokens. Without chunking, truncation at
    max_length=384 silently discards skills from the second half of every CV.
    Each chunk becomes an independent training example so the model sees the
    entire document during training.
    """
    chunked = []
    for r in records:
        tokens = r["tokens"]
        tags   = r["ner_tags_str"]
        n      = len(tokens)
        if n == 0:
            continue
        start = 0
        idx   = 0
        while start < n:
            end = min(start + max_words, n)
            chunked.append({
                "tokens"      : tokens[start:end],
                "ner_tags_str": tags[start:end],
                "doc_id"      : f"{r['doc_id']}_c{idx}",
                "source"      : r["source"],
            })
            idx += 1
            if end >= n:
                break
            start = end - stride
    return chunked


def records_to_hf(records: list[dict],
                  apply_chunking: bool = True,
                  stride: int | None = None) -> Dataset:
    if apply_chunking:
        # stride=None falls back to CFG["chunk_stride"] (overlapping, for train)
        # stride=0  -> non-overlapping chunks (for val/test, prevents double-counting)
        effective_stride = CFG["chunk_stride"] if stride is None else stride
        records = chunk_records(
            records,
            max_words=CFG["chunk_words"],
            stride=effective_stride,
        )
    tokens_col   = [r["tokens"]      for r in records]
    ner_tags_col = [
        [LOCAL_LABEL2ID.get(t, 0) for t in r["ner_tags_str"]]
        for r in records
    ]
    return Dataset.from_dict({"tokens": tokens_col, "ner_tags": ner_tags_col})

# Train: overlapping chunks -> more samples, data augmentation effect
# Val/test: non-overlapping chunks (stride=0) -> each entity counted exactly once
train_ds = records_to_hf(train_records, apply_chunking=True, stride=None)
val_ds   = records_to_hf(val_records,   apply_chunking=True, stride=CFG["chunk_stride_eval"])
test_ds  = records_to_hf(test_records,  apply_chunking=True, stride=CFG["chunk_stride_eval"])

raw_datasets = DatasetDict({"train": train_ds, "validation": val_ds, "test": test_ds})
print("\\nHF DatasetDict ready:")
for split, ds in raw_datasets.items():
    print(f"  {split:12s}: {len(ds):,} samples")
"""))

# ── 7: EDA ────────────────────────────────────────────────────────────────────
CELLS.append(md("## EDA"))

CELLS.append(cod("""\
train_split = raw_datasets["train"]

seq_lengths = [len(s) for s in train_split["tokens"]]
print(f"Seq length — mean: {np.mean(seq_lengths):.1f}  "
      f"median: {np.median(seq_lengths):.1f}  "
      f"max: {np.max(seq_lengths) if seq_lengths else 0}  "
      f"p95: {np.percentile(seq_lengths, 95) if seq_lengths else 0:.0f}")

entity_counts = collections.Counter()
for tags in train_split["ner_tags"]:
    for t in tags:
        lbl = LOCAL_ID2LABEL.get(t, "O")
        if lbl != "O" and lbl.startswith("B-"):
            entity_counts[lbl[2:]] += 1

print("\\nEntity counts (train):")
for lbl, cnt in entity_counts.most_common():
    bar = "█" * (cnt // max(1, max(entity_counts.values()) // 30))
    print(f"  {lbl:30s} {cnt:6d}  {bar}")
"""))

# ── 8: Tokenizer & pretrained label alignment ─────────────────────────────────
CELLS.append(md("## Tokenizer & Label Alignment"))

CELLS.append(cod("""\
tokenizer = AutoTokenizer.from_pretrained(CFG["base_model"])
config    = AutoConfig.from_pretrained(CFG["base_model"])

PRETRAINED_ID2LABEL = config.id2label
PRETRAINED_LABEL2ID = {v: k for k, v in PRETRAINED_ID2LABEL.items()}
NUM_LABELS = len(PRETRAINED_ID2LABEL)

# IT skill label ids using pretrained schema (for loss upweighting and skills F1)
IT_SKILL_LABEL_IDS = [
    PRETRAINED_LABEL2ID[lbl]
    for lbl in PRETRAINED_LABEL2ID
    if any(sk in lbl for sk in IT_SKILL_ENTITY_TYPES)
]
SKILLS_LABEL_IDS = [
    PRETRAINED_LABEL2ID[lbl]
    for lbl in PRETRAINED_LABEL2ID
    if "Skills" in lbl   # B-Skills + I-Skills only
]

print(f"Pretrained label count : {NUM_LABELS}")
print(f"IT skill label ids     : {IT_SKILL_LABEL_IDS}")
print(f"Skills-only label ids  : {SKILLS_LABEL_IDS}")
"""))

# ── 9: Tokenize & align ───────────────────────────────────────────────────────
CELLS.append(md("## Tokenize & Align Labels"))

CELLS.append(cod("""\
IGNORE_INDEX = -100

def tokenize_and_align_labels(examples):
    tokenized = tokenizer(
        examples["tokens"],
        truncation=True,
        max_length=CFG["max_length"],
        padding="max_length",
        is_split_into_words=True,
        return_offsets_mapping=False,
    )
    all_labels = []
    for i, ner_tags in enumerate(examples["ner_tags"]):
        word_ids   = tokenized.word_ids(batch_index=i)
        prev_word  = None
        label_ids  = []
        for word_id in word_ids:
            if word_id is None:
                label_ids.append(IGNORE_INDEX)
            elif word_id != prev_word:
                raw_tag = ner_tags[word_id] if word_id < len(ner_tags) else 0
                local_str = LOCAL_ID2LABEL.get(raw_tag, "O")
                remapped  = PRETRAINED_LABEL2ID.get(local_str,
                            PRETRAINED_LABEL2ID.get("O", 0))
                label_ids.append(remapped)
            else:
                label_ids.append(IGNORE_INDEX)
            prev_word = word_id
        all_labels.append(label_ids)
    tokenized["labels"] = all_labels
    return tokenized

print("Tokenising…")
tokenized_datasets = raw_datasets.map(
    tokenize_and_align_labels,
    batched=True,
    remove_columns=raw_datasets["train"].column_names,
)
print("Done. Features:", list(tokenized_datasets["train"].features.keys()))
"""))

# ── 10: tf.data ───────────────────────────────────────────────────────────────
CELLS.append(md("## tf.data Pipeline"))

CELLS.append(cod("""\
def hf_to_tf_dataset(hf_ds, batch_size: int, shuffle: bool = False) -> tf.data.Dataset:
    L = CFG["max_length"]
    def gen():
        for s in hf_ds:
            yield (
                {
                    "input_ids"     : s["input_ids"],
                    "attention_mask": s["attention_mask"],
                    "token_type_ids": s.get("token_type_ids", [0] * L),
                },
                s["labels"],
            )
    sig = (
        {
            "input_ids"     : tf.TensorSpec([L], tf.int32),
            "attention_mask": tf.TensorSpec([L], tf.int32),
            "token_type_ids": tf.TensorSpec([L], tf.int32),
        },
        tf.TensorSpec([L], tf.int32),
    )
    ds = tf.data.Dataset.from_generator(gen, output_signature=sig)
    ds = ds.apply(tf.data.experimental.assert_cardinality(len(hf_ds)))
    if shuffle:
        ds = ds.shuffle(buffer_size=500, seed=42)
    return ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)

BATCH   = CFG["batch_size"]
train_tf = hf_to_tf_dataset(tokenized_datasets["train"],      BATCH, shuffle=True)
val_tf   = hf_to_tf_dataset(tokenized_datasets["validation"], BATCH)
test_tf  = hf_to_tf_dataset(tokenized_datasets["test"],       BATCH)

print(f"train batches: {len(train_tf)}")
print(f"val   batches: {len(val_tf)}")
print(f"test  batches: {len(test_tf)}")
"""))

# ── 11: ITSkillAttentionHead ───────────────────────────────────────────────────
CELLS.append(md("## Model Architecture"))

CELLS.append(cod("""\
class ITSkillAttentionHead(tf.keras.layers.Layer):
    \"\"\"Lightweight residual re-scoring head that amplifies skill-entity logits.

    Architecture: Dense(hidden, gelu) → Dropout → Dense(num_labels) + residual.
    Initialised near-zero so training is stable at the start.
    \"\"\"
    def __init__(self, num_labels: int, hidden_dim: int = 256,
                 dropout_rate: float = 0.1, **kw):
        super().__init__(**kw)
        self.num_labels    = num_labels
        self.dense1        = tf.keras.layers.Dense(hidden_dim, activation="gelu", name="it_d1")
        self.dropout       = tf.keras.layers.Dropout(dropout_rate, name="it_drop")
        # Zero-init: output starts at 0 so residual = identity at epoch 0,
        # preserving pretrained logits until the head has learned useful features.
        self.dense2        = tf.keras.layers.Dense(
            num_labels,
            kernel_initializer="zeros",
            bias_initializer="zeros",
            name="it_d2",
        )
        self.residual_proj = tf.keras.layers.Dense(
            num_labels, use_bias=False,
            kernel_initializer="zeros", name="it_res"
        )

    def call(self, logits, training=False):
        x = self.dense1(logits)
        x = self.dropout(x, training=training)
        x = self.dense2(x)
        return logits + self.residual_proj(logits) + x * 0.1

    def get_config(self):
        cfg = super().get_config()
        cfg.update({"num_labels": self.num_labels,
                    "hidden_dim": self.dense1.units,
                    "dropout_rate": self.dropout.rate})
        return cfg

print("ITSkillAttentionHead defined")
"""))

# ── 12: QLOPNERModel ──────────────────────────────────────────────────────────
CELLS.append(cod("""\
class QLOPNERModel(tf.keras.Model):
    \"\"\"BERT-based NER model with custom skill re-scoring head.

    Wraps TFBertForTokenClassification and adds:
      - Extra Dropout before the classifier head
      - ITSkillAttentionHead for residual logit re-scoring
    Supports staged unfreezing via `set_unfreeze(n)`.
    \"\"\"

    def __init__(self,
                 bert_model,
                 num_labels: int,
                 dropout_rate: float = 0.1,
                 unfreeze_last_n_layers: int = 0,
                 **kwargs):
        super().__init__(**kwargs)
        self.bert_ner      = bert_model
        self.extra_dropout = tf.keras.layers.Dropout(dropout_rate, name="extra_dropout")
        self.it_head       = ITSkillAttentionHead(
            num_labels, hidden_dim=256, dropout_rate=dropout_rate, name="it_skill_head"
        )
        self.num_labels    = num_labels
        self._freeze_backbone(unfreeze_last_n_layers)

    def _freeze_backbone(self, unfreeze_n: int):
        \"\"\"Freeze everything except the top `unfreeze_n` encoder layers.\"\"\"
        self.bert_ner.trainable = True
        self.bert_ner.bert.embeddings.trainable = False
        n_total = len(self.bert_ner.bert.encoder.layer)
        for i, layer in enumerate(self.bert_ner.bert.encoder.layer):
            layer.trainable = (unfreeze_n > 0 and i >= n_total - unfreeze_n)
        trainable   = sum(int(np.prod(v.shape)) for v in self.trainable_variables)
        untrainable = sum(int(np.prod(v.shape)) for v in self.non_trainable_variables)
        print(f"Trainable params: {trainable:,} / {trainable + untrainable:,}  "
              f"(BERT layers unfrozen: {unfreeze_n}/{n_total})")

    def set_unfreeze(self, n: int):
        \"\"\"Call at epoch boundary to progressively unfreeze BERT layers.\"\"\"
        self._freeze_backbone(n)

    def get_config(self):
        \"\"\"Required for SavedModel / .keras serialisation.\"\"\"
        base = super().get_config()
        base.update({
            "num_labels"            : self.num_labels,
            "dropout_rate"          : self.extra_dropout.rate,
            "unfreeze_last_n_layers": 0,
        })
        return base

    @classmethod
    def from_config(cls, config):
        raise NotImplementedError(
            "QLOPNERModel.from_config: rebuild bert_model first, "
            "then call QLOPNERModel(bert_model=..., **config)."
        )

    def call(self, inputs, training=False):
        bert_out = self.bert_ner(
            input_ids      = inputs["input_ids"],
            attention_mask = inputs["attention_mask"],
            token_type_ids = inputs["token_type_ids"],
            training       = training,
        )
        logits = bert_out.logits
        logits = self.extra_dropout(logits, training=training)
        logits = self.it_head(logits, training=training)
        return logits

print("QLOPNERModel defined")
"""))

# ── 13: Load BERT + build model ───────────────────────────────────────────────
CELLS.append(md("## Load Pre-Trained BERT (PyTorch → TF)"))

CELLS.append(cod("""\
import torch
from transformers import BertForTokenClassification

print("Downloading PyTorch weights and converting to TF...")
pt_model = BertForTokenClassification.from_pretrained(
    CFG["base_model"], num_labels=NUM_LABELS, ignore_mismatched_sizes=True
)
LOCAL_MODEL_DIR = "/kaggle/working/temp_pt_model"
pt_model.save_pretrained(LOCAL_MODEL_DIR, safe_serialization=False)
del pt_model
torch.cuda.empty_cache()
print("PyTorch weights saved locally.")

tf.keras.backend.clear_session()

with strategy.scope():
    _bert_base = TFBertForTokenClassification.from_pretrained(
        LOCAL_MODEL_DIR, from_pt=True, num_labels=NUM_LABELS
    )
    print(f"TF port complete (num_labels={NUM_LABELS})")

    # Epoch 1: backbone frozen; unfreeze at epoch CFG["unfreeze_epoch"]
    model = QLOPNERModel(
        bert_model             = _bert_base,
        num_labels             = NUM_LABELS,
        dropout_rate           = CFG["dropout_rate"],
        unfreeze_last_n_layers = 0,    # start frozen
        name                   = "qlop_ner",
    )
"""))

# ── 14: Custom Loss + callback ────────────────────────────────────────────────
CELLS.append(md("## Custom Components"))

CELLS.append(cod("""\
# ── (A) Masked CCE with SEPARATE B-tag / I-tag / O weighting ──────────────────
class MaskedSparseCCELoss(tf.keras.losses.Loss):
    \"\"\"Cross-entropy that ignores IGNORE_INDEX (-100) and applies per-class weights.

    Key insight: B-Skills needs HIGH weight (model must detect skill boundaries),
    but I-Skills needs LOW weight (prevents entity spillage where model chains
    I-Skills forever across punctuation and unrelated text).
    \"\"\"
    def __init__(self, ignore_index=-100, b_skill_ids=None, i_skill_ids=None,
                 b_weight=5.0, i_weight=1.5, **kw):
        super().__init__(reduction=tf.keras.losses.Reduction.NONE, **kw)
        self.ignore_index = ignore_index
        self.b_skill_ids  = b_skill_ids or []
        self.i_skill_ids  = i_skill_ids or []
        self.b_weight     = b_weight
        self.i_weight     = i_weight

    def call(self, y_true, y_pred):
        mask   = tf.cast(tf.not_equal(y_true, self.ignore_index), tf.float32)
        y_safe = tf.where(tf.equal(y_true, self.ignore_index),
                          tf.zeros_like(y_true), y_true)
        n_cls  = tf.shape(y_pred)[-1]
        y_oh   = tf.one_hot(y_safe, depth=n_cls)
        per_tok = tf.keras.losses.categorical_crossentropy(
            y_oh, y_pred, from_logits=True, label_smoothing=0.0
        )
        weights = tf.ones_like(mask)
        if self.b_skill_ids:
            b_ids = tf.constant(self.b_skill_ids, dtype=tf.int32)
            is_b  = tf.reduce_any(
                tf.equal(tf.expand_dims(y_safe, -1), tf.reshape(b_ids, [1, 1, -1])),
                axis=-1)
            weights = tf.where(is_b, tf.fill(tf.shape(mask), self.b_weight), weights)
        if self.i_skill_ids:
            i_ids = tf.constant(self.i_skill_ids, dtype=tf.int32)
            is_i  = tf.reduce_any(
                tf.equal(tf.expand_dims(y_safe, -1), tf.reshape(i_ids, [1, 1, -1])),
                axis=-1)
            weights = tf.where(is_i, tf.fill(tf.shape(mask), self.i_weight), weights)
        per_tok = per_tok * weights
        return tf.reduce_sum(per_tok * mask) / (tf.reduce_sum(mask) + 1e-8)

    def get_config(self):
        cfg = super().get_config()
        cfg.update({
            "ignore_index": self.ignore_index,
            "b_skill_ids": self.b_skill_ids,
            "i_skill_ids": self.i_skill_ids,
            "b_weight": self.b_weight,
            "i_weight": self.i_weight,
        })
        return cfg

B_SKILLS_IDS = [PRETRAINED_LABEL2ID["B-Skills"]]  # [19]
I_SKILLS_IDS = [PRETRAINED_LABEL2ID["I-Skills"]]  # [20]

loss_fn = MaskedSparseCCELoss(
    ignore_index = IGNORE_INDEX,
    b_skill_ids  = B_SKILLS_IDS,
    i_skill_ids  = I_SKILLS_IDS,
    b_weight     = CFG["b_skill_weight"],
    i_weight     = CFG["i_skill_weight"],
    name         = "masked_scce",
)
print(f"MaskedSparseCCELoss ready | B-Skills weight={CFG['b_skill_weight']}, I-Skills weight={CFG['i_skill_weight']}")
"""))

# ── 15: QLOPTrainingCallback ──────────────────────────────────────────────────
CELLS.append(cod("""\
class QLOPTrainingCallback:
    \"\"\"Manual callback for the GradientTape loop.

    Tracks loss, accuracy, and val_skills_f1. Early-stops on val_skills_f1.
    \"\"\"
    BOLD = "\\033[1m"; GREEN = "\\033[92m"; YELLOW = "\\033[93m"
    RED  = "\\033[91m"; CYAN  = "\\033[96m"; RESET  = "\\033[0m"

    def __init__(self, patience: int = 2, min_delta: float = 0.001):
        self.patience      = patience
        self.min_delta     = min_delta
        self.best_val_f1   = -float("inf")
        self.wait          = 0
        self.stop_training = False
        self.history       = {k: [] for k in
                              ("train_loss","val_loss","train_acc","val_acc",
                               "val_f1","val_skills_f1")}

    def on_epoch_begin(self, epoch, total):
        print(f"\\n{self.BOLD}{self.CYAN}{'═'*60}\\n"
              f"  Epoch {epoch+1}/{total}\\n{'═'*60}{self.RESET}")
        self._t0 = time.time()

    def on_step_end(self, step, total, loss, interval=50):
        if (step + 1) % interval == 0 or step == total - 1:
            pct = (step + 1) / total * 100
            bar = "▓" * int(pct / 5) + "░" * (20 - int(pct / 5))
            print(f"\\r  [{bar}] {pct:5.1f}%  step={step+1}/{total}  "
                  f"loss={loss:.4f}", end="", flush=True)

    def on_epoch_end(self, epoch, metrics):
        t = time.time() - self._t0
        for k, v in metrics.items():
            if k in self.history:
                self.history[k].append(v)

        val_sf1 = metrics.get("val_skills_f1", 0.0)
        val_f1  = metrics.get("val_f1", 0.0)
        # Primary: val_skills_f1 when > 0; fallback to val_f1 to avoid premature stops.
        primary_metric = val_sf1 if val_sf1 > 0 else val_f1
        improved = primary_metric > self.best_val_f1 + self.min_delta

        if improved:
            mark = f"{self.GREEN}↑ NEW BEST{self.RESET}"
        elif val_sf1 == 0.0:
            mark = f"{self.YELLOW}(skills_f1=0, watching val_f1){self.RESET}"
        else:
            mark = ""

        print(f"\\n  ⏱ {t:.0f}s  "
              f"train_loss={metrics.get('train_loss',0):.4f}  "
              f"val_loss={metrics.get('val_loss',0):.4f}  "
              f"val_f1={val_f1:.4f}  "
              f"val_skills_f1={val_sf1:.4f}  {mark}")

        if improved:
            self.best_val_f1 = primary_metric
            self.wait = 0
        else:
            self.wait += 1
            print(f"  {self.YELLOW}⚠ No improvement {self.wait}/{self.patience}{self.RESET}")
            if self.wait >= self.patience:
                self.stop_training = True
                print(f"  {self.RED}Early stopping!{self.RESET}")

    def on_train_end(self):
        print(f"\\n{self.BOLD}Best val_skills_f1: {self.best_val_f1:.4f}{self.RESET}")

callback = QLOPTrainingCallback(patience=2)
print("QLOPTrainingCallback ready")
"""))

# ── 16: LR schedule + optimizer ───────────────────────────────────────────────
CELLS.append(md("## Optimizer & LR Schedule"))

CELLS.append(cod("""\
total_steps  = len(train_tf) * CFG["epochs"]
warmup_steps = int(total_steps * CFG["warmup_ratio"])
print(f"Total steps: {total_steps}  Warmup: {warmup_steps}")

class LinearWarmupDecay(tf.keras.optimizers.schedules.LearningRateSchedule):
    \"\"\"Linear warmup then linear decay to zero.\"\"\"\n    def __init__(self, peak_lr, warmup_steps, total_steps, **kw):
        super().__init__(**kw)
        self.peak_lr      = float(peak_lr)
        self.warmup_steps = float(warmup_steps)
        self.total_steps  = float(total_steps)

    def __call__(self, step):
        s      = tf.cast(step, tf.float32)
        warmup = self.peak_lr * (s / max(self.warmup_steps, 1.0))
        decay  = self.peak_lr * tf.maximum(
            0.0, (self.total_steps - s) / max(self.total_steps - self.warmup_steps, 1.0)
        )
        return tf.where(s < self.warmup_steps, warmup, decay)

    def get_config(self):
        return {"peak_lr": self.peak_lr,
                "warmup_steps": self.warmup_steps,
                "total_steps":  self.total_steps}

with strategy.scope():
    lr_schedule = LinearWarmupDecay(
        peak_lr      = CFG["lr_head"],
        warmup_steps = warmup_steps,
        total_steps  = total_steps,
    )
    optimizer = tf.keras.optimizers.Adam(
        learning_rate = lr_schedule,
        clipnorm      = CFG["clipnorm"],
        name          = "adam_qlop",
    )
print("Optimizer ready")
"""))

# ── 17: TensorBoard ───────────────────────────────────────────────────────────
CELLS.append(cod("""\
ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
train_writer = tf.summary.create_file_writer(os.path.join(CFG["log_dir"], "train", ts))
val_writer   = tf.summary.create_file_writer(os.path.join(CFG["log_dir"], "val",   ts))
print("TensorBoard writers ready")
print(f"  %load_ext tensorboard")
print(f"  %tensorboard --logdir {CFG['log_dir']}")
"""))

# ── 18: Metric helpers ────────────────────────────────────────────────────────
CELLS.append(md("## Metric Helpers"))

CELLS.append(cod("""\
def compute_token_accuracy(logits, labels):
    preds   = tf.argmax(logits, axis=-1, output_type=tf.int32)
    mask    = tf.cast(tf.not_equal(labels, IGNORE_INDEX), tf.float32)
    correct = tf.cast(tf.equal(preds, labels), tf.float32) * mask
    return float(tf.reduce_sum(correct) / (tf.reduce_sum(mask) + 1e-8))


def batch_to_seqeval(logits_list, labels_list):
    \"\"\"Convert batches to seqeval string-tag sequences.\"\"\"\n    true_seqs, pred_seqs = [], []
    for logits, labels in zip(logits_list, labels_list):
        pred_ids  = tf.argmax(logits, axis=-1).numpy()
        label_ids = labels.numpy()
        for pred_row, lbl_row in zip(pred_ids, label_ids):
            t_seq, p_seq = [], []
            for p, l in zip(pred_row, lbl_row):
                if l == IGNORE_INDEX:
                    continue
                t_seq.append(PRETRAINED_ID2LABEL.get(int(l), "O"))
                p_seq.append(PRETRAINED_ID2LABEL.get(int(p), "O"))
            true_seqs.append(t_seq)
            pred_seqs.append(p_seq)
    return true_seqs, pred_seqs


def evaluate_seqeval(logits_list, labels_list, verbose=False):
    \"\"\"Full seqeval metrics + skills-only F1 with diagnostic counts.\"\"\"\n    true_seqs, pred_seqs = batch_to_seqeval(logits_list, labels_list)
    f1  = seq_f1(true_seqs,        pred_seqs, zero_division=0)
    pre = seq_precision(true_seqs, pred_seqs, zero_division=0)
    rec = seq_recall(true_seqs,    pred_seqs, zero_division=0)

    # Skills-only F1 — primary training signal
    true_skills = [[t if "Skills" in t else "O" for t in seq] for seq in true_seqs]
    pred_skills = [[t if "Skills" in t else "O" for t in seq] for seq in pred_seqs]
    skills_f1   = seq_f1(true_skills, pred_skills, zero_division=0)

    # Diagnostic: must see B-Skills in both true and pred for F1 > 0
    true_b_skills = sum(t.count("B-Skills") for t in true_seqs)
    pred_b_skills = sum(t.count("B-Skills") for t in pred_seqs)
    print(f"  [skills diag] true B-Skills={true_b_skills}  pred B-Skills={pred_b_skills}")

    if verbose:
        print(classification_report(true_seqs, pred_seqs, zero_division=0))
    return {"f1": f1, "precision": pre, "recall": rec, "skills_f1": skills_f1}


print("Metric helpers ready")
"""))

# ── 19: Model warmup ──────────────────────────────────────────────────────────
CELLS.append(md("## Model Warm-Up & Optimizer Init"))

CELLS.append(cod("""\
L = CFG["max_length"]
with strategy.scope():
    dummy = {
        "input_ids"     : tf.zeros([1, L], tf.int32),
        "attention_mask": tf.zeros([1, L], tf.int32),
        "token_type_ids": tf.zeros([1, L], tf.int32),
    }
    _ = model(dummy, training=False)

    # tf-keras Adam.build() is idempotent: once self.built=True, all subsequent
    # calls are silent no-ops.  The first call MUST include every variable that
    # will ever receive a gradient -- otherwise unfreezing mid-training raises:
    #   KeyError: 'The optimizer cannot recognize variable ...'
    # Fix: temporarily expose all target BERT layers, build, then re-freeze.
    model.set_unfreeze(CFG["unfreeze_n_layers"])   # expose top-4 BERT layers
    optimizer.build(model.trainable_variables)      # build slots for ALL target vars
    model.set_unfreeze(0)                           # re-freeze for staged training start

    n_slots = len([v for v in optimizer.variables if "iteration" not in v.name])
    print(f"Optimizer pre-built -- {n_slots} slot variables registered")
    print("Model warm-up done -- no lazy init during training loop")
"""))

# ── 20: Training loop ─────────────────────────────────────────────────────────
CELLS.append(md("## Custom Training Loop (`tf.GradientTape`)"))

CELLS.append(cod("""\
dist_train_tf = strategy.experimental_distribute_dataset(train_tf)
dist_val_tf   = strategy.experimental_distribute_dataset(val_tf)

def unpack_dist(t):
    return tf.concat(t.values, axis=0) if hasattr(t, "values") else t

def train_step(inputs, labels):
    with tf.GradientTape() as tape:
        logits      = model(inputs, training=True)
        loss        = loss_fn(labels, logits)
        scaled_loss = loss / tf.cast(NUM_REPLICAS, tf.float32)
    grads = tape.gradient(scaled_loss, model.trainable_variables)
    optimizer.apply_gradients(zip(grads, model.trainable_variables))
    return loss, logits

@tf.function(reduce_retracing=True)
def dist_train_step(inputs, labels):
    losses, logits = strategy.run(train_step, args=(inputs, labels))
    return strategy.reduce(tf.distribute.ReduceOp.SUM, losses, axis=None), logits, labels

def val_step(inputs, labels):
    logits = model(inputs, training=False)
    loss   = loss_fn(labels, logits)
    return loss, logits

@tf.function(reduce_retracing=True)
def dist_val_step(inputs, labels):
    losses, logits = strategy.run(val_step, args=(inputs, labels))
    return strategy.reduce(tf.distribute.ReduceOp.SUM, losses, axis=None), logits, labels


global_step = 0
best_val_skills_f1 = -1.0

for epoch in range(CFG["epochs"]):

    # ── Staged unfreezing: unfreeze top-N layers at epoch CFG["unfreeze_epoch"] ──
    if epoch + 1 == CFG["unfreeze_epoch"]:
        model.set_unfreeze(CFG["unfreeze_n_layers"])
        # Rebuild optimizer slots for newly unfrozen BERT variables.
        optimizer.build(model.trainable_variables)
        optimizer.learning_rate = LinearWarmupDecay(
            peak_lr      = CFG["lr_bert"],
            warmup_steps = 0,
            total_steps  = len(train_tf) * (CFG["epochs"] - epoch),
        )
        print(f">>> Epoch {epoch+1}: unfroze top {CFG['unfreeze_n_layers']} BERT layers")

    callback.on_epoch_begin(epoch, CFG["epochs"])

    # ── Train ──
    epoch_t_loss, epoch_t_acc = [], []
    for step, (b_in, b_lbl) in enumerate(dist_train_tf):
        t_loss, t_logits, t_labels = dist_train_step(b_in, b_lbl)
        t_logits_f = unpack_dist(t_logits)
        t_labels_f = unpack_dist(t_labels)
        t_acc      = compute_token_accuracy(t_logits_f, t_labels_f)
        epoch_t_loss.append(float(t_loss))
        epoch_t_acc.append(t_acc)
        with train_writer.as_default():
            tf.summary.scalar("step/loss",     float(t_loss), step=global_step)
            tf.summary.scalar("step/accuracy", t_acc,         step=global_step)
        callback.on_step_end(step, len(train_tf), float(t_loss))
        global_step += 1

    # ── Validate ──
    epoch_v_loss, epoch_v_acc = [], []
    v_logits_list, v_labels_list = [], []
    for b_in, b_lbl in dist_val_tf:
        v_loss, v_logits, v_labels = dist_val_step(b_in, b_lbl)
        v_logits_f = unpack_dist(v_logits)
        v_labels_f = unpack_dist(v_labels)
        epoch_v_loss.append(float(v_loss))
        epoch_v_acc.append(compute_token_accuracy(v_logits_f, v_labels_f))
        v_logits_list.append(v_logits_f)
        v_labels_list.append(v_labels_f)

    mean_tl = float(np.mean(epoch_t_loss))
    mean_ta = float(np.mean(epoch_t_acc))
    mean_vl = float(np.mean(epoch_v_loss))
    mean_va = float(np.mean(epoch_v_acc))

    val_metrics  = evaluate_seqeval(v_logits_list, v_labels_list)
    val_f1       = val_metrics["f1"]
    val_skills_f1 = val_metrics["skills_f1"]

    with val_writer.as_default():
        tf.summary.scalar("epoch/loss",       mean_vl,     step=epoch)
        tf.summary.scalar("epoch/accuracy",   mean_va,     step=epoch)
        tf.summary.scalar("epoch/f1",         val_f1,      step=epoch)
        tf.summary.scalar("epoch/skills_f1",  val_skills_f1, step=epoch)
    val_writer.flush(); train_writer.flush()

    callback.on_epoch_end(epoch, {
        "train_loss": mean_tl, "val_loss": mean_vl,
        "train_acc":  mean_ta, "val_acc":  mean_va,
        "val_f1":     val_f1,  "val_skills_f1": val_skills_f1,
    })

    # ── Save best checkpoint ──
    # Primary: val_skills_f1 when > 0; fallback: val_f1 when skills_f1=0.
    # Strict > so checkpoint is NOT overwritten every epoch when stuck at 0.0.
    ckpt_metric = val_skills_f1 if val_skills_f1 > 0 else val_f1
    if ckpt_metric > best_val_skills_f1:
        best_val_skills_f1 = ckpt_metric
        model.save_weights(CFG["ckpt_path"])
        print(f"  ✓ Best checkpoint saved "
              f"(val_skills_f1={val_skills_f1:.4f}, val_f1={val_f1:.4f})")

    if callback.stop_training:
        break

callback.on_train_end()
"""))

# ── 21: Training history ──────────────────────────────────────────────────────
CELLS.append(cod("""\
history      = callback.history
epochs_ran   = len(history["train_loss"])
ep_ax        = range(1, epochs_ran + 1)

fig, axes = plt.subplots(1, 3, figsize=(16, 4))
axes[0].plot(ep_ax, history["train_loss"], "o-", label="Train", color="#4A90D9")
axes[0].plot(ep_ax, history["val_loss"],   "s--",label="Val",   color="#E8453C")
axes[0].set_title("Loss"); axes[0].set_xlabel("Epoch"); axes[0].legend(); axes[0].grid(alpha=0.3)

axes[1].plot(ep_ax, history["train_acc"], "o-",  label="Train", color="#4A90D9")
axes[1].plot(ep_ax, history["val_acc"],   "s--", label="Val",   color="#E8453C")
axes[1].axhline(0.85, color="green", ls=":", lw=2, label="Target")
axes[1].set_title("Token Accuracy"); axes[1].set_xlabel("Epoch"); axes[1].legend(); axes[1].grid(alpha=0.3)

axes[2].plot(ep_ax, history["val_f1"],       "D-",  color="#7B68EE", label="All entities")
axes[2].plot(ep_ax, history["val_skills_f1"],"^--", color="#E8453C", label="Skills only")
axes[2].axhline(0.85, color="green", ls=":", lw=2, label="Target")
axes[2].set_title("Val seqeval F1"); axes[2].set_xlabel("Epoch"); axes[2].legend(); axes[2].grid(alpha=0.3)

plt.suptitle("QLOP NER — Training History", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig("/kaggle/working/training_history.png", dpi=120, bbox_inches="tight")
plt.show()
print("Training history saved.")
"""))

# ── 22: Test evaluation ───────────────────────────────────────────────────────
CELLS.append(md("## Test Evaluation"))

CELLS.append(cod("""\
# Reload best checkpoint
if os.path.exists(CFG["ckpt_path"]):
    model.load_weights(CFG["ckpt_path"])
    print(f"Best checkpoint loaded from {CFG['ckpt_path']}")

test_logits_list, test_labels_list = [], []
test_losses = []

for b_in, b_lbl in test_tf:
    t_loss, t_logits = val_step(b_in, b_lbl)
    test_logits_list.append(t_logits)
    test_labels_list.append(b_lbl)
    test_losses.append(float(t_loss))

mean_test_loss = float(np.mean(test_losses))
test_metrics   = evaluate_seqeval(test_logits_list, test_labels_list, verbose=True)

print(f"\\n{'═'*50}")
print(f"  Test Loss        : {mean_test_loss:.4f}")
print(f"  seqeval F1       : {test_metrics['f1']:.4f}  "
      f"{'✅' if test_metrics['f1'] >= 0.85 else '❌'} (target ≥ 0.85)")
print(f"  Skills-only F1   : {test_metrics['skills_f1']:.4f}  "
      f"{'✅' if test_metrics['skills_f1'] >= 0.80 else '❌'} (target ≥ 0.80)")
print(f"  Precision / Recall: {test_metrics['precision']:.4f} / {test_metrics['recall']:.4f}")
"""))

# ── 23: Export ────────────────────────────────────────────────────────────────
CELLS.append(md("## Export (SavedModel + Weights + Metadata)"))

CELLS.append(cod("""\
# ── SavedModel
L = CFG["max_length"]
dummy = {
    "input_ids"     : tf.zeros((1, L), tf.int32),
    "attention_mask": tf.ones ((1, L), tf.int32),
    "token_type_ids": tf.zeros((1, L), tf.int32),
}
_ = model(dummy, training=False)
tf.saved_model.save(model, CFG["savedmodel_path"])
print(f"SavedModel → {CFG['savedmodel_path']}")

# ── .keras weights
model.save_weights(CFG["weights_path"])
print(f"Weights    → {CFG['weights_path']}")

# ── Tokenizer
tokenizer.save_pretrained(os.path.join(CFG["savedmodel_path"], "tokenizer"))

# ── model_meta.json
model_meta = {
    "model_name"       : "QLOP NER v1",
    "base_model"       : CFG["base_model"],
    "num_labels"       : NUM_LABELS,
    "max_length"       : CFG["max_length"],
    "id2label"         : {str(k): v for k, v in PRETRAINED_ID2LABEL.items()},
    "label2id"         : {v: str(k) for k, v in PRETRAINED_ID2LABEL.items()},
    "test_f1"          : round(test_metrics["f1"],         4),
    "test_skills_f1"   : round(test_metrics["skills_f1"],  4),
    "test_precision"   : round(test_metrics["precision"],  4),
    "test_recall"      : round(test_metrics["recall"],     4),
    "it_skill_entities": list(IT_SKILL_ENTITY_TYPES),
    "skills_label_ids" : SKILLS_LABEL_IDS,
    "vocab_582_path"   : CFG["vocab_json"],
    "roles_path"       : CFG["roles_json"],
}
meta_path = os.path.join(CFG["savedmodel_path"], "model_meta.json")
with open(meta_path, "w") as f:
    json.dump(model_meta, f, indent=2)
print(f"model_meta.json → {meta_path}")

print("\\nExported files:")
for root, _, files in os.walk(CFG["savedmodel_path"]):
    for fname in files:
        fp = os.path.join(root, fname)
        print(f"  {fp}  ({os.path.getsize(fp)/1e6:.1f} MB)")
"""))

# ── 24: Inference demo + JSON contract ────────────────────────────────────────
CELLS.append(md("""\
## Inference Demo & JSON Output Contract

The cell below shows the production inference flow and the exact JSON that
Module 1 emits for the frontend (Human-in-the-Loop review) and the handoff
payload for Module 2/3.
"""))

CELLS.append(cod("""\
import re

# ── Normalization rules (loaded from artefact) ────────────────────────────────
_norm_rules_path = f\"{BASE_DATASET}/normalization_rules.json\"
_norm_rules = json.loads(open(_norm_rules_path).read()).get("rules", {}) \\
              if os.path.exists(_norm_rules_path) else {}

def normalize_skill(surface: str) -> str:
    s = re.sub(r"\\s+", " ", surface.strip().lower())
    return _norm_rules.get(s, s)

def skill_in_vocab(normalized: str) -> bool:
    return normalized in vocab_582

# ── Inference ─────────────────────────────────────────────────────────────────
def extract_entities(text: str, conf_threshold: float = 0.5) -> dict:
    \"\"\"
    Run NER on raw resume text.
    Returns the Module 1 JSON response (before user validation).

    Output schema:
    {
      "target_role": null,           # always null — user fills via dropdown
      "skills": [
        {
          "surface": "Python",
          "normalized_guess": "python",
          "in_vocab_582": true,
          "confidence": 0.97,
          "risk_level": "low",       # low / medium / high based on confidence
          "review_status": "pending" # pending | accepted | rejected
        }
      ],
      "profile_entities": {
        "name": [...], "designation": [...], "location": [...],
        "companies_worked_at": [...], "degree": [...],
        "college_name": [...], "years_of_experience": [...]
      },
      "model_meta": { "model_name": ..., "max_length": ... }
    }
    \"\"\"
    # Tokenize with chunking for long CVs
    words = text.split()
    chunk_size = CFG["max_length"] - 2   # [CLS] + [SEP]
    overlap    = 32
    all_preds  = {}   # word_idx -> (label, confidence)

    start = 0
    while start < len(words):
        end   = min(start + chunk_size, len(words))
        chunk = words[start:end]

        enc = tokenizer(
            chunk,
            truncation=True,
            max_length=CFG["max_length"],
            padding="max_length",
            is_split_into_words=True,
            return_tensors="tf",
        )
        inputs = {
            "input_ids"     : enc["input_ids"],
            "attention_mask": enc["attention_mask"],
            "token_type_ids": enc.get("token_type_ids",
                                       tf.zeros_like(enc["input_ids"])),
        }
        logits = model(inputs, training=False)[0]          # (seq_len, num_labels)
        probs  = tf.nn.softmax(logits, axis=-1).numpy()
        preds  = np.argmax(probs, axis=-1)
        confs  = np.max(probs, axis=-1)
        wids   = enc.word_ids(batch_index=0)

        prev_wid = None
        for pos, wid in enumerate(wids):
            if wid is None or wid == prev_wid:
                prev_wid = wid
                continue
            abs_idx = start + wid
            label   = PRETRAINED_ID2LABEL.get(int(preds[pos]), "O")
            conf    = float(confs[pos])
            if abs_idx not in all_preds or conf > all_preds[abs_idx][1]:
                all_preds[abs_idx] = (label, conf)
            prev_wid = wid

        if end >= len(words):
            break
        start = end - overlap

    # Aggregate word predictions into spans
    skills     = []
    profile    = collections.defaultdict(list)
    i = 0
    while i < len(words):
        label, conf = all_preds.get(i, ("O", 0.0))
        if label.startswith("B-") and conf >= conf_threshold:
            entity_type = label[2:]
            span_words  = [words[i]]
            span_confs  = [conf]
            j = i + 1
            while j < len(words):
                next_label, next_conf = all_preds.get(j, ("O", 0.0))
                if next_label == f"I-{entity_type}":
                    span_words.append(words[j])
                    span_confs.append(next_conf)
                    j += 1
                else:
                    break
            surface  = " ".join(span_words)
            mean_conf = float(np.mean(span_confs))

            if entity_type == "Skills":
                normed   = normalize_skill(surface)
                in_vocab = skill_in_vocab(normed)
                risk     = "low" if mean_conf >= 0.85 else "medium" if mean_conf >= 0.6 else "high"
                skills.append({
                    "surface"         : surface,
                    "normalized_guess": normed,
                    "in_vocab_582"    : in_vocab,
                    "confidence"      : round(mean_conf, 4),
                    "risk_level"      : risk,
                    "review_status"   : "pending",
                })
            else:
                key = entity_type.lower().replace(" ", "_")
                profile[key].append({"text": surface, "confidence": round(mean_conf, 4)})
            i = j
        else:
            i += 1

    return {
        "target_role"     : None,
        "skills"          : skills,
        "profile_entities": dict(profile),
        "model_meta"      : {
            "model_name": model_meta["model_name"],
            "max_length": model_meta["max_length"],
        },
    }


# ── Demo ──────────────────────────────────────────────────────────────────────
DEMO_TEXT = \"\"\"
John Doe
Email: john.doe@email.com | Phone: +1-555-0100 | Location: San Francisco, CA

Senior Software Engineer at Google (2019–2024)

Skills: Python, TensorFlow, Kubernetes, Docker, React, PostgreSQL, REST API, Git

Education:
  B.Sc Computer Science, Stanford University, 2019
\"\"\"

result = extract_entities(DEMO_TEXT)
print("Module 1 JSON output:")
print(json.dumps(result, indent=2))
"""))

# ── 25: HITL handoff schema ───────────────────────────────────────────────────
CELLS.append(md("""\
## HITL Handoff to Module 2/3

After the user accepts/rejects skills in the frontend, the validated payload
sent to Module 2/3 has this minimal structure:
"""))

CELLS.append(cod("""\
# Simulate user validation: accept all "low" risk, reject "high" risk
for skill in result["skills"]:
    if skill["risk_level"] == "low":
        skill["review_status"] = "accepted"
    elif skill["risk_level"] == "high":
        skill["review_status"] = "rejected"

validated_skills = [
    s["normalized_guess"]
    for s in result["skills"]
    if s["review_status"] == "accepted" and s["in_vocab_582"]
]
rejected_skills  = [s["normalized_guess"] for s in result["skills"]
                    if s["review_status"] == "rejected"]
unmapped         = [s["normalized_guess"] for s in result["skills"]
                    if s["review_status"] == "accepted" and not s["in_vocab_582"]]

# User picks target_role from role_labels.json dropdown
# (hint from profile_entities.designation if available)
designation_hints = [e["text"] for e in result["profile_entities"].get("designation", [])]
print("Designation hints for role dropdown:", designation_hints)

handoff_payload = {
    "target_role"              : "Backend Developer",   # user-selected
    "validated_skills"         : validated_skills,
    "rejected_skills"          : rejected_skills,
    "unmapped_user_added_skills": unmapped,
}
print("\\nHandoff payload to Module 2/3:")
print(json.dumps(handoff_payload, indent=2))
"""))

# ─────────────────────────────────────────────────────────────────────────────
NB = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10.0"},
    },
    "cells": CELLS,
}

out_path = Path(__file__).parent.parent / "notebooks" / "qlop-ner-cv-extraction.ipynb"
out_path.write_text(json.dumps(NB, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"Written {len(CELLS)} cells to {out_path}")
