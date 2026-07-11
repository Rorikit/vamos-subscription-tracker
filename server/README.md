# Backend

FastAPI API for Vamos Subscription Tracker.

## Run locally

```powershell
cd server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will create `vamos_subscriptions.db` and seed demo data on first start.

