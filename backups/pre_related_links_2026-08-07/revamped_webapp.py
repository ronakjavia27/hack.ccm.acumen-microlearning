import os
import json
import re
import html
import secrets
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import FastAPI, Request, Response, Depends, HTTPException, Cookie
from fastapi.responses import HTMLResponse, JSONResponse

# =====================================================================
# CONFIGURATION
# =====================================================================

FEEDBACK_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSd6xRmmimmVc0Sv4AeNls-oxLR6k_zX8D_QERFZwPP6zlfjRw/viewform?usp=header"
SUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSffsrF8DPWaTa-03XisMqSU5Da_8QdE-JrINdDP5iRmvWAI8Q/viewform?usp=header"
UNSUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScz864mkLh5AqBYVzAh573hWu98NdmwwPC2vaU1lfBE3WHHHg/viewform?usp=header"

DISCLAIMER_TEXT = """**Welcome to hack.CCM \U0001F9A9 — Please Read Before You Explore**

Welcome! This platform is a hobby passion project designed to make critical care education more structured, accessible, and easily retainable.

To help you get the most out of your study sessions, we use AI to condense massive volumes of medical text, guidelines, and open-source research papers into highly readable summaries. However, before you dive in, please note the following:

**\u26A0\uFE0F For Education, Not Consultation**
This is a tool for knowledge enhancement and personal study only. It is not a clinical decision-making tool. Always rely on official guidelines and your own institutional protocols for real-world patient care.

**\U0001F916 The AI Factor**
As the saying goes, "To err is human; to hallucinate is AI." While we have taken immense care to review the data and eliminate errors, AI-assisted formatting isn't always flawless.

**\U0001F6D1 Use Responsibly**
Double-check critical values and protocols. You are the clinician; this is just your study buddy.

**\U0001F50D Spotted a Discrepancy?**
If you find any errors, outdated data, or weird AI quirks, please help us improve! Report it via our Feedback button below.

The ultimate aim here is to format large information into quick, retainable reads. This does not replace the need to study original papers or guidelines in full detail. Adequate emphasis and credit have been given to the original authors and journals wherever possible—I claim no personal ownership over this data.

By clicking "Proceed" below, you acknowledge that you understand this tool's educational purpose and agree to use it responsibly."""

OUTPUT_DIR = "./output_files"
JSON_TRACKER_FILE = "./sent_summaries.json"
PEARLS_JSON = "./pearls.json"
ESBICM_INDEX_PATH = "./output_files/esbicm_trials/esbicm_trials_index.json"
CONDENSED_TRIALS_DIR = "./output_files/trials_database_condensed"

CREDITS_TEXT = """**Editor(s)**

**Dr. Ankur Gupta**, MBBS, EDIC, FCCCM, AFIC, PGDID, FICM, PGDMLE
Consultant Intensivist, Apollo Hospitals, Indore, INDIA
Founder President, Educational Society of Bedside Intensive Care Medicine (ESBICM)

**Dr. Pranay Bajpai**, MD (Medicine), FCCS, IDCC, MBA (HA)
Assistant Professor, Department of Medicine
MGM Medical College & M.Y. Group of Hospitals, Indore, INDIA
Consultant, Critical Care & Respiratory Medicine, Apollo Hospitals, Indore

**Co-Editor**

**Dr. Sonal Kaushika**, MBBS, FCCCM, AFIC
Associate Consultant, Critical Care
Shalby Hospital, Ahmedabad, Gujarat, INDIA

**A project by:**
Academic Committee of ESBICM (ACE)

**Contributors**

**Dr. Nikhilesh Jain**, DNB (Med), MRCPI, IDCCM, FCCCM, PGDHM, FIECMO
Director and Operational Head, Department of Critical Care Services
Care CHL Hospital, Indore

**Dr. Vivek Joshi**, DA, IDCCM, FCCCM, MBA (HA)
Medical Superintendent and Head, Critical Care
Shalby Hospital, Indore

**Dr. Vivek Baxi**, MD, FCCCM, AFIC, PGCDM
Head, Department of Critical Care Medicine
Consultant Intensivist and Physician
Shalby Hospitals (Naroda), Ahmedabad, Gujarat

**Dr. Prerna Bedi Lakhotia**, MBBS, DNB (Anesthesia), IDCCM, FGID
Consultant Intensivist
Apollo Hospitals, Indore

**Dr. Benjamin Baby Johnson**, MBBS, AFIC, PGDMLE
Consultant, Critical Care & ICU In-charge
Sankeshwar Mission Hospital

**Dr. Abhi Paliwal**, MBBS, DNB (Family Medicine), AFIC
Associate Consultant, Critical Care
Apollo Hospitals, Indore"""

TRIAL_DISCLAIMER_TEXT = """**Legal Disclaimer**

**Educational Purpose Only**
This website provides summaries of published clinical trials for informational and educational purposes only. It is not a substitute for professional medical advice, diagnosis, or treatment.

**No Warranties & Evolving Information**
Medical knowledge changes rapidly. While we aim for accuracy, the authors and publishers make no express or implied warranties regarding the completeness, accuracy, or currency of this content. We assume no liability for errors, omissions, or clinical outcomes resulting from the use of this data.

**Professional Duty**
Practitioners must exercise independent clinical judgment. Always consult original trial publications and manufacturer guidelines to verify dosages, contraindications, and administration methods before treating patients."""

ESBICM_SPEC_COLORS = {
    "Airway & Procedures": "#8B5CF6",
    "ARDS & Mechanical Ventilation": "#0EA5E9",
    "Cardiac Arrest & Post-Resuscitation Care": "#EF4444",
    "Cardiovascular Critical Care": "#C6554B",
    "General ICU & Miscellaneous": "#6B7280",
    "Hematology & Transfusion": "#E11D48",
    "Infection & Antibiotic Stewardship": "#10B981",
    "Neurological Critical Care": "#6B5B95",
    "Nutrition, GI & Glycemic Control": "#84CC16",
    "Renal & Electrolytes (AKI, RRT)": "#D97706",
    "Sedation, Analgesia & Delirium": "#F97316",
    "Sepsis & Septic Shock": "#DC2626",
    "Trauma, Hemorrhage, Coagulopathy & VTE": "#9333EA",
}

app = FastAPI()

# =====================================================================
# AUTHENTICATION
# =====================================================================

SESSION_COOKIE_NAME = "hackccm_sess"
SESSION_MAX_AGE = 2592000  # 30 days
COOKIE_SECURE = os.environ.get("VERCEL", "").lower() == "1"

from acumen_core.kv import kv_get as _kv_get, kv_set as _kv_set, kv_delete as _kv_delete, kv_scan as _kv_scan

# =====================================================================

# ---- Password hashing (stdlib only) ----
def _hash_password(password):
    salt = os.urandom(16)
    h = hashlib.sha256(salt + password.encode("utf-8")).hexdigest()
    return f"$sha256${salt.hex()}${h}"

def _verify_password(password, pw_hash):
    if not pw_hash or not pw_hash.startswith("$sha256$"):
        return False
    parts = pw_hash.split("$")
    if len(parts) != 4:
        return False
    try:
        salt = bytes.fromhex(parts[2])
        h = hashlib.sha256(salt + password.encode("utf-8")).hexdigest()
        return h == parts[3]
    except (ValueError, IndexError):
        return False

def _session_id():
    return secrets.token_urlsafe(32)

# ---- Local dev: bypass login entirely ----
# On Vercel (VERCEL=1) login is required. When running locally, auto-login
# as the local admin account so the login page never blocks local use.
LOCAL_DEV_MODE = os.environ.get("VERCEL", "").strip().lower() != "1"

def _local_dev_login():
    """Auto-create/resolve the local admin. Returns (user, session_id)."""
    email = "admin@gmail.com"
    user = _kv_get(f"auth:users:{email}")
    if not user:
        user = {
            "email": email,
            "first_name": "Admin",
            "last_name": "",
            "workplace": "",
            "city": "",
            "password_hash": _hash_password("admin@admin"),
            "created_at": datetime.utcnow().isoformat(),
            "features": {},
            "is_admin": True,
        }
        _kv_set(f"auth:users:{email}", user)
    sid = _session_id()
    _kv_set(f"auth:session:{sid}", {"email": email, "created_at": datetime.utcnow().isoformat()}, ttl=SESSION_MAX_AGE)
    return user, sid

# ---- Auth helpers ----
FEATURE_FLAGS = ["papers", "guidelines", "pearls", "trials", "trials_detail", "condensed_trials", "search", "bookmarks", "theory"]

DEFAULT_FEATURE_STATES = {
    "condensed_trials": False,
    "theory": False,
}

def _get_session_user(request):
    sid = request.cookies.get(SESSION_COOKIE_NAME)
    if not sid:
        if LOCAL_DEV_MODE:
            return _local_dev_login()[0]
        return None
    sess = _kv_get(f"auth:session:{sid}")
    if not sess:
        if LOCAL_DEV_MODE:
            return _local_dev_login()[0]
        return None
    return _kv_get(f"auth:users:{sess.get('email')}")

async def _require_user(request: Request, response: Response):
    user = _get_session_user(request)
    if not user:
        response.delete_cookie(SESSION_COOKIE_NAME)
        raise HTTPException(status_code=401, detail="Login required")
    return user

def _access_defaults():
    d = _kv_get("auth:access_defaults")
    if d is None:
        d = {}
        _kv_set("auth:access_defaults", d)
    return {f: d.get(f, DEFAULT_FEATURE_STATES.get(f, True)) for f in FEATURE_FLAGS}

def _user_has_feature(user, feature):
    if user.get("is_admin"):
        return True
    defaults = _access_defaults()
    overrides = user.get("features", {}) or {}
    return {**defaults, **overrides}.get(feature, False)


def _require_feature(user, feature):
    if not _user_has_feature(user, feature):
        raise HTTPException(status_code=403, detail=f"Feature '{feature}' is not enabled for this account")

# ---- Per-user data (bookmarks now; history/notes/prefs later) ----
BOOKMARKS_MAX_ITEMS = 500
BOOKMARKS_MAX_FOLDERS = 10
BOOKMARK_KINDS = ("paper", "guideline", "pearl", "trial", "condensed", "flashcard", "note")

def _user_data(email, key, default=None):
    data = _kv_get(f"user:{email}:{key}")
    if data is None or not isinstance(data, dict):
        return default if default is not None else {}
    return data

def _save_user_data(email, key, data):
    if not isinstance(data, dict):
        return False
    return _kv_set(f"user:{email}:{key}", data)

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
            "added_at": datetime.utcnow().isoformat(),
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

