"""Smoke tests for the logged-in portal page, its static assets and the read-only content APIs."""
import json
import re

BOOT_KEYS = {
    "spec_vars", "spec_labels", "type_list", "articles", "pearls", "subtopic_map", "show_disclaimer",
    "trial_index", "trial_spec_labels", "trial_spec_vars", "trial_spec_counts", "trial_subtopic_map",
    "trial_result_cats", "trial_types_list", "condensed_index", "condensed_systems",
    "condensed_result_cats", "condensed_types_list", "flashcard_decks", "theory_spec_vars",
    "theory_subtopic_map", "theory_notes", "related_catalog", "related_index", "related_meta",
    "user_features", "user_is_admin", "admin_feature_flags", "credits_text", "trial_disclaimer_text",
    "disclaimer_text", "feedback_form_url", "subscribe_form_url", "unsubscribe_form_url",
}


def boot_of(html):
    m = re.search(r'<script id="boot" type="application/json">(.*?)</script>', html, re.S)
    assert m, "no #boot block"
    return json.loads(m.group(1))


def test_dashboard_renders_for_logged_in_user(user_client):
    r = user_client.get("/")
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store, max-age=0"
    html = r.text
    assert "<title>hack.CCM — Knowledge Portal</title>" in html
    assert html.rstrip().endswith("</html>")
    for marker in ('id="searchTrigger"', 'data-view="papers"', 'id="disclaimerOverlay"'):
        assert marker in html, marker
    # a template with a typo'd or unfilled placeholder must never reach the browser
    for leftover in ("@@F", "{{", "{%", "StrictUndefined"):
        assert leftover not in html, leftover


def test_page_is_a_thin_shell(user_client):
    """CSS and JS are static files now, not inline in the page."""
    html = user_client.get("/").text
    assert "<style>" not in html and html.count("<script>") == 0
    assert re.search(r'<link rel="stylesheet" href="/static/css/app\.css\?v=[0-9a-f]{10}">', html)
    assert re.search(r'<script src="/static/js/app\.js\?v=[0-9a-f]{10}"></script>', html)


def test_boot_payload(user_client):
    boot = boot_of(user_client.get("/").text)
    assert set(boot) == BOOT_KEYS
    assert boot["user_is_admin"] is False
    assert isinstance(boot["articles"], list) and boot["articles"]
    assert isinstance(boot["pearls"], list) and isinstance(boot["show_disclaimer"], bool)
    assert boot["user_features"]["papers"] is True and boot["user_features"]["theory"] is False
    assert boot["flashcard_decks"] == [] and boot["theory_notes"] == []  # theory feature off for this user


def test_boot_json_cannot_break_out_of_its_script_tag(user_client, portal, monkeypatch):
    evil = "</script><img src=x onerror=alert(1)> & <!--"
    monkeypatch.setattr(portal, "load_pearls", lambda: [{"system": "Sepsis", "type": "Review", "text": evil}])
    html = user_client.get("/").text
    boot_block = re.search(r'<script id="boot" type="application/json">(.*?)</script>', html, re.S).group(1)
    assert "</script" not in boot_block and "<img" not in boot_block and "<!--" not in boot_block
    assert boot_of(html)["pearls"][0]["text"] == evil  # still round-trips exactly


def test_static_assets_served_with_cache_headers(user_client):
    html = user_client.get("/").text
    css_url = re.search(r'href="(/static/css/app\.css\?v=[0-9a-f]+)"', html).group(1)
    js_url = re.search(r'src="(/static/js/app\.js\?v=[0-9a-f]+)"', html).group(1)

    css = user_client.get(css_url)
    assert css.status_code == 200 and css.headers["content-type"].startswith("text/css")
    assert css.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert "--radius:10px" in css.text and "@@F" not in css.text

    js = user_client.get(js_url)
    assert js.status_code == 200 and "javascript" in js.headers["content-type"]
    assert js.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert "function showView" in js.text
    assert "getElementById('boot')" in js.text and "@@F" not in js.text

    unversioned = user_client.get("/static/js/app.js")
    assert unversioned.headers["cache-control"] == "public, max-age=300"
    assert user_client.get("/static/js/missing.js").status_code == 404


