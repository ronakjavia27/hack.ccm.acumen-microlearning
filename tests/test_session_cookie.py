"""The session cookie is set in one place (webapp.auth.set_session_cookie); every sign-in path uses it."""
import re

from acumen_core import kv
from webapp import auth


def cookie_header(response):
    return next(v for k, v in response.headers.multi_items() if k.lower() == "set-cookie" and v.startswith("hackccm_sess="))


def assert_standard_flags(header, secure=False):
    low = header.lower()
    assert "httponly" in low and "samesite=lax" in low and "max-age=2592000" in low and "path=/" in low
    assert ("secure" in low.replace("samesite", "")) is secure


def test_signup_and_login_set_the_standard_cookie(client):
    r = client.post("/api/signup", json={"email": "a@b.co", "password": "longenough1"})
    assert_standard_flags(cookie_header(r))
    client.cookies.clear()
    assert_standard_flags(cookie_header(client.post("/api/login", json={"email": "a@b.co", "password": "longenough1"})))


def test_secure_flag_follows_the_deployment(client, monkeypatch):
    monkeypatch.setattr(auth, "COOKIE_SECURE", True)
    r = client.post("/api/signup", json={"email": "a@b.co", "password": "longenough1"})
    assert_standard_flags(cookie_header(r), secure=True)


def test_local_dev_page_sets_the_standard_cookie_and_session_is_valid(dev_client):
    r = dev_client.get("/")
    assert_standard_flags(cookie_header(r))
    sid = re.match(r"hackccm_sess=([^;]+)", cookie_header(r)).group(1)
    assert kv.kv_get(f"auth:session:{sid}")["email"] == "admin@gmail.com"


def test_session_id_is_unguessable_and_unique(client):
    ids = {auth.new_session_id() for _ in range(50)}
    assert len(ids) == 50 and all(len(i) >= 40 for i in ids)