# ---- Landing page HTML ----
LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>hack.CCM — Critical Care Microlearning</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#1F1B14;color:#F1E4CE;font-family:system-ui,sans-serif;display:flex;min-height:100vh;align-items:center;justify-content:center}
.card{background:#29241B;border:1px solid #3A3226;border-radius:16px;padding:48px 40px;width:440px;max-width:94vw}
h1{font-size:28px;margin-bottom:4px;letter-spacing:-.02em}
.sub{color:#C4B18C;font-size:14px;margin-bottom:28px}
.tabs{display:flex;gap:0;margin-bottom:24px;border-bottom:1px solid #3A3226}
.tab{padding:10px 20px;cursor:pointer;color:#C4B18C;font-size:14px;border-bottom:2px solid transparent;transition:.15s}
.tab.active{color:#F1E4CE;border-bottom-color:#E8B778}
.form{display:block}.form.hidden{display:none}
.form input{width:100%;padding:10px 14px;background:#1F1B14;border:1px solid #3A3226;border-radius:8px;color:#F1E4CE;font-size:14px;margin-bottom:12px;outline:none;transition:.15s}
.form input:focus{border-color:#E8B778}
.form .row{display:flex;gap:10px}
.form .row input{flex:1}
.pw-wrap{display:flex;gap:6px;align-items:center;margin-bottom:12px}
.pw-wrap input{flex:1;margin-bottom:0}
.pw-wrap .toggle{width:auto;padding:10px 14px;background:none;border:1px solid #3A3226;border-radius:8px;color:#C4B18C;cursor:pointer;font-size:12px;white-space:nowrap;flex-shrink:0;transition:.15s}
.pw-wrap .toggle:hover{border-color:#E8B778;color:#F1E4CE}
button{width:100%;padding:11px;background:#E8B778;color:#1F1B14;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;transition:.15s}
button:hover{background:#d4a55e}
.error{color:#f55;font-size:13px;margin:8px 0;min-height:18px}
.success{color:#4ade80;font-size:13px;margin:8px 0}
.ecg{text-align:center;font-size:32px;margin-bottom:12px;opacity:.3;letter-spacing:4px}
.legal{text-align:center;margin-top:20px;font-size:12px;color:#8A7F6A}
.legal a{color:#8A7F6A;text-decoration:none;border-bottom:1px dotted #8A7F6A;cursor:pointer}
.legal a:hover{color:#C4B18C}
.overlay{display:none;position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.7);align-items:center;justify-content:center;padding:20px}
.overlay-content{background:#29241B;border:1px solid #3A3226;border-radius:16px;padding:32px;max-width:560px;width:100%;max-height:80vh;overflow-y:auto;color:#F1E4CE;font-size:14px;line-height:1.6}
.overlay-content h2{margin-bottom:16px;font-size:20px}
.overlay-content strong{color:#E8B778}
.overlay-close{float:right;background:none;border:none;color:#C4B18C;font-size:24px;cursor:pointer;line-height:1}
</style>
</head>
<body>
<div class="card">
<div class="ecg">_~^~_~^~_</div>
<h1>hack.CCM</h1>
<div class="sub">Critical Care Microlearning</div>
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
function switchTab(t){document.querySelectorAll('.tab').forEach(el=>el.classList.toggle('active',el.id==='tab'+t.charAt(0).toUpperCase()+t.slice(1)));document.getElementById('loginForm').classList.toggle('hidden',t!=='login');document.getElementById('signupForm').classList.toggle('hidden',t!=='signup')}
document.getElementById('pwToggle').onclick=function(){var p=document.getElementById('signupPassword');p.type=p.type==='password'?'text':'password';this.textContent=p.type==='password'?'Show':'Hide'}
document.getElementById('loginPwToggle').onclick=function(){var p=document.getElementById('loginPassword');p.type=p.type==='password'?'text':'password';this.textContent=p.type==='password'?'Show':'Hide'}
var discText='**Welcome to hack.CCM \\u{1F9A9} \\u2014 Please Read Before You Explore**\\n\\nWelcome! This platform is a hobby passion project designed to make critical care education more structured, accessible, and easily retainable.\\n\\n**\\u26A0\\uFE0F For Education, Not Consultation**\\nThis is a tool for knowledge enhancement and personal study only. It is not a clinical decision-making tool. Always rely on official guidelines and your own institutional protocols for real-world patient care.\\n\\n**\\u{1F916} The AI Factor**\\nAs the saying goes, \\"To err is human; to hallucinate is AI.\\" While we have taken immense care to review the data and eliminate errors, AI-assisted formatting isn\\'t always flawless.\\n\\n**\\u{1F6D1} Use Responsibly**\\nDouble-check critical values and protocols. You are the clinician; this is just your study buddy.\\n\\n**\\u{1F50D} Spotted a Discrepancy?**\\nIf you find any errors, outdated data, or weird AI quirks, please help us improve! Report it via our Feedback button below.';
function showLandingDisclaimer(){document.getElementById('landingDisclaimerText').innerHTML=discText.replace(/\\*\\*(.+?)\\*\\*/g,'<strong>$1</strong>').replace(/\\n\\n/g,'</p><p>').replace(/\\n/g,'<br>');document.getElementById('landingDisclaimerOverlay').style.display='flex'}
document.getElementById('landingDisclaimerLink').addEventListener('click',showLandingDisclaimer);
document.getElementById('landingDisclaimerClose').addEventListener('click',function(){document.getElementById('landingDisclaimerOverlay').style.display='none'});
document.getElementById('landingDisclaimerOverlay').addEventListener('click',function(e){if(e.target===this)this.style.display='none'});
document.getElementById('loginForm').onsubmit=async function(e){e.preventDefault();var b=this.querySelector('button');b.disabled=true;var err=document.getElementById('loginError');err.textContent='';try{var r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:document.getElementById('loginEmail').value,password:document.getElementById('loginPassword').value})});if(r.ok){window.location.reload();return}var d=await r.json();err.textContent=d.detail||'Invalid email or password'}catch(e){err.textContent='Network error'}b.disabled=false}
document.getElementById('signupForm').onsubmit=async function(e){e.preventDefault();var b=this.querySelector('button');b.disabled=true;var err=document.getElementById('signupError');var ok=document.getElementById('signupSuccess');err.textContent='';ok.textContent='';var pw=document.getElementById('signupPassword').value;try{var r=await fetch('/api/signup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:document.getElementById('signupEmail').value,password:pw,first_name:document.getElementById('signupFirstName').value,last_name:document.getElementById('signupLastName').value,workplace:document.getElementById('signupWorkplace').value,city:document.getElementById('signupCity').value})});if(r.ok){window.location.reload();return}var d=await r.json();err.textContent=d.detail||'Account creation failed'}catch(e){err.textContent='Network error'}b.disabled=false}
</script>
</body>
</html>"""

# ---- End auth ----

def load_approved_ledger():
    if not os.path.exists(JSON_TRACKER_FILE):
        return []
    try:
        with open(JSON_TRACKER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return []

def load_pearls():
    if not os.path.exists(PEARLS_JSON):
        return []
    try:
        with open(PEARLS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        expected = ["id", "timestamp", "source_paper", "doi", "author", "system", "type", "pearl", "remarks", "file_name", "topic"]
        for entry in data:
            for k in expected:
                if k not in entry:
                    entry[k] = ""
        # Backfill system from source summaries
        try:
            with open("sent_summaries.json", "r", encoding="utf-8") as f:
                summaries = json.load(f)
            summary_map = {}
            for s in summaries:
                fn = str(s.get("file_name", "")).strip()
                sys = str(s.get("system", "")).strip()
                if fn and sys:
                    summary_map[fn] = sys
            for p in data:
                fn = str(p.get("file_name", "")).strip()
                fn_pdf = fn[:-5] + ".pdf" if fn.endswith(".json") else fn
                cur = str(p.get("system", "")).strip()
                if fn_pdf in summary_map and not cur:
                    p["system"] = summary_map[fn_pdf]
        except Exception:
            pass
        return data
    except (json.JSONDecodeError, Exception):
        return []

def load_trial_index():
    if not os.path.exists(ESBICM_INDEX_PATH):
        return []
    try:
        with open(ESBICM_INDEX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return []

def load_flashcard_decks():
    """Load flashcard decks from the unified store (output_files/flashcards/).
    One deck per (system, subtopic) file; cards carry explicit front/back."""
    try:
        from acumen_core import flashcards as fc
    except Exception:
        return []
    decks = []
    try:
        idx = fc.load_flashcards_index()
    except Exception:
        return []
    for system in idx.get("systems", {}):
        for subtopic in idx["systems"][system]:
            data = fc.load_subtopic_file(system, subtopic)
            if not data or not data.get("cards"):
                continue
            cards = []
            for c in data["cards"]:
                if not isinstance(c, dict):
                    continue
                cards.append({
                    "id": str(c.get("id", "")),
                    "subtopic": str((c.get("data") or {}).get("original_subtopic") or c.get("subtopic", "")),
                    "front": str(c.get("front", "")),
                    "back": str(c.get("back", "")),
                    "status": str(c.get("status", "pending")),
                    "tags": sorted({str(t) for t in (c.get("tags") or []) if isinstance(t, str) and str(t).strip()}),
                })
            if cards:
                decks.append({
                    "id": f"{system}/{subtopic}",
                    "specialty": system,
                    "title": subtopic,
                    "cards": cards,
                    "subtopics": sorted({t for c in cards for t in c["tags"]}),
                })
    return decks


def load_theory_notes():
    """Load Theory Topics: every file under output_files/Theory MDs/ (any
    extension) rendered as markdown by the portal. Notes are organized into
    {Specialty}/{Subtopic}/ subfolders (see classify_theory.py); a sidecar
    theory_notes_meta.json provides clean titles + taxonomy overrides."""
    notes = []
    base = os.path.join(OUTPUT_DIR, "Theory MDs")
    if not os.path.isdir(base):
        return notes
    meta = {}
    meta_path = os.path.join(base, "theory_notes_meta.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {}
    for root, dirs, fnames in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        if root == base:
            fnames = [f for f in fnames if f != "theory_notes_meta.json"]
        for fn in sorted(fnames):
            path = os.path.join(root, fn)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    md_in = f.read()
            except Exception:
                continue
            rel = os.path.relpath(path, base)
            rel_slash = rel.replace(os.sep, "/")
            m_entry = meta.get(rel_slash) or {}
            # folder-derived taxonomy (ground truth = folder structure)
            parts = rel.split(os.sep)
            system = m_entry.get("system") or (parts[0] if len(parts) > 1 else "General")
            subtopic = m_entry.get("subtopic") or (parts[1] if len(parts) > 1 else "General")
            # title: manifest > first heading (any level, after any leading img) > cleaned filename
            title = m_entry.get("title") or ""
            if not title:
                body_head = md_in
                if body_head.startswith("<img") and "\n" in body_head:
                    body_head = body_head.split("\n", 1)[1]
                mm = re.search(r"^\s*#{1,6}\s+(.+?)\s*$", body_head, re.M)
                title = mm.group(1).strip() if mm else ""
            if not title:
                title = os.path.splitext(fn)[0].replace("_", " ")
            notes.append({
                "id": fn,
                "title": title,
                "md": md_in,
                "system": system,
                "subtopic": subtopic,
            })
    notes.sort(key=lambda n: (n.get("system") or "", n.get("subtopic") or "", n["title"].lower()))
    return notes

def load_condensed_trial_index():
    if not os.path.exists(CONDENSED_TRIALS_DIR):
        return []
    index = []
    for root, dirs, fnames in os.walk(CONDENSED_TRIALS_DIR):
        for fname in fnames:
            if not fname.endswith(".json"):
                continue
            rel = os.path.relpath(os.path.join(root, fname), CONDENSED_TRIALS_DIR)
            parts = rel.split(os.sep)
            system = parts[0] if len(parts) > 1 else "Other"
            name = os.path.splitext(fname)[0]
            entry = {"system": system, "name": name, "file_rel": rel}
            try:
                with open(os.path.join(root, fname), "r", encoding="utf-8") as f:
                    payload = json.load(f)
                entry["trial_name"] = payload.get("trial_name", "")
                entry["one_liner"] = payload.get("one_liner", "")
                entry["trial_type"] = payload.get("trial_type", "")
                entry["result_category"] = payload.get("result_category", "")
                entry["sample_size"] = payload.get("sample_size", "")
                y = payload.get("year", "")
                entry["year"] = int(y) if y and str(y).isdigit() else 0
                keywords = payload.get("keywords", [])
                entry["keywords_str"] = " ".join(keywords) if isinstance(keywords, list) else str(keywords)
            except Exception:
                pass
            index.append(entry)
    return sorted(index, key=lambda x: x["name"])

def load_condensed_trial(system, name):
    target = os.path.join(CONDENSED_TRIALS_DIR, system, f"{name}.json")
    if not os.path.exists(target):
        return None
    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)

# =====================================================================
# SVG — ECG motif (embedded)
# =====================================================================
ECG_SVG = '''<svg width="0" height="0" style="position:absolute">
  <symbol id="ecg" viewBox="0 0 260 14">
    <path d="M0 7 L95 7 L104 1 L112 13 L120 3 L128 7 L260 7"/>
  </symbol>
</svg>'''

# =====================================================================
# HOMEPAGE
# =====================================================================

SPEC_COLORS = {
    "Cardiology": "#C6554B", "Pulmonology": "#3A7CA5", "Infectious Diseases": "#4F8A6D",
    "Neurology": "#6B5B95", "Nephrology": "#B08D57", "Gastroenterology": "#10B981",
    "Hematology": "#E11D48", "Hepatology": "#14B8A6", "Immunology": "#A855F7",
    "Sepsis": "#F97316", "Trauma": "#DC2626", "Endocrinology": "#06B6D4",
    "General": "#6B7280", "Multisystem": "#6366F1",
    "Nutrition": "#84CC16", "Obstetrics and Gynecology": "#D946EF", "Rheumatology": "#0EA5E9",
    "Toxicology": "#7C3AED", "Oncology": "#059669", "Surgery": "#D97706",
    "Cardiothoracic": "#C6554B", "Vascular": "#0891B2", "Other": "#9333EA",
}

@app.get("/", response_class=HTMLResponse)
async def render_dashboard(request: Request, response: Response):
    user = _get_session_user(request)
    if not user:
        return HTMLResponse(content=LANDING_HTML)
    entries = load_approved_ledger()

    articles_list = []
    systems_set = set()
    types_set = set()
    if entries:
        for idx, entry in enumerate(entries):
            raw_doi = str(entry.get("doi", "")).strip()
            clean_doi_url = "#"
            if raw_doi and raw_doi.lower() not in ["none", "nan", ""]:
                if raw_doi.startswith("http://") or raw_doi.startswith("https://"):
                    clean_doi_url = raw_doi
                else:
                    clean_doi_url = f"https://doi.org/{raw_doi}"
            sys = str(entry.get("system", "General")).strip()
            typ = str(entry.get("type", "Other")).strip()
            systems_set.add(sys)
            types_set.add(typ)
            articles_list.append({
                "id": str(idx),
                "title": str(entry.get("title", "Unknown Title")),
                "authors": str(entry.get("authors", "Unknown Authors")),
                "system": sys,
                "journal": str(entry.get("journal", "Unknown Source")),
                "type": typ,
                "doi": clean_doi_url,
                "file_name": str(entry.get("file_name", "")),
                "date_added": str(entry.get("date_added", "")),
                "year": str(entry.get("year", "")),
                "subtopic": str(entry.get("subtopic", sys)).strip(),
            })

    pearls = load_pearls()
    pearl_systems = sorted(set(
        p["system"] for p in pearls if isinstance(p.get("system"), str) and p["system"].strip()
    ))
    pearl_types = sorted(set(
        p["type"] for p in pearls if isinstance(p.get("type"), str) and p["type"].strip()
    ))

    papers_only = [a for a in articles_list if a["type"].lower() != "guideline"]
    guidelines_only = [a for a in articles_list if a["type"].lower() == "guideline"]
    papers_count = len(papers_only)
    guidelines_count = len(guidelines_only)
    specialties_list = sorted(systems_set)
    pearl_count = len(pearls)

    trial_index = load_trial_index()
    trial_specialties = sorted(set(t["specialty"] for t in trial_index))
    condensed_index = load_condensed_trial_index()
    condensed_systems = sorted(set(c["system"] for c in condensed_index))
    trial_subtopic_map = {}
    for t in trial_index:
        sp = t["specialty"]
        st = t.get("subtopic", "General")
        if sp not in trial_subtopic_map:
            trial_subtopic_map[sp] = set()
        trial_subtopic_map[sp].add(st)
    trial_subtopic_map = {k: sorted(v) for k, v in trial_subtopic_map.items()}
    trial_spec_counts = {}
    for t in trial_index:
        sp = t["specialty"]
        trial_spec_counts[sp] = trial_spec_counts.get(sp, 0) + 1
    trial_result_cats = sorted(set(t["result_category"] for t in trial_index))
    trial_types_list = sorted(set(t["trial_type"] for t in trial_index))

    show_disclaimer = "true" if DISCLAIMER_TEXT.strip() else "false"

    # Build subtopic map per system (from data + approved subtopics)
    raw_subtopic_map = {}
    for entry in entries:
        sys = entry.get("system", "General").strip()
        st = entry.get("subtopic", sys).strip()
        if sys not in raw_subtopic_map:
            raw_subtopic_map[sys] = set()
        raw_subtopic_map[sys].add(st)
    subtopic_map = {k: sorted(v) for k, v in raw_subtopic_map.items()}

    # Build CSS variable mapping for specialties
    spec_css_vars = {}
    spec_css_vars_js = {}
    for s in systems_set:
        color = SPEC_COLORS.get(s, "#6B7280")
        var_name = "--spec-" + re.sub(r"[^a-zA-Z0-9]", "", s.lower())
        spec_css_vars[var_name] = color
        spec_css_vars_js[s] = var_name

    # Additional colors for specialties not in data but in color map
    for s, c in SPEC_COLORS.items():
        var_name = "--spec-" + re.sub(r"[^a-zA-Z0-9]", "", s.lower())
        if var_name not in spec_css_vars:
            spec_css_vars[var_name] = c
        if s not in spec_css_vars_js:
            spec_css_vars_js[s] = var_name

    spec_css_str = "; ".join(f"{k}:{v}" for k, v in spec_css_vars.items()) + ";"

    spec_labels_js = json.dumps(list(spec_css_vars_js.keys()))
    spec_vars_js = json.dumps(spec_css_vars_js)

    type_list_js = json.dumps(sorted(
        t for t in types_set if t and t.lower() not in ["none", "nan"]
    ))

    # Trial CSS vars
    trial_spec_css = {}
    for s in trial_specialties:
        color = ESBICM_SPEC_COLORS.get(s, "#6B7280")
        var_name = "--tspec-" + re.sub(r"[^a-zA-Z0-9]", "", s.lower())
        trial_spec_css[var_name] = color
    trial_spec_str = "; ".join(f"{k}:{v}" for k, v in trial_spec_css.items()) + ";"
    trial_spec_labels_js = json.dumps(list(trial_specialties))
    trial_spec_vars_js = json.dumps({s: "--tspec-" + re.sub(r"[^a-zA-Z0-9]", "", s.lower()) for s in trial_specialties})
    trial_spec_counts_js = json.dumps(trial_spec_counts)
    trial_subtopic_map_js = json.dumps(trial_subtopic_map)
    trial_result_cats_js = json.dumps(trial_result_cats)
    trial_types_list_js = json.dumps(trial_types_list)
    trial_index_js = json.dumps(trial_index)
    condensed_index_js = json.dumps(condensed_index)
    condensed_systems_js = json.dumps(condensed_systems)
    condensed_result_cats = sorted(set(t.get("result_category", "") for t in condensed_index if t.get("result_category")))
    condensed_types_list = sorted(set(t.get("trial_type", "") for t in condensed_index if t.get("trial_type")))
    condensed_result_cats_js = json.dumps(condensed_result_cats)
    condensed_types_list_js = json.dumps(condensed_types_list)

    # Theory flashcard decks (unified store) + Theory Topics (markdown notes)
    flashcard_decks = load_flashcard_decks() if _user_has_feature(user, "theory") else []
    theory_notes = load_theory_notes() if _user_has_feature(user, "theory") else []
    THEORY_SPEC_COLORS = {
        "Cardiology": "#C6554B", "Pulmonology": "#3A7CA5", "Neurology": "#6B5B95",
        "Nephrology": "#B08D57", "Gastroenterology": "#14B8A6",
        "Infectious Diseases": "#4F8A6D", "Hematology": "#E11D48",
        "Endocrinology": "#06B6D4", "Trauma": "#DC2626", "Surgery": "#6B7280",
        "Toxicology": "#7C3AED", "Sepsis": "#F97316", "General": "#9333EA",
        "Other": "#9333EA",
    }
    theory_specs = sorted(set(d["specialty"] for d in flashcard_decks))
    theory_spec_css = {}
    for s in theory_specs:
        color = THEORY_SPEC_COLORS.get(s, "#9333EA")
        var_name = "--theory-spec-" + re.sub(r"[^a-zA-Z0-9]", "", s.lower())
        theory_spec_css[var_name] = color
    theory_spec_str = "; ".join(f"{k}:{v}" for k, v in theory_spec_css.items()) + ";"
    theory_spec_vars_js = json.dumps({
        s: "--theory-spec-" + re.sub(r"[^a-zA-Z0-9]", "", s.lower()) for s in theory_specs
    })
    flashcard_decks_js = json.dumps(flashcard_decks)
    theory_notes_js = json.dumps(theory_notes)
    theory_total_cards = sum(len(d["cards"]) for d in flashcard_decks)
    theory_subtopic_map = {}
    for d in flashcard_decks:
        for t in d.get("subtopics") or []:
            theory_subtopic_map.setdefault(d["specialty"], set()).add(t)
    theory_subtopic_map = {s: sorted(v) for s, v in theory_subtopic_map.items()}
    theory_subtopic_map_js = json.dumps(theory_subtopic_map)

    # Compute resolved feature flags for the authenticated user
    user_features = {f: _user_has_feature(user, f) for f in FEATURE_FLAGS}
    user_features_js = json.dumps(user_features)
    user_is_admin_js = "true" if user.get("is_admin") else "false"
    insights_tag = '<script defer src="/_vercel/insights/script.js"></script>' if os.environ.get("VERCEL") else ''

    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dim">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>hack.CCM — Knowledge Portal</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Atkinson+Hyperlegible:wght@400;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
{insights_tag}
{ECG_SVG}
<style>
  :root{{
    --font-display:'Space Grotesk',sans-serif;
    --font-body:'Atkinson Hyperlegible',sans-serif;
    --font-mono:'JetBrains Mono',monospace;
    {spec_css_str}
    {trial_spec_str}
    {theory_spec_str}
    --radius:10px;
    --shadow:0 1px 2px rgba(0,0,0,.12), 0 4px 16px rgba(0,0,0,.08);
  }}
  html[data-theme="light"]{{ --bg:#F6F7F9; --bg-elev:#FFFFFF; --bg-sunk:#EEF0F3; --ink:#14213D; --ink-muted:#5B6472; --border:#E1E4E9; --accent:#0C8A8B; --accent-ink:#FFFFFF; --shadow:0 1px 2px rgba(20,33,61,.06),0 8px 24px rgba(20,33,61,.06); }}
  html[data-theme="dim"]{{ --bg:#1F1B14; --bg-elev:#29241B; --bg-sunk:#241F17; --ink:#F1E4CE; --ink-muted:#C4B18C; --border:#3A3226; --accent:#E8B778; --accent-ink:#1F1B14; }}
  html[data-theme="dark"]{{ --bg:#0B0E11; --bg-elev:#14181D; --bg-sunk:#101317; --ink:#E7E9EC; --ink-muted:#8A929C; --border:#232830; --accent:#2DD4CF; --accent-ink:#0B0E11; }}

  *{{box-sizing:border-box;}}
  html,body{{margin:0;padding:0;}}
  body{{ background:var(--bg); color:var(--ink); font-family:var(--font-body); font-size:var(--site-fs,16px); line-height:1.5; transition:background .25s ease, color .25s ease; padding-bottom:76px; }}
  h1,h2,h3,.display{{ font-family:var(--font-display); letter-spacing:-.01em; margin:0; }}
  .mono{{ font-family:var(--font-mono); }}
  a{{color:inherit;}}
  button{{font-family:inherit;}}
  :focus-visible{{ outline:2px solid var(--accent); outline-offset:2px; }}

  .ecg-line{{ display:block; width:100%; height:14px; overflow:visible; }}
  .ecg-line path{{ fill:none; stroke:var(--accent); stroke-width:1.5; stroke-linecap:round; stroke-linejoin:round; }}
  .ecg-sweep path{{ stroke-dasharray:260; stroke-dashoffset:260; animation:sweep 1.4s ease-out forwards; }}
  @keyframes sweep{{ to{{ stroke-dashoffset:0; }} }}
  @media (prefers-reduced-motion:reduce){{ .ecg-sweep path{{ animation:none; stroke-dashoffset:0; }} }}

  header{{ position:sticky; top:0; z-index:40; background:var(--bg-elev); border-bottom:1px solid var(--border); }}
  .header-row{{ max-width:1180px; margin:0 auto; padding:12px 16px 6px; display:flex; align-items:center; gap:14px; }}
  .icon-btn{{ background:transparent; border:1px solid transparent; color:var(--ink); width:38px; height:38px; border-radius:8px; cursor:pointer; display:flex; align-items:center; justify-content:center; font-size:18px; flex-shrink:0; }}
  .icon-btn:hover{{ background:var(--bg-sunk); }}
  .wordmark{{ font-weight:700; font-size:1.2rem; cursor:pointer; font-family:var(--font-display); }}
  .wordmark span{{ color:var(--accent); }}
  .top-nav{{ display:none; gap:2px; margin-left:8px; flex:1; overflow-x:auto; }}
  .top-nav button{{ text-decoration:none; font-size:.88rem; font-weight:600; color:var(--ink-muted); padding:9px 11px; border-radius:8px; white-space:nowrap; background:none; border:none; cursor:pointer; }}
  .top-nav button.active{{ color:var(--ink); background:var(--bg-sunk); }}
  .header-actions{{ display:flex; gap:6px; margin-left:auto; flex-shrink:0; }}
  @media (min-width:860px){{ .top-nav{{ display:flex; }} body{{ padding-bottom:0; }} }}

  main{{ max-width:1180px; margin:0 auto; padding:20px 16px 40px; }}
  .view{{ display:none; }}
  .view.active{{ display:block; }}
  .eyebrow{{ font-family:var(--font-mono); font-size:.7rem; letter-spacing:.12em; text-transform:uppercase; color:var(--accent); margin:0 0 6px; }}
  .section-head{{ display:flex; align-items:baseline; justify-content:space-between; margin:26px 0 10px; gap:10px; flex-wrap:wrap; }}
  .section-head h2{{ font-size:1rem; }}
  .section-head a, .section-head button.linklike{{ font-size:.82rem; color:var(--accent); text-decoration:none; font-weight:600; background:none; border:none; cursor:pointer; padding:0; }}

  .hero{{ display:grid; grid-template-columns:1fr; gap:14px; margin-bottom:20px; }}
  @media (min-width:720px){{ .hero{{ grid-template-columns:1fr 1fr; }} }}
  .card{{ background:var(--bg-elev); border:1px solid var(--border); border-radius:var(--radius); box-shadow:var(--shadow); overflow:hidden; }}
  .card-body{{ padding:16px; }}
  .stripe{{ height:4px; width:100%; }}
  .pill{{ display:inline-flex; align-items:center; gap:5px; font-size:.72rem; font-weight:700; padding:3px 9px; border-radius:99px; font-family:var(--font-mono); letter-spacing:.02em; }}
  .dot{{ width:6px; height:6px; border-radius:50%; flex-shrink:0; }}
  .hero .card, .card[data-view], .card[data-open-paper], .card[data-open-pearl]{{ cursor:pointer; }}
  .hero .card:hover, .card[data-view]:hover, .card[data-open-paper]:hover, .card[data-open-pearl]:hover{{ border-color:var(--accent); }}
  .hero .card h3{{ font-size:1.02rem; margin:10px 0 6px; }}
  .hero .card p{{ color:var(--ink-muted); font-size:.9rem; margin:0; }}

  .stats-strip{{ display:flex; gap:22px; flex-wrap:wrap; padding:14px 16px; background:var(--bg-elev); border:1px solid var(--border); border-radius:var(--radius); margin-bottom:8px; }}
  .stat-item{{ font-size:.82rem; color:var(--ink-muted); }}
  .stat-item b{{ color:var(--ink); font-size:1.05rem; font-family:var(--font-display); display:block; }}

  .spec-grid{{ display:grid; grid-template-columns:repeat(auto-fill,minmax(130px,1fr)); gap:10px; }}
  .spec-tile{{ border:1px solid var(--border); background:var(--bg-elev); border-radius:var(--radius); padding:14px 12px; cursor:pointer; text-align:left; width:100%; font:inherit; color:var(--ink); }}
  .spec-tile:hover{{ border-color:var(--tile-color, var(--accent)); }}
  .spec-tile .dot{{ width:10px; height:10px; margin-bottom:8px; }}
  .spec-tile .count{{ color:var(--ink-muted); font-size:.72rem; font-family:var(--font-mono); margin-top:2px; }}

  .subscribe-banner{{ display:flex; flex-wrap:wrap; align-items:center; gap:12px; justify-content:space-between; padding:18px; border-radius:var(--radius); background:var(--bg-sunk); border:1px dashed var(--border); margin:30px 0 10px; }}

  .toolbar{{ display:flex; align-items:center; gap:10px; margin-bottom:10px; flex-wrap:wrap; }}
  .btn{{ border:1px solid var(--border); background:var(--bg-elev); color:var(--ink); padding:8px 13px; border-radius:8px; font-size:.86rem; font-weight:600; cursor:pointer; }}
  .btn:hover{{ background:var(--bg-sunk); }}
  .btn.primary{{ background:var(--accent); color:var(--accent-ink); border-color:var(--accent); }}
  .search-box{{ flex:1; min-width:160px; display:flex; align-items:center; gap:8px; border:1px solid var(--border); background:var(--bg-elev); border-radius:8px; padding:2px 12px; color:var(--ink-muted); }}
  .search-box input{{ background:transparent; border:none; outline:none; color:var(--ink); font-family:inherit; font-size:.9rem; width:100%; padding:9px 2px; }}
  input::placeholder, .search-box input::placeholder{{ color:var(--ink-muted); opacity:.7; }}

  .content-grid{{ display:grid; grid-template-columns:1fr; gap:22px; }}
  @media (min-width:860px){{ .content-grid{{ grid-template-columns:220px 1fr; }} }}
  .filter-panel{{ display:none; }}
  @media (min-width:860px){{ .filter-panel{{ display:block; }} }}
  #filterToggleBtn{{ }}
  @media (min-width:860px){{ #filterToggleBtn{{ display:none; }} }}
  .filter-group{{ margin-bottom:16px; }}
  .filter-group h4, .sheet h4{{ font-size:.72rem; text-transform:uppercase; letter-spacing:.06em; color:var(--ink-muted); margin:0 0 8px; }}
  .filter-group label, .sheet label{{ display:flex; align-items:center; gap:8px; font-size:.87rem; padding:5px 0; color:var(--ink); cursor:pointer; }}
  .pearl-count{{ font-size:.78rem; color:var(--ink-muted); margin:6px 0 12px; }}

  .sheet-backdrop, .drawer-backdrop, .search-overlay-backdrop{{ position:fixed; inset:0; background:rgba(0,0,0,.45); opacity:0; pointer-events:none; transition:opacity .2s ease; }}
  .sheet-backdrop{{ z-index:60; }} .drawer-backdrop{{ z-index:90; }} .search-overlay-backdrop{{ z-index:80; }}
  .sheet{{ position:fixed; left:0; right:0; bottom:0; z-index:61; background:var(--bg-elev); border-radius:16px 16px 0 0; padding:16px 16px 24px; transform:translateY(100%); transition:transform .28s ease; max-height:75vh; overflow:auto; border-top:1px solid var(--border); }}
  body.sheet-open .sheet-backdrop{{ opacity:1; pointer-events:auto; }}
  body.sheet-open .sheet{{ transform:translateY(0); }}
  .sheet-handle{{ width:36px; height:4px; background:var(--border); border-radius:99px; margin:0 auto 10px; }}

  .coming-soon{{ text-align:center; padding:80px 20px; }}
  .coming-soon-icon{{ font-size:3rem; margin-bottom:10px; }}
  .coming-soon-text{{ color:var(--ink-muted); max-width:40ch; margin:8px auto; }}

  .doc-list{{ display:grid; grid-template-columns:1fr; gap:10px; }}
  .doc-card{{ display:flex; gap:0; background:var(--bg-elev); border:1px solid var(--border); border-radius:var(--radius); cursor:pointer; overflow:hidden; text-align:left; width:100%; padding:0; font:inherit; color:var(--ink); }}
  .doc-card:hover{{ border-color:var(--accent); }}
  .doc-stripe{{ width:4px; flex-shrink:0; }}
  .doc-inner{{ padding:13px 15px; flex:1; min-width:0; }}
  .doc-top{{ display:flex; gap:8px; align-items:center; margin-bottom:6px; flex-wrap:wrap; }}
  .doc-title{{ font-weight:700; font-size:.95rem; margin:0 0 4px; }}
  .doc-snippet{{ color:var(--ink-muted); font-size:.85rem; margin:0; }}
  .type-tag{{ font-size:.68rem; color:var(--ink-muted); font-family:var(--font-mono); }}
  .theory-sub-tag{{ font-size:.66rem; font-family:var(--font-mono); color:var(--accent); background:var(--bg-sunk); border:1px solid var(--border); border-radius:99px; padding:1px 7px; }}
  .chip-count{{ font-size:.66rem; opacity:.75; }}

  .divider{{ margin:34px 0 18px; }}
  .feature-grid{{ display:grid; grid-template-columns:1fr; gap:12px; }}
  @media (min-width:720px){{ .feature-grid{{ grid-template-columns:1fr 1fr 1fr; }} }}
  .feature-card{{ padding:16px; }}
  .feature-card h3{{ font-size:1rem; margin:8px 0 6px; }}
  .feature-card p{{ font-size:.85rem; color:var(--ink-muted); margin:0 0 10px; }}
  .mini-table{{ width:100%; border-collapse:collapse; font-family:var(--font-mono); font-size:.72rem; }}
  .mini-table td{{ padding:5px 4px; border-top:1px solid var(--border); color:var(--ink-muted); }}
  .mini-table td:first-child{{ color:var(--ink); font-weight:600; }}
  .badge{{ font-size:.68rem; font-family:var(--font-mono); padding:2px 7px; border-radius:99px; border:1px solid var(--border); color:var(--ink-muted); }}

  .pearl-toolbar{{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:10px; }}
  .chip{{ border:1px solid var(--border); background:var(--bg-elev); color:var(--ink); padding:6px 12px; border-radius:99px; font-size:.78rem; cursor:pointer; display:inline-flex; align-items:center; gap:6px; }}
  .chip.active{{ background:var(--chip-color,var(--accent)); color:var(--accent-ink); border-color:transparent; }}
  .chip .dot{{ width:7px; height:7px; }}
  .pearl-row{{ display:flex; gap:10px; align-items:flex-start; padding:11px 4px; border-bottom:1px solid var(--border); cursor:pointer; width:100%; background:none; border-left:none; border-right:none; border-top:none; text-align:left; font:inherit; color:var(--ink); }}
  .pearl-row:hover{{ background:var(--bg-sunk); }}
  .pearl-row .dot{{ margin-top:6px; }}
  .pearl-row .txt{{ flex:1; font-size:.88rem; }}
  .pearl-row .src{{ font-family:var(--font-mono); font-size:.66rem; color:var(--ink-muted); display:block; margin-top:3px; }}

  .search-overlay{{ position:fixed; top:8vh; left:50%; transform:translateX(-50%) translateY(-10px); width:min(600px,92vw); max-height:78vh; background:var(--bg-elev); border:1px solid var(--border); border-radius:14px; z-index:81; box-shadow:var(--shadow); opacity:0; pointer-events:none; transition:opacity .2s, transform .2s; overflow:hidden; display:flex; flex-direction:column; }}
  body.search-open .search-overlay-backdrop, body.search-open .search-overlay{{ opacity:1; pointer-events:auto; transform:translateX(-50%) translateY(0); }}
  .search-input-row{{ display:flex; align-items:center; gap:10px; padding:14px; border-bottom:1px solid var(--border); }}
  .search-input-row input{{ flex:1; border:none; background:transparent; outline:none; font-size:1rem; color:var(--ink); font-family:var(--font-body); }}
  .search-results{{ overflow:auto; padding:8px 6px; }}
  .search-group-label{{ font-family:var(--font-mono); font-size:.66rem; text-transform:uppercase; letter-spacing:.06em; color:var(--ink-muted); padding:10px 10px 4px; }}
  .search-result{{ display:block; width:100%; text-align:left; padding:9px 10px; border-radius:8px; border:none; background:transparent; color:var(--ink); cursor:pointer; font-size:.86rem; font:inherit; }}
  .search-result:hover{{ background:var(--bg-sunk); }}
  .search-empty{{ padding:26px; text-align:center; color:var(--ink-muted); font-size:.86rem; }}

  .drawer{{ position:fixed; top:0; bottom:0; left:0; width:min(300px,84vw); background:var(--bg-elev); z-index:91; transform:translateX(-100%); transition:transform .25s ease; border-right:1px solid var(--border); overflow:auto; padding:16px; }}
  body.drawer-open .drawer-backdrop{{ opacity:1; pointer-events:auto; }}
  body.drawer-open .drawer{{ transform:translateX(0); }}
  .drawer h4{{ font-size:.68rem; text-transform:uppercase; letter-spacing:.07em; color:var(--ink-muted); margin:18px 0 6px; }}
  .drawer-link{{ display:flex; align-items:center; gap:10px; width:100%; text-align:left; padding:9px 8px; border-radius:8px; border:none; background:transparent; color:var(--ink); font-size:.9rem; cursor:pointer; font:inherit; }}
  .drawer-link:hover{{ background:var(--bg-sunk); }}
  .drawer-link.active{{ background:var(--bg-sunk); color:var(--accent); font-weight:700; }}
  .chip-row{{ display:flex; gap:6px; flex-wrap:wrap; padding:2px 2px 4px; }}

  .toast{{ position:fixed; left:50%; bottom:100px; transform:translateX(-50%) translateY(20px); background:var(--ink); color:var(--bg); padding:10px 18px; border-radius:8px; font-size:.85rem; opacity:0; pointer-events:none; transition:.25s; z-index:100; max-width:80vw; text-align:center; }}
  .toast.show{{ opacity:1; transform:translateX(-50%) translateY(0); }}

  .reader-backdrop{{ position:fixed; inset:0; background:rgba(0,0,0,.45); z-index:70; opacity:0; pointer-events:none; transition:opacity .2s ease; }}
  .reader{{ position:fixed; top:0; right:0; bottom:0; width:100%; background:var(--bg-elev); z-index:71; transform:translateX(100%); transition:transform .3s ease; overflow:auto; border-left:1px solid var(--border); }}
  @media (min-width:860px){{ .reader{{ width:60vw; max-width:880px; min-width:480px; }} }}
  body.reader-open .reader-backdrop{{ opacity:1; pointer-events:auto; }}
  body.reader-open .reader{{ transform:translateX(0); }}
  .reader-head{{ position:sticky; top:0; z-index:5; background:var(--bg-elev); }}
  .reader-progress{{ height:3px; background:var(--accent); width:0%; transition:width .1s linear; }}
  .reader-top{{ display:flex; align-items:center; gap:8px; padding:10px 14px; border-bottom:1px solid var(--border); }}
  .size-chip-row{{ display:flex; gap:4px; }}
  .size-chip{{ border:1px solid var(--border); background:transparent; color:var(--ink); border-radius:6px; cursor:pointer; padding:5px 9px; font-family:var(--font-display); line-height:1; }}
  .size-chip.active{{ background:var(--accent); color:var(--accent-ink); border-color:var(--accent); }}
  .reader-body{{ padding:20px 20px 60px; max-width:720px; margin:0 auto; font-size:var(--reader-fs, var(--site-fs, 16px)); }}
  .reader-body h2{{ font-size:1.35em; margin-bottom:6px; }}
  .reader-body .meta{{ color:var(--ink-muted); font-size:.82em; margin-bottom:18px; }}
  .reader-body p{{ font-size:1em; }}
  .pearl-box{{ background:var(--bg-sunk); border-left:3px solid var(--accent); border-radius:6px; padding:12px 14px; font-size:.92em; margin:16px 0; }}
  .evidence-head{{ margin:22px 0 6px; font-size:.85em; text-transform:uppercase; letter-spacing:.05em; color:var(--ink-muted); }}
.evidence-row{{ font-size:.85em; padding:7px 0; border-bottom:1px dashed var(--border); }}
.evidence-statement{{ line-height:1.45; }}
.evidence-stat{{ font-family:var(--font-mono); color:var(--accent); font-size:.78em; margin-top:3px; }}

  /* reader extra: collapsible sections, print btn, loading */
  .reader-body .summary-section{{ margin-bottom:.5rem; border:1px solid var(--border); border-radius:8px; overflow:hidden; }}
  .reader-body .summary-heading{{ padding:.6rem .9rem; font-weight:700; font-size:.8rem; cursor:pointer; background:var(--bg-sunk); user-select:none; font-family:var(--font-display); }}
  .reader-body .summary-content{{ padding:.7rem 1rem; }}
  .reader-body .reader-loading{{ text-align:center; padding:40px; color:var(--ink-muted); }}
  .reader-body .reader-actions{{ display:flex; gap:6px; flex-wrap:wrap; margin:14px 0; }}

  .ai-fab{{ position:fixed; right:18px; bottom:88px; z-index:50; width:52px; height:52px; border-radius:50%; background:var(--accent); color:var(--accent-ink); border:none; box-shadow:var(--shadow); font-size:20px; cursor:pointer; }}
  @media (min-width:860px){{ .ai-fab{{ bottom:24px; }} }}
  .reader-nav{{ display:flex; gap:8px; margin-top:16px; flex-wrap:wrap; }}
  .nav-btn{{ flex:1; min-width:80px; text-align:center; font-size:.82rem; }}

  .ai-panel{{ position:fixed; right:16px; bottom:150px; z-index:51; width:min(320px, 90vw); background:var(--bg-elev); border:1px solid var(--border); border-radius:14px; box-shadow:var(--shadow); padding:14px; display:none; }}
  @media (min-width:860px){{ .ai-panel{{ bottom:86px; }} }}
  body.ai-open .ai-panel{{ display:block; }}
  .ai-msg{{ font-size:.85rem; margin-bottom:10px; padding:8px 10px; border-radius:8px; background:var(--bg-sunk); }}
  .ai-source{{ font-family:var(--font-mono); font-size:.68rem; color:var(--accent); margin-top:4px; display:block; }}

  .bottom-nav{{ position:fixed; left:0; right:0; bottom:0; z-index:41; background:var(--bg-elev); border-top:1px solid var(--border); display:flex; justify-content:space-around; padding:8px 4px 10px; }}
  @media (min-width:860px){{ .bottom-nav{{ display:none; }} }}
  .nav-item{{ background:none; border:none; color:var(--ink-muted); display:flex; flex-direction:column; align-items:center; gap:3px; font-size:.64rem; font-family:var(--font-mono); cursor:pointer; padding:2px 6px; }}
  .nav-item .glyph{{ font-size:19px; }}
  .nav-item.active{{ color:var(--accent); }}
  .nav-item .notch{{ width:16px; height:6px; opacity:0; }}
  .nav-item.active .notch{{ opacity:1; }}

  input[type=email], textarea{{ padding:10px 12px; border-radius:8px; border:1px solid var(--border); background:var(--bg-elev); color:var(--ink); font-family:inherit; }}
  select{{ font-family:inherit; }}

  /* disclaimer */
  .disclaimer-backdrop{{ position:fixed; inset:0; background:rgba(0,0,0,.55); z-index:90; display:flex; align-items:center; justify-content:center; padding:20px; }}
  .disclaimer-box{{ background:var(--bg-elev); border:1px solid var(--border); border-radius:14px; max-width:480px; width:100%; padding:24px; box-shadow:var(--shadow); max-height:80vh; overflow-y:auto; }}
  .disclaimer-box h2{{ font-size:1.1rem; margin-bottom:12px; }}
  .disclaimer-box p{{ font-size:.88rem; color:var(--ink-muted); line-height:1.6; margin-bottom:12px; white-space:pre-wrap; }}

  .content-grid, .doc-list{{ align-content:start; }}
  .doc-list > *{{ align-self:start; }}

  .spec-tile{{ border-left:3px solid var(--tile-color,var(--accent)); }}

  #scrollTopBtn{{
    position:fixed; right:18px; bottom:150px; z-index:49;
    width:40px; height:40px; border-radius:50%;
    background:var(--bg-elev); border:1px solid var(--border);
    color:var(--ink-muted); cursor:pointer; font-size:18px;
    opacity:0; pointer-events:none; transition:opacity .25s;
    display:flex; align-items:center; justify-content:center;
  }}
  #scrollTopBtn.visible{{ opacity:1; pointer-events:auto; }}
  #scrollTopBtn:hover{{ background:var(--bg-sunk); color:var(--ink); }}

  /* specialty collapsible panels */
  .spec-panel{{ border:1px solid var(--border); border-radius:var(--radius); margin-bottom:12px; overflow:hidden; }}
  .spec-panel-head{{
    display:flex; align-items:center; gap:10px; padding:12px 14px;
    cursor:pointer; background:var(--bg-elev); font-weight:700; font-size:.92rem; user-select:none;
  }}
  .spec-panel-head:hover{{ background:var(--bg-sunk); }}
  .spec-panel-head .toggle-icon{{ margin-left:auto; font-size:.8rem; color:var(--ink-muted); transition:transform .2s; }}
  .spec-panel.open .spec-panel-head .toggle-icon{{ transform:rotate(180deg); }}
  .spec-panel-body{{ display:none; padding:14px; border-top:1px solid var(--border); background:var(--bg); }}
  .spec-panel.open .spec-panel-body{{ display:block; }}
  .spec-panel .collapse-btn{{
    display:flex; align-items:center; justify-content:center; gap:4px;
    width:100%; padding:8px; border:none; background:transparent;
    color:var(--ink-muted); cursor:pointer; font-size:.78rem; font-family:var(--font-mono);
  }}
  .spec-panel .collapse-btn:hover{{ color:var(--ink); }}
  .spec-view-head{{ display:flex; align-items:center; gap:12px; margin-bottom:16px; }}
  .spec-view-head .dot{{ width:14px; height:14px; }}
  .spec-view-head h2{{ font-size:1.1rem; }}
  .subtopic-chip-row{{ display:flex; gap:6px; flex-wrap:wrap; padding:0 0 12px; margin-bottom:8px; border-bottom:1px solid var(--border); }}
  .subtopic-chip{{ border:1px solid var(--border); background:var(--bg-elev); color:var(--ink-muted); padding:4px 11px; border-radius:99px; font-size:.72rem; cursor:pointer; font-family:var(--font-mono); white-space:nowrap; transition:all .15s; }}
  .subtopic-chip:hover{{ border-color:var(--accent); color:var(--ink); }}
  .subtopic-chip.active{{ background:var(--accent); color:var(--accent-ink); border-color:var(--accent); }}
  .subtopic-chip-clear{{ border:1px solid var(--border); background:transparent; color:var(--ink-muted); padding:4px 11px; border-radius:99px; font-size:.72rem; cursor:pointer; font-family:var(--font-mono); }}
  .subtopic-chip-clear:hover{{ border-color:var(--accent); color:var(--ink); }}

  ::-webkit-scrollbar{{ width:5px; }}
  ::-webkit-scrollbar-track{{ background:transparent; }}
  ::-webkit-scrollbar-thumb{{ background:var(--border); border-radius:3px; }}

  /* ===== TRIALS ===== */
  .trials-hero-card{{ display:block; background:var(--bg-elev); border:1px solid var(--border); border-radius:var(--radius); padding:24px; cursor:pointer; text-align:center; transition:border-color .2s; }}
  .trials-hero-card:hover{{ border-color:var(--accent); }}
  .trials-hero-card .trophy{{ font-size:2.4rem; display:block; margin-bottom:8px; }}
  .trials-hero-card h3{{ font-size:1.1rem; margin:6px 0; }}
  .trials-hero-card .sub{{ color:var(--ink-muted); font-size:.82rem; }}
  .trials-hero-condensed{{ border-color:var(--accent); border-style:dashed; }}
  .trials-hero-condensed:hover{{ border-color:var(--accent); background:color-mix(in srgb, var(--accent) 6%, transparent); }}

  .trials-filter-bar{{ display:flex; gap:8px; flex-wrap:wrap; align-items:flex-end; margin-bottom:18px; padding:14px; background:var(--bg-sunk); border-radius:var(--radius); border:1px solid var(--border); }}
  .trials-filter-group{{ display:flex; flex-direction:column; gap:4px; min-width:150px; flex:1; }}
  .trials-filter-group label{{ font-size:.7rem; font-family:var(--font-mono); text-transform:uppercase; letter-spacing:.06em; color:var(--ink-muted); }}
  .trials-filter-group select{{ padding:7px 8px; border-radius:6px; border:1px solid var(--border); background:var(--bg-elev); color:var(--ink); font-size:.85rem; }}
  .trials-filter-actions{{ display:flex; gap:6px; align-items:flex-end; padding-bottom:2px; }}

  .trials-spec-grid{{ display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:10px; }}
  .trials-spec-tile{{ border:1px solid var(--border); background:var(--bg-elev); border-radius:var(--radius); padding:14px 12px; cursor:pointer; text-align:left; width:100%; font:inherit; color:var(--ink); border-left:3px solid var(--tile-color,var(--accent)); transition:border-color .2s; }}
  .trials-spec-tile:hover{{ border-color:var(--tile-color,var(--accent)); }}
  .trials-spec-tile .dot{{ width:10px; height:10px; margin-bottom:8px; }}
  .trials-spec-tile .count{{ color:var(--ink-muted); font-size:.72rem; font-family:var(--font-mono); margin-top:2px; }}

  .trial-card{{ border:1px solid var(--border); border-radius:var(--radius); background:var(--bg-elev); padding:14px 16px; cursor:pointer; transition:border-color .2s; margin-bottom:8px; }}
  .trial-card:hover{{ border-color:var(--accent); }}
  .trial-card h4{{ font-size:.95rem; margin:0 0 4px; }}
  .trial-card .one-liner{{ color:var(--ink-muted); font-size:.84rem; margin:0 0 8px; }}
  .trial-card .meta-row{{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; font-size:.75rem; }}

  .trial-result-negneu{{ color:#A855F7; border-color:#A855F7; }}
  .trial-result-positive{{ color:#10B981; border-color:#10B981; }}
  .trial-result-negative{{ color:#EF4444; border-color:#EF4444; }}
  .trial-result-neutral{{ color:#6B7280; border-color:#6B7280; }}

  .trials-back-header{{ display:flex; align-items:center; gap:10px; margin-bottom:16px; flex-wrap:wrap; }}
  .trials-back-header h2{{ font-size:1.1rem; flex:1; }}
  .trials-back-btn{{ background:none; border:none; color:var(--accent); cursor:pointer; font-size:.88rem; font-weight:600; padding:6px 10px; border-radius:6px; }}
  .trials-back-btn:hover{{ background:var(--bg-sunk); }}

  /* Trial detail page */
  .trial-detail{{ max-width:800px; margin:0 auto; }}
  .trial-credits-bar{{ display:flex; align-items:center; gap:8px; padding:10px 14px; background:var(--bg-sunk); border:1px solid var(--border); border-radius:8px; margin-bottom:18px; font-size:.82rem; color:var(--ink-muted); flex-wrap:wrap; }}
  .trial-credits-bar .trophy{{ font-size:1.1rem; }}
  .trial-credits-bar .spacer{{ flex:1; }}
  .icon-btn-sm{{ background:none; border:1px solid var(--border); border-radius:6px; cursor:pointer; padding:4px 8px; font-size:.78rem; color:var(--ink-muted); display:inline-flex; align-items:center; gap:4px; font-family:inherit; }}
  .icon-btn-sm:hover{{ background:var(--bg-elev); color:var(--ink); }}

  .trial-detail h1{{ font-size:1.3rem; margin-bottom:4px; }}
  .trial-journal{{ color:var(--ink-muted); font-size:.85rem; margin-bottom:12px; }}
  .trial-meta-strip{{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:14px; }}
  .trial-meta-strip .badge{{ font-size:.75rem; padding:3px 10px; }}
  .trial-one-liner{{ font-style:italic; color:var(--ink-muted); border-left:3px solid var(--accent); padding:10px 14px; margin:0 0 20px; background:var(--bg-sunk); border-radius:0 8px 8px 0; }}

  .trial-nav-bar{{ display:flex; gap:8px; margin:20px 0; }}
  .trial-nav-bar .nav-btn{{ flex:1; }}

  .trial-section{{ margin-bottom:.6rem; border:1px solid var(--border); border-radius:8px; overflow:hidden; }}
  .trial-section summary{{ padding:.7rem 1rem; font-weight:700; font-size:.85rem; cursor:pointer; background:var(--bg-sunk); user-select:none; font-family:var(--font-display); }}
  .trial-section .section-body{{ padding:.7rem 1rem; }}
  .trial-section .section-body p{{ margin:.4em 0; }}
  .trial-section .section-body ul{{ padding-left:1.2em; }}
  .trial-section .section-body li{{ margin:.2em 0; }}
  .pico-table{{ width:100%; border-collapse:collapse; font-size:.85rem; }}
  .pico-table th{{ text-align:left; width:120px; padding:6px 10px; color:var(--ink-muted); vertical-align:top; }}
  .pico-table td{{ padding:6px 10px; }}
  .outcomes-table{{ width:100%; border-collapse:collapse; font-size:.78rem; }}
  .outcomes-table th, .outcomes-table td{{ border:1px solid var(--border); padding:5px 8px; text-align:left; }}
  .outcomes-table th{{ background:var(--bg-sunk); font-weight:700; white-space:nowrap; }}
  .outcomes-table tr:hover{{ background:var(--bg-sunk); }}
  .quick-recall-box{{ background:color-mix(in srgb, var(--accent) 8%, transparent); border:1px solid var(--accent); border-radius:8px; padding:14px 16px; margin:0 0 16px; }}
  .quick-recall-box .qr-title{{ font-weight:700; font-size:.85rem; margin-bottom:8px; font-family:var(--font-display); }}
  .quick-recall-box .qr-numbers{{ display:flex; flex-wrap:wrap; gap:6px; margin-bottom:8px; }}
  .quick-recall-box .qr-num{{ background:var(--bg-elev); border:1px solid var(--border); border-radius:6px; padding:4px 10px; font-family:var(--font-mono); font-size:.78rem; }}
  .quick-recall-box .qr-takeaway{{ font-style:italic; font-size:.85rem; color:var(--ink-muted); }}

  /* Trial overlays */
  .trial-overlay-backdrop{{ position:fixed; inset:0; background:rgba(0,0,0,.55); z-index:90; display:flex; align-items:center; justify-content:center; padding:20px; }}
  .trial-overlay-box{{ background:var(--bg-elev); border:1px solid var(--border); border-radius:14px; max-width:520px; width:100%; padding:24px; box-shadow:var(--shadow); max-height:80vh; overflow-y:auto; }}
  .trial-overlay-box h2{{ font-size:1.1rem; margin-bottom:12px; }}
  .trial-overlay-box p{{ font-size:.88rem; color:var(--ink-muted); line-height:1.6; margin-bottom:12px; white-space:pre-wrap; }}
  .trial-overlay-box .btn{{ margin-top:8px; }}

  .result-badge{{ font-size:.68rem; font-family:var(--font-mono); padding:2px 7px; border-radius:99px; border:1px solid; }}
  .result-badge.pos{{ color:#10B981; border-color:#10B981; background:rgba(16,185,129,.1); }}
  .result-badge.neg{{ color:#EF4444; border-color:#EF4444; background:rgba(239,68,68,.1); }}
  .result-badge.neu{{ color:#A855F7; border-color:#A855F7; background:rgba(168,85,247,.1); }}
  .result-badge.negneu{{ color:#D97706; border-color:#D97706; background:rgba(217,119,6,.1); }}

  .trial-empty{{ text-align:center; padding:60px 20px; color:var(--ink-muted); }}
  .trial-empty .icon{{ font-size:2.5rem; display:block; margin-bottom:8px; }}

  /* ===== BOOKMARKS ===== */
  .bookmark-btn{{ cursor:pointer; transition:transform .15s; }}
  .bookmark-btn:hover{{ transform:scale(1.1); }}
  .bookmark-btn.active{{ color:var(--accent); border-color:var(--accent); }}
  .bookmark-btn.active::after{{ content:''; position:absolute; top:-2px; right:-2px; width:8px; height:8px; border-radius:50%; background:var(--accent); }}
  .bm-count{{ display:inline-flex; align-items:center; justify-content:center; min-width:18px; height:18px; padding:0 5px; margin-left:5px; border-radius:99px; background:var(--accent); color:var(--accent-ink); font-size:.66rem; font-family:var(--font-mono); font-weight:700; vertical-align:middle; }}
  .bm-count.zero{{ display:none; }}
  .bookmarks-folder-row{{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px; }}
  .bookmarks-folder-pill{{ display:inline-flex; align-items:center; gap:6px; border:1px solid var(--border); background:var(--bg-elev); color:var(--ink); padding:5px 12px; border-radius:99px; font-size:.76rem; cursor:pointer; font-family:var(--font-mono); }}
  .bookmarks-folder-pill.active{{ border-color:var(--accent); color:var(--accent); }}
  .bookmarks-folder-pill .fdot{{ width:8px; height:8px; border-radius:50%; }}
  .bm-section-head{{ display:flex; align-items:center; gap:8px; margin:20px 0 8px; font-family:var(--font-display); font-size:.9rem; }}
  .bm-section-head .bar{{ flex:1; height:1px; background:var(--border); }}
  .bm-card{{ display:flex; flex-direction:column; gap:8px; background:var(--bg-elev); border:1px solid var(--border); border-radius:var(--radius); padding:12px 14px; margin-bottom:8px; transition:border-color .15s; }}
  .bm-card:hover{{ border-color:var(--accent); }}
  .bm-card-top{{ display:flex; gap:10px; align-items:flex-start; cursor:pointer; text-align:left; background:none; border:none; padding:0; font:inherit; color:inherit; width:100%; }}
  .bm-card-top .bm-title{{ font-weight:700; font-size:.9rem; line-height:1.35; }}
  .bm-card-top .bm-meta{{ color:var(--ink-muted); font-size:.76rem; margin-top:3px; }}
  .bm-card-actions{{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; }}
  .bm-card-actions select{{ padding:4px 6px; border-radius:6px; border:1px solid var(--border); background:var(--bg-elev); color:var(--ink); font-size:.75rem; max-width:160px; }}
  .bm-tags-input{{ flex:1; min-width:140px; padding:5px 9px; border-radius:6px; border:1px solid var(--border); background:var(--bg-elev); color:var(--ink); font-size:.75rem; }}
  .bm-tag{{ display:inline-flex; align-items:center; gap:4px; border:1px solid var(--border); border-radius:99px; padding:2px 8px; font-size:.68rem; font-family:var(--font-mono); color:var(--ink-muted); }}
  .bm-del{{ background:none; border:none; color:var(--ink-muted); cursor:pointer; font-size:.95rem; padding:0 4px; }}
  .bm-del:hover{{ color:#EF4444; }}
  .bm-empty{{ text-align:center; padding:60px 20px; color:var(--ink-muted); }}
  .bm-empty .icon{{ font-size:2.5rem; display:block; margin-bottom:8px; }}
  .bm-new-folder{{ display:none; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:12px; padding:12px; background:var(--bg-sunk); border:1px dashed var(--border); border-radius:var(--radius); }}
  .bm-new-folder.show{{ display:flex; }}
  .bm-new-folder input{{ padding:6px 10px; border-radius:6px; border:1px solid var(--border); background:var(--bg-elev); color:var(--ink); font-size:.82rem; min-width:160px; }}
  .folder-swatch{{ width:22px; height:22px; border-radius:50%; cursor:pointer; border:2px solid transparent; flex-shrink:0; }}
  .folder-swatch.active{{ border-color:var(--ink); }}
  .bm-folder-edit{{ background:none; border:none; color:var(--ink-muted); cursor:pointer; font-size:.78rem; padding:0 3px; font-family:var(--font-mono); }}
  .bm-folder-edit:hover{{ color:var(--ink); }}
  .bm-folder-edit.del:hover{{ color:#EF4444; }}

  /* ===== THEORY FLASHCARDS ===== */
  .theory-stage{{ margin:14px 0; }}
  .theory-card-wrap{{ perspective:1400px; margin:12px 0 14px; }}
  .theory-card-inner{{ position:relative; width:100%; min-height:340px; transform-style:preserve-3d; transition:transform .45s ease; }}
  .theory-card-inner.flip{{ cursor:pointer; }}
  .theory-card-inner.flipped{{ transform:rotateY(180deg); }}
  .theory-face{{ position:absolute; top:0; left:0; right:0; bottom:0; backface-visibility:hidden; -webkit-backface-visibility:hidden; background:var(--bg-elev); border:1px solid var(--border); border-radius:14px; box-shadow:var(--shadow); padding:22px 24px; overflow:auto; max-height:72vh; }}
  .theory-face.back{{ transform:rotateY(180deg); }}
  .theory-face .flip-hint{{ position:absolute; bottom:10px; right:16px; font-size:.68rem; font-family:var(--font-mono); color:var(--ink-muted); }}
  /* Fallback when the browser lacks backface-visibility 3D support: swap display instead of rotating */
  .theory-card-wrap.no-3d{{ perspective:none; }}
  .theory-card-wrap.no-3d .theory-card-inner{{ transform-style:flat; transform:none !important; }}
  .theory-card-wrap.no-3d .theory-face{{ position:relative; top:auto; left:auto; right:auto; bottom:auto; transform:none !important; display:none; }}
  .theory-card-wrap.no-3d .theory-face.front{{ display:block; }}
  .theory-card-wrap.no-3d .theory-card-inner.flipped .theory-face.front{{ display:none; }}
  .theory-card-wrap.no-3d .theory-card-inner.flipped .theory-face.back{{ display:block; }}
  .theory-card-flat{{ background:var(--bg-elev); border:1px solid var(--border); border-radius:14px; box-shadow:var(--shadow); padding:22px 24px; max-height:72vh; overflow:auto; }}
  .theory-card-question{{ margin:0 0 14px; font-size:1.06rem; font-weight:650; line-height:1.45; color:var(--ink); background:var(--bg-sunk); border:1px solid var(--border); border-left:3px solid var(--accent); border-radius:10px; padding:10px 14px; }}
  .theory-card-question p{{ margin:0; }}
  .theory-card-content{{ font-size:var(--theory-card-fs, .94rem); line-height:1.55; }}
  .theory-card-content h1, .theory-card-content h2, .theory-card-content h3{{ font-size:1.02rem; margin:12px 0 6px; }}
  .theory-card-content p{{ margin:8px 0; }}
  .theory-card-content ul, .theory-card-content ol{{ margin:8px 0; padding-left:22px; }}
  .theory-card-content table{{ border-collapse:collapse; width:100%; font-size:.85em; margin:12px 0; }}
  .theory-card-content th, .theory-card-content td{{ border:1px solid var(--border); padding:7px 10px; text-align:left; vertical-align:top; }}
  .theory-card-content th{{ background:var(--bg-sunk); font-weight:700; }}
  .theory-card-content code{{ font-family:var(--font-mono); font-size:.86em; background:var(--bg-sunk); border-radius:4px; padding:1px 5px; }}
  .theory-card-head{{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:6px; }}
  .theory-card-progress{{ font-family:var(--font-mono); font-size:.76rem; color:var(--ink-muted); margin-left:auto; }}
  .theory-mode-chip{{ border:1px solid var(--border); background:transparent; color:var(--ink-muted); padding:5px 12px; border-radius:99px; font-size:.74rem; cursor:pointer; }}
  .theory-mode-chip.active{{ background:var(--accent); color:var(--accent-ink); border-color:var(--accent); }}
  .theory-dots{{ display:flex; gap:6px; flex-wrap:wrap; justify-content:center; margin-top:12px; }}
  .theory-dot{{ width:9px; height:9px; border-radius:50%; border:1px solid var(--border); background:transparent; cursor:pointer; padding:0; }}
  .theory-dot.active{{ background:var(--accent); border-color:var(--accent); }}
  .theory-dot.saved{{ background:var(--ink-muted); border-color:var(--ink-muted); }}
  .theory-dot.saved.active{{ background:var(--accent); border-color:var(--accent); }}
  .theory-dot.muted{{ opacity:.28; cursor:not-allowed; }}
  .theory-card-tags{{ display:flex; align-items:center; gap:6px; flex-wrap:wrap; margin:4px 0 2px; min-height:26px; }}
  .theory-tag-pill{{ font-size:.68rem; font-family:var(--font-mono); color:var(--ink-muted); border:1px dashed var(--border); border-radius:99px; padding:2px 9px; }}
  .theory-tag-pill.hot{{ color:var(--accent); border-color:color-mix(in srgb, var(--accent) 45%, transparent); }}
  .theory-tag-x{{ cursor:pointer; margin-left:4px; color:var(--ink-muted); }}
  .theory-tag-x:hover{{ color:var(--accent); }}
  .theory-deck-rows .doc-card{{ cursor:pointer; }}
  .theory-saved-badge{{ font-size:.66rem; font-family:var(--font-mono); color:var(--accent); margin-left:6px; }}

  /* ===== THEORY TOPICS (markdown notes) ===== */
  .theory-note{{ font-size:var(--theory-note-fs, var(--site-fs, 16px)); line-height:1.6; color:var(--ink); }}
  .theory-note h1{{ font-size:1.5rem; margin:20px 0 10px; }}
  .theory-note h2{{ font-size:1.3rem; margin:18px 0 8px; }}
  .theory-note h3{{ font-size:1.12rem; margin:16px 0 8px; }}
  .theory-note h4{{ font-size:1rem; margin:14px 0 6px; }}
  .theory-note p{{ margin:10px 0; }}
  .theory-note ul, .theory-note ol{{ margin:10px 0; padding-left:24px; }}
  .theory-note li{{ margin:4px 0; }}
  .theory-note code{{ font-family:var(--font-mono); font-size:.9em; background:var(--bg-sunk); border-radius:4px; padding:1px 5px; }}
  .theory-note pre{{ background:var(--bg-sunk); border:1px solid var(--border); border-radius:10px; padding:12px 14px; overflow:auto; }}
  .theory-note pre code{{ background:none; padding:0; }}
  .theory-note blockquote{{ border-left:3px solid var(--accent); margin:12px 0; padding:4px 14px; color:var(--ink-muted); }}
  .theory-note table{{ border-collapse:collapse; width:100%; font-size:.92em; margin:14px 0; }}
  .theory-note th, .theory-note td{{ border:1px solid var(--border); padding:7px 10px; text-align:left; vertical-align:top; }}
  .theory-note th{{ background:var(--bg-sunk); font-weight:700; }}
  .theory-table-wrap{{ position:relative; max-width:100%; overflow-x:auto; overflow-y:hidden; margin:14px 0; border:1px solid var(--border); border-radius:10px; background:var(--bg); -webkit-overflow-scrolling:touch; scrollbar-width:thin; }}
  .theory-table-wrap table{{ width:100%; margin:0; }}
  .theory-table-wrap th, .theory-table-wrap td{{ white-space:nowrap; }}
  .theory-table-wrap::-webkit-scrollbar{{ height:8px; }}
  .theory-table-wrap::-webkit-scrollbar-thumb{{ background:var(--border); border-radius:8px; }}
  @media (hover:none){{
    .theory-table-wrap{{ scrollbar-width:none; }}
    .theory-table-wrap::-webkit-scrollbar{{ display:none; }}
  }}
  .theory-table-expand{{ display:inline-flex; align-items:center; gap:6px; margin:14px 0 0; padding:6px 14px; background:var(--bg-sunk); color:var(--ink); border:1px solid var(--border); border-radius:99px; font:inherit; font-size:.78rem; cursor:pointer; }}
  .theory-table-expand:hover{{ border-color:var(--accent); color:var(--accent); }}
  .theory-table-expand .tt-expand-icon{{ color:var(--accent); }}
  /* Fullscreen table viewer */
  .theory-table-overlay{{ position:fixed; inset:0; z-index:9999; background:var(--bg); display:flex; flex-direction:column; }}
  .theory-table-overlay-bar{{ display:flex; align-items:center; gap:10px; padding:10px 14px; background:var(--bg-elev); border-bottom:1px solid var(--border); flex:0 0 auto; }}
  .theory-table-overlay-title{{ flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:.85rem; color:var(--ink-muted); }}
  .theory-table-overlay-scroll{{ flex:1; overflow:auto; padding:14px; -webkit-overflow-scrolling:touch; }}
  .theory-table-overlay-scroll table{{ border-collapse:collapse; width:auto; font-size:.92em; background:var(--bg); }}
  .theory-table-overlay-scroll th, .theory-table-overlay-scroll td{{ border:1px solid var(--border); padding:7px 10px; text-align:left; vertical-align:top; white-space:nowrap; }}
  .theory-table-overlay-scroll th{{ background:var(--bg-sunk); font-weight:700; position:sticky; top:0; }}
  .theory-table-fit-inner{{ display:inline-block; max-width:100%; }}
  .theory-note hr{{ border:none; border-top:1px solid var(--border); margin:18px 0; }}
  .theory-note a{{ color:var(--accent); }}
  /* Flip-mode front question: big + centered (H2-scale) */
  .theory-front-big{{ display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; min-height:100%; font-size:1.5rem; font-weight:600; line-height:1.4; gap:14px; }}
  .theory-front-big p{{ margin:0; }}
  .theory-front-big h1, .theory-front-big h2, .theory-front-big h3{{ font-size:1.6rem; margin:0; }}
  /* Per-deck card list header */
  .theory-card-list-head{{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:6px; }}
  .theory-list-toggle{{ display:inline-flex; align-items:center; gap:8px; background:var(--bg-elev); border:1px solid var(--border); border-radius:99px; padding:6px 14px; cursor:pointer; font:inherit; font-size:.8rem; color:var(--ink); margin-left:auto; }}
  .theory-list-toggle:hover{{ background:var(--bg-sunk); border-color:var(--accent); }}
  .theory-list-toggle .theory-toggle-caret{{ color:var(--accent); font-size:.72rem; }}
  /* Breadcrumb navigation */
  .theory-crumbs{{ display:flex; align-items:center; gap:4px; flex-wrap:wrap; margin:0 0 12px; padding:8px 12px; background:var(--bg-sunk); border:1px solid var(--border); border-radius:var(--radius); font-size:.8rem; }}
  .crumb{{ background:none; border:none; color:var(--ink-muted); font:inherit; font-size:.8rem; cursor:pointer; padding:2px 6px; border-radius:6px; }}
  .crumb:hover{{ color:var(--accent); background:var(--bg-elev); }}
  .crumb-current{{ color:var(--ink); cursor:default; }}
  .crumb-current:hover{{ color:var(--ink); background:none; }}
  .crumb-title{{ max-width:240px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
  .crumb-sep{{ color:var(--ink-muted); opacity:.5; }}
  .btn.nav-btn:disabled{{ opacity:.35; cursor:not-allowed; }}
  .theory-card-head .pill, .theory-card-list-head .pill, .theory-study-head .pill{{ max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}

</style>
</head>
<body>

<svg width="0" height="0" style="position:absolute">
  <symbol id="ecg" viewBox="0 0 260 14"><path d="M0 7 L95 7 L104 1 L112 13 L120 3 L128 7 L260 7"/></symbol>
</svg>

<header>
  <div class="header-row">
    <button class="icon-btn" id="hamburgerBtn" aria-label="Open menu">&#9776;</button>
    <div class="wordmark" id="logo" role="button" tabindex="0" aria-label="Go to homepage">hack<span>.CCM</span></div>
    <nav class="top-nav" aria-label="Primary">
      <button data-view="home" class="active">Home</button>
      <button data-view="papers">Papers</button>
      <button data-view="guidelines">Guidelines</button>
      <button data-view="pearls">Pearls</button>
      <button data-view="trials">Trials</button>
      <button data-view="antibiotics">Antibiotics</button>
      <button data-view="theory">Theory</button>
      <button data-view="rrt">RRT</button>
      <button data-view="ai">AI Assistant</button>
      <button data-view="bookmarks">&#128278; Bookmarks<span class="bm-count zero" id="bookmarksTopCount">0</span></button>
    </nav>
    <div class="header-actions">
      <button class="icon-btn" id="searchTrigger" aria-label="Search">&#128269;</button>
      <button class="icon-btn theme-btn" id="themeBtn" aria-label="Change theme">&#9712;</button>
      <button class="icon-btn" id="headerLogout" aria-label="Sign out">&#128682;</button>
    </div>
  </div>
  <svg class="ecg-line ecg-sweep" viewBox="0 0 260 14" preserveAspectRatio="none"><use href="#ecg"/></svg>
</header>

<main>

  <!-- HOME -->
  <section class="view active" id="view-home">
    <p class="eyebrow">Today on the unit</p>
    <div class="hero" id="homeHero"></div>
    <div class="stats-strip" id="homeStats"></div>

    <div class="section-head"><h2>Browse by specialty</h2></div>
    <div class="spec-grid" id="homeSpecGrid"></div>

    <div class="section-head"><h2>Recently added</h2><button class="linklike" data-view="papers">View all papers &rarr;</button></div>
    <div class="doc-list" id="homeRecent"></div>

    <div class="divider"><svg class="ecg-line" viewBox="0 0 260 14" preserveAspectRatio="none"><use href="#ecg"/></svg></div>
    <p class="eyebrow">Building out next</p>
    <div class="feature-grid">
      <div class="card feature-card" data-view="antibiotics" role="button" tabindex="0">
        <span class="badge">Antibiotics Hub</span>
        <h3>Quick-reference drug table</h3>
        <p>Searchable, filterable by class, sorted narrow&rarr;broad spectrum.</p>
        <table class="mini-table">
          <tr><td>Meropenem</td><td>1g q8h</td><td>CrCl-adj</td></tr>
          <tr><td>Pip-Tazo</td><td>4.5g q6h ext.</td><td>CrCl-adj</td></tr>
        </table>
      </div>
      <div class="card feature-card" data-view="theory" role="button" tabindex="0">
        <span class="badge">Theory Library</span>
        <h3>Structured CCM curriculum</h3>
        <p>Core topics with read/unread tracking and read-time badges.</p>
        <p style="margin-top:10px"><span class="badge" style="color:var(--accent);border-color:var(--accent)">Quick Read &middot; 5 min</span> &nbsp; <span class="badge">Deep Dive</span></p>
      </div>
      <div class="card feature-card" data-view="ai" role="button" tabindex="0">
        <span class="badge">AI Assistant</span>
        <h3>Ask, cited to source</h3>
        <p>&ldquo;Summarize this pearl&rdquo; or &ldquo;compare with the ESC guideline&rdquo; &mdash; answers link back to the repository.</p>
      </div>
    </div>

    <div class="subscribe-banner">
      <div><strong>Get the daily pearl by email.</strong><div style="color:var(--ink-muted);font-size:.85rem">One email a day, unsubscribe any time.</div></div>
      <button class="btn primary" data-view="subscribe" type="button">Subscribe</button>
    </div>
  </section>

  <!-- PAPERS -->
  <section class="view" id="view-papers">
    <div class="section-head" style="margin-top:0"><h2>Papers</h2></div>
    <div class="toolbar">
      <button class="btn" id="filterToggleBtn" type="button">Filters</button>
      <div class="search-box"><span>&#128269;</span><input id="papersSearch" placeholder="Search papers by title&hellip;"></div>
      <select id="papersSort" class="btn" style="margin-left:4px;font-size:.82rem">
        <option value="newest">Newest</option>
        <option value="oldest">Oldest</option>
      </select>
    </div>
    <p class="pearl-count" id="papersCount"></p>
    <div class="content-grid">
      <aside class="filter-panel" id="filterPanelDesktop"></aside>
      <section class="doc-list" id="papersList" aria-label="Filtered papers"></section>
    </div>
  </section>

  <!-- GUIDELINES -->
  <section class="view" id="view-guidelines">
    <div class="section-head" style="margin-top:0"><h2>Guidelines</h2></div>
    <div class="toolbar">
      <button class="btn" id="guidelinesFilterToggleBtn" type="button">Filters</button>
      <div class="search-box"><span>&#128269;</span><input id="guidelinesSearch" placeholder="Search guidelines by title&hellip;"></div>
      <select id="guidelinesSort" class="btn" style="margin-left:4px;font-size:.82rem">
        <option value="newest">Newest</option>
        <option value="oldest">Oldest</option>
      </select>
    </div>
    <p class="pearl-count" id="guidelinesCount"></p>
    <div class="content-grid">
      <aside class="filter-panel" id="filterPanelGuidelines"></aside>
      <section class="doc-list" id="guidelinesList" aria-label="Filtered guidelines"></section>
    </div>
  </section>

  <!-- SPECIALTY VIEW -->
  <section class="view" id="view-specialty">
    <div class="spec-view-head"><span class="dot" id="specViewDot"></span><h2 id="specViewTitle"></h2></div>
    <div class="subtopic-chip-row" id="specSubtopicChips"></div>
    <div class="spec-panel" id="specPanelPapers">
      <div class="spec-panel-head" role="button" tabindex="0">
        <span>&#128196;</span><span id="specPanelPapersTitle">Papers</span><span class="toggle-icon">&#9660;</span>
      </div>
      <div class="spec-panel-body">
        <div style="display:flex;justify-content:flex-end;margin-bottom:8px">
          <select id="specPapersSort" class="btn" style="font-size:.8rem">
            <option value="newest">Newest</option>
            <option value="oldest">Oldest</option>
          </select>
        </div>
        <div id="specPanelPapersBody"></div>
      </div>
      <button class="collapse-btn" data-target="specPanelPapers">&#9650; Collapse</button>
    </div>
    <div class="spec-panel" id="specPanelGuidelines">
      <div class="spec-panel-head" role="button" tabindex="0">
        <span>&#128203;</span><span id="specPanelGuidelinesTitle">Guidelines</span><span class="toggle-icon">&#9660;</span>
      </div>
      <div class="spec-panel-body">
        <div style="display:flex;justify-content:flex-end;margin-bottom:8px">
          <select id="specGuidelinesSort" class="btn" style="font-size:.8rem">
            <option value="newest">Newest</option>
            <option value="oldest">Oldest</option>
          </select>
        </div>
        <div id="specPanelGuidelinesBody"></div>
      </div>
      <button class="collapse-btn" data-target="specPanelGuidelines">&#9650; Collapse</button>
    </div>
    <div class="spec-panel" id="specPanelPearls">
      <div class="spec-panel-head" role="button" tabindex="0">
        <span>&#128142;</span><span id="specPanelPearlsTitle">Pearls</span><span class="toggle-icon">&#9660;</span>
      </div>
      <div class="spec-panel-body" id="specPanelPearlsBody"></div>
      <button class="collapse-btn" data-target="specPanelPearls">&#9650; Collapse</button>
    </div>
  </section>

  <!-- PEARLS -->
  <section class="view" id="view-pearls">
    <div class="section-head" style="margin-top:0"><h2>Pearls</h2></div>
    <p style="color:var(--ink-muted);font-size:.85rem;margin:0 0 14px">Dense rows, quick specialty chips, and paged loading &mdash; built for a library in the thousands, not dozens.</p>
    <div class="pearl-toolbar">
      <div class="search-box" style="flex:1;min-width:180px"><span>&#128269;</span><input id="pearlsSearch" placeholder="Search pearl text&hellip;"></div>
      <select id="pearlsSort" class="btn">
        <option value="newest">Newest first</option>
        <option value="oldest">Oldest first</option>
      </select>
    </div>
    <div class="pearl-toolbar" id="pearlChips"></div>
    <p class="pearl-count" id="pearlsCount"></p>
    <div id="pearlsList"></div>
    <div style="text-align:center;margin-top:14px">
      <button class="btn" id="loadMorePearls" type="button">Load more</button>
    </div>
  </section>

  <!-- STUB VIEWS -->
  <section class="view" id="view-antibiotics">
    <div class="coming-soon">
      <p class="coming-soon-icon">&#128679;</p>
      <h2>Coming Soon</h2>
      <p class="coming-soon-text">The Antibiotics Hub is under development. Check back soon.</p>
    </div>
  </section>
  <!-- THEORY: hero (notes + flashcards) -->
  <section class="view" id="view-theory">
    <div class="section-head" style="margin-top:0"><h2>Theory</h2></div>
    <div class="theory-crumbs" id="theoryCrumbs" style="display:none"></div>
    <div class="hero" id="theoryHero">
      <div class="card" data-theory-mode-view="notes" role="button" tabindex="0">
        <div class="stripe" style="background:var(--accent)"></div>
        <div class="card-body">
          <div class="eyebrow">Long-form notes</div>
          <h3>Theory Topics</h3>
          <p>{len(theory_notes)} deep-dive notes, rendered from markdown &mdash; tap to read.</p>
        </div>
      </div>
      <div class="card" data-theory-mode-view="flashcards" role="button" tabindex="0">
        <div class="stripe" style="background:var(--accent)"></div>
        <div class="card-body">
          <div class="eyebrow">Study cards</div>
          <h3>Flashcards</h3>
          <p>{theory_total_cards} cards across {len(theory_specs)} systems &mdash; flip, save, revise.</p>
        </div>
      </div>
    </div>

    <!-- Theory Topics (markdown notes) -->
    <div id="theoryNotesPane" style="display:none">
      <div class="section-head" style="margin-top:0">
        <h2>Theory Topics</h2>
      </div>
      <div class="pearl-toolbar" id="theoryNotesSearchRow">
        <div class="search-box" style="flex:1;min-width:180px"><span>&#128269;</span><input id="theoryNotesSearch" placeholder="Search notes&hellip;" autocomplete="off"></div>
      </div>
      <div class="pearl-toolbar" id="theoryNotesChips"></div>
      <p class="pearl-count" id="theoryNotesCount"></p>
      <div class="doc-list theory-deck-rows" id="theoryNotesList"></div>
      <div id="theoryNoteReader" style="display:none"></div>
    </div>

    <!-- Flashcards -->
    <div id="theoryFlashcardsPane" style="display:none">
      <div class="section-head" style="margin-top:0">
        <h2>Theory &mdash; Flashcards</h2>
      </div>
      <div id="theoryBrowser">
        <p style="color:var(--ink-muted);font-size:.85rem;margin:0 0 14px">Flashcards &mdash; study them card by card, flip them, save the ones worth revisiting.</p>
        <div class="pearl-toolbar">
          <div class="search-box" style="flex:1;min-width:180px"><span>&#128269;</span><input id="theorySearch" placeholder="Search decks and cards&hellip;" autocomplete="off"></div>
        </div>
        <div class="pearl-toolbar" id="theoryChips"></div>
        <div class="pearl-toolbar" id="theorySubtopicChips" style="flex-wrap:wrap"></div>
        <p class="pearl-count" id="theoryCount"></p>
        <div class="doc-list theory-deck-rows" id="theoryDeckList"></div>
      </div>
      <div id="theoryCardList" style="display:none">
        <div class="theory-card-list-head" id="theoryCardListHead"></div>
        <p class="pearl-count" id="theoryCardListCount"></p>
        <div class="doc-list" id="theoryCardListBody"></div>
      </div>
      <div id="theoryStudy" style="display:none">
        <div class="theory-card-head" id="theoryStudyHead"></div>
        <div class="theory-card-tags" id="theoryCardTags"></div>
        <div class="theory-stage" id="theoryCardStage"></div>
        <div class="reader-nav" id="theoryCardNav"></div>
        <div class="theory-dots" id="theoryCardDots"></div>
      </div>
    </div>
  </section>
  <section class="view" id="view-rrt">
    <div class="coming-soon">
      <p class="coming-soon-icon">&#128679;</p>
      <h2>Coming Soon</h2>
      <p class="coming-soon-text">The RRT section is under development. Check back soon.</p>
    </div>
  </section>
  <section class="view" id="view-ai">
    <div class="coming-soon">
      <p class="coming-soon-icon">&#128679;</p>
      <h2>Coming Soon</h2>
      <p class="coming-soon-text">The AI Assistant page is under development. Check back soon.</p>
    </div>
  </section>
  <section class="view" id="view-subscribe">
    <p class="eyebrow">Stay updated</p>
    <h2>Subscribe to the daily pearl</h2>
    <p style="color:var(--ink-muted);max-width:52ch">Coming soon &mdash; this feature is presently not active. Click the button below to access the Google Form.</p>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:14px;max-width:420px">
      <button class="btn primary" id="subscribeBtn" type="button">Subscribe via Google Form</button>
    </div>
  </section>
  <section class="view" id="view-unsubscribe">
    <p class="eyebrow">Manage email</p>
    <h2>Unsubscribe</h2>
    <p style="color:var(--ink-muted);max-width:52ch">Coming soon &mdash; this feature is presently not active. Click the button below to access the Google Form.</p>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:14px;max-width:420px">
      <button class="btn" id="unsubscribeBtn" type="button">Unsubscribe via Google Form</button>
    </div>
  </section>
  <section class="view" id="view-feedback">
    <p class="eyebrow">We&rsquo;re listening</p>
    <h2>Feedback</h2>
    <p style="color:var(--ink-muted);max-width:52ch">Bug reports, feature requests, or a pearl that felt wrong &mdash; all of it helps.</p>
    <div style="margin-top:14px">
      <button class="btn primary" id="feedbackBtn" type="button">&#128172; Send feedback via Google Form</button>
    </div>
  </section>
  <section class="view" id="view-about">
    <p class="eyebrow">About</p>
    <h2>hack.CCM</h2>
    <p style="color:var(--ink-muted);max-width:56ch">A critical care education portal built by and for ICU clinicians &mdash; summarized papers, guidelines, and pearls, kept short enough to read between patients. Companion content also runs on Instagram as HACK-CCM.</p>
  </section>

  <!-- TRIALS MAIN VIEW -->
  <section class="view" id="view-trials">
    <div class="section-head" style="margin-top:0"><h2>Trials</h2></div>

    <!-- ESBICM hero card — click opens the ESBICM dashboard directly -->
    <div class="trials-hero-card" style="cursor:pointer">
      <div data-view="trials-esbicm" role="button" tabindex="0">
        <span class="trophy">&#127942;</span>
        <h3>Recent Landmark Trials in Critical Care</h3>
        <p class="sub">Sourced from ESBICM</p>
        <p class="sub" style="margin-top:4px">{len(trial_index)} trials across {len(trial_specialties)} specialties &mdash; tap to explore</p>
      </div>
      <div style="display:flex;gap:8px;justify-content:center;margin-top:14px">
        <button class="icon-btn-sm" onclick="event.stopPropagation();openTrialOverlay('trialCreditsOverlay','credits')">&#127942; Credits</button>
        <button class="icon-btn-sm" onclick="event.stopPropagation();openTrialOverlay('trialDisclaimerOverlay','disclaimer')">&#8505;&#65039;</button>
      </div>
    </div>

    <!-- Core Critical Care Trials hero card -->
    {'' if not _user_has_feature(user, 'condensed_trials') else '''
    <div class="trials-hero-card trials-hero-condensed" style="cursor:pointer;margin-top:16px">
      <div data-view="trials-condensed" role="button" tabindex="0">
        <span class="trophy">&#128221;</span>
        <h3>Core Critical Care Trials</h3>
        <p class="sub">Summaries with PICO, outcomes &amp; critical appraisal</p>
        <p class="sub" style="margin-top:4px">{len(condensed_index)} trials &mdash; tap to explore</p>
      </div>
    </div>
    '''}
  </section>

  <!-- ESBICM MAIN (specialty grid + filter) -->
  <section class="view" id="view-trials-esbicm">
    <div class="trials-back-header">
      <button class="trials-back-btn" data-view="trials">&larr; Back</button>
      <h2>ESBICM Landmark Trials</h2>
    </div>

    <div class="trials-filter-bar">
      <div class="trials-filter-group">
        <label>Specialty</label>
        <select id="trialFilterSpecialty">
          <option value="">All Specialties</option>
          {''.join(f'<option value="{s}">{s}</option>' for s in trial_specialties)}
        </select>
      </div>
      <div class="trials-filter-group">
        <label>Result</label>
        <select id="trialFilterResult">
          <option value="">All Results</option>
          {''.join(f'<option value="{c}">{c}</option>' for c in trial_result_cats)}
        </select>
      </div>
      <div class="trials-filter-group">
        <label>Trial Type</label>
        <select id="trialFilterType">
          <option value="">All Types</option>
          {''.join(f'<option value="{t}">{t}</option>' for t in trial_types_list)}
        </select>
      </div>
      <div class="trials-filter-actions">
        <button class="btn" id="trialFilterBtn">Filter</button>
        <button class="btn" id="trialClearBtn">Clear</button>
      </div>
    </div>

    <div id="trialsEsbicmResults"></div>
  </section>

  <!-- ESBICM SPECIALTY VIEW -->
  <section class="view" id="view-trials-specialty">
    <div class="trials-back-header">
      <button class="trials-back-btn" id="trialsSpecBackBtn">&larr; Back</button>
      <span class="dot" id="trialsSpecDot" style="width:14px;height:14px"></span>
      <h2 id="trialsSpecTitle"></h2>
    </div>
    <div class="subtopic-chip-row" id="trialsSubtopicChips"></div>
    <div id="trialsSpecList"></div>
  </section>

  <!-- CONDENSED TRIALS MAIN (system grid + filter) -->
  <section class="view" id="view-trials-condensed">
    <div class="trials-back-header">
      <button class="trials-back-btn" data-view="trials">&larr; Back</button>
      <h2>Core Critical Care Trials</h2>
    </div>

    <div class="trials-filter-bar">
      <div class="trials-filter-group">
        <label>Specialty</label>
        <select id="condensedFilterSpecialty">
          <option value="">All Specialties</option>
          {''.join(f'<option value="{s}">{s}</option>' for s in condensed_systems)}
        </select>
      </div>
      <div class="trials-filter-group">
        <label>Result</label>
        <select id="condensedFilterResult">
          <option value="">All Results</option>
          {''.join(f'<option value="{c}">{c}</option>' for c in condensed_result_cats)}
        </select>
      </div>
      <div class="trials-filter-group">
        <label>Trial Type</label>
        <select id="condensedFilterType">
          <option value="">All Types</option>
          {''.join(f'<option value="{t}">{t}</option>' for t in condensed_types_list)}
        </select>
      </div>
      <div class="trials-filter-actions">
        <button class="btn" id="condensedFilterBtn">Filter</button>
        <button class="btn" id="condensedClearBtn">Clear</button>
      </div>
    </div>

    <div id="condensedTrialsContent"></div>
  </section>

  <!-- CONDENSED TRIALS SYSTEM VIEW -->
  <section class="view" id="view-condensed-system">
    <div class="trials-back-header">
      <button class="trials-back-btn" data-view="trials-condensed">&larr; Back</button>
      <h2 id="condensedSysTitle"></h2>
    </div>
    <div id="condensedSysList"></div>
  </section>

  <!-- CONDENSED TRIAL DETAIL -->
  <section class="view" id="view-condensed-detail">
    <div class="trials-back-header">
      <button class="trials-back-btn" id="condensedDetailBackBtn">&larr; Back</button>
      <div style="flex:1"></div>
    </div>
    <div class="trial-detail" id="condensedDetailBody"></div>
  </section>

  <!-- TRIAL DETAIL FULL PAGE -->
  <section class="view" id="view-trial-detail">
    <div class="trials-back-header">
      <button class="trials-back-btn" id="trialDetailBackBtn">&larr; Back</button>
      <div style="flex:1"></div>
      <button class="trials-back-btn" id="trialDetailPrevBtn" data-trial-prev style="display:none">&larr; Prev</button>
      <button class="trials-back-btn" id="trialDetailNextBtn" data-trial-next style="display:none">Next &rarr;</button>
    </div>
    <div class="trial-detail" id="trialDetailBody"></div>
  </section>

  <!-- BOOKMARKS -->
  <section class="view" id="view-bookmarks">
    <div class="section-head" style="margin-top:0">
      <h2>&#128278; Bookmarks</h2>
      <span class="pearl-count" id="bookmarksCount"></span>
    </div>
    <div class="toolbar">
      <div class="search-box" style="min-width:180px">
        <span>&#128269;</span>
        <input id="bookmarksSearch" placeholder="Filter by title or tag&hellip;" autocomplete="off">
      </div>
      <button class="btn" id="bookmarksNewFolderBtn">&#128193; New folder</button>
    </div>
    <div class="bm-new-folder" id="bookmarksNewFolderRow">
      <input id="bookmarksNewFolderName" placeholder="Folder name" maxlength="60">
      <div id="bookmarksNewFolderColors" style="display:flex;gap:6px;align-items:center"></div>
      <button class="btn primary" id="bookmarksCreateFolderBtn">Create</button>
      <button class="btn" id="bookmarksCancelFolderBtn">Cancel</button>
    </div>
    <div class="bookmarks-folder-row" id="bookmarksFoldersRow"></div>
    <div id="bookmarksList"></div>
  </section>

</main>

<!-- MOBILE FILTER SHEET -->
<div class="sheet-backdrop" id="sheetBackdrop"></div>
<div class="sheet" id="filterSheet" role="dialog" aria-label="Filters">
  <div class="sheet-handle"></div>
  <div id="filterSheetBody"></div>
</div>

<!-- HAMBURGER DRAWER -->
<div class="drawer-backdrop" id="drawerBackdrop"></div>
<nav class="drawer" id="drawer" aria-label="Site menu">
  <h4>Navigate</h4>
  <button class="drawer-link" data-view="home">&#127968; Home</button>
  <button class="drawer-link" data-view="papers">&#128196; Papers</button>
  <button class="drawer-link" data-view="guidelines">&#128203; Guidelines</button>
  <button class="drawer-link" data-view="pearls">&#128142; Pearls</button>
  <button class="drawer-link" data-view="trials">&#127942; Trials</button>
  <button class="drawer-link" data-view="antibiotics">&#128137; Antibiotics</button>
  <button class="drawer-link" data-view="theory">&#129504; Theory Library</button>
  <button class="drawer-link" data-view="rrt">&#128680; RRT</button>
  <button class="drawer-link" data-view="ai">&#129302; AI Assistant</button>
  <button class="drawer-link" data-view="bookmarks">&#128278; Bookmarks<span class="bm-count zero" id="bookmarksDrawerCount">0</span></button>
  <h4>Text size</h4>
  <div class="chip-row" id="fontChips">
    <button class="chip" data-font-px="14">XS</button>
    <button class="chip" data-font-px="15">S</button>
    <button class="chip active" data-font-px="16">M</button>
    <button class="chip" data-font-px="17">L</button>
    <button class="chip" data-font-px="18">XL</button>
  </div>
  <h4>Theme</h4>
  <div class="chip-row" id="themeChips">
    <button class="chip" data-theme-choice="light">Light</button>
    <button class="chip active" data-theme-choice="dim">Dim</button>
    <button class="chip" data-theme-choice="dark">Dark</button>
  </div>
  <h4>Account &amp; feedback</h4>
  <button class="drawer-link" data-view="subscribe">&#9993;&#65039; Subscribe</button>
  <button class="drawer-link" data-view="unsubscribe">&#9995; Unsubscribe</button>
  <button class="drawer-link" data-view="feedback">&#128172; Feedback</button>
  <button class="drawer-link" data-view="about">&#8505;&#65039; About us</button>
  <button class="drawer-link" data-open-disclaimer>&#9888;&#65039; Disclaimer</button>
  <button class="drawer-link" id="drawerLogout">&#128682; Sign Out</button>
</nav>

<!-- GLOBAL SEARCH -->
<div class="search-overlay-backdrop" id="searchBackdrop"></div>
<div class="search-overlay" id="searchOverlay" role="dialog" aria-label="Global search">
  <div class="search-input-row">
    <span>&#128269;</span>
    <input id="globalSearchInput" placeholder="Search papers, pearls, antibiotics&hellip;" autocomplete="off">
    <button class="icon-btn" id="closeSearchBtn" aria-label="Close search">&#10005;</button>
  </div>
  <div class="search-results" id="searchResults"></div>
</div>

<!-- READING PANEL -->
<div class="reader-backdrop" id="readerBackdrop"></div>
<div class="reader" id="reader" role="dialog" aria-label="Reading view">
  <div class="reader-head">
    <div class="reader-progress" id="readerProgress"></div>
    <div class="reader-top">
      <button class="icon-btn" id="closeReader" aria-label="Close">&#8592;</button>
      <div class="size-chip-row" id="readerFontChips">
        <button class="size-chip" data-reader-font="0.85" style="font-size:11px" aria-label="Extra small text">A</button>
        <button class="size-chip" data-reader-font="0.925" style="font-size:12px" aria-label="Small text">A</button>
        <button class="size-chip active" data-reader-font="1" style="font-size:13px" aria-label="Medium text">A</button>
        <button class="size-chip" data-reader-font="1.1" style="font-size:14px" aria-label="Large text">A</button>
        <button class="size-chip" data-reader-font="1.25" style="font-size:15px" aria-label="Extra large text">A</button>
      </div>
      <button class="icon-btn" aria-label="Read aloud" style="margin-left:auto">&#128266;</button>
    </div>
  </div>
  <div class="reader-body" id="readerBody"></div>
</div>

<!-- AI ASSISTANT FAB -->
<button id="scrollTopBtn" aria-label="Scroll to top">&#9650;</button>
<button class="ai-fab" id="aiFab" aria-label="Open AI assistant">&#129302;</button>
<div class="ai-panel" id="aiPanel">
  <p class="eyebrow" style="margin-bottom:8px">AI Assistant</p>
  <div class="ai-msg">Explain the 0/1-hr troponin pearl in simpler terms.<span class="ai-source">&rarr; sourced from RAPID-TnT summary</span></div>
  <div class="ai-msg">One undetectable troponin, taken 3+ hours after pain started, is usually enough to rule out a heart attack &mdash; no need to wait for a repeat draw.</div>
</div>

<!-- BOTTOM NAV -->
<nav class="bottom-nav" aria-label="Primary mobile">
  <button class="nav-item" data-view="papers"><svg class="notch ecg-line" viewBox="0 0 260 14" preserveAspectRatio="none"><use href="#ecg"/></svg><span class="glyph">&#128196;</span>Papers</button>
  <button class="nav-item" data-view="guidelines"><svg class="notch ecg-line" viewBox="0 0 260 14" preserveAspectRatio="none"><use href="#ecg"/></svg><span class="glyph">&#128203;</span>Guidelines</button>
  <button class="nav-item" data-view="pearls"><svg class="notch ecg-line" viewBox="0 0 260 14" preserveAspectRatio="none"><use href="#ecg"/></svg><span class="glyph">&#128142;</span>Pearls</button>
  <button class="nav-item" data-view="trials"><svg class="notch ecg-line" viewBox="0 0 260 14" preserveAspectRatio="none"><use href="#ecg"/></svg><span class="glyph">&#127942;</span>Trials</button>
  <button class="nav-item" data-view="theory"><svg class="notch ecg-line" viewBox="0 0 260 14" preserveAspectRatio="none"><use href="#ecg"/></svg><span class="glyph">&#129504;</span>Theory</button>
  <button class="nav-item" data-view="bookmarks"><svg class="notch ecg-line" viewBox="0 0 260 14" preserveAspectRatio="none"><use href="#ecg"/></svg><span class="glyph">&#128278;</span>Saved</button>
</nav>

<div class="toast" id="toast"></div>

<!-- DISCLAIMER -->
<div id="disclaimerOverlay" class="disclaimer-backdrop" style="display:none">
  <div class="disclaimer-box">
    <div id="disclaimerText"></div>
    <div style="display:flex;gap:10px;margin-top:18px;flex-wrap:wrap">
      <button class="btn primary" onclick="dismissDisclaimer()" style="flex:1;padding:12px;border-radius:8px;border:none;background:var(--accent);color:var(--accent-ink);font-weight:700;font-size:.9rem;">Proceed to Dashboard</button>
      <button class="btn" onclick="window.open('{FEEDBACK_FORM_URL}','_blank')" style="flex:1;padding:12px;border-radius:8px;font-size:.85rem;">\U0001F50D Report Issue</button>
    </div>
  </div>
</div>

<!-- TRIAL CREDITS OVERLAY -->
<div id="trialCreditsOverlay" class="trial-overlay-backdrop" style="display:none">
  <div class="trial-overlay-box">
    <h2>&#127942; Credits</h2>
    <div id="trialCreditsText"></div>
    <button class="btn" onclick="closeTrialOverlay('trialCreditsOverlay')" style="margin-top:14px">Close</button>
  </div>
</div>

<!-- TRIAL DISCLAIMER OVERLAY -->
<div id="trialDisclaimerOverlay" class="trial-overlay-backdrop" style="display:none">
  <div class="trial-overlay-box">
    <h2>&#9888;&#65039; Disclaimer</h2>
    <div id="trialDisclaimerText"></div>
    <button class="btn" onclick="closeTrialOverlay('trialDisclaimerOverlay')" style="margin-top:14px">Close</button>
  </div>
</div>

<!-- THEORY TABLE FULL VIEW -->
<div id="theoryTableOverlay" class="theory-table-overlay" style="display:none" role="dialog" aria-label="Table full view">
  <div class="theory-table-overlay-bar">
    <button class="btn nav-btn" data-theory-table-close style="flex:0 0 auto">&larr; Back</button>
    <span class="theory-table-overlay-title" id="theoryTableOverlayTitle">Table</span>
    <button class="btn nav-btn" data-theory-table-fit style="flex:0 0 auto">Fit width</button>
  </div>
  <div class="theory-table-overlay-scroll" id="theoryTableOverlayScroll"><div class="theory-table-fit-inner" id="theoryTableFitInner"></div></div>
</div>

<script>
// =====================================================================
// DATA (injected from Python)
// =====================================================================
const SPEC_VAR = {spec_vars_js};
const SPECS = {spec_labels_js}.map(function(n){{ return {{name:n, var:SPEC_VAR[n]}}; }});
const TYPES = {type_list_js};

const baseDataset = {json.dumps(articles_list)};
const allPearls = {json.dumps(pearls)};
const SUBTOPIC_MAP = {json.dumps(subtopic_map)};
const showDisclaimer = {show_disclaimer};

// Trial data
const TRIAL_INDEX = {trial_index_js};
const TRIAL_SPECS = {trial_spec_labels_js};
const TRIAL_SPEC_VAR = {trial_spec_vars_js};
const TRIAL_SPEC_COUNTS = {trial_spec_counts_js};
const TRIAL_SUBTOPIC_MAP = {trial_subtopic_map_js};
const TRIAL_RESULT_CATS = {trial_result_cats_js};
const TRIAL_TYPES = {trial_types_list_js};

// Condensed trial data
const CONDENSED_INDEX = {condensed_index_js};
const CONDENSED_SYSTEMS = {condensed_systems_js};
const CONDENSED_RESULT_CATS = {condensed_result_cats_js};
const CONDENSED_TYPES = {condensed_types_list_js};

// Theory flashcard decks (unified store) + theory notes
const allFlashcardDecks = {flashcard_decks_js};
const THEORY_SPEC_VAR = {theory_spec_vars_js};
const THEORY_SUBTOPIC_MAP = {theory_subtopic_map_js};
const THEORY_NOTES = {theory_notes_js};

// Feature flags (resolved server-side: defaults + per-user overrides)
const USER_FEATURES = {user_features_js};
const USER_IS_ADMIN = {user_is_admin_js};

let _trialFilterState = {{ specialty: '', result_category: '', trial_type: '' }};
let _currentTrialList = [];
let _currentTrialIdx = -1;
let _currentTrialSlug = '';
let _currentCondensedRef = '';
let _bookmarks = {{items: {{}}, folders: {{}}}};
let _bookmarkMeta = {{}};
let _bookmarksFolderFilter = null;
let _bmNewFolderColor = '#E8B778';
const BM_FOLDER_COLORS = ['#E8B778','#0C8A8B','#2DD4CF','#8B5CF6','#EF4444','#10B981','#D97706','#6B7280'];

// Theory flashcard study state
let _theoryMode = null; // null = hero, 'notes' = Theory Topics, 'flashcards' = decks
let _theoryActiveSpecs = new Set(allFlashcardDecks.map(function(d){{ return d.specialty; }}));
let _theorySavedOnly = false;
let _notesSavedOnly = false;
let _notesActiveSpecs = new Set();
let _notesActiveSubtopic = null;
let _currentTheoryNote = null;
let _theoryTableOverlayOpen = false;
let _theoryTableFitActive = false;
let _theoryActiveSubtopic = null;
let _currentDeck = null;
let _currentCardIdx = 0;
let _theoryCardOrder = [];
let _theoryViewMode = 'single';
let _theoryFlipped = false;
let _theoryListCollapsed = false; // card list collapses into a dropdown when a card is open
let _theoryStudyFromList = false; // study was entered from the per-deck card list
let _restoring = false; // true while restoring from history/deep links (no pushes)
let _theorySearchTimers = {{}};
// True when the browser can do real 3D card flips (backface-visibility).
// False -> the reader falls back to display-swapping (.no-3d) so faces never stack.
let _css3d = (function(){{
  try {{ return !!(window.CSS && window.CSS.supports && window.CSS.supports('backface-visibility','hidden')); }}
  catch(e) {{ return false; }}
}})();

// =====================================================================
// STATE
// =====================================================================
const filterState = {{
  specialties: Object.fromEntries(SPECS.map(function(s){{ return [s.name,true]; }})),
  types: Object.fromEntries(TYPES.map(function(t){{ return [t,true]; }})),
}};
let activePearlSpecs = new Set(SPECS.map(function(s){{ return s.name; }}));
let pearlsPageSize = 25;
let pearlsShown = pearlsPageSize;
let activeSubtopic = null;

// =====================================================================
// HELPERS
// =====================================================================
function pillHTML(spec, label){{
  var v = SPEC_VAR[spec];
  if (!v) v = '--spec-other';
  return '<span class="pill" style="background:color-mix(in srgb, var('+v+') 18%, transparent); color:var('+v+')"><span class="dot" style="background:var('+v+')"></span>'+label+'</span>';
}}

function docCardHTML(p){{
  var v = SPEC_VAR[p.system] || '--spec-other';
  var dateStr = p.date_added ? p.date_added.substring(0,10) : '';
  return '<button class="doc-card" data-open-paper="'+p.id+'">'+
    '<div class="doc-stripe" style="background:var('+v+')"></div>'+
    '<div class="doc-inner">'+
      '<div class="doc-top">'+pillHTML(p.system, p.system)+'<span class="type-tag">'+p.type+' &middot; '+dateStr+'</span></div>'+
      '<p class="doc-title">'+p.title+'</p>'+
      '<p class="doc-snippet">'+(p.authors!=='Unknown Authors' ? '&mdash; '+p.authors : '')+'</p>'+
    '</div>'+
  '</button>';
}}

function emptyStateHTML(label){{
  return '<p style="color:var(--ink-muted);padding:20px 4px">No '+label+' match these filters. Try clearing a specialty or type.</p>';
}}

// =====================================================================
// VIEW SWITCHING
// =====================================================================
function showView(name){{
  // Feature flag check: block views that the user doesn't have access to
  var featureMap = {{
    'trials': 'trials',
    'trials-esbicm': 'trials',
    'trials-condensed': 'condensed_trials',
    'trials-specialty': 'trials',
    'trials-detail': 'trials_detail',
    'condensed-system': 'condensed_trials',
    'condensed-detail': 'trials_detail',
    'papers': 'papers',
    'guidelines': 'guidelines',
    'pearls': 'pearls',
    'search': 'search',
    'bookmarks': 'bookmarks',
    'theory': 'theory'
  }};
  var requiredFeature = featureMap[name];
  if (requiredFeature && !USER_IS_ADMIN && !USER_FEATURES[requiredFeature]) {{
    return;
  }}
  document.querySelectorAll('.view').forEach(function(v){{ v.classList.remove('active'); }});
  var target = document.getElementById('view-'+name);
  (target || document.getElementById('view-home')).classList.add('active');
  document.querySelectorAll('[data-view]').forEach(function(el){{ el.classList.toggle('active', el.dataset.view===name); }});
  window.scrollTo({{top:0, behavior:'instant'}});
  closeDrawer(); closeSheet();
  if(name==='home'){{ renderHomeHero(); renderHomeStats(); renderHomeSpecGrid(); renderHomeRecent(); }}
  if(name==='papers') renderPapers();
  if(name==='guidelines') renderGuidelines();
  if(name==='pearls'){{ renderPearlChips(); renderPearls(); }}
  if(name==='trials') renderTrials();
  if(name==='trials-esbicm') renderESBICM();
  if(name==='trials-condensed') renderCondensedTrials();
  if(name==='bookmarks') renderBookmarks();
  if(name==='theory'){{
    var activeView = document.querySelector('.view.active');
    if(activeView && activeView.id==='view-theory'){{
      if(_theoryMode) theoryBackToHero();
    }} else {{
      renderTheoryPane(_theoryMode);
    }}
  }}
}}

// =====================================================================
// HOME
// =====================================================================
function getDailyIndex(){{
  var t=new Date().toISOString().split('T')[0];
  var h=0;for(var i=0;i<t.length;i++){{h=((h<<5)-h)+t.charCodeAt(i);h=h&h;}}
  return Math.abs(h)%(baseDataset.length||1);
}}

var _pearlOfDay = null;
var _currentPearlList = [];
var _currentPearlIndex = -1;
var _readerHistoryStack = [];
function renderHomeHero(){{
  if (!baseDataset.length) {{ document.getElementById('homeHero').innerHTML = ''; return; }}
  var sorted = [].concat(baseDataset).sort(function(a,b){{ return parseInt(a.id)-parseInt(b.id); }});
  var paperOfDay = sorted[getDailyIndex()];
  _pearlOfDay = allPearls.length ? allPearls[Math.floor(Math.random()*allPearls.length)] : null;
  var pv = SPEC_VAR[paperOfDay.system] || '--spec-other';
  document.getElementById('homeHero').innerHTML =
    '<div class="card" data-open-paper="'+paperOfDay.id+'" tabindex="0" role="button" aria-label="Open paper of the day">'+
      '<div class="stripe" style="background:var('+pv+')"></div>'+
      '<div class="card-body">'+
        '<p class="eyebrow" style="margin-bottom:8px">Paper of the day</p>'+
        pillHTML(paperOfDay.system, paperOfDay.system+' &middot; '+paperOfDay.type)+
        '<h3>'+escapeHtml(paperOfDay.title)+'</h3>'+
        '<p>'+(paperOfDay.authors && paperOfDay.authors!=='Unknown Authors' ? '&mdash; '+escapeHtml(paperOfDay.authors) : '')+'</p>'+
      '</div>'+
    '</div>'+
    (_pearlOfDay ? (
      '<div class="card" data-open-pearl="day" tabindex="0" role="button" aria-label="Open pearl of the day">'+
        '<div class="stripe" style="background:var(--spec-other)"></div>'+
        '<div class="card-body">'+
          '<p class="eyebrow" style="margin-bottom:8px">Pearl of the day</p>'+
          pillHTML(_pearlOfDay.system || 'General', (_pearlOfDay.system || 'General')+' &middot; Pearl')+
          '<h3 style="font-size:1rem">"'+escapeHtml((_pearlOfDay.pearl||'').substring(0,120))+(_pearlOfDay.pearl && _pearlOfDay.pearl.length>120?'&hellip;':'')+'"</h3>'+
          '<p>Tap to read the full context.</p>'+
        '</div>'+
      '</div>'
    ) : '');
}}

function renderHomeStats(){{
  var papersCount = baseDataset.filter(function(a){{ return a.type.toLowerCase()!=='guideline'; }}).length;
  var guidelinesCount = baseDataset.filter(function(a){{ return a.type.toLowerCase()==='guideline'; }}).length;
  var specsCount = new Set(baseDataset.map(function(a){{ return a.system; }})).size;
  document.getElementById('homeStats').innerHTML =
    '<div class="stat-item"><b>'+papersCount+'</b>papers</div>'+
    '<div class="stat-item"><b>'+guidelinesCount+'</b>guidelines</div>'+
    '<div class="stat-item"><b>'+allPearls.length+'</b>pearls</div>'+
    '<div class="stat-item"><b>'+specsCount+'</b>specialties</div>';
}}

function renderHomeSpecGrid(){{
  var specCounts = {{}};
  baseDataset.forEach(function(a){{ specCounts[a.system] = (specCounts[a.system]||0)+1; }});
  var sortedSpecs = Object.keys(specCounts).sort();
  document.getElementById('homeSpecGrid').innerHTML = sortedSpecs.map(function(s){{
    var v = SPEC_VAR[s] || '--spec-other';
    var count = specCounts[s];
    return '<button class="spec-tile" data-spec-jump="'+s+'" style="--tile-color:var('+v+')">'+
      '<span class="dot" style="background:var('+v+')"></span>'+
      '<div style="font-weight:700;font-size:.88rem">'+s+'</div>'+
      '<div class="count">'+count+' articles</div>'+
    '</button>';
  }}).join('');
}}

function renderHomeRecent(){{
  var recent = [].concat(baseDataset).sort(function(a,b){{ return (b.date_added||'').localeCompare(a.date_added||''); }});
  document.getElementById('homeRecent').innerHTML = recent.slice(0,3).map(docCardHTML).join('');
}}

function jumpToSpecialty(name){{
  activeSubtopic = null;
  showView('specialty');
  renderSpecialty(name);
}}

// =====================================================================
// FILTER PANEL (papers)
// =====================================================================
function filterGroupsHTML(){{
  var specHTML = SPECS.map(function(s){{
    return '<label><input type="checkbox" data-spec="'+s.name+'" '+(filterState.specialties[s.name]?'checked':'')+'><span class="dot" style="background:var('+s.var+')"></span>'+s.name+'</label>';
  }}).join('');
  return ''+
    '<div class="filter-actions">'+
      '<button class="btn filter-reset" type="button" style="width:48%">Reset</button>'+
      '<button class="btn primary apply-btn" type="button" style="width:48%">Apply</button>'+
    '</div>'+
    '<div class="filter-group">'+
      '<h4>Specialty</h4>'+
      '<label><input type="checkbox" class="all-check" data-group="specialties"><strong>All</strong></label>'+
      specHTML+
    '</div>';
}}

function updateAllCheckboxState(container, group){{
  var allBox = container.querySelector('.all-check[data-group="'+group+'"]');
  if(!allBox) return;
  var boxes = [].slice.call(container.querySelectorAll(group==='specialties' ? '[data-spec]' : '[data-type]'));
  var checkedCount = boxes.filter(function(b){{ return b.checked; }}).length;
  allBox.checked = checkedCount===boxes.length;
  allBox.indeterminate = checkedCount>0 && checkedCount<boxes.length;
}}

function renderFilterCheckboxes(){{
  ['filterPanelDesktop','filterSheetBody','filterPanelGuidelines'].forEach(function(id){{
    var el = document.getElementById(id);
    if(!el) return;
    el.innerHTML = filterGroupsHTML();
    updateAllCheckboxState(el,'specialties');
  }});
}}

function renderPapers(){{
    var q = (document.getElementById('papersSearch').value || '').toLowerCase().trim();
    var sortVal = document.getElementById('papersSort').value;
    var articles = baseDataset.filter(function(p){{ return p.type.toLowerCase()!=='guideline'; }});
    var filtered = articles.filter(function(p){{
      return filterState.specialties[p.system] && (q==='' || p.title.toLowerCase().indexOf(q)!==-1);
    }});
    if(sortVal==='newest'){{
      filtered = [].concat(filtered).sort(function(a,b){{ return (b.date_added||'').localeCompare(a.date_added||''); }});
    }} else {{
      filtered = [].concat(filtered).sort(function(a,b){{ return (a.date_added||'').localeCompare(b.date_added||''); }});
    }}
    document.getElementById('papersList').innerHTML = filtered.map(docCardHTML).join('') || emptyStateHTML('papers');
    document.getElementById('papersCount').textContent = 'Showing '+filtered.length+' of '+articles.length+' papers';
  }}

function renderGuidelines(){{
    var q = (document.getElementById('guidelinesSearch').value || '').toLowerCase().trim();
    var sortVal = document.getElementById('guidelinesSort').value;
    var filtered = baseDataset.filter(function(p){{
      return p.type.toLowerCase()==='guideline' && filterState.specialties[p.system] && (q==='' || p.title.toLowerCase().indexOf(q)!==-1);
    }});
    if(sortVal==='newest'){{
      filtered = [].concat(filtered).sort(function(a,b){{ return (b.date_added||'').localeCompare(a.date_added||''); }});
    }} else {{
      filtered = [].concat(filtered).sort(function(a,b){{ return (a.date_added||'').localeCompare(b.date_added||''); }});
    }}
    document.getElementById('guidelinesList').innerHTML = filtered.map(docCardHTML).join('') || emptyStateHTML('guidelines');
    document.getElementById('guidelinesCount').textContent = 'Showing '+filtered.length+' guidelines';
  }}

// =====================================================================
// SPECIALTY THREE-PANEL VIEW
// =====================================================================
function renderSpecialty(name){{
  var v = SPEC_VAR[name] || '--spec-other';
  document.getElementById('specViewDot').style.background = 'var('+v+')';
  document.getElementById('specViewTitle').textContent = name;

  var papersInSpec = baseDataset.filter(function(p){{ return p.system===name && p.type.toLowerCase()!=='guideline'; }});
  var guidelinesInSpec = baseDataset.filter(function(p){{ return p.system===name && p.type.toLowerCase()==='guideline'; }});
  var pearlsInSpec = allPearls.filter(function(p){{ return p.system===name; }});

  /* apply subtopic filter */
  if(activeSubtopic){{
    papersInSpec = papersInSpec.filter(function(p){{ return (p.subtopic||p.system)===activeSubtopic; }});
    guidelinesInSpec = guidelinesInSpec.filter(function(p){{ return (p.subtopic||p.system)===activeSubtopic; }});
    pearlsInSpec = pearlsInSpec.filter(function(p){{ return (p.subtopic||p.system)===activeSubtopic; }});
  }}

  /* apply sort */
  var specPapersSort = document.getElementById('specPapersSort').value;
  if(specPapersSort==='newest'){{
    papersInSpec = [].concat(papersInSpec).sort(function(a,b){{ return (b.date_added||'').localeCompare(a.date_added||''); }});
  }} else {{
    papersInSpec = [].concat(papersInSpec).sort(function(a,b){{ return (a.date_added||'').localeCompare(b.date_added||''); }});
  }}
  var specGuidelinesSort = document.getElementById('specGuidelinesSort').value;
  if(specGuidelinesSort==='newest'){{
    guidelinesInSpec = [].concat(guidelinesInSpec).sort(function(a,b){{ return (b.date_added||'').localeCompare(a.date_added||''); }});
  }} else {{
    guidelinesInSpec = [].concat(guidelinesInSpec).sort(function(a,b){{ return (a.date_added||'').localeCompare(b.date_added||''); }});
  }}

  document.getElementById('specPanelPapersTitle').innerHTML = 'Papers ('+papersInSpec.length+')';
  document.getElementById('specPanelPapersBody').innerHTML = papersInSpec.map(docCardHTML).join('') || emptyStateHTML('papers');
  document.getElementById('specPanelPapers').classList.add('open');

  document.getElementById('specPanelGuidelinesTitle').innerHTML = 'Guidelines ('+guidelinesInSpec.length+')';
  document.getElementById('specPanelGuidelinesBody').innerHTML = guidelinesInSpec.map(docCardHTML).join('') || emptyStateHTML('guidelines');
  document.getElementById('specPanelGuidelines').classList.remove('open');

  document.getElementById('specPanelPearlsTitle').innerHTML = 'Pearls ('+pearlsInSpec.length+')';
  var specV = SPEC_VAR[name] || '--spec-other';
  document.getElementById('specPanelPearlsBody').innerHTML = pearlsInSpec.map(function(p){{
    return '<div class="pearl-row" style="cursor:pointer;display:block;padding:11px 4px;border-bottom:1px solid var(--border)" data-open-pearl="'+p.id+'">'+
      '<div style="margin-bottom:4px;font-size:.88rem;line-height:1.4">'+escapeHtml(p.pearl||'')+'</div>'+
      '<div style="font-size:.7rem;color:var('+specV+');opacity:.85">'+escapeHtml(p.source_paper||'')+'</div>'+
    '</div>';
  }}).join('') || '<p style="color:var(--ink-muted);padding:11px 4px">No pearls for this specialty yet.</p>';
  document.getElementById('specPanelPearls').classList.remove('open');

  renderSpecialtySubtopicChips(name);
}}

function renderSpecialtySubtopicChips(name){{
  var subtopics = SUBTOPIC_MAP[name] || [];
  var chipsHTML = '<button class="subtopic-chip-clear" data-subtopic-clear>Clear all</button>';
  subtopics.forEach(function(st){{
    var paperCount = baseDataset.filter(function(p){{ return p.system===name && (p.subtopic||p.system)===st && p.type.toLowerCase()!=='guideline'; }}).length;
    var guidelineCount = baseDataset.filter(function(p){{ return p.system===name && (p.subtopic||p.system)===st && p.type.toLowerCase()==='guideline'; }}).length;
    var pearlCount = allPearls.filter(function(p){{ return p.system===name && (p.subtopic||p.system)===st; }}).length;
    var active = activeSubtopic===st ? ' active' : '';
    chipsHTML += '<button class="subtopic-chip'+active+'" data-subtopic="'+st+'">'+st+' <span style="opacity:.6">'+paperCount+'p '+guidelineCount+'g '+pearlCount+'&#9679;</span></button>';
  }});
  document.getElementById('specSubtopicChips').innerHTML = chipsHTML;
}}

// =====================================================================
// PEARLS
// =====================================================================
function renderPearlChips(){{
  var pearlCounts = {{}};
  allPearls.forEach(function(p){{ var sys=p.system||'Other'; pearlCounts[sys]=(pearlCounts[sys]||0)+1; }});
  var chipsHTML = SPECS.map(function(s){{
    var count = pearlCounts[s.name]||0;
    var active = activePearlSpecs.has(s.name);
    return '<button class="chip '+(active?'active':'')+'" data-pearl-chip="'+s.name+'" style="--chip-color:var('+s.var+')"><span class="dot" style="background:'+(active?'currentColor':'var('+s.var+')')+'"></span>'+s.name+' ('+count+')</button>';
  }}).join('');
  document.getElementById('pearlChips').innerHTML = chipsHTML + '<button class="chip" data-pearl-chip-reset>Reset</button><button class="chip" data-pearl-chip-uncheck>Uncheck all</button>';
}}

function renderPearls(){{
  var q = (document.getElementById('pearlsSearch').value || '').toLowerCase().trim();
  var sortVal = document.getElementById('pearlsSort').value;
  var filtered = allPearls.filter(function(p){{
    return activePearlSpecs.has(p.system) && (q==='' || (p.pearl||'').toLowerCase().indexOf(q)!==-1);
  }});
  if(sortVal==='newest') {{
    filtered = [].concat(filtered).sort(function(a,b){{ return parseInt(b.id||0) - parseInt(a.id||0); }});
  }} else {{
    filtered = [].concat(filtered).sort(function(a,b){{ return parseInt(a.id||0) - parseInt(b.id||0); }});
  }}
  _currentPearlList = filtered;
  var shown = filtered.slice(0, pearlsShown);
  var noPearlsHTML = emptyStateHTML('pearls');
  if(activePearlSpecs.size===0){{ noPearlsHTML = '<p style="color:var(--ink-muted);text-align:center;padding:20px">Select a specialty above to see pearls.</p>'; }}
  document.getElementById('pearlsList').innerHTML = shown.map(function(p){{
    var v = SPEC_VAR[p.system] || '--spec-other';
    return '<button class="pearl-row" data-open-pearl="'+p.id+'">'+
      '<span class="dot" style="background:var('+v+')"></span>'+
      '<span class="txt">'+escapeHtml((p.pearl||'').substring(0,150))+(p.pearl&&p.pearl.length>150?'&hellip;':'')+'<span class="src">'+(p.system||'')+' &middot; '+(p.source_paper||'Clinical pearl')+' &middot; '+(p.timestamp||'')+'</span></span>'+
    '</button>';
  }}).join('') || noPearlsHTML;
  document.getElementById('pearlsCount').textContent = 'Showing '+shown.length+' of '+filtered.length+' pearls';
  document.getElementById('loadMorePearls').style.display = shown.length < filtered.length ? 'inline-flex' : 'none';
}}

// =====================================================================
// READER
// =====================================================================
function openReader(entry, kind){{
  if (!entry) return;
  var v = SPEC_VAR[entry.system] || '--spec-other';
  var body = document.getElementById('readerBody');
  body.scrollTop = 0;
  document.getElementById('readerProgress').style.width = '0%';

  if(kind==='pearl'){{
    _currentPearlIndex = _currentPearlList.findIndex(function(p){{ return String(p.id)===String(entry.id); }});
    var idx = _currentPearlIndex;
    var prevBtn = idx>0 ? '<button class="btn nav-btn" data-pearl-nav="prev">&#9664; Previous</button>' : '';
    var nextBtn = idx>=0 && idx<_currentPearlList.length-1 ? '<button class="btn nav-btn" data-pearl-nav="next">Next &#9654;</button>' : '';
    var hasPrintablePaper = entry.file_name && baseDataset.some(function(d){{ return d.file_name === entry.file_name.replace(/\\.json$/, '.pdf'); }});
    var articleBtn = hasPrintablePaper ? '<button class="btn nav-btn" data-open-pearl-article="'+entry.id+'">&#128196; Open article</button>' : '';
    var navRow = (prevBtn||nextBtn||articleBtn) ? '<div class="reader-nav">'+articleBtn+prevBtn+nextBtn+'</div>' : '';
    var pbmRef = 'pearl:'+entry.id;
    registerBookmarkMeta(pbmRef, {{kind:'pearl', title: entry.pearl || entry.source_paper || 'Clinical pearl', system: entry.system || 'General', type: entry.type || 'Pearl', locator: {{id: entry.id}}}});
    body.innerHTML = ''+
      pillHTML(entry.system||'General', (entry.system||'General')+' &middot; Pearl')+
      '<h2 style="font-size:1.15rem;line-height:1.4">"'+escapeHtml(entry.pearl||'')+'"</h2>'+
      '<p class="meta">'+(entry.source_paper||'Clinical pearl')+' &middot; '+(entry.timestamp||'')+'</p>'+
      '<div class="reader-actions">'+bookmarkBtnHTML(pbmRef)+'</div>'+
      navRow;
    document.body.classList.add('reader-open');
    pushReaderState();
    return;
  }}

  // Paper
  body.innerHTML = '<div class="reader-loading"><p>&#128270; Loading summary&hellip;</p></div>';
  document.body.classList.add('reader-open');
  pushReaderState();

  var file_name = encodeURIComponent(entry.file_name || '');
  var system = encodeURIComponent(entry.system || 'General');
  var type = encodeURIComponent(entry.type || 'Other');
  fetch('/api/summary?file_name='+file_name+'&system='+system+'&type='+type)
    .then(function(r){{ return r.json(); }})
    .then(function(data){{
      if(data.error){{ body.innerHTML = '<div class="reader-loading"><p>&#9888;&#65039; Could not load summary.</p></div>'; return; }}
      var content = data.content || '';
      var authors = data.authors || 'Unknown Authors';
      var doiHTML = (entry.doi && entry.doi!=='#') ? '<a href="'+entry.doi+'" target="_blank" class="btn" style="font-size:.76rem;padding:5px 10px;display:inline-block;border:1px solid var(--border);border-radius:6px;">&#128279; Source</a>' : '';
      var rendered = marked.parse(content);
      var collapsible = makeCollapsible(rendered);

      // Build evidence rows from recommendations if present
      var evidenceHTML = '';
      if(data.recommendations && data.recommendations.length) {{
        evidenceHTML = '<h4 class="evidence-head">Key evidence</h4>';
        data.recommendations.forEach(function(block){{
          if(block.recommendations) {{
            block.recommendations.forEach(function(rec){{
              var stat = rec.strength ? rec.strength : '';
              if(rec.evidence_grade) stat = stat + (stat ? ' ' : '') + rec.evidence_grade;
              var label = rec.statement ? rec.statement : '';
              if(rec.rec_id) label = '['+rec.rec_id+'] '+label;
              evidenceHTML += '<div class="evidence-row"><div class="evidence-statement">'+marked.parse(label)+'</div>'+(stat?'<div class="evidence-stat">'+escapeHtml(stat)+'</div>':'')+'</div>';
            }});
          }}
        }});
      }}

      // Build pearl box
      var pearlBoxHTML = '';
      if(data.key_pearls && data.key_pearls.length) {{
        pearlBoxHTML = '<div class="pearl-box"><strong>Key pearl &mdash;</strong> '+escapeHtml(data.key_pearls[0])+'</div>';
      }}

      var bmKind = (entry.type||'').toLowerCase()==='guideline' ? 'guideline' : 'paper';
      var bmRef = bmKind + ':' + (entry.file_name || '');
      registerBookmarkMeta(bmRef, {{kind: bmKind, title: entry.title, system: entry.system || 'General', type: entry.type || 'Other', locator: {{file_name: entry.file_name || '', system: entry.system || 'General', type: entry.type || 'Other'}}}});
      body.innerHTML = ''+
        pillHTML(entry.system, entry.system+' &middot; '+entry.type)+
        '<h2>'+escapeHtml(entry.title)+'</h2>'+
        '<p class="meta">'+(authors!=='Unknown Authors'?'&mdash; '+escapeHtml(authors)+' &middot; ':'')+ (entry.journal||'')+'</p>'+
        '<div class="reader-actions">'+doiHTML+bookmarkBtnHTML(bmRef)+exportPaperBtnHTML(entry)+'</div>'+
        pearlBoxHTML+
        collapsible+
        evidenceHTML;
      katexify(body);
    }})
    .catch(function(){{
      body.innerHTML = '<div class="reader-loading"><p>&#10060; Network error.</p></div>';
    }});
}}

function closeReader(){{ document.body.classList.remove('reader-open'); }}

var _readerStatePushed = false;
function pushReaderState(){{ _readerStatePushed = true; history.pushState(null, ''); }}

function makeCollapsible(html){{
  var parts = html.split(/(<h2[^>]*>[\\s\\S]*?<\\/h2>)/i);
  if(parts.length<2) return html;
  var r = ''; if(parts[0].trim()) r += '<div>'+parts[0]+'</div>';
  var first = true;
  for(var i=1;i<parts.length;i+=2){{
    var h = parts[i], c = parts[i+1]||'', m = h.match(/>([^<]*)</), t = m ? m[1] : 'Section';
    r += '<details class="summary-section"'+(first?' open':'')+'><summary class="summary-heading">'+t+'</summary><div class="summary-content">'+c.replace(h,'')+'</div></details>';
    first = false;
  }}
  return r;
}}

// =====================================================================
// SEARCH OVERLAY
// =====================================================================
function openSearch(){{
  document.body.classList.add('search-open');
  var input = document.getElementById('globalSearchInput');
  input.value = '';
  renderSearchResults('');
  setTimeout(function(){{ input.focus(); }}, 60);
}}
function closeSearch(){{ document.body.classList.remove('search-open'); }}
function renderSearchResults(qRaw){{
  var q = (qRaw||'').toLowerCase().trim();
  var box = document.getElementById('searchResults');
  if(q===''){{ box.innerHTML = '<div class="search-empty">Try &ldquo;troponin&rdquo;, &ldquo;pip-tazo&rdquo;, &ldquo;KDIGO&rdquo;, or a specialty name.</div>'; return; }}
  var pMatches = baseDataset.filter(function(p){{ return p.title.toLowerCase().indexOf(q)!==-1; }}).slice(0,5);
  var plMatches = allPearls.filter(function(p){{ return (p.pearl||'').toLowerCase().indexOf(q)!==-1; }}).slice(0,5);
  var ctMatches = CONDENSED_INDEX.filter(function(t){{
    return t.trial_name.toLowerCase().indexOf(q)!==-1
        || (t.one_liner||'').toLowerCase().indexOf(q)!==-1
        || (t.keywords_str||'').toLowerCase().indexOf(q)!==-1
        || t.system.toLowerCase().indexOf(q)!==-1;
  }}).slice(0,5);
  var esMatches = TRIAL_INDEX.filter(function(t){{
    return (t.trial_name||'').toLowerCase().indexOf(q)!==-1
        || (t.one_liner||'').toLowerCase().indexOf(q)!==-1
        || (t.specialty||'').toLowerCase().indexOf(q)!==-1;
  }}).slice(0,5);
  var fcMatches = [];
  var theoryCardsSearched = 0;
  allFlashcardDecks.forEach(function(d){{
    d.cards.forEach(function(c){{
      var hay = (c.subtopic+' '+(c.front||'')+' '+(c.back||'')+' '+(c.tags||[]).join(' ')+' '+d.specialty+' '+d.title).toLowerCase();
      if(hay.indexOf(q)!==-1 && theoryCardsSearched<6){{
        theoryCardsSearched++;
        fcMatches.push({{cardId: c.id, deckId: d.id, label: (c.front||c.subtopic||c.id).substring(0,90), system: d.specialty}});
      }}
    }});
  }});
  var ntMatches = THEORY_NOTES.filter(function(n){{
    return (n.title+' '+n.md).toLowerCase().indexOf(q)!==-1;
  }}).slice(0,5);
  var total = pMatches.length + plMatches.length + ctMatches.length + esMatches.length + fcMatches.length + ntMatches.length;
  if(!total){{ box.innerHTML = '<div class="search-empty">No results for &ldquo;'+qRaw+'&rdquo;.</div>'; return; }}
  var html = '';
  if(pMatches.length) html += '<div class="search-group-label">Papers &amp; guidelines ('+pMatches.length+')</div>' + pMatches.map(function(p){{ return '<button class="search-result" data-open-paper="'+p.id+'" data-close-search>'+escapeHtml(p.title)+'</button>'; }}).join('');
  if(plMatches.length) html += '<div class="search-group-label">Pearls ('+plMatches.length+')</div>' + plMatches.map(function(p){{ return '<button class="search-result" data-open-pearl="'+p.id+'" data-close-search>'+escapeHtml((p.pearl||'').substring(0,80))+'</button>'; }}).join('');
  if(ctMatches.length) html += '<div class="search-group-label">Core Critical Care Trials ('+ctMatches.length+')</div>' + ctMatches.map(function(t){{ return '<button class="search-result" data-open-condensed="'+t.system+'/'+t.name+'" data-close-search>'+escapeHtml(t.trial_name)+'</button>'; }}).join('');
  if(esMatches.length) html += '<div class="search-group-label">ESBICM Landmark Trials ('+esMatches.length+')</div>' + esMatches.map(function(t){{ return '<button class="search-result" data-open-trial="'+t.slug+'" data-close-search>'+escapeHtml(t.trial_name||'')+' &middot; '+escapeHtml(t.specialty||'')+'</button>'; }}).join('');
  if(fcMatches.length) html += '<div class="search-group-label">Flashcards ('+fcMatches.length+')</div>' + fcMatches.map(function(f){{ return '<button class="search-result" data-theory-card="'+f.cardId+'" data-close-search>'+escapeHtml(f.label)+' &middot; '+escapeHtml(f.system)+'</button>'; }}).join('');
  if(ntMatches.length) html += '<div class="search-group-label">Theory Topics ('+ntMatches.length+')</div>' + ntMatches.map(function(n){{ return '<button class="search-result" data-theory-note="'+escapeHtml(n.id)+'" data-close-search>'+escapeHtml(n.title)+'</button>'; }}).join('');
  box.innerHTML = html;
}}

// =====================================================================
// DRAWER / SHEET
// =====================================================================
function openDrawer(){{ document.body.classList.add('drawer-open'); }}
function closeDrawer(){{ document.body.classList.remove('drawer-open'); }}
function openSheet(){{ document.body.classList.add('sheet-open'); }}
function closeSheet(){{ document.body.classList.remove('sheet-open'); }}

// =====================================================================
// THEME / FONT
// =====================================================================
var THEMES = ['light','dim','dark'];
var THEME_GLYPH = {{light:'&#9728;', dim:'&#9712;', dark:'&#9790;'}};
function setTheme(t){{
  document.documentElement.setAttribute('data-theme', t);
  var tb = document.getElementById('themeBtn');
  if(tb) tb.innerHTML = THEME_GLYPH[t] || '&#9712;';
  document.querySelectorAll('#themeChips .chip').forEach(function(c){{ c.classList.toggle('active', c.dataset.themeChoice===t); }});
  try {{ localStorage.setItem('hackccm_theme', t); }} catch(e){{}}
}}
function setSiteFontSize(px){{
  document.body.style.setProperty('--site-fs', px + 'px');
  document.querySelectorAll('#fontChips .chip').forEach(function(c){{ c.classList.toggle('active', c.dataset.fontPx===String(px)); }});
  try {{ localStorage.setItem('hackccm_fontSize', String(px)); }} catch(e){{}}
}}
function showToast(msg){{
  var t = document.getElementById('toast');
  t.innerHTML = msg;
  t.classList.add('show');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(function(){{ t.classList.remove('show'); }}, 2400);
}}

function escapeHtml(str){{
  if(!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

function capitalizeFirst(str){{
  if(!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}}

function renderListItem(v){{
  if(typeof v === 'string') return '<li>'+escapeHtml(v)+'</li>';
  if(v && typeof v === 'object'){{
    if(v.domain && v.notes) return '<li><strong>'+escapeHtml(v.domain)+':</strong> '+escapeHtml(v.notes)+'</li>';
    if(v.topic && v.notes) return '<li><strong>'+escapeHtml(v.topic)+':</strong> '+escapeHtml(v.notes)+'</li>';
    if(v.trial && v.relation) return '<li><strong>'+escapeHtml(v.trial)+':</strong> '+escapeHtml(v.relation)+'</li>';
    return '<li>'+escapeHtml(JSON.stringify(v))+'</li>';
  }}
  return '<li>'+escapeHtml(String(v))+'</li>';
}}

// =====================================================================
// TRIALS
// =====================================================================
function renderTrials(){{
  // My Trials placeholder is static HTML
  // ESBICM hero card is static HTML
}}

function renderESBICM(){{
  var container = document.getElementById('trialsEsbicmResults');
  var spec = document.getElementById('trialFilterSpecialty').value;
  var res = document.getElementById('trialFilterResult').value;
  var typ = document.getElementById('trialFilterType').value;
  var hasFilter = spec || res || typ;

  if(!hasFilter){{
    // Show specialty grid
    var html = '<div class="trials-spec-grid">';
    TRIAL_SPECS.forEach(function(s){{
      var c = TRIAL_SPEC_COUNTS[s] || 0;
      var v = TRIAL_SPEC_VAR[s] || '--tspec-general';
      html += '<button class="trials-spec-tile" style="--tile-color:var('+v+')" data-trial-spec="'+s+'" role="button">'+
        '<div class="dot" style="background:var('+v+')"></div>'+
        '<div style="font-weight:700;font-size:.9rem">'+s+'</div>'+
        '<div class="count">'+c+' trial'+(c!==1?'s':'')+'</div>'+
        '</button>';
    }});
    html += '</div>';
    container.innerHTML = html;
    return;
  }}

  // Filtered: fetch from API
  var params = new URLSearchParams({{specialty:spec, result_category:res, trial_type:typ, page:1, limit:300}});
  fetch('/api/trials?'+params.toString())
    .then(function(r){{ return r.json(); }})
    .then(function(data){{
      var list = data.trials || [];
      _currentTrialList = list;
      if(!list.length){{
        container.innerHTML = '<div class="trial-empty"><span class="icon">&#128270;</span><p style="color:var(--ink-muted)">No trials match your filters.</p></div>';
        return;
      }}
      var html = '<p style="font-size:.82rem;color:var(--ink-muted);margin-bottom:10px">'+list.length+' trial'+(list.length!==1?'s':'')+' found</p>';
      list.forEach(function(t, i){{
        html += renderTrialCard(t, i);
      }});
      container.innerHTML = html;
    }});
}}

function renderTrialCard(t, idx){{
  var resClass = (t.result_category||'').toLowerCase().replace(/[^a-z]/g,'');
  var resColor = 'neu';
  if(resClass.indexOf('pos')>=0) resColor = 'pos';
  else if(resClass.indexOf('neg')>=0 && resClass.indexOf('neu')>=0) resColor = 'negneu';
  else if(resClass.indexOf('neg')>=0) resColor = 'neg';
  return '<div class="trial-card" data-open-trial="'+t.slug+'" data-idx="'+idx+'" role="button" tabindex="0">'+
    '<h4>'+escapeHtml(t.trial_name)+'</h4>'+
    '<p class="one-liner">'+escapeHtml(t.one_liner||'')+'</p>'+
    '<div class="meta-row">'+
      '<span class="badge">'+escapeHtml(t.trial_type||'')+'</span>'+
      '<span class="result-badge '+resColor+'">'+escapeHtml(t.result_category||'')+'</span>'+
      (t.sample_size ? '<span class="badge">n='+t.sample_size+'</span>' : '')+
      '<span class="badge">'+t.year+'</span>'+
    '</div>'+
    '</div>';
}}

function renderTrialsSpecialty(name){{
  showView('trials-specialty');
  document.getElementById('trialsSpecTitle').textContent = name;
  var dot = document.getElementById('trialsSpecDot');
  var v = TRIAL_SPEC_VAR[name] || '--tspec-general';
  dot.style.background = 'var('+v+')';

  // Subtopic chips
  var sts = TRIAL_SUBTOPIC_MAP[name] || ['General'];
  var chipHtml = '<button class="subtopic-chip active" data-st="">All</button>';
  sts.forEach(function(st){{
    chipHtml += '<button class="subtopic-chip" data-st="'+escapeHtml(st)+'">'+escapeHtml(st)+'</button>';
  }});
  document.getElementById('trialsSubtopicChips').innerHTML = chipHtml;

  // Back button
  document.getElementById('trialsSpecBackBtn').onclick = function(){{ showView('trials-esbicm'); }};

  _filterTrialsBySpecialty(name, '');
}}

function _filterTrialsBySpecialty(name, subtopic){{
  var filtered = TRIAL_INDEX.filter(function(t){{
    if(t.specialty !== name) return false;
    if(subtopic && t.subtopic !== subtopic) return false;
    return true;
  }});
  _currentTrialList = filtered;
  var html = '';
  filtered.forEach(function(t, i){{
    html += renderTrialCard(t, i, filtered);
  }});
  if(!html) html = '<div class="trial-empty"><span class="icon">&#128270;</span><p style="color:var(--ink-muted)">No trials in this category.</p></div>';
  document.getElementById('trialsSpecList').innerHTML = html;
}}

function openTrialDetail(slug, list, idx){{
  showView('trial-detail');
  _currentTrialList = list || [];
  _currentTrialIdx = typeof idx === 'number' ? idx : -1;
  _currentTrialSlug = slug || '';

  var body = document.getElementById('trialDetailBody');
  body.innerHTML = '<div style="text-align:center;padding:40px;color:var(--ink-muted)">Loading&hellip;</div>';

  fetch('/api/trial/'+slug)
    .then(function(r){{ return r.json(); }})
    .then(function(data){{
      if(data.error){{ body.innerHTML = '<div class="trial-empty"><span class="icon">&#9888;</span><p>Could not load trial.</p></div>'; return; }}
      renderTrialDetailHTML(data, body);
    }});
}}

function renderTrialDetailHTML(data, body){{
  // Credits bar
  var html = '<div class="trial-credits-bar">'+
    '<span class="trophy">&#127942;</span>'+
    '<span>Data sourced from <strong>ESBICM Trials Database</strong></span>'+
    '<span class="spacer"></span>'+
    '<button class="icon-btn-sm" onclick="openTrialOverlay(&#x27;trialCreditsOverlay&#x27;,&#x27;credits&#x27;)">&#127942; Credits</button>'+
    '<button class="icon-btn-sm" onclick="openTrialOverlay(&#x27;trialDisclaimerOverlay&#x27;,&#x27;disclaimer&#x27;)">&#8505;&#65039;</button>'+
    '</div>';

  // Title + journal
  html += '<h1>'+escapeHtml(data.trial_name || data.trial_title || '')+'</h1>';
  html += '<div class="trial-journal">';
  if(data.journal) html += escapeHtml(data.journal);
  if(data.year) html += ' &middot; '+data.year;
  if(data.doi){{
    var doiUrl = data.doi;
    if(doiUrl && doiUrl!=='#' && !doiUrl.startsWith('http')) doiUrl = 'https://doi.org/'+doiUrl;
    if(doiUrl && doiUrl!=='#') html += ' &middot; <a href="'+doiUrl+'" target="_blank" rel="noopener" style="color:var(--accent)">&#128279; DOI</a>';
  }}
  html += '</div>';
  registerBookmarkMeta('trial:'+_currentTrialSlug, {{kind: 'trial', title: data.trial_name || data.trial_title || '', system: data.specialty || 'General', type: data.trial_type || '', locator: {{slug: _currentTrialSlug}}}});
  html += '<div class="reader-actions" style="margin-top:10px">'+bookmarkBtnHTML('trial:'+_currentTrialSlug)+'</div>';

  // Meta strip
  html += '<div class="trial-meta-strip">';
  if(data.trial_type) html += '<span class="badge">'+escapeHtml(data.trial_type)+'</span>';
  if(data.result_category){{
    var rc = data.result_category.toLowerCase().replace(/[^a-z]/g,'');
    var rcls = 'neu';
    if(rc.indexOf('pos')>=0) rcls = 'pos';
    else if(rc.indexOf('neg')>=0 && rc.indexOf('neu')>=0) rcls = 'negneu';
    else if(rc.indexOf('neg')>=0) rcls = 'neg';
    html += '<span class="result-badge '+rcls+'">'+escapeHtml(data.result_category)+'</span>';
  }}
  if(data.sample_size) html += '<span class="badge">n='+data.sample_size+'</span>';
  if(data.evidence_level) html += '<span class="badge">&#11088; '+escapeHtml(data.evidence_level)+'</span>';
  html += '</div>';

  // One-liner
  if(data.one_liner) html += '<div class="trial-one-liner">'+escapeHtml(data.one_liner)+'</div>';

  // Sections as collapsible
  if(data.sections && data.sections.length){{
    data.sections.forEach(function(s){{
      var secContent = preprocessTrialContent(s.content || '');
      var secHtml = '<div class="trial-section"><details'+(s.id<=2?' open':'')+'><summary>'+escapeHtml(s.heading||'')+'</summary><div class="section-body">';
      if (typeof marked !== 'undefined' && marked.parse) {{
        secHtml += marked.parse(secContent);
      }} else {{
        secHtml += '<p>'+secContent.replace(/\\n/g, '<br>')+'</p>';
      }}
      secHtml += '</div></details></div>';
      html += secHtml;
    }});
  }}

  // Prev/Next nav
  html += '<div class="trial-nav-bar">';
  if(_currentTrialIdx > 0 && _currentTrialList.length){{
    var prev = _currentTrialList[_currentTrialIdx - 1];
    html += '<button class="btn nav-btn" onclick="openTrialDetail(&#x27;'+prev.slug+'&#x27;,_currentTrialList,'+(_currentTrialIdx-1)+')">&larr; '+escapeHtml(prev.toc_name||'Previous')+'</button>';
  }}
  if(_currentTrialIdx >= 0 && _currentTrialIdx < _currentTrialList.length - 1){{
    var next = _currentTrialList[_currentTrialIdx + 1];
    html += '<button class="btn nav-btn" onclick="openTrialDetail(&#x27;'+next.slug+'&#x27;,_currentTrialList,'+(_currentTrialIdx+1)+')">'+escapeHtml(next.toc_name||'Next')+' &rarr;</button>';
  }}
  html += '</div>';

  body.innerHTML = html;
  katexify(body);
}}

function preprocessTrialContent(text){{
  if(!text) return '';
  // Convert bullet characters to markdown list syntax
  var out = text.replace(/^\u2022\\s*/gm, '- ').replace(/^o\\s+/gm, '  - ');
  return out;
}}

function filterTrials(){{
  renderESBICM();
}}

function clearTrialFilters(){{
  document.getElementById('trialFilterSpecialty').value = '';
  document.getElementById('trialFilterResult').value = '';
  document.getElementById('trialFilterType').value = '';
  renderESBICM();
}}

function openTrialOverlay(id, kind){{
  document.getElementById(id).style.display = 'flex';
  if(kind==='credits'){{
    var md = `{CREDITS_TEXT.replace('`','\\`').replace('$','\\$')}`;
    var html = md.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>').replace(/\\n\\n/g, '</p><p>').replace(/\\n/g, '<br>');
    document.getElementById('trialCreditsText').innerHTML = '<p>'+html+'</p>';
  }}
  if(kind==='disclaimer'){{
    var md = `{TRIAL_DISCLAIMER_TEXT.replace('`','\\`').replace('$','\\$')}`;
    var html = md.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>').replace(/\\n\\n/g, '</p><p>').replace(/\\n/g, '<br>');
    document.getElementById('trialDisclaimerText').innerHTML = '<p>'+html+'</p>';
  }}
}}

function closeTrialOverlay(id){{
  document.getElementById(id).style.display = 'none';
}}

// =====================================================================
// CONDENSED TRIALS
// =====================================================================

function renderCondensedTrials(){{
  var container = document.getElementById('condensedTrialsContent');
  var spec = document.getElementById('condensedFilterSpecialty').value;
  var res = document.getElementById('condensedFilterResult').value;
  var typ = document.getElementById('condensedFilterType').value;
  var hasFilter = spec || res || typ;

  if(!hasFilter){{
    // Show specialty grid
    var html = '<div class="trials-spec-grid">';
    CONDENSED_SYSTEMS.forEach(function(s){{
      var count = CONDENSED_INDEX.filter(function(t){{ return t.system === s; }}).length;
      var v = TRIAL_SPEC_VAR[s] || '--tspec-general';
      html += '<button class="trials-spec-tile" style="--tile-color:var('+v+')" data-condensed-spec="'+s+'" role="button">'+
        '<div class="dot" style="background:var('+v+')"></div>'+
        '<div style="font-weight:700;font-size:.9rem">'+s+'</div>'+
        '<div class="count">'+count+' trial'+(count!==1?'s':'')+'</div>'+
        '</button>';
    }});
    html += '</div>';
    container.innerHTML = html;
    return;
  }}

  // Filtered: show trial cards sorted by year descending
  var filtered = CONDENSED_INDEX.filter(function(t){{
    if(spec && t.system !== spec) return false;
    if(res && t.result_category !== res) return false;
    if(typ && t.trial_type !== typ) return false;
    return true;
  }}).sort(function(a,b){{ return (b.year||0) - (a.year||0); }});
  if(!filtered.length){{
    container.innerHTML = '<div class="trial-empty"><span class="icon">&#128270;</span><p style="color:var(--ink-muted)">No trials match your filters.</p></div>';
    return;
  }}
  var html = '<p style="font-size:.82rem;color:var(--ink-muted);margin-bottom:10px">'+filtered.length+' trial'+(filtered.length!==1?'s':'')+' found</p>';
  filtered.forEach(function(t, i){{
    var resClass = (t.result_category||'').toLowerCase().replace(/[^a-z]/g,'');
    var resColor = 'neu';
    if(resClass.indexOf('pos')>=0) resColor = 'pos';
    else if(resClass.indexOf('neg')>=0 && resClass.indexOf('neu')>=0) resColor = 'negneu';
    else if(resClass.indexOf('neg')>=0) resColor = 'neg';
    html += '<div class="trial-card" data-open-condensed="'+t.system+'/'+t.name+'" data-idx="'+i+'" role="button" tabindex="0">'+
      '<h4>'+escapeHtml(t.trial_name || t.name.replace(/_/g,' '))+'</h4>'+
      '<p class="one-liner">'+escapeHtml(t.one_liner||'')+'</p>'+
      '<div class="meta-row">'+
        (t.trial_type ? '<span class="badge">'+escapeHtml(t.trial_type)+'</span>' : '')+
        (t.result_category ? '<span class="result-badge '+resColor+'">'+escapeHtml(t.result_category)+'</span>' : '')+
        (t.sample_size ? '<span class="badge">n='+t.sample_size+'</span>' : '')+
        (t.year ? '<span class="badge">'+t.year+'</span>' : '')+
      '</div>'+
      '</div>';
  }});
  container.innerHTML = html;
}}

function filterCondensed(){{
  renderCondensedTrials();
}}

function clearCondensedFilters(){{
  document.getElementById('condensedFilterSpecialty').value = '';
  document.getElementById('condensedFilterResult').value = '';
  document.getElementById('condensedFilterType').value = '';
  renderCondensedTrials();
}}

function renderCondensedSystem(name){{
  showView('condensed-system');
  document.getElementById('condensedSysTitle').textContent = name;
  var trials = CONDENSED_INDEX.filter(function(t){{ return t.system === name; }}).sort(function(a,b){{ return (b.year||0) - (a.year||0); }});
  var html = '';
  trials.forEach(function(t, i){{
    var resClass = (t.result_category||'').toLowerCase().replace(/[^a-z]/g,'');
    var resColor = 'neu';
    if(resClass.indexOf('pos')>=0) resColor = 'pos';
    else if(resClass.indexOf('neg')>=0 && resClass.indexOf('neu')>=0) resColor = 'negneu';
    else if(resClass.indexOf('neg')>=0) resColor = 'neg';
    html += '<div class="trial-card" data-open-condensed="'+t.system+'/'+t.name+'" data-idx="'+i+'" role="button" tabindex="0">'+
      '<h4>'+escapeHtml(t.trial_name || t.name.replace(/_/g,' '))+'</h4>'+
      '<p class="one-liner">'+escapeHtml(t.one_liner||'')+'</p>'+
      '<div class="meta-row">'+
        (t.trial_type ? '<span class="badge">'+escapeHtml(t.trial_type)+'</span>' : '')+
        (t.result_category ? '<span class="result-badge '+resColor+'">'+escapeHtml(t.result_category)+'</span>' : '')+
        (t.sample_size ? '<span class="badge">n='+t.sample_size+'</span>' : '')+
        (t.year ? '<span class="badge">'+t.year+'</span>' : '')+
      '</div>'+
      '</div>';
  }});
  if(!html) html = '<div class="trial-empty"><span class="icon">&#128270;</span><p style="color:var(--ink-muted)">No trials in this category.</p></div>';
  document.getElementById('condensedSysList').innerHTML = html;
}}

function openCondensedTrialDetail(system, name){{
  showView('condensed-detail');
  _currentCondensedRef = 'condensed:' + system + ':' + name;
  var body = document.getElementById('condensedDetailBody');
  body.innerHTML = '<div style="text-align:center;padding:40px;color:var(--ink-muted)">Loading&hellip;</div>';
  document.getElementById('condensedDetailBackBtn').onclick = function(){{ renderCondensedSystem(system); }};
  fetch('/api/condensed-trial/'+encodeURIComponent(system)+'/'+encodeURIComponent(name))
    .then(function(r){{ return r.json(); }})
    .then(function(data){{
      if(data.error){{ body.innerHTML = '<div class="trial-empty"><span class="icon">&#9888;</span><p>Could not load trial.</p></div>'; return; }}
      renderCondensedDetailHTML(data, body);
    }});
}}

function renderCondensedDetailHTML(data, body){{
  var html = '';

  // Title + journal
  html += '<h1>'+escapeHtml(data.trial_name || '')+'</h1>';
  html += '<div class="trial-journal">';
  if(data.journal) html += escapeHtml(data.journal);
  if(data.year) html += ' &middot; '+data.year;
  if(data.doi){{
    var doiUrl = data.doi;
    if(doiUrl && doiUrl!=='#' && !doiUrl.startsWith('http')) doiUrl = 'https://doi.org/'+doiUrl;
    if(doiUrl && doiUrl!=='#') html += ' &middot; <a href="'+doiUrl+'" target="_blank" rel="noopener" style="color:var(--accent)">&#128279; DOI</a>';
  }}
  html += '</div>';
  var cparts = String(_currentCondensedRef).split(':');
  var cSys = cparts[1] || 'General';
  var cName = cparts[2] || '';
  registerBookmarkMeta(_currentCondensedRef, {{kind: 'condensed', title: data.trial_name || '', system: cSys, type: data.trial_type || '', locator: {{system: cSys, name: cName}}}});
  html += '<div class="reader-actions" style="margin-top:10px">'+bookmarkBtnHTML(_currentCondensedRef)+'</div>';

  // Meta strip
  html += '<div class="trial-meta-strip">';
  if(data.trial_type) html += '<span class="badge">'+escapeHtml(data.trial_type)+'</span>';
  if(data.result_category){{
    var rc = data.result_category.toLowerCase().replace(/[^a-z]/g,'');
    var rcls = 'neu';
    if(rc.indexOf('pos')>=0) rcls = 'pos';
    else if(rc.indexOf('neg')>=0 && rc.indexOf('neu')>=0) rcls = 'negneu';
    else if(rc.indexOf('neg')>=0) rcls = 'neg';
    html += '<span class="result-badge '+rcls+'">'+escapeHtml(data.result_category)+'</span>';
  }}
  if(data.sample_size) html += '<span class="badge">n='+data.sample_size+'</span>';
  if(data.evidence_level) html += '<span class="badge">&#11088; '+escapeHtml(data.evidence_level)+'</span>';
  html += '</div>';

  // One-liner
  if(data.one_liner) html += '<div class="trial-one-liner">'+escapeHtml(data.one_liner)+'</div>';

  var sec = data.sections || {{}};

  // PICO card
  if(data.pico){{
    html += '<div class="trial-section"><details open><summary>PICO</summary><div class="section-body"><table class="pico-table"><tr><th>Population</th><td>'+escapeHtml(data.pico.population||'')+'</td></tr><tr><th>Intervention</th><td>'+escapeHtml(data.pico.intervention||'')+'</td></tr><tr><th>Comparison</th><td>'+escapeHtml(data.pico.comparison||'')+'</td></tr><tr><th>Outcome</th><td>'+escapeHtml(data.pico.outcome||'')+'</td></tr></table></div></details></div>';
  }}

  // Quick recall box
  if(sec.quick_recall){{
    var qr = sec.quick_recall;
    html += '<div class="quick-recall-box">'+
      '<div class="qr-title">&#128161; Quick Recall</div>'+
      '<div class="qr-numbers">';
    if(qr.numbers_to_remember){{
      qr.numbers_to_remember.forEach(function(n){{ html += '<div class="qr-num">'+escapeHtml(n)+'</div>'; }});
    }}
    html += '</div>';
    if(qr.one_line_takeaway) html += '<div class="qr-takeaway">'+escapeHtml(qr.one_line_takeaway)+'</div>';
    html += '</div>';
  }}

  // Clinical Summary (renamed from clinical_bottom_line)
  if(sec.clinical_bottom_line){{
    var cbl = sec.clinical_bottom_line;
    html += '<div class="trial-section"><details open><summary>Clinical Summary</summary><div class="section-body">';
    if(cbl.verdict) html += '<p><strong>Verdict:</strong> '+escapeHtml(cbl.verdict)+'</p>';
    if(cbl.applies_to) html += '<p><strong>Applies to:</strong> '+escapeHtml(cbl.applies_to)+'</p>';
    if(cbl.does_not_mean) html += '<p><strong>Does not mean:</strong> '+escapeHtml(cbl.does_not_mean)+'</p>';
    if(cbl.implementation_caveats && cbl.implementation_caveats.length){{
      html += '<p><strong>Implementation caveats:</strong></p><ul>';
      cbl.implementation_caveats.forEach(function(c){{ html += '<li>'+escapeHtml(c)+'</li>'; }});
      html += '</ul>';
    }}
    html += '</div></details></div>';
  }}

  // Critical Appraisal
  if(sec.critical_appraisal){{
    var ca = sec.critical_appraisal;
    html += '<div class="trial-section"><details open><summary>Critical Appraisal</summary><div class="section-body">';
    if(ca.summary) html += '<p><strong>Summary:</strong> '+escapeHtml(ca.summary)+'</p>';
    if(ca.rating) html += '<p><strong>Rating:</strong> <span class="badge">'+escapeHtml(ca.rating)+'</span></p>';
    if(ca.strengths && ca.strengths.length){{
      html += '<p><strong>Strengths:</strong></p><ul>';
      ca.strengths.forEach(function(s){{ html += '<li>'+escapeHtml(s)+'</li>'; }});
      html += '</ul>';
    }}
    if(ca.weaknesses && ca.weaknesses.length){{
      html += '<p><strong>Weaknesses:</strong></p><ul>';
      ca.weaknesses.forEach(function(w){{ html += '<li>'+escapeHtml(w)+'</li>'; }});
      html += '</ul>';
    }}
    html += '</div></details></div>';
  }}

  // Outcomes table
  if(sec.results && sec.results.outcomes_table && sec.results.outcomes_table.length){{
    html += '<div class="trial-section"><details open><summary>Outcomes</summary><div class="section-body"><div style="overflow-x:auto"><table class="outcomes-table"><thead><tr><th>Outcome</th><th>Intervention</th><th>Control</th><th>Measure</th><th>Value</th><th>95% CI</th><th>P</th><th>Note</th></tr></thead><tbody>';
    sec.results.outcomes_table.forEach(function(r){{
      html += '<tr><td>'+escapeHtml(r.outcome||'')+'</td><td>'+escapeHtml(r.group_a||'')+'</td><td>'+escapeHtml(r.group_b||'')+'</td><td>'+escapeHtml(r.effect_measure||'')+'</td><td>'+escapeHtml(r.effect_value||'')+'</td><td>'+escapeHtml(r.ci_95||'')+'</td><td>'+escapeHtml(r.p_value||'')+'</td><td>'+escapeHtml(r.note||'')+'</td></tr>';
    }});
    html += '</tbody></table></div></div></details></div>';
  }}

  // Subgroup table
  if(sec.results && sec.results.subgroup_table && sec.results.subgroup_table.length){{
    html += '<div class="trial-section"><details><summary>Subgroup Analyses</summary><div class="section-body"><div style="overflow-x:auto"><table class="outcomes-table"><thead><tr><th>Subgroup</th><th>Intervention</th><th>Control</th><th>Measure</th><th>Value</th><th>95% CI</th><th>P-interaction</th></tr></thead><tbody>';
    sec.results.subgroup_table.forEach(function(r){{
      html += '<tr><td>'+escapeHtml(r.subgroup||'')+'</td><td>'+escapeHtml(r.group_a||'')+'</td><td>'+escapeHtml(r.group_b||'')+'</td><td>'+escapeHtml(r.effect_measure||'')+'</td><td>'+escapeHtml(r.effect_value||'')+'</td><td>'+escapeHtml(r.ci_95||'')+'</td><td>'+escapeHtml(r.p_interaction||'')+'</td></tr>';
    }});
    html += '</tbody></table></div></div></details></div>';
  }}

  // Collapsible: background, methods, internal/external validity, strengths, limitations, etc.
  var collapsibleSections = [
    {{key:'background', label:'Background &amp; Hypothesis'}},
    {{key:'methods', label:'Methods'}},
    {{key:'internal_validity', label:'Internal Validity'}},
    {{key:'external_validity', label:'External Validity'}},
    {{key:'safety', label:'Safety'}},
    {{key:'strengths', label:'Strengths'}},
    {{key:'limitations', label:'Limitations'}},
    {{key:'authors_conclusion', label:"Authors' Conclusion"}},
    {{key:'controversies', label:'Controversies'}},
    {{key:'context_related_trials', label:'Related Trials'}},
    {{key:'unresolved_questions', label:'Unresolved Questions'}},
  ];

  collapsibleSections.forEach(function(cs){{
    var val = sec[cs.key];
    if(!val) return;
    var content = '';
    if(Array.isArray(val)){{
      content = '<ul>'+val.map(function(v){{
        if(typeof v === 'string') return '<li>'+escapeHtml(v)+'</li>';
        if(v.topic && v.notes) return '<li><strong>'+escapeHtml(v.topic)+':</strong> '+escapeHtml(v.notes)+'</li>';
        if(v.domain && v.notes) return '<li><strong>'+escapeHtml(v.domain)+':</strong> '+escapeHtml(v.notes)+'</li>';
        if(v.trial && v.relation) return '<li><strong>'+escapeHtml(v.trial)+':</strong> '+escapeHtml(v.relation)+'</li>';
        return '<li>'+escapeHtml(JSON.stringify(v))+'</li>';
      }}).join('')+'</ul>';
    }} else if(typeof val === 'object'){{
      var pairs = [];
      Object.keys(val).forEach(function(k){{
        var v = val[k];
        var label = capitalizeFirst(k.replace(/_/g,' '));
        if(Array.isArray(v)){{
          pairs.push('<p><strong>'+label+':</strong></p><ul>'+v.map(function(i){{ return renderListItem(i); }}).join('')+'</ul>');
        }} else if(typeof v === 'object'){{
          pairs.push('<p><strong>'+label+':</strong></p><ul>'+Object.keys(v).map(function(sk){{ return '<li><strong>'+capitalizeFirst(sk.replace(/_/g,' '))+':</strong> '+escapeHtml(v[sk])+'</li>'; }}).join('')+'</ul>');
        }} else {{
          pairs.push('<p><strong>'+label+':</strong> '+escapeHtml(v)+'</p>');
        }}
      }});
      content = pairs.join('');
    }} else {{
      content = '<p>'+escapeHtml(val)+'</p>';
    }}
    if(content) html += '<div class="trial-section"><details><summary>'+cs.label+'</summary><div class="section-body">'+content+'</div></details></div>';
  }});

  body.innerHTML = html;
  katexify(body);
}}

// =====================================================================
// THEORY FLASHCARDS
// =====================================================================
function _theorySpecVar(spec){{ return THEORY_SPEC_VAR[spec] || '--spec-other'; }}
function _theoryPill(spec, label){{
  var v = _theorySpecVar(spec);
  return '<span class="pill" style="background:color-mix(in srgb, var('+v+') 18%, transparent); color:var('+v+')"><span class="dot" style="background:var('+v+')"></span>'+escapeHtml(label)+'</span>';
}}
function _bmEnabled(){{ return USER_IS_ADMIN || USER_FEATURES['bookmarks']; }}
function _savedCardRefs(deckId){{
    // Bookmark refs are flashcard:<uuid>; match via the locator.deck stored on save
  return Object.keys(_bookmarks.items || {{}}).filter(function(r){{
    var it = _bookmarks.items[r];
    return it && it.locator && it.locator.deck === deckId;
  }});
}}
function theoryCardRef(deckId, cardId){{ return 'flashcard:'+cardId; }}
function theoryDeckFromCardId(cardId){{
  for(var i=0;i<allFlashcardDecks.length;i++){{
    for(var j=0;j<allFlashcardDecks[i].cards.length;j++){{
      if(allFlashcardDecks[i].cards[j].id === cardId) return {{deck: allFlashcardDecks[i], idx: j}};
    }}
  }}
  return null;
}}

// ---- Theory navigation helpers ----
function _theoryViewActive(){{ return !!(document.getElementById('view-theory') && document.getElementById('view-theory').classList.contains('active')); }}
function _theoryStudyVisible(){{ var el = document.getElementById('theoryStudy'); return !!(el && el.style.display!=='none'); }}

function theoryReset(){{
  _currentDeck = null;
  _currentTheoryNote = null;
  _theoryListCollapsed = false;
  _theoryStudyFromList = false;
  _notesActiveSpecs = new Set();
  _notesActiveSubtopic = null;
  var st = document.getElementById('theoryStudy'); if(st) st.style.display='none';
  var cl = document.getElementById('theoryCardList'); if(cl) cl.style.display='none';
  var br = document.getElementById('theoryBrowser'); if(br) br.style.display='';
  var rd = document.getElementById('theoryNoteReader'); if(rd){{ rd.style.display='none'; rd.innerHTML=''; }}
  var nl = document.getElementById('theoryNotesList'); if(nl) nl.style.display='';
  var nc = document.getElementById('theoryNotesCount'); if(nc) nc.style.display='';
  var sr = document.getElementById('theoryNotesSearchRow'); if(sr) sr.style.display='';
  var sc = document.getElementById('theoryNotesChips'); if(sc) sc.style.display='';
}}

function _focusCrumb(){{
  var bar = document.getElementById('theoryCrumbs');
  if(!bar) return;
  var t = bar.querySelector('button.crumb-current') || bar.querySelector('button[data-crumb]');
  if(t && t.focus){{ try{{ t.focus({{preventScroll:true}}); }} catch(e){{ t.focus(); }} }}
}}

function renderTheoryCrumbs(){{
  var bar = document.getElementById('theoryCrumbs');
  if(!bar) return;
  if(!_theoryMode){{ bar.style.display='none'; bar.innerHTML=''; return; }}
  var parts = ['<button class="crumb" data-crumb="0" title="Back to all theory">All theory</button>'];
  if(_theoryMode==='notes'){{
    parts.push('<span class="crumb-sep">&#8250;</span><button class="crumb'+( _currentTheoryNote?'':' crumb-current')+'" data-crumb="1" title="Back to notes list">Theory Topics</button>');
    if(_currentTheoryNote){{
      parts.push('<span class="crumb-sep">&#8250;</span><span class="crumb crumb-current crumb-title" title="'+escapeHtml(_currentTheoryNote.title)+'">'+escapeHtml(_currentTheoryNote.title)+'</span>');
    }}
  }} else {{
    parts.push('<span class="crumb-sep">&#8250;</span><button class="crumb'+( _currentDeck?'':' crumb-current')+'" data-crumb="1" title="Back to all decks">Flashcards</button>');
    if(_currentDeck){{
      var studying = _theoryStudyVisible();
      parts.push('<span class="crumb-sep">&#8250;</span><button class="crumb'+( studying?'':' crumb-current')+'" data-crumb="2" title="Card list">'+escapeHtml(_currentDeck.title)+'</button>');
      if(studying){{
        var posIdx = _theoryCardOrder.indexOf(_currentCardIdx); if(posIdx===-1) posIdx = 0;
        parts.push('<span class="crumb-sep">&#8250;</span><span class="crumb crumb-current">Card '+(posIdx+1)+' of '+_theoryCardOrder.length+'</span>');
      }}
    }}
  }}
  bar.innerHTML = parts.join('');
  bar.style.display = 'flex';
}}

function theoryGoTo(level){{
  if(_theoryMode==='notes'){{
    if(_currentTheoryNote && level<=1){{ theoryNotesBack(); return; }}
    if(level<=0){{ theoryBackToHero(); }}
    return;
  }}
  if(level<=0){{ theoryBackToHero(); return; }}
  if(level===1){{ theoryBackToBrowser(); return; }}
  if(level===2 && _currentDeck && _theoryStudyVisible()){{ theoryStudyToList(); }}
}}

function theoryStepBackFromStudy(){{
  if(_theoryStudyFromList && _currentDeck) theoryStudyToList();
  else theoryBackToBrowser();
}}

function _theoryHistoryURL(){{
  if(_theoryMode==='notes'){{
    var q = [];
    q.push('theory=notes');
    _notesActiveSpecs.forEach(function(s){{ q.push('nspec='+encodeURIComponent(s)); }});
    if(_notesActiveSubtopic) q.push('nsub='+encodeURIComponent(_notesActiveSubtopic));
    if(_notesSavedOnly) q.push('saved=1');
    if(_currentTheoryNote) q.push('note='+encodeURIComponent(_currentTheoryNote.id));
    else {{
      var nq = (document.getElementById('theoryNotesSearch').value||'').trim();
      if(nq) q.push('q='+encodeURIComponent(nq));
    }}
    return window.location.pathname+'?'+q.join('&');
  }}
  if(_theoryMode==='flashcards'){{
    var q = ['theory=flashcards'];
    if(_theorySavedOnly) q.push('saved=1');
    if(_currentDeck){{
      q.push('system='+encodeURIComponent(_currentDeck.specialty));
      if(_theoryActiveSubtopic) q.push('subtopic='+encodeURIComponent(_theoryActiveSubtopic));
      if(_theoryStudyVisible()){{
        var cur = _currentDeck.cards[_currentCardIdx];
        if(cur && cur.id) q.push('card='+encodeURIComponent(cur.id));
      }} else {{
        q.push('list=1');
        q.push('deck='+encodeURIComponent(_currentDeck.id));
      }}
    }} else {{
      if(_theoryActiveSpecs.size===1) q.push('system='+encodeURIComponent(Array.from(_theoryActiveSpecs)[0]));
      if(_theoryActiveSubtopic) q.push('subtopic='+encodeURIComponent(_theoryActiveSubtopic));
      var dq = (document.getElementById('theorySearch').value||'').trim();
      if(dq) q.push('q='+encodeURIComponent(dq));
    }}
    return window.location.pathname+'?'+q.join('&');
  }}
  return null;
}}

function _theoryPush(){{
  if(_restoring) return;
  var u = _theoryHistoryURL();
  history.pushState({{t:1}}, '', u || window.location.pathname);
}}

function _theoryReplace(){{
  if(_restoring) return;
  var u = _theoryHistoryURL();
  history.replaceState({{t:1}}, '', u || window.location.pathname);
}}

function _applyTheoryDeepLink(params){{
  theoryReset();
  var theoryMode = params.get('theory');
  if(!theoryMode){{ renderTheoryPane(null); return; }}
  if(theoryMode==='notes'){{
    var nq = params.get('q');
    if(nq!=null) document.getElementById('theoryNotesSearch').value = nq;
    _notesSavedOnly = params.get('saved')==='1';
    _notesActiveSpecs = new Set((params.getAll('nspec')||[]).filter(Boolean));
    _notesActiveSubtopic = params.get('nsub');
    var nid = params.get('note');
    renderTheoryPane('notes');
    if(nid) openTheoryNote(nid);
    return;
  }}
  if(theoryMode==='flashcards'){{
    var sys = params.get('system');
    var sub = params.get('subtopic');
    var cid = params.get('card');
    var dck = params.get('deck');
    var dq = params.get('q');
    if(dq!=null) document.getElementById('theorySearch').value = dq;
    _theorySavedOnly = params.get('saved')==='1';
    _theoryActiveSubtopic = sub || null;
    _theoryActiveSpecs = sys
      ? new Set([sys])
      : new Set(allFlashcardDecks.map(function(d){{ return d.specialty; }}));
    renderTheoryPane('flashcards');
    if(dck){{
      var dhit = allFlashcardDecks.find(function(d){{ return d.id===dck; }});
      if(dhit){{
        if(params.get('list')==='1') openTheoryCardList(dhit.id);
        else openTheoryDeck(dhit.id, 0);
      }}
      return;
    }}
    if(params.get('list')==='1' && sys && sub){{
      var lhit = allFlashcardDecks.find(function(d){{
        return d.id.toLowerCase() === (sys+'/'+sub).toLowerCase();
      }});
      if(lhit) openTheoryCardList(lhit.id);
      return;
    }}
    if(cid){{
      var tRef = theoryDeckFromCardId(cid);
      if(tRef){{
        _theoryActiveSpecs.add(tRef.deck.specialty);
        openTheoryDeck(tRef.deck.id, tRef.idx);
      }}
      return;
    }}
    if(sub && sys){{
      var hit = allFlashcardDecks.find(function(d){{
        return d.id.toLowerCase() === (sys+'/'+sub).toLowerCase();
      }});
      if(hit) openTheoryDeck(hit.id, 0);
    }}
  }}
}}

function katexify(root){{
  // Render LaTeX delimiters ($$...$$, \\\\(...\\\\), \\\\[...\\\\]) inside a container.
  // Single-$ is intentionally NOT enabled (currency amounts appear in pearls/notes).
  if(!root || typeof renderMathInElement !== 'function') return;
  try {{
    renderMathInElement(root, {{
      delimiters:[
        {{left:'$$', right:'$$', display:true}},
        {{left:'\\\\(', right:'\\\\)', display:false}},
        {{left:'\\\\[', right:'\\\\]', display:true}}
      ],
      throwOnError:false,
      strict:'ignore'
    }});
  }} catch(e){{}}
}}

// ---- Theory Topics (markdown notes) ----
function _theoryFilteredNotes(){{
  var q = (document.getElementById('theoryNotesSearch').value||'').toLowerCase().trim();
  return THEORY_NOTES.filter(function(n){{
    if(_notesSavedOnly && !(_bookmarks.items && _bookmarks.items['note:'+n.id])) return false;
    if(_notesActiveSpecs.size && !_notesActiveSpecs.has(n.system)) return false;
    if(_notesActiveSubtopic && n.subtopic!==_notesActiveSubtopic) return false;
if(!q) return true;
    return (n.title+' '+n.md).toLowerCase().indexOf(q)!==-1;
  }});
}}

function theoryNoteNav(delta){{
  if(!_currentTheoryNote) return;
  var order = _theoryFilteredNotes();
  var idx = -1;
  for(var i=0;i<order.length;i++){{
    if(order[i].id===_currentTheoryNote.id){{ idx=i; break; }}
  }}
  var ni = idx+delta;
  if(ni<0 || ni>=order.length) return;
  openTheoryNote(order[ni].id, true);
}}

function renderTheoryNotes(){{
  var q = (document.getElementById('theoryNotesSearch').value||'').toLowerCase().trim();
  var list = document.getElementById('theoryNotesList');
  var countEl = document.getElementById('theoryNotesCount');
  var box = document.getElementById('theoryNotesChips');
if(box){{
    var savedCount = Object.keys(_bookmarks.items || {{}}).filter(function(r){{ return r.indexOf('note:')===0; }}).length;
    var specSet = {{}}, subSet = {{}};
    THEORY_NOTES.forEach(function(n){{ specSet[n.system]=(specSet[n.system]||0)+1; subSet[n.system+'\u0001'+n.subtopic]=(subSet[n.system+'\u0001'+n.subtopic]||0)+1; }});
    var specChips = Object.keys(specSet).sort().map(function(s){{
      return '<button class="chip'+( _notesActiveSpecs.has(s)?' active':'')+'" data-notes-spec="'+escapeHtml(s)+'" style="--chip-color:var(--accent)">'+escapeHtml(s)+' <span class="chip-count">'+specSet[s]+'</span></button>';
    }}).join('');
    var subChips = '';
    if(_notesActiveSpecs.size===1){{
      var onlySpec = Array.from(_notesActiveSpecs)[0];
      subChips = Object.keys(subSet).filter(function(k){{ return k.indexOf(onlySpec+'\u0001')===0; }}).sort().map(function(k){{
        var sub = k.split('\u0001')[1];
        return '<button class="chip'+( _notesActiveSubtopic===sub?' active':'')+'" data-notes-sub="'+escapeHtml(sub)+'" style="--chip-color:var(--accent)">'+escapeHtml(sub)+' <span class="chip-count">'+subSet[k]+'</span></button>';
      }}).join('');
    }}
    var anyActive = _notesActiveSpecs.size>0 || _notesActiveSubtopic || _notesSavedOnly;
    box.innerHTML = specChips + subChips +
      '<button class="chip'+( _notesSavedOnly?' active':'')+'" data-notes-saved-only style="--chip-color:var(--accent)">&#128278; Saved ('+savedCount+')</button>'+
      (anyActive ? '<button class="chip" data-notes-clear-all style="--chip-color:var(--ink-muted)">&#10005; Clear</button>' : '');
  }}
  if(!THEORY_NOTES.length){{
    list.innerHTML = '<div class="bm-empty"><span class="icon">&#128214;</span><p>No theory notes yet. Drop markdown files into <span class="mono">output_files/Theory MDs/</span>.</p></div>';
    if(countEl) countEl.textContent = '';
    return;
  }}
  var filtered = _theoryFilteredNotes();
  list.innerHTML = filtered.map(function(n){{
    var saved = !!(_bookmarks.items && _bookmarks.items['note:'+n.id]);
    return '<button class="doc-card" data-theory-note="'+escapeHtml(n.id)+'">'+
      '<div class="doc-stripe" style="background:var(--accent)"></div>'+
      '<div class="doc-inner">'+
        '<div class="doc-top"><span class="type-tag">'+escapeHtml(n.system||'Note')+'</span>'+(n.subtopic && n.subtopic!=='General' ? '<span class="theory-sub-tag">'+escapeHtml(n.subtopic)+'</span>':'')+(saved?'<span class="theory-saved-badge">&#128278; saved</span>':'')+'</div>'+
        '<p class="doc-title">'+escapeHtml(n.title)+'</p>'+
        '<p class="doc-snippet">'+escapeHtml(n.md.replace(/\s+/g,' ').substring(0,110))+'</p>'+
      '</div>'+
    '</button>';
  }}).join('');
  if(countEl) countEl.textContent = filtered.length ? 'Showing '+filtered.length+' of '+THEORY_NOTES.length+' notes' : '';
}}

function _theoryMarkdownHTML(md){{
  // Degrade footnote syntax: drop [^n] references and [^n]: definition lines
  var out = String(md||'');
  out = out.replace(/^\[\^[^\]]+\]:\s*.*$/gm, '');
  out = out.replace(/\[\^[^\]]+\]/g, '');
  try {{
    var html = marked.parse(out);
    html = html.replace(/<table>[\s\S]*?<\/table>/g, function(t){{
      return '<button class="theory-table-expand" data-theory-table-open type="button"><span class="tt-expand-icon">&#8693;</span> Full view</button>'+
             '<div class="theory-table-wrap" data-theory-table-open>'+t+'</div>';
    }});
    return html;
  }} catch(e){{ return '<pre>'+escapeHtml(out)+'</pre>'; }}
}}

function openTheoryNote(noteId, fromReader){{
  var note = THEORY_NOTES.find(function(n){{ return n.id===noteId; }});
  if(!note) return;
  _currentTheoryNote = note;
  renderTheoryPane('notes');
  document.getElementById('theoryNotesSearchRow').style.display = 'none';
  document.getElementById('theoryNotesChips').style.display = 'none';
  document.getElementById('theoryNotesList').style.display = 'none';
  document.getElementById('theoryNotesCount').style.display = 'none';
  var ref = 'note:'+note.id;
  registerBookmarkMeta(ref, {{kind:'note', title: note.title, system: 'Theory Topics', type: 'Note', locator: {{noteId: note.id}}}});
  var saveBtn = _bmEnabled() ? bookmarkBtnHTML(ref) : '';
  var reader = document.getElementById('theoryNoteReader');
  reader.style.display = 'block';
  var order = _theoryFilteredNotes();
  var idx = -1;
  for(var i=0;i<order.length;i++){{ if(order[i].id===note.id){{ idx=i; break; }} }}
  var prevBtn = idx>0 ? '<button class="btn nav-btn" data-theory-note-nav="-1" title="Previous note">&#9664; Prev</button>' : '';
  var nextBtn = (idx>=0 && idx<order.length-1) ? '<button class="btn nav-btn" data-theory-note-nav="1" title="Next note">Next &#9654;</button>' : '';
  reader.innerHTML =
    '<div class="theory-card-head" style="margin-bottom:14px">'+
      _theoryPill(note.system||'General', note.title)+
      (note.subtopic && note.subtopic!=='General' ? '<span class="theory-sub-tag" style="align-self:center">'+escapeHtml(note.subtopic)+'</span>' : '')+
      prevBtn+nextBtn+
      exportNoteBtnHTML(note)+
      '<span style="flex:1"></span>'+
      saveBtn+
      theoryFontChipsHTML('notes')+
    '</div>'+
    '<article class="theory-note" id="theoryNoteArticle">'+_theoryMarkdownHTML(note.md)+'</article>';
  applyTheoryFont('notes');
  katexify(document.getElementById('theoryNoteArticle'));
  renderTheoryCrumbs();
  if(fromReader) _theoryReplace(); else _theoryPush();
  _focusCrumb();
  window.scrollTo({{top:0, behavior:'instant'}});
}}

function theoryNotesBack(){{
  document.getElementById('theoryNoteReader').style.display = 'none';
  document.getElementById('theoryNoteReader').innerHTML = '';
  document.getElementById('theoryNotesList').style.display = '';
  document.getElementById('theoryNotesCount').style.display = '';
  document.getElementById('theoryNotesSearchRow').style.display = '';
  document.getElementById('theoryNotesChips').style.display = '';
  _currentTheoryNote = null;
  renderTheoryNotes();
  renderTheoryCrumbs();
  _theoryPush();
  _focusCrumb();
  window.scrollTo({{top:0, behavior:'instant'}});
}}

/* ---- Theory table full-view overlay ---- */
function openTheoryTableOverlay(src){{
  var table = null;
  if(src){{
    var wrap = (typeof src.closest==='function' && src.closest('.theory-table-wrap')) ||
      (src.nextElementSibling && src.nextElementSibling.classList && src.nextElementSibling.classList.contains('theory-table-wrap') ? src.nextElementSibling : null);
    if(wrap) table = wrap.querySelector('table');
  }}
  if(!table && src && src.tagName==='TABLE') table = src;
  if(!table) return;
  var title = (_currentTheoryNote && _currentTheoryNote.title) ? _currentTheoryNote.title : 'Table';
  var inner = document.getElementById('theoryTableFitInner');
  inner.innerHTML = '';
  inner.appendChild(table.cloneNode(true));
  document.getElementById('theoryTableOverlayTitle').textContent = title + ' \u00B7 Table';
  var scrollEl = document.getElementById('theoryTableOverlayScroll');
  scrollEl.scrollTop = 0; scrollEl.scrollLeft = 0;
  _theoryTableFitActive = false;
  scrollEl.classList.remove('fit');
  inner.style.zoom = '';
  var fitBtn = document.querySelector('[data-theory-table-fit]');
  if(fitBtn) fitBtn.textContent = 'Fit width';
  document.getElementById('theoryTableOverlay').style.display = 'flex';
  document.body.style.overflow = 'hidden';
  _theoryTableOverlayOpen = true;
  var ov = document.getElementById('theoryTableOverlay');
  var fsReq = ov.requestFullscreen || ov.webkitRequestFullscreen;
  if(fsReq){{
    var p = fsReq.call(ov);
    if(p && p.catch) p.catch(function(){{}});
  }}
}}

function closeTheoryTableOverlay(){{
  if(!_theoryTableOverlayOpen) return;
  if(document.fullscreenElement || document.webkitFullscreenElement){{
    var p = (document.exitFullscreen || document.webkitExitFullscreen).call(document);
    if(p && p.catch) p.catch(finishCloseTheoryTableOverlay);
    return;
  }}
  finishCloseTheoryTableOverlay();
}}

function finishCloseTheoryTableOverlay(){{
  document.getElementById('theoryTableOverlay').style.display = 'none';
  document.getElementById('theoryTableFitInner').innerHTML = '';
  document.body.style.overflow = '';
  _theoryTableOverlayOpen = false;
  _theoryTableFitActive = false;
}}

function theoryTableToggleFit(){{
  if(!_theoryTableOverlayOpen) return;
  _theoryTableFitActive = !_theoryTableFitActive;
  var scrollEl = document.getElementById('theoryTableOverlayScroll');
  var inner = document.getElementById('theoryTableFitInner');
  var btn = document.querySelector('[data-theory-table-fit]');
  if(_theoryTableFitActive){{
    scrollEl.classList.add('fit');
    if(btn) btn.textContent = 'Fit: off';
    theoryTableApplyFit();
  }} else {{
    scrollEl.classList.remove('fit');
    inner.style.zoom = '';
    if(btn) btn.textContent = 'Fit width';
  }}
}}

function theoryTableApplyFit(){{
  if(!_theoryTableFitActive) return;
  var scrollEl = document.getElementById('theoryTableOverlayScroll');
  var inner = document.getElementById('theoryTableFitInner');
  var table = inner.querySelector('table');
  if(!table) return;
  var avail = scrollEl.clientWidth - 28;
  var scale = Math.min(1, avail / (table.scrollWidth || 1));
  inner.style.zoom = scale >= 1 ? '' : String(scale);
}}

document.addEventListener('fullscreenchange', function(){{
  if(_theoryTableOverlayOpen && !document.fullscreenElement) finishCloseTheoryTableOverlay();
}});
document.addEventListener('webkitfullscreenchange', function(){{
  if(_theoryTableOverlayOpen && !document.webkitFullscreenElement) finishCloseTheoryTableOverlay();
}});
window.addEventListener('resize', function(){{
  if(_theoryTableOverlayOpen && _theoryTableFitActive) theoryTableApplyFit();
}});

function renderTheoryPane(mode){{
  if(mode==='hero') mode = null;
  _theoryMode = mode || null;
  var hero = document.getElementById('theoryHero');
  var notes = document.getElementById('theoryNotesPane');
  var cards = document.getElementById('theoryFlashcardsPane');
  if(!hero || !notes || !cards) return;
  hero.style.display = _theoryMode ? 'none' : '';
  notes.style.display = _theoryMode==='notes' ? '' : 'none';
  cards.style.display = _theoryMode==='flashcards' ? '' : 'none';
  if(_theoryMode==='notes'){{ renderTheoryNotes(); }}
  if(_theoryMode==='flashcards'){{ renderTheoryChips(); renderTheoryDecks(); }}
  renderTheoryCrumbs();
}}

function theoryBackToHero(){{
  theoryReset();
  renderTheoryPane(null);
  renderTheoryCrumbs();
  _theoryPush();
  window.scrollTo({{top:0, behavior:'instant'}});
}}

function renderTheoryChips(){{
  var box = document.getElementById('theoryChips');
  if(!box) return;
  if(_theoryActiveSpecs.size!==1) _theoryActiveSubtopic = null;
  var counts = {{}};
  allFlashcardDecks.forEach(function(d){{ counts[d.specialty] = (counts[d.specialty]||0)+1; }});
  var html = Object.keys(counts).sort().map(function(s){{
    var active = _theoryActiveSpecs.has(s);
    return '<button class="chip '+(active?'active':'')+'" data-theory-chip="'+escapeHtml(s)+'" style="--chip-color:var('+_theorySpecVar(s)+')"><span class="dot" style="background:var('+_theorySpecVar(s)+')"></span>'+escapeHtml(s)+' ('+counts[s]+')</button>';
  }}).join('');
  var savedCount = Object.keys(_bookmarks.items || {{}}).filter(function(r){{ return r.indexOf('flashcard:')===0; }}).length;
  html += '<button class="chip'+( _theorySavedOnly?' active':'')+'" data-theory-saved-only style="--chip-color:var(--accent)">&#128278; Saved ('+savedCount+')</button>';
  box.innerHTML = html + '<button class="chip" data-theory-chip-reset>Reset</button><button class="chip" data-theory-chip-uncheck>Uncheck all</button>';
  renderTheorySubtopicChips();
}}

function renderTheorySubtopicChips(){{
  var box = document.getElementById('theorySubtopicChips');
  if(!box) return;
  if(_theoryActiveSpecs.size!==1){{
    box.innerHTML = '';
    return;
  }}
  var spec = Array.from(_theoryActiveSpecs)[0];
  var subs = THEORY_SUBTOPIC_MAP[spec] || [];
  if(!subs.length){{
    box.innerHTML = '';
    return;
  }}
  var deckCounts = {{}};
  allFlashcardDecks.forEach(function(d){{
    if(d.specialty!==spec) return;
    (d.subtopics||[]).forEach(function(t){{ deckCounts[t] = (deckCounts[t]||0)+1; }});
  }});
  var html = '<span class="pearl-count" style="margin:0 6px 0 0;flex:0 0 auto">Subtopic:</span>';
  html += subs.map(function(t){{
    var active = _theoryActiveSubtopic===t;
    return '<button class="chip'+(active?' active':'')+'" data-theory-subtopic="'+escapeHtml(t)+'" style="--chip-color:var('+_theorySpecVar(spec)+')">'+escapeHtml(t)+(deckCounts[t]?' ('+deckCounts[t]+')':'')+'</button>';
  }}).join('');
  if(_theoryActiveSubtopic) html += '<button class="chip" data-theory-subtopic-clear style="--chip-color:var(--ink-muted)">&#10005; Clear</button>';
  box.innerHTML = html;
}}

function renderTheoryDecks(){{
  var q = (document.getElementById('theorySearch').value||'').toLowerCase().trim();
  var list = document.getElementById('theoryDeckList');
  var countEl = document.getElementById('theoryCount');
  if(!allFlashcardDecks.length){{
    list.innerHTML = '<div class="bm-empty"><span class="icon">&#129504;</span><p>No flashcard decks yet. Drop files under <span class="mono">flashcards_input/{{Specialty}}/</span> (md = authored deck, pdf/txt/docx/html = raw material) and run <span class="mono">python flashcards.py</span>.</p></div>';
    if(countEl) countEl.textContent = '';
    return;
  }}
  var filtered = allFlashcardDecks.filter(function(d){{
    if(!_theoryActiveSpecs.has(d.specialty)) return false;
    var savedRefs = _savedCardRefs(d.id);
    if(_theorySavedOnly && !savedRefs.length) return false;
    if(_theoryActiveSubtopic && (d.subtopics||[]).indexOf(_theoryActiveSubtopic)===-1) return false;
    if(q){{
      var hay = (d.title+' '+d.specialty+' '+d.subtopics.join(' ')+' '+d.cards.map(function(c){{ return c.subtopic+' '+(c.front||'')+' '+(c.back||'')+' '+(c.tags||[]).join(' '); }}).join(' ')).toLowerCase();
      if(hay.indexOf(q)===-1) return false;
    }}
    return true;
  }});
  var html = filtered.map(function(d){{
    var savedRefs = _savedCardRefs(d.id);
    var savedBadge = savedRefs.length ? '<span class="theory-saved-badge">&#128278; '+savedRefs.length+'</span>' : '';
    var snip = (d.subtopics||[]).length ? (d.subtopics||[]).slice(0,4).join(' \u00B7 ') : d.cards.map(function(c){{ return c.subtopic; }}).slice(0,3).join(' \u00B7 ');
    return '<button class="doc-card" data-theory-deck="'+escapeHtml(d.id)+'">'+
      '<div class="doc-stripe" style="background:var('+_theorySpecVar(d.specialty)+')"></div>'+
      '<div class="doc-inner">'+
        '<div class="doc-top">'+_theoryPill(d.specialty, d.specialty)+'<span class="type-tag">'+d.cards.length+' card'+(d.cards.length===1?'':'s')+'</span>'+savedBadge+'</div>'+
        '<p class="doc-title">'+escapeHtml(d.title)+'</p>'+
        '<p class="doc-snippet">'+escapeHtml(snip)+'</p>'+
      '</div>'+
    '</button>';
  }}).join('');
  list.innerHTML = html || '<p style="color:var(--ink-muted);padding:20px 4px">No decks match these filters.</p>';
  if(countEl) countEl.textContent = 'Showing '+filtered.length+' of '+allFlashcardDecks.length+' decks';
}}

function openTheoryDeck(deckId, cardIdxOrId, smooth){{
  var deck = allFlashcardDecks.find(function(d){{ return d.id===deckId; }});
  if(!deck) return;
  _currentDeck = deck;
  _theoryStudyFromList = false;
  _theoryListCollapsed = false;
  _theoryActiveSpecs.add(deck.specialty);
  renderTheoryPane('flashcards');
  _theoryCardOrder = _theoryActiveSubtopic
    ? deck.cards.map(function(c, i){{ return (c.tags||[]).indexOf(_theoryActiveSubtopic)>-1 ? i : -1; }}).filter(function(i){{ return i>-1; }})
    : deck.cards.map(function(c, i){{ return i; }});
  if(!_theoryCardOrder.length) _theoryCardOrder = deck.cards.map(function(c, i){{ return i; }});
  var start = 0;
  if(typeof cardIdxOrId==='number') start = (cardIdxOrId>=0 && cardIdxOrId<deck.cards.length) ? cardIdxOrId : _theoryCardOrder[0];
  else if(typeof cardIdxOrId==='string'){{
    var byId = deck.cards.findIndex(function(c){{ return c.id===cardIdxOrId; }});
    start = byId>-1 ? byId : _theoryCardOrder[0];
  }} else {{
    start = _theoryCardOrder[0];
  }}
  if(_theoryActiveSubtopic && _theoryCardOrder.indexOf(start)===-1) start = _theoryCardOrder[0];
  _currentCardIdx = start;
  _theoryFlipped = false;
  document.getElementById('theoryBrowser').style.display = 'none';
  document.getElementById('theoryStudy').style.display = 'block';
  renderTheoryCard();
  if(smooth) theoryScrollToStudy();
  _theoryPush();
  _focusCrumb();
}}

function theoryBackToBrowser(){{
  _currentDeck = null;
  _theoryListCollapsed = false;
  _theoryStudyFromList = false;
  document.getElementById('theoryStudy').style.display = 'none';
  document.getElementById('theoryCardList').style.display = 'none';
  document.getElementById('theoryBrowser').style.display = '';
  renderTheoryDecks();
  renderTheoryCrumbs();
  _theoryPush();
  _focusCrumb();
  window.scrollTo({{top:0, behavior:'instant'}});
}}

function theoryStudyToList(){{
  if(!_currentDeck) return;
  _theoryListCollapsed = false;
  renderTheoryCardList();
  document.getElementById('theoryStudy').style.display = 'none';
  document.getElementById('theoryCardList').style.display = 'block';
  renderTheoryCrumbs();
  _theoryPush();
  _focusCrumb();
  window.scrollTo({{top:0, behavior:'instant'}});
}}

function openTheoryCardList(deckId){{
  var deck = allFlashcardDecks.find(function(d){{ return d.id===deckId; }});
  if(!deck) return;
  renderTheoryPane('flashcards');
  _currentDeck = deck;
  _theoryStudyFromList = false;
  _theoryListCollapsed = false;
  _theoryActiveSpecs.add(deck.specialty);
  document.getElementById('theoryBrowser').style.display = 'none';
  document.getElementById('theoryStudy').style.display = 'none';
  document.getElementById('theoryCardList').style.display = 'block';
  renderTheoryCardList();
  renderTheoryCrumbs();
  _theoryPush();
  _focusCrumb();
}}

function renderTheoryCardList(){{
  var deck = _currentDeck;
  if(!deck) return;
  var filtered = _theoryActiveSubtopic
    ? deck.cards.filter(function(c){{ return (c.tags||[]).indexOf(_theoryActiveSubtopic)>-1; }})
    : deck.cards;
  if(!filtered.length) filtered = deck.cards;
  var collapsed = !!_theoryListCollapsed;
  var toggleLabel = collapsed
    ? filtered.length+' card'+(filtered.length===1?'':'s')+' &middot; show list'
    : 'Collapse list';
  var toggleCaret = collapsed ? '&#9660;' : '&#9650;';
  document.getElementById('theoryCardListHead').innerHTML =
    _theoryPill(deck.specialty, deck.title)+
    '<button class="theory-list-toggle" data-theory-list-toggle title="'+(collapsed?'Show the card list':'Hide the card list')+'"><span class="theory-toggle-caret">'+toggleCaret+'</span><span>'+toggleLabel+'</span></button>';
  var countEl = document.getElementById('theoryCardListCount');
  countEl.style.display = collapsed ? 'none' : '';
  countEl.textContent = filtered.length===deck.cards.length
    ? 'Showing '+filtered.length+' card'+(filtered.length===1?'':'s')
    : 'Showing '+filtered.length+' of '+deck.cards.length+' cards (filtered to '+escapeHtml(_theoryActiveSubtopic)+')';
  var body = document.getElementById('theoryCardListBody');
  body.style.display = collapsed ? 'none' : '';
  body.innerHTML = filtered.map(function(c){{
    var saved = !!(_bookmarks.items && _bookmarks.items[theoryCardRef(deck.id, c.id)]);
    return '<button class="pearl-row" data-theory-card-open="'+c.id+'">'+
      '<span class="dot" style="background:var('+_theorySpecVar(deck.specialty)+')"></span>'+
      '<span class="txt">'+escapeHtml((c.front||c.subtopic||'Card').substring(0,160))+'<span class="src">'+(c.tags||[]).join(' \u00B7 ')+(saved?' \u00B7 saved':'')+'</span></span>'+
    '</button>';
  }}).join('') || '<p style="color:var(--ink-muted);padding:20px 4px">No cards match this subtopic.</p>';
  renderTheoryCrumbs();
}}

function theoryScrollToStudy(){{
  var st = document.getElementById('theoryStudy');
  if(st) st.scrollIntoView({{block:'start', behavior:'smooth'}});
}}

function theoryFontSize(scope){{
  var k = 'hackccm_theoryFont_'+scope;
  try {{
    var v = parseFloat(localStorage.getItem(k)||'');
    if(v && v>=0.7 && v<=2) return v;
  }} catch(e){{}}
  return scope==='cards' ? 0.94 : 1;
}}

function theoryFontChipsHTML(scope){{
  var cur = theoryFontSize(scope);
  var vals = scope==='cards' ? [0.85, 0.94, 1.15] : [0.85, 1, 1.2];
  return vals.map(function(f){{
    var label = f<0.94 ? 'A-' : (f>1.05 ? 'A+' : 'A');
    return '<button class="theory-mode-chip'+(Math.abs(cur-f)<0.001?' active':'')+'" data-theory-font="'+scope+'" data-theory-font-val="'+f+'" title="Text size">'+label+'</button>';
  }}).join('');
}}

function applyTheoryFont(scope){{
  var v = theoryFontSize(scope);
  if(scope==='notes'){{
    var art = document.getElementById('theoryNoteArticle');
    if(art) art.style.setProperty('--theory-note-fs', v+'rem');
  }} else {{
    var stage = document.getElementById('theoryCardStage');
    if(stage) stage.style.setProperty('--theory-card-fs', v+'rem');
  }}
}}

function theoryNav(delta){{
  if(!_currentDeck) return;
  var pos = _theoryCardOrder.indexOf(_currentCardIdx);
  var nextPos = pos + delta;
  if(nextPos<0 || nextPos>=_theoryCardOrder.length) return;
  _currentCardIdx = _theoryCardOrder[nextPos];
  _theoryFlipped = false;
  renderTheoryCard();
  _theoryReplace();
}}

function renderTheoryCard(){{
  if(!_currentDeck) return;
  var deck = _currentDeck;
  var posIdx = _theoryCardOrder.indexOf(_currentCardIdx);
  if(posIdx===-1) posIdx = 0;
  var card = deck.cards[_currentCardIdx];
  var total = _theoryCardOrder.length;
  var filtered = !!_theoryActiveSubtopic;
  var ref = theoryCardRef(deck.id, card.id);

  registerBookmarkMeta(ref, {{kind:'flashcard', title: card.subtopic || deck.title, system: deck.specialty, type: 'Flashcard', locator: {{deck: deck.id, card: card.id, cardIdx: _currentCardIdx}}}});

  var saveBtn = _bmEnabled() ? bookmarkBtnHTML(ref) : '';
  var modeToggles = '<button class="theory-mode-chip'+( _theoryViewMode==='single'?' active':'')+'" data-theory-mode="single">Single face</button><button class="theory-mode-chip'+( _theoryViewMode==='flip'?' active':'')+'" data-theory-mode="flip">Flip card</button>';

  document.getElementById('theoryStudyHead').innerHTML =
    _theoryPill(deck.specialty, deck.title)+
    '<span class="theory-card-progress">Card '+(posIdx+1)+' of '+total+(filtered?' (filtered)':'')+'</span>'+
    '<button class="btn nav-btn" data-theory-list-open title="Show the card list">List &#9776;</button>'+
    saveBtn;

  var tagRow = (card.tags||[]).length ? card.tags.map(function(t){{
    return '<span class="theory-tag-pill'+(filtered && t===_theoryActiveSubtopic?' hot':'')+'">'+escapeHtml(t)+'</span>';
  }}).join('') : '';
  if(filtered) tagRow += '<button class="theory-tag-pill" data-theory-tag-clear title="Clear subtopic filter">'+escapeHtml(_theoryActiveSubtopic)+' <span class="theory-tag-x">&#10005;</span></button>';
  document.getElementById('theoryCardTags').innerHTML = tagRow;

  var stage = document.getElementById('theoryCardStage');
  var frontHTML = (card.front||'').trim() ? marked.parse(card.front) : '<h3>'+escapeHtml(card.subtopic)+'</h3>';
  var backHTML = marked.parse(card.back||'');
  if(_theoryViewMode==='flip'){{
    stage.innerHTML =
      '<div class="theory-card-wrap'+( _css3d?'':' no-3d')+'"><div class="theory-card-inner flip'+( _theoryFlipped?' flipped':'')+'" id="theoryFlipInner">'+
        '<div class="theory-face front theory-card-content"><div class="theory-front-big">'+frontHTML+'</div><span class="flip-hint">tap to flip \u21C5</span></div>'+
        '<div class="theory-face back theory-card-content">'+backHTML+'<span class="flip-hint">tap to flip \u21C5</span></div>'+
      '</div></div>';
  }} else {{
    var frontText = (card.front||'').trim();
    var qHTML;
    if(!frontText){{
      qHTML = '<h3 class="theory-card-question">'+escapeHtml(card.subtopic||deck.title)+'</h3>';
    }} else {{
      var qBody = marked.parse(frontText).trim().replace(/^<p>\s*/,'').replace(/\s*<\/p>$/,'');
      var qBlock = /<(p|div|ul|ol|table|blockquote|h[1-6])\s*>/i.test(qBody);
      qHTML = qBlock
        ? '<div class="theory-card-question">'+qBody+'</div>'
        : '<h3 class="theory-card-question">'+qBody+'</h3>';
    }}
    stage.innerHTML = qHTML + '<div class="theory-card-flat theory-card-content">'+backHTML+'</div>';
  }}
  katexify(stage);
  applyTheoryFont('cards');

  var prevBtn = '<button class="btn nav-btn"'+(posIdx===0?' disabled':'')+' data-theory-nav="-1">&#9664; Previous</button>';
  var nextBtn = posIdx<total-1
    ? '<button class="btn nav-btn" data-theory-nav="1">Next &#9654;</button>'
    : '<button class="btn nav-btn" data-theory-done>Done &#10004;</button>';
  document.getElementById('theoryCardNav').innerHTML = prevBtn + nextBtn + modeToggles + theoryFontChipsHTML('cards');

  document.getElementById('theoryCardDots').innerHTML = _theoryCardOrder.map(function(ci, pi){{
    var c = deck.cards[ci];
    var saved = !!(_bookmarks.items && _bookmarks.items[theoryCardRef(deck.id, c.id)]);
    return '<button class="theory-dot'+( pi===posIdx?' active':'')+( saved?' saved':'')+'" data-theory-dot="'+pi+'" title="Card '+(pi+1)+' of '+total+'"></button>';
  }}).join('');
  renderTheoryCrumbs();
}}

function theorySetViewMode(mode){{
  _theoryViewMode = mode;
  _theoryFlipped = false;
  renderTheoryCard();
}}

// =====================================================================
// BOOKMARKS
// =====================================================================
function registerBookmarkMeta(ref, meta){{ _bookmarkMeta[ref] = meta || {{}}; }}

function bookmarkBtnHTML(ref, label){{
  var active = !!(_bookmarks.items && _bookmarks.items[ref]);
  return '<button class="icon-btn bookmark-btn'+(active?' active':'')+'" data-bookmark-toggle="'+escapeHtml(ref)+'" aria-label="'+(active?'Remove bookmark':'Add bookmark')+'" title="'+(active?'Remove bookmark':'Add bookmark')+'">'+(label||'&#128278;')+'</button>';
}}

function exportPaperBtnHTML(entry){{
  var qs = 'kind=paper&file_name='+encodeURIComponent(entry.file_name||'')+'&system='+encodeURIComponent(entry.system||'General')+'&type='+encodeURIComponent(entry.type||'Other');
  return '<button class="btn nav-btn" data-export-paper="'+escapeHtml(qs)+'" title="Open a printable version of this summary in a new window">&#128196; Export / PDF</button>';
}}

function exportNoteBtnHTML(note){{
  var qs = 'kind=note&file_name='+encodeURIComponent(note.id||'')+'&title='+encodeURIComponent((note.title||'').substring(0,120));
  return '<button class="btn nav-btn" data-export-note="'+escapeHtml(qs)+'" title="Open a printable version of this note in a new window">&#128196; Export / PDF</button>';
}}

function refreshBookmarkButtons(){{
  document.querySelectorAll('[data-bookmark-toggle]').forEach(function(btn){{
    var ref = btn.dataset.bookmarkToggle;
    var active = !!(_bookmarks.items && _bookmarks.items[ref]);
    btn.classList.toggle('active', active);
    btn.title = active ? 'Remove bookmark' : 'Add bookmark';
    btn.setAttribute('aria-label', active ? 'Remove bookmark' : 'Add bookmark');
  }});
}}

function updateBookmarkCounts(){{
  var n = Object.keys(_bookmarks.items || {{}}).length;
  ['bookmarksTopCount','bookmarksDrawerCount'].forEach(function(id){{
    var el = document.getElementById(id);
    if(el){{ el.textContent = n; el.classList.toggle('zero', n===0); }}
  }});
  var c = document.getElementById('bookmarksCount');
  if(c) c.textContent = n + ' saved';
}}

function loadBookmarks(){{
  if(!USER_IS_ADMIN && !USER_FEATURES['bookmarks']) return;
  fetch('/api/bookmarks').then(function(r){{ return r.json(); }}).then(function(data){{
    if(data && data.items) _bookmarks = data;
    else _bookmarks = {{items: {{}}, folders: {{}}}};
    updateBookmarkCounts(); refreshBookmarkButtons();
  }}).catch(function(){{}});
}}

function toggleBookmark(ref, btn){{
  if(!_bookmarks.items) _bookmarks.items = {{}};
  if(_bookmarks.items[ref]){{
    fetch('/api/bookmarks?ref='+encodeURIComponent(ref), {{method:'DELETE'}}).then(function(r){{ return r.json(); }}).then(function(d){{
      delete _bookmarks.items[ref];
      updateBookmarkCounts(); refreshBookmarkButtons();
      if(document.querySelector('.view.active').id==='view-bookmarks') renderBookmarks();
      showToast('Bookmark removed');
    }}).catch(function(){{ showToast('Failed &mdash; try again'); }});
  }} else {{
    var meta = _bookmarkMeta[ref] || {{}};
    var payload = {{
      ref: ref,
      kind: meta.kind || 'paper',
      title: meta.title || 'Untitled',
      system: meta.system || 'General',
      type: meta.type || '',
      locator: meta.locator || {{}}
    }};
    fetch('/api/bookmarks', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify(payload)}}).then(function(r){{ return r.json(); }}).then(function(d){{
      if(d && d.item) _bookmarks.items[ref] = d.item;
      updateBookmarkCounts(); refreshBookmarkButtons();
      if(document.querySelector('.view.active').id==='view-bookmarks') renderBookmarks();
      showToast('Bookmark saved');
    }}).catch(function(){{ showToast('Failed &mdash; try again'); }});
  }}
}}

function removeBookmark(ref){{
  if(!(_bookmarks.items && _bookmarks.items[ref])) return;
  fetch('/api/bookmarks?ref='+encodeURIComponent(ref), {{method:'DELETE'}}).then(function(r){{ return r.json(); }}).then(function(d){{
    delete _bookmarks.items[ref];
    updateBookmarkCounts(); refreshBookmarkButtons(); renderBookmarks();
  }}).catch(function(){{ showToast('Failed &mdash; try again'); }});
}}

function setBookmarkFolder(ref, folder){{
  fetch('/api/bookmarks', {{method:'PATCH', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{ref: ref, folder: folder || null}})}}).then(function(r){{ return r.json(); }}).then(function(d){{
    if(d && d.item) _bookmarks.items[ref] = d.item;
    renderBookmarks();
  }}).catch(function(){{ showToast('Failed &mdash; try again'); }});
}}

function setBookmarkTags(ref, raw){{
  var tags = String(raw||'').split(',').map(function(t){{ return t.trim(); }}).filter(function(t){{ return t; }}).slice(0,20);
  fetch('/api/bookmarks', {{method:'PATCH', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{ref: ref, tags: tags}})}}).then(function(r){{ return r.json(); }}).then(function(d){{
    if(d && d.item) _bookmarks.items[ref] = d.item;
    renderBookmarks();
  }}).catch(function(){{ showToast('Failed &mdash; try again'); }});
}}

function createBookmarkFolder(){{
  var nameEl = document.getElementById('bookmarksNewFolderName');
  var name = (nameEl.value||'').trim();
  if(!name) return;
  fetch('/api/bookmarks/folders', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{name: name, color: _bmNewFolderColor}})}}).then(function(r){{ return r.json(); }}).then(function(d){{
    if(d && d.id){{
      if(!_bookmarks.folders) _bookmarks.folders = {{}};
      _bookmarks.folders[d.id] = d.folder;
    }}
    nameEl.value = '';
    document.getElementById('bookmarksNewFolderRow').classList.remove('show');
    renderBookmarks();
  }}).catch(function(){{ showToast('Failed &mdash; try again'); }});
}}

function renameBookmarkFolder(fid){{
  var f = _bookmarks.folders && _bookmarks.folders[fid];
  if(!f) return;
  var name = prompt('Folder name', f.name);
  if(!name || !name.trim()) return;
  fetch('/api/bookmarks/folders', {{method:'PATCH', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{id: fid, name: name.trim()}})}}).then(function(r){{ return r.json(); }}).then(function(d){{
    if(d && d.folder && _bookmarks.folders) _bookmarks.folders[fid] = d.folder;
    renderBookmarks();
  }}).catch(function(){{ showToast('Failed &mdash; try again'); }});
}}

function deleteBookmarkFolder(fid){{
  if(!confirm('Delete this folder? Bookmarks inside will move to Uncategorized.')) return;
  fetch('/api/bookmarks/folders?ref='+encodeURIComponent(fid), {{method:'DELETE'}}).then(function(r){{ return r.json(); }}).then(function(d){{
    if(_bookmarks.folders && _bookmarks.folders[fid]) delete _bookmarks.folders[fid];
    Object.keys(_bookmarks.items||{{}}).forEach(function(ref){{ if(_bookmarks.items[ref].folder===fid) _bookmarks.items[ref].folder = null; }});
    if(_bookmarksFolderFilter===fid) _bookmarksFolderFilter = null;
    renderBookmarks();
  }}).catch(function(){{ showToast('Failed &mdash; try again'); }});
}}

function openBookmark(ref){{
  var bm = _bookmarks.items && _bookmarks.items[ref];
  if(!bm) return;
  if(bm.kind==='paper' || bm.kind==='guideline'){{
    var loc = bm.locator || {{}};
    var entry = {{id: ref, file_name: loc.file_name, system: loc.system || bm.system || 'General', type: loc.type || bm.type || 'Other', title: bm.title, authors: '', doi: '#', journal: '', date_added: '', year: '', subtopic: ''}};
    var live = baseDataset.find(function(d){{ return d.file_name === loc.file_name; }});
    if(live) entry = live;
    openReader(entry, 'paper');
    return;
  }}
  if(bm.kind==='pearl'){{
    var loc = bm.locator || {{}};
    var livePearl = allPearls.find(function(p){{ return String(p.id)===String(loc.id); }});
    if(livePearl){{ openReader(livePearl, 'pearl'); }}
    else {{
      openReader({{id: loc.id, pearl: bm.title, source_paper: '', doi: '', author: '', system: bm.system || 'General', type: bm.type || 'Pearl', remarks: '', file_name: '', topic: '', timestamp: ''}}, 'pearl');
    }}
    return;
  }}
  if(bm.kind==='trial'){{
    var slug = (bm.locator && bm.locator.slug) ? bm.locator.slug : String(ref).replace(/^trial:/,'');
    openTrialDetail(slug, [], -1);
    return;
  }}
  if(bm.kind==='condensed'){{
    var loc = bm.locator || {{}};
    openCondensedTrialDetail(loc.system || 'General', loc.name || '');
    return;
  }}
  if(bm.kind==='flashcard'){{
    var loc = bm.locator || {{}};
    if(!_theoryViewActive()) showView('theory');
    if(loc.card){{
      var tRef = theoryDeckFromCardId(loc.card);
      if(tRef){{ openTheoryDeck(tRef.deck.id, tRef.idx); return; }}
    }}
    openTheoryDeck(loc.deck || '', typeof loc.cardIdx==='number' ? loc.cardIdx : 0);
    return;
  }}
  if(bm.kind==='note'){{
    var loc = bm.locator || {{}};
    if(!_theoryViewActive()) showView('theory');
    if(loc.noteId){{ openTheoryNote(loc.noteId); return; }}
    var nId = String(ref).replace(/^note:/,'');
    if(nId) openTheoryNote(nId);
    return;
  }}
}}

function renderFolderSwatches(active){{
  var row = document.getElementById('bookmarksNewFolderColors');
  if(!row) return;
  row.innerHTML = BM_FOLDER_COLORS.map(function(c){{
    return '<button type="button" class="folder-swatch'+(c===active?' active':'')+'" data-bm-color="'+c+'" style="background:'+c+'" aria-label="Color '+c+'"></button>';
  }}).join('');
}}

function bmCardHTML(bm){{
  var kindLabel = {{paper:'Paper', guideline:'Guideline', pearl:'Pearl', trial:'Trial', condensed:'Condensed Trial', flashcard:'Flashcard', note:'Theory Note'}}[bm.kind] || bm.kind;
  var folderOpts = '<option value="">No folder</option>';
  Object.keys(_bookmarks.folders||{{}}).forEach(function(fid){{
    folderOpts += '<option value="'+escapeHtml(fid)+'"'+(bm.folder===fid?' selected':'')+'>'+escapeHtml(_bookmarks.folders[fid].name)+'</option>';
  }});
  var dispTitle = String(bm.title||bm.ref);
  if(dispTitle.length>140) dispTitle = dispTitle.substring(0,140)+'&hellip;';
  var tags = (bm.tags||[]).map(function(t){{ return '<span class="bm-tag">#'+escapeHtml(t)+'</span>'; }}).join('');
  return '<div class="bm-card">'+
    '<button class="bm-card-top" data-bookmark-open="'+escapeHtml(bm.ref)+'" role="button" tabindex="0">'+
      '<div style="flex:1;min-width:0">'+
        '<div style="margin-bottom:6px">'+pillHTML(bm.system||'General', (bm.system||'General')+' &middot; '+kindLabel)+'</div>'+
        '<div class="bm-title">'+escapeHtml(dispTitle)+'</div>'+
        '<div class="bm-meta">'+(bm.type?escapeHtml(bm.type):'')+(bm.added_at?' &middot; saved '+escapeHtml(String(bm.added_at).substring(0,10)):'')+'</div>'+
      '</div>'+
      '<span class="bm-del" style="font-size:1.1rem">&#8250;</span>'+
    '</button>'+
    '<div class="bm-card-actions">'+
      '<select data-bookmark-folder="'+escapeHtml(bm.ref)+'" title="Move to folder">'+folderOpts+'</select>'+
      '<input class="bm-tags-input" data-bookmark-tags="'+escapeHtml(bm.ref)+'" placeholder="Tags: sepsis, exam" value="'+escapeHtml((bm.tags||[]).join(', '))+'" autocomplete="off">'+
      '<span style="flex:1"></span>'+
      '<button class="bm-del" data-bookmark-del="'+escapeHtml(bm.ref)+'" title="Remove bookmark">&times;</button>'+
    '</div>'+
    (tags?'<div style="display:flex;gap:5px;flex-wrap:wrap">'+tags+'</div>':'')+
  '</div>';
}}

function renderBookmarks(){{
  var list = document.getElementById('bookmarksList');
  var foldersRow = document.getElementById('bookmarksFoldersRow');
  if(!list) return;
  var items = _bookmarks.items || {{}};
  var folders = _bookmarks.folders || {{}};
  var refs = Object.keys(items);
  var q = (document.getElementById('bookmarksSearch').value||'').toLowerCase().trim();

  var fhtml = '';
  if(Object.keys(folders).length){{
    fhtml += '<button class="bookmarks-folder-pill'+( _bookmarksFolderFilter===null ? ' active':'')+'" data-bm-folder-all>All</button>';
    Object.keys(folders).forEach(function(fid){{
      var f = folders[fid];
      fhtml += '<button class="bookmarks-folder-pill'+( _bookmarksFolderFilter===fid ? ' active':'')+'" data-bm-folder="'+escapeHtml(fid)+'">'+
        '<span class="fdot" style="background:'+escapeHtml(f.color||'#E8B778')+'"></span>'+escapeHtml(f.name)+'</button>';
      fhtml += '<button class="bm-folder-edit" data-bm-folder-rename="'+escapeHtml(fid)+'" title="Rename folder">&#9998;</button>';
      fhtml += '<button class="bm-folder-edit del" data-bm-folder-del="'+escapeHtml(fid)+'" title="Delete folder">&times;</button>';
    }});
  }}
  foldersRow.innerHTML = fhtml;

  if(!refs.length){{
    list.innerHTML = '<div class="bm-empty"><span class="icon">&#128278;</span><p>No bookmarks yet. Tap the &#128278; button on any paper, pearl, or trial to save it here.</p></div>';
    return;
  }}

  var filtered = refs.filter(function(ref){{
    var bm = items[ref];
    if(_bookmarksFolderFilter !== null && bm.folder !== _bookmarksFolderFilter) return false;
    if(!q) return true;
    var hay = (bm.title||'')+' '+(bm.system||'')+' '+(bm.tags||[]).join(' ');
    return hay.toLowerCase().indexOf(q) !== -1;
  }});
  if(!filtered.length){{
    list.innerHTML = '<div class="bm-empty"><span class="icon">&#128270;</span><p>No bookmarks match your filters.</p></div>';
    return;
  }}

  var groups = {{}};
  var none = [];
  filtered.forEach(function(ref){{ var g = items[ref].folder || null; if(g) (groups[g] = groups[g] || []).push(ref); else none.push(ref); }});
  var order = Object.keys(groups).sort(function(a,b){{ return ((folders[a]||{{}}).name||'').localeCompare((folders[b]||{{}}).name||''); }});
  if(none.length) order.unshift('');

  var html = '';
  order.forEach(function(g){{
    var label = g ? (folders[g]||{{}}).name||'Folder' : 'Uncategorized';
    var color = g ? (folders[g]||{{}}).color||'#E8B778' : 'var(--ink-muted)';
    var groupRefs = g ? groups[g] : none;
    html += '<div class="bm-section-head"><span class="dot" style="background:'+color+'"></span>'+escapeHtml(label)+' <span class="pearl-count">('+groupRefs.length+')</span><span class="bar"></span></div>';
    groupRefs.forEach(function(ref){{ html += bmCardHTML(items[ref]); }});
  }});
  list.innerHTML = html;
}}

// =====================================================================
// DISCLAIMER
// =====================================================================
function dismissDisclaimer(){{
  document.getElementById('disclaimerOverlay').style.display='none';
  try {{ sessionStorage.setItem('hackccm_disclaimer','1'); }} catch(e){{}}
}}
if(showDisclaimer && !(function(){{ try {{ return sessionStorage.getItem('hackccm_disclaimer'); }} catch(e){{ return null; }} }})()){{
  var md = `{DISCLAIMER_TEXT.replace('`','\\`').replace('$','\\$')}`;
  var html = md.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>').replace(/\\n\\n/g, '</p><p>').replace(/\\n/g, '<br>');
  document.getElementById('disclaimerText').innerHTML = '<h2>\u26A0\uFE0F Disclaimer</h2><p>'+html+'</p>';
  document.getElementById('disclaimerOverlay').style.display='flex';
}}

// =====================================================================
// EVENT WIRING (direct listeners for static elements)
// =====================================================================
document.getElementById('logo').addEventListener('click', function(){{ showView('home'); }});
document.getElementById('logo').addEventListener('keydown', function(e){{ if(e.key==='Enter'||e.key===' '){{ e.preventDefault(); showView('home'); }} }});
document.getElementById('hamburgerBtn').addEventListener('click', openDrawer);
document.getElementById('drawerBackdrop').addEventListener('click', closeDrawer);
document.getElementById('searchTrigger').addEventListener('click', openSearch);
document.getElementById('closeSearchBtn').addEventListener('click', closeSearch);
document.getElementById('searchBackdrop').addEventListener('click', closeSearch);
document.getElementById('globalSearchInput').addEventListener('input', function(e){{ renderSearchResults(e.target.value); }});
document.getElementById('themeBtn').addEventListener('click', function(){{
  var cur = document.documentElement.getAttribute('data-theme');
  setTheme(THEMES[(THEMES.indexOf(cur)+1) % THEMES.length]);
}});
function doLogout(){{ fetch('/api/logout',{{method:'POST'}}).then(function(){{ window.location.reload(); }}); }}
document.getElementById('headerLogout').addEventListener('click', doLogout);
document.getElementById('drawerLogout').addEventListener('click', function(){{ closeDrawer(); doLogout(); }});
document.getElementById('filterToggleBtn').addEventListener('click', openSheet);
document.getElementById('guidelinesFilterToggleBtn').addEventListener('click', openSheet);
document.getElementById('sheetBackdrop').addEventListener('click', closeSheet);
document.getElementById('bookmarksSearch').addEventListener('input', renderBookmarks);
document.getElementById('theorySearch').addEventListener('input', function(){{
  clearTimeout(_theorySearchTimers.decks);
  _theorySearchTimers.decks = setTimeout(function(){{
    renderTheoryDecks();
    _theoryReplace();
  }}, 200);
}});
document.getElementById('theoryNotesSearch').addEventListener('input', function(){{
  clearTimeout(_theorySearchTimers.notes);
  _theorySearchTimers.notes = setTimeout(function(){{
    renderTheoryNotes();
    _theoryReplace();
  }}, 200);
}});
document.getElementById('bookmarksNewFolderBtn').addEventListener('click', function(){{
  document.getElementById('bookmarksNewFolderRow').classList.add('show');
  renderFolderSwatches(_bmNewFolderColor);
  document.getElementById('bookmarksNewFolderName').focus();
}});
document.getElementById('bookmarksCancelFolderBtn').addEventListener('click', function(){{
  document.getElementById('bookmarksNewFolderRow').classList.remove('show');
  document.getElementById('bookmarksNewFolderName').value = '';
}});
document.getElementById('bookmarksCreateFolderBtn').addEventListener('click', createBookmarkFolder);
document.getElementById('bookmarksNewFolderName').addEventListener('keydown', function(e){{ if(e.key==='Enter') createBookmarkFolder(); }});
document.getElementById('papersSearch').addEventListener('input', renderPapers);
document.getElementById('papersSort').addEventListener('change', renderPapers);
document.getElementById('guidelinesSearch').addEventListener('input', renderGuidelines);
document.getElementById('guidelinesSort').addEventListener('change', renderGuidelines);
document.getElementById('pearlsSearch').addEventListener('input', function(){{ pearlsShown = pearlsPageSize; renderPearls(); }});
document.getElementById('pearlsSort').addEventListener('change', renderPearls);
document.getElementById('loadMorePearls').addEventListener('click', function(){{ pearlsShown += pearlsPageSize; renderPearls(); }});
document.getElementById('closeReader').addEventListener('click', function(){{
  if(_readerHistoryStack.length>0){{
    var prev = _readerHistoryStack.pop();
    openReader(prev.entry, prev.kind);
  }} else {{
    closeReader();
  }}
}});
document.getElementById('readerBackdrop').addEventListener('click', closeReader);
document.getElementById('readerBody').addEventListener('scroll', function(){{
  var pct = this.scrollTop / (this.scrollHeight - this.clientHeight) * 100;
  document.getElementById('readerProgress').style.width = Math.min(100, Math.max(0, pct)) + '%';
}});
document.getElementById('scrollTopBtn').addEventListener('click', function(){{ window.scrollTo({{top:0,behavior:'smooth'}}); }});
document.getElementById('specPapersSort').addEventListener('change', function(){{
  var specViewTitle = document.getElementById('specViewTitle').textContent;
  if(specViewTitle) renderSpecialty(specViewTitle);
}});
document.getElementById('specGuidelinesSort').addEventListener('change', function(){{
  var specViewTitle = document.getElementById('specViewTitle').textContent;
  if(specViewTitle) renderSpecialty(specViewTitle);
}});
window.addEventListener('scroll', function(){{
  document.getElementById('scrollTopBtn').classList.toggle('visible', window.scrollY>400);
}});
window.addEventListener('popstate', function(e){{
  if(document.body.classList.contains('reader-open')){{
    if(_readerHistoryStack.length>0){{
      var prev = _readerHistoryStack.pop();
      openReader(prev.entry, prev.kind);
    }} else {{
      closeReader();
    }}
    return;
  }}
  if(document.body.classList.contains('drawer-open')){{ closeDrawer(); return; }}
  if(document.body.classList.contains('sheet-open')){{ closeSheet(); return; }}
  if(document.body.classList.contains('search-open')){{ closeSearch(); return; }}
}});
document.getElementById('aiFab').addEventListener('click', function(){{ document.body.classList.toggle('ai-open'); }});
document.getElementById('subscribeBtn').addEventListener('click', function(){{
  showToast('Coming soon — redirecting to Google Form for now.');
  window.open('{SUBSCRIBE_FORM_URL}', '_blank');
}});
document.getElementById('unsubscribeBtn').addEventListener('click', function(){{
  showToast('Coming soon — redirecting to Google Form for now.');
  window.open('{UNSUBSCRIBE_FORM_URL}', '_blank');
}});
document.getElementById('feedbackBtn').addEventListener('click', function(){{
  window.open('{FEEDBACK_FORM_URL}', '_blank');
}});

// Trial filter/clear buttons
var trialFilterBtn = document.getElementById('trialFilterBtn');
if(trialFilterBtn) trialFilterBtn.addEventListener('click', filterTrials);
var trialClearBtn = document.getElementById('trialClearBtn');
if(trialClearBtn) trialClearBtn.addEventListener('click', clearTrialFilters);
// Condensed filter/clear buttons
var condFilterBtn = document.getElementById('condensedFilterBtn');
if(condFilterBtn) condFilterBtn.addEventListener('click', filterCondensed);
var condClearBtn = document.getElementById('condensedClearBtn');
if(condClearBtn) condClearBtn.addEventListener('click', clearCondensedFilters);
// Trial detail back button
var trialDetailBack = document.getElementById('trialDetailBackBtn');
if(trialDetailBack) trialDetailBack.addEventListener('click', function(){{ showView('trials-esbicm'); }});

// =====================================================================
// DELEGATED EVENT HANDLING (for dynamically rendered elements)
// =====================================================================
document.addEventListener('click', function(e){{
  if(e.target.closest('[data-close-search]')) closeSearch();

  /* Re-open disclaimer from hamburger */
  if(e.target.closest('[data-open-disclaimer]')){{
    closeDrawer();
    var md = `{DISCLAIMER_TEXT.replace('`','\\\\`').replace('$','\\\\$')}`;
    var html = md.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>').replace(/\\n\\n/g, '</p><p>').replace(/\\n/g, '<br>');
    document.getElementById('disclaimerText').innerHTML = '<h2>\u26A0\uFE0F Disclaimer</h2><p>'+html+'</p>';
    document.getElementById('disclaimerOverlay').style.display='flex';
    return;
  }}

  var openPaperBtn = e.target.closest('[data-open-paper]');
  if(openPaperBtn){{ var id=openPaperBtn.dataset.openPaper; var paper=baseDataset.find(function(x){{ return x.id===id; }}); if(paper) openReader(paper,'paper'); return; }}

  var openPearlBtn = e.target.closest('[data-open-pearl]');
  if(openPearlBtn){{
    var pid = openPearlBtn.dataset.openPearl;
    if(pid==='day'){{ if(_pearlOfDay) openReader(_pearlOfDay,'pearl'); return; }}
    var pearl = allPearls.find(function(x){{ return String(x.id)===String(pid); }});
    if(pearl) openReader(pearl,'pearl'); return;
  }}

  var navBtn = e.target.closest('[data-view]');
  if(navBtn){{ showView(navBtn.dataset.view); return; }}

  var specTile = e.target.closest('[data-spec-jump]');
  if(specTile){{ jumpToSpecialty(specTile.dataset.specJump); return; }}

  var pearlChip = e.target.closest('[data-pearl-chip]');
  if(pearlChip){{
    var name = pearlChip.dataset.pearlChip;
    if(activePearlSpecs.has(name)) activePearlSpecs.delete(name); else activePearlSpecs.add(name);
    pearlsShown = pearlsPageSize; renderPearlChips(); renderPearls(); return;
  }}
  if(e.target.closest('[data-pearl-chip-reset]')){{
    activePearlSpecs = new Set(SPECS.map(function(s){{ return s.name; }}));
    pearlsShown = pearlsPageSize; renderPearlChips(); renderPearls(); return;
  }}
  if(e.target.closest('[data-pearl-chip-uncheck]')){{
    activePearlSpecs = new Set();
    pearlsShown = pearlsPageSize; renderPearlChips(); renderPearls(); return;
  }}

  /* Subtopic chips in specialty view */
  var subtopicBtn = e.target.closest('[data-subtopic]');
  if(subtopicBtn){{
    activeSubtopic = subtopicBtn.dataset.subtopic;
    var specName = document.getElementById('specViewTitle').textContent;
    if(specName) renderSpecialty(specName);
    return;
  }}
  if(e.target.closest('[data-subtopic-clear]')){{
    activeSubtopic = null;
    var specName = document.getElementById('specViewTitle').textContent;
    if(specName) renderSpecialty(specName);
    return;
  }}

  /* Pearl navigation (prev/next) */
  var pearlNav = e.target.closest('[data-pearl-nav]');
  if(pearlNav){{
    var step = pearlNav.dataset.pearlNav==='next' ? 1 : -1;
    var targetIdx = _currentPearlIndex + step;
    if(targetIdx>=0 && targetIdx<_currentPearlList.length){{
      _readerHistoryStack = [];
      openReader(_currentPearlList[targetIdx], 'pearl');
    }}
    return;
  }}

  /* Open pearl article in same reader */
  var openArticle = e.target.closest('[data-open-pearl-article]');
  if(openArticle){{
    var pearlId = openArticle.dataset.openPearlArticle;
    var pearl = allPearls.find(function(p){{ return String(p.id)===String(pearlId); }});
    if(pearl && pearl.file_name){{
      var pdfFn = pearl.file_name.replace(/\\.json$/, '.pdf');
      var paper = baseDataset.find(function(d){{ return d.file_name === pdfFn; }});
      if(paper){{
        _readerHistoryStack.push({{kind:'pearl', entry:pearl}});
        openReader(paper, 'paper');
      }}
    }}
    return;
  }}

  /* Apply filters button */
  var applyBtn = e.target.closest('.apply-btn');
  if(applyBtn){{
    var container = applyBtn.closest('#filterPanelDesktop, #filterSheetBody, #filterPanelGuidelines');
    if(container){{
      SPECS.forEach(function(s){{ var el = container.querySelector('[data-spec="'+s.name+'"]'); if(el) filterState.specialties[s.name] = el.checked; }});
      renderFilterCheckboxes();
    }}
    var activeView = document.querySelector('.view.active');
    if(activeView){{
      if(activeView.id==='view-papers') renderPapers();
      if(activeView.id==='view-guidelines') renderGuidelines();
    }}
    if(container && container.id==='filterSheetBody') closeSheet();
    return;
  }}

  var resetBtn = e.target.closest('.filter-reset');
  if(resetBtn){{
    SPECS.forEach(function(s){{ filterState.specialties[s.name] = true; }});
    renderFilterCheckboxes();
    var activeView = document.querySelector('.view.active');
    if(activeView){{
      if(activeView.id==='view-papers') renderPapers();
      if(activeView.id==='view-guidelines') renderGuidelines();
    }}
    return;
  }}

  /* specialty panel toggle */
  var specPanelHead = e.target.closest('.spec-panel-head');
  if(specPanelHead){{
    var panel = specPanelHead.closest('.spec-panel');
    if(panel) panel.classList.toggle('open');
    return;
  }}
  var collapseBtn = e.target.closest('.spec-panel .collapse-btn');
  if(collapseBtn){{
    var panel = collapseBtn.closest('.spec-panel');
    if(panel) panel.classList.remove('open');
    return;
  }}

  var readerFontBtn = e.target.closest('[data-reader-font]');
  if(readerFontBtn){{
    document.querySelector('.reader-body').style.setProperty('--reader-fs', readerFontBtn.dataset.readerFont+'rem');
    document.querySelectorAll('#readerFontChips .size-chip').forEach(function(c){{ c.classList.toggle('active', c===readerFontBtn); }});
    return;
  }}

  var fontChip = e.target.closest('[data-font-px]');
  if(fontChip){{ setSiteFontSize(+fontChip.dataset.fontPx); return; }}

  var themeChip = e.target.closest('[data-theme-choice]');
  if(themeChip){{ setTheme(themeChip.dataset.themeChoice); return; }}

  /* Trial specialty grid tile */
  var trialSpecTile = e.target.closest('[data-trial-spec]');
  if(trialSpecTile){{ renderTrialsSpecialty(trialSpecTile.dataset.trialSpec); return; }}

  /* Condensed trial spec tile */
  var condensedSpecTile = e.target.closest('[data-condensed-spec]');
  if(condensedSpecTile){{ renderCondensedSystem(condensedSpecTile.dataset.condensedSpec); return; }}

  /* Open condensed trial detail */
  var condensedCard = e.target.closest('[data-open-condensed]');
  if(condensedCard){{
    var parts = condensedCard.dataset.openCondensed.split('/');
    openCondensedTrialDetail(parts[0], parts[1]);
    return;
  }}

  /* Open trial detail from card */
  var trialCard = e.target.closest('[data-open-trial]');
  if(trialCard){{
    var slug = trialCard.dataset.openTrial;
    var idx = parseInt(trialCard.dataset.idx, 10);
    if(!isNaN(idx) && idx>=0 && idx<_currentTrialList.length){{
      openTrialDetail(slug, _currentTrialList, idx);
    }} else {{
      openTrialDetail(slug, [], -1);
    }}
    return;
  }}

  /* Trials subtopic chips */
  var trialSubBtn = e.target.closest('#trialsSubtopicChips .subtopic-chip');
  if(trialSubBtn){{
    document.querySelectorAll('#trialsSubtopicChips .subtopic-chip').forEach(function(c){{ c.classList.remove('active'); }});
    trialSubBtn.classList.add('active');
    var st = trialSubBtn.dataset.st || '';
    var name = document.getElementById('trialsSpecTitle').textContent;
    _filterTrialsBySpecialty(name, st);
    return;
  }}

  /* Close trial overlays on backdrop click */
  if(e.target.matches('.trial-overlay-backdrop')){{
    e.target.style.display = 'none';
  }}

  /* Bookmarks */
  var bmToggle = e.target.closest('[data-bookmark-toggle]');
  if(bmToggle){{ toggleBookmark(bmToggle.dataset.bookmarkToggle); return; }}

  var bmOpen = e.target.closest('[data-bookmark-open]');
  if(bmOpen){{ openBookmark(bmOpen.dataset.bookmarkOpen); return; }}

  var bmDel = e.target.closest('[data-bookmark-del]');
  if(bmDel){{ removeBookmark(bmDel.dataset.bookmarkDel); return; }}

  var bmFolderAll = e.target.closest('[data-bm-folder-all]');
  if(bmFolderAll){{ _bookmarksFolderFilter = null; renderBookmarks(); return; }}

  var bmFolder = e.target.closest('[data-bm-folder]');
  if(bmFolder){{ _bookmarksFolderFilter = bmFolder.dataset.bmFolder; renderBookmarks(); return; }}

  var bmFolderRename = e.target.closest('[data-bm-folder-rename]');
  if(bmFolderRename){{ renameBookmarkFolder(bmFolderRename.dataset.bmFolderRename); return; }}

  var bmFolderDel = e.target.closest('[data-bm-folder-del]');
  if(bmFolderDel){{ deleteBookmarkFolder(bmFolderDel.dataset.bmFolderDel); return; }}

  var bmColor = e.target.closest('[data-bm-color]');
  if(bmColor){{ _bmNewFolderColor = bmColor.dataset.bmColor; renderFolderSwatches(_bmNewFolderColor); return; }}

  /* Theory flashcards */
  var theoryModeBtn = e.target.closest('[data-theory-mode-view]');
  if(theoryModeBtn){{
    var tmode = theoryModeBtn.dataset.theoryModeView;
    renderTheoryPane(tmode);
    _theoryPush();
    _focusCrumb();
    return;
  }}

  var theoryCrumb = e.target.closest('[data-crumb]');
  if(theoryCrumb){{ theoryGoTo(parseInt(theoryCrumb.dataset.crumb,10)||0); return; }}

  var theoryFontBtn = e.target.closest('[data-theory-font]');
  if(theoryFontBtn){{
    var tscope = theoryFontBtn.dataset.theoryFont;
    var tval = parseFloat(theoryFontBtn.dataset.theoryFontVal)||1;
    try {{ localStorage.setItem('hackccm_theoryFont_'+tscope, String(tval)); }} catch(e){{}}
    applyTheoryFont(tscope);
    document.querySelectorAll('[data-theory-font="'+tscope+'"]').forEach(function(c){{
      c.classList.toggle('active', c===theoryFontBtn);
    }});
    return;
  }}

  var theoryNoteBtn = e.target.closest('[data-theory-note]');
  if(theoryNoteBtn){{
    if(!_theoryViewActive()) showView('theory');
    openTheoryNote(theoryNoteBtn.dataset.theoryNote); return;
  }}

  var theoryNoteNavBtn = e.target.closest('[data-theory-note-nav]');
  if(theoryNoteNavBtn){{ theoryNoteNav(parseInt(theoryNoteNavBtn.dataset.theoryNoteNav,10)||0); return; }}

  var exportNoteBtn = e.target.closest('[data-export-note]');
  if(exportNoteBtn){{ window.open('/export/print?'+exportNoteBtn.dataset.exportNote, '_blank', 'noopener'); return; }}
  var exportPaperBtn = e.target.closest('[data-export-paper]');
  if(exportPaperBtn){{ window.open('/export/print?'+exportPaperBtn.dataset.exportPaper, '_blank', 'noopener'); return; }}

  var theoryTableOpen = e.target.closest('[data-theory-table-open]');
  if(theoryTableOpen){{ openTheoryTableOverlay(theoryTableOpen); return; }}
  var theoryTableClose = e.target.closest('[data-theory-table-close]');
  if(theoryTableClose){{ closeTheoryTableOverlay(); return; }}
  var theoryTableFit = e.target.closest('[data-theory-table-fit]');
  if(theoryTableFit){{ theoryTableToggleFit(); return; }}

  var theoryCardSearch = e.target.closest('[data-theory-card]');
  if(theoryCardSearch){{
    var tRef = theoryDeckFromCardId(theoryCardSearch.dataset.theoryCard);
    if(tRef){{
      if(!_theoryViewActive()) showView('theory');
      openTheoryDeck(tRef.deck.id, tRef.idx);
    }}
    return;
  }}

  var theoryListOpen = e.target.closest('[data-theory-list-open]');
  if(theoryListOpen && _currentDeck){{ openTheoryCardList(_currentDeck.id); return; }}

  var theoryDone = e.target.closest('[data-theory-done]');
  if(theoryDone){{ theoryStepBackFromStudy(); return; }}

  var theoryCardOpen = e.target.closest('[data-theory-card-open]');
  if(theoryCardOpen && _currentDeck){{
    _theoryListCollapsed = true;
    renderTheoryCardList();
    openTheoryDeck(_currentDeck.id, theoryCardOpen.dataset.theoryCardOpen, true);
    _theoryStudyFromList = true;
    return;
  }}

  var theoryListToggle = e.target.closest('[data-theory-list-toggle]');
  if(theoryListToggle){{
    _theoryListCollapsed = !_theoryListCollapsed;
    renderTheoryCardList();
    return;
  }}

  var theoryDeckBtn = e.target.closest('[data-theory-deck]');
  if(theoryDeckBtn){{ openTheoryDeck(theoryDeckBtn.dataset.theoryDeck, 0); return; }}

  var theoryChip = e.target.closest('[data-theory-chip]');
  if(theoryChip){{
    var s = theoryChip.dataset.theoryChip;
    if(_theoryActiveSpecs.has(s)) _theoryActiveSpecs.delete(s); else _theoryActiveSpecs.add(s);
    renderTheoryChips(); renderTheoryDecks(); _theoryReplace(); return;
  }}

  var theoryReset = e.target.closest('[data-theory-chip-reset]');
  if(theoryReset){{ _theoryActiveSpecs = new Set(allFlashcardDecks.map(function(d){{ return d.specialty; }})); renderTheoryChips(); renderTheoryDecks(); _theoryReplace(); return; }}

  var theoryUncheck = e.target.closest('[data-theory-chip-uncheck]');
  if(theoryUncheck){{ _theoryActiveSpecs = new Set(); renderTheoryChips(); renderTheoryDecks(); _theoryReplace(); return; }}

  var theorySavedOnly = e.target.closest('[data-theory-saved-only]');
  if(theorySavedOnly){{ _theorySavedOnly = !_theorySavedOnly; renderTheoryChips(); renderTheoryDecks(); _theoryReplace(); return; }}
  var notesSavedOnly = e.target.closest('[data-notes-saved-only]');
  if(notesSavedOnly){{ _notesSavedOnly = !_notesSavedOnly; renderTheoryNotes(); _theoryReplace(); return; }}
  var notesSpec = e.target.closest('[data-notes-spec]');
  if(notesSpec){{
    var s = notesSpec.getAttribute('data-notes-spec');
    if(_notesActiveSpecs.has(s)) _notesActiveSpecs.delete(s);
    else _notesActiveSpecs.add(s);
    if(!_notesActiveSpecs.size) _notesActiveSubtopic = null;
    else if(_notesActiveSpecs.size>1) _notesActiveSubtopic = null;
    renderTheoryNotes(); _theoryReplace(); return;
  }}
  var notesSub = e.target.closest('[data-notes-sub]');
  if(notesSub){{
    _notesActiveSubtopic = (_notesActiveSubtopic===notesSub.getAttribute('data-notes-sub')) ? null : notesSub.getAttribute('data-notes-sub');
    renderTheoryNotes(); _theoryReplace(); return;
  }}
  var notesClearAll = e.target.closest('[data-notes-clear-all]');
  if(notesClearAll){{ _notesSavedOnly = false; _notesActiveSpecs = new Set(); _notesActiveSubtopic = null; renderTheoryNotes(); _theoryReplace(); return; }}

  var theorySub = e.target.closest('[data-theory-subtopic]');
  if(theorySub){{
    var t = theorySub.dataset.theorySubtopic;
    _theoryActiveSubtopic = (_theoryActiveSubtopic===t) ? null : t;
    renderTheorySubtopicChips(); renderTheoryDecks(); _theoryReplace(); return;
  }}

  var theorySubClear = e.target.closest('[data-theory-subtopic-clear]');
  if(theorySubClear){{ _theoryActiveSubtopic = null; renderTheorySubtopicChips(); renderTheoryDecks(); _theoryReplace(); return; }}

  var theoryTagClear = e.target.closest('[data-theory-tag-clear]');
  if(theoryTagClear && _currentDeck){{
    _theoryActiveSubtopic = null;
    _theoryCardOrder = _currentDeck.cards.map(function(c, i){{ return i; }});
    if(_theoryCardOrder.indexOf(_currentCardIdx)===-1) _currentCardIdx = 0;
    _theoryFlipped = false;
    renderTheoryChips();
    renderTheoryCard();
    _theoryReplace();
    return;
  }}

  var theoryNavBtn = e.target.closest('[data-theory-nav]');
  if(theoryNavBtn){{ theoryNav(parseInt(theoryNavBtn.dataset.theoryNav,10)||0); return; }}

  var theoryDot = e.target.closest('[data-theory-dot]');
  if(theoryDot){{
    var tpos = parseInt(theoryDot.dataset.theoryDot,10)||0;
    if(_theoryCardOrder[tpos]!=null){{
      _currentCardIdx = _theoryCardOrder[tpos];
      _theoryFlipped = false;
      renderTheoryCard();
      _theoryReplace();
    }}
    return;
  }}

  var theoryMode = e.target.closest('[data-theory-mode]');
  if(theoryMode){{ theorySetViewMode(theoryMode.dataset.theoryMode); return; }}

  var theoryFlipInner = e.target.closest('#theoryFlipInner');
  if(theoryFlipInner){{ _theoryFlipped = !_theoryFlipped; theoryFlipInner.classList.toggle('flipped', _theoryFlipped); return; }}
}});

document.addEventListener('change', function(e){{
  var container = e.target.closest('#filterPanelDesktop, #filterSheetBody, #filterPanelGuidelines');
  if(container){{
    if(e.target.classList.contains('all-check')){{
      container.querySelectorAll('[data-spec]').forEach(function(b){{ b.checked = e.target.checked; }});
    }}
    SPECS.forEach(function(s){{ var el = container.querySelector('[data-spec="'+s.name+'"]'); if(el) filterState.specialties[s.name] = el.checked; }});
    renderFilterCheckboxes();
  }}
  var bmFolderSel = e.target.closest('[data-bookmark-folder]');
  if(bmFolderSel){{ setBookmarkFolder(bmFolderSel.dataset.bookmarkFolder, e.target.value || null); return; }}
  var bmTags = e.target.closest('[data-bookmark-tags]');
  if(bmTags){{ setBookmarkTags(bmTags.dataset.bookmarkTags, e.target.value); return; }}
}});

document.addEventListener('keydown', function(e){{
  if(e.key==='Escape'){{
    if(_theoryTableOverlayOpen){{ closeTheoryTableOverlay(); }}
    else if(_theoryStudyVisible()){{ theoryStepBackFromStudy(); }}
    else if(document.getElementById('theoryCardList') && document.getElementById('theoryCardList').style.display!=='none'){{ theoryBackToBrowser(); }}
    else if(document.getElementById('theoryNoteReader') && document.getElementById('theoryNoteReader').style.display!=='none'){{ theoryNotesBack(); }}
    closeSearch(); closeDrawer(); closeSheet(); closeReader(); document.body.classList.remove('ai-open');
  }}
  if((e.ctrlKey||e.metaKey)&&e.key==='k'){{ e.preventDefault(); openSearch(); }}
  if((e.key==='Enter'||e.key===' ')&&e.target.matches('[role="button"]')){{ e.preventDefault(); e.target.click(); }}
  if(_theoryStudyVisible() && !e.target.matches('input,textarea,select')){{
    if(e.key==='ArrowRight'){{ theoryNav(1); }}
    if(e.key==='ArrowLeft'){{ theoryNav(-1); }}
  }}
}});

// =====================================================================
// INIT
// =====================================================================
(function init(){{
  // Load saved prefs
  try {{
    var savedTheme = localStorage.getItem('hackccm_theme');
    if(savedTheme) setTheme(savedTheme); else setTheme('dim');
    var savedFont = localStorage.getItem('hackccm_fontSize');
    if(savedFont) setSiteFontSize(+savedFont); else setSiteFontSize(16);
  }} catch(e){{ setTheme('dim'); setSiteFontSize(16); }}

  // Hide nav/drawer links for disabled features (admins see all)
  if (!USER_IS_ADMIN) {{
    var navFeatureMap = {{
      'papers': 'papers',
      'guidelines': 'guidelines',
      'pearls': 'pearls',
      'trials': 'trials',
      'trials-esbicm': 'trials',
      'trials-condensed': 'condensed_trials',
      'trials-specialty': 'trials',
      'trials-detail': 'trials_detail',
      'condensed-system': 'condensed_trials',
      'condensed-detail': 'trials_detail',
      'bookmarks': 'bookmarks',
      'theory': 'theory'
    }};
    Object.keys(navFeatureMap).forEach(function(viewName) {{
      var feature = navFeatureMap[viewName];
      if (!USER_FEATURES[feature]) {{
        document.querySelectorAll('[data-view="' + viewName + '"]').forEach(function(el) {{
          el.style.display = 'none';
        }});
      }}
    }});
    // Hide search trigger if search feature is disabled
    if (!USER_FEATURES['search']) {{
      var searchEl = document.getElementById('searchTrigger');
      if (searchEl) searchEl.style.display = 'none';
    }}
  }}

  renderFilterCheckboxes();
  loadBookmarks();
  showView('home');

  // Deep links + browser history:
  //   ?theory=flashcards[&system=S&subtopic=T&card=<uuid>][&q=..][&saved=1]
  //   ?theory=notes[&note=<file>][&q=..][&saved=1]
  _restoring = true;
  try {{ _applyTheoryDeepLink(new URLSearchParams(window.location.search)); }} catch(e){{}}
  _restoring = false;
  window.addEventListener('popstate', function(){{
    _restoring = true;
    try {{ _applyTheoryDeepLink(new URLSearchParams(window.location.search)); }} catch(e){{}}
    _restoring = false;
  }});
}})();
</script>
</body>
</html>"""
    resp = HTMLResponse(content=html)
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    if LOCAL_DEV_MODE and not request.cookies.get(SESSION_COOKIE_NAME):
        _, dev_sid = _local_dev_login()
        resp.set_cookie(key=SESSION_COOKIE_NAME, value=dev_sid, max_age=SESSION_MAX_AGE, httponly=True, samesite="lax", secure=COOKIE_SECURE)
    return resp

# =====================================================================
# API ENDPOINTS
# =====================================================================

@app.get("/api/debug")
async def api_debug():
    from acumen_core import kv as _kvmod
    return {"kv_backend": _kvmod.kv_backend(), "vercel": os.environ.get("VERCEL", "")}

@app.post("/api/signup")
async def api_signup(body: dict, response: Response):
    try:
        email = str(body.get("email", "")).strip().lower()
        password = body.get("password", "")
        if not email or "@" not in email:
            raise HTTPException(400, "Valid email required")
        if len(password) < 8:
            raise HTTPException(400, "Password must be at least 8 characters")
        if _kv_get(f"auth:users:{email}"):
            raise HTTPException(409, "An account with this email already exists")
        user = {
            "email": email,
            "first_name": str(body.get("first_name", "")).strip(),
            "last_name": str(body.get("last_name", "")).strip(),
            "workplace": str(body.get("workplace", "")).strip(),
            "city": str(body.get("city", "")).strip(),
            "password_hash": _hash_password(password),
            "created_at": datetime.utcnow().isoformat(),
            "features": {},
        }
        _kv_set(f"auth:users:{email}", user)
        sid = _session_id()
        _kv_set(f"auth:session:{sid}", {"email": email, "created_at": datetime.utcnow().isoformat()}, ttl=SESSION_MAX_AGE)
        response.set_cookie(key=SESSION_COOKIE_NAME, value=sid, max_age=SESSION_MAX_AGE, httponly=True, samesite="lax", secure=COOKIE_SECURE)
        return {"ok": True, "email": email}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        return JSONResponse(500, {"error": type(e).__name__, "detail": str(e), "traceback": traceback.format_exc()})

@app.post("/api/login")
async def api_login(body: dict, response: Response):
    try:
        email = str(body.get("email", "")).strip().lower()
        password = body.get("password", "")
        if not email or not password:
            raise HTTPException(400, "Email and password required")
        user = _kv_get(f"auth:users:{email}")
        if not user or not isinstance(user, dict):
            raise HTTPException(401, "Invalid email or password")
        pwh = user.get("password_hash")
        if not pwh:
            raise HTTPException(401, "Invalid email or password")
        if not _verify_password(password, pwh):
            raise HTTPException(401, "Invalid email or password")
        sid = _session_id()
        _kv_set(f"auth:session:{sid}", {"email": email, "created_at": datetime.utcnow().isoformat()}, ttl=SESSION_MAX_AGE)
        response.set_cookie(key=SESSION_COOKIE_NAME, value=sid, max_age=SESSION_MAX_AGE, httponly=True, samesite="lax", secure=COOKIE_SECURE)
        return {"ok": True, "email": email}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        return JSONResponse(500, {"error": type(e).__name__, "detail": str(e), "traceback": traceback.format_exc()})

@app.post("/api/logout")
async def api_logout(request: Request, response: Response):
    sid = request.cookies.get(SESSION_COOKIE_NAME)
    if sid:
        _kv_delete(f"auth:session:{sid}")
    response.delete_cookie(SESSION_COOKIE_NAME)
    return {"ok": True}

@app.get("/api/me")
async def api_me(request: Request):
    user = _get_session_user(request)
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

@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


# =====================================================================
# BOOKMARKS (per-user, stored in KV under user:{email}:bookmarks)
# =====================================================================

@app.get("/api/bookmarks")
async def api_bookmarks_list(request: Request):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_feature(user, "bookmarks")
    return _user_data(user["email"], "bookmarks")

@app.post("/api/bookmarks")
async def api_bookmarks_add(request: Request, body: dict):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_feature(user, "bookmarks")
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

@app.patch("/api/bookmarks")
async def api_bookmarks_update(request: Request, body: dict):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_feature(user, "bookmarks")
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

@app.delete("/api/bookmarks")
async def api_bookmarks_delete(request: Request, ref: str = ""):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_feature(user, "bookmarks")
    email = user["email"]
    data = _user_data(email, "bookmarks")
    items = data.setdefault("items", {})
    if ref in items:
        del items[ref]
        _save_user_data(email, "bookmarks", data)
    return {"ok": True}

@app.post("/api/bookmarks/folders")
async def api_bookmarks_folder_add(request: Request, body: dict):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_feature(user, "bookmarks")
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
        "created_at": datetime.utcnow().isoformat(),
    }
    folders[fid] = folder
    _save_user_data(email, "bookmarks", data)
    return {"ok": True, "id": fid, "folder": folder}

@app.patch("/api/bookmarks/folders")
async def api_bookmarks_folder_update(request: Request, body: dict):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_feature(user, "bookmarks")
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

@app.delete("/api/bookmarks/folders")
async def api_bookmarks_folder_delete(request: Request, ref: str = ""):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_feature(user, "bookmarks")
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


@app.get("/api/summary")
async def get_json_summary(request: Request, file_name: str, system: str = "General", type: str = "Unclassified"):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_feature(user, "papers")
    base_name = os.path.splitext(file_name)[0]
    clean_system = "".join(x for x in str(system) if x.isalnum() or x in "._- ").strip()
    clean_type = "".join(x for x in str(type) if x.isalnum() or x in "._- ").strip()
    target = os.path.join(OUTPUT_DIR, clean_system, clean_type, f"{base_name}.json")
    if not os.path.exists(target):
        for root, dirs, files in os.walk(OUTPUT_DIR):
            if f"{base_name}.json" in files:
                target = os.path.join(root, f"{base_name}.json")
                break
    if not os.path.exists(target):
        return JSONResponse(status_code=404, content={"error": f"Summary not found: {base_name}.json"})
    try:
        with open(target, "r", encoding="utf-8") as f:
            payload = json.load(f)
        content = payload.get("clinical_summary_markdown", "")
        authors = payload.get("primary_authors", "")
        if not content:
            content = format_new_schema_as_markdown(payload)
        if not authors:
            authors = payload.get("authors", "")
        if not authors:
            issuing = payload.get("issuing_bodies", [])
            if issuing:
                authors = ", ".join(issuing)
        if not authors:
            authors = "Unknown Authors"
        return {
            "content": content,
            "authors": authors,
            "key_pearls": payload.get("key_pearls", []),
            "recommendations": payload.get("recommendation_blocks", []),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/export/print")
async def export_print(request: Request, kind: str = "paper", file_name: str = "", title: str = ""):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    feature = "theory" if kind == "note" else "papers"
    _require_feature(user, feature)
    the_title = ""
    meta_html = ""
    content = ""
    kind_label = "Print Friendly"
    try:
        if kind == "note":
            note = None
            base = os.path.join(OUTPUT_DIR, "Theory MDs")
            if os.path.isdir(base):
                for root, dirs, files in os.walk(base):
                    if file_name in files:
                        try:
                            with open(os.path.join(root, file_name), "r", encoding="utf-8", errors="replace") as f:
                                note = {"md": f.read()}
                        except Exception:
                            pass
                        break
            if not note:
                return JSONResponse(status_code=404, content={"error": f"Note not found: {file_name}"})
            content = note["md"]
            stem = os.path.splitext(file_name)[0].replace("_", " ")
            m = re.search(r"^\s*#{1,6}\s+(.+?)\s*$", content, re.M)
            t = m.group(1).strip() if m else stem
            title_label = title or t
            meta_html = f"<span>{html.escape(title or t)}</span>"
            kind_label = "Theory Topic"
        else:
            base_name = os.path.splitext(file_name)[0]
            clean_system = "".join(x for x in str(request.query_params.get("system", "General")) if x.isalnum() or x in "._- ").strip()
            clean_type = "".join(x for x in str(request.query_params.get("type", "Other")) if x.isalnum() or x in "._- ").strip()
            target = os.path.join(OUTPUT_DIR, clean_system, clean_type, f"{base_name}.json")
            if not os.path.exists(target):
                for root, dirs, files in os.walk(OUTPUT_DIR):
                    if f"{base_name}.json" in files:
                        target = os.path.join(root, f"{base_name}.json")
                        break
            if not os.path.exists(target):
                return JSONResponse(status_code=404, content={"error": f"Summary not found: {base_name}.json"})
            with open(target, "r", encoding="utf-8") as f:
                payload = json.load(f)
            content = payload.get("clinical_summary_markdown", "") or format_new_schema_as_markdown(payload)
            title_label = payload.get("title") or base_name
            authors = payload.get("primary_authors") or payload.get("authors") or ""
            if not authors:
                issuing = payload.get("issuing_bodies", [])
                if issuing:
                    authors = ", ".join(issuing)
            meta = []
            if authors:
                meta.append(html.escape(authors))
            if payload.get("journal"):
                meta.append(html.escape(str(payload["journal"])))
            if payload.get("year"):
                meta.append(html.escape(str(payload["year"])))
            meta_html = " &middot; ".join(meta)
            kind_label = "Guideline" if str(payload.get("doc_type", "")).lower() == "guideline" else "Paper"
        return HTMLResponse(content=render_printable(title_label, meta_html, content, kind_label))
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/search")
async def search_summaries(request: Request, q: str = ""):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_feature(user, "search")
    if not q.strip():
        return {"matches": []}
    query = q.strip().lower()
    results = []
    if os.path.exists(OUTPUT_DIR):
        for root, dirs, files in os.walk(OUTPUT_DIR):
            for fname in files:
                if not fname.endswith(".json"):
                    continue
                try:
                    fpath = os.path.join(root, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        payload = json.load(f)
                    search_text = extract_search_text(payload)
                    if query in search_text:
                        title, system, article_type, journal = extract_metadata(payload)
                        results.append({"file_name": fname, "title": title, "system": system or "Other", "type": article_type or "Other", "journal": journal})
                except Exception:
                    continue
    return {"matches": results}


@app.get("/api/pearls")
async def get_pearls(request: Request, q: str = "", system: str = "", type: str = "", page: int = 1, limit: int = 50):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_feature(user, "pearls")
    pearls = load_pearls()
    filtered = []
    for p in pearls:
        if q and q.lower() not in str(p.get("pearl", "")).lower() and q.lower() not in str(p.get("source_paper", "")).lower():
            continue
        if system and p.get("system", "") != system:
            continue
        if type and p.get("type", "") != type:
            continue
        filtered.append(p)
    total = len(filtered)
    start = (page - 1) * limit
    end = start + limit
    return {"pearls": filtered[start:end], "total": total, "page": page, "totalPages": (total + limit - 1) // limit if limit > 0 else 1}


@app.get("/api/trials/stats")
async def get_trials_stats(request: Request):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_feature(user, "trials")
    idx = load_trial_index()
    counts = {}
    for t in idx:
        sp = t.get("specialty", "Other")
        counts[sp] = counts.get(sp, 0) + 1
    return {"stats": counts}


@app.get("/api/trials")
async def get_trials(
    request: Request,
    specialty: str = "",
    result_category: str = "",
    trial_type: str = "",
    q: str = "",
    page: int = 1,
    limit: int = 50
):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_feature(user, "trials")
    idx = load_trial_index()
    filtered = []
    for t in idx:
        if specialty and t.get("specialty", "") != specialty:
            continue
        if result_category and t.get("result_category", "") != result_category:
            continue
        if trial_type and t.get("trial_type", "") != trial_type:
            continue
        if q and q.lower() not in t.get("trial_name", "").lower() and q.lower() not in t.get("one_liner", "").lower():
            continue
        filtered.append(t)
    total = len(filtered)
    start = (page - 1) * limit
    end = start + limit
    return {
        "trials": filtered[start:end],
        "total": total,
        "page": page,
        "totalPages": (total + limit - 1) // limit if limit > 0 else 1
    }


@app.get("/api/trial/{slug}")
async def get_trial(request: Request, slug: str):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_feature(user, "trials")
    idx = load_trial_index()
    match = None
    for t in idx:
        if t.get("slug", "") == slug:
            match = t
            break
    if not match:
        return JSONResponse(status_code=404, content={"error": f"Trial not found: {slug}"})
    file_path = match.get("file_path", "")
    target = os.path.join(OUTPUT_DIR, file_path)
    if not os.path.exists(target):
        return JSONResponse(status_code=404, content={"error": f"Trial file not found: {file_path}"})
    try:
        with open(target, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/condensed-trials")
async def get_condensed_trials(request: Request, system: str = ""):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_feature(user, "condensed_trials")
    idx = load_condensed_trial_index()
    if system:
        idx = [c for c in idx if c["system"] == system]
    return {"trials": idx}


@app.get("/api/condensed-trial/{system}/{name}")
async def get_condensed_trial(request: Request, system: str, name: str):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_feature(user, "condensed_trials")
    from urllib.parse import unquote
    system = unquote(system)
    name = unquote(name)
    payload = load_condensed_trial(system, name)
    if payload is None:
        return JSONResponse(status_code=404, content={"error": f"Condensed trial not found: {system}/{name}"})
    return payload


# =====================================================================
# HELPERS
# =====================================================================

def spec_color_from_name(name):
    colors = {
        "Cardiology": "C6554B", "Pulmonology": "3A7CA5", "Infectious Diseases": "4F8A6D",
        "Neurology": "6B5B95", "Nephrology": "B08D57", "Gastroenterology": "10B981",
        "Hematology": "E11D48", "Hepatology": "14B8A6", "Immunology": "A855F7",
        "Sepsis": "F97316", "Trauma": "DC2626", "Endocrinology": "06B6D4",
        "General": "6B7280", "Multisystem": "6366F1",
        "Nutrition": "84CC16", "Obstetrics and Gynecology": "D946EF", "Rheumatology": "0EA5E9",
        "Toxicology": "7C3AED", "Oncology": "059669", "Surgery": "D97706", "Other": "9333EA",
    }
    return colors.get(name, "6B7280")


def bold_labels(text):
    return re.sub(
        r'\b(Strengths|Limitations|Dose|Indication|Adverse effects?|Route|Frequency|'
        r'Duration|Monitoring|Contraindications?|Precautions?|Key Point|Note|Finding|'
        r'Result|Recommendation)\s*:',
        r'**\1:**',
        text
    )


def render_printable(title, meta_html, markdown, kind_label):
    """Standalone, printable HTML page rendering markdown (with KaTeX math).
    Used by /export/print — opens in a new window where the user saves as PDF."""
    esc = html.escape
    page_title = esc(title) if title else "hack.CCM Export"
    html_out = f"""<!DOCTYPE html>
<html lang="en" data-theme="dim">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{page_title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<style>
  :root {{
    --ink:#F1E4CE; --ink-muted:#C4B18C; --border:#3A3226; --accent:#E8B778;
    --bg-sunk:#241F17; --radius:10px;
  }}
  * {{ box-sizing:border-box; }}
  html, body {{ margin:0; padding:0; }}
  body {{ background:#1F1B14; color:var(--ink); font-family:'Atkinson Hyperlegible',sans-serif; font-size:16px; line-height:1.5; }}
  .toolbar {{ position:fixed; top:0; left:0; right:0; display:flex; align-items:center; gap:10px; padding:10px 18px; background:#14100B; border-bottom:1px solid var(--border); z-index:20; }}
  .toolbar .tag {{ font-size:.72rem; letter-spacing:.08em; text-transform:uppercase; color:var(--ink-muted); }}
  .toolbar .btn {{ margin-left:auto; background:var(--accent); color:#1F1B14; border:none; font:inherit; font-weight:700; padding:8px 16px; border-radius:8px; cursor:pointer; }}
  .doc {{ max-width:880px; margin:70px auto 60px; padding:0 22px; }}
  h1.doc-title {{ font-family:'Space Grotesk',sans-serif; font-size:1.7rem; line-height:1.3; margin:10px 0 6px; }}
  .meta {{ color:var(--ink-muted); font-size:.9rem; margin:0 0 22px; }}
  .article h1, .article h2 {{ font-family:'Space Grotesk',sans-serif; }}
  .article h1 {{ font-size:1.45rem; margin:24px 0 10px; }}
  .article h2 {{ font-size:1.25rem; margin:22px 0 8px; }}
  .article h3 {{ font-size:1.08rem; margin:18px 0 8px; }}
  .article p {{ margin:10px 0; }}
  .article ul, .article ol {{ margin:10px 0; padding-left:26px; }}
  .article li {{ margin:4px 0; }}
  .article code {{ font-family:'JetBrains Mono',monospace; font-size:.86em; background:var(--bg-sunk); border-radius:4px; padding:1px 5px; }}
  .article pre {{ background:var(--bg-sunk); border:1px solid #3A3226; border-radius:10px; padding:12px 14px; overflow:auto; }}
  .article blockquote {{ border-left:3px solid var(--accent); margin:12px 0; padding:4px 14px; color:var(--ink-muted); }}
  .article table {{ border-collapse:collapse; width:100%; margin:14px 0; }}
  .article th, .article td {{ border:1px solid #3A3226; padding:7px 10px; text-align:left; vertical-align:top; }}
  .article th {{ background:var(--bg-sunk); font-weight:700; }}
  .article a {{ color:var(--accent); }}
  .article hr {{ border:none; border-top:1px solid #3A3226; margin:18px 0; }}
  .katex-display {{ margin:14px 0; overflow-x:auto; overflow-y:hidden; }}
  @media print {{
    .toolbar {{ display:none; }}
    body {{ background:#fff !important; color:#111 !important; }}
    .doc {{ margin:0 auto; max-width:none; padding:0; }}
    a {{ color:#111 !important; text-decoration:none; }}
    .article table, .article th, .article td {{ border-color:#888; }}
    .article code {{ background:#f0f0f0; }}
  }}
</style>
</head>
<body>
<div class="toolbar"><span class="badge">hack.CCM &middot; {esc(kind_label or '')}</span><button class="btn" onclick="window.print()">&#128196; Print / Save as PDF</button></div>
<div class="doc">
  <h1>{page_title}</h1>
  <div class="meta">{meta_html or ''}</div>
  <article class="article" id="md-content"></article>
</div>
<script>
  var RAW = {json.dumps(markdown or "", ensure_ascii=False)};
  try {{ document.getElementById('md-content').innerHTML = marked.parse(RAW); }} catch(e){{ document.getElementById('md-content').textContent = RAW; }}
  function renderMath(){{
    try{{ if(window.renderMathInElement){{ renderMathInElement(document.getElementById('md-content'),{{delimiters:[{{left:'$$',right:'$$',display:true}},{{left:'\\\\(',right:'\\\\)',display:false}},{{left:'\\\\[',right:'\\\\]',display:true}}],throwOnError:false,strict:'ignore'}}); }} }}catch(e){{}}
  }}
  renderMath();
  window.addEventListener('load', function(){{ setTimeout(function(){{ window.print(); }}, 600); }});
</script>
</body>
</html>"""
    return html_out


def format_new_schema_as_markdown(payload):
    parts = []
    summary = payload.get("one_line_summary", "")
    if summary:
        parts.append(f"> **One-Line Summary:** {summary}\n")
    pearls = payload.get("key_pearls", [])
    if pearls:
        parts.append("## Key Pearls\n" + "\n".join(f"- {p}" for p in pearls) + "\n")
    sections = payload.get("sections", [])
    if sections:
        for s in sections:
            heading = s.get("heading", "")
            content = s.get("content", "")
            section_pearls = s.get("section_pearls", [])
            block = f"## {heading}\n{content}" if heading else content
            if section_pearls:
                block += "\n\n**Section Pearls:**\n" + "\n".join(f"- {sp}" for sp in section_pearls)
            parts.append(block)
    rec_blocks = payload.get("recommendation_blocks", [])
    if rec_blocks:
        for block in rec_blocks:
            topic = block.get("topic", "")
            narrative = block.get("narrative", "")
            block_parts = [f"## {topic}"] if topic else []
            if narrative:
                block_parts.append(narrative)
            for rec in block.get("recommendations", []):
                rec_id = rec.get("rec_id")
                statement = rec.get("statement", "")
                strength = rec.get("strength")
                evidence_grade = rec.get("evidence_grade")
                label = f"[{rec_id}] " if rec_id else ""
                meta_parts = []
                if strength:
                    meta_parts.append(strength)
                if evidence_grade:
                    meta_parts.append(evidence_grade)
                meta = f" *({', '.join(meta_parts)})*" if meta_parts else ""
                block_parts.append(f"- {label}{statement}{meta}")
            parts.append("\n".join(block_parts))
    protocol = payload.get("bedside_protocol", [])
    if protocol:
        protocol_parts = ["## Bedside Protocol"]
        for step in protocol:
            step_num = step.get("step", "")
            title = step.get("title", "")
            action = step.get("action", "")
            protocol_parts.append(f"**Step {step_num}: {title}**\n\n{action}")
        parts.append("\n\n".join(protocol_parts))
    drugs_doses = payload.get("drugs_doses", [])
    if drugs_doses:
        block = "## Drugs & Doses\n"
        for dd in drugs_doses:
            drug = dd.get("drug", "")
            dose = dd.get("dose", "")
            indication = dd.get("indication", "")
            adverse = dd.get("adverse_effects", "")
            block += f"- **{drug}**"
            if dose:
                block += f"  \n  **Dose:** {dose}"
            if indication:
                block += f"  \n  **Indication:** {indication}"
            if adverse:
                block += f"  \n  **Adverse effects:** {adverse}"
            block += "\n"
        parts.append(block)
    strengths = payload.get("strengths_limitations", "")
    if strengths:
        parts.append(f"## Strengths & Limitations\n{bold_labels(strengths)}")
    return "\n\n".join(parts)


def extract_search_text(payload):
    text_parts = []

    # Paper/guideline format
    text_parts.append(payload.get("paper_name", ""))
    text_parts.append(payload.get("clinical_summary_markdown", ""))
    text_parts.append(payload.get("primary_authors", ""))
    text_parts.append(payload.get("journal_name", ""))
    text_parts.append(payload.get("title", ""))
    authors = payload.get("authors", "")
    if not authors:
        issuing = payload.get("issuing_bodies", [])
        if issuing:
            authors = ", ".join(issuing)
    text_parts.append(authors)
    text_parts.append(payload.get("journal", ""))
    text_parts.append(payload.get("one_line_summary", ""))
    for p in payload.get("key_pearls", []):
        text_parts.append(p)
    secs_array = payload.get("sections", [])
    if isinstance(secs_array, list):
        for s in secs_array:
            if isinstance(s, dict):
                text_parts.append(s.get("heading", ""))
                text_parts.append(s.get("content", ""))
                for sp in s.get("section_pearls", []):
                    text_parts.append(sp)
    text_parts.append(payload.get("consensus_method", ""))
    for b in payload.get("recommendation_blocks", []):
        text_parts.append(b.get("topic", ""))
        text_parts.append(b.get("narrative", ""))
        for r in b.get("recommendations", []):
            text_parts.append(r.get("statement", ""))
    for ib in payload.get("issuing_bodies", []):
        text_parts.append(ib)
    for step in payload.get("bedside_protocol", []):
        text_parts.append(step.get("title", ""))
        text_parts.append(step.get("action", ""))
    text_parts.append(payload.get("strengths_limitations", ""))
    for tag in payload.get("tags", []):
        text_parts.append(tag)

    # Trial format (condensed)
    text_parts.append(payload.get("trial_name", ""))
    text_parts.append(payload.get("trial_title", ""))
    text_parts.append(payload.get("one_liner", ""))
    text_parts.append(payload.get("citation", ""))
    text_parts.append(payload.get("specialty", ""))
    for kw in payload.get("keywords", []):
        text_parts.append(kw)

    # Trial sections (condensed — object with named keys like background, methods, results)
    trial_sec = payload.get("sections", {})
    if isinstance(trial_sec, dict):
        for sec_key, sec_val in trial_sec.items():
            if isinstance(sec_val, str):
                text_parts.append(sec_val)
            elif isinstance(sec_val, dict):
                for sub_val in sec_val.values():
                    if isinstance(sub_val, str):
                        text_parts.append(sub_val)
                    elif isinstance(sub_val, list):
                        for item in sub_val:
                            if isinstance(item, str):
                                text_parts.append(item)
                            elif isinstance(item, dict):
                                for iv in item.values():
                                    if isinstance(iv, str):
                                        text_parts.append(iv)

    return " ".join(text_parts).lower()


def extract_metadata(payload):
    title = payload.get("paper_name") or payload.get("title") or payload.get("trial_name") or payload.get("trial_title", "")
    system = payload.get("system") or ""
    if not system and payload.get("specialty"):
        if isinstance(payload["specialty"], list):
            system = ", ".join(payload["specialty"])
        else:
            system = payload["specialty"]
    article_type = payload.get("type_of_article") or ""
    if not article_type and payload.get("doc_type"):
        article_type = payload["doc_type"]
    if not article_type and payload.get("trial_type"):
        article_type = payload["trial_type"]
    journal = payload.get("journal_name") or payload.get("journal", "")
    if not journal:
        issuing = payload.get("issuing_bodies", [])
        if issuing:
            journal = ", ".join(issuing)
    if not journal:
        journal = "Unknown Journal"
    return title, system, article_type, journal
