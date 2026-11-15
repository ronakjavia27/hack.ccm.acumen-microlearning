"""Sign-in page, the logged-in dashboard page and the favicon."""
import os

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse

from webapp.auth import (
    dev_login_allowed,
    get_session_user,
    local_dev_login,
    SESSION_COOKIE_NAME,
    set_session_cookie,
)
from webapp.boot import build_dashboard_page
from webapp.config import DISCLAIMER_TEXT, ECG_SVG
from webapp.templating import asset_url, render_template, script_json

router = APIRouter()


# ---- Landing page HTML ----
def _landing_disclaimer(text):
    """The sign-in page shows the portal's disclaimer, minus its closing 'click Proceed' paragraph
    (there is no Proceed button before login)."""
    paragraphs = text.rstrip().split("\n\n")
    if paragraphs and paragraphs[-1].lstrip().startswith('By clicking "Proceed"'):
        paragraphs = paragraphs[:-1]
    return "\n\n".join(paragraphs)


LANDING_DISCLAIMER_TEXT = _landing_disclaimer(DISCLAIMER_TEXT)


def _render_landing(request):
    """Sign-in page. create_app(google=True) sets app.state.google_auth, which switches on the Google section."""
    google = getattr(request.app.state, "google_auth", None)
    return render_template(
        "landing.html",
        google=bool(google),
        css_url=asset_url("css/landing.css"),
        js_url=asset_url("js/landing.js"),
        google_js_url=asset_url("js/google_signin.js"),
        config_json=script_json({"disclaimer_text": LANDING_DISCLAIMER_TEXT, "google": google}),
    )


@router.get("/", response_class=HTMLResponse)
async def render_dashboard(request: Request, response: Response):
    user = get_session_user(request)
    if not user:
        return HTMLResponse(content=_render_landing(request))
    boot, context = build_dashboard_page(user)
    insights_tag = '<script defer src="/_vercel/insights/script.js"></script>' if os.environ.get("VERCEL") else ''
    html = render_template(
        "dashboard.html",
        user=user,
        insights_tag=insights_tag,
        ecg_svg=ECG_SVG,
        css_url=asset_url("css/app.css"),
        js_url=asset_url("js/app.js"),
        boot_json=script_json(boot),
        **context,
    )
    resp = HTMLResponse(content=html)
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    if dev_login_allowed(request) and not request.cookies.get(SESSION_COOKIE_NAME):
        _, dev_sid = local_dev_login()
        set_session_cookie(resp, dev_sid)
    return resp


@router.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)
