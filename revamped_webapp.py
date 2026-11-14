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
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, StrictUndefined

# Import vocabulary normalization
from acumen_core.vocabulary import get_allowed_specialties, build_specialty_map

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


def _require_admin(user):
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

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
            # The reserved BOOKS/ subfolder (chaptered books) is quarantined from
            # the portal for now — skip it so books don't surface as notes.
            if rel_slash.upper().startswith("BOOKS/"):
                continue
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
            processed_at = m_entry.get("processed_at") or ""
            date_added = processed_at[:10] if processed_at else datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")
            notes.append({
                "id": fn,
                "title": title,
                "md": md_in,
                "system": system,
                "subtopic": subtopic,
                "rel": rel_slash,
                "date_added": date_added,
            })
    notes.sort(key=lambda n: (n.get("system") or "", n.get("subtopic") or "", n["title"].lower()))
    return notes

def load_related_links():
    """Load output_files/related_links.json (precomputed by acumen_core/linker.py).

    Returns {catalog, index, generated_at, entity_count}:
      catalog = [{id, kind, system, type, subtopic, title, tags}] for every
                known entity — built from the full entity catalog so entries
                that haven't been linked yet still resolve; stored tags from
                the links file are merged in.
      index   = {entity_id: [{to, kind, reason, weight}]} — forward + reverse
                edges merged per entity so both directions resolve instantly."""
    from acumen_core.linking import entity_catalog
    path = os.path.join(OUTPUT_DIR, "related_links.json")
    empty = {"catalog": [], "index": {}, "generated_at": "", "entity_count": 0}
    if not os.path.exists(path):
        return empty
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, Exception):
        return empty
    entities = data.get("entities") or {}
    if not isinstance(entities, dict):
        return empty

    # Full catalog: every known entity (complete even mid-run); merge stored tags
    catalog = []
    try:
        base_catalog = entity_catalog()
    except Exception:
        base_catalog = []
    if base_catalog:
        for ent in base_catalog:
            eid = ent["id"]
            stored = entities.get(eid) or {}
            catalog.append({
                "id": eid,
                "kind": stored.get("kind") or ent.get("kind", ""),
                "system": stored.get("system") or ent.get("system", ""),
                "type": stored.get("type") or ent.get("type", ""),
                "subtopic": stored.get("subtopic") or ent.get("subtopic", ""),
                "title": stored.get("title") or ent.get("title", "") or eid,
                "tags": stored.get("tags") or [],
            })
    else:
        for eid, ent in entities.items():
            catalog.append({
                "id": eid,
                "kind": ent.get("kind", ""),
                "system": ent.get("system", ""),
                "type": ent.get("type", ""),
                "subtopic": ent.get("subtopic", ""),
                "title": ent.get("title", "") or eid,
                "tags": ent.get("tags") or [],
            })
    catalog_ids = {c["id"] for c in catalog}

    index = {}
    for eid, ent in entities.items():
        if eid not in catalog_ids:
            continue
        index.setdefault(eid, [])
        for lb in ent.get("links") or []:
            t = lb.get("to")
            if not t or t == eid or t not in catalog_ids:
                continue
            edge = {
                "to": t,
                "kind": lb.get("kind", ""),
                "reason": lb.get("reason", "same topic"),
                "weight": lb.get("weight", 0.5),
            }
            index.setdefault(eid, []).append(edge)
            index.setdefault(t, []).append(dict(edge, to=eid, kind=ent.get("kind", "")))
    for eid, lst in index.items():
        dedup = {}
        for lb in lst:
            cur = dedup.get(lb["to"])
            if cur is None or (lb.get("weight") or 0) > (cur.get("weight") or 0):
                dedup[lb["to"]] = lb
        index[eid] = sorted(dedup.values(), key=lambda x: -(x.get("weight") or 0))
    return {
        "catalog": catalog,
        "index": index,
        "generated_at": data.get("generated_at", ""),
        "entity_count": data.get("entity_count", 0),
    }

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

# =====================================================================
# TEMPLATES & STATIC ASSETS
# =====================================================================

WEBAPP_DIR = Path(__file__).resolve().parent / "webapp"

