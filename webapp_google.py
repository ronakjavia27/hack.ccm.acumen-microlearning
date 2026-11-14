import logging
import os, sys, secrets
from html import escape as _esc
from urllib.parse import urlsplit, urlunsplit
from fastapi import Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

# Import the existing app (all routes + auth helpers register on import)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import revamped_webapp

app = revamped_webapp.app

# Pull in auth helpers from the base module
_kv_get = revamped_webapp._kv_get
_kv_set = revamped_webapp._kv_set
_kv_delete = revamped_webapp._kv_delete
_session_id = revamped_webapp._session_id
_get_session_user = revamped_webapp._get_session_user
SESSION_COOKIE_NAME = revamped_webapp.SESSION_COOKIE_NAME
SESSION_MAX_AGE = revamped_webapp.SESSION_MAX_AGE
COOKIE_SECURE = revamped_webapp.COOKIE_SECURE
_now_iso = revamped_webapp._now_iso

log = logging.getLogger("hackccm.google")

GOOGLE_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET", "")
PRODUCTION_DOMAIN = "hackccm.vercel.app"

# =====================================================================
# LANDING PAGE — switch on the Google section of the shared sign-in page
# =====================================================================

app.state.google_auth = {
    "client_id": GOOGLE_CLIENT_ID,
    "production_domain": PRODUCTION_DOMAIN,
}

# =====================================================================
# GOOGLE OAUTH — shared helpers
# =====================================================================

GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")
OAUTH_STATE_COOKIE = "hackccm_oauth_state"


def _safe_redirect(target):
    """Where to send the user after sign-in. Only places on this site are allowed (a path, or a
    URL on PRODUCTION_DOMAIN, reduced to its path); anything else falls back to "/"."""
    t = str(target or "").strip()
    if not t or any(ord(c) < 32 for c in t) or "\\" in t:
        return "/"
    if t.startswith("/") and not t.startswith("//"):
        return t
    parts = urlsplit(t)
    if parts.scheme in ("http", "https") and parts.hostname == PRODUCTION_DOMAIN:
        return urlunsplit(("", "", parts.path or "/", parts.query, parts.fragment))
    return "/"


def _verify_google_id_token(id_token):
    """Check an ID token with Google's tokeninfo endpoint (signature + expiry) and make sure it
    was issued to *this* app. Returns (claims, email) or raises HTTPException(401)."""
    import requests as http
    resp = http.get("https://oauth2.googleapis.com/tokeninfo", params={"id_token": id_token}, timeout=10)
    if not resp.ok:
        raise HTTPException(401, "Invalid Google credential")
    info = resp.json()
    if not GOOGLE_CLIENT_ID or info.get("aud") != GOOGLE_CLIENT_ID:
        raise HTTPException(401, "Google credential was not issued for this app")
    if info.get("iss") not in GOOGLE_ISSUERS:
        raise HTTPException(401, "Invalid Google credential issuer")
    email = str(info.get("email", "")).strip().lower()
    if not email or str(info.get("email_verified")).lower() != "true":
        raise HTTPException(401, "Email not verified")
    return info, email


def _google_sign_in(info, email):
    """Create or refresh the account for a verified Google identity and open a session."""
    given_name = str(info.get("given_name", "") or "")
    family_name = str(info.get("family_name", "") or "")
    full_name = str(info.get("name", "") or "")
    now = _now_iso()
    existing = _kv_get(f"auth:users:{email}")
    if existing and isinstance(existing, dict):
        existing["google_uid"] = info.get("sub", "")
        existing["auth_provider"] = "google"
        # a verified Google email takes over any password account registered with it, so a
        # password set by someone who pre-registered the address stops working
        existing.pop("password_hash", None)
        existing["first_name"] = existing.get("first_name") or given_name or full_name
        existing["last_name"] = existing.get("last_name") or family_name
        existing["last_login"] = now
        user = existing
    else:
        user = {
            "email": email,
            "google_uid": info.get("sub", ""),
            "auth_provider": "google",
            "first_name": given_name or full_name,
            "last_name": family_name,
            "created_at": now,
            "last_login": now,
            "features": {},
        }
    _kv_set(f"auth:users:{email}", user)
    sid = _session_id()
    _kv_set(f"auth:session:{sid}", {"email": email, "created_at": now}, ttl=SESSION_MAX_AGE)
    return sid


def _set_session_cookie(response, sid):
    response.set_cookie(key=SESSION_COOKIE_NAME, value=sid, max_age=SESSION_MAX_AGE, httponly=True, samesite="lax", secure=COOKIE_SECURE)


def _oauth_error_page(title, detail=None):
    detail_html = f"<p style='color:#f55;margin:12px 0'>{_esc(str(detail))}</p>" if detail is not None else ""
    return HTMLResponse(f"<html><body style='background:#1F1B14;color:#F1E4CE;font-family:sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh'><div style='text-align:center'><h2>{title}</h2>{detail_html}<a href='/' style='color:#E8B778'>Back to home</a></div></body></html>")

# =====================================================================
# GOOGLE OAUTH — redirect page (served from production domain)
# =====================================================================

