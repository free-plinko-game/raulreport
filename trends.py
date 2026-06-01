"""
Cross-run trend aggregation for the Phase 4 Dashboard.

Pure computation over the run JSON files already on disk — no LLM, no HTTP, no new
dependencies. Mirrors the intelligence.py pattern. All functions take a list of full
run dicts (as returned by storage.load_all_runs(), ascending by date) plus an optional
keyword filter, and return JSON-serialisable structures the dashboard charts consume.
"""
from __future__ import annotations

from collections import defaultdict

from config import CATEGORY_KEYS, BY_KEY

# The "hostile" cluster — spammy / impersonating / compromised domains. The headline
# SERP-health signal is the combined share of these categories. PARASITE is shown as
# its own band (affiliate sections on otherwise-legit sites) and is not counted hostile.
HOSTILE = {"FAKE_CASINO", "EMD", "SUBDOMAIN", "FLIPPED", "HACKED"}


def _run_keywords(run: dict, kw_filter: set[str] | None) -> list[dict]:
    kws = run.get("keywords", [])
    if kw_filter:
        kws = [k for k in kws if k.get("keyword") in kw_filter]
    return kws


def _positions(run: dict, kw_filter: set[str] | None):
    """Yield (keyword, position) for every classified position in a run."""
    for k in _run_keywords(run, kw_filter):
        for p in k.get("positions", []):
            yield k.get("keyword", ""), p


def category_colours() -> dict[str, str]:
    """key -> '#RRGGBB' for chart styling, from the central taxonomy."""
    return {k: f"#{BY_KEY[k].fill}" for k in CATEGORY_KEYS}


# ── Section 1 — SERP Health Trend ────────────────────────────────────────────────

def serp_health(runs: list[dict], kw_filter: set[str] | None = None) -> dict:
    """Per-run category counts + percentages, plus the hostile-share series."""
    series = []
    for run in runs:
        counts = defaultdict(int)
        total = 0
        for _, p in _positions(run, kw_filter):
            cat = p.get("category", "")
            counts[cat] += 1
            total += 1
        hostile = sum(c for cat, c in counts.items() if cat in HOSTILE)
        series.append({
            "run_date": run.get("run_date", ""),
            "total": total,
            "counts": {k: counts.get(k, 0) for k in CATEGORY_KEYS},
            "pct": {k: round(counts.get(k, 0) / total * 100, 1) if total else 0 for k in CATEGORY_KEYS},
            "hostile_count": hostile,
            "hostile_pct": round(hostile / total * 100, 1) if total else 0,
        })

    # Run-on-run hostile delta for the alert banner
    alert = None
    if len(series) >= 2:
        prev, cur = series[-2]["hostile_pct"], series[-1]["hostile_pct"]
        if cur - prev >= 2.0:
            alert = {
                "from_pct": prev,
                "to_pct": cur,
                "delta_pp": round(cur - prev, 1),
            }
    return {"series": series, "categories": CATEGORY_KEYS, "alert": alert}


# ── Section 2 — New Entrants ─────────────────────────────────────────────────────

def new_entrants(runs: list[dict], kw_filter: set[str] | None = None) -> dict:
    """Domains in the latest run's top-10 for a keyword that weren't there last run."""
    if len(runs) < 2:
        return {"run_date": runs[-1].get("run_date") if runs else None, "entrants": []}

    prev, cur = runs[-2], runs[-1]

    def by_kw_domains(run):
        m: dict[str, dict[str, dict]] = defaultdict(dict)
        for kw, p in _positions(run, kw_filter):
            dom = p.get("domain", "")
            if dom:
                m[kw][dom] = p
        return m

    prev_map = by_kw_domains(prev)
    cur_map = by_kw_domains(cur)

    entrants = []
    for kw, doms in cur_map.items():
        prior = set(prev_map.get(kw, {}).keys())
        for dom, p in doms.items():
            if dom not in prior:
                cat = p.get("category", "")
                entrants.append({
                    "domain": dom,
                    "category": cat,
                    "category_label": BY_KEY[cat].label if cat in BY_KEY else cat,
                    "keyword": kw,
                    "rank": p.get("rank"),
                    "hostile": cat in HOSTILE,
                })
    # Hostile first, then by rank
    entrants.sort(key=lambda e: (not e["hostile"], e["rank"] or 99))
    return {
        "run_date": cur.get("run_date"),
        "prev_run_date": prev.get("run_date"),
        "entrants": entrants,
        "keyword_count": len({e["keyword"] for e in entrants}),
    }