# autoescape stays off on purpose: the page used to be one big f-string, and the markup handed
# to the template (option lists, SVG, <script> tags) is trusted. Data that comes from the
# content files travels through the escaped #boot JSON block instead (see _script_json).
_jinja = Environment(
    loader=FileSystemLoader(str(WEBAPP_DIR / "templates")),
    autoescape=False,
    undefined=StrictUndefined,
    keep_trailing_newline=True,
)


def _render_template(name, **ctx):
    return _jinja.get_template(name).render(**ctx)


def _script_json(obj):
    """JSON for a <script type="application/json"> block. '<', '>' and '&' are written as
    unicode escapes, so data such as a pearl containing "</script>" can never end the tag."""
    return json.dumps(obj).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


_asset_hashes = {}


def _asset_url(rel):
    """/static/<rel>?v=<content hash>: the hash makes the long-lived cache header safe."""
    path = WEBAPP_DIR / "static" / rel
    mtime = path.stat().st_mtime_ns
    cached = _asset_hashes.get(rel)
    if not cached or cached[0] != mtime:
        cached = (mtime, hashlib.sha1(path.read_bytes()).hexdigest()[:10])
        _asset_hashes[rel] = cached
    return f"/static/{rel}?v={cached[1]}"


class _AssetFiles(StaticFiles):
    async def get_response(self, path, scope):
        resp = await super().get_response(path, scope)
        if resp.status_code == 200:
            versioned = b"v=" in scope.get("query_string", b"")
            resp.headers["Cache-Control"] = (
                "public, max-age=31536000, immutable" if versioned else "public, max-age=300"
            )
        return resp


