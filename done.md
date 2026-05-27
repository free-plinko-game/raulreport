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

---

## Phase 2a — Ads Intelligence (2026-05-27)

### What was added

- `prompts/extract_and_classify.md` — new Step 4 instructs the LLM to extract
  paid ads separately from organic results. Fields: `position`, `ad_position`
  (top/bottom/shopping), `advertiser`, `display_url`, `landing_url`,
  `is_offshore` (boolean, flagged against a hardcoded list of ACMA-licensed AU
  brands), `notes`. Output schema updated to include `ads: []`.
- `llm.py` — `_validate_result` now returns a third value (ads list);
  `classify_paste` signature updated to `(positions, warnings, ads, usage)`.
  Invalid `ad_position` values coerced to `"top"`.
- `storage.py` — `ads: []` added to keyword init in `create_run`;
  `update_keyword` accepts `ads` param. `list_runs` now computes `total_ads`
  and `total_offshore` per run for the index badge.
- `app.py` — `process_keyword` unpacks the new ads return value, stores it,
  and includes it in the JSON response.
- `run.html` — tab-based layout: Tab 1 is the existing SERP Overview (unchanged),
  Tab 2 is Ads Intelligence. Tab 2 shows a run-level summary table (all 26
  keywords, click to expand per-keyword ad detail). Tab badge is colour-coded:
  blue (ads, zero offshore), amber (1–3 offshore), red (4+ offshore).
- `app.js` — tab toggle; `renderAdsTab(idx, ads)` rebuilds the summary row and
  detail table after Process; `updateAdsBadge()` keeps the tab label live.
- `index.html` — Ads Intel column on the run history table shows the same
  colour-coded badge (blue/amber/red) based on offshore count.
- `style.css` — tab bar, ads badge, ads summary/detail table styles.

### Phase 2b — Ads Intelligence PDF Report (2026-05-27)

- `prompts/ads_report_analysis.md` — LLM prompt for the analysis agent. Takes all
  ads data across all keywords and returns: `executive_summary`,
  `offshore_density_analysis`, `key_findings`, `ad_type_breakdown`, `top_advertisers`,
  `keyword_highlights`, and `classified_ads` (each ad enriched with `ad_type`).
  Six ad type classifications: `LICENSED_OPERATOR`, `OFFSHORE_OPERATOR`, `AFFILIATE`,
  `CRYPTO_CASINO`, `APP`, `OTHER`.
- `pdf_report.py` — `fpdf2`-based PDF builder. Cover page with key stats, executive
  summary, offshore density bar chart, ad type breakdown table, key findings,
  top advertisers table, keyword highlights, and full per-keyword detail.
  Uses `OPENAI_REPORT_MODEL` env var (defaults to `gpt-4o`) for better narrative quality.
- `llm.py` — `generate_ads_report_analysis(run_date, keywords_with_ads)` added.
- `app.py` — `GET /run/<date>/ads-report` endpoint: calls analysis LLM, builds PDF,
  streams download as `AUS_Ads_Intelligence_<date>.pdf`.
- `run.html` — "Download PDF Report" button on the Ads Intelligence tab header.
  Disabled until ads data exists.
- `app.js` — Fetch-based download handler with "Generating report…" spinner.
  Triggers browser save-as via blob URL.
- `requirements.txt` — `fpdf2==2.7.9` added.

### What's NOT in the xlsx
Ads data is intentionally excluded from the xlsx export — the boss's template
has fixed columns and ads intel is analyst-facing, not the weekly deliverable.

---

## Phase 3 — Run Intelligence (2026-05-27)

### What was added

- `prompts/extract_serp_features.md` — LLM prompt that analyses a raw SERP paste and
  returns structured SERP feature data: `featured_snippet_domain`, `has_paa`,
  `paa_questions[]`, `has_news_box`, `has_video_carousel`, `has_knowledge_panel`,
  `has_shopping`, `local_pack_present`, `serp_feature_count`, and a `snippet_analysis`
  block (bonus language count, compliance language count, bonus amounts, CTA types,
  freshness years, review ratings flag). One LLM call per keyword, uses `gpt-4o-mini`.
