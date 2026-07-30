import os, sys, json, secrets
from datetime import datetime
from fastapi import FastAPI, Request, Response, HTTPException
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

GOOGLE_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET", "")
PRODUCTION_DOMAIN = "hackccm.vercel.app"

# Save the original dashboard HTML before we override LANDING_HTML
ORIGINAL_DASHBOARD_HTML = revamped_webapp.LANDING_HTML

# Middleware: if logged in and hitting /, serve dashboard instead of login page
@app.middleware("http")
async def auth_dashboard_middleware(request: Request, call_next):
    if request.url.path == "/":
        user = _get_session_user(request)
        if user:
            return HTMLResponse(content=ORIGINAL_DASHBOARD_HTML)
    return await call_next(request)

# =====================================================================
# LANDING PAGE — add Google OAuth button
# =====================================================================

GOOGLE_LANDING_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>hack.CCM — Critical Care Microlearning</title>
<script src="https://accounts.google.com/gsi/client" async defer></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#1F1B14;color:#F1E4CE;font-family:system-ui,sans-serif;display:flex;min-height:100vh;align-items:center;justify-content:center}}
.card{{background:#29241B;border:1px solid #3A3226;border-radius:16px;padding:48px 40px;width:440px;max-width:94vw;text-align:center}}
h1{{font-size:28px;margin-bottom:4px;letter-spacing:-.02em}}
.sub{{color:#C4B18C;font-size:14px;margin-bottom:28px}}
.tabs{{display:flex;gap:0;margin-bottom:24px;border-bottom:1px solid #3A3226}}
.tab{{padding:10px 20px;cursor:pointer;color:#C4B18C;font-size:14px;border-bottom:2px solid transparent;transition:.15s}}
.tab.active{{color:#F1E4CE;border-bottom-color:#E8B778}}
.form{{display:block}}.form.hidden{{display:none}}
.form input{{width:100%;padding:10px 14px;background:#1F1B14;border:1px solid #3A3226;border-radius:8px;color:#F1E4CE;font-size:14px;margin-bottom:12px;outline:none;transition:.15s}}
.form input:focus{{border-color:#E8B778}}
.form .row{{display:flex;gap:10px}}
.form .row input{{flex:1}}
.pw-wrap{{display:flex;gap:6px;align-items:center;margin-bottom:12px}}
.pw-wrap input{{flex:1;margin-bottom:0}}
.pw-wrap .toggle{{width:auto;padding:10px 14px;background:none;border:1px solid #3A3226;border-radius:8px;color:#C4B18C;cursor:pointer;font-size:12px;white-space:nowrap;flex-shrink:0;transition:.15s}}
.pw-wrap .toggle:hover{{border-color:#E8B778;color:#F1E4CE}}
button{{width:100%;padding:11px;background:#E8B778;color:#1F1B14;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;transition:.15s}}
button:hover{{background:#d4a55e}}
.error{{color:#f55;font-size:13px;margin:8px 0;min-height:18px}}
.success{{color:#4ade80;font-size:13px;margin:8px 0}}
.ecg{{text-align:center;font-size:32px;margin-bottom:12px;opacity:.3;letter-spacing:4px}}
.separator{{text-align:center;color:#8A7F6A;font-size:12px;margin:12px 0;position:relative}}
.separator::before,.separator::after{{content:'';position:absolute;top:50%;width:40%;height:1px;background:#3A3226}}
.separator::before{{left:0}}.separator::after{{right:0}}
.google-btn-wrapper{{display:flex;justify-content:center;min-height:42px;margin-bottom:4px}}
.legal{{text-align:center;margin-top:20px;font-size:12px;color:#8A7F6A}}
.legal a{{color:#8A7F6A;text-decoration:none;border-bottom:1px dotted #8A7F6A;cursor:pointer}}
.legal a:hover{{color:#C4B18C}}
.hidden{{display:none!important}}
.overlay{{display:none;position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.7);align-items:center;justify-content:center;padding:20px}}
.overlay-content{{background:#29241B;border:1px solid #3A3226;border-radius:16px;padding:32px;max-width:560px;width:100%;max-height:80vh;overflow-y:auto;color:#F1E4CE;font-size:14px;line-height:1.6}}
.overlay-content h2{{margin-bottom:16px;font-size:20px}}
.overlay-content strong{{color:#E8B778}}
.overlay-close{{float:right;background:none;border:none;color:#C4B18C;font-size:24px;cursor:pointer;line-height:1}}
</style>
</head>
<body>
<div class="card">
<div class="ecg">_~^~_~^~_</div>
<h1>hack.CCM</h1>
<div class="sub">Critical Care Microlearning</div>
<div id="googleSection" class="hidden">
<div class="google-btn-wrapper" id="googleButtonWrapper"></div>
<div class="separator">or</div>
</div>
<div class="tabs"><div class="tab active" onclick="switchTab('login')" id="tabLogin">Sign In</div><div class="tab" onclick="switchTab('signup')" id="tabSignup">Create Account</div></div>
<form class="form" id="loginForm">
<input type="email" id="loginEmail" placeholder="Email" required>
<div class="pw-wrap"><input type="password" id="loginPassword" placeholder="Password" required><button type="button" class="toggle" id="loginPwToggle">Show</button></div>
<div class="error" id="loginError"></div>
<button type="submit">Sign In</button>
</form>
<form class="form hidden" id="signupForm">
<input type="email" id="signupEmail" placeholder="Email" required>
<div class="pw-wrap"><input type="password" id="signupPassword" placeholder="Password (min 8 chars)" required><button type="button" class="toggle" id="pwToggle">Show</button></div>
<div class="row"><input type="text" id="signupFirstName" placeholder="First name"><input type="text" id="signupLastName" placeholder="Last name"></div>
<div class="row"><input type="text" id="signupWorkplace" placeholder="Workplace / Institution"><input type="text" id="signupCity" placeholder="City"></div>
<div class="error" id="signupError"></div>
<div class="success" id="signupSuccess"></div>
<button type="submit">Create Account</button>
</form>
<div class="legal"><a id="landingDisclaimerLink">&#9888;&#65039; Disclaimer</a></div>
</div>
<div class="overlay" id="landingDisclaimerOverlay">
<div class="overlay-content">
<button class="overlay-close" id="landingDisclaimerClose">&times;</button>
<div id="landingDisclaimerText"></div>
</div>
</div>
<script>
var CLIENT_ID = '{GOOGLE_CLIENT_ID}';
var IS_PRODUCTION = location.hostname === '{PRODUCTION_DOMAIN}';
var HAS_GOOGLE_CLIENT = Boolean(CLIENT_ID);

if (IS_PRODUCTION && HAS_GOOGLE_CLIENT) {{
  document.getElementById('googleSection').classList.remove('hidden');
  function handleGoogleCredential(response) {{
    var errEl = document.getElementById('loginError');
    errEl.textContent = '';
    fetch('/api/auth/google', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{credential: response.credential}})
    }}).then(function(r) {{
      if (!r.ok) return r.json().then(function(d) {{ throw new Error(d.detail || 'Google auth failed'); }});
      return r.json();
    }}).then(function(data) {{
      if (data.sid) {{
        document.cookie = '{SESSION_COOKIE_NAME}=' + data.sid + ';path=/;max-age={SESSION_MAX_AGE}';
        window.location.reload();
      }}
    }}).catch(function(err) {{
      errEl.textContent = err.message;
    }});
  }}
  try {{
    if (typeof google !== 'undefined' && google.accounts) {{
      google.accounts.id.initialize({{client_id: CLIENT_ID, callback: handleGoogleCredential, cancel_on_tap_outside: false}});
      google.accounts.id.renderButton(document.getElementById('googleButtonWrapper'), {{type: 'standard', shape: 'rectangular', theme: 'outline', size: 'large', text: 'signin_with'}});
      google.accounts.id.prompt();
    }} else {{
      throw new Error('GSI not loaded');
    }}
  }} catch(e) {{
    document.getElementById('googleButtonWrapper').innerHTML = '<a href="' + location.origin + '/api/auth/google?redirect=' + encodeURIComponent(location.href) + '" style="display:inline-flex;align-items:center;gap:8px;padding:10px 24px;border:1px solid #3A3226;border-radius:8px;color:#F1E4CE;text-decoration:none;font-size:14px;background:#1F1B14"><svg width="18" height="18" viewBox="0 0 48 48"><path fill="#FFC107" d="M43.6 20.1H42V20H24v8h11.3c-1.6 4.6-5.9 8-11.3 8-6.4 0-11.6-5.2-11.6-11.6S17.6 12.8 24 12.8c3 0 5.7 1.1 7.8 2.9l5.7-5.7C34.1 6.7 29.4 4.5 24 4.5 12.7 4.5 3.5 13.7 3.5 25S12.7 45.5 24 45.5 44.5 36.3 44.5 25c0-1.6-.2-3.2-.5-4.7l-.4-.2z"/><path fill="#FF3D00" d="M4.9 14.7l6.6 4.9C13 15 18 12.8 24 12.8c3 0 5.7 1.1 7.8 2.9l5.7-5.7C34.1 6.7 29.4 4.5 24 4.5 16.1 4.5 9.2 8.6 5.7 14.5l-.8.2z"/><path fill="#4CAF50" d="M24 45.5c5.5 0 10.5-2 14.3-5.3l-6.6-5.6c-2.2 1.5-5 2.4-7.7 2.4-5.5 0-10.2-3.6-11.8-8.6l-6.8 5.3C9.2 41.4 16.1 45.5 24 45.5z"/><path fill="#1976D2" d="M43.6 20.1H42V20H24v8h11.3c-.8 2.3-2.2 4.3-4.1 5.7l6.6 5.6c-.1.1 7.7-6 7.7-18.5 0-1.6-.2-3.2-.5-4.7l-.4-.1z"/></svg> Sign in with Google</a>';
  }}
}}

// Handle session param from redirect flow
var params = new URLSearchParams(location.search);
var sidParam = params.get('hackccm_sess');
if (sidParam) {{
  document.cookie = '{SESSION_COOKIE_NAME}=' + sidParam + ';path=/;max-age={SESSION_MAX_AGE}';
  history.replaceState(null, '', location.pathname);
  location.reload();
}}

function switchTab(t){{document.querySelectorAll('.tab').forEach(function(el){{el.classList.toggle('active',el.id==='tab'+t.charAt(0).toUpperCase()+t.slice(1))}});document.getElementById('loginForm').classList.toggle('hidden',t!=='login');document.getElementById('signupForm').classList.toggle('hidden',t!=='signup')}}
document.getElementById('pwToggle').onclick=function(){{var p=document.getElementById('signupPassword');p.type=p.type==='password'?'text':'password';this.textContent=p.type==='password'?'Show':'Hide'}}
document.getElementById('loginPwToggle').onclick=function(){{var p=document.getElementById('loginPassword');p.type=p.type==='password'?'text':'password';this.textContent=p.type==='password'?'Show':'Hide'}}
var discText='**Welcome to hack.CCM \\u{{1F9A9}} \\u2014 Please Read Before You Explore**\\n\\nWelcome! This platform is a hobby passion project designed to make critical care education more structured, accessible, and easily retainable.\\n\\n**\\u26A0\\uFE0F For Education, Not Consultation**\\nThis is a tool for knowledge enhancement and personal study only. It is not a clinical decision-making tool. Always rely on official guidelines and your own institutional protocols for real-world patient care.\\n\\n**\\u{{1F916}} The AI Factor**\\nAs the saying goes, \\"To err is human; to hallucinate is AI.\\" While we have taken immense care to review the data and eliminate errors, AI-assisted formatting isn\\'t always flawless.\\n\\n**\\u{{1F6D1}} Use Responsibly**\\nDouble-check critical values and protocols. You are the clinician; this is just your study buddy.\\n\\n**\\u{{1F50D}} Spotted a Discrepancy?**\\nIf you find any errors, outdated data, or weird AI quirks, please help us improve! Report it via our Feedback button below.';
function showLandingDisclaimer(){{document.getElementById('landingDisclaimerText').innerHTML=discText.replace(/\\*\\*(.+?)\\*\\*/g,'<strong>$1</strong>').replace(/\\n\\n/g,'</p><p>').replace(/\\n/g,'<br>');document.getElementById('landingDisclaimerOverlay').style.display='flex'}}
document.getElementById('landingDisclaimerLink').addEventListener('click',showLandingDisclaimer);
document.getElementById('landingDisclaimerClose').addEventListener('click',function(){{document.getElementById('landingDisclaimerOverlay').style.display='none'}});
document.getElementById('landingDisclaimerOverlay').addEventListener('click',function(e){{if(e.target===this)this.style.display='none'}});
document.getElementById('loginForm').onsubmit=async function(e){{e.preventDefault();var b=this.querySelector('button');b.disabled=true;var err=document.getElementById('loginError');err.textContent='';try{{var r=await fetch('/api/login',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{email:document.getElementById('loginEmail').value,password:document.getElementById('loginPassword').value}})}});if(r.ok){{window.location.reload();return}}var d=await r.json();err.textContent=d.detail||'Invalid email or password'}}catch(e){{err.textContent='Network error'}}b.disabled=false}}
document.getElementById('signupForm').onsubmit=async function(e){{e.preventDefault();var b=this.querySelector('button');b.disabled=true;var err=document.getElementById('signupError');var ok=document.getElementById('signupSuccess');err.textContent='';ok.textContent='';var pw=document.getElementById('signupPassword').value;try{{var r=await fetch('/api/signup',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{email:document.getElementById('signupEmail').value,password:pw,first_name:document.getElementById('signupFirstName').value,last_name:document.getElementById('signupLastName').value,workplace:document.getElementById('signupWorkplace').value,city:document.getElementById('signupCity').value}})}});if(r.ok){{window.location.reload();return}}var d=await r.json();err.textContent=d.detail||'Account creation failed'}}catch(e){{err.textContent='Network error'}}b.disabled=false}}
</script>
</body>
</html>"""

# Override the landing page in revamped_webapp so the root route uses our version
revamped_webapp.LANDING_HTML = GOOGLE_LANDING_HTML

# =====================================================================
# GOOGLE OAUTH — redirect page (served from production domain)
# =====================================================================

@app.get("/api/auth/google")
async def google_auth_redirect(request: Request, redirect: str = ""):
    hostname = request.url.hostname
    is_production = hostname == PRODUCTION_DOMAIN
    has_client = bool(GOOGLE_CLIENT_ID)

    state = secrets.token_urlsafe(16)
    if redirect:
        _kv_set(f"auth:oauth:state:{state}", {"redirect": redirect, "created_at": datetime.utcnow().isoformat()}, ttl=600)

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
    if (data.sid) {{
      document.cookie = '{SESSION_COOKIE_NAME}=' + data.sid + ';path=/;max-age={SESSION_MAX_AGE}';
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
    return HTMLResponse(content=html)

# =====================================================================
# GOOGLE OAUTH — credential handler
# =====================================================================

@app.post("/api/auth/google")
async def google_auth_handler(body: dict, response: Response):
    try:
        credential = body.get("credential", "")
        if not credential:
            raise HTTPException(400, "Missing credential")

        import requests as http
        verify = http.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}", timeout=10)
        if not verify.ok:
            raise HTTPException(401, "Invalid Google credential")

        info = verify.json()
        email = str(info.get("email", "")).strip().lower()
        if not email or not info.get("email_verified"):
            raise HTTPException(401, "Email not verified")

        google_uid = info.get("sub", "")
        given_name = str(info.get("given_name", "") or "")
        family_name = str(info.get("family_name", "") or "")
        full_name = str(info.get("name", "") or "")

        now = datetime.utcnow().isoformat()

        # Check if user exists by email — overwrite with Google data
        existing = _kv_get(f"auth:users:{email}")
        if existing and isinstance(existing, dict):
            existing["google_uid"] = google_uid
            existing["auth_provider"] = "google"
            existing.pop("password_hash", None)
            existing["first_name"] = existing.get("first_name") or given_name or full_name
            existing["last_name"] = existing.get("last_name") or family_name
            existing["last_login"] = now
            user = existing
        else:
            user = {
                "email": email,
                "google_uid": google_uid,
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
        response.set_cookie(key=SESSION_COOKIE_NAME, value=sid, max_age=SESSION_MAX_AGE, httponly=True, samesite="lax", secure=COOKIE_SECURE)

        # Resolve redirect from state
        state_key = body.get("state", "")
        redirect_to = None
        if state_key:
            state_data = _kv_get(f"auth:oauth:state:{state_key}")
            if state_data and isinstance(state_data, dict):
                redirect_to = state_data.get("redirect", "")
            _kv_delete(f"auth:oauth:state:{state_key}")

        return {"ok": True, "sid": sid, "redirect": redirect_to}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        return JSONResponse(500, {"error": type(e).__name__, "detail": str(e), "traceback": traceback.format_exc()})

# =====================================================================
# GOOGLE OAUTH — server-side redirect callback
# =====================================================================

@app.get("/api/auth/google/callback")
async def google_oauth_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error or not code:
        return HTMLResponse(f"<html><body style='background:#1F1B14;color:#F1E4CE;font-family:sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh'><div style='text-align:center'><h2>Sign-in cancelled or failed</h2><p style='color:#f55;margin:12px 0'>{error or 'No authorization code received'}</p><a href='/' style='color:#E8B778'>Back to home</a></div></body></html>")

    # Verify state
    state_data = _kv_get(f"auth:oauth:state:{state}")
    if not state_data or not isinstance(state_data, dict):
        return HTMLResponse("<html><body style='background:#1F1B14;color:#F1E4CE;font-family:sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh'><div style='text-align:center'><h2>Invalid or expired state</h2><a href='/' style='color:#E8B778'>Back to home</a></div></body></html>", status_code=403)
    redirect_to = state_data.get("redirect", "/")
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
        return HTMLResponse(f"<html><body style='background:#1F1B14;color:#F1E4CE;font-family:sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh'><div style='text-align:center'><h2>Token exchange failed</h2><p style='color:#f55;margin:12px 0'>{token_resp.status_code}</p><a href='/' style='color:#E8B778'>Back to home</a></div></body></html>", status_code=502)

    tokens = token_resp.json()
    id_token = tokens.get("id_token", "")
    if not id_token:
        return HTMLResponse("<html><body style='background:#1F1B14;color:#F1E4CE;font-family:sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh'><div style='text-align:center'><h2>No ID token received</h2><a href='/' style='color:#E8B778'>Back to home</a></div></body></html>", status_code=502)

    # Verify the ID token via Google's tokeninfo endpoint
    verify = http.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}", timeout=10)
    if not verify.ok:
        return HTMLResponse("<html><body style='background:#1F1B14;color:#F1E4CE;font-family:sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh'><div style='text-align:center'><h2>Token verification failed</h2><a href='/' style='color:#E8B778'>Back to home</a></div></body></html>", status_code=502)

    info = verify.json()
    email = str(info.get("email", "")).strip().lower()
    if not email or not info.get("email_verified"):
        return HTMLResponse("<html><body style='background:#1F1B14;color:#F1E4CE;font-family:sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh'><div style='text-align:center'><h2>Email not verified</h2><a href='/' style='color:#E8B778'>Back to home</a></div></body></html>", status_code=403)

    google_uid = info.get("sub", "")
    given_name = str(info.get("given_name", "") or "")
    family_name = str(info.get("family_name", "") or "")
    now = datetime.utcnow().isoformat()

    existing = _kv_get(f"auth:users:{email}")
    if existing and isinstance(existing, dict):
        existing["google_uid"] = google_uid
        existing["auth_provider"] = "google"
        existing.pop("password_hash", None)
        existing["first_name"] = existing.get("first_name") or given_name or family_name
        existing["last_name"] = existing.get("last_name") or family_name
        existing["last_login"] = now
        user = existing
    else:
        user = {
            "email": email,
            "google_uid": google_uid,
            "auth_provider": "google",
            "first_name": given_name or info.get("name", ""),
            "last_name": family_name,
            "created_at": now,
            "last_login": now,
            "features": {},
        }

    _kv_set(f"auth:users:{email}", user)

    sid = _session_id()
    _kv_set(f"auth:session:{sid}", {"email": email, "created_at": now}, ttl=SESSION_MAX_AGE)

    # Redirect back with session cookie
    sep = "&" if "?" in redirect_to else "?"
    redirect_url = f"{redirect_to}{sep}hackccm_sess={sid}"
    resp = HTMLResponse(status_code=302)
    resp.headers["Location"] = redirect_url
    resp.set_cookie(key=SESSION_COOKIE_NAME, value=sid, max_age=SESSION_MAX_AGE, httponly=True, samesite="lax", secure=COOKIE_SECURE)
    return resp

