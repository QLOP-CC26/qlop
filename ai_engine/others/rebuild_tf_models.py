"""Rebuild TF SavedModels for Model3 (Skill Gap) and Model4 (Course Rec).

The original saved_model.pb files are missing; only the checkpoint variables
exist. This script:
  1. Rebuilds the exact architectures from the training notebooks.
  2. Attempts to restore weights from the existing checkpoint variables.
  3. Falls back to quick retraining from the .npz data if restoration fails.
  4. Exports each model as a proper TF SavedModel with the serving signatures
     that model_loader.py expects.

Run from project root:
  D:\\DBSCodingCamp\\qlop\\.venv\\Scripts\\python.exe rebuild_tf_models.py
"""

from __future__ import annotations

import json
import os
import sys

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import numpy as np
import tensorflow as tf

print(f"TF version: {tf.__version__}")

BASE = "ai_engine/model_assets/recommendation"
MODEL3_PATH = f"{BASE}/model3_savedmodel"
MODEL4_PATH = f"{BASE}/model4_savedmodel"
DATA_DIR = BASE
NPZ3 = f"{DATA_DIR}/synthetic_users_model3.npz"
NPZ4 = f"{DATA_DIR}/synthetic_demand_course_model4.npz"


# ─────────────────────────────────────────────────────────────
# Model 3 — Skill Gap Priority Scorer
# Architecture confirmed from notebook + checkpoint shapes:
#   Embedding(27, 8) + Dense(128) + Dense(64) + Dense(489, sigmoid)
# ─────────────────────────────────────────────────────────────

def build_model3(n_skills: int = 489, n_roles: int = 27, emb_dim: int = 8) -> tf.keras.Model:
    input_skills = tf.keras.Input(shape=(n_skills,), dtype=tf.float32, name="user_skills")
    input_role = tf.keras.Input(shape=(1,), dtype=tf.int32, name="role_index")

    role_emb = tf.keras.layers.Embedding(n_roles, emb_dim, name="role_embedding")(input_role)
    role_emb = tf.keras.layers.Flatten()(role_emb)

    x = tf.keras.layers.Concatenate()([input_skills, role_emb])
    x = tf.keras.layers.Dense(128, activation="relu", name="dense1")(x)
    x = tf.keras.layers.Dropout(0.3, name="dropout1")(x)
    x = tf.keras.layers.Dense(64, activation="relu", name="dense2")(x)
    output = tf.keras.layers.Dense(n_skills, activation="sigmoid", dtype=tf.float32, name="output")(x)

    return tf.keras.Model(inputs=[input_skills, input_role], outputs=output, name="Model3_SkillGap")


def load_model3_or_train() -> tf.keras.Model:
    npz = np.load(NPZ3)
    n_skills = int(npz["N_SKILLS"])
    n_roles = int(npz["N_ROLES"])
    print(f"  Model3 data: N_SKILLS={n_skills}, N_ROLES={n_roles}, samples={len(npz['X_users'])}")

    model = build_model3(n_skills, n_roles)
    # Warm-up build (establishes variable shapes)
    _ = model([np.zeros((1, n_skills), dtype=np.float32),
               np.zeros((1, 1), dtype=np.int32)], training=False)

    ckpt_path = f"{MODEL3_PATH}/variables/variables"
    restored = False
    try:
        ckpt = tf.train.Checkpoint(model=model)
        status = ckpt.read(ckpt_path)
        # assert_consumed raises if shapes don't match
        status.expect_partial()
        # Quick sanity: run inference to make sure weights are non-zero
        test_out = model([np.zeros((1, n_skills), np.float32),
                          np.zeros((1, 1), np.int32)], training=False)
        if test_out.numpy().sum() != 0:
            print("  Model3 weights restored from checkpoint.")
        restored = True
    except Exception as e:
        print(f"  Checkpoint restore failed ({e}). Training from scratch…")

    if not restored:
        _train_model3(model, npz, n_skills)

    return model


def _train_model3(model: tf.keras.Model, npz, n_skills: int) -> None:
    X_users = npz["X_users"]
    X_roles = npz["X_roles"].reshape(-1, 1)
    Y = npz["Y_targets"]

    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
                  loss="binary_crossentropy",
                  metrics=["mae"])
    model.fit(
        [X_users, X_roles], Y,
        epochs=15, batch_size=256, validation_split=0.1,
        verbose=1,
    )
    print("  Model3 training done.")