- `prompts/cluster_paa.md` — LLM prompt that groups all PAA questions from a run into
  thematic clusters. Input: list of `{question, keyword}`. Output: `clusters[]` with
  `theme`, `question_count`, and `questions[]`. Uses `gpt-4o` for better grouping quality.
- `storage.py` — `serp_features: None` added to keyword init; `paa_clusters: None` and
  `intelligence_generated_at: None` added to run init. New helpers:
  `update_serp_features(run_date, idx, serp_features)` and
  `update_intelligence(run_date, paa_clusters)`.
- `llm.py` — `extract_serp_features(keyword, raw_paste)` and `cluster_paa(run_date,
  paa_items)` added. Path constants `SERP_FEATURES_PROMPT_PATH` and
  `CLUSTER_PAA_PROMPT_PATH` added.
- `intelligence.py` — NEW pure-aggregation module (no LLM calls):
  - `operator_visibility_index(keywords)` — ranks domains by keyword breadth with
    keyword_count, total_appearances, avg_position, best_position, category.
  - `serp_landscape_summary(keywords)` — aggregates SERP feature flags across all
    keywords; computes snippet ownership breakdown by category.
  - `snippet_language_summary(keywords)` — bonus heat list, compliance distribution
    buckets, all CTA types, freshness years.
- `app.py` — two new routes:
  - `GET  /run/<date>/intelligence` — renders the intelligence page; calls all three
    aggregation functions if intelligence has been generated.
  - `POST /run/<date>/intelligence/generate` — loops over all keywords with raw_paste,
    calls `extract_serp_features` (skipping already-extracted), then clusters PAA,
    then calls `storage.update_intelligence`. On-demand to keep the Process workflow fast.
- `templates/intelligence.html` — 4-section page:
  1. SERP Landscape — stat row (snippet/PAA/news/video/KP/shopping counts), snippet
     ownership bar chart by category, keyword detail table.
  2. Snippet Language Analysis — bonus copy density heat bars, compliance distribution
     buckets, CTA pattern pills, freshness years.
  3. Operator Visibility Index — filterable table by category with JS re-numbering.
     Structured for Phase 4 column extensions (Licence Found, Affiliate Signals).
  4. People Also Ask — accordion clusters with question count badges and
     "Copy all questions" button.
- `static/intelligence.js` — generate button handler, OVI category filter with
  row re-numbering, PAA copy-to-clipboard with textarea fallback.
- `static/style.css` — intelligence page styles added (stat row, snippet bars, heat
  bars, compliance buckets, OVI filter buttons, PAA accordion, CTA pills).
- `run.html` — "View Intelligence →" link added to the progress bar row alongside
  "Generate XLSX", always visible regardless of processing state.

### Design decisions

- **On-demand generation**: `generate_intelligence` is triggered by button click, not
  automatically on run completion — 27+ LLM calls would make the weekly Process workflow
  significantly slower.
- **Skip already-extracted**: on Regenerate, keywords with existing `serp_features` are
  skipped. PAA clustering always re-runs (it's one call and clusters may shift with new
  keywords).
- **Graceful errors**: individual keyword failures are collected and returned in the JSON
  response; partial results are still stored and displayed.

## File tree

```
.
├── app.py
├── intelligence.py
├── llm.py
├── pdf_report.py
├── storage.py
├── xlsx_export.py
├── requirements.txt
├── .env.example
├── .gitignore
├── data/
│   ├── keywords.json
│   └── runs/                 # generated, gitignored
├── prompts/
│   ├── extract_and_classify.md
│   ├── extract_ads.md
│   ├── ads_report_analysis.md
│   ├── extract_serp_features.md
│   └── cluster_paa.md
├── static/
│   ├── app.js
│   ├── intelligence.js
│   └── style.css
└── templates/
    ├── base.html
    ├── index.html
    ├── intelligence.html
    └── run.html
```
