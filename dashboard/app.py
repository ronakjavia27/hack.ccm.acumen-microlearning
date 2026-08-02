"""FastAPI sub-router for the hack.CCM Console dashboard.

Mounted at `/console` (prepend `/console` to all paths).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from .modules import bootstrap, all_kinds, get_spec, ItemNotFound, list_specs
from .modules.summaries import get_content as summaries_get_content
from .storage import REPO_ROOT, PUSH, audit_tail, LOCKS, audit, read_json
from . import backup as backup_mod
from .cascade import cascade_summary_update, cascade_preview
from .modules.accounts import list_users, get_user, update_user, delete_user, get_defaults, save_defaults, FEATURE_FLAGS, FEATURE_LABELS

router = APIRouter(prefix="/console")


@router.get("/api/subtopics")
async def api_subtopics():
    """Return the master system→subtopic vocabulary from acumen_core/subtopics.json."""
    path = REPO_ROOT / "acumen_core" / "subtopics.json"
    data = read_json(path, default={})
    return data


@router.post("/api/summaries/{item_id}/cascade-preview")
async def api_cascade_preview(item_id: str, body: Dict[str, Any]):
    _ensure_bootstrap()
    try:
        spec = get_spec("summaries")
        item = spec.get_fn(item_id)
    except ItemNotFound:
        raise HTTPException(404, f"summary/{item_id} not found")
    file_name = item.get("file_name", "")
    if not file_name:
        return {"total_pearls": 0}
    old_system = body.get("old_system", item.get("system", ""))
    old_subtopic = body.get("old_subtopic", item.get("subtopic", ""))
    new_system = body.get("new_system", old_system)
    new_subtopic = body.get("new_subtopic", old_subtopic)
    result = cascade_preview(file_name, {"system": old_system, "subtopic": old_subtopic},
                              {"system": new_system, "subtopic": new_subtopic})
    return result


@router.post("/api/update-pearls-bulk")
async def api_update_pearls_bulk(body: Dict[str, Any]):
    """Bulk-update pearls by file_name. Used after cascade confirmation."""
    from .cascade import cascade_apply
    file_name = body.get("file_name", "")
    new_system = body.get("system", "")
    new_subtopic = body.get("subtopic", "")
    if not file_name:
        raise HTTPException(400, "file_name required")
    result = cascade_apply(file_name, new_system, new_subtopic)
    return result


_bootstrapped = False


def _ensure_bootstrap():
    global _bootstrapped
    if not _bootstrapped:
        bootstrap()
        _bootstrapped = True


# =========================================================================
# Dashboard HTML
# =========================================================================
@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_index():
    _ensure_bootstrap()
    html_path = Path(__file__).parent / "static" / "dashboard.html"
    if not html_path.exists():
        return HTMLResponse("<h1>dashboard.html not built yet</h1>", status_code=404)
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


# =========================================================================
# Fixed-name API endpoints (MUST come before /api/{kind})
# =========================================================================
@router.get("/api/info")
async def api_info():
    _ensure_bootstrap()
    from acumen_core.kv import _use_upstash, kv_scan, kv_get, KV_URL, KV_TOKEN
    import requests as req
    kv_ok = _use_upstash()
    scan_all = []
    scan_users = []
    user_sample = []
    raw_keys = None
    if kv_ok:
        keys = kv_scan("*")
        scan_all = keys[:20]
        keys2 = kv_scan("auth:users:*")
        scan_users = keys2[:10]
        for k in scan_users[:3]:
            u = kv_get(k)
            if u:
                u.pop("password_hash", None)
                user_sample.append({"key": k, "data": u})
        try:
            rs = req.get(f"{KV_URL}/keys/auth:users:*", headers={"Authorization": f"Bearer {KV_TOKEN}"}, timeout=5)
            raw_keys = {"status": rs.status_code, "body": rs.text[:500] if rs.ok else rs.text[:200]}
        except Exception as e:
            raw_keys = {"error": str(e)[:200]}
    return {
        "kv_connected": kv_ok,
        "keys_all_count": len(scan_all),
        "keys_all_sample": scan_all,
        "keys_users_found": len(scan_users),
        "keys_users_sample": scan_users,
        "user_sample": user_sample,
        "raw_keys": raw_keys,
        "modules": [s.kind for s in all_kinds()],
        "repo_root": str(REPO_ROOT),
    }


@router.get("/api/modules")
async def api_modules():
    _ensure_bootstrap()
    return list_specs()


@router.post("/api/push")
async def api_push(body: Dict[str, Any]):
    _ensure_bootstrap()
    kind = body.get("kind", "unknown")
    ids = body.get("ids", [])
    paths = body.get("paths", [])
    message = body.get("message", f"console({kind}): edit {', '.join(map(str, ids))}")
    if not paths:
        raise HTTPException(400, "No paths to push")
    job_id = PUSH.submit(kind, ids, paths, message)
    return {"job_id": job_id}


@router.get("/api/push/{job_id}")
async def api_push_status(job_id: str):
    s = PUSH.status(job_id)
    if s is None:
        raise HTTPException(404, f"push job {job_id} not found")
    return s


@router.post("/api/push-all")
async def api_push_all(body: Dict[str, Any]):
    paths = body.get("all_paths", [])
    if not paths:
        raise HTTPException(400, "No paths")
    paths = list(dict.fromkeys(paths))
    job_id = PUSH.submit("global", ["all"], paths, "console: bulk push")
    return {"job_id": job_id}


@router.get("/api/backup")
async def api_backup_list():
    return backup_mod.list_backups()


@router.post("/api/backup")
async def api_backup_create(body: Dict[str, Any]):
    label = body.get("label", "dashboard")
    try:
        dest = backup_mod.create_backup(label)
        return {"ok": True, "path": str(dest), "label": label}
    except Exception as e:
        raise HTTPException(500, f"Backup failed: {e}")


@router.post("/api/backup/restore")
async def api_backup_restore(body: Dict[str, Any]):
    result = backup_mod.restore_backup(
        body.get("from"), body.get("to"), body.get("force", False),
    )
    if not result["ok"]:
        raise HTTPException(400, result["error"])
    return result


@router.get("/api/backup/verify/{name}")
async def api_backup_verify(name: str):
    return backup_mod.verify_backup(name)


# =========================================================================
# ACCOUNTS (user management + feature flags)
# =========================================================================
@router.get("/api/accounts/defaults")
async def api_accounts_defaults():
    return get_defaults()


@router.put("/api/accounts/defaults")
async def api_accounts_defaults_update(body: Dict[str, Any]):
    return save_defaults(body)


@router.get("/api/accounts/features/definitions")
async def api_accounts_feature_defs():
    return {
        "flags": FEATURE_FLAGS,
        "labels": FEATURE_LABELS,
    }


@router.get("/api/accounts")
async def api_accounts_list():
    return list_users()


@router.get("/api/accounts/{email:path}")
async def api_accounts_get(email: str):
    user = get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/api/accounts/{email:path}")
async def api_accounts_update(email: str, body: Dict[str, Any]):
    result = update_user(email, body)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.delete("/api/accounts/{email:path}")
async def api_accounts_delete(email: str):
    if not delete_user(email):
        raise HTTPException(status_code=404, detail="User not found")
    return {"deleted": True}


@router.post("/api/flashcards/{item_id:path}/regenerate-card")
async def api_flashcard_regenerate(item_id: str, body: Dict[str, Any]):
    """Regenerate a single flashcard card with an edit comment (unified store)."""
    _ensure_bootstrap()
    try:
        spec = get_spec("flashcards")
        deck = spec.get_fn(item_id)
    except ItemNotFound:
        raise HTTPException(404, f"flashcards/{item_id} not found")
    card_id = body.get("card_id", "")
    edit_comment = body.get("edit_comment", "")
    if not card_id or not edit_comment:
        raise HTTPException(400, "card_id and edit_comment required")

    from .modules.flashcards import _regenerate_card, _rewrite_md_card, _view_card, slugify
    from acumen_core import flashcards as fc

    card = fc.find_card(card_id)
    if card is None:
        raise HTTPException(404, f"card {card_id} not found")
    revised = _regenerate_card(card, edit_comment)
    if not revised:
        raise HTTPException(400, "regeneration failed")
    new_sub = revised.get("subtopic") or (card.get("data") or {}).get("original_subtopic") or card.get("subtopic", "")
    new_front = revised.get("front") or card.get("front") or ""
    new_back = revised.get("back") or card.get("back") or ""
    card["subtopic"] = fc.canonical_subtopic(card.get("system"), new_sub)
    card["data"]["original_subtopic"] = new_sub
    card["front"] = new_front
    card["back"] = new_back
    card.setdefault("edit_history", []).append(
        f"console regen '{edit_comment[:60]}' at {datetime.now().isoformat()}"
    )
    fc.upsert_card(card)
    # Write the revised card back into the authored markdown, when mappable
    src_file = card.get("source_file") or ""
    if card.get("source") == "md" and src_file:
        md_abs = REPO_ROOT / "flashcards_md" / src_file.replace("\\", "/")
        _rewrite_md_card(md_abs, new_sub, new_back, new_front)
    return {"updated": True, "card": _view_card(card)}


@router.post("/api/flashcards/{item_id:path}/reclassify")
async def api_flashcard_reclassify(item_id: str, body: Dict[str, Any]):
    """Move every card of a subtopic file to another system/subtopic."""
    _ensure_bootstrap()
    try:
        spec = get_spec("flashcards")
        deck = spec.get_fn(item_id)
    except ItemNotFound:
        raise HTTPException(404, f"flashcards/{item_id} not found")
    new_system = (body.get("system") or "").strip() or deck["_system"]
    new_subtopic = (body.get("subtopic") or "").strip() or deck["_subtopic"]
    from acumen_core import flashcards as fc
    moved = 0
    for c in deck["_raw"].get("cards", []):
        if fc.move_card(c["id"], new_system, new_subtopic):
            moved += 1
    return {"updated": moved > 0, "moved": moved, "id": f"{new_system}/{new_subtopic}"}


@router.get("/api/audit")
async def api_audit(n: int = Query(200)):
    return audit_tail(n)


# =========================================================================
# Generic CRUD (parameterized — must come after fixed routes above)
# =========================================================================
@router.get("/api/{kind}")
async def api_list(
    kind: str,
    q: str = Query(""),
    system: str = Query(""),
    status: str = Query(""),
    type: str = Query(""),
):
    _ensure_bootstrap()
    try:
        spec = get_spec(kind)
    except ItemNotFound:
        raise HTTPException(404, f"unknown module: {kind}")
    filters = {}
    if q:
        filters["q"] = q
    if system:
        filters["system"] = system
    if status:
        filters["status"] = status
    if type:
        filters["type"] = type
    return spec.list_fn(filters or None)


@router.get("/api/summaries/{item_id}/content")
async def api_summary_content(item_id: str):
    _ensure_bootstrap()
    try:
        return summaries_get_content(item_id)
    except ItemNotFound:
        raise HTTPException(404, f"summary {item_id} not found")

@router.post("/api/{kind}/bulk-status")
async def api_bulk_status(kind: str, body: Dict[str, Any]):
    _ensure_bootstrap()
    try:
        spec = get_spec(kind)
    except ItemNotFound:
        raise HTTPException(404, f"unknown module: {kind}")
    ids = body.get("ids", [])
    status = body.get("status", "")
    if not ids or not status:
        raise HTTPException(400, "ids and status required")
    result = spec.bulk_status_fn(ids, status)
    audit(kind, "bulk", f"bulk set {len(ids)} items to {status}")
    return result


@router.post("/api/{kind}/bulk-delete")
async def api_bulk_delete(kind: str, body: Dict[str, Any]):
    _ensure_bootstrap()
    try:
        spec = get_spec(kind)
    except ItemNotFound:
        raise HTTPException(404, f"unknown module: {kind}")
    ids = body.get("ids", [])
    if not ids:
        raise HTTPException(400, "ids required")
    result = spec.bulk_delete_fn(ids)
    audit(kind, "bulk", f"bulk delete {len(ids)} items")
    return result


@router.delete("/api/{kind}/{item_id:path}")
async def api_delete(kind: str, item_id: str):
    _ensure_bootstrap()
    try:
        spec = get_spec(kind)
    except ItemNotFound:
        raise HTTPException(404, f"unknown module: {kind}")
    LOCKS.acquire(kind, item_id)
    try:
        result = spec.delete_fn(item_id)
        audit(kind, item_id, "delete")
        return result
    except ItemNotFound:
        raise HTTPException(404, f"{kind}/{item_id} not found")
    finally:
        LOCKS.release(kind, item_id)


@router.get("/api/{kind}/{item_id:path}")
async def api_get(kind: str, item_id: str):
    _ensure_bootstrap()
    try:
        spec = get_spec(kind)
    except ItemNotFound:
        raise HTTPException(404, f"unknown module: {kind}")
    try:
        return spec.get_fn(item_id)
    except ItemNotFound:
        raise HTTPException(404, f"{kind}/{item_id} not found")


@router.put("/api/{kind}/{item_id:path}")
async def api_update(kind: str, item_id: str, body: Dict[str, Any]):
    _ensure_bootstrap()
    try:
        spec = get_spec(kind)
    except ItemNotFound:
        raise HTTPException(404, f"unknown module: {kind}")
    LOCKS.acquire(kind, item_id)
    try:
        result = spec.update_fn(item_id, body)
        return result
    except ItemNotFound:
        raise HTTPException(404, f"{kind}/{item_id} not found")
    finally:
        LOCKS.release(kind, item_id)
