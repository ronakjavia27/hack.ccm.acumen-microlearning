"""Password hashing, local-dev auto-login, the retired default admin password and error handling."""
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from acumen_core import kv
from conftest import LOCALHOST
from webapp import auth
from webapp.routers import auth as auth_router

LEGACY_DEFAULT = "admin@admin"


def legacy_hash(password, salt=b"0123456789abcdef"):
    return f"$sha256${salt.hex()}${hashlib.sha256(salt + password.encode()).hexdigest()}"


def put_user(email, password_hash, **extra):
    from acumen_core import kv

    kv.kv_set(f"auth:users:{email}", {"email": email, "password_hash": password_hash, "features": {}, **extra})


def stored_hash(email):
    from acumen_core import kv

    return kv.kv_get(f"auth:users:{email}")["password_hash"]


# ---------- hashing ----------

def test_legacy_sha256_hashes_still_verify():
    assert auth.verify_password("hunter2hunter2", legacy_hash("hunter2hunter2"))
    assert not auth.verify_password("nope", legacy_hash("hunter2hunter2"))


@pytest.mark.parametrize("bad", [None, "", "garbage", "$scrypt$x$y$z$q$r", "$scrypt$16384$8$1$zz$zz", "$sha256$zz$zz", 12345])
def test_malformed_hashes_never_verify(bad):
    assert auth.verify_password("whatever", bad) is False


def test_oversized_password_is_not_hashed_or_verified():
    assert auth.verify_password("x" * (auth.PASSWORD_MAX_LEN + 1), auth.hash_password("x")) is False
    assert auth.verify_password(12345, auth.hash_password("x")) is False


def test_legacy_hash_is_upgraded_on_successful_login(client):
    put_user("old@example.com", legacy_hash("correct-horse"))
    assert client.post("/api/login", json={"email": "old@example.com", "password": "correct-horse"}).status_code == 200
    upgraded = stored_hash("old@example.com")
    assert upgraded.startswith("$scrypt$") and auth.verify_password("correct-horse", upgraded)
    client.cookies.clear()
    assert client.post("/api/login", json={"email": "old@example.com", "password": "correct-horse"}).status_code == 200
    assert stored_hash("old@example.com") == upgraded  # current-format hashes are left alone


def test_failed_login_does_not_touch_the_stored_hash(client):
    put_user("old@example.com", legacy_hash("correct-horse"))
    before = stored_hash("old@example.com")
    assert client.post("/api/login", json={"email": "old@example.com", "password": "wrong-one"}).status_code == 401
    assert stored_hash("old@example.com") == before


def test_password_length_and_type_validation(client):
    assert client.post("/api/signup", json={"email": "a@b.co", "password": "x" * 1025}).status_code == 400
    assert client.post("/api/signup", json={"email": "a@b.co", "password": 12345678}).status_code == 400
    assert client.post("/api/login", json={"email": "a@b.co", "password": 12345678}).status_code == 400
    assert client.post("/api/signup", json={"email": "a@b.co", "password": "x" * 1024}).status_code == 200


# ---------- local dev auto-login ----------

def test_dev_login_works_from_localhost(dev_client):
    assert dev_client.get("/api/me").json()["is_admin"] is True


def test_dev_login_creates_no_session_per_request(dev_client):
    from acumen_core import kv

    for _ in range(3):
        dev_client.get("/api/me")
    assert [k for k in kv._load() if k.startswith("auth:session:")] == []


@pytest.mark.parametrize("headers", [
    {"x-forwarded-for": "203.0.113.9"}, {"x-real-ip": "203.0.113.9"}, {"forwarded": "for=203.0.113.9"},
    {"x-forwarded-host": "portal.example.com"},
])
def test_dev_login_refused_behind_a_proxy(dev_client, headers):
    assert dev_client.get("/api/me", headers=headers).json() == {"authenticated": False}


def test_dev_login_refused_for_a_public_hostname_or_remote_client(app, monkeypatch):
    monkeypatch.setattr(auth, "LOCAL_DEV_MODE", True)
    public_host = TestClient(app, base_url="http://portal.example.com", client=("127.0.0.1", 1))
    remote = TestClient(app, base_url="http://localhost", client=("203.0.113.9", 1))
    assert public_host.get("/api/me").json() == {"authenticated": False}
    assert remote.get("/api/me").json() == {"authenticated": False}


