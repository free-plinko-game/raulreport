"""WSGI entry point for the SERP Classifier.

On PythonAnywhere, the platform's WSGI shim lives at
`/var/www/<username>_pythonanywhere_com_wsgi.py`. That shim should import
`application` from this file. See DEPLOYMENT.md.

Locally you don't need this file — `python app.py` still works for dev.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from app import app as application  # noqa: E402

__all__ = ["application"]
