"""REST API for the frontend, wrapping finance_platform.FinancialPlatform.

SESSION MODEL (read before deploying anywhere real):
Each upload creates a session_id (uuid4) whose FinancialPlatform instance is
kept in an in-memory Python dict. This is intentionally simple for local
development only:
  - State is lost on server restart.
  - Does not work across multiple worker processes (e.g. gunicorn with
    workers > 1) since each process has its own memory.
  - No expiry/cleanup — sessions accumulate in memory until the process
    restarts.
For anything beyond local dev/demo use, replace SESSIONS with a real store
(Redis, a database) keyed the same way.
"""
import os
import sys
import uuid
import traceback

from flask import Flask, request, jsonify

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from finance_platform import FinancialPlatform, REQUIRED_LOAN_MANUAL_FIELDS

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
SESSIONS = {}  # session_id -> FinancialPlatform instance


@app.after_request
def add_cors_headers(response):
    """Manual CORS (no flask-cors dependency needed) — allows the Vite dev
    server (a different port) to call this API during local development."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/api/upload", methods=["POST", "OPTIONS"])
def upload():
    if request.method == "OPTIONS":
        return "", 204

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files provided. Send one or more files under the 'files' field."}), 400

    session_id = str(uuid.uuid4())
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    saved_paths = []
    for f in files:
        safe_name = os.path.basename(f.filename)
        if not safe_name:
            continue
        path = os.path.join(session_dir, safe_name)
        f.save(path)
        saved_paths.append(path)

    if not saved_paths:
        return jsonify({"error": "No valid filenames in upload."}), 400

    try:
        platform = FinancialPlatform(saved_paths)
    except Exception as e:
        return jsonify({"error": f"Failed to process uploaded file(s): {str(e)}"}), 422

    SESSIONS[session_id] = platform

    return jsonify({
        "session_id": session_id,
        "transaction_count": len(platform.transactions),
        "ingestion_report": platform.ingestion_report,
    })


def _get_platform_or_404(session_id):
    platform = SESSIONS.get(session_id)
    if platform is None:
        return None, (jsonify({"error": "Unknown or expired session_id. Upload again."}), 404)
    return platform, None


@app.route("/api/health-score", methods=["GET"])
def health_score():
    session_id = request.args.get("session_id")
    platform, err = _get_platform_or_404(session_id)
    if err:
        return err
    try:
        return jsonify(platform.health_score())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/loan-preassessment", methods=["POST"])
def loan_preassessment():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    platform, err = _get_platform_or_404(session_id)
    if err:
        return err

    missing = [f for f in REQUIRED_LOAN_MANUAL_FIELDS if f not in data]
    if missing:
        return jsonify({
            "error": "Missing required fields — these cannot be derived from a bank "
                     "statement and must be provided by the user.",
            "missing_fields": missing,
        }), 400

    try:
        result = platform.loan_preassessment(
            age=int(data["age"]), credit_score=int(data["credit_score"]),
            assets=float(data["assets"]), existing_loan=int(data["existing_loan"]),
            criminal_record=int(data["criminal_record"]),
        )
        return jsonify(result)
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid field value: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    query = (data.get("query") or "").strip()
    platform, err = _get_platform_or_404(session_id)
    if err:
        return err
    if not query:
        return jsonify({"error": "Empty query."}), 400
    try:
        return jsonify(platform.ask(query))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    """Simple liveness check for the frontend to confirm the API is reachable."""
    return jsonify({"status": "ok", "active_sessions": len(SESSIONS)})


if __name__ == "__main__":
    app.run(port=5000, debug=True)
