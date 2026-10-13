# Employee Productivity Digital Twin
CSV → preprocessing → EDA → feature engineering → 3 ML models → Django REST API → React dashboard → what-if simulation.

## Run it (5 steps)
```bash
# 0. (recommended) virtual env
python -m venv venv && source venv/bin/activate        # Windows: venv\Scripts\activate

# 1. Install
pip install -r requirements.txt

# 2. Put your CSV in /data and name it exactly: 06_employee_productivity_digital_twin.csv
#    (no CSV yet? run:  cd data && python make_sample_data.py && cd ..   -> creates a fake one for testing)

# 3. Train + compare models (creates backend/artifacts/*)
cd backend
python train_model.py            # or: python train_model.py ../data/your_file.csv

# 4. Create the history database
python manage.py migrate

# 5. Start server, then open http://127.0.0.1:8000
python manage.py runserver
```
Internet is needed in the browser once (React / Chart.js load from a CDN).

## API
| Method | URL | Purpose |
|---|---|---|
| GET | /api/health/ | status + best model |
| GET | /api/schema/ | input features, ranges, classes, models |
| GET | /api/summary/ | EDA stats, metrics, confusion matrices, importance |
| GET | /api/employees/ , /api/employees/<id>/?model= | twin list / profile + prediction + history |
| POST | /api/predict/ `{features, model?, employee_id?}` | prediction + probabilities |
| POST | /api/whatif/ `{base, scenario, model?, employee_id?}` | baseline vs scenario |
| GET | /api/history/?employee_id= | logged predictions |

## Structure
- `backend/train_model.py` – training, comparison, saves models and `metadata.json`
- `backend/api/` – features.py (shared engineering), ml_service.py, views.py, models.py
- `frontend/` – index.html, style.css, app.jsx (React, served by Django)

## Troubleshooting
- Dashboard says "Loading…" → you skipped step 3, or the server isn't running.
- `Employee_ID` / `Productivity_Level` must exist as column names in your CSV.
- After changing the CSV or code, re-run `train_model.py` and restart the server.
