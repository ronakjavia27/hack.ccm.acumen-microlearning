"""Google sign-in: token validation, redirect handling and the OAuth state cookie.

Google's endpoints are replaced by fakes, so these run offline.
"""
import pytest
import requests
from fastapi.testclient import TestClient

from webapp import auth
from webapp.routers import auth_google

CLIENT_ID = "our-client-id.apps.googleusercontent.com"
PROD = "hackccm.vercel.app"


class FakeResponse:
    def __init__(self, data=None, ok=True, status_code=200):
        self._data, self.ok, self.status_code = data or {}, ok, status_code

    def json(self):
        return self._data


def claims(**over):
    base = {"email": "Reader@Example.com", "email_verified": "true", "sub": "g-1", "aud": CLIENT_ID,
            "iss": "https://accounts.google.com", "given_name": "Rea", "family_name": "Der"}
    base.update(over)
    return base


@pytest.fixture
def wg(monkeypatch):
    monkeypatch.setattr(auth_google, "GOOGLE_CLIENT_ID", CLIENT_ID)
    monkeypatch.setattr(auth_google, "GOOGLE_CLIENT_SECRET", "secret")
    return auth_google


@pytest.fixture
def tokeninfo(monkeypatch):
    """tokeninfo.set(claims) controls what Google 'returns'; .calls records the requests made."""
    class Box:
        data = claims()
        calls = []
        token_ok = True

    def fake_get(url, **kw):
        Box.calls.append((url, kw))
        return FakeResponse(Box.data, ok=Box.data is not None)

    def fake_post(url, **kw):
        return FakeResponse({"id_token": "the-id-token"} if Box.token_ok else {}, ok=Box.token_ok, status_code=200 if Box.token_ok else 400)

    Box.calls = []
    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "post", fake_post)
    return Box


@pytest.fixture
def prod(wg, google_app, monkeypatch):
    monkeypatch.setattr(auth, "LOCAL_DEV_MODE", False)
    return TestClient(google_app, base_url=f"https://{PROD}", follow_redirects=False)


# ---------- credential (popup) flow ----------

def test_valid_credential_signs_in_without_leaking_the_session_id(prod, tokeninfo):
    r = prod.post("/api/auth/google", json={"credential": "tok"})
    assert r.status_code == 200 and r.json() == {"ok": True, "redirect": None}
    assert "sid" not in r.json()
    assert "httponly" in r.headers["set-cookie"].lower()
    assert prod.get("/api/me").json()["email"] == "reader@example.com"


def test_credential_for_another_app_is_rejected(prod, tokeninfo):
    tokeninfo.data = claims(aud="someone-elses-app")
    assert prod.post("/api/auth/google", json={"credential": "tok"}).status_code == 401
    assert prod.get("/api/me").json() == {"authenticated": False}


@pytest.mark.parametrize("verified", ["false", False, None, "", "no"])
def test_unverified_email_is_rejected(prod, tokeninfo, verified):
    tokeninfo.data = claims(email_verified=verified)
    assert prod.post("/api/auth/google", json={"credential": "tok"}).status_code == 401


def test_wrong_issuer_and_missing_client_id_are_rejected(prod, tokeninfo, wg, monkeypatch):
    tokeninfo.data = claims(iss="https://evil.example")
    assert prod.post("/api/auth/google", json={"credential": "tok"}).status_code == 401
    tokeninfo.data = claims()
    monkeypatch.setattr(wg, "GOOGLE_CLIENT_ID", "")
    assert prod.post("/api/auth/google", json={"credential": "tok"}).status_code == 401


def test_invalid_token_and_missing_credential(prod, tokeninfo):
    assert prod.post("/api/auth/google", json={}).status_code == 400
    tokeninfo.data = None  # tokeninfo says not ok
    assert prod.post("/api/auth/google", json={"credential": "bad"}).status_code == 401


def test_credential_is_url_encoded_not_interpolated(prod, tokeninfo):
    prod.post("/api/auth/google", json={"credential": "abc&aud=x"})
    url, kw = tokeninfo.calls[0]
    assert url == "https://oauth2.googleapis.com/tokeninfo" and kw["params"] == {"id_token": "abc&aud=x"}


def test_google_login_replaces_a_preregistered_password(prod, tokeninfo):
    prod.post("/api/signup", json={"email": "reader@example.com", "password": "attacker-chosen"})
    prod.cookies.clear()
    assert prod.post("/api/auth/google", json={"credential": "tok"}).status_code == 200
    prod.cookies.clear()
    assert prod.post("/api/login", json={"email": "reader@example.com", "password": "attacker-chosen"}).status_code == 401