app.mount("/static", _AssetFiles(directory=str(WEBAPP_DIR / "static")), name="static")


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

    show_disclaimer = bool(DISCLAIMER_TEXT.strip())

    # Build subtopic map per system (from data + approved subtopics)
    raw_subtopic_map = {}
    for entry in entries:
        sys = entry.get("system", "General").strip()
        st = entry.get("subtopic", sys).strip()
        if sys not in raw_subtopic_map:
            raw_subtopic_map[sys] = set()
        raw_subtopic_map[sys].add(st)
    subtopic_map = {k: sorted(v) for k, v in raw_subtopic_map.items()}

    # Build CSS variable mapping for specialties using canonical vocabulary
    allowed_specialties = get_allowed_specialties()
    spec_map = build_specialty_map(allowed_specialties)

    def canonical_specialty(name):
        """Normalize specialty name to canonical form."""
        return spec_map.get(name.lower(), name)

    spec_css_vars = {}
    spec_css_vars_js = {}
    for s in systems_set:
        canon = canonical_specialty(s)
        color = SPEC_COLORS.get(canon, "#6B7280")
        var_name = "--spec-" + re.sub(r"[^a-zA-Z0-9]", "", canon.lower())
        spec_css_vars[var_name] = color
        spec_css_vars_js[canon] = var_name

    # Additional colors for specialties not in data but in color map
    for s, c in SPEC_COLORS.items():
        canon = canonical_specialty(s)
        var_name = "--spec-" + re.sub(r"[^a-zA-Z0-9]", "", canon.lower())
        if var_name not in spec_css_vars:
            spec_css_vars[var_name] = c
        if canon not in spec_css_vars_js:
            spec_css_vars_js[canon] = var_name

    spec_css_str = "; ".join(f"{k}:{v}" for k, v in spec_css_vars.items()) + ";"

    type_list = sorted(
        t for t in types_set if t and t.lower() not in ["none", "nan"]
    )

    # Trial CSS vars
    trial_spec_css = {}
    for s in trial_specialties:
        color = ESBICM_SPEC_COLORS.get(s, "#6B7280")
        var_name = "--tspec-" + re.sub(r"[^a-zA-Z0-9]", "", s.lower())
        trial_spec_css[var_name] = color
    trial_spec_str = "; ".join(f"{k}:{v}" for k, v in trial_spec_css.items()) + ";"
    trial_spec_vars = {s: "--tspec-" + re.sub(r"[^a-zA-Z0-9]", "", s.lower()) for s in trial_specialties}
    condensed_result_cats = sorted(set(t.get("result_category", "") for t in condensed_index if t.get("result_category")))
    condensed_types_list = sorted(set(t.get("trial_type", "") for t in condensed_index if t.get("trial_type")))

    # Theory flashcard decks (unified store) + Theory Topics (markdown notes)
    flashcard_decks = load_flashcard_decks() if _user_has_feature(user, "theory") else []
    theory_notes = load_theory_notes() if _user_has_feature(user, "theory") else []
    THEORY_SPEC_COLORS = {
        "Cardiology": "#C6554B", "Pulmonology": "#3A7CA5", "Neurology": "#6B5B95",
        "Nephrology": "#B08D57", "Gastroenterology": "#14B8A6",
        "Infectious Diseases": "#4F8A6D", "Hematology": "#E11D48",
        "Endocrinology": "#06B6D4", "Trauma": "#DC2626", "Surgery": "#6B7280",
        "Toxicology": "#7C3AED", "Sepsis": "#F97316", "General": "#9333EA",
        "Other": "#9333EA", "Hepatology": "#B45309", "Immunology": "#A855F7",
        "Multisystem": "#0EA5E9", "Nutrition": "#84CC16",
        "Obstetrics And Gynecology": "#DB2777", "Oncology": "#A78BFA",
        "Cardiothoracic": "#0891B2", "Vascular": "#F59E0B",
        "Rheumatology": "#0D9488",
    }
    theory_specs = sorted(
        set(d["specialty"] for d in flashcard_decks)
        | set(n.get("system") for n in theory_notes if n.get("system"))
    )
    theory_spec_css = {}
    for s in theory_specs:
        color = THEORY_SPEC_COLORS.get(s, "#9333EA")
        var_name = "--theory-spec-" + re.sub(r"[^a-zA-Z0-9]", "", s.lower())
        theory_spec_css[var_name] = color
    theory_spec_str = "; ".join(f"{k}:{v}" for k, v in theory_spec_css.items()) + ";"
    theory_spec_vars = {
        s: "--theory-spec-" + re.sub(r"[^a-zA-Z0-9]", "", s.lower()) for s in theory_specs
    }
    theory_total_cards = sum(len(d["cards"]) for d in flashcard_decks)
    theory_subtopic_map = {}
    for d in flashcard_decks:
        for t in d.get("subtopics") or []:
            theory_subtopic_map.setdefault(d["specialty"], set()).add(t)
    theory_subtopic_map = {s: sorted(v) for s, v in theory_subtopic_map.items()}

    # Cross-linking data (papers ↔ guidelines ↔ theory ↔ decks) precomputed by acumen_core/linker.py
    related_data = load_related_links()
    related_meta = {
        "generated_at": related_data.get("generated_at", ""),
        "entity_count": related_data.get("entity_count", 0),
        "loaded": bool(related_data["catalog"]),
    }

    # Compute resolved feature flags for the authenticated user
    user_features = {f: _user_has_feature(user, f) for f in FEATURE_FLAGS}
    insights_tag = '<script defer src="/_vercel/insights/script.js"></script>' if os.environ.get("VERCEL") else ''

    boot = {
        "spec_vars": spec_css_vars_js,
        "spec_labels": list(spec_css_vars_js.keys()),
        "type_list": type_list,
        "articles": articles_list,
        "pearls": pearls,
        "subtopic_map": subtopic_map,
        "show_disclaimer": show_disclaimer,
        "trial_index": trial_index,
        "trial_spec_labels": list(trial_specialties),
        "trial_spec_vars": trial_spec_vars,
        "trial_spec_counts": trial_spec_counts,
        "trial_subtopic_map": trial_subtopic_map,
        "trial_result_cats": trial_result_cats,
        "trial_types_list": trial_types_list,
        "condensed_index": condensed_index,
        "condensed_systems": condensed_systems,
        "condensed_result_cats": condensed_result_cats,
        "condensed_types_list": condensed_types_list,
        "flashcard_decks": flashcard_decks,
        "theory_spec_vars": theory_spec_vars,
        "theory_subtopic_map": theory_subtopic_map,
        "theory_notes": theory_notes,
        "related_catalog": related_data["catalog"],
        "related_index": related_data["index"],
        "related_meta": related_meta,
        "user_features": user_features,
        "user_is_admin": bool(user.get("is_admin")),
        "admin_feature_flags": FEATURE_FLAGS,
        "credits_text": CREDITS_TEXT,
        "trial_disclaimer_text": TRIAL_DISCLAIMER_TEXT,
        "disclaimer_text": DISCLAIMER_TEXT,
        "feedback_form_url": FEEDBACK_FORM_URL,
        "subscribe_form_url": SUBSCRIBE_FORM_URL,
        "unsubscribe_form_url": UNSUBSCRIBE_FORM_URL,
    }
    html = _render_template(
        "dashboard.html",
        user=user,
        insights_tag=insights_tag,
        ecg_svg=ECG_SVG,
        css_url=_asset_url("css/app.css"),
        js_url=_asset_url("js/app.js"),
        boot_json=_script_json(boot),
        spec_css_str=spec_css_str,
        trial_spec_str=trial_spec_str,
        theory_spec_str=theory_spec_str,
        theory_notes=theory_notes,
        theory_total_cards=theory_total_cards,
        theory_specs=theory_specs,
        trial_index=trial_index,
        trial_specialties=trial_specialties,
        trial_result_cats=trial_result_cats,
        trial_types_list=trial_types_list,
        can_see_condensed=_user_has_feature(user, "condensed_trials"),
        condensed_index=condensed_index,
        condensed_systems=condensed_systems,
        condensed_result_cats=condensed_result_cats,
        condensed_types_list=condensed_types_list,
        feedback_form_url=FEEDBACK_FORM_URL,
    )
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

