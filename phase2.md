# RaulReport — Phase 2: Ads Intelligence
**Status:** Planning
**Requested by:** Manager
**Scope:** Paid search visibility layer — separate from organic SERP reporting

---

## Background

RaulReport Phase 1 classifies organic SERP results across 26 AU casino keywords and exports a structured Excel report. The tool works by accepting a raw SERP paste, running it through GPT-4o-mini, and returning ranked positions with warnings.

Phase 2 adds a paid ads intelligence layer. The LLM already receives the full SERP paste — ads are visible in the input. This is **extraction-only**, no new scraping is required for the MVP.

The manager's request:

> *"I need you to look at the core keyword and let me know which keywords ads are coming up — how many? To which landing pages? Are they promoting offshore casinos? Any intel you can gather."*

---

## Goals

- Surface paid ad data per keyword without touching the existing organic workflow
- Flag offshore operators clearly (AU compliance context)
- Keep ads reporting **separate** from the main xlsx export — this is analyst intel, not the boss's template
- Build an MVP fast, with a clear upgrade path to deeper scraping

---

## What's NOT Changing (Phase 2 Constraints)

| Item | Reason |
|---|---|
| xlsx export template | No ads column — boss's format stays intact |
| Save/edit workflow | Ads are read-only intel, analysts don't edit them |
| Auth & storage format | One new `ads: []` field per keyword, otherwise unchanged |
| Existing 6 endpoints | No new routes needed for MVP |

---

## MVP — Phase 2a: LLM Extraction from SERP Paste

Everything below is extraction from the existing input. No external calls.

### What the LLM extracts per keyword

| Field | Description |
|---|---|
| `advertiser` | Brand name as it appears in the ad |
| `landing_url` | The destination URL shown or inferred |
| `is_offshore` | Boolean — flagged against known AU licensing signals |
| `notes` | Freeform intel (e.g. "unlicensed", "targets AU market", "known brand") |
| `ad_position` | Top / Bottom / Shopping (where in the SERP) |

### Offshore flagging logic (prompt-level, Phase 2a)

The LLM is instructed to flag `is_offshore: true` when:
- Domain is not `.com.au`
- Brand is a known offshore operator (1xBet, BetWinner, 22Bet, etc.)
- Ad copy contains AU-targeting language but brand has no AU licence signal

This is heuristic — accuracy improves with the Phase 2b upgrade below.

### UI — Tab-Based Layout on `run.html`

The existing SERP overview table stays exactly as-is. Ads intel lives in a **second tab** on the same `run.html` page — no scrolling past organic results to find it, no layout disruption to the existing view.

```
┌─────────────────────┬──────────────────────┐
│  SERP Overview  ←   │   Ads Intelligence   │
└─────────────────────┴──────────────────────┘
```

**Tab 1 — SERP Overview** (unchanged)
The existing keyword cards, position table, warnings, and Save edits button. No changes.

**Tab 2 — Ads Intelligence**
A table across all 26 keywords showing every ad detected in the run:

```
Keyword                 │ Ads │ Offshore │ Advertisers
────────────────────────┼─────┼──────────┼──────────────────────────────
online casino australia │  3  │  ⚠ 2    │ BetWinner, Sportsbet, 1xBet
best online casino      │  1  │   0      │ Crown
poker online australia  │  0  │    —     │ —
...
```

Clicking a keyword row expands to show full ad detail:

```
▼ online casino australia — 3 ads, ⚠ 2 offshore

 #  │ Advertiser   │ Landing Page              │ Offshore │ Notes
────┼──────────────┼───────────────────────────┼──────────┼──────────────────────
 1  │ BetWinner    │ betwinner.com/au           │  YES ⚠  │ Unlicensed, targets AU
 2  │ Sportsbet    │ sportsbet.com.au/casino    │  no      │ Licensed AU operator
 3  │ 1xBet        │ 1xbet.com/en/casino        │  YES ⚠  │ Known offshore brand
```

**Tab badge** — the Ads Intelligence tab label shows a live count so analysts know at a glance if there's anything worth checking:

```
│   Ads Intelligence  ⚠ 11  │
```

Colour logic for the badge:
- **No badge** — no ads found across the run
- **Blue badge** — ads found, zero offshore
- **Amber badge** — 1–3 offshore detections
- **Red badge** — 4+ offshore detections

### Top-Level Ads Overview (new section on `index.html`)

A run-level summary visible on the index/history page:

