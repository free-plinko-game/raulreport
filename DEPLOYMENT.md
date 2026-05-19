# Deploying to PythonAnywhere (free tier)

This walks through deploying the SERP Classifier to PythonAnywhere's
"Beginner" (free) plan. Total setup time: ~15 minutes.

## Prerequisites

- A PythonAnywhere account (free tier — sign up at pythonanywhere.com).
  Your URL will be `https://<username>.pythonanywhere.com`.
- The repo pushed to a git host you can clone from (GitHub, GitLab, Bitbucket).
- Values ready for the five env vars in `.env.example`. Generate a strong
  `APP_PASSWORD` and a 32-byte hex `FLASK_SECRET_KEY` (e.g.
  `python -c "import secrets; print(secrets.token_hex(32))"`).

## 1. Clone the repo

From the PythonAnywhere dashboard open a **Bash console** ("Consoles" tab →
"Bash"). Clone into your home directory:

```bash
cd ~
git clone <your-repo-url> serp-classifier
cd serp-classifier
mkdir -p data/runs
```

The `mkdir -p data/runs` step is required — `data/runs/` is gitignored, so
the directory won't be created by the clone. The app will fail the first
write if it doesn't exist.

## 2. Create a virtualenv and install deps

Still in the Bash console:

```bash
mkvirtualenv --python=python3.11 serp-classifier
pip install -r ~/serp-classifier/requirements.txt
```

`mkvirtualenv` is provided by PythonAnywhere; it places the venv at
`~/.virtualenvs/serp-classifier`. Make a note of that path — you'll paste
it into the Web tab in step 4.

## 3. Create the web app (Manual Configuration)

In the dashboard, go to **Web** → **Add a new web app**.

- Domain: accept the default `<username>.pythonanywhere.com`.
- Framework: pick **Manual configuration** (NOT the Flask quickstart — the
  quickstart writes its own boilerplate WSGI file we'd then have to undo).
- Python version: **3.11**.

After this step you'll be on the configuration page for the new web app.

## 4. Point the WSGI shim at our `wsgi.py`

The Web tab shows a link like:

> WSGI configuration file:
> `/var/www/<username>_pythonanywhere_com_wsgi.py`

Click that link to open the editor. PythonAnywhere's stock content imports
a placeholder `hello_world` app. Replace the entire file with:

```python
import sys
import os

PROJECT_DIR = os.path.expanduser('~/serp-classifier')
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# Pull the Flask app object exposed by our repo's wsgi.py
from wsgi import application  # noqa: E402,F401
```

Save the file.

## 5. Set the virtualenv path

On the Web tab, find the **Virtualenv** section. Paste:

```
/home/<username>/.virtualenvs/serp-classifier
```

(Replace `<username>` with your PA username. PA expands this for you when
saved.)

## 6. Set environment variables (NOT a .env file)

PA's WSGI workers do NOT auto-load `.env`. Use the Web tab's
**Environment variables** section (further down the same page). Add each of:

| Name | Value |
|---|---|
| `OPENAI_API_KEY` | your real key (`sk-...`) |
| `OPENAI_MODEL` | `gpt-4o-mini` (or whatever model you want) |
| `APP_USERNAME` | e.g. `admin` |
| `APP_PASSWORD` | a strong password (this is what the boss types) |
| `FLASK_SECRET_KEY` | 64-hex-char random string |

Save. Each save persists immediately but the running worker won't pick
them up until the next reload (step 8).

## 7. (Optional but recommended) Static files mapping

Still on the Web tab, the **Static files** section. Add:

| URL | Directory |
|---|---|
| `/static/` | `/home/<username>/serp-classifier/static/` |

This lets PA's nginx serve CSS/JS directly without waking the Python
worker — faster, and your daily CPU-seconds quota lasts longer.

## 8. Reload

Hit the big green **Reload** button at the top of the Web tab. Browse to
`https://<username>.pythonanywhere.com/healthz` — you should see
`{"ok": true}` with no auth prompt.

Then browse to `/` — you'll get the Basic Auth login dialog. Enter the
`APP_USERNAME` / `APP_PASSWORD` you set in step 6 and you're in.

## Updating the app

After a `git pull` on the server:

```bash
cd ~/serp-classifier
git pull
# (only if requirements.txt changed)
workon serp-classifier
pip install -r requirements.txt
```

Then click **Reload** on the Web tab. Code changes don't apply until you
reload — there's no autoreloader under WSGI.

## Free-tier limits to be aware of

- **3-month idle rule**: the app is disabled if you don't log in to the
  PA dashboard for ~3 months. Just visit the dashboard occasionally.
- **Daily CPU-seconds quota**: free accounts get ~100 CPU-seconds/day. A
  full 26-keyword run is well under that — the LLM does the heavy work
  off-platform.
- **Outbound HTTP whitelist**: free accounts can only call hosts on PA's
  whitelist. `api.openai.com` IS on it; if you switch models to a host
  that isn't (e.g. self-hosted LLM, a non-OpenAI provider), you'll need
  to upgrade or change provider.
- **Memory**: low (hundreds of MB). Don't paste enormous SERPs — the
  built-in `MAX_CONTENT_LENGTH = 5 MB` cap (app.py) already protects you.
- **No background workers**: the free tier doesn't run scheduled tasks
  or persistent background threads. The codebase doesn't use either, so
  nothing to do — just don't add them later without upgrading.

## Troubleshooting

- **500 on every page** → tail `Error log` on the Web tab. Almost always
  a missing env var or an unset `APP_PASSWORD` (returns 401 by design if
  blank — see app.py `_check_auth`).
- **`ModuleNotFoundError: dotenv`** → wrong virtualenv path on the Web tab,
  or you didn't `pip install -r requirements.txt` inside the venv.
- **`Permission denied` writing JSON** → `~/serp-classifier/data/runs/`
  doesn't exist; rerun `mkdir -p data/runs` in a Bash console.
- **OpenAI calls hang** → check the model name. Confirm in `Files` tab
  that the .env is NOT being read (it isn't, but just in case you copied
  a stale value). The env vars on the Web tab are authoritative.
