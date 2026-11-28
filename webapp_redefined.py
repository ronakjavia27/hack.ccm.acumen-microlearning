"""
webapp_redefined.py — Vercel entrypoint for the theory-first hack.CCM portal.

Import order matters:
  1. webapp_google registers the Google OAuth routes (/api/auth/google*) on
     revamped_webapp.app and swaps revamped_webapp.LANDING_HTML for the Google
     sign-in landing page.
  2. redefined_ui then copies every revamped_webapp route (including the Google
     ones) into its own app and serves the redesigned UI at "/". The previous
     portal stays reachable at "/classic".

Local run:  uvicorn webapp_redefined:app --port 8000
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import webapp_google  # noqa: E402,F401  (side effects: Google routes + landing)
import redefined_ui  # noqa: E402

app = redefined_ui.app