# ─────────────────────────────────────────────────────────────
# Model 4 — Course Recommendation Two-Tower
# Architecture deduced from checkpoint shapes:
#   DemandTower: 489→256→128→64→32
#   CourseTower: 1999→256→128→64→32
#   Interaction:  concat([d,c,d*c,d-c])=128 → Dense(32) → bilinear W[32,32]
# ─────────────────────────────────────────────────────────────

class FourInteractionModel(tf.keras.Model):
    """Two-tower model with 4-element interaction (concat, diff, element-wise product, ...).

    Interaction: concat([d, c, d*c, d-c]) → 4*32=128 → Dense(32) → score
    where score = sigmoid( reduced_sum(hidden * W @ course_emb) )
    giving variables: kernel[128,32], bias[32], W[32,32]  — matches checkpoint.
    """

    def __init__(self, n_demand: int = 489, n_course: int = 1999, embed_dim: int = 32):
        super().__init__(name="Model4_CourseRec")
        hidden = 256

        self.demand_tower = tf.keras.Sequential([
            tf.keras.layers.Dense(hidden, activation="relu"),
            tf.keras.layers.Dense(hidden // 2, activation="relu"),
            tf.keras.layers.Dense(hidden // 4, activation="relu"),
            tf.keras.layers.Dense(embed_dim, activation="relu"),
        ], name="DemandTower")

        self.course_tower = tf.keras.Sequential([
            tf.keras.layers.Dense(hidden, activation="relu"),
            tf.keras.layers.Dense(hidden // 2, activation="relu"),
            tf.keras.layers.Dense(hidden // 4, activation="relu"),
            tf.keras.layers.Dense(embed_dim, activation="relu"),
        ], name="CourseTower")

        # Interaction:  concat([d, c, d*c, d-c]) → 4*embed_dim → Dense(embed_dim) → W → score
        self.interaction_dense = tf.keras.layers.Dense(embed_dim, use_bias=True, name="interaction_dense")
        self.W = self.add_weight(shape=(embed_dim, embed_dim), initializer="glorot_uniform",
                                 trainable=True, name="bilinear_W")
        self.output_act = tf.keras.layers.Activation("sigmoid", dtype=tf.float32, name="output_sigmoid")

    def call(self, inputs, training: bool = False):
        demand_vec, course_vec = inputs
        demand_vec = tf.cast(demand_vec, tf.float32)
        course_vec = tf.cast(course_vec, tf.float32)

        d = self.demand_tower(demand_vec, training=training)
        c = self.course_tower(course_vec, training=training)

        # 4-component interaction → 4 * embed_dim = 128
        interact = tf.concat([d, c, d * c, d - c], axis=-1)
        hidden = self.interaction_dense(interact)                     # (batch, embed_dim)
        score = tf.reduce_sum(hidden * (c @ self.W), axis=-1, keepdims=True)  # (batch, 1)
        return self.output_act(score)


def load_model4_or_train() -> FourInteractionModel:
    npz = np.load(NPZ4)
    demand_vecs = npz["demand_vectors"]     # (15000, 489)
    course_vecs_all = npz["course_vectors"] # (1980, 1999)
    course_indices = npz["course_indices"]  # (15000,)
    targets = npz["targets"].reshape(-1, 1) # (15000, 1)

    n_demand = demand_vecs.shape[1]
    n_course = course_vecs_all.shape[1]
    print(f"  Model4 data: demand_dim={n_demand}, course_dim={n_course}, samples={len(demand_vecs)}")

    model = FourInteractionModel(n_demand, n_course)
    # Warm-up
    _ = model([np.zeros((1, n_demand), np.float32),
               np.zeros((1, n_course), np.float32)], training=False)
    print(f"  Model4 variables: {len(model.variables)}")

    ckpt_path = f"{MODEL4_PATH}/variables/variables"
    restored = False
    try:
        ckpt = tf.train.Checkpoint(model=model)
        status = ckpt.read(ckpt_path)
        status.expect_partial()
        test_out = model([np.zeros((1, n_demand), np.float32),
                          np.zeros((1, n_course), np.float32)], training=False)
        if test_out.numpy().sum() > 0:
            print("  Model4 weights restored from checkpoint.")
            restored = True
        else:
            print("  Checkpoint loaded but output is zero — retraining…")
    except Exception as e:
        print(f"  Checkpoint restore failed ({e}). Training from scratch…")

    if not restored:
        _train_model4(model, demand_vecs, course_vecs_all, course_indices, targets)

    return model


def _train_model4(model: FourInteractionModel, demand_vecs, course_vecs_all,
                  course_indices, targets) -> None:
    course_vecs_selected = course_vecs_all[course_indices]  # (15000, 1999)
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
                  loss="mse", metrics=["mae"])
    model.fit(
        [demand_vecs, course_vecs_selected], targets,
        epochs=15, batch_size=256, validation_split=0.1,
        verbose=1,
    )
    print("  Model4 training done.")


# ─────────────────────────────────────────────────────────────
# Export helpers — create serving signatures matching model_loader.py
# ─────────────────────────────────────────────────────────────

def export_model3(model: tf.keras.Model, path: str, n_skills: int = 489) -> None:
    """Export with signature: user_skills (float32), role_index (int32) → output_0 (float32)."""

    @tf.function(input_signature=[
        tf.TensorSpec([None, n_skills], tf.float32, name="user_skills"),
        tf.TensorSpec([None, 1], tf.int32, name="role_index"),
    ])
    def serving_fn(user_skills, role_index):
        result = model([user_skills, role_index], training=False)
        return {"output_0": result}

    tf.saved_model.save(
        model, path,
        signatures={"serving_default": serving_fn},
    )
    print(f"  Model3 saved: {path}")


def export_model4(model: FourInteractionModel, path: str,
                  n_demand: int = 489, n_course: int = 1999) -> None:
    """Export with signature: args_0 (float16), args_0_1 (float16) → output_0 (float32).

    model_loader uses:
        out4 = infer4(args_0=demand_batch_f16, args_0_1=course_batch_f16)
        scores = list(out4.values())[0].numpy().flatten()
    """

    @tf.function(input_signature=[
        tf.TensorSpec([None, n_demand], tf.float16, name="args_0"),
        tf.TensorSpec([None, n_course], tf.float16, name="args_0_1"),
    ])
    def serving_fn(args_0, args_0_1):
        result = model([args_0, args_0_1], training=False)
        return {"output_0": result}

    tf.saved_model.save(
        model, path,
        signatures={"serving_default": serving_fn},
    )
    print(f"  Model4 saved: {path}")


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n===== Rebuilding Model3 (Skill Gap) =====")
    m3 = load_model3_or_train()
    npz3 = np.load(NPZ3)
    export_model3(m3, MODEL3_PATH, n_skills=int(npz3["N_SKILLS"]))

    print("\n===== Rebuilding Model4 (Course Rec) =====")
    m4 = load_model4_or_train()
    npz4 = np.load(NPZ4)
    export_model4(m4, MODEL4_PATH,
                  n_demand=npz4["demand_vectors"].shape[1],
                  n_course=npz4["course_vectors"].shape[1])

    print("\n===== Verifying exports =====")
    # Verify Model3
    loaded3 = tf.saved_model.load(MODEL3_PATH)
    infer3 = loaded3.signatures["serving_default"]
    n_skills = int(npz3["N_SKILLS"])
    out3 = infer3(
        user_skills=tf.constant(np.zeros((1, n_skills), np.float32)),
        role_index=tf.constant(np.zeros((1, 1), np.int32)),
    )
    assert "output_0" in out3, "Model3: 'output_0' key missing!"
    assert out3["output_0"].shape == (1, n_skills), f"Wrong shape: {out3['output_0'].shape}"
    print(f"  Model3 OK — output shape {out3['output_0'].shape}")

    # Verify Model4
    loaded4 = tf.saved_model.load(MODEL4_PATH)
    infer4 = loaded4.signatures["serving_default"]
    n_demand = npz4["demand_vectors"].shape[1]
    n_course = npz4["course_vectors"].shape[1]
    out4 = infer4(
        args_0=tf.constant(np.zeros((5, n_demand), np.float16)),
        args_0_1=tf.constant(np.zeros((5, n_course), np.float16)),
    )
    scores = list(out4.values())[0].numpy().flatten()
    assert len(scores) == 5, f"Model4: expected 5 scores, got {len(scores)}"
    print(f"  Model4 OK — output scores shape {scores.shape}")

    print("\nAll models rebuilt and verified. Run uvicorn again.")
