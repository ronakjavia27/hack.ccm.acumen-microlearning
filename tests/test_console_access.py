"""Console access guard (Tailscale Serve, owner-only). Run: python -m pytest tests/test_console_access.py -q"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from dashboard import access  # noqa: E402

OWNER = "owner@example.com"


@pytest.fixture
def make_client(monkeypatch):
    monkeypatch.setenv("CONSOLE_OWNER", OWNER)
    monkeypatch.delenv("CONSOLE_ALLOW_LAN", raising=False)
    app = FastAPI()
    app.add_middleware(access.ConsoleAccessMiddleware)

    @app.get("/console/ping")
    def ping(request: Request):
        return {"reviewer": access.reviewer_name(request)}

    return lambda host: TestClient(app, client=(host, 50000))


def test_local_browser_allowed(make_client):
    assert make_client("127.0.0.1").get("/console/ping").status_code == 200


def test_owner_via_tailscale_allowed_and_named(make_client):
    r = make_client("127.0.0.1").get("/console/ping", headers={"Tailscale-User-Login": "Owner@Example.com",
                                                               "Tailscale-User-Name": "Dr Owner"})
    assert r.status_code == 200 and r.json()["reviewer"] == "Dr Owner"


def test_other_tailscale_login_refused(make_client):
    r = make_client("127.0.0.1").get("/console/ping", headers={"Tailscale-User-Login": "someone@else.com"})
    assert r.status_code == 403 and "not allowed" in r.text


def test_lan_device_refused_unless_enabled(make_client, monkeypatch):
    assert make_client("192.168.1.23").get("/console/ping").status_code == 403
    monkeypatch.setenv("CONSOLE_ALLOW_LAN", "1")
    assert make_client("192.168.1.23").get("/console/ping").status_code == 200


def test_remote_refused_when_owner_unset(make_client, monkeypatch):
    monkeypatch.delenv("CONSOLE_OWNER")
    r = make_client("127.0.0.1").get("/console/ping", headers={"Tailscale-User-Login": OWNER})
    assert r.status_code == 403 and "CONSOLE_OWNER" in r.text
    assert access.startup_warning()


def test_studio_reviewer_comes_from_tailscale_identity(monkeypatch):
    from dashboard import studio_api
    req = type("R", (), {"headers": {"tailscale-user-name": "Dr Owner"}})()
    assert studio_api._by("typed name", req) == "Dr Owner"          # identity can't be typed over
    assert studio_api._by("typed name", type("R", (), {"headers": {}})()) == "typed name"


def test_dashboard_app_is_private_by_default():
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard_app.py")).read()
    assert 'default="127.0.0.1"' in src and "ConsoleAccessMiddleware" in src
