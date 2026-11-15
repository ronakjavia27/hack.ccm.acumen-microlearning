"""Application factory for the hack.CCM portal."""
from fastapi import FastAPI

from webapp.config import WEBAPP_DIR
from webapp.routers import (
    admin,
    auth,
    auth_google,
    bookmarks,
    export,
    pages,
    papers,
    pearls,
    search,
    trials,
)
from webapp.templating import AssetFiles

# Routers are included in this order. A route that could be shadowed by an earlier, more general
# one (e.g. /api/admin/users/defaults vs /api/admin/users/{email:path}) must stay inside its own
# router, ahead of the general route; tests/test_routes.py checks that nothing is shadowed.
ROUTERS = (pages, auth, admin, bookmarks, papers, export, search, pearls, trials)


def create_app(google=False):
    """Build the portal. google=True (the Vercel entrypoint) also enables Google sign-in."""
    app = FastAPI()
    app.mount("/static", AssetFiles(directory=str(WEBAPP_DIR / "static")), name="static")
    for module in ROUTERS:
        app.include_router(module.router)
    if google:
        # the sign-in page shows the Google section when this is set
        app.state.google_auth = {
            "client_id": auth_google.GOOGLE_CLIENT_ID,
            "production_domain": auth_google.PRODUCTION_DOMAIN,
        }
        app.include_router(auth_google.router)
    return app
