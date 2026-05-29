"""Inspect existing checkpoint variable names so we can rebuild matching architectures."""
import sys
sys.path.insert(0, "ai_engine")

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import tensorflow as tf

for name, path in [
    ("Model3", "ai_engine/assets/recommendation/tf_models/model3_savedmodel/variables/variables"),
    ("Model4", "ai_engine/assets/recommendation/tf_models/model4_savedmodel/variables/variables"),
]:
    print(f"\n{'='*60}")
    print(f"{name} checkpoint variables:")
    print(f"{'='*60}")
    try:
        ckpt = tf.train.load_checkpoint(path)
        shapes = ckpt.get_variable_to_shape_map()
        dtypes = ckpt.get_variable_to_dtype_map()
        for var_name in sorted(shapes.keys()):
            print(f"  {var_name:60s}  shape={shapes[var_name]}  dtype={dtypes[var_name].name}")
    except Exception as e:
        print(f"  ERROR: {e}")
