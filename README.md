# RaulReport — SERP Classifier

Internal Flask tool that monitors **26 Australian online-casino keywords** every week.
It replaces a slow manual spreadsheet workflow: instead of hand-classifying every Google
result, an analyst pastes the raw SERP text, an LLM extracts and classifies the top 10
organic results, the analyst reviews/edits, and the tool produces the exact `.xlsx`
deliverable the team already uses — plus several layers of extra intelligence on top.

## What it does

| Layer | What you get |
|---|---|
| **Classification** (Phase 1) | Paste SERP text → top-10 organic results classified into 11 categories → editable review table → downloadable `.xlsx` matching the boss's template |
| **Ads Intelligence** (Phase 2) | Paid-ad extraction per keyword, offshore flagging, and a downloadable PDF report |
| **Run Intelligence** (Phase 3) | On-demand deeper analysis of a single run: SERP features, snippet language, operator visibility, People-Also-Ask clusters, with a PDF export |
| **Trends Dashboard** (Phase 4) | Cross-run charts: SERP health over time, new entrants, domain persistence, EMD lifecycle, keyword volatility, ads pressure |
| **Scraping** (Phase 5) | Planned — live page fetching + offshore verification (see [phase5.md](phase5.md)) |

## Quick start (local dev)

```bash
git clone <repo-url> raulreport && cd raulreport
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in OPENAI_API_KEY + APP_PASSWORD
mkdir -p data/runs            # gitignored; must exist before first write
python app.py                 # http://127.0.0.1:5000
```

Log in with the `APP_USERNAME` / `APP_PASSWORD` from your `.env`.

## Documentation

- **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** — how to run a weekly report, step by step. Start here if you're an analyst.
- **[docs/TECHNICAL.md](docs/TECHNICAL.md)** — architecture, data model, modules, routes, deployment, and how to extend it. Start here if you're working on the code.

## Tech at a glance

Python 3.11+ · Flask 3 · OpenAI Chat Completions (`gpt-4o-mini` / `gpt-4o`) ·
openpyxl (xlsx) · fpdf2 (PDFs) · Chart.js via CDN (dashboard) · JSON-on-disk storage ·
gunicorn + systemd in production. No database, no build step, no SPA framework.

## Production

Runs on a DigitalOcean VPS under gunicorn + systemd. Deploy is `git pull` + service
restart — see the **Deployment** section of [docs/TECHNICAL.md](docs/TECHNICAL.md).
