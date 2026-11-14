"""The sign-in page is one template shared by revamped_webapp and webapp_google."""
import json
import re

GOOGLE = {"client_id": "test-client", "production_domain": "hackccm.vercel.app",
          "cookie_name": "hackccm_sess", "session_max_age": 2592000}


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


def test_google_landing(client, portal):
    portal.app.state.google_auth = GOOGLE
    html = client.get("/").text
    assert 'id="googleSection" class="hidden"' in html
    assert '<script src="https://accounts.google.com/gsi/client" async defer></script>' in html
    assert config_of(html)["google"] == GOOGLE
    # Google script first, shared script second (the old inline order)
    assert html.index("google_signin.js") < html.index("landing.js")


def test_landing_is_a_thin_shell(client):
    html = client.get("/").text
    assert "<style>" not in html and html.count("<script>") == 0
    assert re.search(r'<link rel="stylesheet" href="/static/css/landing\.css\?v=[0-9a-f]{10}">', html)


def test_landing_assets_served(client, portal):
    portal.app.state.google_auth = GOOGLE
    html = client.get("/").text
    for url in re.findall(r'(?:href|src)="(/static/[^"]+)"', html):
        r = client.get(url)
        assert r.status_code == 200, url
        assert r.headers["cache-control"] == "public, max-age=31536000, immutable", url
    assert "switchTab" in client.get("/static/js/landing.js").text
    assert "handleGoogleCredential" in client.get("/static/js/google_signin.js").text


def test_landing_config_roundtrips_disclaimer_exactly(client, portal):
    cfg = config_of(client.get("/").text)
    assert cfg["disclaimer_text"] == portal.LANDING_DISCLAIMER_TEXT
    assert cfg["disclaimer_text"].startswith("**Welcome to hack.CCM")


def test_landing_config_cannot_break_out_of_script_tag(client, portal, monkeypatch):
    monkeypatch.setattr(portal, "LANDING_DISCLAIMER_TEXT", "</script><img src=x onerror=alert(1)> & <!--")
    html = client.get("/").text
    block = re.search(r'<script id="landing-config" type="application/json">(.*?)</script>', html, re.S).group(1)
    assert "<" not in block and ">" not in block and "&" not in block
    assert config_of(html)["disclaimer_text"] == "</script><img src=x onerror=alert(1)> & <!--"


def test_no_landing_monkeypatch_left(portal):
    import webapp_google

    assert not hasattr(portal, "LANDING_HTML") and not hasattr(webapp_google, "GOOGLE_LANDING_HTML")
    assert webapp_google.app.state.google_auth["cookie_name"] == portal.SESSION_COOKIE_NAME
