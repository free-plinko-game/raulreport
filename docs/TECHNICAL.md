# RaulReport — Technical Documentation

Audience: developers maintaining or extending the app. For the analyst workflow see
[USER_GUIDE.md](USER_GUIDE.md).

---

## 1. Overview

RaulReport is a single-process Flask application. It has **no database** — all state
lives in JSON files on disk under `data/runs/`. There is **no front-end build step**:
pages are server-rendered Jinja2 templates progressively enhanced with vanilla JS.
The only external service is the OpenAI API.

The app is organised around **runs**. A run is one week's monitoring snapshot, keyed by
date (`2026-05-27`). Each run holds 26 keywords; each keyword holds the pasted SERP text,
the classified organic positions, extracted ads, and optional intelligence data.

---

## 2. Tech stack

| Concern | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | Production VPS runs 3.12 |
| Web framework | Flask 3.0.3 | HTTP Basic Auth, no sessions/login DB |
| WSGI server (prod) | gunicorn 22.0.0 | 2 workers, `--timeout 300`, binds `127.0.0.1:8011` |
| Reverse proxy (prod) | nginx | Terminates TLS on `:1539`, proxies to gunicorn |
| Rate limiting | Flask-Limiter 4.1.1 | In-memory caps on the OpenAI-spending routes |
| LLM | OpenAI Chat Completions | JSON mode; `gpt-4o-mini` default, `gpt-4o` for analysis |
| HTTP client pin | `httpx<0.28.0` | `openai==1.54.4` passes a `proxies` kwarg removed in httpx 0.28 |
| Spreadsheet | openpyxl 3.1.5 | Builds the boss's `.xlsx` template incl. doughnut chart |
| PDF | fpdf2 2.7.9 | Core latin-1 fonts; Unicode sanitised before encoding |
| Charts (dashboard) | Chart.js 4.4.1 via CDN | Client-side only; needs internet in the browser |
| Storage | JSON-on-disk | Atomic writes via temp file + `os.replace` |
| Config | python-dotenv | Reads `.env` |

No Redis, no Celery, no SQL, no Node toolchain.

---

## 3. Repository layout

```
app.py                 Flask app: routes, auth, request handling
wsgi.py                WSGI entry point (exposes `application`)
config.py              SINGLE SOURCE OF TRUTH for the category taxonomy
llm.py                 OpenAI wrappers + response validators + domain normalisation
storage.py             JSON persistence: load/save runs, atomic writes, agg03 helpers
xlsx_export.py         Builds the .xlsx deliverable (legend, grid, summary, chart)
intelligence.py        Single-run aggregation (OVI, SERP landscape, snippet language)
trends.py              Cross-run aggregation for the dashboard
pdf_report.py          Ads Intelligence PDF (fpdf2)
pdf_intelligence.py    Run Intelligence PDF (fpdf2)

prompts/
  extract_and_classify.md   Organic top-10 extraction + 11-category classification
  extract_ads.md            Paid-ad extraction (+ domain_category)
  ads_report_analysis.md    Ads analysis agent (ad-type taxonomy + narrative)
  extract_serp_features.md  SERP feature + snippet-language detection
  cluster_paa.md            People-Also-Ask theme clustering

templates/   base / index / run / intelligence / dashboard (Jinja2)
static/      style.css, app.js, intelligence.js, charts.js

data/
  keywords.json        The 26 monitored keywords (input list)
  runs/                Per-run JSON files (gitignored)
```

Planning docs live at the repo root: `requirements.md` (original spec — note it predates
the 11-category taxonomy), `phase2.md`–`phase5.md`, `done.md`.

---

## 4. The category taxonomy (`config.py`)

`config.py` is the **single source of truth**. Every layer — LLM validation, xlsx export,
web UI pills, intelligence/dashboard colours — derives from the `CATEGORIES` list. To add,
rename, or recolour a category, edit this file only.

Each `Category` has: `key` (CSS-safe internal token, stored in run JSON), `label`
(human-facing display string), `definition` (legend text), `fill`/`font` (hex colours),
and `bold` (xlsx weight).

The 11 organic categories:

| key | label | role |
|---|---|---|
| `SUBDOMAIN` | SUBDOMAIN & TLD ABUSE | subdomain spam / pseudo-TLD abuse |
| `FLIPPED` | FLIPPED | a formerly-legit domain turned wholly into a casino |
| `EMD` | EXACT MATCH DOMAIN (EMD) | purpose-built exact-keyword domain |
| `HACKED` | HACKED | legit site compromised, casino injected on paths |
| `PARASITE` | PARASITE | affiliate casino section on an otherwise-legit site |
| `UGC` | UGC | Reddit / Trustpilot / Quora / forums / YouTube |
| `PUBLISHER` | PUBLISHER | legitimate gambling-industry review hub |
| `OPERATOR` | OPERATORS | licensed, legitimate operator |
| `GOV` | GOV | government / regulator / help service |
| `APP` | APP | app-store listing |
| `FAKE_CASINO` | Fake Casino | unlicensed offshore imposter casino |

Derived exports: `CATEGORY_KEYS`, `VALID_CATEGORIES` (set), `BY_KEY`, `CATEGORY_LABELS`,
plus helpers `hex_to_rgb()` and `label_for()`.

> **Taxonomy history.** The app launched with 8 categories; `FLIPPED`, `EMD`, and
> `FAKE_CASINO` were added 2026-05-27. Runs created before then only contain the original
> keys — relevant for any cross-run analysis (see `trends.py` notes).

