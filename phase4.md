# RaulReport — Phase 4: Scraping Layer
**Status:** Planning
**Depends on:** Phase 1 + Phase 2 + Phase 3
**New infrastructure:** Async job queue, scraper module, per-run HTML snapshots

---

## Goal

Enrich SERP data with live intelligence pulled directly from the ranking URLs. Everything in Phases 1–3 came from the pasted SERP text. Phase 4 goes to the actual pages.

This is a separate infrastructure project. It does not change the core reporting workflow.

---

## What Scraping Unlocks

| Signal | Source | Phase 3 equivalent |
|---|---|---|
| Actual page title & H1 | Live fetch | Snippet text (partial) |
| Real landing URL after redirects | Redirect chain | Displayed URL only |
| Licence number on page | Page content | Compliance language flag (heuristic) |
| Bonus offer on landing page | Page content | Snippet mention (unreliable) |
| Page load / tech stack | Headers | None |
| Affiliate tracker chain | Redirect chain | None |
| Screenshot for audit | Headless browser | None |
| Ad landing page verification | Live fetch | URL from LLM extraction |

---

## Architecture

### The core problem with scraping in a Flask app

A synchronous scrape of 26 keywords × 10 results = 260 HTTP requests. At 1 req/sec minimum that's 4+ minutes. You cannot block a web request for 4 minutes.

**Solution: async job queue with a worker.**

```
Browser                  Flask App               Worker Process
   │                         │                         │
   │  POST /enrich/<run_id>   │                         │
   ├────────────────────────►│                         │
   │                         │  Add job to queue       │
   │                         ├────────────────────────►│
   │  202 Accepted           │                         │  Fetch URLs
   │◄────────────────────────┤                         │  Parse HTML
   │                         │                         │  Store results
   │  GET /enrich/status      │                         │
   ├────────────────────────►│                         │
   │  {done: 12, total: 260} │                         │
   │◄────────────────────────┤                         │
```

### Job queue — keep it simple for MVP

No Redis, no Celery. A **Python `threading.Thread` + in-memory queue** is enough for a single-server Flask app with one analyst using it at a time. If it needs to scale later, drop in RQ (Redis Queue) with minimal code changes.

```python
# scrape_queue.py
import queue, threading
job_queue = queue.Queue()

def worker():
    while True:
        job = job_queue.get()
        process_scrape_job(job)
        job_queue.task_done()

threading.Thread(target=worker, daemon=True).start()
```

---

## Scraping Scope — Two Tiers

### Tier 1 — Lightweight fetch (default, runs on every enrichment)

Fast, low risk of blocking. Pure `requests` + `BeautifulSoup`.

Per URL:
- Follow redirects, log full chain
- Capture final domain (resolves affiliate trackers)
- Extract `<title>`, first `<h1>`, `<meta name="description">`
- Scan for AU licence number patterns (regex: ACT/NT/state gambling authority formats)
- Scan for known compliance badge text ("eCOGRA", "ACMA", "Responsible Gambling")
- Detect affiliate platform signals in URL params (`aff_id=`, `ref=`, `btag=`, etc.)
- Response code + load time

