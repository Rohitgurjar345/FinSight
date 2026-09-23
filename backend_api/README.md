# Backend API

Flask REST wrapper around `finance_platform.FinancialPlatform`. Fully tested
end-to-end in this build (real HTTP calls against a running server — see
below to reproduce).

## Setup
```bash
pip install -r ../requirements.txt
pip install flask
```
(`flask-cors` was not installable in the sandbox this was built in — no
network access — so CORS is handled manually via an `after_request` hook in
`app.py` instead. This works fine; no separate package needed.)

## Run
```bash
python app.py
```
Runs on `http://127.0.0.1:5000`.

## Endpoints (all tested with real requests during this build)

| Method | Path | Body / Params | Returns |
|---|---|---|---|
| GET | `/api/health` | — | `{"status": "ok", "active_sessions": N}` |
| POST | `/api/upload` | multipart `files` (one or more) | `{session_id, transaction_count, ingestion_report}` |
| GET | `/api/health-score` | `?session_id=...` | Health score + breakdown + estimation warnings |
| POST | `/api/loan-preassessment` | JSON: `session_id, age, credit_score, assets, existing_loan, criminal_record` | Loan tier + disclaimer, or a 400 listing missing fields if any are absent |
| POST | `/api/ask` | JSON: `session_id, query` | RAG assistant answer + source |

## Session model — read before deploying anywhere beyond local dev

Sessions are an in-memory Python dict (`SESSIONS`), keyed by a `session_id`
returned from `/api/upload`. This means:
- State is lost on server restart.
- Does not work with multiple worker processes (e.g. `gunicorn -w 4`) since
  each process has its own memory — a request could land on a worker that
  never saw the upload.
- No expiry — sessions accumulate until the process restarts.

Fine for local development and testing. Replace `SESSIONS` with Redis or a
database, keyed the same way, before this goes anywhere real.

## Verifying it yourself

```bash
curl http://127.0.0.1:5000/api/health

curl -X POST http://127.0.0.1:5000/api/upload \
  -F "files=@../data/raw/bank.xlsx"
# copy the session_id from the response, then:

curl "http://127.0.0.1:5000/api/health-score?session_id=YOUR_SESSION_ID"

curl -X POST http://127.0.0.1:5000/api/loan-preassessment \
  -H "Content-Type: application/json" \
  -d '{"session_id":"YOUR_SESSION_ID","age":32,"credit_score":720,"assets":200000,"existing_loan":0,"criminal_record":0}'

curl -X POST http://127.0.0.1:5000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"session_id":"YOUR_SESSION_ID","query":"what is my total spend?"}'
```
