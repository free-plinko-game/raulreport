# RaulReport — Phase 4: Trends Dashboard
**Status:** Planning
**Depends on:** Phase 1 (SERP Classifier) — data accumulates automatically from every run
**New route:** `/dashboard`
**New infrastructure:** None — pure aggregation over existing JSON run files

---

## Why This Is Phase 4 (Not Later)

Everything here is already sitting on disk. Every weekly run produces a dated JSON file in `data/runs/`. No new scraping, no new LLM calls, no new dependencies. This is aggregation logic and charts — and it gets more valuable every week that passes.

Scraping (previously Phase 4) moves to Phase 5 because it requires real infrastructure. Trends just requires reading files you already have.

---

## Data Model Ground Truth (read first)

Three things the trend logic must respect — corrected against the live codebase:

1. **There is no `OFFSHORE` or `AFFILIATE` organic category.** The 11 organic
   categories are: `SUBDOMAIN`, `FLIPPED`, `EMD`, `HACKED`, `PARASITE`, `UGC`,
   `PUBLISHER`, `OPERATOR`, `GOV`, `APP`, `FAKE_CASINO` (see `config.py`).
   "Offshore" is an **ads-only** flag (`is_offshore` on ad records), never an
   organic position category. Wherever this doc says "offshore/fake share" for
   organic results, it means the **HOSTILE cluster**:
   `FAKE_CASINO + EMD + SUBDOMAIN + FLIPPED + HACKED`, contrasted against the
   **LEGIT cluster** `OPERATOR + PUBLISHER + GOV + UGC + APP`. (`PARASITE` is
   ambiguous — count it as hostile-leaning but show it as its own band.)
2. **The taxonomy expanded mid-history.** Early runs were classified with the
   old 8 categories — `FLIPPED`, `EMD`, `FAKE_CASINO` did not exist yet, so their
   bands are legitimately zero until the week they were introduced, and some
   domains now tagged `EMD` were `SUBDOMAIN` back then. The SERP Health and EMD
   sections must render this gracefully (no back-projection unless explicitly
   backfilled) and a small note should explain the break to the reader.
3. **Field names.** A run is `run["keywords"][i]` with `.positions` (each having
   `.category`, `.domain`, `.rank`), `.ads`, optional `.serp_features`. There is
   no `results` key (that was the scraping doc). Domains are normalized
   lowercase, `www.`-stripped (true prefix strip as of the Phase 4 bugfix), so
   they match cleanly across runs.

---

## The Core Questions Trends Answers

| Question | Signal |
|---|---|
| Is the SERP getting more or less hostile? | Offshore/fake domain share over time |
| Who's entrenched vs. who's testing the water? | Domain persistence across runs |
| What showed up this week that wasn't there before? | New entrant detection |
| Are throwaway EMDs sticking around or rotating fast? | EMD survival / churn rate |
| Which keywords are most volatile? | Position instability index |
| Is offshore ad pressure growing? | Ads-per-keyword trend + offshore flag rate |

---

## Entry Point

A top-level **Dashboard** link in the nav — always visible, sits alongside the run history list.

```
RaulReport   [Dashboard]   [Runs ▾]   Week 21
```

Minimum data to show the dashboard meaningfully: **3 runs**. Below that, surface a holding state:

```
┌─────────────────────────────────────────┐
│  Trends unlock after 3 runs.            │
│  You have 2. One more week to go.  🕐   │
└─────────────────────────────────────────┘
```

---

## Page Layout — `/dashboard`

```
┌──────────────────────────────────────────────────────┐
│  Dashboard                    [Last 4 weeks ▾]       │
├──────────────────┬───────────────────────────────────┤
│                  │                                   │
│  Keyword Filter  │   1. SERP Health Trend            │
│  [All 26 ▾]      │   2. New Entrants This Week       │
│                  │   3. Operator Visibility Index    │
│                  │   4. EMD / Throwaway Tracker      │
│                  │   5. Keyword Volatility           │
│                  │   6. Ads Pressure Trend           │
│                  │                                   │
└──────────────────┴───────────────────────────────────┘
```

**Time range selector** — defaults to last 4 runs (one month). Options: 4 / 8 / 12 / All.

**Keyword filter** — default "All 26". Analysts can scope the entire dashboard to a single keyword or a subset when investigating a specific term.

---

## Section 1 — SERP Health Trend

**What it shows:** Category composition across all keywords over time. The story of whether the SERPs are getting cleaner or dirtier.

### Data

For each run, count total filled result slots (≤ 26 keywords × 10) and break down
by the real category keys. Express as percentages. Categories absent in a given
run (e.g. `EMD` before it was introduced) are simply omitted / zero.

```json
{
  "2026-05-05": { "OPERATOR": 18, "PUBLISHER": 21, "PARASITE": 28, "UGC": 9, "SUBDOMAIN": 11, "GOV": 7 },
  "2026-05-27": { "OPERATOR": 17, "PUBLISHER": 14, "PARASITE": 29, "UGC": 8, "SUBDOMAIN": 9, "EMD": 11, "FAKE_CASINO": 5, "FLIPPED": 1, "GOV": 6 }
}
```

