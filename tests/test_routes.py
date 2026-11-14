"""The route table is the contract of the portal: refactors must not add, drop or reorder routes.

Order matters because FastAPI matches in registration order (e.g. /api/admin/users/defaults
must stay ahead of /api/admin/users/{email:path}).
"""
import json
from pathlib import Path

EXPECTED = Path(__file__).with_name("expected_routes.json")


def _route_table(app):
    rows = []
    for r in app.routes:
        methods = sorted(getattr(r, "methods", None) or [])
        rows.append([",".join(methods), r.path])
    return rows


def test_route_table_unchanged(portal):
    import webapp_google  # the deployed entrypoint (adds the Google OAuth routes)

    assert _route_table(webapp_google.app) == json.loads(EXPECTED.read_text())


def test_webapp_google_shares_the_same_app(portal):
    import webapp_google

    assert webapp_google.app is portal.app
    paths = {r.path for r in portal.app.routes}
    assert {"/api/auth/google", "/api/auth/google/callback"} <= paths
