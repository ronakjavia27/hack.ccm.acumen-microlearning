"""Per-user bookmarks and bookmark folders."""
import secrets

from fastapi import APIRouter, HTTPException, Request

from acumen_core import kv
from webapp.auth import get_session_user, now_iso, require_feature

router = APIRouter()


# ---- Per-user data (bookmarks now; history/notes/prefs later) ----
BOOKMARKS_MAX_ITEMS = 500
BOOKMARKS_MAX_FOLDERS = 10
BOOKMARK_KINDS = ("paper", "guideline", "pearl", "trial", "condensed", "flashcard", "note")


def _user_data(email, key, default=None):
    data = kv.kv_get(f"user:{email}:{key}")
    if data is None or not isinstance(data, dict):
        return default if default is not None else {}
    return data


def _save_user_data(email, key, data):
    if not isinstance(data, dict):
        return False
    return kv.kv_set(f"user:{email}:{key}", data)


def _clean_tags(tags):
    if not isinstance(tags, list):
        return []
    out = []
    for t in tags[:20]:
        s = str(t).strip().strip("#").strip()
        if s and len(s) <= 40 and s not in out:
            out.append(s)
    return out


def _bookmark_item(body, existing=None):
    item = dict(existing or {})
    kind = str(body.get("kind", item.get("kind", ""))).strip().lower()
    ref = str(body.get("ref", item.get("ref", ""))).strip()
    if kind not in BOOKMARK_KINDS:
        raise HTTPException(400, f"Invalid bookmark kind '{kind}'")
    if not ref or len(ref) > 300:
        raise HTTPException(400, "Valid bookmark ref required")
    if existing is None:
        item.update({
            "ref": ref,
            "kind": kind,
            "title": str(body.get("title", ""))[:300] or ref,
            "system": str(body.get("system", ""))[:80],
            "type": str(body.get("type", ""))[:40],
            "locator": body.get("locator") if isinstance(body.get("locator"), dict) else {},
            "added_at": now_iso(),
        })
    else:
        item["ref"] = ref
        if body.get("title"):
            item["title"] = str(body["title"])[:300]
        if body.get("system") is not None:
            item["system"] = str(body["system"])[:80]
        if body.get("type") is not None:
            item["type"] = str(body["type"])[:40]
    if "folder" in body:
        item["folder"] = body.get("folder") or None
    if "tags" in body:
        item["tags"] = _clean_tags(body.get("tags"))
    return item


@router.get("/api/bookmarks")
async def api_bookmarks_list(request: Request):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_feature(user, "bookmarks")
    return _user_data(user["email"], "bookmarks")


@router.post("/api/bookmarks")
async def api_bookmarks_add(request: Request, body: dict):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_feature(user, "bookmarks")
    email = user["email"]
    data = _user_data(email, "bookmarks")
    items = data.setdefault("items", {})
    folders = data.setdefault("folders", {})
    ref = str(body.get("ref", "")).strip()
    if not ref or len(ref) > 300:
        raise HTTPException(400, "Valid bookmark ref required")
    existing = items.get(ref)
    if existing is None and len(items) >= BOOKMARKS_MAX_ITEMS:
        raise HTTPException(400, f"Bookmark limit reached ({BOOKMARKS_MAX_ITEMS})")
    item = _bookmark_item(body, existing)
    folder = item.get("folder")
    if folder and folder not in folders:
        item["folder"] = None
    items[ref] = item
    _save_user_data(email, "bookmarks", data)
    return {"ok": True, "item": item}


@router.patch("/api/bookmarks")
async def api_bookmarks_update(request: Request, body: dict):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_feature(user, "bookmarks")
    email = user["email"]
    ref = str(body.get("ref", "")).strip()
    if not ref:
        raise HTTPException(400, "Bookmark ref required")
    data = _user_data(email, "bookmarks")
    items = data.setdefault("items", {})
    existing = items.get(ref)
    if existing is None:
        raise HTTPException(404, "Bookmark not found")
    item = _bookmark_item(body, existing)
    folders = data.setdefault("folders", {})
    if item.get("folder") and item["folder"] not in folders:
        item["folder"] = None
    items[ref] = item
    _save_user_data(email, "bookmarks", data)
    return {"ok": True, "item": item}


@router.delete("/api/bookmarks")
async def api_bookmarks_delete(request: Request, ref: str = ""):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_feature(user, "bookmarks")
    email = user["email"]
    data = _user_data(email, "bookmarks")
    items = data.setdefault("items", {})
    if ref in items:
        del items[ref]
        _save_user_data(email, "bookmarks", data)
    return {"ok": True}


@router.post("/api/bookmarks/folders")
async def api_bookmarks_folder_add(request: Request, body: dict):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_feature(user, "bookmarks")
    email = user["email"]
    name = str(body.get("name", "")).strip()[:60]
    if not name:
        raise HTTPException(400, "Folder name required")
    data = _user_data(email, "bookmarks")
    folders = data.setdefault("folders", {})
    if len(folders) >= BOOKMARKS_MAX_FOLDERS:
        raise HTTPException(400, f"Folder limit reached ({BOOKMARKS_MAX_FOLDERS})")
    fid = "f" + secrets.token_hex(4)
    folder = {
        "name": name,
        "color": str(body.get("color", ""))[:20] or "#E8B778",
        "created_at": now_iso(),
    }
    folders[fid] = folder
    _save_user_data(email, "bookmarks", data)
    return {"ok": True, "id": fid, "folder": folder}


@router.patch("/api/bookmarks/folders")
async def api_bookmarks_folder_update(request: Request, body: dict):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_feature(user, "bookmarks")
    email = user["email"]
    fid = str(body.get("id", "")).strip()
    data = _user_data(email, "bookmarks")
    folders = data.setdefault("folders", {})
    folder = folders.get(fid)
    if folder is None:
        raise HTTPException(404, "Folder not found")
    if body.get("name") is not None:
        name = str(body["name"]).strip()[:60]
        if not name:
            raise HTTPException(400, "Folder name required")
        folder["name"] = name
    if body.get("color") is not None:
        folder["color"] = str(body["color"])[:20] or "#E8B778"
    _save_user_data(email, "bookmarks", data)
    return {"ok": True, "folder": folder}


@router.delete("/api/bookmarks/folders")
async def api_bookmarks_folder_delete(request: Request, ref: str = ""):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_feature(user, "bookmarks")
    email = user["email"]
    data = _user_data(email, "bookmarks")
    folders = data.setdefault("folders", {})
    items = data.setdefault("items", {})
    if ref in folders:
        del folders[ref]
        for item in items.values():
            if item.get("folder") == ref:
                item["folder"] = None
        _save_user_data(email, "bookmarks", data)
    return {"ok": True}