Two **ads-only** axes are orthogonal to the above and live on ad records, not positions:
`is_offshore` (boolean heuristic) and `domain_category` (the same 11 keys + `OTHER`,
classifying the ad's landing domain).

---

## 5. Data model

Runs are stored at `data/runs/<run_date>.json`. Shape:

```jsonc
{
  "run_date": "2026-05-27",
  "status": "in_progress" | "complete",   // auto-derived: complete when all 26 processed
  "created_at": "2026-05-27T11:00:00Z",
  "updated_at": "...",
  "paa_clusters": null | { ... },          // set by intelligence generation
  "intelligence_generated_at": null | "...",
  "intelligence_regenerated_at": null | "...",
  "keywords": [
    {
      "keyword": "online casino australia",
      "processed_at": null | "...",
      "raw_paste": "…pasted SERP text…",
      "positions": [
        {
          "rank": 1,
          "short_label": "Trustpilot",     // what shows in the xlsx cell
          "domain": "au.trustpilot.com",   // lowercased, www-stripped
          "full_url": "https://…",
          "category": "UGC",               // one of the 11 keys
          "reasoning": "…",
          "edited": false                  // true once an analyst changes it
        }
      ],
      "ads": [
        {
          "position": 1,
          "ad_position": "top|bottom|shopping",
          "advertiser": "BetWinner",
          "display_url": "betwinner.com › au",
          "landing_url": "https://…",
          "is_offshore": true,
          "notes": "…",
          "domain_category": "FAKE_CASINO" // 11 keys + OTHER
        }
      ],
      "warnings": [ { "rank": 3, "issue": "…", "detail": "…" } ],
      "serp_features": null | { … },       // set by intelligence generation
      "serp_features_paste_hash": "…"      // sha256[:16] of raw_paste at extraction time
    }
  ]
}
```

**Atomic writes.** `storage._write()` writes to `<file>.json.tmp` then `os.replace()`s it
into place, so a crash can never leave a half-written run. `status` is recomputed on every
write (complete when every keyword has `processed_at`).

**Key storage functions:** `create_run` (idempotent — opens existing), `load_run`,
`load_all_runs` (ascending by date, for trends), `list_runs` (lightweight summaries with
`total_ads`/`total_offshore`), `update_keyword`, `update_serp_features`,
`update_intelligence`.

---

## 6. LLM layer (`llm.py`)

All OpenAI calls go through `llm.py`. Common traits: **JSON mode**
(`response_format={"type": "json_object"}`), exponential backoff (max 3 retries on
rate-limit / timeout / API error), a single JSON-parse retry on malformed output, and
strict server-side validation of the result before it's trusted.

| Function | Prompt | Model | Returns |
|---|---|---|---|
| `classify_paste(keyword, paste)` | extract_and_classify.md | `OPENAI_MODEL` | `(positions, warnings, usage)` |
| `extract_ads_paste(keyword, paste)` | extract_ads.md | `OPENAI_MODEL` | `(ads, usage)` |
| `generate_ads_report_analysis(date, kw_ads)` | ads_report_analysis.md | `OPENAI_REPORT_MODEL` | analysis dict |
| `extract_serp_features(keyword, paste)` | extract_serp_features.md | `OPENAI_MODEL` | features dict |
| `cluster_paa(date, paa_items)` | cluster_paa.md | `OPENAI_REPORT_MODEL` | clusters dict |

**Two-call design.** Organic classification and ad extraction are *separate* LLM calls with
*separate* prompts. They were once combined and interfered badly (the organic prompt strips
the sponsored block, which destroyed the ad data before the ad step ran). Keep them apart.

**Validation.** `_validate_result` coerces unknown organic categories to `PARASITE` + a
warning; `_validate_ads` coerces unknown `ad_position` to `top` and unknown `domain_category`
to `OTHER`. `VALID_CATEGORIES` is imported from `config.py`.

**Domain normalisation.** `_normalize_domain()` lowercases and strips a leading `www.`
*prefix* via regex. (Do **not** use `str.lstrip("www.")` — it strips leading `w`/`.`
characters and mangles domains like `west.com` → `est.com`. Cross-run trend matching
depends on stable domain identity.)

---

## 7. Aggregation layers (no LLM)

These are pure, deterministic functions over stored data — fast, cheap, and safe to call
on every page load.

- **`intelligence.py`** (single run): `operator_visibility_index`, `serp_landscape_summary`,
  `snippet_language_summary`.
- **`trends.py`** (across runs): `serp_health`, `new_entrants`, `cross_run_ovi`,
  `emd_tracker`, `keyword_volatility`, `ads_pressure`, and the `build_dashboard` assembler.
  The "hostile cluster" used for the SERP-health headline is
  `FAKE_CASINO + EMD + SUBDOMAIN + FLIPPED + HACKED`. Colours come from `config.py` so
  charts match the xlsx and UI.

---

## 8. Output generators

- **`xlsx_export.build_workbook(run)`** — reproduces the boss's template: legend block,
  26-keyword × 10-rank grid with per-category cell fills, market-share summary with live
  formulas, and a doughnut chart. **Layout anchors are computed from the taxonomy length**
  (legend rows, summary rows, TOTAL row, chart position) so adding categories never breaks
  the sheet.
- **`pdf_report.build_report(run, analysis)`** — Ads Intelligence PDF (cover stats,
  executive summary, offshore density chart, ad-type breakdown, top advertisers, per-keyword
  detail).
- **`pdf_intelligence.build_intelligence_report(run, landscape, snippet, ovi)`** — Run
  Intelligence PDF (4 sections mirroring the intelligence page).

Both PDFs use fpdf2 core latin-1 fonts, so text is sanitised through a Unicode-replacement
table and word-boundary truncation before encoding.

---

## 9. HTTP routes (`app.py`)

All routes except `/healthz` require HTTP Basic Auth (`requires_auth` decorator,
constant-time credential compare). The three OpenAI-spending routes are
additionally **rate-limited** (Flask-Limiter, in-memory — counts are per gunicorn
worker, so effective limits are ~2×): `process_keyword` 30/min, `ads_report`
12/min, `generate_intelligence` 6/min. Every `<run_date>` path param is validated
against `^\d{4}-\d{2}-\d{2}$` before it reaches the filesystem (`_load_run_or_404`),
as defence-in-depth against path tricks in the `data/runs/` filename.

| Method | Path | Purpose |
|---|---|---|
| GET | `/healthz` | Liveness check (no auth) |
| GET | `/` | Index: run history + "start run" form |
| GET | `/dashboard` | Trends dashboard page (3-run gate) |
| GET | `/dashboard/data` | Trends JSON; `?range=4\|8\|12\|all&keyword=<kw>\|all` |
| POST | `/run` | Create/open a run for a date (idempotent) |
| GET | `/run/<date>` | Run page (SERP Overview + Ads Intelligence tabs) |
| POST | `/run/<date>/keyword/<idx>/process` | Classify + extract ads for one keyword |
| POST | `/run/<date>/keyword/<idx>/save` | Persist analyst edits to positions |
| GET | `/run/<date>/generate` | Download the `.xlsx` |
| GET | `/run/<date>/intelligence` | Run Intelligence page |
| POST | `/run/<date>/intelligence/generate` | Run feature extraction + PAA clustering |
| GET | `/run/<date>/intelligence/pdf` | Download Run Intelligence PDF |
| GET | `/run/<date>/ads-report` | Generate + download Ads Intelligence PDF |

**Intelligence generation** runs `extract_serp_features` for all keywords **in parallel**
(`ThreadPoolExecutor`, up to 10 workers) then one PAA-clustering call. It is **hash-stable**:
each keyword stores a hash of the `raw_paste` it was extracted from, and a re-generate only
re-extracts keywords whose paste actually changed (`force=true` from the Regenerate button).
This avoids LLM non-determinism shifting counts on unchanged data.

---

## 10. Configuration (env vars)

Set in `.env` (local) or the systemd `EnvironmentFile` (prod). See `.env.example`.

| Var | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | — | required |
| `OPENAI_MODEL` | `gpt-4o-mini` | extraction/classification calls |
| `OPENAI_REPORT_MODEL` | `gpt-4o` | analysis: ads report + PAA clustering |
| `APP_USERNAME` | `admin` | Basic Auth user |
| `APP_PASSWORD` | — | Basic Auth password (auth disabled if unset) |
| `FLASK_SECRET_KEY` | random per boot | set a fixed hex value in prod |

---

## 11. Deployment (production — DigitalOcean VPS)

Production runs on an Ubuntu 24.04 VPS — a **shared box** that also hosts other apps.
The live URL is **`https://209.97.176.252:1539`** (note `https`). The repo lives at
`/opt/raulreport`.

**Request path:** browser → **nginx** (TLS termination on `:1539`) → **gunicorn**
(`127.0.0.1:8011`) → Flask. gunicorn is *not* internet-facing; nginx is the only thing
that talks to it. The cert is **self-signed** (`/etc/ssl/raulreport/`, CN/SAN = the bare
IP — no domain exists, so Let's Encrypt isn't possible), hence a one-time browser
"not trusted" warning. Plain HTTP to `:1539` returns nginx 400. `app.py` adds `ProxyFix`
(`x_for=1, x_proto=1`) so the real client IP reaches the rate limiter and `request.scheme`
reflects HTTPS — safe because gunicorn binds localhost, so nginx is the sole client.

**systemd unit** (`/etc/systemd/system/raulreport.service`) runs as a dedicated
non-root `raulreport` user with sandboxing (`NoNewPrivileges`, `ProtectSystem=strict`
with `ReadWritePaths=/opt/raulreport/data`, `ProtectHome`, `PrivateTmp`, etc.) and:

```
ExecStart=/opt/raulreport/venv/bin/gunicorn -w 2 --timeout 300 -b 127.0.0.1:8011 app:app
EnvironmentFile=/opt/raulreport/.env
```

> Gotcha: `load_dotenv()` opens `.env` at import and raises `PermissionError` if the file
> exists but is unreadable — so `.env` must be group-readable by the service user (640),
> not 600 root-only.

The `--timeout 300` matters: intelligence generation makes ~26 parallel LLM calls and the
default 30 s gunicorn timeout would kill the worker mid-request (symptom: client sees an
HTML error page — `Unexpected token '<' … is not valid JSON`).

**Routine deploy** (the repo dir is root-owned, so run as root):

```bash
sudo -i
cd /opt/raulreport && git pull
# if requirements.txt changed (e.g. Flask-Limiter):
source venv/bin/activate && pip install -r requirements.txt && deactivate
systemctl restart raulreport
systemctl status raulreport --no-pager
```

Verify the full chain: `curl -sk https://localhost:1539/healthz` → `{"ok":true}`.
Logs: `journalctl -u raulreport -f`.

> `DEPLOYMENT.md` at the repo root documents an **alternative** PythonAnywhere deployment and
> is what `wsgi.py` references. The VPS above is the live production environment. See the
> hardening log in `done.md` for the full security-pass details (firewall, sudo scope, cert).

---

## 12. Extending the app

- **Add/change a category** → edit `CATEGORIES` in `config.py` only. The xlsx legend/summary/
  chart, UI dropdown/pills, and intelligence/trend colours all follow. If you add a *new key*,
  also add a definition + disambiguation example to `prompts/extract_and_classify.md` so the
  LLM can produce it, and (optionally) to `prompts/extract_ads.md` for ad landing domains.
- **Add an LLM task** → new prompt in `prompts/`, new wrapper + validator in `llm.py`
  following the existing retry/validate pattern.
- **Add a trends section** → new function in `trends.py`, include it in `build_dashboard`,
  render it in `templates/dashboard.html` + `static/charts.js`.
- **Storage changes** → add the field to the keyword/run init in `storage.create_run` and a
  focused `update_*` helper. Existing runs simply won't have the field; read with
  `.get(field)` and degrade gracefully (the codebase does this throughout).

---

## 13. Known constraints

- **Single analyst at a time.** No locking on concurrent edits to the same run; last write
  wins. Fine for the intended one-user workflow.
- **Dashboard needs ≥3 runs** and the viewer's browser needs internet (Chart.js CDN).
- **Reprocessing a keyword overwrites** its prior classification.
- **No automated scraping yet** — all SERP data comes from pasted text (Phase 5 covers live
  fetching; see `phase5.md`).
