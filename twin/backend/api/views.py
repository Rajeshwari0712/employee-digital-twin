import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from . import ml_service as ml
from .models import PredictionLog
from .features import TARGET, ID_COL

def _body(r):
    try: return json.loads(r.body or "{}")
    except ValueError: return {}

def _log(emp, kind, res, inputs):
    PredictionLog.objects.create(employee_id=emp or "", kind=kind, model_name=res["model"], inputs=inputs,
                                 label=res["prediction"], confidence=res["confidence"])

def health(r):
    return JsonResponse({"status": "ok", "best_model": ml.meta()["best_model"]})

def schema(r):
    m = ml.meta()
    return JsonResponse({"features": m["features"], "classes": m["classes"], "models": m["models"], "best_model": m["best_model"]})

def summary(r):
    m = ml.meta()
    return JsonResponse({k: m[k] for k in ("best_model", "classes", "metrics", "confusion", "importance", "eda", "team_means", "class_means")})

def employee_list(r):
    df = ml.employees(); out = df[[ID_COL, TARGET]].rename(columns={ID_COL: "id", TARGET: "actual"})
    return JsonResponse({"employees": out.to_dict("records")})

def employee_detail(r, emp_id):
    df = ml.employees(); row = df[df[ID_COL].astype(str) == str(emp_id)]
    if row.empty: return JsonResponse({"error": "Employee not found"}, status=404)
    rec = json.loads(row.iloc[0].to_json())
    feats = {f["name"]: rec.get(f["name"]) for f in ml.meta()["features"]}
    res = ml.predict(feats, r.GET.get("model"))
    hist = list(PredictionLog.objects.filter(employee_id=str(emp_id)).values("kind", "label", "confidence", "created_at")[:10])
    return JsonResponse({"id": emp_id, "actual": rec.get(TARGET), "features": feats, "engineered": ml.engineered(feats),
                         "prediction": res, "team_means": ml.meta()["team_means"], "history": hist})

@csrf_exempt
def predict(r):
    b = _body(r); feats = b.get("features", {})
    try: res = ml.predict(feats, b.get("model"))
    except (ValueError, TypeError) as e: return JsonResponse({"error": f"Invalid input: {e}"}, status=400)
    _log(b.get("employee_id"), "predict", res, feats)
    return JsonResponse({**res, "engineered": ml.engineered(feats)})

@csrf_exempt
def whatif(r):
    b = _body(r); base, scen = b.get("base", {}), b.get("scenario", {})
    try: rb, rs = ml.predict(base, b.get("model")), ml.predict(scen, b.get("model"))
    except (ValueError, TypeError) as e: return JsonResponse({"error": f"Invalid input: {e}"}, status=400)
    changed = {k: {"from": base.get(k), "to": v} for k, v in scen.items() if str(base.get(k)) != str(v)}
    _log(b.get("employee_id"), "whatif", rs, scen)
    return JsonResponse({"baseline": rb, "scenario": rs, "changed": changed,
                         "engineered_baseline": ml.engineered(base), "engineered_scenario": ml.engineered(scen)})

def history(r):
    qs = PredictionLog.objects.all()
    if r.GET.get("employee_id"): qs = qs.filter(employee_id=r.GET["employee_id"])
    return JsonResponse({"history": list(qs.values("employee_id", "kind", "model_name", "label", "confidence", "created_at")[:50])})
