# RaulReport — User Guide

This guide is for the analyst running the weekly report. No coding required. For the
technical reference see [TECHNICAL.md](TECHNICAL.md).

---

## What this tool is for

Every week we monitor how 26 Australian online-casino keywords look on Google — which kinds
of sites are ranking, whether offshore/illegitimate operators are showing up, and how that
changes over time. This tool turns the raw Google results into the classified spreadsheet
the team uses, and adds extra reports on top.

You do the searching and the judgement calls. The tool does the typing, classifying,
colour-coding, counting, and charting.

---

## Logging in

Open the app URL in your browser. You'll get a username/password prompt — use the credentials
you were given. (Production lives at **`https://209.97.176.252:1539`** — note the `https`.
On first visit you'll see a certificate warning because it uses a self-signed cert for an
internal tool; click "Proceed anyway" — the connection is still encrypted.)

The top bar has two links: the app name (your run history / home) and **Dashboard** (trends).

---

## The weekly workflow

### 1. Start a run

On the home page, pick the date and click to start a run. A "run" is one week's report.
If a run already exists for that date, you'll just reopen it — nothing is overwritten.

You land on the **run page**, showing all 26 keywords as collapsible cards and a progress
bar (`0 / 26 processed`).

### 2. Process each keyword

For each keyword:

1. **Search it on Google** (VPN to Australia, as usual) so you see the real AU results.
2. **Select all the page text and copy it** — the whole SERP, ads and all. Don't worry about
   tidying it; paste the lot.
3. In the keyword's card, **paste** into the box and click **Process**.
4. The tool calls the AI, then shows a **review table** of the top 10 organic results, each
   with a suggested **category**.
5. **Check the categories.** The AI is good but not perfect. Use the dropdown to fix any that
   are wrong (see the category cheat-sheet below). Edited rows are marked.
6. Click **Save edits**.

The card turns green and the progress bar advances. Repeat for all 26.

> Tip: there's a **copy** button on each keyword name so you can paste it straight into Google.

### 3. Download the spreadsheet

Once all 26 are processed, the **Generate XLSX** button activates. Click it to download the
`.xlsx` in the exact template format — legend, colour-coded grid, market-share summary, and
the doughnut chart, all filled in. This is the weekly deliverable.

---

## The 11 categories (cheat-sheet)

When reviewing, this is what each label means. The trickiest distinctions are between the
"spammy domain" types — the rule of thumb is in brackets.

| Category | Meaning |
|---|---|
| **SUBDOMAIN & TLD ABUSE** | Casino spam living in a *subdomain* of another site, or on a throwaway/pseudo TLD (`.site`, `.club`, `.online`, `.co.com`). *(spam lives in the subdomain/TLD)* |
| **FLIPPED** | A domain that used to be a normal business/personal site, now turned *entirely* into a casino. *(old site gone, whole domain is casino now)* |
| **EXACT MATCH DOMAIN (EMD)** | A purpose-built domain whose name *is* the keyword phrase, e.g. `real-money-casino-aus.online`. *(the domain name is the keywords)* |
| **HACKED** | A real, still-working unrelated site that's been compromised to host casino pages on some URLs. *(legit site still live, casino hidden on paths)* |
| **PARASITE** | A legit news/general site with an affiliate casino section bolted on. *(real site, casino is just one section)* |
| **UGC** | User content — Reddit, Trustpilot, Quora, forums, YouTube. |
| **PUBLISHER** | A legitimate gambling-industry review hub. |
| **OPERATORS** | A licensed, legitimate casino/sportsbook running its own site. |
| **GOV** | Government, regulator, or government-funded help service. |
| **APP** | An app-store listing (Google Play / App Store). |
| **Fake Casino** | A site acting as a casino but an unlicensed offshore imposter (not a real licensed operator). |

If two could apply, pick your best judgement — the AI also leaves a **warning** (yellow
banner) on rows it found ambiguous, so look there first.

---

## Ads Intelligence

On the run page, switch to the **Ads Intelligence** tab. As you process keywords, the tool
also pulls out the **paid ads** for each one — advertiser, landing page, ad position, whether
it looks **offshore**, and what kind of domain it points to.

The tab badge is colour-coded so you can see at a glance how much offshore ad pressure there
is (blue = ads but none offshore, amber = some, red = a lot).

Click **Download PDF Report** for a written analysis: an executive summary, offshore density,
a breakdown of ad types, the top advertisers, and per-keyword detail. This is a separate AI
pass and takes a little while to generate.

---

## Run Intelligence (deeper analysis)

From the run page, click **View Intelligence →**. This is optional, on-demand analysis of a
single week. Click **Generate Intelligence** and wait ~30–60 seconds (it analyses every
keyword). You'll get four sections:

1. **SERP Landscape** — which Google features appear (featured snippets, People-Also-Ask,
   news, video, etc.) and who owns the featured snippets.
2. **Snippet Language** — how much bonus/promo language vs. compliance language shows up, plus
   call-to-action patterns.
3. **Operator Visibility Index** — which domains rank across the most keywords this week.
4. **People Also Ask** — the PAA questions grouped into themes (with a "copy all" button).

There's a **Download PDF** button once it's generated. If you re-scrape a keyword later,
hit **Regenerate** — it only re-analyses keywords whose text actually changed.

---

## Trends Dashboard

The **Dashboard** link (top bar) shows how things change *across* weeks. It needs at least
**3 runs** of history before it unlocks — until then it shows a "keep running" message.

You can scope it with the **Range** (last 4 / 8 / 12 / all runs) and **Keyword** filters.
Sections:

1. **SERP Health Trend** — the category mix over time. The "hostile" share (Fake Casino + EMD
   + Subdomain + Flipped + Hacked) is the headline signal; a banner warns if it jumps.
2. **New Entrants** — domains that appeared this week but weren't there last week (hostile
   ones flagged first — these are usually worth a look).
3. **Operator Visibility Index** — which domains are *entrenched* (present most weeks) vs.
   one-offs, and whether they're rising or falling.
4. **EMD / Throwaway Tracker** — exact-match spam domains currently active, plus a "graveyard"
   of ones that have disappeared.
5. **Keyword Volatility** — which keywords have the most churn (good early-warning signal).
6. **Ads Pressure** — total and offshore ad counts over time.

> The charts load from the internet, so you need to be online to view the dashboard.

---

## Tips & gotchas

- **Paste the whole SERP**, ads and all. The tool handles separating ads from organic results.
- **Always review categories** before saving — the AI handles the obvious cases well but the
  spammy-domain distinctions need a human eye.
- **The spreadsheet only unlocks at 26/26.** If the button is greyed out, you have keywords
  left to process.
- **Re-processing a keyword replaces** its previous result — only re-do one if you mean to.
- **Older weeks won't show the newer categories** (Flipped / EMD / Fake Casino were added
  later) — that's expected, not a bug.
- If a report **takes a while or seems stuck**, give it time — the PDF and intelligence steps
  make multiple AI calls. If you get an error mentioning JSON, refresh and try again; if it
  persists, flag it to whoever maintains the app.
