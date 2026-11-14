import re


def test_me_anonymous(client):
    assert client.get("/api/me").json() == {"authenticated": False}


def test_signup_then_me_then_logout(client):
    r = client.post("/api/signup", json={"email": "A@Example.com", "password": "longenough1", "first_name": "Ada"})
    assert r.status_code == 200 and r.json() == {"ok": True, "email": "a@example.com"}
    assert "hackccm_sess" in client.cookies

    me = client.get("/api/me").json()
    assert me["authenticated"] and me["email"] == "a@example.com" and me["first_name"] == "Ada"
    assert me["is_admin"] is False

    assert client.post("/api/logout").json() == {"ok": True}
    client.cookies.clear()
    assert client.get("/api/me").json() == {"authenticated": False}


def test_signup_validation(client):
    assert client.post("/api/signup", json={"email": "nope", "password": "longenough1"}).status_code == 400
    assert client.post("/api/signup", json={"email": "a@b.co", "password": "short"}).status_code == 400
    assert client.post("/api/signup", json={"email": "a@b.co", "password": "longenough1"}).status_code == 200
    assert client.post("/api/signup", json={"email": "a@b.co", "password": "longenough1"}).status_code == 409


def test_login(client):
    client.post("/api/signup", json={"email": "a@b.co", "password": "longenough1"})
    client.cookies.clear()
    assert client.post("/api/login", json={"email": "a@b.co", "password": "wrong-password"}).status_code == 401
    assert client.post("/api/login", json={"email": "ghost@b.co", "password": "longenough1"}).status_code == 401
    assert client.post("/api/login", json={"email": "", "password": ""}).status_code == 400
    assert client.post("/api/login", json={"email": "a@b.co", "password": "longenough1"}).status_code == 200
    assert client.get("/api/me").json()["authenticated"] is True


def test_password_hash_roundtrip(portal):
    h = portal._hash_password("s3cret-pass")
    assert re.fullmatch(r"\$scrypt\$16384\$8\$1\$[0-9a-f]{32}\$[0-9a-f]{64}", h)
    assert portal._verify_password("s3cret-pass", h)
    assert not portal._verify_password("other", h)
    assert not portal._verify_password("s3cret-pass", "")
    assert portal._hash_password("s3cret-pass") != h  # fresh salt every time


def test_protected_api_requires_login(client):
    for path in ("/api/bookmarks", "/api/search?q=sepsis", "/api/pearls", "/api/trials", "/api/trials/stats"):
        assert client.get(path).status_code == 401, path


def test_admin_api_requires_admin(user_client):
    assert user_client.get("/api/admin/users").status_code == 403


def test_local_dev_mode_autologin_is_admin(dev_client):
    me = dev_client.get("/api/me").json()
    assert me["authenticated"] and me["is_admin"] is True


def test_landing_page_for_anonymous(client):
    r = client.get("/")
    assert r.status_code == 200
    assert 'id="loginForm"' in r.text and 'id="signupForm"' in r.text
