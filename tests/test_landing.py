"""The sign-in page is one template shared by revamped_webapp and webapp_google."""
import json
import re

from fastapi.testclient import TestClient

from webapp import auth, config
from webapp.routers import pages

GOOGLE = {"client_id": "test-client", "production_domain": "hackccm.vercel.app"}


def config_of(html):
    m = re.search(r'<script id="landing-config" type="application/json">(.*?)</script>', html, re.S)
    assert m, "no landing-config block"
    return json.loads(m.group(1))


def test_plain_landing_has_no_google(client):
    html = client.get("/").text
    assert 'id="loginForm"' in html and 'id="signupForm"' in html
    assert "googleSection" not in html and "gsi/client" not in html
    assert "google_signin.js" not in html
    assert config_of(html)["google"] is None


def test_google_landing(google_app, monkeypatch):
    monkeypatch.setattr(auth, "LOCAL_DEV_MODE", False)
    google_app.state.google_auth = GOOGLE
    html = TestClient(google_app).get("/").text
    assert 'id="googleSection" class="hidden"' in html
    assert '<script src="https://accounts.google.com/gsi/client" async defer></script>' in html
    assert config_of(html)["google"] == GOOGLE
    # Google script first, shared script second (the old inline order)
    assert html.index("google_signin.js") < html.index("landing.js")


def test_landing_is_a_thin_shell(client):
    html = client.get("/").text
    assert "<style>" not in html and html.count("<script>") == 0
    assert re.search(r'<link rel="stylesheet" href="/static/css/landing\.css\?v=[0-9a-f]{10}">', html)


def test_landing_assets_served(google_app, monkeypatch):
    monkeypatch.setattr(auth, "LOCAL_DEV_MODE", False)
    client = TestClient(google_app)
    html = client.get("/").text
    for url in re.findall(r'(?:href|src)="(/static/[^"]+)"', html):
        r = client.get(url)
        assert r.status_code == 200, url
        assert r.headers["cache-control"] == "public, max-age=31536000, immutable", url
    assert "switchTab" in client.get("/static/js/landing.js").text
    assert "handleGoogleCredential" in client.get("/static/js/google_signin.js").text


def test_landing_config_roundtrips_disclaimer_exactly(client):
    cfg = config_of(client.get("/").text)
    assert cfg["disclaimer_text"] == pages.LANDING_DISCLAIMER_TEXT
    assert cfg["disclaimer_text"].startswith("**Welcome to hack.CCM")


def test_landing_disclaimer_is_the_portal_disclaimer_minus_the_proceed_line():
    """One source of truth: the sign-in page used to carry an older, shorter copy that left out
    the AI-summarisation paragraph."""
    full = config.DISCLAIMER_TEXT.rstrip().split("\n\n")
    landing = pages.LANDING_DISCLAIMER_TEXT.split("\n\n")
    assert landing == full[:-1] and full[-1].startswith('By clicking "Proceed"')
    assert "Proceed" not in pages.LANDING_DISCLAIMER_TEXT
    assert "we use AI to condense" in pages.LANDING_DISCLAIMER_TEXT


def test_landing_disclaimer_helper_leaves_text_without_a_proceed_line_alone():
    assert pages._landing_disclaimer("one\n\ntwo\n") == "one\n\ntwo"


def test_landing_config_cannot_break_out_of_script_tag(client, monkeypatch):
    monkeypatch.setattr(pages, "LANDING_DISCLAIMER_TEXT", "</script><img src=x onerror=alert(1)> & <!--")
    html = client.get("/").text
    block = re.search(r'<script id="landing-config" type="application/json">(.*?)</script>', html, re.S).group(1)
    assert "<" not in block and ">" not in block and "&" not in block
    assert config_of(html)["disclaimer_text"] == "</script><img src=x onerror=alert(1)> & <!--"


def test_no_landing_monkeypatch_left():
    import webapp_google

    assert not hasattr(webapp_google, "GOOGLE_LANDING_HTML") and not hasattr(webapp_google, "revamped_webapp")


def test_each_entrypoint_builds_its_own_app():
    import revamped_webapp
    import webapp_google

    assert revamped_webapp.app is not webapp_google.app
    assert getattr(revamped_webapp.app.state, "google_auth", None) is None
    assert webapp_google.app.state.google_auth["production_domain"] == "hackccm.vercel.app"


def test_google_script_never_touches_the_session_cookie(client):
    """The server sets the HttpOnly session cookie; the page must not read, write or accept one."""
    js = client.get("/static/js/google_signin.js").text
    assert "document.cookie" not in js and "hackccm_sess" not in js and "sidParam" not in js
