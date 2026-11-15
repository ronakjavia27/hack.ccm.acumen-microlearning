"""Shared fixtures for the portal tests.

The portal reads data through cwd-relative paths ("./output_files", ...) and keeps
users/sessions in acumen_core.kv, so every test runs from the repo root against a
throwaway KV file and never touches Upstash or the real local_kv.json.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

os.environ.pop("VERCEL", None)
os.environ["KV_LOCAL"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

from webapp import auth  # noqa: E402
from webapp.app import create_app  # noqa: E402

LOCALHOST = {"base_url": "http://localhost", "client": ("127.0.0.1", 50000)}


@pytest.fixture(autouse=True)
def _isolated_kv(tmp_path, monkeypatch):
    from acumen_core import kv

    monkeypatch.setattr(kv, "_KV_FILE", str(tmp_path / "kv.json"))


@pytest.fixture
def app():
    """The portal without Google sign-in (what `uvicorn revamped_webapp:app` serves)."""
    return create_app()


@pytest.fixture
def google_app():
    """The portal as deployed on Vercel (webapp_google): adds Google sign-in."""
    return create_app(google=True)


@pytest.fixture
def client(app, monkeypatch):
    """Client that must really log in (local-dev auto-login disabled)."""
    monkeypatch.setattr(auth, "LOCAL_DEV_MODE", False)
    return TestClient(app)


@pytest.fixture
def dev_client(app, monkeypatch):
    """Client behaving like `uvicorn revamped_webapp:app` locally (auto-login as admin)."""
    monkeypatch.setattr(auth, "LOCAL_DEV_MODE", True)
    return TestClient(app, **LOCALHOST)


@pytest.fixture
def user_client(client):
    r = client.post("/api/signup", json={"email": "reader@example.com", "password": "correct-horse"})
    assert r.status_code == 200, r.text
    return client
