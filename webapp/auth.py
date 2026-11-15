"""Sessions, password hashing, feature flags and the local-dev auto-login."""
import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, Request, Response

from acumen_core import kv
from acumen_core.features import resolve_defaults

log = logging.getLogger("hackccm")


SESSION_COOKIE_NAME = "hackccm_sess"
SESSION_MAX_AGE = 2592000  # 30 days
COOKIE_SECURE = os.environ.get("VERCEL", "").lower() == "1"


# ---- Password hashing (stdlib only) ----
# scrypt (memory-hard) with a per-password salt. Hashes written by older versions
# ("$sha256$salt$hash") still verify and are upgraded on the user's next successful login.
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1
PASSWORD_MAX_LEN = 1024


def hash_password(password):
    salt = os.urandom(16)
    h = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return f"$scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${h.hex()}"


def verify_password(password, pw_hash):
    if not isinstance(pw_hash, str) or not isinstance(password, str) or len(password) > PASSWORD_MAX_LEN:
        return False
    parts = pw_hash.split("$")
    try:
        if len(parts) == 7 and parts[1] == "scrypt":
            n, r, p = int(parts[2]), int(parts[3]), int(parts[4])
            salt, expected = bytes.fromhex(parts[5]), bytes.fromhex(parts[6])
            h = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=len(expected))
            return hmac.compare_digest(h, expected)
        if len(parts) == 4 and parts[1] == "sha256":  # legacy format
            salt = bytes.fromhex(parts[2])
            h = hashlib.sha256(salt + password.encode("utf-8")).hexdigest()
            return hmac.compare_digest(h.encode(), parts[3].encode())
    except (ValueError, IndexError, OverflowError, MemoryError):
        return False
    return False


def needs_rehash(pw_hash):
    return not (isinstance(pw_hash, str) and pw_hash.startswith(f"$scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}$"))


def new_session_id():
    return secrets.token_urlsafe(32)


def now_iso():
    """UTC timestamp as a naive ISO string (the format already stored in KV)."""
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


# ---- Local dev: bypass login ----
# On Vercel (VERCEL=1) login is always required. For a developer running the portal on their
# own machine, requests auto-login as a local admin so the login page never blocks local use.
# That shortcut is deliberately narrow: it needs the local KV file (never Upstash/production),
# a request made through localhost, and no reverse-proxy headers, so a Docker/VPS deployment
# or a run pointed at production KV can never hand out the admin account. LOCAL_DEV=0 turns it off.
LOCAL_DEV_MODE = (
    os.environ.get("VERCEL", "").strip().lower() != "1"
    and os.environ.get("LOCAL_DEV", "").strip().lower() not in ("0", "false", "no", "off")
)
_LOOPBACK_HOSTS = ("127.0.0.1", "::1", "localhost")
_PROXY_HEADERS = ("x-forwarded-for", "x-forwarded-host", "x-real-ip", "forwarded", "x-vercel-id")
DEFAULT_ADMIN_EMAIL = "admin@gmail.com"
_RETIRED_DEFAULT_PASSWORD = "admin@admin"  # older versions created the local admin with this password


def dev_login_allowed(request):
    if not LOCAL_DEV_MODE:
        return False
    from acumen_core import kv as _kvmod
    if _kvmod.kv_backend()["backend"] != "local":
        return False
    client = request.client.host if request.client else ""
    if client not in _LOOPBACK_HOSTS or request.url.hostname not in _LOOPBACK_HOSTS:
        return False
    return not any(h in request.headers for h in _PROXY_HEADERS)


# Stored hashes already checked against the retired default password. Verifying costs an scrypt run
# (~40 ms), and the local dev admin is looked up on every cookie-less request, so each distinct hash
# is only checked once per process. A different hash (e.g. someone resets the password to the
# default) is not in the set and is checked again.
_not_default_hashes = set()


def retire_default_admin_password(user):
    """Older versions gave the local admin the password 'admin@admin'. If an account still has it
    (e.g. it was created in a shared KV), replace it with an unguessable one. True if replaced."""
    if user.get("email") != DEFAULT_ADMIN_EMAIL:
        return False
    stored = user.get("password_hash")
    if isinstance(stored, str) and stored in _not_default_hashes:
        return False
    if verify_password(_RETIRED_DEFAULT_PASSWORD, stored):
        user["password_hash"] = hash_password(secrets.token_urlsafe(32))
        kv.kv_set(f"auth:users:{DEFAULT_ADMIN_EMAIL}", user)
        log.warning("Disabled the default password of %s", DEFAULT_ADMIN_EMAIL)
        return True
    if isinstance(stored, str):
        _not_default_hashes.add(stored)
    return False


def dev_admin_user():
    """The local admin account (created on first use, with a random password nobody knows)."""
    user = kv.kv_get(f"auth:users:{DEFAULT_ADMIN_EMAIL}")
    if not isinstance(user, dict) or not user:
        user = {
            "email": DEFAULT_ADMIN_EMAIL,
            "first_name": "Admin",
            "last_name": "",
            "workplace": "",
            "city": "",
            "password_hash": hash_password(secrets.token_urlsafe(32)),
            "created_at": now_iso(),
            "features": {},
            "is_admin": True,
        }
        kv.kv_set(f"auth:users:{DEFAULT_ADMIN_EMAIL}", user)
    else:
        retire_default_admin_password(user)
    return user


def local_dev_login():
    """Local admin plus a fresh session for it. Returns (user, session_id)."""
    user = dev_admin_user()
    sid = new_session_id()
    kv.kv_set(f"auth:session:{sid}", {"email": DEFAULT_ADMIN_EMAIL, "created_at": now_iso()}, ttl=SESSION_MAX_AGE)
    return user, sid


# ---- Auth helpers ----
def get_session_user(request):
    sid = request.cookies.get(SESSION_COOKIE_NAME)
    if not sid:
        return dev_admin_user() if dev_login_allowed(request) else None
    sess = kv.kv_get(f"auth:session:{sid}")
    if not sess:
        return dev_admin_user() if dev_login_allowed(request) else None
    return kv.kv_get(f"auth:users:{sess.get('email')}")


async def require_user(request: Request, response: Response):
    user = get_session_user(request)
    if not user:
        response.delete_cookie(SESSION_COOKIE_NAME)
        raise HTTPException(status_code=401, detail="Login required")
    return user


def access_defaults():
    d = kv.kv_get("auth:access_defaults")
    if d is None:
        d = {}
        kv.kv_set("auth:access_defaults", d)
    return resolve_defaults(d)


def user_has_feature(user, feature):
    if user.get("is_admin"):
        return True
    defaults = access_defaults()
    overrides = user.get("features", {}) or {}
    return {**defaults, **overrides}.get(feature, False)


def require_feature(user, feature):
    if not user_has_feature(user, feature):
        raise HTTPException(status_code=403, detail=f"Feature '{feature}' is not enabled for this account")


def require_admin(user):
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")


def set_session_cookie(response, sid):
    """Open the browser session: the one (HttpOnly) cookie that carries the session id."""
    response.set_cookie(key=SESSION_COOKIE_NAME, value=sid, max_age=SESSION_MAX_AGE, httponly=True, samesite="lax", secure=COOKIE_SECURE)