```
Run: Week 21 — 26 May 2025
Organic: ✓ Complete    Ads Intel: 18/26 keywords had ads   ⚠ 11 offshore detections
```

Clicking through to `run.html` opens to Tab 1 (SERP Overview) by default; analysts switch to Tab 2 for ads detail.

---

## Files Changed — Phase 2a

| File | Change |
|---|---|
| `prompts/extract_and_classify.md` | Add Step 5 — paid ads extraction instructions with offshore heuristics ✅ (already drafted) |
| `llm.py` | Add ads list to `classify_paste()` return; validate structure |
| `storage.py` | Add `ads: []` to keyword data model; pass through `update_keyword()` |
| `app.py` | Pass ads from LLM → storage → JSON response on `/process` |
| `run.html` | Add tab switcher (SERP Overview / Ads Intelligence); Ads tab renders keyword-level summary table with expandable rows |
| `app.js` | Tab toggle logic; render ads table dynamically after Process returns; offshore badge count on tab label |

**Estimated effort:** 1 focused session with Claude Code across these 6 files.

---

## Phase 2b — Deeper Scraping (Post-MVP Upgrade)

Once the MVP is validated, this layer adds real-time ad verification by hitting the landing pages directly.

> ⚠️ This requires external HTTP calls from the server. Plan for rate limiting, rotating user agents, and possible blocking by affiliate tracking systems.

### What Phase 2b adds

| Enhancement | Detail |
|---|---|
| **Live landing page fetch** | Server-side GET to the landing URL — capture final redirect destination (affiliate links often redirect) |
| **Redirect chain logging** | Record the full chain: ad URL → tracker → final domain |
| **Title & meta extraction** | Grab `<title>` and `<meta name="description">` to confirm AU targeting in copy |
| **Licence badge detection** | Scrape for ACT/NT licence numbers, eCOGRA seals, "Australian" mentions |
| **Screenshot capture** | Optional — `playwright` headless screenshot stored per run for audit trail |
| **Offshore confidence score** | Weighted score replacing binary flag: domain + copy + redirect + brand list |

### New files for Phase 2b

| File | Purpose |
|---|---|
| `scraper.py` | Async fetch + redirect chain + basic HTML parse |
| `licence_check.py` | AU licence number pattern matching against ACMA / state lists |
| `data/offshore_brands.json` | Curated list of known offshore operators for lookup |

### Phase 2b UI additions

- Expand the ads table with a **"Verified"** column (timestamp of last live check)
- Add a **"Re-verify"** button per keyword to trigger a fresh scrape without reprocessing the whole SERP
- Redirect chain shown on hover/expand within the ads table row

### Phase 2b Infrastructure notes

- Rate limit scrape jobs (1 req/sec minimum)
- Store raw HTML snapshots in `data/runs/<run_id>/ads_html/` for audit
- Consider a job queue (even a simple in-memory list) if scraping 26 keywords serially is too slow — async with `aiohttp` is the right call here

---

## Reporting Separation Strategy

Ads data is **intentionally excluded** from the xlsx export. Rationale:

1. The boss's template has fixed columns — changing it risks the existing workflow
2. Ads intel is operational/analyst-facing, not the weekly deliverable
3. Offshore flagging is a compliance signal that warrants its own paper trail

**If a separate ads report export is later required**, the right approach is a new `ads_export.py` module producing a second workbook — not modifying `xlsx_export.py`.

---

## Open Questions

| Question | Who decides |
|---|---|
| Should offshore detections trigger an email alert? | Manager |
| How often should Phase 2b scraping run — on every Process, or on-demand? | Dev preference: on-demand first |
| Is there a known AU licence list we should hardcode, or rely on LLM heuristics only? | Compliance / manager |
| Should analysts be able to add manual notes to an ad entry? | Manager — currently read-only by design |

---

## Suggested Build Order

```
Phase 2a (MVP)
  1. prompts/extract_and_classify.md  ← already drafted
  2. llm.py                           ← add ads validation
  3. storage.py                       ← add ads field
  4. app.py                           ← wire through
  5. app.js                           ← render panel
  6. run.html                         ← ads table markup
  7. index.html                       ← run-level summary badge

Phase 2b (Scraping layer)
  8. data/offshore_brands.json        ← curated brand list
  9. scraper.py                       ← async fetch + redirect chain
 10. licence_check.py                 ← AU licence pattern matching
 11. app.py                           ← new /verify-ads endpoint
 12. run.html + app.js                ← verified column + re-verify button
```

---

