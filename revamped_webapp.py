"""Entrypoint for the portal without Google sign-in.

Run locally with:  uvicorn revamped_webapp:app --port 8000
The application itself lives in the webapp/ package (see webapp/app.py).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from webapp.app import create_app  # noqa: E402

app = create_app()
