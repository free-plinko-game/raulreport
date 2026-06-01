"""JSON-on-disk persistence for runs."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
RUNS_DIR = DATA_DIR / "runs"
KEYWORDS_PATH = DATA_DIR / "keywords.json"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_keywords() -> list[str]:
    with open(KEYWORDS_PATH, encoding="utf-8") as f:
        return json.load(f)


def run_path(run_date: str) -> Path:
    return RUNS_DIR / f"{run_date}.json"


def list_runs() -> list[dict]:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for p in sorted(RUNS_DIR.glob("*.json"), reverse=True):
        try:
            with open(p, encoding="utf-8") as f:
                r = json.load(f)
            keywords = r.get("keywords", [])
            done = sum(1 for k in keywords if k.get("processed_at"))
            total_ads = sum(len(k.get("ads", [])) for k in keywords)
            total_offshore = sum(
                sum(1 for a in k.get("ads", []) if a.get("is_offshore"))
                for k in keywords
            )
            out.append({
                "run_date": r.get("run_date", p.stem),
                "status": r.get("status", "in_progress"),
                "created_at": r.get("created_at"),
                "updated_at": r.get("updated_at"),
                "total": len(keywords),
                "done": done,
                "total_ads": total_ads,
                "total_offshore": total_offshore,
            })
        except (json.JSONDecodeError, OSError):
            continue
    return out


def create_run(run_date: str) -> dict:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = run_path(run_date)
    if path.exists():
        return load_run(run_date)
    keywords = load_keywords()
    now = _utcnow()
    run = {
        "run_date": run_date,
        "status": "in_progress",
        "created_at": now,
        "updated_at": now,
        "paa_clusters": None,
        "intelligence_generated_at": None,
        "intelligence_regenerated_at": None,
        "keywords": [
            {
                "keyword": kw,
                "processed_at": None,
                "raw_paste": "",
                "positions": [],
                "ads": [],
                "warnings": [],
                "serp_features": None,
            }
            for kw in keywords
        ],
    }
    _write(run)
    return run


def load_run(run_date: str) -> dict | None:
    path = run_path(run_date)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_all_runs() -> list[dict]:
    """Full run dicts, sorted by run_date ascending. For cross-run trend analysis."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    runs = []
    for p in sorted(RUNS_DIR.glob("*.json")):
        try:
            with open(p, encoding="utf-8") as f:
                runs.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue
    runs.sort(key=lambda r: r.get("run_date", ""))
    return runs


def _write(run: dict) -> None:
    run["updated_at"] = _utcnow()
    all_done = all(k.get("processed_at") for k in run["keywords"])
    run["status"] = "complete" if all_done else "in_progress"
    path = run_path(run["run_date"])
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(run, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def update_serp_features(run_date: str, idx: int, serp_features: dict, paste_hash: str = "") -> None:
    run = load_run(run_date)
    if run is None:
        raise FileNotFoundError(run_date)
    run["keywords"][idx]["serp_features"] = serp_features
    run["keywords"][idx]["serp_features_paste_hash"] = paste_hash
    _write(run)


def update_intelligence(run_date: str, paa_clusters: dict) -> None:
    run = load_run(run_date)
    if run is None:
        raise FileNotFoundError(run_date)
    run["paa_clusters"] = paa_clusters
    now = _utcnow()
    if run.get("intelligence_generated_at"):
        run["intelligence_regenerated_at"] = now
    else:
        run["intelligence_generated_at"] = now
    _write(run)


def update_keyword(
    run_date: str,
    idx: int,
    *,
    raw_paste: str | None = None,
    positions: list[dict] | None = None,
    ads: list[dict] | None = None,
    warnings: list[dict] | None = None,
    mark_processed: bool = False,
) -> dict:
    run = load_run(run_date)
    if run is None:
        raise FileNotFoundError(run_date)
    if not 0 <= idx < len(run["keywords"]):
        raise IndexError(idx)
    kw = run["keywords"][idx]
    if raw_paste is not None:
        kw["raw_paste"] = raw_paste
    if positions is not None:
        kw["positions"] = positions
    if ads is not None:
        kw["ads"] = ads
    if warnings is not None:
        kw["warnings"] = warnings
    if mark_processed:
        kw["processed_at"] = _utcnow()
    _write(run)
    return kw
