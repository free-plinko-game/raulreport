"""SERP Classifier — Flask app."""
from __future__ import annotations

import logging
import os
import secrets
from datetime import date
from functools import wraps
from io import BytesIO

from dotenv import load_dotenv
from flask import (
    Flask, Response, abort, jsonify, redirect, render_template, request,
    send_file, url_for,
)

import storage
from llm import LLMError, VALID_CATEGORIES, classify_paste
from xlsx_export import build_workbook

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB paste cap


def _check_auth(username: str, password: str) -> bool:
    expected_u = os.environ.get("APP_USERNAME", "admin")
    expected_p = os.environ.get("APP_PASSWORD", "")
    if not expected_p:
        return False
    return secrets.compare_digest(username, expected_u) and secrets.compare_digest(password, expected_p)


def requires_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        if not auth or not _check_auth(auth.username or "", auth.password or ""):
            return Response(
                "Login required",
                401,
                {"WWW-Authenticate": 'Basic realm="SERP Classifier"'},
            )
        return f(*args, **kwargs)
    return wrapper


@app.route("/healthz")
def healthz():
    return {"ok": True}


@app.route("/")
@requires_auth
def index():
    runs = storage.list_runs()
    today = date.today().isoformat()
    return render_template("index.html", runs=runs, today=today)


@app.route("/run", methods=["POST"])
@requires_auth
def create_run():
    run_date = request.form.get("run_date") or date.today().isoformat()
    storage.create_run(run_date)
    return redirect(url_for("view_run", run_date=run_date))


@app.route("/run/<run_date>")
@requires_auth
def view_run(run_date: str):
    run = storage.load_run(run_date)
    if run is None:
        abort(404)
    done = sum(1 for k in run["keywords"] if k.get("processed_at"))
    return render_template(
        "run.html",
        run=run,
        done=done,
        total=len(run["keywords"]),
        categories=sorted(VALID_CATEGORIES),
    )


@app.route("/run/<run_date>/keyword/<int:idx>/process", methods=["POST"])
@requires_auth
def process_keyword(run_date: str, idx: int):
    run = storage.load_run(run_date)
    if run is None:
        abort(404)
    if not 0 <= idx < len(run["keywords"]):
        abort(404)
    payload = request.get_json(silent=True) or request.form
    raw_paste = (payload.get("raw_paste") or "").strip()
    if not raw_paste:
        return jsonify({"error": "raw_paste is required"}), 400

    kw_name = run["keywords"][idx]["keyword"]
    try:
        positions, warnings, _usage = classify_paste(kw_name, raw_paste)
    except LLMError as e:
        app.logger.exception("LLM failure for %s/%d", run_date, idx)
        return jsonify({"error": str(e)}), 502

    storage.update_keyword(
        run_date, idx,
        raw_paste=raw_paste,
        positions=positions,
        warnings=warnings,
        mark_processed=True,
    )
    return jsonify({"positions": positions, "warnings": warnings})


@app.route("/run/<run_date>/keyword/<int:idx>/save", methods=["POST"])
@requires_auth
def save_keyword(run_date: str, idx: int):
    run = storage.load_run(run_date)
    if run is None:
        abort(404)
    if not 0 <= idx < len(run["keywords"]):
        abort(404)
    payload = request.get_json(silent=True) or {}
    raw_positions = payload.get("positions", [])
    if not isinstance(raw_positions, list):
        return jsonify({"error": "positions must be a list"}), 400

    cleaned = []
    for i, p in enumerate(raw_positions):
        if not isinstance(p, dict):
            continue
        cat = (p.get("category") or "").upper().strip()
        if cat not in VALID_CATEGORIES:
            return jsonify({"error": f"invalid category at row {i + 1}: {cat!r}"}), 400
        cleaned.append({
            "rank": int(p.get("rank", i + 1)),
            "short_label": str(p.get("short_label", "")).strip(),
            "domain": str(p.get("domain", "")).strip(),
            "full_url": str(p.get("full_url", "")).strip(),
            "category": cat,
            "reasoning": str(p.get("reasoning", "")).strip(),
            "edited": bool(p.get("edited", True)),
        })

    storage.update_keyword(
        run_date, idx,
        positions=cleaned,
        mark_processed=True,
    )
    return jsonify({"ok": True, "positions": cleaned})


@app.route("/run/<run_date>/generate")
@requires_auth
def generate_xlsx(run_date: str):
    run = storage.load_run(run_date)
    if run is None:
        abort(404)
    wb = build_workbook(run)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    fname = f"AUS_SERP_classified_{run_date}.xlsx"
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=fname,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
