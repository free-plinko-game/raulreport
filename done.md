# Done — SERP Classifier v1

Internal Flask tool per `requirements.md`. Built 2026-05-19.

## What was built

### Backend (Python 3.11+, Flask 3.0)
- `app.py` — Flask app with HTTP Basic Auth, all 7 endpoints in §5:
  - `GET  /healthz` (no auth, liveness check)
  - `GET  /` (lists past runs, "Start new run" form)
  - `POST /run` (creates `./data/runs/<date>.json`, idempotent — opens existing)
  - `GET  /run/<date>` (renders 26 keyword cards)
  - `POST /run/<date>/keyword/<idx>/process` (calls LLM, stores positions)
  - `POST /run/<date>/keyword/<idx>/save` (persists analyst edits, validates categories)
  - `GET  /run/<date>/generate` (streams xlsx download)
- `storage.py` — JSON-on-disk with atomic writes (`os.replace` via `.tmp`). Auto-derives
  run `status` (in_progress / complete) on every save.
- `llm.py` — OpenAI Chat Completions wrapper. Uses JSON mode, exponential backoff
  (max 3 retries on rate-limit / timeout / API errors), single JSON-parse retry on
  malformed responses, falls back to PARASITE + warning on invalid category strings.
  Model configurable via `OPENAI_MODEL` env var (default `gpt-4o-mini`).
- `xlsx_export.py` — `openpyxl` workbook builder. Reproduces the boss's template
  layout from §9 — legend (rows 5-13), 26-keyword block (rows 15-41), summary +
  TOTAL formulas (rows 45-54). Body cell colours per §7 with appropriate
  white-on-dark font where contrast demands.

### LLM prompt
- `prompts/extract_and_classify.md` — system prompt with the full 8-category
  taxonomy, SERP-feature handling rules (ads, PAA, featured snippet, Top Stories,
  Reddit clusters, sitelinks, breadcrumbs), `short_label` conventions, and a
  strict JSON output schema. Domain examples seeded from the supplied template.

### Frontend (server-rendered + vanilla JS)
- `templates/base.html`, `templates/index.html`, `templates/run.html`
- `static/style.css`, `static/app.js`
- Accordion keyword cards (open by default until processed, then collapsed)
- Live progress bar, "Generate XLSX" enabled once 26/26 done
- Per-row editing with category dropdown — dirty rows highlighted, save persists
- Warnings rendered as yellow banners above each review table
- No build step, no SPA framework — pure progressive enhancement

### Config
- `requirements.txt` — pinned: Flask 3.0.3, openpyxl 3.1.5, openai 1.54.4, python-dotenv 1.0.1
- `.env.example` — `OPENAI_API_KEY`, `OPENAI_MODEL`, `APP_USERNAME`, `APP_PASSWORD`, `FLASK_SECRET_KEY`
- `.gitignore` — excludes `.env`, `data/runs/`, generated xlsx files
- `data/keywords.json` — 26 keywords loaded from `keywords.txt`

## How to run

```
pip install -r requirements.txt
cp .env.example .env       # fill in OPENAI_API_KEY + APP_PASSWORD
python app.py              # serves http://127.0.0.1:5000
```

Then open `/`, "Start run", paste SERP text into each card, click Process, edit
the review table if needed, click Save. When all 26 keywords are green, click
"Generate XLSX".

## Smoke-test results

- `python -m py_compile` clean across all 4 modules.
- `xlsx_export.build_workbook` round-trip: structural cells (date, legend, 26
  keyword rows, summary header, TOTAL formulas) match the template byte-positions.
- Flask test-client run-through: auth challenge on `/`, healthz no-auth, run
  rendering, xlsx download streaming, save endpoint validates bad + good
  payloads, process endpoint rejects empty paste with 400 — all return expected
  status codes.

## Decisions / deviations

- **OPERATOR vs OPERATORS**: the supplied template uses both — "OPERATORS"
  in the legend with grey fill, "OPERATOR" in the summary block also grey, while
  body cells with operator data use the navy `1F3864` from §7. Exporter matches
  this exactly so the boss's file looks the same.
- **Idempotent run creation**: posting `/run` with an existing date opens the
  run rather than overwriting it (avoids accidental data loss).
- **Atomic JSON writes**: every keyword save writes through a `.tmp` file and
  `os.replace` so a crash can't half-write the run state.
- **Open questions in §14 deferred** to v1.1 — runs are kept forever, reprocess
  silently overwrites edits, in-progress runs are not migrated when
  `keywords.json` changes.

## File tree

```
.
├── app.py
├── llm.py
├── storage.py
├── xlsx_export.py
├── requirements.txt
├── .env.example
├── .gitignore
├── data/
│   ├── keywords.json
│   └── runs/                 # generated, gitignored
├── prompts/
│   └── extract_and_classify.md
├── static/
│   ├── app.js
│   └── style.css
└── templates/
    ├── base.html
    ├── index.html
    └── run.html
```
