"""Account endpoints: signup, login, logout and the current user."""
import logging

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from acumen_core import kv
from webapp.auth import (
    get_session_user,
    hash_password,
    needs_rehash,
    new_session_id,
    now_iso,
    PASSWORD_MAX_LEN,
    retire_default_admin_password,
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE,
    set_session_cookie,
    verify_password,
)

router = APIRouter()
log = logging.getLogger("hackccm")


@router.post("/api/signup")
async def api_signup(body: dict, response: Response):
    try:
        email = str(body.get("email", "")).strip().lower()
        password = body.get("password", "")
        if not email or "@" not in email:
            raise HTTPException(400, "Valid email required")
        if not isinstance(password, str) or len(password) < 8:
            raise HTTPException(400, "Password must be at least 8 characters")
        if len(password) > PASSWORD_MAX_LEN:
            raise HTTPException(400, f"Password must be at most {PASSWORD_MAX_LEN} characters")
        if kv.kv_get(f"auth:users:{email}"):
            raise HTTPException(409, "An account with this email already exists")
        user = {
            "email": email,
            "first_name": str(body.get("first_name", "")).strip(),
            "last_name": str(body.get("last_name", "")).strip(),
            "workplace": str(body.get("workplace", "")).strip(),
            "city": str(body.get("city", "")).strip(),
            "password_hash": hash_password(password),
            "created_at": now_iso(),
            "features": {},
        }
        kv.kv_set(f"auth:users:{email}", user)
        sid = new_session_id()
        kv.kv_set(f"auth:session:{sid}", {"email": email, "created_at": now_iso()}, ttl=SESSION_MAX_AGE)
        set_session_cookie(response, sid)
        return {"ok": True, "email": email}
    except HTTPException:
        raise
    except Exception:
        log.exception("signup failed")
        return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})


@router.post("/api/login")
async def api_login(body: dict, response: Response):
    try:
        email = str(body.get("email", "")).strip().lower()
        password = body.get("password", "")
        if not email or not password or not isinstance(password, str):
            raise HTTPException(400, "Email and password required")
        user = kv.kv_get(f"auth:users:{email}")
        if not user or not isinstance(user, dict):
            raise HTTPException(401, "Invalid email or password")
        pwh = user.get("password_hash")
        if not pwh:
            raise HTTPException(401, "Invalid email or password")
        if retire_default_admin_password(user):
            raise HTTPException(401, "Invalid email or password")
        if not verify_password(password, pwh):
            raise HTTPException(401, "Invalid email or password")
        if needs_rehash(pwh):  # upgrade an older hash now that we hold the plaintext
            user["password_hash"] = hash_password(password)
            kv.kv_set(f"auth:users:{email}", user)
        sid = new_session_id()
        kv.kv_set(f"auth:session:{sid}", {"email": email, "created_at": now_iso()}, ttl=SESSION_MAX_AGE)
        set_session_cookie(response, sid)
        return {"ok": True, "email": email}
    except HTTPException:
        raise
    except Exception:
        log.exception("login failed")
        return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})


@router.post("/api/logout")
async def api_logout(request: Request, response: Response):
    sid = request.cookies.get(SESSION_COOKIE_NAME)
    if sid:
        kv.kv_delete(f"auth:session:{sid}")
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"ok": True}


@router.get("/api/me")
async def api_me(request: Request):
    user = get_session_user(request)
    if not user:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "email": user["email"],
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
        "workplace": user.get("workplace", ""),
        "city": user.get("city", ""),
        "is_admin": bool(user.get("is_admin")),
        "features": user.get("features", {}),
    }