**Rate limit:** 1 req/2 sec, sequential per domain (don't hammer the same host).

### Tier 2 — Headless browser (on-demand, per keyword or per URL)

For pages that block `requests` or require JS to render. Uses `playwright`.

Additional capabilities:
- Full-page screenshot stored as PNG
- Rendered HTML after JS execution
- Cookie consent / geo-redirect detection ("this site not available in your region")
- Interstitial / age-gate detection

Tier 2 is slower and more likely to get blocked. Treat it as an investigative tool, not a bulk operation. Analysts trigger it manually on specific URLs.

---

## Offshore Verification Upgrade

Phase 2a flagged offshore operators using LLM heuristics against a hardcoded brand list. Phase 4 adds **verification**:

```
Phase 2a:  is_offshore = LLM guess based on domain + brand name
Phase 4:   is_offshore_verified = confirmed by:
             - No AU licence number found on landing page
             - Domain not .com.au AND no ACT/NT licence text
             - Affiliate tracker chain routes through known offshore network
             - Geo-redirect detected (site serves AU users differently)
```

The ads table in Phase 2a gets a new **"Verified"** column with timestamp. Unverified rows keep the existing heuristic flag. Verified rows show a checkmark and the evidence source.

---

## Data Storage

### New fields on keyword records

```json
{
  "results": [
    {
      "position": 1,
      "domain": "oddschecker.com",
      "url": "https://...",
      "scrape": {
        "status": "done",
        "fetched_at": "2026-05-27T14:00:00Z",
        "final_url": "https://oddschecker.com/au/casino",
        "redirect_chain": ["https://track.aff.com/?id=123", "..."],
        "title": "Best Online Casinos Australia 2026",
        "h1": "Top AU Casino Sites",
        "licence_numbers": [],
        "compliance_badges": ["eCOGRA"],
        "affiliate_signals": ["btag=", "ref=odds"],
        "load_ms": 842,
        "tier2_screenshot": null
      }
    }
  ]
}
```

### HTML snapshots

Raw HTML stored separately — not in the main JSON (too large). Path convention:

```
data/runs/<run_id>/snapshots/<keyword_slug>/<position>_<domain>.html
```

Gitignored. Kept for 90 days then pruned. Useful for audit trail on offshore verification disputes.

---

## New Files

| File | Purpose |
|---|---|
| `scraper.py` | Tier 1 fetch — requests + BeautifulSoup, redirect chain, licence scan |
| `scrape_queue.py` | In-memory job queue + worker thread |
| `headless.py` | Tier 2 playwright wrapper — screenshot, rendered HTML |
| `licence_check.py` | AU licence number patterns + compliance badge detection |
| `data/offshore_brands.json` | Curated list of known offshore operators (augments LLM heuristic) |
| `data/affiliate_params.json` | Known affiliate URL parameter signatures |

### Changes to existing files

| File | Change |
|---|---|
| `storage.py` | Add `scrape: {}` object to result records; helper to write snapshots |
| `app.py` | New `/enrich/<run_id>` POST endpoint; `/enrich/status` GET for polling |
| `templates/intelligence.html` | Add enrichment trigger button + live progress indicator per section |
| `run.html` | "Enrich data 🔍" button — visible after run is saved |

---

## New Dependencies

| Package | Purpose |
|---|---|
| `requests` | Already available — Tier 1 fetching |
| `beautifulsoup4` | HTML parsing |
| `playwright` | Tier 2 headless browser (separate install: `playwright install chromium`) |
| `aiohttp` | Optional upgrade for parallel Tier 1 fetching if sequential proves too slow |

---

## UI — Enrichment Flow

### Triggering enrichment

On `run.html`, after a run is saved:

```
[Download XLSX]  [View Intelligence →]  [Enrich data 🔍]
```

Clicking **Enrich data** opens a modal:

```
┌─────────────────────────────────────────────┐
│  Enrich Run — Week 21                       │
│                                             │
│  This will fetch 260 URLs and may take      │
│  5–8 minutes. You can close this page —     │
│  enrichment continues in the background.    │
│                                             │
│  Scope:  ● All keywords (260 URLs)          │
│          ○ Flagged keywords only (offshore) │
│          ○ Select keywords...               │
│                                             │
│  Tier:   ● Lightweight (recommended)        │
│          ○ Include headless browser         │
│                                             │
│           [Cancel]   [Start Enrichment]     │
└─────────────────────────────────────────────┘
```

### Progress tracking

A status bar on the intelligence page while enrichment runs:

```
Enrichment in progress...  142 / 260 URLs  ████████████░░░░░░  55%
Est. time remaining: 2 min
```

### Results in intelligence view

Once enrichment is complete, each section in the intelligence page gains an extra column or callout with live data. For example, the Operator Visibility Index gains:

```
Domain           │ Keywords │ Avg Pos │ Licence Found │ Affiliate Signals
─────────────────┼──────────┼─────────┼───────────────┼──────────────────
oddschecker.com  │  18/26   │   3.2   │      —        │ btag=, ref=
sportsbet.com.au │  14/26   │   4.8   │  ACT 88002     │ none
1xbet.com        │   3/26   │   2.1   │      ✗ none   │ aff_id=
```

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Sites block the scraper | High (casino/affiliate space) | Rotate user agents; respect robots.txt; Tier 2 fallback |
| Affiliate URLs redirect to geo-blocked pages | Medium | Log redirect chain; flag geo-block as a data point |
| Playwright install complexity on server | Medium | Document setup; provide install script |
| Scrape jobs pile up if triggered multiple times | Low | Lock enrichment per run — one active job at a time |
| HTML snapshots fill disk | Low | 90-day prune script in cron |

---

## What Phase 4 Does NOT Include

- A dashboard / trend view across multiple runs (separate roadmap item)
- Automated scheduled scraping (manual trigger only for MVP)
- Proxy rotation service (add if blocking becomes a significant problem)
- Any changes to xlsx export

---

## Build Order

```
1. data/offshore_brands.json        ← curate known offshore list
2. data/affiliate_params.json       ← known affiliate URL params
3. licence_check.py                 ← AU licence patterns + badge detection
4. scraper.py                       ← Tier 1 fetch + parsing
5. scrape_queue.py                  ← job queue + worker thread
6. storage.py                       ← add scrape fields + snapshot writer
7. app.py                           ← /enrich + /enrich/status endpoints
8. run.html                         ← Enrich button
9. intelligence.html                ← progress bar + enriched columns
10. headless.py                     ← Tier 2 (do last — most complex)
```

---

## Open Questions

| Question | Recommendation |
|---|---|
| Should enrichment run automatically after Process, or stay manual? | Manual — keeps Phase 1 workflow fast |
| Rotate user agents or use a fixed one? | Rotate from a short list; log block rate |
| Store screenshots locally or in object storage (S3)? | Local for MVP; S3 if storage becomes an issue |
| How long to retain HTML snapshots? | 90 days — covers quarterly review cycles |
| Should the ACMA licence list be fetched live or hardcoded? | Hardcoded JSON updated manually — ACMA's register isn't easily machine-readable |

---

*Document owner: Raul — last updated May 2026*