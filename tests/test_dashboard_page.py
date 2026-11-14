"""Smoke tests for the logged-in portal page and the read-only content APIs."""


def test_dashboard_renders_for_logged_in_user(user_client):
    r = user_client.get("/")
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store, max-age=0"
    html = r.text
    assert "<title>hack.CCM — Knowledge Portal</title>" in html
    assert html.rstrip().endswith("</html>")
    for marker in ('id="searchTrigger"', 'data-view="papers"', 'id="disclaimerOverlay"', "function showView"):
        assert marker in html, marker
    assert "@@F" not in html


def test_dashboard_embeds_user_flags(user_client):
    html = user_client.get("/").text
    assert "const USER_IS_ADMIN = false;" in html
    assert "&#128101; Users</button>" not in html


def test_dev_admin_sees_users_button(dev_client):
    html = dev_client.get("/").text
    assert "const USER_IS_ADMIN = true;" in html
    assert "&#128101; Users</button>" in html


def test_content_apis(user_client):
    c = user_client
    assert c.get("/api/trials/stats").status_code == 200
    r = c.get("/api/pearls", params={"page": 1, "limit": 5})
    assert r.status_code == 200
    r = c.get("/api/search", params={"q": "sepsis"})
    assert r.status_code == 200
    assert c.get("/api/trials", params={"limit": 3}).status_code == 200
    assert c.get("/api/condensed-trials").status_code in (200, 403)  # feature is off by default