The headline derived metric is **Hostile Share %** =
`(FAKE_CASINO + EMD + SUBDOMAIN + FLIPPED + HACKED) / total filled slots`.

### UI

Stacked area chart — one band per category, colours pulled from `config.py`
(`Category.fill`) so the dashboard matches the xlsx legend and the rest of the UI.
X-axis is run dates, Y-axis is percentage share. Order the hostile-cluster bands
together at the bottom so the "dirty" share reads as one visual mass.

```
100% ┤░░░░░░░░  UGC / GOV / APP
     │▒▒▒▒▒▒▒▒  PUBLISHER
     │▓▓▓▓▓▓▓▓  OPERATOR
  50%┤████████  PARASITE
     │██████░░  SUBDOMAIN / FLIPPED / HACKED
     │▓▓▓▓▓▓▓▓  EMD + FAKE_CASINO   ← hostile cluster; if this grows, that's the alert
   0%┤────────────────────────────
     May 5   May 12  May 19  May 26
```

**Callout** — if Hostile Share rises more than 2 percentage points run-on-run,
surface a banner:

```
⚠  Hostile share up 3.1pp this run (24% → 27.1%). 4 new hostile domains detected.
```

---

## Section 2 — New Entrants This Week

**What it shows:** Domains appearing in the top 10 for a keyword this week that weren't there last week. The most operationally useful signal — new entrants are usually worth investigating.

### Logic

Diff the current run's domain set against the previous run for each keyword. A domain is a "new entrant" if it wasn't in the top 10 for that keyword in the prior run.

Flag (and sort to the top) if the new entrant is in the **hostile cluster** —
`category in {FAKE_CASINO, EMD, SUBDOMAIN, FLIPPED, HACKED}` — using the stored
LLM classification. No substring re-derivation needed; the category is already
on the position record.

### UI

Simple ranked list, most notable first (offshore/fake flagged to the top):

```
New this week — 7 domains across 5 keywords

⚠ casinoonlineaustralia2026.com  │ EMD         │ online casino australia  │ #4  ← NEW ⚠
⚠ royalreels-22.site             │ FAKE_CASINO │ best online casino       │ #7  ← NEW ⚠
  pokernews.com                  │ PUBLISHER   │ poker online australia   │ #3
  abc.net.au                     │ GOV         │ online gambling laws     │ #6
  ...
```

Each row links to the run where it appeared, opening at that keyword card.

---

## Section 3 — Operator Visibility Index (Cross-Run)

**What it shows:** Which domains are consistently present across runs vs. which are one-week appearances. Persistence = entrenchment. Phase 3 built the single-run OVI; this is the same table tracked over time.

### Data

For each domain, track:
- **Runs present** — how many of the last N runs did this domain appear in at least once
- **Keyword breadth** — average number of keywords per run
- **Average position** — rolling average
- **First seen / last seen** — date range
- **Trend** — position improving, stable, or declining

### UI

Table, sortable by any column. Default sort: runs present (descending).

```
Domain                │ Runs │ Keywords │ Avg Pos │ Trend   │ First Seen
──────────────────────┼──────┼──────────┼─────────┼─────────┼───────────
oddschecker.com       │  8/8 │  18/26   │   3.1   │ stable  │ May 5
royalreels-18.site    │  7/8 │   4/26   │   6.4   │  ↑ up   │ May 12  ⚠
sportsbet.com.au      │  8/8 │  14/26   │   4.9   │ stable  │ May 5
casino.org            │  6/8 │   9/26   │   2.8   │  ↓ down │ May 5
betwinner-au.com      │  3/8 │   2/26   │   8.1   │  ↑ up   │ May 19  ⚠
```

Hostile-cluster domains (FAKE_CASINO/EMD/SUBDOMAIN/FLIPPED/HACKED) flagged with ⚠,
using each domain's most recent classification. A domain present for 7/8 runs and
trending up is a different story than one at 3/8 and declining.

---

## Section 4 — EMD / Throwaway Tracker

**What it shows:** Exact-match domains are a known spam tactic in the AU casino space. This section tracks their lifecycle — when they appear, how long they survive, and whether they're replaced by successors.

### EMD Detection

Primary source: the stored `category == "EMD"` classification on each position —
the LLM already makes this call during Process, so the tracker just reads it.

**Backfill caveat:** runs predating the EMD category (pre-2026-05-27) have no `EMD`
tag; those domains were classified `SUBDOMAIN`. For historic continuity, optionally
re-flag old-run domains as likely-EMD via substring matching against `keywords.json`
(2+ keyword tokens in the domain name, e.g. `onlinepokiesau.net`), clearly marked as
inferred. New runs always use the real classification.

### UI

Two panels:

**Active EMDs** — currently appearing in the most recent run:

