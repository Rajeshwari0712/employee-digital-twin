import json, joblib, numpy as np, pandas as pd
from functools import lru_cache
from pathlib import Path
from django.conf import settings
from .features import add_features, TARGET, ID_COL

ART = Path(settings.BASE_DIR) / "artifacts"

@lru_cache(maxsize=1)
def meta():
    return json.loads((ART / "metadata.json").read_text())

@lru_cache(maxsize=8)
def get_model(name):
    return joblib.load(ART / (name.lower().replace(" ", "_") + "_model.pkl"))

@lru_cache(maxsize=1)
def employees():
    return pd.read_csv(ART / "employees.csv")

def to_frame(feats):
    row = {}
    for f in meta()["features"]:
        v = feats.get(f["name"])
        empty = v is None or v == ""
        row[f["name"]] = (np.nan if empty else float(v)) if f["type"] == "number" else (np.nan if empty else v)
    return pd.DataFrame([row])

def predict(feats, model_name=None):
    name = model_name if model_name in meta()["models"] else meta()["best_model"]
    m = get_model(name)
    proba = m.predict_proba(to_frame(feats))[0]
    classes = [str(c) for c in m.classes_]
    i = int(np.argmax(proba))
    return {"model": name, "prediction": classes[i], "confidence": float(proba[i]),
            "probabilities": {c: float(p) for c, p in zip(classes, proba)}}

def engineered(feats):
    d = add_features(to_frame(feats)).iloc[0]
    return {k: (None if pd.isna(d[k]) else round(float(d[k]), 3)) for k in ("Task_Efficiency", "Training_Ratio") if k in d}
