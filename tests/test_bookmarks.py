def test_bookmark_crud(user_client):
    c = user_client
    assert c.get("/api/bookmarks").json() == {}

    r = c.post("/api/bookmarks", json={"ref": "pearl:1", "kind": "pearl", "title": "A pearl", "system": "Sepsis"})
    assert r.status_code == 200
    item = r.json()["item"]
    assert item["ref"] == "pearl:1" and item["title"] == "A pearl" and "added_at" in item

    c.post("/api/bookmarks/folders", json={"name": "Revise"})
    folders = c.get("/api/bookmarks").json()["folders"]
    assert len(folders) == 1
    folder_id = next(iter(folders))

    r = c.patch("/api/bookmarks", json={"ref": "pearl:1", "folder": folder_id, "tags": ["#icu", "icu", " fluids "]})
    assert r.status_code == 200
    assert r.json()["item"]["folder"] == folder_id
    assert r.json()["item"]["tags"] == ["icu", "fluids"]

    assert c.delete("/api/bookmarks", params={"ref": "pearl:1"}).json() == {"ok": True}
    assert c.get("/api/bookmarks").json()["items"] == {}


def test_bookmark_validation(user_client):
    c = user_client
    assert c.post("/api/bookmarks", json={"ref": "", "kind": "pearl"}).status_code == 400
    assert c.post("/api/bookmarks", json={"ref": "x", "kind": "bogus"}).status_code == 400
    assert c.patch("/api/bookmarks", json={"ref": "missing"}).status_code == 404


def test_bookmarks_are_per_user(portal, client):
    client.post("/api/signup", json={"email": "one@x.co", "password": "longenough1"})
    client.post("/api/bookmarks", json={"ref": "paper:1", "kind": "paper", "title": "T"})
    client.cookies.clear()
    client.post("/api/signup", json={"email": "two@x.co", "password": "longenough1"})
    assert client.get("/api/bookmarks").json() == {}
