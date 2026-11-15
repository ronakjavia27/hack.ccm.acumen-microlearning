"""Feature flags are defined once (acumen_core/features.py) for both the portal and the admin console."""
from acumen_core import features, kv
from dashboard.modules import accounts
from fastapi.testclient import TestClient


def test_portal_and_console_share_one_definition():
    assert accounts.FEATURE_FLAGS is features.FEATURE_FLAGS
    assert accounts.FEATURE_LABELS is features.FEATURE_LABELS
    assert set(features.FEATURE_LABELS) == set(features.FEATURE_FLAGS)
    assert "bookmarks" in features.FEATURE_FLAGS and len(features.FEATURE_FLAGS) == 9


def test_resolve_defaults_layers_stored_values_over_the_built_in_ones():
    assert features.resolve_defaults({}) == {f: f not in ("condensed_trials", "theory") for f in features.FEATURE_FLAGS}
    assert features.resolve_defaults({"theory": True, "papers": False})["theory"] is True
    assert features.resolve_defaults({"papers": False})["papers"] is False
    assert features.resolve_defaults(None) == features.resolve_defaults({})
    assert features.resolve_defaults("garbage") == features.resolve_defaults({})
    assert list(features.resolve_defaults({})) == features.FEATURE_FLAGS  # stable order


def test_clean_flags_keeps_only_known_flags_as_booleans():
    assert features.clean_flags({"papers": 1, "bookmarks": 0, "nonsense": True}) == {"papers": True, "bookmarks": False}
    assert features.clean_flags(None) == {}


# ---- regression: the console used to erase flags it did not know about ----

def test_console_save_keeps_a_bookmarks_override():
    kv.kv_set("auth:users:u@x.co", {"email": "u@x.co", "password_hash": "h", "features": {"bookmarks": False, "theory": True}})
    # the console UI sends back every flag it was given, including the one it used to not know about
    updated = accounts.update_user("u@x.co", {"features": {"bookmarks": False, "theory": False}})
    assert updated["features"] == {"bookmarks": False, "theory": False}
    assert kv.kv_get("auth:users:u@x.co")["features"]["bookmarks"] is False


def test_console_defaults_include_every_flag_and_keep_bookmarks():
    assert set(accounts.get_defaults()) == set(features.FEATURE_FLAGS)
    saved = accounts.save_defaults({"bookmarks": False, "papers": True, "unknown": True})
    assert saved == {"bookmarks": False, "papers": True}
    assert accounts.get_defaults()["bookmarks"] is False


def test_console_exposes_the_bookmarks_flag_and_label():
    from dashboard.app import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    body = TestClient(app).get("/console/api/accounts/features/definitions").json()
    assert body["flags"] == features.FEATURE_FLAGS and body["labels"]["bookmarks"] == "Bookmarks"


# ---- the portal's own admin API uses the same helpers ----

def test_portal_admin_defaults_roundtrip(dev_client):
    r = dev_client.put("/api/admin/users/defaults", json={"theory": True, "bogus": True, "bookmarks": False})
    assert r.status_code == 200
    out = r.json()
    assert list(out) == features.FEATURE_FLAGS and out["theory"] is True and out["bookmarks"] is False and "bogus" not in out
    assert dev_client.get("/api/admin/users/defaults").json() == out


def test_portal_user_features_follow_the_defaults(user_client):
    kv.kv_set("auth:access_defaults", {"bookmarks": False})
    assert user_client.get("/api/bookmarks").status_code == 403  # bookmarks switched off for everyone
    kv.kv_set("auth:users:reader@example.com", {**kv.kv_get("auth:users:reader@example.com"), "features": {"bookmarks": True}})
    assert user_client.get("/api/bookmarks").status_code == 200  # per-user override wins