@app.get("/api/auth/google")
async def google_auth_redirect(request: Request, redirect: str = ""):
    hostname = request.url.hostname
    is_production = hostname == PRODUCTION_DOMAIN
    has_client = bool(GOOGLE_CLIENT_ID)

    state = secrets.token_urlsafe(16)
    _kv_set(f"auth:oauth:state:{state}", {"redirect": _safe_redirect(redirect), "created_at": _now_iso()}, ttl=600)

    if not is_production or not has_client:
        if not is_production:
            msg = f"Google Sign-In is only available on <strong>{PRODUCTION_DOMAIN}</strong>."
        else:
            msg = "Google Sign-In is not configured. Please set <strong>OAUTH_CLIENT_ID</strong>."
        html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>hack.CCM — Google Sign-In</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#1F1B14;color:#F1E4CE;font-family:system-ui,sans-serif;display:flex;min-height:100vh;align-items:center;justify-content:center}}
.card{{background:#29241B;border:1px solid #3A3226;border-radius:16px;padding:40px;width:400px;max-width:94vw;text-align:center}}
h1{{font-size:24px;margin-bottom:4px}}
p{{color:#C4B18C;font-size:14px;margin-bottom:16px;line-height:1.5}}
.back{{display:inline-block;margin-top:20px;color:#E8B778;font-size:13px;text-decoration:none}}
</style>
</head>
<body>
<div class="card">
<div style="font-size:40px;margin-bottom:12px;opacity:.3">_~^~_~^~_</div>
<h1>hack.CCM</h1>
<p>{msg}</p>
<p>Please use <strong>email &amp; password</strong> to sign in, or configure Google OAuth credentials.</p>
<a href="/" class="back">&larr; Back to sign in</a>
</div>
</body>
</html>"""
        return HTMLResponse(content=html)

    # Production: render GSI button + server-side redirect fallback
    from urllib.parse import urlencode
    oauth_params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": f"https://{PRODUCTION_DOMAIN}/api/auth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    oauth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(oauth_params)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>hack.CCM — Google Sign-In</title>
<script src="https://accounts.google.com/gsi/client" async defer></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#1F1B14;color:#F1E4CE;font-family:system-ui,sans-serif;display:flex;min-height:100vh;align-items:center;justify-content:center}}
.card{{background:#29241B;border:1px solid #3A3226;border-radius:16px;padding:40px;width:400px;max-width:94vw;text-align:center}}
h1{{font-size:24px;margin-bottom:4px}}
p{{color:#C4B18C;font-size:14px;margin-bottom:24px}}
.google-btn-wrapper{{display:flex;justify-content:center;min-height:42px;margin-bottom:8px}}
.fallback{{margin-top:16px}}
.fallback a{{display:inline-flex;align-items:center;gap:8px;padding:10px 24px;border:1px solid #3A3226;border-radius:8px;color:#F1E4CE;text-decoration:none;font-size:14px;background:#1F1B14;transition:.15s}}
.fallback a:hover{{border-color:#E8B778}}
.msg{{color:#8A7F6A;font-size:12px;margin-top:12px}}
.error{{color:#f55;font-size:13px;margin:8px 0;min-height:18px}}
.back{{display:inline-block;margin-top:20px;color:#8A7F6A;font-size:13px;text-decoration:none}}
.back:hover{{color:#C4B18C}}
</style>
</head>
<body>
<div class="card">
<div style="font-size:40px;margin-bottom:12px;opacity:.3">_~^~_~^~_</div>
<h1>hack.CCM</h1>
<p>Sign in with Google</p>
<div class="google-btn-wrapper" id="googleButtonWrapper"></div>
<div class="error" id="error"></div>
<div class="fallback" id="fallbackSection" style="display:none">
<div style="color:#8A7F6A;font-size:12px;margin-bottom:8px">or</div>
<a href="{oauth_url}" id="serverRedirectLink">
<svg width="18" height="18" viewBox="0 0 48 48"><path fill="#FFC107" d="M43.6 20.1H42V20H24v8h11.3c-1.6 4.6-5.9 8-11.3 8-6.4 0-11.6-5.2-11.6-11.6S17.6 12.8 24 12.8c3 0 5.7 1.1 7.8 2.9l5.7-5.7C34.1 6.7 29.4 4.5 24 4.5 12.7 4.5 3.5 13.7 3.5 25S12.7 45.5 24 45.5 44.5 36.3 44.5 25c0-1.6-.2-3.2-.5-4.7l-.4-.2z"/><path fill="#FF3D00" d="M4.9 14.7l6.6 4.9C13 15 18 12.8 24 12.8c3 0 5.7 1.1 7.8 2.9l5.7-5.7C34.1 6.7 29.4 4.5 24 4.5 16.1 4.5 9.2 8.6 5.7 14.5l-.8.2z"/><path fill="#4CAF50" d="M24 45.5c5.5 0 10.5-2 14.3-5.3l-6.6-5.6c-2.2 1.5-5 2.4-7.7 2.4-5.5 0-10.2-3.6-11.8-8.6l-6.8 5.3C9.2 41.4 16.1 45.5 24 45.5z"/><path fill="#1976D2" d="M43.6 20.1H42V20H24v8h11.3c-.8 2.3-2.2 4.3-4.1 5.7l6.6 5.6c-.1.1 7.7-6 7.7-18.5 0-1.6-.2-3.2-.5-4.7l-.4-.1z"/></svg> Continue with Google (redirect)
</a>
<div class="msg">After signing in you'll be sent back to continue.</div>
</div>
<a href="/" class="back">&larr; Back to sign in</a>
</div>
<script>
var CLIENT_ID = '{GOOGLE_CLIENT_ID}';
function handleCredentialResponse(response) {{
  var errEl = document.getElementById('error');
  errEl.textContent = '';
  fetch('/api/auth/google', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{credential: response.credential}})
  }}).then(function(r) {{
    if (!r.ok) return r.json().then(function(d) {{ throw new Error(d.detail || 'Auth failed'); }});
    return r.json();
  }}).then(function(data) {{
    if (data.ok) {{
      window.location.href = data.redirect || '/';
    }}
  }}).catch(function(err) {{
    errEl.textContent = err.message;
    document.getElementById('fallbackSection').style.display = 'block';
  }});
}}
try {{
  if (typeof google !== 'undefined' && google.accounts) {{
    google.accounts.id.initialize({{client_id: CLIENT_ID, callback: handleCredentialResponse, cancel_on_tap_outside: false}});
    google.accounts.id.renderButton(document.getElementById('googleButtonWrapper'), {{type: 'standard', shape: 'rectangular', theme: 'outline', size: 'large', text: 'signin_with'}});
    google.accounts.id.prompt();
  }} else {{
    throw new Error('GSI not loaded');
  }}
}} catch(e) {{
  document.getElementById('error').textContent = 'Popup sign-in unavailable.';
  document.getElementById('fallbackSection').style.display = 'block';
}}
</script>
</body>
</html>"""
    page = HTMLResponse(content=html)
    # the callback only accepts a state that this browser was given
    page.set_cookie(key=OAUTH_STATE_COOKIE, value=state, max_age=600, httponly=True, samesite="lax", secure=COOKIE_SECURE)
    return page

# =====================================================================
# GOOGLE OAUTH — credential handler
# =====================================================================

@app.post("/api/auth/google")
async def google_auth_handler(body: dict, response: Response):
    try:
        credential = body.get("credential", "")
        if not credential:
            raise HTTPException(400, "Missing credential")
        info, email = _verify_google_id_token(credential)
        sid = _google_sign_in(info, email)
        _set_session_cookie(response, sid)

        # Resolve redirect from state
        state_key = body.get("state", "")
        redirect_to = None
        if state_key:
            state_data = _kv_get(f"auth:oauth:state:{state_key}")
            if state_data and isinstance(state_data, dict):
                redirect_to = _safe_redirect(state_data.get("redirect"))
            _kv_delete(f"auth:oauth:state:{state_key}")

        return {"ok": True, "redirect": redirect_to}
    except HTTPException:
        raise
    except Exception:
        log.exception("Google sign-in failed")
        return JSONResponse(status_code=500, content={"detail": "Sign-in failed. Please try again."})

# =====================================================================
# GOOGLE OAUTH — server-side redirect callback
# =====================================================================

@app.get("/api/auth/google/callback")
async def google_oauth_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error or not code:
        return _oauth_error_page("Sign-in cancelled or failed", error or "No authorization code received")

    # The state must exist server-side AND have been issued to this browser (cookie set when the
    # flow started); otherwise someone could log a victim into the attacker's account.
    cookie_state = request.cookies.get(OAUTH_STATE_COOKIE, "")
    state_data = _kv_get(f"auth:oauth:state:{state}") if state else None
    if (not state or not cookie_state or not isinstance(state_data, dict)
            or not secrets.compare_digest(cookie_state.encode(), state.encode())):
        return _oauth_error_page("Invalid or expired state")
    redirect_to = _safe_redirect(state_data.get("redirect"))
    _kv_delete(f"auth:oauth:state:{state}")

    # Exchange code for tokens
    import requests as http
    token_resp = http.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": f"https://{PRODUCTION_DOMAIN}/api/auth/google/callback",
        "grant_type": "authorization_code",
    }, timeout=10)
    if not token_resp.ok:
        return _oauth_error_page("Token exchange failed", token_resp.status_code)

    id_token = token_resp.json().get("id_token", "")
    if not id_token:
        return _oauth_error_page("No ID token received")

    try:
        info, email = _verify_google_id_token(id_token)
    except HTTPException as exc:
        return _oauth_error_page("Email not verified" if "verified" in str(exc.detail) else "Token verification failed")

    sid = _google_sign_in(info, email)
    resp = HTMLResponse(status_code=302)
    resp.headers["Location"] = redirect_to
    _set_session_cookie(resp, sid)
    resp.delete_cookie(OAUTH_STATE_COOKIE)
    return resp
