"""Admin-only endpoints: user management and the diagnostics endpoint."""
import os

from fastapi import APIRouter, HTTPException, Request

from acumen_core import kv
from webapp.auth import (
    DEFAULT_FEATURE_STATES,
    FEATURE_FLAGS,
    access_defaults,
    get_session_user,
    require_admin,
)

router = APIRouter()


@router.get("/api/debug")
async def api_debug(request: Request):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_admin(user)
    from acumen_core import kv as _kvmod
    return {"kv_backend": _kvmod.kv_backend(), "vercel": os.environ.get("VERCEL", "")}


def _admin_users_list():
    from concurrent.futures import ThreadPoolExecutor
    keys = kv.kv_scan("auth:users:*") or []
    if not keys:
        return []
    with ThreadPoolExecutor(max_workers=min(10, len(keys))) as pool:
        users = [u for u in pool.map(kv.kv_get, keys) if u]
    for u in users:
        u.pop("password_hash", None)
    users.sort(key=lambda u: u.get("created_at", ""), reverse=True)
    return users


def _admin_user_get(email: str):
    user = kv.kv_get(f"auth:users:{email}")
    if user:
        user.pop("password_hash", None)
    return user


def _admin_user_update(email: str, body: dict):
    user = kv.kv_get(f"auth:users:{email}")
    if not user:
        return None
    features = body.get("features")
    if features is not None and isinstance(features, dict):
        user["features"] = {k: bool(v) for k, v in features.items() if k in FEATURE_FLAGS}
    for field in ("first_name", "last_name", "workplace", "city"):
        if field in body:
            user[field] = str(body[field]).strip()
    if "is_admin" in body:
        user["is_admin"] = bool(body["is_admin"])
    kv.kv_set(f"auth:users:{email}", user)
    user.pop("password_hash", None)
    return user


def _admin_user_delete(email: str) -> bool:
    user = kv.kv_get(f"auth:users:{email}")
    if not user:
        return False
    kv.kv_delete(f"auth:users:{email}")
    session_keys = kv.kv_scan("auth:session:*") or []
    for sk in session_keys:
        sess = kv.kv_get(sk)
        if sess and sess.get("email") == email:
            kv.kv_delete(sk)
    return True


def _admin_save_defaults(body: dict):
    clean = {k: bool(v) for k, v in body.items() if k in FEATURE_FLAGS}
    kv.kv_set("auth:access_defaults", clean)
    return {f: clean.get(f, DEFAULT_FEATURE_STATES.get(f, True)) for f in FEATURE_FLAGS}


@router.get("/api/admin/users")
async def api_admin_users_list(request: Request):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_admin(user)
    return _admin_users_list()


@router.get("/api/admin/users/defaults")
async def api_admin_users_defaults(request: Request):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_admin(user)
    return access_defaults()


@router.put("/api/admin/users/defaults")
async def api_admin_users_defaults_update(request: Request, body: dict):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_admin(user)
    return _admin_save_defaults(body)


@router.put("/api/admin/users/{email:path}")
async def api_admin_users_update(email: str, request: Request, body: dict):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_admin(user)
    result = _admin_user_update(email, body)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.delete("/api/admin/users/{email:path}")
async def api_admin_users_delete(email: str, request: Request):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_admin(user)
    if not _admin_user_delete(email):
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}