# ── Section 3 — Operator Visibility Index (cross-run) ────────────────────────────

def cross_run_ovi(runs: list[dict], kw_filter: set[str] | None = None) -> dict:
    """Per-domain persistence across runs: runs present, breadth, avg pos, trend."""
    n_runs = len(runs)
    # domain -> per-run data
    dom_runs: dict[str, dict[str, dict]] = defaultdict(dict)
    latest_cat: dict[str, str] = {}

    for run in runs:
        rd = run.get("run_date", "")
        seen_kw: dict[str, list[int]] = defaultdict(list)
        for kw, p in _positions(run, kw_filter):
            dom = p.get("domain", "")
            if not dom:
                continue
            seen_kw[dom].append(p.get("rank", 99))
            latest_cat[dom] = p.get("category", "")  # runs ascending -> ends on latest
        for dom, ranks in seen_kw.items():
            dom_runs[dom][rd] = {
                "keywords": len(ranks),
                "avg_pos": round(sum(ranks) / len(ranks), 1),
                "best": min(ranks),
            }

    domains = []
    for dom, per_run in dom_runs.items():
        dates = sorted(per_run.keys())
        avg_positions = [per_run[d]["avg_pos"] for d in dates]
        kw_breadth = [per_run[d]["keywords"] for d in dates]
        # Trend: compare avg position first half vs second half (lower = better)
        trend = "stable"
        if len(avg_positions) >= 2:
            mid = len(avg_positions) // 2
            early = sum(avg_positions[:mid or 1]) / (mid or 1)
            late = sum(avg_positions[mid:]) / (len(avg_positions) - mid)
            if late < early - 0.5:
                trend = "up"      # improving (lower position number)
            elif late > early + 0.5:
                trend = "down"
        cat = latest_cat.get(dom, "")
        domains.append({
            "domain": dom,
            "runs_present": len(per_run),
            "runs_total": n_runs,
            "avg_keywords": round(sum(kw_breadth) / len(kw_breadth), 1),
            "avg_pos": round(sum(avg_positions) / len(avg_positions), 1),
            "first_seen": dates[0],
            "last_seen": dates[-1],
            "trend": trend,
            "category": cat,
            "category_label": BY_KEY[cat].label if cat in BY_KEY else cat,
            "hostile": cat in HOSTILE,
        })
    domains.sort(key=lambda d: (-d["runs_present"], d["avg_pos"]))
    return {"domains": domains, "runs_total": n_runs}


# ── Section 4 — EMD / Throwaway Tracker ──────────────────────────────────────────

def emd_tracker(runs: list[dict], kw_filter: set[str] | None = None) -> dict:
    """Active EMDs in the latest run + a graveyard of EMDs that have disappeared.

    Uses the stored EMD classification. (Backfill for pre-EMD runs is out of scope
    for the MVP — those domains were tagged SUBDOMAIN and would need inference.)
    """
    # domain -> sorted list of run_dates where it was classified EMD (+ best rank/kw)
    emd_runs: dict[str, list[dict]] = defaultdict(list)
    for run in runs:
        rd = run.get("run_date", "")
        best: dict[str, dict] = {}
        for kw, p in _positions(run, kw_filter):
            if p.get("category") != "EMD":
                continue
            dom = p.get("domain", "")
            rank = p.get("rank", 99)
            if dom and (dom not in best or rank < best[dom]["rank"]):
                best[dom] = {"rank": rank, "keyword": kw}
        for dom, info in best.items():
            emd_runs[dom].append({"run_date": rd, **info})

    latest_rd = runs[-1].get("run_date") if runs else None
    active, graveyard = [], []
    for dom, appearances in emd_runs.items():
        dates = [a["run_date"] for a in appearances]
        last = appearances[-1]
        peak = min(a["rank"] for a in appearances)
        entry = {
            "domain": dom,
            "weeks_active": len(appearances),
            "first_seen": dates[0],
            "last_seen": dates[-1],
            "peak_position": peak,
            "keyword": last["keyword"],
            "latest_position": last["rank"],
        }
        if dates[-1] == latest_rd:
            active.append(entry)
        else:
            graveyard.append(entry)

    active.sort(key=lambda e: e["latest_position"])
    graveyard.sort(key=lambda e: e["last_seen"], reverse=True)
    return {"active": active, "graveyard": graveyard, "latest_run": latest_rd}