def test_asset_version_changes_with_content(portal, tmp_path, monkeypatch):
    (tmp_path / "static" / "css").mkdir(parents=True)
    f = tmp_path / "static" / "css" / "x.css"
    f.write_text("a{}")
    monkeypatch.setattr(portal, "WEBAPP_DIR", tmp_path)
    first = portal._asset_url("css/x.css")
    f.write_text("b{color:red}")
    assert portal._asset_url("css/x.css") != first


def test_dev_admin_sees_admin_ui(dev_client):
    html = dev_client.get("/").text
    assert boot_of(html)["user_is_admin"] is True
    assert "&#128101; Users</button>" in html


def test_non_admin_has_no_users_button(user_client):
    assert "&#128101; Users</button>" not in user_client.get("/").text


def test_condensed_trials_card_shows_the_real_count(dev_client):
    """Regression: the card used to print the literal text '{len(condensed_index)}'."""
    html = dev_client.get("/").text
    n = len(boot_of(html)["condensed_index"])
    assert n > 0
    assert f"{n} trials &mdash; tap to explore" in html
    assert "{len(" not in html


def test_condensed_trials_card_hidden_without_feature(user_client):
    assert "Core Critical Care Trials</h3>" not in user_client.get("/").text


def test_content_apis(user_client):
    c = user_client
    assert c.get("/api/trials/stats").status_code == 200
    r = c.get("/api/pearls", params={"page": 1, "limit": 5})
    assert r.status_code == 200
    r = c.get("/api/search", params={"q": "sepsis"})
    assert r.status_code == 200
    assert c.get("/api/trials", params={"limit": 3}).status_code == 200
    assert c.get("/api/condensed-trials").status_code == 403  # feature is off by default


def test_specialty_order_is_alphabetical(user_client):
    labels = boot_of(user_client.get("/").text)["spec_labels"]
    assert labels == sorted(labels) and len(labels) > 5


def test_page_is_identical_across_processes_with_different_hash_seeds():
    """The specialty chips used to be ordered by iterating a Python set, so a restart reshuffled them."""
    import hashlib
    import os
    import subprocess
    import sys
    import textwrap

    code = textwrap.dedent("""
        import hashlib, os, sys, tempfile
        sys.path.insert(0, ".")
        os.environ["KV_LOCAL"] = "1"; os.environ.pop("VERCEL", None)
        from acumen_core import kv
        kv._KV_FILE = os.path.join(tempfile.mkdtemp(), "kv.json")
        import revamped_webapp as rw
        from fastapi.testclient import TestClient
        c = TestClient(rw.app, base_url="http://localhost", client=("127.0.0.1", 1))
        html = c.get("/").text
        sys.stdout.write(hashlib.sha1(html.encode()).hexdigest())
    """)
    digests = set()
    for seed in ("1", "2", "3"):
        env = {**os.environ, "PYTHONHASHSEED": seed, "KV_LOCAL": "1"}
        env.pop("VERCEL", None)
        out = subprocess.run([sys.executable, "-W", "ignore", "-c", code], env=env, capture_output=True, text=True, check=True)
        digests.add(out.stdout.strip()[-40:])
    assert len(digests) == 1, digests


def test_filter_option_values_are_html_escaped(user_client, portal, monkeypatch):
    nasty = 'Weird & <b>"x"</b>'
    monkeypatch.setattr(portal, "load_trial_index", lambda: [
        {"specialty": nasty, "result_category": nasty, "trial_type": nasty, "subtopic": "General", "slug": "s", "title": "t"}])
    html = user_client.get("/").text
    assert "<b>" not in html.split('id="view-trials-esbicm"')[1].split("</section>")[0]
    assert 'value="Weird &amp; &lt;b&gt;&#34;x&#34;&lt;/b&gt;"' in html
