"""SERP Classifier — Flask app."""
from __future__ import annotations

import hashlib
import logging
import os
import re
import secrets
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from functools import wraps
from io import BytesIO

from dotenv import load_dotenv
from flask import (
    Flask, Response, abort, jsonify, redirect, render_template, request,
    send_file, url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

import storage
import trends
from config import CATEGORIES, CATEGORY_LABELS, VALID_CATEGORIES
from llm import (
    LLMError, classify_paste, extract_ads_paste,
    generate_ads_report_analysis, extract_serp_features, cluster_paa,
)

MIN_RUNS_FOR_DASHBOARD = 3
from xlsx_export import build_workbook
from pdf_report import build_report
from intelligence import operator_visibility_index, serp_landscape_summary, snippet_language_summary
from pdf_intelligence import build_intelligence_report

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB paste cap

# Behind nginx (one proxy hop): trust X-Forwarded-For / X-Forwarded-Proto so the
# client's real IP reaches the rate limiter and request.scheme reflects HTTPS.
# Safe only because gunicorn binds 127.0.0.1 — nginx is the sole client.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Rate limiter — caps abuse of the OpenAI-spending endpoints (see @limiter.limit below).
# In-memory storage: counts are per-worker (gunicorn runs 2), so effective limits are ~2x.
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="memory://",
)


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


_RUN_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _load_run_or_404(run_date: str):
    """Reject anything that isn't a YYYY-MM-DD date before it reaches the filesystem
    (defense-in-depth against path tricks in the data/runs/ filename), then load
    the run or 404."""
    if not _RUN_DATE_RE.match(run_date):
        abort(404)
    run = storage.load_run(run_date)
    if run is None:
        abort(404)
    return run


@app.route("/healthz")
def healthz():
    return {"ok": True}


@app.route("/")
@requires_auth
def index():
    runs = storage.list_runs()
    today = date.today().isoformat()
    return render_template("index.html", runs=runs, today=today)


@app.route("/dashboard")
@requires_auth
def dashboard():
    all_runs = storage.load_all_runs()
    run_dates = [r.get("run_date", "") for r in all_runs]
    keywords = storage.load_keywords()
    return render_template(
        "dashboard.html",
        run_count=len(all_runs),
        run_dates=run_dates,
        keywords=keywords,
        min_runs=MIN_RUNS_FOR_DASHBOARD,
        category_labels=CATEGORY_LABELS,
    )


@app.route("/dashboard/data")
@requires_auth
def dashboard_data():
    all_runs = storage.load_all_runs()
    if len(all_runs) < MIN_RUNS_FOR_DASHBOARD:
        return jsonify({
            "ready": False,
            "run_count": len(all_runs),
            "min_runs": MIN_RUNS_FOR_DASHBOARD,
        })

    # Time-range slice: last N runs (4/8/12) or all
    rng = request.args.get("range", "4")
    if rng != "all":
        try:
            n = int(rng)
            all_runs = all_runs[-n:] if n > 0 else all_runs
        except ValueError:
            all_runs = all_runs[-4:]

    # Keyword filter: "all" or a specific keyword
    kw = request.args.get("keyword", "all")
    kw_filter = None if kw == "all" else {kw}

    data = trends.build_dashboard(all_runs, kw_filter)
    data["ready"] = True
    return jsonify(data)


@app.route("/run", methods=["POST"])
@requires_auth
def create_run():
    run_date = request.form.get("run_date") or date.today().isoformat()
    if not _RUN_DATE_RE.match(run_date):
        abort(400)
    storage.create_run(run_date)
    return redirect(url_for("view_run", run_date=run_date))


@app.route("/run/<run_date>")
@requires_auth
def view_run(run_date: str):
    run = _load_run_or_404(run_date)
    done = sum(1 for k in run["keywords"] if k.get("processed_at"))
    return render_template(
        "run.html",
        run=run,
        done=done,
        total=len(run["keywords"]),
        categories=CATEGORIES,
        category_labels=CATEGORY_LABELS,
    )


@app.route("/run/<run_date>/keyword/<int:idx>/process", methods=["POST"])
@requires_auth
@limiter.limit("30 per minute")
def process_keyword(run_date: str, idx: int):
    run = _load_run_or_404(run_date)
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

    try:
        ads, _ads_usage = extract_ads_paste(kw_name, raw_paste)
    except LLMError as e:
        app.logger.warning("Ads LLM failure for %s/%d — continuing without ads: %s", run_date, idx, e)
        ads = []

    storage.update_keyword(
        run_date, idx,
        raw_paste=raw_paste,
        positions=positions,
        ads=ads,
        warnings=warnings,
        mark_processed=True,
    )
    return jsonify({"positions": positions, "ads": ads, "warnings": warnings})