def test_dev_login_refused_when_kv_is_not_the_local_file(dev_client, monkeypatch):
    from acumen_core import kv

    monkeypatch.setattr(kv, "kv_backend", lambda: {"backend": "upstash", "reason": "test"})
    assert dev_client.get("/api/me").json() == {"authenticated": False}
    assert kv._load() == {}  # and it did not create the admin account in that store


def test_dev_login_off_when_disabled(app, monkeypatch):
    monkeypatch.setattr(auth, "LOCAL_DEV_MODE", False)
    c = TestClient(app, **LOCALHOST)
    assert c.get("/api/me").json() == {"authenticated": False}


def test_dev_admin_has_no_known_password(dev_client):
    dev_client.get("/api/me")
    h1 = stored_hash("admin@gmail.com")
    assert not auth.verify_password(LEGACY_DEFAULT, h1) and h1.startswith("$scrypt$")
    dev_client.cookies.clear()
    assert dev_client.post("/api/login", json={"email": "admin@gmail.com", "password": LEGACY_DEFAULT}).status_code == 401


# ---------- the retired default admin password ----------

def test_default_admin_password_is_disabled_wherever_it_still_exists(client):
    put_user("admin@gmail.com", legacy_hash(LEGACY_DEFAULT), is_admin=True)
    r = client.post("/api/login", json={"email": "admin@gmail.com", "password": LEGACY_DEFAULT})
    assert r.status_code == 401
    assert client.get("/api/me").json() == {"authenticated": False}
    assert not auth.verify_password(LEGACY_DEFAULT, stored_hash("admin@gmail.com"))
    assert client.post("/api/login", json={"email": "admin@gmail.com", "password": LEGACY_DEFAULT}).status_code == 401


def test_default_admin_password_also_retired_in_new_hash_format(client):
    put_user("admin@gmail.com", auth.hash_password(LEGACY_DEFAULT), is_admin=True)
    assert client.post("/api/login", json={"email": "admin@gmail.com", "password": LEGACY_DEFAULT}).status_code == 401


def test_admin_account_with_a_real_password_is_unaffected(client):
    put_user("admin@gmail.com", auth.hash_password("a-real-passphrase"), is_admin=True)
    assert client.post("/api/login", json={"email": "admin@gmail.com", "password": "a-real-passphrase"}).status_code == 200
    assert client.get("/api/me").json()["is_admin"] is True


def test_dev_admin_lookup_retires_default_password(dev_client):
    put_user("admin@gmail.com", legacy_hash(LEGACY_DEFAULT), is_admin=True)
    dev_client.get("/api/me")
    assert not auth.verify_password(LEGACY_DEFAULT, stored_hash("admin@gmail.com"))


# ---------- /api/debug ----------

def test_debug_endpoint_is_admin_only(app, user_client, dev_client):
    anonymous = TestClient(app)  # LOCAL_DEV_MODE is patched on by dev_client; this host is not localhost
    assert anonymous.get("/api/debug").status_code == 401
    assert user_client.get("/api/debug").status_code == 403  # signed-in, not an admin
    r = dev_client.get("/api/debug")
    assert r.status_code == 200 and "kv_backend" in r.json()


# ---------- error handling ----------

def test_signup_failure_returns_generic_json_without_internals(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("kv exploded: secret-token-123")

    monkeypatch.setattr(kv, "kv_set", boom)
    r = client.post("/api/signup", json={"email": "a@b.co", "password": "longenough1"})
    assert r.status_code == 500 and r.json()["detail"]
    assert "secret-token-123" not in r.text and "traceback" not in r.text.lower()


def test_login_failure_returns_generic_json_without_internals(client, monkeypatch):
    put_user("a@b.co", auth.hash_password("longenough1"))

    def boom(*a, **k):
        raise RuntimeError("internal-detail-xyz")

    monkeypatch.setattr(auth_router, "verify_password", boom)
    r = client.post("/api/login", json={"email": "a@b.co", "password": "longenough1"})
    assert r.status_code == 500 and "internal-detail-xyz" not in r.text
    assert isinstance(json.loads(r.text)["detail"], str)
