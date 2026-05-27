# RaulReport — Phase 3: Run Intelligence
**Status:** Planning
**Depends on:** Phase 1 (SERP Classifier) + Phase 2 (Ads Intelligence)
**New route:** `/run/<id>/intelligence`

---

## Goal

Give analysts and managers a deeper read on any weekly run without touching the core reporting workflow. The existing `/run/<id>` page stays clean and fast. Intelligence is a deliberate click-through — only when someone wants to go deeper.

---

## Entry Point

A single **"View Intelligence →"** link on the run page, placed unobtrusively near the top — not a tab, not a button that implies it's part of the weekly workflow. Analysts who just want to export never need to go there.

```
Week 21 — 26 May 2026   [Download XLSX]   [View Intelligence →]
```

---

## Page Layout — `/run/<id>/intelligence`

Four sections on a single scrollable page. No tabs — the intelligence view is already a deliberate destination, adding tabs inside it creates another layer of friction.

```
┌─────────────────────────────────────────┐
│  ← Back to Run    Week 21 Intelligence  │
├─────────────────────────────────────────┤
│  1. SERP Landscape                      │
│     Feature saturation, PAA questions,  │
│     featured snippet owners             │
├─────────────────────────────────────────┤
│  2. Snippet Language Analysis           │
│     Bonus copy, compliance signals,     │
│     freshness, content patterns         │
├─────────────────────────────────────────┤
│  3. Operator Visibility Index           │
│     Which operators / affiliates appear │
│     across how many of the 26 keywords  │
├─────────────────────────────────────────┤
│  4. People Also Ask                     │
│     All PAA questions across the run,   │
│     grouped by theme                    │
└─────────────────────────────────────────┘
```

---

## Section 1 — SERP Landscape

**What it answers:** How much of the SERP is Google vs organic content? Who owns the featured position?

### Data extracted per keyword (LLM, same SERP paste)

| Field | Description |
|---|---|
| `featured_snippet` | Domain that holds the answer box, or null |
| `featured_snippet_question` | The question it's answering |
| `has_paa` | Boolean — People Also Ask box present |
| `has_news_box` | Boolean — Top Stories present |
| `has_video_carousel` | Boolean |
| `has_knowledge_panel` | Boolean — brand entity surfaced |
| `has_shopping` | Boolean |
| `local_pack_present` | Boolean |
| `serp_feature_count` | Integer — total features detected |

### UI

A keyword-by-keyword table with icon flags per feature type:

```
Keyword                  │ Snippet │ PAA │ News │ Video │ KP │ Features
─────────────────────────┼─────────┼─────┼──────┼───────┼────┼─────────
online casino australia  │ aff.com │  ✓  │  ✓   │       │    │    3
best online casino       │    —    │  ✓  │      │  ✓    │    │    2
casino bonus australia   │ op.com  │  ✓  │      │       │ ✓  │    3
```

**Featured Snippet ownership summary** — below the table:

```
Featured Snippets this run: 14 keywords
  Affiliates hold:   9   (64%)
  Operators hold:    3   (21%)
  UGC holds:         2   (14%)
```

---

## Section 2 — Snippet Language Analysis

**What it answers:** What messaging is winning in the SERPs? Are competitors leading with bonuses, compliance, or brand?

### Data extracted per result (LLM, from snippet text already in paste)

| Field | Description |
|---|---|
| `bonus_language` | Boolean — welcome offer, bonus amount mentioned |
| `bonus_amount` | String — e.g. "$1000", "200 free spins" if present |
| `compliance_language` | Boolean — "licensed", "ACMA", "Australian regulated" |
| `freshness_year` | Integer — year mentioned in title/snippet, if any |
| `review_rating` | Float — star rating visible in SERP if present |
| `cta_language` | String — dominant CTA if detectable ("Play now", "Compare", "Read review") |

### UI

Two panels side by side:

**Bonus Copy Heat** — which keywords have the most aggressive bonus language in their top 10:
```
casino bonus australia    ████████████  9/10 results mention bonuses
online pokies             ████████      7/10
online casino australia   █████         5/10
```

**Compliance Language Map** — where are AU licensing signals showing up:
```
Keywords with 0 compliance mentions:  8  ← opportunity / concern flag
Keywords with 1–3 mentions:          12
Keywords with 4+ mentions:            6  ← regulated space
```

---

## Section 3 — Operator Visibility Index

**What it answers:** Which domains are actually winning across all 26 keywords? Identifies the real competitors and the dominant affiliates.

### Logic

Aggregate all domain appearances across all 26 keywords × top 10 positions. Score by:
- **Breadth** — how many keywords does this domain appear on?
- **Depth** — what average position does it hold?
- **Category** — OPERATOR, AFFILIATE, PARASITE etc (already classified)