# =====================================================================
# ADMIN — USER MANAGEMENT (admins only; mirrors dashboard Accounts tab)
# =====================================================================

def _admin_users_list():
    from concurrent.futures import ThreadPoolExecutor
    keys = _kv_scan("auth:users:*") or []
    if not keys:
        return []
    with ThreadPoolExecutor(max_workers=min(10, len(keys))) as pool:
        users = [u for u in pool.map(_kv_get, keys) if u]
    for u in users:
        u.pop("password_hash", None)
    users.sort(key=lambda u: u.get("created_at", ""), reverse=True)
    return users

def _admin_user_get(email: str):
    user = _kv_get(f"auth:users:{email}")
    if user:
        user.pop("password_hash", None)
    return user

def _admin_user_update(email: str, body: dict):
    user = _kv_get(f"auth:users:{email}")
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
    _kv_set(f"auth:users:{email}", user)
    user.pop("password_hash", None)
    return user

def _admin_user_delete(email: str) -> bool:
    user = _kv_get(f"auth:users:{email}")
    if not user:
        return False
    _kv_delete(f"auth:users:{email}")
    session_keys = _kv_scan("auth:session:*") or []
    for sk in session_keys:
        sess = _kv_get(sk)
        if sess and sess.get("email") == email:
            _kv_delete(sk)
    return True

def _admin_save_defaults(body: dict):
    clean = {k: bool(v) for k, v in body.items() if k in FEATURE_FLAGS}
    _kv_set("auth:access_defaults", clean)
    return {f: clean.get(f, DEFAULT_FEATURE_STATES.get(f, True)) for f in FEATURE_FLAGS}

@app.get("/api/admin/users")
async def api_admin_users_list(request: Request):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_admin(user)
    return _admin_users_list()

@app.get("/api/admin/users/defaults")
async def api_admin_users_defaults(request: Request):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_admin(user)
    return _access_defaults()

@app.put("/api/admin/users/defaults")
async def api_admin_users_defaults_update(request: Request, body: dict):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_admin(user)
    return _admin_save_defaults(body)

@app.put("/api/admin/users/{email:path}")
async def api_admin_users_update(email: str, request: Request, body: dict):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_admin(user)
    result = _admin_user_update(email, body)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result

@app.delete("/api/admin/users/{email:path}")
async def api_admin_users_delete(email: str, request: Request):
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    _require_admin(user)
    if not _admin_user_delete(email):
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}

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
