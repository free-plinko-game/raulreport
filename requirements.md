# SERP Classifier — Requirements

Update done.md with all changes.

## 1. Purpose

Internal Flask tool that replaces the manual SERP-to-spreadsheet workflow used to monitor 26 Australian online casino keywords each week.

The current process:
1. VPN to Australia, search each keyword on Google manually
2. Copy each result URL into the right cell of a spreadsheet
3. Classify each URL into one of 8 categories
4. Apply colour coding and summary counts

The new process:
1. For each keyword, copy the raw SERP page text and paste it into a textarea
2. Backend calls OpenAI to extract the top 10 organic results AND classify each
3. User reviews / edits the result list
4. After all keywords, user downloads the finished `.xlsx` in the existing template format

Primary user: SEO analyst (vibe coder, comfortable with Flask). Secondary user: OOO coverage person (less technical — should be able to use it with just a quick onboarding doc).

---

## 2. Tech stack

- **Backend**: Python 3.11+, Flask
- **LLM**: OpenAI API. Default model: `gpt-4o-mini` (cheap and good enough at this extraction task). Configurable via env var.
- **XLSX**: `openpyxl` (matches the existing scripts)
- **Storage**: JSON files on disk under `./data/runs/<YYYY-MM-DD>/`. No database needed for v1.
- **Secrets**: `python-dotenv` for `.env` file (gitignored). Production: env vars on the host.
- **Frontend**: HTML + vanilla JS or HTMX. No build step. Keep dependencies minimal.
- **Auth**: HTTP Basic Auth (single shared password from env var) is fine for v1 — internal-only tool.

---

## 3. User flow

```
┌──────────────────────────────────────────────────────────────┐
│ /                                                            │
│  - Lists past runs, "Start new run" button                   │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ /run/<YYYY-MM-DD>                                            │
│  - Shows 26 keyword cards (collapsible)                      │
│  - Progress bar "X / 26 keywords processed"                  │
│  - Each card: status (empty / processed / edited)            │
│  - "Generate XLSX" button (enabled when all 26 done)         │
└──────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┴──────────────┐
              ▼                            ▼
┌──────────────────────────┐  ┌──────────────────────────────┐
│ Per-keyword card         │  │ /run/<id>/generate           │
│  - Paste textarea        │  │  - Builds xlsx from JSON     │
│  - "Process" button      │  │  - Returns download          │
│  - On submit:            │  └──────────────────────────────┘
│      POST to LLM endpoint│
│      shows spinner       │
│  - Review pane:          │
│      table of 10 rows    │
│      each row editable   │
│      (short_label,       │
│       category dropdown) │
│  - "Save" button         │
└──────────────────────────┘
```

A keyword can be reprocessed (re-paste, re-call LLM, overwrite). Edits to the review pane persist until the next reprocess.

---

## 4. Data model

One JSON file per run: `./data/runs/<YYYY-MM-DD>.json`

```json
{
  "run_date": "2026-05-25",
  "status": "in_progress",            // in_progress | complete
  "created_at": "2026-05-25T08:30:00Z",
  "updated_at": "2026-05-25T09:12:00Z",
  "keywords": [
    {
      "keyword": "Australian online casinos",
      "processed_at": "2026-05-25T08:35:00Z",
      "raw_paste": "...full paste text...",
      "positions": [
        {
          "rank": 1,
          "short_label": "Trustpilot",
          "domain": "au.trustpilot.com",
          "full_url": "https://au.trustpilot.com/review/...",
          "category": "UGC",
          "reasoning": "User-review aggregator",
          "edited": false
        }
      ],
      "warnings": []
    }
  ]
}
```

The keyword list is fixed and lives in `./data/keywords.json` (a flat array of 26 strings). The boss has tweaked the list before — making it a config file means no code change to update.

---

