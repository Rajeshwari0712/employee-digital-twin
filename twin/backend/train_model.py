"""Run:  python train_model.py [path/to/data.csv]
Does: data understanding -> preprocessing -> EDA stats -> feature engineering -> train 3 models
-> compare -> save models + metadata.json (used by the Django API and dashboard)."""
import sys, json, joblib, numpy as np, pandas as pd
from pathlib import Path
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder, FunctionTransformer
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from api.features import add_features, FeatureWeighter, KNN_WEIGHTS, TARGET, ID_COL

CSV = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE.parent / "data" / "06_employee_productivity_digital_twin.csv"
ART = BASE / "artifacts"; ART.mkdir(exist_ok=True)

def clean(o):  # make JSON-safe (NaN -> None, numpy -> python)
    if isinstance(o, dict): return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    if isinstance(o, np.generic): o = o.item()
    if isinstance(o, float) and (np.isnan(o) or np.isinf(o)): return None
    return o

# ---------- 1. Data understanding ----------
df = pd.read_csv(CSV)
print(f"Loaded {CSV.name}: {df.shape[0]} rows x {df.shape[1]} cols")
eda = {"rows": len(df), "columns": df.shape[1], "dtypes": df.dtypes.astype(str).to_dict(),
       "missing": df.isna().sum().to_dict(), "duplicates": int(df.duplicated().sum()),
       "describe": df.describe().round(3).to_dict()}

# ---------- 2. Preprocessing ----------
df = df.drop_duplicates().dropna(subset=[TARGET]).reset_index(drop=True)
num_cols = [c for c in df.select_dtypes("number").columns if c != ID_COL]
invalid = 0
for c in num_cols:                       # invalid values -> NaN (imputed inside the pipeline)
    m = df[c] < 0; invalid += int(m.sum()); df.loc[m, c] = np.nan
if "Attendance" in df:
    m = df["Attendance"] > 100; invalid += int(m.sum()); df.loc[m, "Attendance"] = np.nan
eda["invalid_values_fixed"] = invalid
eda["outliers_iqr"] = {}
for c in num_cols:
    q1, q3 = df[c].quantile([.25, .75]); i = q3 - q1
    eda["outliers_iqr"][c] = int(((df[c] < q1 - 1.5 * i) | (df[c] > q3 + 1.5 * i)).sum())
eda["class_distribution"] = df[TARGET].value_counts().to_dict()
eda["correlation"] = df[num_cols].corr().round(2).to_dict()
eda["hist"] = {}
for c in num_cols:
    cnt, edges = np.histogram(df[c].dropna(), bins=10)
    eda["hist"][c] = {"labels": [f"{edges[i]:.1f}" for i in range(10)], "counts": cnt.tolist()}
df.to_csv(ART / "employees.csv", index=False)

# ---------- 3. Features / split ----------
X = df.drop(columns=[c for c in [ID_COL, TARGET] if c in df.columns]); y = df[TARGET]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

def make_pre():
    num = Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())])
    cat = Pipeline([("imp", SimpleImputer(strategy="most_frequent")), ("oh", OneHotEncoder(handle_unknown="ignore", sparse_output=False))])
    ct = ColumnTransformer([("num", num, make_column_selector(dtype_include=np.number)),
                            ("cat", cat, make_column_selector(dtype_exclude=np.number))])
    return ct.set_output(transform="pandas")

def pipe(clf, weighted=False):
    steps = [("fe", FunctionTransformer(add_features)), ("pre", make_pre())]
    if weighted: steps.append(("weights", FeatureWeighter(KNN_WEIGHTS)))
    return Pipeline(steps + [("clf", clf)])

models = {
    "KNN": pipe(KNeighborsClassifier(n_neighbors=5), weighted=True),
    "Random Forest": pipe(RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced")),
    "Decision Tree": pipe(DecisionTreeClassifier(max_depth=5, random_state=42, class_weight="balanced")),
}

# ---------- 4. Train + compare ----------
labels = sorted(y.unique()); rows = []; cms = {}
for name, m in models.items():
    m.fit(X_train, y_train); p = m.predict(X_test)
    rows.append({"Model": name, "Accuracy": accuracy_score(y_test, p),
                 "Macro Precision": precision_score(y_test, p, average="macro", zero_division=0),
                 "Macro Recall": recall_score(y_test, p, average="macro", zero_division=0),
                 "Macro F1": f1_score(y_test, p, average="macro", zero_division=0),
                 "Weighted F1": f1_score(y_test, p, average="weighted", zero_division=0)})
    cms[name] = confusion_matrix(y_test, p, labels=labels).tolist()
    joblib.dump(m, ART / (name.lower().replace(" ", "_") + "_model.pkl"))
res = pd.DataFrame(rows).sort_values("Macro F1", ascending=False)
print(res.round(4).to_string(index=False))
best = res.iloc[0]["Model"]; print("Best model:", best)
joblib.dump(models[best], ART / "best_model.pkl")

rf = models["Random Forest"]
names = [n.split("__", 1)[-1] for n in rf.named_steps["pre"].get_feature_names_out()]
imp = sorted(zip(names, rf.named_steps["clf"].feature_importances_), key=lambda t: -t[1])

# ---------- 5. Schema for the dashboard / API ----------
features = []
for c in X.columns:
    if pd.api.types.is_numeric_dtype(X[c]):
        isint = bool((X[c].dropna() % 1 == 0).all())
        features.append({"name": c, "type": "number", "min": float(X[c].min()), "max": float(X[c].max()),
                         "median": float(X[c].median()), "step": 1 if isint else 0.1})
    else:
        features.append({"name": c, "type": "category", "categories": sorted(X[c].dropna().unique().tolist()),
                         "mode": X[c].mode().iloc[0]})
meta = {"features": features, "classes": labels, "best_model": best, "models": list(models),
        "metrics": res.to_dict("records"), "confusion": cms, "importance": [{"feature": a, "importance": float(b)} for a, b in imp[:12]],
        "eda": eda, "team_means": df[num_cols].mean().round(3).to_dict(),
        "class_means": df.groupby(TARGET)[num_cols].mean().round(3).to_dict("index")}
res.to_csv(ART / "model_comparison.csv", index=False)
(ART / "metadata.json").write_text(json.dumps(clean(meta)))
print("Artifacts saved to", ART)