```
Domain                        │ Keyword              │ Position │ Weeks active
──────────────────────────────┼──────────────────────┼──────────┼─────────────
casinoonlineaustralia2026.com │ online casino aus    │    4     │     1  ← new
bestpokiesitesau.net          │ best pokie sites     │    7     │     3
onlinecasinobonus-au.site     │ casino bonus aus     │    2     │     1  ← new
```

**EMD Graveyard** — domains that appeared then disappeared:

```
Domain                     │ Active     │ Duration │ Peak position
───────────────────────────┼────────────┼──────────┼──────────────
casinoau2025.site          │ Apr–May    │  4 weeks │     3
bestcasinoaustralia.net    │ Mar–Apr    │  2 weeks │     6
pokiesonlineau.com         │ Mar only   │  1 week  │     8
```

Pattern recognition callout — if the tool detects a domain disappearing and a near-identical one appearing (e.g. `casinoau2025.site` → `casinoau2026.site`), flag it:

```
🔄 Possible successor detected: casinoau2025.site (gone) → casinoau2026.com (new, #3)
```

---

## Section 5 — Keyword Volatility Index

**What it shows:** Which of the 26 keywords have the most unstable SERPs — high churn in domains ranking, large position swings. Useful for prioritising where to focus attention.

### Volatility Score

Per keyword, per run transition:
- Count of domains that changed (entered or exited top 10)
- Sum of absolute position changes for domains present in both runs
- Weighted: new OFFSHORE/FAKE entrants add bonus volatility points

Rolling average across selected time range = volatility score (0–100).

### UI

Horizontal bar chart, keywords ranked by volatility score:

```
online casino australia   ████████████████████  78  ← most volatile
best online casino        ████████████████      62
casino bonus australia    ████████████          48
poker sites australia     ████████              31
...
sportsbet login           ██                     8  ← most stable
```

High-volatility keywords are where new entrants, EMDs, and offshore operators tend to cluster first — a useful early warning.

---

## Section 6 — Ads Pressure Trend

**What it shows:** Is paid search activity on these keywords growing or declining? Are offshore operators spending more or less over time?

*Only visible once Phase 2 (Ads Intelligence) data exists in the runs.*

### Data

Per run: total ads detected across all 26 keywords, and the offshore subset.

### UI

Dual line chart:

```
Ads detected (total)  ─────────────────────────
Offshore ads          ─  ─  ─  ─  ─  ─  ─  ─

25 ┤                              ╭────────
   │                         ╭───╯
20 ┤                    ╭────╯
   │               ╭────╯
15 ┤──────────────╯
   │· · · · · · · · · · · · ·╭· · · · · ·
 5 ┤                    ╭· · ╯
   │               ╭· · ╯
   ┤─────────────────────────────────────
     May 5   May 12   May 19   May 26
```

Advertisers appearing in 3+ consecutive runs flagged as persistent spenders — surfaced as a callout below the chart.

---

## New Files

| File | Purpose |
|---|---|
| `trends.py` | All aggregation logic — reads JSON run files, computes diffs, scores, OVI |
| `templates/dashboard.html` | Dashboard page — 6 sections, time range + keyword filters |
| `static/charts.js` | Chart rendering (Chart.js — already a common CDN include, no new dependency) |

### Changes to existing files

| File | Change |
|---|---|
| `app.py` | New `/dashboard` route; `/dashboard/data` JSON endpoint for async chart loading |
| `templates/base.html` | Add Dashboard link to nav |

---

## Dependencies

**None new.** Chart.js loaded from CDN in `dashboard.html`. All data is aggregated from existing JSON files in `data/runs/`.

---

## Performance Note

With 12+ runs and 26 keywords, the aggregation reads ~300+ JSON records per dashboard load. Fine for MVP. If it gets slow (unlikely before 50+ runs), add a `data/trends_cache.json` that rebuilds on each new run save rather than on each page load.

---

## Build Order

```
1. trends.py                  ← aggregation functions (no UI yet, test in isolation)
2. app.py                     ← /dashboard + /dashboard/data routes
3. templates/dashboard.html   ← page structure + filter controls
4. static/charts.js           ← Chart.js wrappers for each section
5. templates/base.html        ← nav link
```

---

## What Phase 4 Does NOT Include

- Any LLM calls — pure data aggregation
- Any HTTP requests / scraping (Phase 5)
- Automated alerts / email notifications (future)
- User-configurable thresholds for volatility scoring (hardcoded for MVP)

---

## Open Questions

| Question | Recommendation |
|---|---|
| Minimum runs before dashboard is shown? | 3 — below that, show a "keep running" holding state |
| Should the dashboard auto-refresh? | No — load on demand, analyst clicks when they want it |
| Export trends data to CSV? | Nice to have — add a "Export CSV" button per section post-MVP |
| Should volatility alerts surface on the index page? | Yes — a small ⚠ badge next to the most volatile keyword run, link to dashboard |

---

*Document owner: Raul — last updated May 2026*