## 5. Backend endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | List past runs, button to create new |
| `POST` | `/run` | Create new run (today's date). Returns `/run/<date>` |
| `GET` | `/run/<date>` | Run page with all keyword cards |
| `POST` | `/run/<date>/keyword/<idx>/process` | Send `raw_paste` to LLM, store positions, return JSON |
| `POST` | `/run/<date>/keyword/<idx>/save` | Save user-edited positions (overrides LLM output) |
| `GET` | `/run/<date>/generate` | Build and return the xlsx download |
| `GET` | `/healthz` | Liveness check (no auth) |

All endpoints except `/healthz` require HTTP Basic Auth.

---

## 6. OpenAI integration

### Model

Default: `gpt-4o-mini`. Use Chat Completions API with JSON mode (`response_format: { type: "json_object" }`).

### Prompt

System prompt: see `prompts/extract_and_classify.md` (separate file, easier to iterate). The prompt contains:

- The task description
- The 8-category taxonomy with full definitions and examples
- SERP feature handling rules (skip ads, skip PAA, collapse Reddit/Quora clusters, expand Top Stories, etc.)
- The short-label conventions
- The JSON output schema
- Decision heuristics for ambiguous cases

User message: the raw paste text plus the keyword (so the LLM has context for what the user was searching for).

### Output schema

```json
{
  "positions": [
    {
      "rank": 1,
      "short_label": "Trustpilot",
      "domain": "au.trustpilot.com",
      "full_url": "https://au.trustpilot.com/...",
      "category": "UGC",
      "reasoning": "User reviews aggregator"
    }
  ],
  "warnings": [
    {"rank": 7, "issue": "ambiguous between HACKED and PARASITE", "detail": "..."}
  ]
}
```

### Error handling

- Network/timeout errors: surface clearly in the UI with a retry button
- Malformed JSON from LLM: retry once, then show raw response to user with a manual entry option
- Rate limits: exponential backoff, max 3 retries

### Cost expectation

At ~3,000 input tokens per paste × 26 keywords + ~500 output tokens each, on `gpt-4o-mini`, expect well under $0.50 per full weekly run. Log usage so we can monitor.

---

## 7. Classification taxonomy

The LLM prompt contains the authoritative version. Quick reference:

| Category | Colour | What it is |
|---|---|---|
| **SUBDOMAIN** | Light pink `F4CCCC` | Pseudo-TLD spam, cheap-TLD casino brands, keyword-stuffed subdomains |
| **HACKED** | Dark red `C00000` (white text) | Legitimate domains compromised to host casino content |
| **PARASITE** | Orange `F6B26B` | Affiliate iGaming sections on news / general / industry sites |
| **UGC** | Light blue `B4C7E7` | Reddit, Trustpilot, Quora, forums, YouTube |
| **PUBLISHER** | Light green `C6E0B4` | Dedicated casino review hubs (narrow definition) |
| **OPERATOR** | Navy `1F3864` (white text) | Licensed casino/betting brand sites |
| **GOV** | Dark green `548235` (white text) | Government, regulators, help services |
| **APP** | Blue `0070C0` (white text) | App store listings |

Example domains for each are in the existing scripts `update_serps.py` and `reformat_to_new_template.py` — those lists feed straight into the prompt.

---

## 8. SERP parsing rules (passed to LLM)

| Pattern | Action |
|---|---|
| `Sponsored result` / `Sponsored results` … `Hide sponsored result(s)` | Skip everything between |
| `People also ask` block | Skip until next result |
| Featured snippet at top | Roll into position 1 |
| `Top stories` section | Each news item gets its own position |
| Reddit cluster ending with `More results from www.reddit.com` | Collapse to one position, `short_label: "Reddit/Quora"` |
| App store URLs (`play.google.com`, `apps.apple.com`) | `short_label: "Apps"`, `category: APP` |
| `Read more`, `See more`, `#:~:text=...` fragments | Result-internal noise, ignore |
| Sitelinks (`* [...](#anchor)`, child bullets under a result) | Belong to the parent result, don't create new positions |

Input format may be plain text (breadcrumb URLs like `https://au.trustpilot.com › Gambling › Casino`) or Markdown (`[text](url)`). Prompt makes both explicit.

---

## 9. Output: xlsx format

Match the existing boss template exactly. See `AUS_SERP_classified_2026-05-15.xlsx` (current canonical example).

**Layout:**
- Row 2: `Date: <full date>`
- Row 3: `VPN mobile` (preserved as-is)
- Rows 5–13: Legend block (Label / Meaning) with the 8 categories, colour-coded
- Row 15: Column headers — `Keyword`, `1`, `2`, … `10`
- Rows 16–41: 26 keyword rows; URL cells in columns 2–11 hold `short_label` values, coloured per `category`
- Row 45: Summary header — `Category`, `MARKET SHARE %`, `Count`
- Rows 46–53: One row per category, count in column C, percentage formula in column B (`=C46/C54`)
- Row 54: `TOTAL` — `=SUM(B46:B53)` and `=SUM(C46:C53)`

Existing colour-fill logic lives in `reformat_to_new_template.py` — reuse it.

---

## 10. Configuration

`.env` (gitignored):

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
APP_USERNAME=admin
APP_PASSWORD=...
FLASK_SECRET_KEY=...
```

`./data/keywords.json`:

```json
[
  "Australian online casinos",
  "Best casino online australia",
  "online casino australia",
  ...
]
```

(Pull current 26 from any of the existing classified xlsx files — they all share the same list.)

---

## 11. Frontend notes

- Single page per run, no SPA needed
- Each keyword card: accordion (collapsed by default), opens to show paste textarea, process button, review table
- Progress bar at top: `12 / 26`
- Save to JSON on every action — no "save the whole form" flow. User can close the tab and resume.
- Review table: each row has `short_label` (text), `domain` (read-only), `category` (dropdown of 8 options), `reasoning` (tooltip on hover)
- Mark edited cells visually (e.g. small dot or italics) so user knows which were LLM vs user-corrected
- LLM warnings shown as yellow banners above the review table

---

## 12. Reference files

These exist in the repo and contain working logic / data the app can build on:

- `update_serps.py` — current classification rules (will become prompt examples)
- `reformat_to_new_template.py` — xlsx generation logic + new-taxonomy classifier
- `AUS_SERP_classified_2026-05-15.xlsx` — canonical xlsx template (boss's format)
- `AUS_SERP_classified_2026-05-18_new_format.xlsx` — most recent generated report

---

## 13. Out of scope for v1

- Multi-user / concurrent runs
- Auto-scraping SERPs (manual paste is the input by design)
- Public deployment / authentication beyond shared password
- Historical comparison views (`run A vs run B` delta)
- Automated weekly scheduling
- Management summary doc auto-generation
- New-rule learning (LLM doesn't need to "remember" between runs)

---

## 14. Open questions

1. **Storage retention**: keep all historical runs forever, or auto-prune after N weeks?
2. **Reprocess vs re-edit**: if user re-pastes a keyword and clicks Process, do we overwrite their previous edits silently, or warn?
3. **Keyword changes mid-run**: if `keywords.json` is edited while a run is in progress, what happens to the in-progress run?

Best handled by getting v1 in front of real users and seeing what comes up.