# ── Section 5 — Keyword Volatility ───────────────────────────────────────────────

def keyword_volatility(runs: list[dict], kw_filter: set[str] | None = None) -> dict:
    """Per-keyword churn score over consecutive run transitions (0-100, normalised)."""
    if len(runs) < 2:
        return {"keywords": []}

    # keyword -> per-run {domain: rank}
    kw_history: dict[str, list[tuple[str, dict[str, int]]]] = defaultdict(list)
    for run in runs:
        rd = run.get("run_date", "")
        per_kw: dict[str, dict[str, int]] = defaultdict(dict)
        per_kw_hostile: dict[str, set[str]] = defaultdict(set)
        for kw, p in _positions(run, kw_filter):
            dom = p.get("domain", "")
            if dom:
                per_kw[kw][dom] = p.get("rank", 99)
                if p.get("category") in HOSTILE:
                    per_kw_hostile[kw].add(dom)
        for kw, doms in per_kw.items():
            kw_history[kw].append((rd, doms, per_kw_hostile.get(kw, set())))

    scores = []
    for kw, history in kw_history.items():
        if len(history) < 2:
            continue
        raw = 0.0
        transitions = 0
        for (_, prev_doms, _), (_, cur_doms, cur_hostile) in zip(history, history[1:]):
            prev_set, cur_set = set(prev_doms), set(cur_doms)
            changed = len(prev_set ^ cur_set)             # entered or exited
            shifts = sum(abs(cur_doms[d] - prev_doms[d])   # position moves
                         for d in prev_set & cur_set)
            new_hostile = len(cur_hostile - prev_set)      # hostile newcomers weigh extra
            raw += changed + shifts * 0.5 + new_hostile * 2
            transitions += 1
        avg = raw / transitions if transitions else 0
        scores.append({"keyword": kw, "raw": round(avg, 1)})

    # Normalise to 0-100 against the busiest keyword
    max_raw = max((s["raw"] for s in scores), default=0) or 1
    for s in scores:
        s["score"] = round(s["raw"] / max_raw * 100)
    scores.sort(key=lambda s: -s["score"])
    return {"keywords": scores}


# ── Section 6 — Ads Pressure ─────────────────────────────────────────────────────

def ads_pressure(runs: list[dict], kw_filter: set[str] | None = None) -> dict:
    """Total ads + offshore ads per run. Empty series if no ads data exists yet."""
    series = []
    any_ads = False
    for run in runs:
        total_ads = 0
        offshore = 0
        for k in _run_keywords(run, kw_filter):
            ads = k.get("ads", []) or []
            total_ads += len(ads)
            offshore += sum(1 for a in ads if a.get("is_offshore"))
        if total_ads:
            any_ads = True
        series.append({
            "run_date": run.get("run_date", ""),
            "total_ads": total_ads,
            "offshore_ads": offshore,
        })
    return {"series": series, "has_data": any_ads}


# ── Top-level assembler ──────────────────────────────────────────────────────────

def build_dashboard(runs: list[dict], kw_filter: set[str] | None = None) -> dict:
    """Compute every section for the given (already time-sliced) runs."""
    return {
        "run_dates": [r.get("run_date", "") for r in runs],
        "colours": category_colours(),
        "health": serp_health(runs, kw_filter),
        "entrants": new_entrants(runs, kw_filter),
        "ovi": cross_run_ovi(runs, kw_filter),
        "emd": emd_tracker(runs, kw_filter),
        "volatility": keyword_volatility(runs, kw_filter),
        "ads": ads_pressure(runs, kw_filter),
    }