def test_unexpected_failure_returns_generic_json_not_a_traceback(prod, wg, monkeypatch):
    def boom(_):
        raise RuntimeError("secret internals")

    monkeypatch.setattr(wg, "_verify_google_id_token", boom)
    r = prod.post("/api/auth/google", json={"credential": "tok"})
    assert r.status_code == 500 and "secret internals" not in r.text and "traceback" not in r.text.lower()
    assert r.json()["detail"]


# ---------- redirect sanitising ----------

@pytest.mark.parametrize("given,expected", [
    ("", "/"), (None, "/"), ("/", "/"), ("/?theory=notes&q=a", "/?theory=notes&q=a"),
    (f"https://{PROD}/a/b?x=1#frag", "/a/b?x=1#frag"), (f"https://{PROD}", "/"),
    ("https://evil.example/steal", "/"), ("//evil.example", "/"), ("/\\evil.example", "/"),
    (f"https://{PROD}.evil.example/", "/"), (f"https://{PROD}@evil.example/", "/"),
    ("javascript:alert(1)", "/"), ("/ok\nSet-Cookie: x=1", "/"),
])
def test_safe_redirect(wg, given, expected):
    assert wg._safe_redirect(given) == expected


# ---------- redirect (server-side) flow ----------

def start_flow(prod, redirect):
    r = prod.get("/api/auth/google", params={"redirect": redirect})
    assert r.status_code == 200 and "Sign in with Google" in r.text
    state = prod.cookies.get("hackccm_oauth_state")
    assert state, "state cookie not issued"
    return state


def test_redirect_flow_end_to_end(prod, tokeninfo):
    state = start_flow(prod, f"https://{PROD}/?theory=notes")
    r = prod.get("/api/auth/google/callback", params={"code": "c", "state": state})
    assert r.status_code == 302 and r.headers["location"] == "/?theory=notes"
    assert "hackccm_sess" not in r.headers["location"]
    assert prod.get("/api/me").json()["authenticated"] is True
    # state is single-use
    again = prod.get("/api/auth/google/callback", params={"code": "c", "state": state})
    assert "Invalid or expired state" in again.text


def test_redirect_to_another_site_is_not_followed_and_no_session_id_leaves_the_site(prod, tokeninfo):
    state = start_flow(prod, "https://evil.example/steal")
    r = prod.get("/api/auth/google/callback", params={"code": "c", "state": state})
    assert r.status_code == 302 and r.headers["location"] == "/"
    assert "evil" not in r.headers["location"] and "hackccm_sess" not in r.headers["location"]


def test_callback_without_the_browsers_state_cookie_is_rejected(prod, tokeninfo):
    state = start_flow(prod, "/")
    prod.cookies.clear()  # a different browser (the victim) replays the attacker's callback URL
    r = prod.get("/api/auth/google/callback", params={"code": "c", "state": state})
    assert "Invalid or expired state" in r.text and r.status_code == 200
    assert prod.get("/api/me").json() == {"authenticated": False}


def test_callback_with_mismatched_cookie_is_rejected(prod, tokeninfo):
    state = start_flow(prod, "/")
    prod.cookies.set("hackccm_oauth_state", "something-else", domain=PROD)
    assert "Invalid or expired state" in prod.get("/api/auth/google/callback", params={"code": "c", "state": state}).text


def test_callback_rejects_token_for_another_app(prod, tokeninfo):
    state = start_flow(prod, "/")
    tokeninfo.data = claims(aud="someone-elses-app")
    r = prod.get("/api/auth/google/callback", params={"code": "c", "state": state})
    assert "Token verification failed" in r.text
    assert prod.get("/api/me").json() == {"authenticated": False}


def test_callback_rejects_unverified_email(prod, tokeninfo):
    state = start_flow(prod, "/")
    tokeninfo.data = claims(email_verified="false")
    assert "Email not verified" in prod.get("/api/auth/google/callback", params={"code": "c", "state": state}).text


def test_callback_error_parameter_is_escaped(prod):
    payload = "<script>alert(document.domain)</script>"
    r = prod.get("/api/auth/google/callback", params={"error": payload})
    assert payload not in r.text and "&lt;script&gt;" in r.text
    r = prod.get("/api/auth/google/callback")
    assert "No authorization code received" in r.text


def test_token_exchange_failure_page_shows_status_only(prod, tokeninfo):
    state = start_flow(prod, "/")
    tokeninfo.token_ok = False
    r = prod.get("/api/auth/google/callback", params={"code": "c", "state": state})
    assert "Token exchange failed" in r.text and "400" in r.text


def test_not_on_production_host_shows_explanation(wg, google_app, monkeypatch):
    monkeypatch.setattr(auth, "LOCAL_DEV_MODE", False)
    c = TestClient(google_app)  # testserver host
    r = c.get("/api/auth/google")
    assert "only available on" in r.text and not c.cookies.get("hackccm_oauth_state")