@app.route("/run/<run_date>/keyword/<int:idx>/save", methods=["POST"])
@requires_auth
def save_keyword(run_date: str, idx: int):
    run = _load_run_or_404(run_date)
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
    run = _load_run_or_404(run_date)
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


@app.route("/run/<run_date>/intelligence")
@requires_auth
def view_intelligence(run_date: str):
    run = _load_run_or_404(run_date)
    generated = bool(run.get("intelligence_generated_at"))
    ovi = operator_visibility_index(run["keywords"]) if generated else None
    landscape = serp_landscape_summary(run["keywords"]) if generated else None
    snippet = snippet_language_summary(run["keywords"]) if generated else None
    return render_template(
        "intelligence.html",
        run=run,
        generated=generated,
        ovi=ovi,
        landscape=landscape,
        snippet=snippet,
        category_labels=CATEGORY_LABELS,
    )


@app.route("/run/<run_date>/intelligence/generate", methods=["POST"])
@requires_auth
@limiter.limit("6 per minute")
def generate_intelligence(run_date: str):
    run = _load_run_or_404(run_date)

    payload = request.get_json(silent=True) or {}
    force = bool(payload.get("force", False))

    def _paste_hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    # Build list of keywords that need extraction.
    # Always skip keywords with no paste. On first run, skip already-extracted ones.
    # On force (Regenerate), only re-extract if the raw_paste changed since last extraction —
    # this prevents LLM non-determinism from shifting counts on unchanged data.
    pending = []
    for idx, kw_obj in enumerate(run["keywords"]):
        if not kw_obj.get("raw_paste"):
            continue
        if not kw_obj.get("serp_features"):
            pending.append((idx, kw_obj))
            continue
        if force:
            current_hash = _paste_hash(kw_obj["raw_paste"])
            stored_hash  = kw_obj.get("serp_features_paste_hash", "")
            if current_hash != stored_hash:
                pending.append((idx, kw_obj))

    def _extract(idx: int, kw_obj: dict) -> tuple[int, dict | None, str, str | None]:
        paste = kw_obj["raw_paste"]
        try:
            return idx, extract_serp_features(kw_obj["keyword"], paste), _paste_hash(paste), None
        except LLMError as e:
            app.logger.warning("SERP features failed kw=%r: %s", kw_obj["keyword"], e)
            return idx, None, "", kw_obj["keyword"]

    errors: list[str] = []
    results: list[tuple[int, dict, str]] = []

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_extract, idx, kw_obj): idx for idx, kw_obj in pending}
        for fut in as_completed(futures):
            idx, features, paste_hash, err_kw = fut.result()
            if err_kw:
                errors.append(err_kw)
            elif features is not None:
                results.append((idx, features, paste_hash))

    # Write sequentially to avoid storage race conditions
    for idx, features, paste_hash in results:
        storage.update_serp_features(run_date, idx, features, paste_hash)

    # Reload after writes and cluster PAA
    run = storage.load_run(run_date) or {}
    paa_items = []
    for kw_obj in run.get("keywords", []):
        sf = kw_obj.get("serp_features") or {}
        for q in sf.get("paa_questions", []):
            paa_items.append({"question": q, "keyword": kw_obj["keyword"]})

    paa_clusters = {}
    if paa_items:
        try:
            paa_clusters = cluster_paa(run_date, paa_items)
        except LLMError as e:
            app.logger.warning("PAA cluster failed: %s", e)

    storage.update_intelligence(run_date, paa_clusters)
    return jsonify({"ok": True, "errors": errors, "paa_questions": len(paa_items)})


@app.route("/run/<run_date>/intelligence/pdf")
@requires_auth
def intelligence_pdf(run_date: str):
    run = _load_run_or_404(run_date)
    if not run.get("intelligence_generated_at"):
        abort(404)
    landscape = serp_landscape_summary(run["keywords"])
    snippet = snippet_language_summary(run["keywords"])
    ovi = operator_visibility_index(run["keywords"])
    pdf_bytes = build_intelligence_report(run, landscape, snippet, ovi)
    fname = f"AUS_Intelligence_{run_date}.pdf"
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=fname,
    )


@app.route("/run/<run_date>/ads-report")
@requires_auth
@limiter.limit("12 per minute")
def ads_report(run_date: str):
    run = _load_run_or_404(run_date)

    keywords_with_ads = [
        {"keyword": k["keyword"], "ads": k.get("ads", [])}
        for k in run["keywords"]
        if k.get("ads")
    ]
    if not keywords_with_ads:
        return jsonify({"error": "No ads data found — process some keywords first"}), 400

    try:
        analysis = generate_ads_report_analysis(run_date, keywords_with_ads)
    except LLMError as e:
        app.logger.exception("Report LLM failure for %s", run_date)
        return jsonify({"error": str(e)}), 502

    pdf_bytes = build_report(run, analysis)
    fname = f"AUS_Ads_Intelligence_{run_date}.pdf"
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=fname,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
