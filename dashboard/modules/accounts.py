"""Accounts module — manage user accounts and feature flags in Vercel KV.

This does NOT use the standard ModuleSpec pattern because its data
lives in KV (not a static JSON file) and has its own API shape.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from acumen_core.kv import kv_get, kv_set, kv_delete, kv_scan

FEATURE_FLAGS = [
    "papers",
    "guidelines",
    "pearls",
    "trials",
    "trials_detail",
    "condensed_trials",
    "search",
    "theory",
]

FEATURE_LABELS = {
    "papers": "Papers",
    "guidelines": "Guidelines",
    "pearls": "Pearls",
    "trials": "Trials",
    "trials_detail": "Trial Details",
    "condensed_trials": "Condensed Trials",
    "search": "Search",
    "theory": "Theory",
}

DEFAULT_FEATURE_STATES = {
    "condensed_trials": False,
    "theory": False,
}


def list_users() -> List[Dict[str, Any]]:
    from concurrent.futures import ThreadPoolExecutor
    keys = kv_scan("auth:users:*")
    if not keys:
        return []
    with ThreadPoolExecutor(max_workers=min(10, len(keys))) as pool:
        users = list(pool.map(kv_get, keys))
    users = [u for u in users if u]
    for u in users:
        u.pop("password_hash", None)
    users.sort(key=lambda u: u.get("created_at", ""), reverse=True)
    return users


def get_user(email: str) -> Optional[Dict[str, Any]]:
    user = kv_get(f"auth:users:{email}")
    if user:
        user.pop("password_hash", None)
    return user


def update_user(email: str, body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    user = kv_get(f"auth:users:{email}")
    if not user:
        return None
    features = body.get("features")
    if features is not None and isinstance(features, dict):
        clean = {k: bool(v) for k, v in features.items() if k in FEATURE_FLAGS}
        user["features"] = clean
    for field in ("first_name", "last_name", "workplace", "city"):
        if field in body:
            user[field] = str(body[field]).strip()
    if "is_admin" in body:
        user["is_admin"] = bool(body["is_admin"])
    kv_set(f"auth:users:{email}", user)
    user.pop("password_hash", None)
    return user


def delete_user(email: str) -> bool:
    user = kv_get(f"auth:users:{email}")
    if not user:
        return False
    kv_delete(f"auth:users:{email}")
    # clean up sessions for this user
    session_keys = kv_scan("auth:session:*")
    for sk in session_keys:
        sess = kv_get(sk)
        if sess and sess.get("email") == email:
            kv_delete(sk)
    return True


def get_defaults() -> Dict[str, bool]:
    stored = kv_get("auth:access_defaults")
    stored = stored if isinstance(stored, dict) else {}
    defaults = {flag: stored.get(flag, DEFAULT_FEATURE_STATES.get(flag, True)) for flag in FEATURE_FLAGS}
    kv_set("auth:access_defaults", defaults)
    return defaults


def save_defaults(body: Dict[str, bool]) -> Dict[str, bool]:
    clean = {k: bool(v) for k, v in body.items() if k in FEATURE_FLAGS}
    kv_set("auth:access_defaults", clean)
    return clean