No new LLM call needed — this is computed from existing Phase 1 data.

### UI

Ranked table, filterable by category:

```
[All] [Operators] [Affiliates] [Parasites] [UGC]

Rank │ Domain              │ Category  │ Keywords │ Avg Pos │ Best Pos
─────┼─────────────────────┼───────────┼──────────┼─────────┼─────────
  1  │ oddschecker.com     │ AFFILIATE │  18/26   │   3.2   │    1
  2  │ sportsbet.com.au    │ OPERATOR  │  14/26   │   4.8   │    2
  3  │ reddit.com          │ UGC       │  11/26   │   7.1   │    3
  4  │ casino.org          │ AFFILIATE │   9/26   │   2.9   │    1
```

**Operator gap analysis** — which licensed AU operators are absent from keywords where they should be visible:

```
⚠ CrownCasino.com.au — present on 4/26 keywords. Missing from:
  online pokies, best slots australia, +8 more
```

---

## Section 4 — People Also Ask

**What it answers:** What questions is Google associating with these keywords? Signals user intent, regulatory anxiety, content gaps.

### Data extracted per keyword

| Field | Description |
|---|---|
| `paa_questions` | Array of question strings detected in the SERP |

### LLM second pass — theme clustering

After extraction, a single LLM call groups all PAA questions across the full run into themes:

| Theme | Example questions | Count |
|---|---|---|
| Legality / regulation | "Is online casino legal in Australia?" | 14 |
| Best picks | "What is the best online casino in AU?" | 9 |
| Bonuses | "Which casino has the best welcome bonus?" | 7 |
| Safety | "Are online casinos safe in Australia?" | 5 |
| How-to | "How do I deposit at an online casino?" | 3 |

### UI

Accordion by theme. Each theme shows question count badge, expands to list the actual questions with the keyword they appeared on:

```
▼ Legality / Regulation  (14 questions)

  "Is online casino legal in Australia?"        → online casino australia
  "Is gambling online illegal in AU?"           → best online casino
  "What sites are legal for Australians?"       → legal online casino au
  ...
```

**Export** — a "Copy all PAA questions" button. Useful for content teams building FAQ sections.

---

## New Files

| File | Purpose |
|---|---|
| `prompts/extract_serp_features.md` | SERP feature extraction + snippet language analysis (one call per keyword) |
| `prompts/cluster_paa.md` | Theme clustering across all PAA questions (one call per run) |
| `intelligence.py` | Operator visibility index computation (no LLM — pure data aggregation) |
| `templates/intelligence.html` | New page — 4 sections, back link, no auth changes needed |

### Changes to existing files

| File | Change |
|---|---|
| `llm.py` | Add `extract_serp_features()` function — new prompt, same JSON mode pattern |
| `storage.py` | Add `serp_features: {}` and `paa: []` to keyword data model |
| `app.py` | New `/run/<id>/intelligence` route; trigger feature extraction alongside or after organic classification |
| `run.html` | Add "View Intelligence →" link |

---

## LLM Call Budget — Phase 3

Phase 1 already makes 1 call per keyword (organic classification).
Phase 2a adds 1 call per keyword (ads extraction).

Phase 3 adds:
- 1 call per keyword — SERP feature + snippet language extraction
- 1 call per run — PAA theme clustering

For a 26-keyword run: **+27 LLM calls** on top of the existing 52. All using GPT-4o-mini except the PAA clustering (GPT-4o for better grouping quality).

**Trigger options** — decide before building:

| Option | Behaviour |
|---|---|
| **Auto** | Intelligence extracted during Process, stored with run |
| **On-demand** | "Generate Intelligence" button — fires after the core run is saved |

Recommendation: **on-demand** for MVP. Keeps the Process flow fast, lets analysts skip it on weeks they don't need deep analysis. Can flip to auto later.

---

## What Phase 3 Does NOT Include

- Any HTTP requests to external URLs (that's Phase 4)
- Historical comparison / trend data (that's the Dashboard — Phase 4+)
- Editable fields — intelligence view is read-only
- Changes to the xlsx export

---

## Build Order

```
1. prompts/extract_serp_features.md    ← write prompt
2. prompts/cluster_paa.md              ← write prompt
3. storage.py                          ← add serp_features + paa fields
4. llm.py                              ← add extract_serp_features()
5. intelligence.py                     ← operator visibility aggregation
6. app.py                              ← new /intelligence route
7. templates/intelligence.html         ← 4-section page
8. run.html                            ← add "View Intelligence →" link
```

---

*Document owner: Raul — last updated May 2026*