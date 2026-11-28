"""
redefined_ui.py — hack.CCM portal, theory-first redesign.

A new front end for the hack.CCM knowledge portal. It does NOT modify any
existing file: it imports `revamped_webapp` read-only, re-uses every API route
it defines (auth, bookmarks, summaries, trials, print export, admin), and
serves a study-first single-page UI at `/`.

    uvicorn redefined_ui:app --port 8000      # new UI at  /
                                              # old UI at  /classic

Focus: Theory topics -> Flashcards (spaced repetition) -> MCQs -> Pearls ->
Guidelines. Papers and trials live in a secondary "Evidence" group.

Design system (from ui-ux-pro-max, clinician profile: Minimalism / Swiss):
  * Atkinson Hyperlegible for interface and body, Source Serif 4 for long-form
    theory reading, JetBrains Mono for labels and data.
  * Slate neutrals, one clinical teal accent; green / red / amber are reserved
    for answer feedback and recall ratings. Light + dark themes.
  * 44px touch targets, visible focus, reduced-motion, keyboard-first study
    flows (space = flip, 1-4 = rate, A-E = answer, Ctrl/Cmd-K = search).

New API routes (all read-only views over existing data, except progress):
  GET   /api/redefined/bootstrap        catalog for the SPA
  GET   /api/redefined/note?id=         one theory note (markdown)
  GET   /api/redefined/related?ref=     related-links neighbours, resolved
  GET   /api/redefined/guideline?file_name=   structured guideline JSON
  GET   /api/redefined/pearls           pearls with system/subtopic/q/shuffle
  GET   /api/redefined/mcqs?ids=|system=&subtopic=   MCQ questions
  GET   /api/redefined/progress         per-user study progress
  PATCH /api/redefined/progress         merge progress (cards/mcq/notes/activity)

MCQs are produced by `mcq_generator.py` into output_files/mcqs/ (override with
the MCQ_DIR environment variable).
"""

import json
import os
import random
import re
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse

import revamped_webapp as legacy

app = FastAPI(title="hack.CCM — redefined UI")

# Re-use every legacy route except the old home page, which moves to /classic.
for _route in legacy.app.router.routes:
    if getattr(_route, "path", None) == "/":
        continue
    app.router.routes.append(_route)

MCQ_DIR = os.getenv("MCQ_DIR", os.path.join(legacy.OUTPUT_DIR, "mcqs"))
PROGRESS_KEY = "progress"
PROGRESS_LIMITS = {"cards": 20000, "mcq": 20000, "notes": 3000}
ACTIVITY_DAYS = 400


@app.get("/classic", response_class=HTMLResponse)
async def classic_ui(request: Request):
    """The previous portal, unchanged."""
    return await legacy.render_dashboard(request, Response())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_or_401(request):
    user = legacy._get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    return user


def _has_feature(user, feature):
    """Feature check for the redefined UI. Same as the portal's own check,
    except "theory" is ON by default for non-admins: it is only off when an
    admin explicitly turned it off for this user or in the access defaults."""
    if feature == "theory" and not user.get("is_admin"):
        overrides = user.get("features") or {}
        if "theory" in overrides:
            return bool(overrides["theory"])
        defaults = legacy._kv_get("auth:access_defaults") or {}
        if isinstance(defaults, dict) and "theory" in defaults:
            return bool(defaults["theory"])
        return True
    return bool(legacy._user_has_feature(user, feature))


def _require(user, feature):
    if not _has_feature(user, feature):
        raise HTTPException(status_code=403, detail=f"Feature '{feature}' is not enabled for this account")


def _doi_url(raw):
    raw = str(raw or "").strip()
    if not raw or raw.lower() in ("none", "nan"):
        return ""
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    return f"https://doi.org/{raw}"


def _articles():
    out = []
    for idx, e in enumerate(legacy.load_approved_ledger() or []):
        system = str(e.get("system", "General")).strip() or "General"
        out.append({
            "id": str(idx),
            "title": str(e.get("title", "Untitled")),
            "authors": str(e.get("authors", "")),
            "journal": str(e.get("journal", "")),
            "year": str(e.get("year", "") or ""),
            "system": system,
            "subtopic": str(e.get("subtopic", system) or system).strip(),
            "type": str(e.get("type", "Other")).strip() or "Other",
            "doi": _doi_url(e.get("doi")),
            "file_name": str(e.get("file_name", "")),
            "date_added": str(e.get("date_added", "")),
        })
    return out


def _load_mcq_store():
    """All MCQ subtopic files -> flat list of questions (with system/subtopic)."""
    out = []
    if not os.path.isdir(MCQ_DIR):
        return out
    for root, _, files in os.walk(MCQ_DIR):
        for fn in sorted(files):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(root, fn), "r", encoding="utf-8") as f:
                    d = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            system, subtopic = d.get("system", "General"), d.get("subtopic", "General")
            for q in d.get("questions") or []:
                if not isinstance(q, dict) or not q.get("id") or q.get("status") == "rejected":
                    continue
                q = dict(q)
                q["system"], q["subtopic"] = system, subtopic
                out.append(q)
    return out


def _mcq_index(questions):
    """Answer-free index for the bootstrap payload."""
    return [{
        "id": q["id"], "s": q["system"], "t": q["subtopic"],
        "d": q.get("difficulty", "medium"),
        "src": (q.get("source") or {}).get("ref", ""),
        "k": (q.get("source") or {}).get("kind", ""),
    } for q in questions]


def _find_summary_json(file_name, system="", type_=""):
    base = os.path.splitext(file_name)[0]
    clean_sys = "".join(x for x in str(system) if x.isalnum() or x in "._- ").strip()
    clean_type = "".join(x for x in str(type_) if x.isalnum() or x in "._- ").strip()
    target = os.path.join(legacy.OUTPUT_DIR, clean_sys, clean_type, f"{base}.json")
    if os.path.exists(target):
        return target
    for root, _, files in os.walk(legacy.OUTPUT_DIR):
        if f"{base}.json" in files:
            return os.path.join(root, f"{base}.json")
    return None


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.get("/api/redefined/bootstrap")
async def redefined_bootstrap(request: Request):
    user = _user_or_401(request)
    features = {f: _has_feature(user, f) for f in legacy.FEATURE_FLAGS}
    # The legacy print route still applies the legacy theory flag.
    features["print_notes"] = bool(legacy._user_has_feature(user, "theory"))

    articles = _articles() if (features["papers"] or features["guidelines"]) else []
    pearls = legacy.load_pearls() if features["pearls"] else []
    pearl_topics = {}
    for p in pearls:
        s = p.get("system")
        if not (isinstance(s, str) and s.strip()):
            continue
        t = str(p.get("subtopic") or "").strip() or s
        pearl_topics.setdefault(s, {})
        pearl_topics[s][t] = pearl_topics[s].get(t, 0) + 1
    pearl_of_day = None
    if pearls:
        p = pearls[datetime.utcnow().toordinal() % len(pearls)]
        pearl_of_day = {k: p.get(k) for k in ("id", "pearl", "system", "subtopic", "source_paper", "type")}

    trials = legacy.load_trial_index() if features["trials"] else []
    condensed = legacy.load_condensed_trial_index() if features["condensed_trials"] else []
    theory_on = features["theory"]
    decks = legacy.load_flashcard_decks() if theory_on else []
    notes = []
    if theory_on:
        for n in legacy.load_theory_notes():
            md = str(n.get("md") or "")
            notes.append({
                "id": n.get("id"), "rel": n.get("rel"), "title": n.get("title"),
                "system": n.get("system") or "General", "subtopic": n.get("subtopic") or "General",
                "date_added": n.get("date_added"),
                "words": len(md.split()),
                "heads": len(re.findall(r"^#{2,3}\s", md, re.M)),
            })
    mcqs = _mcq_index(_load_mcq_store()) if theory_on else []

    colors = dict(legacy.SPEC_COLORS)
    colors.update(legacy.ESBICM_SPEC_COLORS)

    return {
        "user": {
            "name": (user.get("first_name") or user.get("email", "").split("@")[0]),
            "email": user.get("email", ""),
            "is_admin": bool(user.get("is_admin")),
        },
        "features": features,
        "articles": articles,
        "pearl_count": len(pearls),
        "pearl_topics": pearl_topics,
        "pearl_of_day": pearl_of_day,
        "trials": trials,
        "condensed": condensed,
        "decks": decks,
        "notes": notes,
        "mcqs": mcqs,
        "colors": colors,
        "disclaimer": legacy.DISCLAIMER_TEXT,
        "credits": legacy.CREDITS_TEXT,
        "links": {
            "feedback": legacy.FEEDBACK_FORM_URL,
            "subscribe": legacy.SUBSCRIBE_FORM_URL,
            "unsubscribe": legacy.UNSUBSCRIBE_FORM_URL,
        },
        "local_dev": bool(legacy.LOCAL_DEV_MODE),
    }


@app.get("/api/redefined/note")
async def redefined_note(request: Request, id: str):
    user = _user_or_401(request)
    _require(user, "theory")
    for n in legacy.load_theory_notes():
        if n.get("id") == id or n.get("rel") == id:
            return n
    return JSONResponse(status_code=404, content={"error": "Note not found"})


@app.get("/api/redefined/related")
async def redefined_related(request: Request, ref: str, limit: int = 12):
    """Neighbours of one entity from output_files/related_links.json, resolved
    to {ref, kind, title, system, reason}. ref examples: theory:<rel>,
    paper:<file.pdf>, deck:<System/Subtopic>."""
    _user_or_401(request)
    data = legacy.load_related_links() or {}
    catalog = {c.get("id"): c for c in data.get("catalog") or []}
    out, seen = [], set()
    for edge in (data.get("index") or {}).get(ref, []):
        to = edge.get("to")
        c = catalog.get(to)
        if not c or to in seen:
            continue
        seen.add(to)
        out.append({"ref": to, "kind": c.get("kind"), "title": c.get("title"), "system": c.get("system"),
                    "type": c.get("type"), "reason": edge.get("reason"), "weight": edge.get("weight", 0)})
    out.sort(key=lambda x: -float(x.get("weight") or 0))
    return {"items": out[: max(1, min(limit, 40))]}


@app.get("/api/redefined/guideline")
async def redefined_guideline(request: Request, file_name: str, system: str = "", type: str = "Guideline"):
    user = _user_or_401(request)
    _require(user, "guidelines")
    path = _find_summary_json(file_name, system, type)
    if not path:
        return JSONResponse(status_code=404, content={"error": "Guideline not found"})
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    md = d.get("clinical_summary_markdown") or legacy.format_new_schema_as_markdown(d)
    keep = ("title", "year", "one_line_summary", "issuing_bodies", "key_pearls", "recommendation_blocks",
            "bedside_protocol", "strengths_limitations", "consensus_method", "search_period", "doi", "tags")
    out = {k: d.get(k) for k in keep}
    out["markdown"] = md
    return out


@app.get("/api/redefined/pearls")
async def redefined_pearls(request: Request, q: str = "", system: str = "", subtopic: str = "",
                           page: int = 1, limit: int = 36, shuffle: int = 0):
    user = _user_or_401(request)
    _require(user, "pearls")
    ql = q.lower().strip()
    st = subtopic.lower().strip()
    rows = []
    for p in legacy.load_pearls():
        if system and p.get("system") != system:
            continue
        if st and st != str(p.get("subtopic") or p.get("system") or "").lower().strip():
            continue
        if ql and ql not in (str(p.get("pearl", "")) + " " + str(p.get("source_paper", ""))).lower():
            continue
        rows.append({k: p.get(k) for k in ("id", "pearl", "system", "subtopic", "source_paper", "type", "doi")})
    if shuffle:
        random.Random(shuffle).shuffle(rows)
    limit = max(1, min(limit, 200))
    page = max(1, page)
    total = len(rows)
    return {"pearls": rows[(page - 1) * limit: page * limit], "total": total,
            "pages": max(1, -(-total // limit))}


@app.get("/api/redefined/mcqs")
async def redefined_mcqs(request: Request, ids: str = "", system: str = "", subtopic: str = ""):
    user = _user_or_401(request)
    _require(user, "theory")
    qs = _load_mcq_store()
    if ids:
        want = [i for i in ids.split(",") if i][:200]
        by_id = {q["id"]: q for q in qs}
        qs = [by_id[i] for i in want if i in by_id]
    else:
        qs = [q for q in qs if (not system or q["system"] == system)
              and (not subtopic or q["subtopic"] == subtopic)][:200]
    return {"questions": qs}


def _clean_progress(d):
    d = d if isinstance(d, dict) else {}
    for k in ("cards", "mcq", "notes", "activity"):
        if not isinstance(d.get(k), dict):
            d[k] = {}
    if not isinstance(d.get("last"), dict):
        d["last"] = {}
    return d


@app.get("/api/redefined/progress")
async def redefined_progress_get(request: Request):
    user = _user_or_401(request)
    return _clean_progress(legacy._user_data(user["email"], PROGRESS_KEY))


@app.patch("/api/redefined/progress")
async def redefined_progress_patch(request: Request, body: dict):
    """Merge partial progress. Body keys (all optional):
       cards {uuid: {e,i,d,r,l}}   mcq {qid: {n,c,a,t}}   notes {id: {p,r}}
       activity_inc int (added to today's count)   last {note: id}"""
    user = _user_or_401(request)
    data = _clean_progress(legacy._user_data(user["email"], PROGRESS_KEY))
    for key, cap in PROGRESS_LIMITS.items():
        upd = body.get(key)
        if not isinstance(upd, dict):
            continue
        bucket = data[key]
        for k, v in list(upd.items())[:500]:
            k = str(k)[:300]
            if v is None:
                bucket.pop(k, None)
            elif isinstance(v, dict) and len(json.dumps(v)) < 400:
                bucket[k] = v
        if len(bucket) > cap:
            for k in list(bucket.keys())[: len(bucket) - cap]:
                bucket.pop(k, None)
    inc = body.get("activity_inc")
    if isinstance(inc, int) and 0 < inc <= 500:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        act = data["activity"]
        act[today] = int(act.get(today, 0)) + inc
        cutoff = (datetime.utcnow() - timedelta(days=ACTIVITY_DAYS)).strftime("%Y-%m-%d")
        for k in [k for k in act if k < cutoff]:
            act.pop(k, None)
    if isinstance(body.get("last"), dict):
        last = {k: str(v)[:300] for k, v in body["last"].items() if k in ("note", "deck", "at")}
        data["last"].update(last)
    legacy._save_user_data(user["email"], PROGRESS_KEY, data)
    return {"ok": True, "activity": data["activity"]}


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def redefined_home(request: Request):
    if not legacy._get_session_user(request):
        return HTMLResponse(content=legacy.LANDING_HTML)
    return HTMLResponse(content=PAGE_HTML)


PAGE_HTML = r"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>hack.CCM — Critical care, studied properly</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&family=JetBrains+Mono:wght@400;500&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<script>(function(){var t=localStorage.getItem('hc2-theme');if(!t){t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}document.documentElement.dataset.theme=t;var f=localStorage.getItem('hc2-fs');if(f)document.documentElement.style.setProperty('--read-fs',f+'px')})();</script>
<style>
:root{
  --bg:#F5F7F9; --bg-2:#EBEFF3; --surface:#FFFFFF; --surface-2:#F9FAFB;
  --ink:#0F172A; --ink-2:#334155; --muted:#5B6878; --line:#E2E8F0; --line-2:#CBD5E1;
  --accent:#0F766E; --accent-ink:#FFFFFF; --accent-soft:#E6F4F1; --accent-line:#A7D8CF;
  --ok:#15803D; --ok-soft:#E7F5EC; --bad:#B91C1C; --bad-soft:#FCEBEB; --warn:#B45309; --warn-soft:#FDF2E2;
  --info:#1D4ED8; --info-soft:#E8EEFC;
  --shadow:0 1px 2px rgba(15,23,42,.05),0 2px 8px rgba(15,23,42,.04);
  --shadow-md:0 4px 18px rgba(15,23,42,.08);
  --shadow-lg:0 24px 60px rgba(15,23,42,.20);
  --r:14px; --r-sm:10px;
  --sans:"Atkinson Hyperlegible",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  --serif:"Source Serif 4","Source Serif Pro",Georgia,serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  --read-fs:18px; --rail:244px; --ease:cubic-bezier(.2,.7,.2,1);
}
[data-theme="dark"]{
  --bg:#0B1016; --bg-2:#111923; --surface:#121A23; --surface-2:#16202B;
  --ink:#E6EBF1; --ink-2:#C3CCD7; --muted:#93A1B2; --line:#1F2B38; --line-2:#2C3A49;
  --accent:#2DD4BF; --accent-ink:#04201C; --accent-soft:#0F2E2B; --accent-line:#1F5A53;
  --ok:#4ADE80; --ok-soft:#12301F; --bad:#F87171; --bad-soft:#371618; --warn:#FBBF24; --warn-soft:#33270C;
  --info:#93B4FF; --info-soft:#17233D;
  --shadow:0 1px 2px rgba(0,0,0,.35); --shadow-md:0 6px 20px rgba(0,0,0,.35); --shadow-lg:0 24px 60px rgba(0,0,0,.6);
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:16px;line-height:1.5;-webkit-font-smoothing:antialiased}
a{color:var(--accent)} a:hover{text-decoration-thickness:2px}
button{font:inherit;color:inherit;cursor:pointer}
button:disabled{cursor:not-allowed;opacity:.5}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:8px}
svg.i{width:18px;height:18px;flex:none}
.mono{font-family:var(--mono)} .serif{font-family:var(--serif)}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}

/* ---------- Shell ---------- */
.shell{display:grid;grid-template-columns:var(--rail) 1fr;min-height:100vh}
.rail{position:sticky;top:0;height:100vh;overflow:auto;display:flex;flex-direction:column;padding:20px 12px 14px;border-right:1px solid var(--line);background:var(--surface)}
.brand{display:flex;align-items:center;gap:10px;padding:2px 10px 18px;text-decoration:none;color:var(--ink)}
.brand-mark{width:34px;height:34px;border-radius:10px;background:var(--accent);color:var(--accent-ink);display:grid;place-items:center}
.brand-mark svg{width:22px;height:22px}
.brand-name{font-weight:700;font-size:20px;letter-spacing:-.01em}
.brand-name span{color:var(--muted);font-weight:400}
.rail-label{font:500 11px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted);padding:16px 12px 8px}
.nav-btn{display:flex;align-items:center;gap:12px;width:100%;min-height:40px;padding:8px 12px;border:0;background:none;border-radius:10px;color:var(--ink-2);text-align:left;transition:background .15s}
.nav-btn .count{margin-left:auto;font:500 11.5px var(--mono);color:var(--muted)}
.nav-btn .due{margin-left:auto;font:600 11px var(--mono);background:var(--accent);color:var(--accent-ink);border-radius:999px;padding:2px 8px}
.nav-btn:hover{background:var(--bg-2);color:var(--ink)}
.nav-btn[aria-current="page"]{background:var(--accent-soft);color:var(--ink);font-weight:700}
.nav-btn[aria-current="page"] svg{color:var(--accent)}
.nav-evidence .nav-btn{min-height:36px;font-size:14.5px;color:var(--muted)}
.rail-foot{margin-top:auto;display:flex;flex-direction:column;border-top:1px solid var(--line);padding-top:10px}
.rail-foot .nav-btn{font-size:14px;min-height:36px;color:var(--muted)}

.main{min-width:0;display:flex;flex-direction:column}
.topbar{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:12px;padding:12px 32px;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid transparent}
.topbar.scrolled{border-bottom-color:var(--line)}
.search-trigger{flex:1;min-width:0;max-width:560px;min-height:44px;display:flex;align-items:center;gap:10px;padding:0 14px;border:1px solid var(--line);background:var(--surface);border-radius:12px;color:var(--muted);text-align:left}
.search-trigger:hover{border-color:var(--line-2)}
.search-trigger span:not(.kbd){overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.kbd{margin-left:auto;font:500 11px var(--mono);padding:2px 7px;border:1px solid var(--line-2);border-radius:6px;color:var(--muted);white-space:nowrap}
.top-actions{margin-left:auto;display:flex;gap:8px;align-items:center;flex:none}
.streak{display:flex;align-items:center;gap:6px;height:44px;padding:0 12px;border:1px solid var(--line);border-radius:12px;background:var(--surface);font:600 14px var(--mono);color:var(--warn)}
.icon-btn{width:44px;height:44px;display:grid;place-items:center;border:1px solid var(--line);background:var(--surface);border-radius:12px;color:var(--ink-2)}
.icon-btn:hover{color:var(--ink);border-color:var(--line-2)}
.avatar{width:44px;height:44px;border-radius:50%;background:var(--accent-soft);color:var(--accent);display:grid;place-items:center;font-weight:700;border:0}
.content{padding:8px 32px 96px;max-width:1320px;width:100%}

/* ---------- Type ---------- */
.eyebrow{font:500 11.5px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
h1.pt{font-weight:700;font-size:34px;line-height:1.15;letter-spacing:-.02em;margin:10px 0 6px}
.psub{color:var(--muted);margin:0 0 24px;max-width:680px}
h2.sec{font-weight:700;font-size:20px;letter-spacing:-.01em;margin:40px 0 14px;display:flex;align-items:baseline;gap:12px}
h2.sec .link{margin-left:auto;font-weight:400;font-size:14.5px}
.muted{color:var(--muted)}

/* ---------- Atoms ---------- */
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--shadow)}
.pill{width:fit-content;display:inline-flex;align-items:center;gap:6px;font:500 12px/1 var(--mono);padding:5px 9px;border-radius:999px;background:var(--bg-2);color:var(--ink-2);white-space:nowrap;max-width:100%;overflow:hidden;text-overflow:ellipsis}
.dot{width:8px;height:8px;border-radius:50%;flex:none;background:var(--c,var(--muted))}
.tag{font:600 11px/1 var(--mono);padding:5px 8px;border-radius:6px;white-space:nowrap;letter-spacing:.02em}
.tag.ok{background:var(--ok-soft);color:var(--ok)} .tag.bad{background:var(--bad-soft);color:var(--bad)}
.tag.warn{background:var(--warn-soft);color:var(--warn)} .tag.info{background:var(--info-soft);color:var(--info)}
.tag.neu{background:var(--bg-2);color:var(--ink-2)} .tag.acc{background:var(--accent-soft);color:var(--accent)}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:44px;padding:0 16px;border-radius:11px;border:1px solid var(--line);background:var(--surface);font-weight:700;font-size:15px;text-decoration:none;color:var(--ink);transition:border-color .15s,background .15s,transform .1s}
.btn:hover{border-color:var(--line-2)}
.btn:active{transform:translateY(1px)}
.btn.primary{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
.btn.primary:hover{filter:brightness(1.06)}
.btn.ghost{background:none;border-color:transparent}
.btn.sm{min-height:36px;padding:0 12px;font-size:14px}
.btn.saved{color:var(--accent);border-color:var(--accent-line)}
.chip{min-height:36px;border:1px solid var(--line);background:var(--surface);padding:0 13px;border-radius:999px;font-size:14px;color:var(--ink-2);display:inline-flex;align-items:center;gap:7px}
.chip:hover{border-color:var(--line-2)}
.chip[aria-pressed="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.seg{display:inline-flex;padding:4px;border-radius:12px;background:var(--bg-2);gap:2px}
.seg button{min-height:36px;border:0;background:none;padding:0 14px;border-radius:9px;color:var(--muted);font-weight:700;font-size:14px}
.seg button[aria-pressed="true"]{background:var(--surface);color:var(--ink);box-shadow:var(--shadow)}
.empty{padding:40px 20px;text-align:center;color:var(--muted)}
.input{flex:1;min-width:200px;min-height:44px;display:flex;align-items:center;gap:9px;padding:0 13px;border:1px solid var(--line);background:var(--surface);border-radius:11px}
.input:focus-within{border-color:var(--accent)}
.input input{border:0;outline:0;background:none;flex:1;font:inherit;color:var(--ink);min-width:0}
.input svg{color:var(--muted)}
select.sel{min-height:44px;padding:0 12px;border:1px solid var(--line);background:var(--surface);border-radius:11px;font:inherit;color:var(--ink);max-width:100%}
.toolbar{display:flex;gap:10px;align-items:center;margin-bottom:16px;flex-wrap:wrap}
.count-line{font:12.5px var(--mono);color:var(--muted);margin:0 0 10px}
.bar{height:6px;border-radius:6px;background:var(--bg-2);overflow:hidden;display:flex}
.bar i{display:block;height:100%}
.bar .b1{background:var(--accent)} .bar .b2{background:var(--accent-line)}
.ring{--p:0;width:34px;height:34px;border-radius:50%;flex:none;background:conic-gradient(var(--accent) calc(var(--p)*1%),var(--bg-2) 0);display:grid;place-items:center}
.ring::after{content:"";width:24px;height:24px;border-radius:50%;background:var(--surface)}
.ring.done{background:var(--accent)} .ring.done::after{background:var(--accent)}
.ringwrap{position:relative;display:grid;place-items:center}

/* ---------- Today ---------- */
.hello{display:flex;align-items:flex-end;gap:24px;flex-wrap:wrap;margin:8px 0 22px}
.hello h1{font-weight:700;font-size:32px;line-height:1.15;letter-spacing:-.02em;margin:8px 0 0}
.week{margin-left:auto;display:flex;gap:6px;align-items:flex-end}
.week div{display:flex;flex-direction:column;align-items:center;gap:6px;font:11px var(--mono);color:var(--muted)}
.week i{display:block;width:22px;border-radius:6px;background:var(--bg-2)}
.week i.on{background:var(--accent)}
.week .today{color:var(--ink);font-weight:600}
.actions{display:grid;grid-template-columns:1.25fr 1fr 1fr;gap:16px}
.act{position:relative;padding:22px;display:flex;flex-direction:column;gap:10px;text-align:left;min-height:210px;border:1px solid var(--line);overflow:hidden;transition:border-color .15s,box-shadow .15s}
.act:hover{border-color:var(--line-2);box-shadow:var(--shadow-md)}
.act .ic{width:40px;height:40px;border-radius:11px;background:var(--accent-soft);color:var(--accent);display:grid;place-items:center}
.act h3{margin:0;font-size:20px;line-height:1.25;letter-spacing:-.01em}
.act .big{font:700 40px/1 var(--sans);letter-spacing:-.03em}
.act .foot{margin-top:auto;display:flex;align-items:center;gap:10px;color:var(--muted);font-size:14px}
.act .go{margin-left:auto;color:var(--accent);font-weight:700;display:flex;align-items:center;gap:4px}
.act.feature{background:linear-gradient(160deg,var(--accent-soft),var(--surface) 70%)}
.twocol{display:grid;grid-template-columns:1.4fr 1fr;gap:16px;align-items:start}
.pod{padding:22px}
.pod blockquote{margin:12px 0 14px;font-family:var(--serif);font-size:19px;line-height:1.5}
.spec-map{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px}
.spec{display:flex;flex-direction:column;gap:8px;padding:14px;text-align:left;border:1px solid var(--line);background:var(--surface);border-radius:12px;transition:border-color .15s}
.spec:hover{border-color:var(--c)}
.spec .hd{display:flex;align-items:center;gap:10px;font-weight:700}
.spec .sw{width:10px;height:28px;border-radius:4px;background:var(--c)}
.spec .nums{display:flex;gap:14px;font:12.5px var(--mono);color:var(--muted)}
.spec .nums b{color:var(--ink);font-weight:600}
.list{overflow:hidden}
.row{display:grid;grid-template-columns:4px 1fr auto;gap:16px;align-items:center;padding:14px 18px 14px 0;border:0;border-bottom:1px solid var(--line);background:none;text-align:left;width:100%;min-height:60px}
.row:last-child{border-bottom:0}
.row:hover{background:var(--surface-2)}
.row .stripe{align-self:stretch;background:var(--c,var(--line));border-radius:0 3px 3px 0}
.row .t{font-weight:700;font-size:16px;line-height:1.35;color:var(--ink)}
.row .t.serif{font-family:var(--serif);font-weight:600;font-size:17px}
.row .m{margin-top:4px;display:flex;flex-wrap:wrap;gap:4px 14px;font:12.5px var(--mono);color:var(--muted)}
.row .one{margin-top:5px;color:var(--ink-2);font-size:14.5px}
.row .r{display:flex;align-items:center;gap:8px}

/* ---------- Topics ---------- */
.topics{display:grid;grid-template-columns:250px 1fr;gap:28px;align-items:start}
.tree{position:sticky;top:84px;max-height:calc(100vh - 110px);overflow:auto;padding-right:4px}
.tree button{display:flex;align-items:center;gap:10px;width:100%;min-height:40px;padding:6px 10px;border:0;background:none;border-radius:9px;text-align:left;color:var(--ink-2);font-size:15px}
.tree button:hover{background:var(--bg-2)}
.tree button[aria-pressed="true"]{background:var(--surface);color:var(--ink);font-weight:700;box-shadow:var(--shadow)}
.tree .c{margin-left:auto;font:12px var(--mono);color:var(--muted)}
.tgroup{margin-bottom:26px}
.tgroup h3{display:flex;align-items:center;gap:10px;font-size:15px;margin:0 0 10px;color:var(--ink-2)}
.tgroup h3 .ln{flex:1;height:1px;background:var(--line)}
.tcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:12px}
.tcard{display:flex;gap:14px;align-items:flex-start;padding:16px;text-align:left;border:1px solid var(--line);background:var(--surface);border-radius:12px;min-height:96px;transition:border-color .15s,box-shadow .15s}
.tcard:hover{border-color:var(--line-2);box-shadow:var(--shadow-md)}
.tcard .tt{font-family:var(--serif);font-weight:600;font-size:17px;line-height:1.3}
.tcard .tm{margin-top:8px;display:flex;flex-wrap:wrap;gap:6px}

/* ---------- Topic hub ---------- */
.crumbs{display:flex;flex-wrap:wrap;align-items:center;gap:6px;font-size:14px;color:var(--muted);margin:6px 0 4px}
.crumbs button{border:0;background:none;padding:4px 2px;color:var(--accent);font-size:14px}
.hub{display:grid;grid-template-columns:200px minmax(0,1fr) 300px;gap:32px;align-items:start}
.toc{position:sticky;top:88px;max-height:calc(100vh - 120px);overflow:auto;font-size:14px}
.toc a{display:block;padding:5px 0 5px 12px;border-left:2px solid var(--line);color:var(--muted);text-decoration:none;line-height:1.35}
.toc a.h3{padding-left:24px;font-size:13.5px}
.toc a.on{border-left-color:var(--accent);color:var(--ink);font-weight:700}
.hub-head h1{font-family:var(--serif);font-weight:600;font-size:38px;line-height:1.15;letter-spacing:-.015em;margin:8px 0 12px}
.hub-meta{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;color:var(--muted);font-size:14px;margin-bottom:16px}
.hub-meta span{display:inline-flex;align-items:center;gap:6px}
.hub-actions{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:26px;padding-bottom:20px;border-bottom:1px solid var(--line)}
.readbar{position:fixed;left:0;top:0;height:3px;background:var(--accent);z-index:30;width:0;transition:width .1s}
.prac{position:sticky;top:88px;display:flex;flex-direction:column;gap:14px}
.prac .card{padding:16px}
.prac h4{margin:0 0 10px;font:500 11.5px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.prac .pa{display:flex;align-items:center;gap:12px;width:100%;padding:10px;border:1px solid var(--line);border-radius:10px;background:var(--surface-2);text-align:left;min-height:56px;margin-bottom:8px}
.prac .pa:hover{border-color:var(--accent-line)}
.prac .pa .ic{width:36px;height:36px;border-radius:9px;background:var(--accent-soft);color:var(--accent);display:grid;place-items:center;flex:none}
.prac .pa b{display:block;font-size:15px}
.prac .pa small{color:var(--muted);font-size:13px}
.mini-pearl{font-family:var(--serif);font-size:15px;line-height:1.45;padding:10px 0;border-bottom:1px solid var(--line)}
.mini-pearl:last-of-type{border-bottom:0}
.rel{display:block;width:100%;text-align:left;border:0;background:none;padding:8px 0;border-bottom:1px solid var(--line);font-size:14.5px;line-height:1.35}
.rel:last-child{border-bottom:0}
.rel small{display:block;color:var(--muted);font:12px var(--mono);margin-top:3px}

/* ---------- Prose ---------- */
.prose{font-family:var(--serif);font-size:var(--read-fs);line-height:1.7;color:var(--ink);max-width:72ch}
.prose h1,.prose h2,.prose h3,.prose h4{font-family:var(--sans);letter-spacing:-.01em;line-height:1.3;margin:1.9em 0 .6em;scroll-margin-top:90px}
.prose h1{font-size:1.3em}.prose h2{font-size:1.2em;padding-bottom:8px;border-bottom:1px solid var(--line)}.prose h3{font-size:1.05em}.prose h4{font-size:.95em;color:var(--ink-2)}
.prose p{margin:.8em 0} .prose ul,.prose ol{padding-left:1.3em} .prose li{margin:.35em 0}
.prose strong{font-weight:600;color:var(--ink)}
.prose blockquote{margin:1.2em 0;padding:10px 18px;border-left:3px solid var(--accent);background:var(--accent-soft);border-radius:0 10px 10px 0;color:var(--ink)}
.prose code{font:.85em var(--mono);background:var(--bg-2);padding:1px 5px;border-radius:5px}
.prose table{border-collapse:collapse;width:100%;font:15px/1.45 var(--sans);margin:1.3em 0;display:block;overflow:auto}
.prose th,.prose td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
.prose th{background:var(--bg-2)}
.prose hr{border:0;border-top:1px solid var(--line);margin:2em 0}
.prose img{max-width:100%;border-radius:10px}

/* ---------- Flashcards ---------- */
.deckgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}
.deck{padding:18px;display:flex;flex-direction:column;gap:12px;border:1px solid var(--line);position:relative}
.deck h3{margin:0;font-family:var(--serif);font-weight:600;font-size:20px;line-height:1.25}
.deck .stats{display:flex;gap:16px;font:12.5px var(--mono);color:var(--muted)}
.deck .stats b{color:var(--ink);font-weight:600}
.deck .btns{display:flex;gap:8px;margin-top:auto}
.deck .due-b{position:absolute;top:16px;right:16px}
.banner{display:flex;align-items:center;gap:18px;padding:20px 22px;margin-bottom:22px;flex-wrap:wrap}
.banner .big{font:700 36px/1 var(--sans);letter-spacing:-.02em}
.study{max-width:780px;margin:0 auto}
.study-head{display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap}
.progress{height:6px;background:var(--bg-2);border-radius:6px;overflow:hidden;margin-bottom:20px}
.progress i{display:block;height:100%;background:var(--accent);transition:width .25s var(--ease)}
.flip{perspective:1600px;cursor:pointer}
.flip-in{position:relative;min-height:400px;transition:transform .45s var(--ease);transform-style:preserve-3d}
.flip.on .flip-in{transform:rotateY(180deg)}
.face{position:absolute;inset:0;backface-visibility:hidden;-webkit-backface-visibility:hidden;padding:34px 40px;overflow:auto;display:flex;flex-direction:column}
.face.front{justify-content:center;align-items:center;text-align:center}
.face.front .q{font-family:var(--serif);font-size:27px;line-height:1.35;font-weight:600;max-width:580px}
.face.back{transform:rotateY(180deg)}
.face .prose{font-size:17px}
.face .hint{position:absolute;bottom:14px;left:0;right:0;text-align:center;font:12px var(--mono);color:var(--muted)}
.rate{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:18px}
.rate button{min-height:64px;border-radius:12px;border:1px solid var(--line);background:var(--surface);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;font-weight:700}
.rate button small{font:500 12px var(--mono);color:var(--muted)}
.rate .again{color:var(--bad)} .rate .again:hover{background:var(--bad-soft);border-color:var(--bad)}
.rate .hard{color:var(--warn)} .rate .hard:hover{background:var(--warn-soft);border-color:var(--warn)}
.rate .good{color:var(--ok)} .rate .good:hover{background:var(--ok-soft);border-color:var(--ok)}
.rate .easy{color:var(--info)} .rate .easy:hover{background:var(--info-soft);border-color:var(--info)}
.reveal{display:flex;justify-content:center;margin-top:18px}
.summary{text-align:center;padding:40px 24px}
.summary .big{font:700 54px/1 var(--sans);letter-spacing:-.03em;margin:12px 0}
.kgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:22px 0}
.kgrid div{padding:14px;border:1px solid var(--line);border-radius:12px;text-align:left}
.kgrid b{display:block;font:700 24px var(--sans)}
.kgrid span{font:500 11px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}

/* ---------- MCQ ---------- */
.builder{display:grid;grid-template-columns:1fr 340px;gap:20px;align-items:start}
.bpanel{padding:22px}
.bpanel h3{margin:0 0 4px;font-size:18px}
.field{margin:18px 0 0}
.field .lb{display:block;font:500 11.5px var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:8px}
.qwrap{max-width:820px;margin:0 auto}
.qhead{display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap}
.qhead .timer{margin-left:auto;font:600 15px var(--mono)}
.qcard{padding:28px 30px}
.stem{font-family:var(--serif);font-size:20px;line-height:1.6;margin:14px 0 22px}
.opts{display:flex;flex-direction:column;gap:10px}
.opt{display:flex;align-items:flex-start;gap:14px;width:100%;min-height:56px;padding:13px 16px;border:1.5px solid var(--line);border-radius:12px;background:var(--surface);text-align:left;font-size:16px;line-height:1.45;transition:border-color .15s,background .15s}
.opt:hover:not(:disabled){border-color:var(--accent-line);background:var(--surface-2)}
.opt .k{width:28px;height:28px;border-radius:8px;flex:none;display:grid;place-items:center;font:700 13px var(--mono);background:var(--bg-2);color:var(--ink-2)}
.opt.sel{border-color:var(--accent);background:var(--accent-soft)}
.opt.sel .k{background:var(--accent);color:var(--accent-ink)}
.opt.right{border-color:var(--ok);background:var(--ok-soft)}
.opt.right .k{background:var(--ok);color:#fff}
.opt.wrong{border-color:var(--bad);background:var(--bad-soft)}
.opt.wrong .k{background:var(--bad);color:#fff}
.opt:disabled{cursor:default;opacity:1}
.opt .fb{margin-left:auto;flex:none;font:700 11.5px var(--mono);align-self:center;letter-spacing:.04em}
.explain{margin-top:20px;padding:18px 20px;border-radius:12px;background:var(--surface-2);border:1px solid var(--line)}
.explain .verdict{display:flex;align-items:center;gap:8px;font-weight:700;font-size:17px;margin-bottom:8px}
.explain.ok .verdict{color:var(--ok)} .explain.bad .verdict{color:var(--bad)}
.explain p{margin:0;font-family:var(--serif);font-size:16.5px;line-height:1.6}
.qnav{display:flex;align-items:center;gap:10px;margin-top:20px;flex-wrap:wrap}
.qnav .right{margin-left:auto;display:flex;gap:8px}
.qdots{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0 0}
.qdots button{width:36px;height:36px;border-radius:8px;border:1px solid var(--line);background:var(--surface);font:600 12px var(--mono);color:var(--muted)}
.qdots .cur{border-color:var(--accent);color:var(--ink)}
.qdots .ans{background:var(--bg-2);color:var(--ink)}
.qdots .flag{box-shadow:inset 0 -3px 0 var(--warn)}
.score{display:grid;grid-template-columns:auto 1fr;gap:28px;align-items:center;padding:26px}
.donut{--p:0;width:132px;height:132px;border-radius:50%;background:conic-gradient(var(--ok) calc(var(--p)*1%),var(--bad-soft) 0);display:grid;place-items:center}
.donut div{width:100px;height:100px;border-radius:50%;background:var(--surface);display:grid;place-items:center;text-align:center}
.donut b{font:700 30px/1 var(--sans)} .donut small{display:block;font:11px var(--mono);color:var(--muted);margin-top:4px}
.topicbars{display:flex;flex-direction:column;gap:10px}
.topicbars div{display:grid;grid-template-columns:200px 1fr 60px;gap:12px;align-items:center;font-size:14px}
.topicbars .bar{height:8px}
details.qrev{display:block;padding:14px 18px;border-bottom:1px solid var(--line)}
details.qrev:last-child{border-bottom:0}
details.qrev summary{display:flex;gap:12px;align-items:flex-start;cursor:pointer;list-style:none;min-height:28px}
details.qrev summary::-webkit-details-marker{display:none}

/* ---------- Pearls ---------- */
.pearls{columns:3 300px;column-gap:16px}
.pearl{break-inside:avoid;margin:0 0 16px;padding:18px 18px 14px;border-left:3px solid var(--c,var(--accent))}
.pearl p{font-family:var(--serif);font-size:16.5px;line-height:1.55;margin:0 0 12px;transition:filter .2s}
.recall .pearl p{filter:blur(6px);cursor:pointer;user-select:none}
.recall .pearl.revealed p{filter:none}
.pearl .src{font-size:13px;color:var(--muted);display:flex;gap:10px;align-items:flex-start}
.pearl .src span{flex:1}
.save{border:0;background:none;color:var(--muted);width:40px;height:40px;display:grid;place-items:center;border-radius:8px;flex:none}
.save:hover{background:var(--bg-2)} .save.on{color:var(--accent)}
.qf{max-width:720px;margin:0 auto}
.qf .card{padding:32px 36px;min-height:300px;display:flex;flex-direction:column;gap:16px}
.qf blockquote{margin:0;font-family:var(--serif);font-size:24px;line-height:1.5;flex:1}
.qf .actions2{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:16px}
.qf .actions2 button{min-height:60px;font-size:16px}

/* ---------- Guidelines ---------- */
.gl-spec{margin-bottom:28px}
.gl-spec h3{display:flex;align-items:center;gap:10px;margin:0 0 10px;font-size:16px}
.rec-block{margin:0 0 16px;padding:18px 20px;box-shadow:none}
.rec-block h3{margin:0 0 6px;font-size:17px;display:flex;gap:10px;align-items:baseline}
.rec-block h3 .n{font:600 12px var(--mono);color:var(--accent)}
.rec-block .nar{font-family:var(--serif);font-size:16px;line-height:1.6;color:var(--ink-2);margin:0 0 10px}
.rec{display:flex;gap:12px;align-items:flex-start;padding:10px 12px;border-radius:10px;background:var(--surface-2);border:1px solid var(--line);margin-top:8px}
.rec .tick{width:22px;height:22px;flex:none;border-radius:6px;background:var(--accent-soft);color:var(--accent);display:grid;place-items:center;margin-top:1px}
.rec .tick svg{width:14px;height:14px}
.rec .st{flex:1;font-size:15.5px;line-height:1.5}
.rec .bd{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
details.full{margin-top:24px;border:1px solid var(--line);border-radius:12px;padding:0 18px;background:var(--surface)}
details.full summary{cursor:pointer;min-height:48px;display:flex;align-items:center;font-weight:700}

/* ---------- Reader (slide-over) ---------- */
.scrim{position:fixed;inset:0;background:rgba(8,12,18,.42);opacity:0;pointer-events:none;transition:opacity .2s;z-index:40}
.scrim.on{opacity:1;pointer-events:auto}
.reader{position:fixed;top:0;right:0;bottom:0;width:min(820px,100vw);background:var(--surface);z-index:41;transform:translateX(100%);transition:transform .26s var(--ease);display:flex;flex-direction:column;box-shadow:var(--shadow-lg)}
.reader.on{transform:none}
.reader-top{display:flex;align-items:center;gap:8px;padding:12px 18px;border-bottom:1px solid var(--line);flex-wrap:wrap}
.reader-body{overflow:auto;padding:28px 44px 80px}
.reader-body h1.rt{font-family:var(--serif);font-weight:600;font-size:30px;line-height:1.2;margin:12px 0 10px}
.rmeta{display:flex;flex-wrap:wrap;gap:6px 16px;font:12.5px var(--mono);color:var(--muted);margin-bottom:20px}
.callout{padding:16px 18px;border-radius:12px;background:var(--accent-soft);border:1px solid var(--accent-line);margin:0 0 18px}
.callout .eyebrow{color:var(--accent);margin-bottom:8px;display:block}
.callout ul{margin:0;padding-left:18px}
.callout li{margin:5px 0;font-family:var(--serif);font-size:16px;line-height:1.5}
.kv{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin:0 0 22px}
.kv div{padding:12px 14px;border:1px solid var(--line);border-radius:10px}
.kv b{display:block;font:500 10.5px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:4px}

/* ---------- Palette / Modal ---------- */
.palette{position:fixed;left:50%;top:11vh;transform:translate(-50%,-8px);width:min(700px,94vw);z-index:51;opacity:0;pointer-events:none;transition:.16s;overflow:hidden;box-shadow:var(--shadow-lg)}
.palette.on{opacity:1;pointer-events:auto;transform:translate(-50%,0)}
.palette .input{border:0;border-bottom:1px solid var(--line);border-radius:0;min-height:58px;padding:0 18px;font-size:17px}
.pal-res{max-height:58vh;overflow:auto;padding:8px}
.pal-group{font:500 10.5px var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted);padding:12px 12px 6px}
.pal-item{display:flex;gap:12px;align-items:center;width:100%;border:0;background:none;text-align:left;min-height:44px;padding:8px 12px;border-radius:10px}
.pal-item[aria-selected="true"],.pal-item:hover{background:var(--bg-2)}
.pal-item .pt{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pal-item .ps{font:12px var(--mono);color:var(--muted);margin-left:auto;white-space:nowrap}
.pal-foot{display:flex;gap:16px;padding:10px 16px;border-top:1px solid var(--line);font:12px var(--mono);color:var(--muted)}
.modal{position:fixed;inset:0;display:grid;place-items:center;z-index:60;padding:20px;background:rgba(8,12,18,.5);opacity:0;pointer-events:none;transition:.2s}
.modal.on{opacity:1;pointer-events:auto}
.modal .card{width:min(620px,100%);max-height:86vh;display:flex;flex-direction:column;box-shadow:var(--shadow-lg)}
.modal .mb{overflow:auto;padding:28px 32px 8px}
.modal .mf{padding:16px 32px 22px;display:flex;justify-content:flex-end;gap:10px;border-top:1px solid var(--line)}
.modal .prose{font-size:16px}
.toast{position:fixed;left:50%;bottom:28px;transform:translate(-50%,20px);background:var(--ink);color:var(--bg);padding:12px 18px;border-radius:12px;font-weight:700;opacity:0;transition:.2s;z-index:70;pointer-events:none}
.toast.on{opacity:1;transform:translate(-50%,0)}

/* ---------- Responsive ---------- */
.tabbar{display:none}
@media (max-width:1200px){
  .hub{grid-template-columns:minmax(0,1fr) 290px}
  .toc{display:none}
}
@media (max-width:1050px){
  .actions{grid-template-columns:1fr 1fr}
  .actions .act.feature{grid-column:1/-1}
  .twocol,.builder{grid-template-columns:1fr}
  .hub{grid-template-columns:1fr}
  .prac{position:static}
}
@media (max-width:860px){
  .shell{grid-template-columns:1fr}
  .rail{display:none}
  .topbar{padding:10px 14px;gap:8px}
  .streak span{display:none}
  .content{padding:4px 16px 112px}
  .hello h1{font-size:26px}
  .week{margin-left:0}
  .actions{grid-template-columns:1fr}
  .act{min-height:0;padding:18px}
  .act .ic{display:none}
  .act .big{font-size:32px}
  h1.pt{font-size:28px}
  .hub-head h1{font-size:29px}
  .topics{grid-template-columns:1fr}
  .tree{position:static;max-height:none;display:flex;overflow:auto;gap:6px;padding-bottom:6px}
  .tree button{white-space:nowrap;width:auto;flex:none;border:1px solid var(--line);background:var(--surface)}
  .tree .c{margin-left:6px}
  .tree .rail-label{display:none}
  .reader-body{padding:20px 18px 80px}
  .kbd{display:none}
  .face{padding:26px 22px} .face.front .q{font-size:22px}
  .flip-in{min-height:360px}
  .rate{grid-template-columns:repeat(2,1fr)}
  .qcard{padding:20px 18px} .stem{font-size:18px}
  .kgrid{grid-template-columns:1fr 1fr}
  .score{grid-template-columns:1fr;justify-items:center;text-align:center}
  .topicbars{width:100%}
  .topicbars div{grid-template-columns:1fr 1fr 44px;text-align:left}
  .qf .card{padding:24px 22px} .qf blockquote{font-size:20px}
  .tabbar{display:flex;position:fixed;left:0;right:0;bottom:0;z-index:30;background:var(--surface);border-top:1px solid var(--line);padding:4px 4px calc(4px + env(safe-area-inset-bottom))}
  .tabbar button{flex:1;border:0;background:none;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;min-height:54px;font-size:11.5px;font-weight:700;color:var(--muted)}
  .tabbar svg{width:22px;height:22px}
  .tabbar button[aria-current="page"]{color:var(--accent)}
}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{transition:none!important;animation:none!important}}
</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<symbol id="i-home" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/></symbol>
<symbol id="i-book" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 6.5C10 5 7 4.5 3 5v14c4-.5 7 0 9 1.5 2-1.5 5-2 9-1.5V5c-4-.5-7 0-9 1.5z"/><path d="M12 6.5v14"/></symbol>
<symbol id="i-cards" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="7" width="14" height="13" rx="2"/><path d="M7 4h12a2 2 0 0 1 2 2v11"/></symbol>
<symbol id="i-quiz" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="M7 8.5l1.5 1.5L11 7.5M7 15.5l1.5 1.5L11 14.5M14 9h3M14 16h3"/></symbol>
<symbol id="i-pearl" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8"/><circle cx="9.5" cy="9.5" r="2"/></symbol>
<symbol id="i-guide" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 4h6l1 2h3v15H5V6h3z"/><path d="M9 4v3h6V4M9 12l2 2 4-4M9 17h6"/></symbol>
<symbol id="i-paper" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z"/><path d="M14 3v5h5M8 13h8M8 17h5"/></symbol>
<symbol id="i-trial" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3h6M10 3v6L4.5 18.5A1.7 1.7 0 0 0 6 21h12a1.7 1.7 0 0 0 1.5-2.5L14 9V3"/><path d="M7 15h10"/></symbol>
<symbol id="i-bm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12v18l-6-4-6 4z"/></symbol>
<symbol id="i-bmf" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="M6 3h12v18l-6-4-6 4z"/></symbol>
<symbol id="i-search" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></symbol>
<symbol id="i-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></symbol>
<symbol id="i-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z"/></symbol>
<symbol id="i-x" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></symbol>
<symbol id="i-ext" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></symbol>
<symbol id="i-print" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M7 9V3h10v6M7 17H4v-6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v6h-3"/><path d="M7 14h10v7H7z"/></symbol>
<symbol id="i-left" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></symbol>
<symbol id="i-right" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></symbol>
<symbol id="i-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></symbol>
<symbol id="i-eye" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></symbol>
<symbol id="i-bolt" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L4 14h7l-1 8 9-12h-7z"/></symbol>
<symbol id="i-flame" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c4 0 7-2.8 7-7 0-3.5-2.5-6-4-8-.5 2-1.5 3-3 3 .5-3-1-6-4-8 0 4-5 6.5-5 13 0 4.2 4 7 9 7z"/></symbol>
<symbol id="i-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></symbol>
<symbol id="i-flag" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 21V4M5 4h11l-2 4 2 4H5"/></symbol>
<symbol id="i-shuffle" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5"/></symbol>
<symbol id="i-info" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/></symbol>
<symbol id="i-msg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a8 8 0 0 1-11.8 7L3 21l2-6.2A8 8 0 1 1 21 12z"/></symbol>
<symbol id="i-logout" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h4M16 17l5-5-5-5M21 12H9"/></symbol>
<symbol id="i-clock" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></symbol>
<symbol id="i-text" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 18L9 6l5 12M5.8 14h6.4M15 18l3-7 3 7M16 16h4"/></symbol>
</defs></svg>

<div class="readbar" id="readbar"></div>
<div class="shell">
  <aside class="rail" aria-label="Primary">
    <a class="brand" href="?v=today" data-go="today">
      <span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 13h4l2-4 3 9 3-13 2.5 8H22"/></svg></span>
      <span class="brand-name">hack.CCM <span>study</span></span>
    </a>
    <nav id="nav"></nav>
    <div class="rail-foot">
      <button class="nav-btn" data-act="about"><svg class="i"><use href="#i-info"/></svg>About &amp; credits</button>
      <button class="nav-btn" data-act="feedback"><svg class="i"><use href="#i-msg"/></svg>Send feedback</button>
      <button class="nav-btn" data-act="classic"><svg class="i"><use href="#i-left"/></svg>Classic view</button>
      <button class="nav-btn" data-act="logout" id="logoutBtn"><svg class="i"><use href="#i-logout"/></svg>Sign out</button>
    </div>
  </aside>
  <div class="main">
    <header class="topbar" id="topbar">
      <button class="search-trigger" data-act="palette" aria-label="Search everything"><svg class="i"><use href="#i-search"/></svg><span>Search topics, cards, MCQs, guidelines…</span><span class="kbd">Ctrl K</span></button>
      <div class="top-actions">
        <div class="streak" id="streak" title="Study streak"><svg class="i"><use href="#i-flame"/></svg><b id="streakN">0</b><span>day streak</span></div>
        <button class="icon-btn" id="themeBtn" aria-label="Toggle dark mode"></button>
        <button class="avatar" id="avatar" aria-label="Account">?</button>
      </div>
    </header>
    <main class="content" id="view" tabindex="-1"></main>
  </div>
</div>
<nav class="tabbar" id="tabbar" aria-label="Primary"></nav>

<div class="scrim" id="scrim"></div>
<aside class="reader" id="reader" role="dialog" aria-modal="true" aria-label="Reader">
  <div class="reader-top" id="readerTop"></div>
  <div class="reader-body" id="readerBody"></div>
</aside>
<div class="palette card" id="palette" role="dialog" aria-modal="true" aria-label="Search">
  <label class="input"><svg class="i"><use href="#i-search"/></svg><input id="palInput" placeholder="Search everything…" autocomplete="off" aria-label="Search"><span class="kbd">Esc</span></label>
  <div class="pal-res" id="palRes" role="listbox"></div>
  <div class="pal-foot"><span>↑↓ move</span><span>↵ open</span><span>/ or Ctrl K anywhere</span></div>
</div>
<div class="modal" id="modal" role="dialog" aria-modal="true"><div class="card"><div class="mb prose" id="modalBody"></div><div class="mf" id="modalFoot"></div></div></div>
<div class="toast" id="toast" role="status" aria-live="polite"></div>

<script>
(function(){
"use strict";
/* =========================================================== core */
var D=null, BM={items:{},folders:{}}, PR={cards:{},mcq:{},notes:{},activity:{},last:{}};
var S={view:'today', params:{}, topics:{spec:'',q:''}, topic:null, cards:{session:null}, mcq:{run:null, cfg:{spec:'',topic:'',n:10,mode:'tutor',filter:'all'}},
       pearls:{mode:'grid',q:'',system:'',subtopic:'',page:1,items:[],total:0,pages:1,recall:false,qf:null},
       gl:{q:'',spec:''}, lib:{spec:'',type:'',q:'',sort:'new',limit:40}, trials:{src:'esbicm',q:'',spec:'',res:'',limit:40}};
var $=function(s,r){return (r||document).querySelector(s)}, $$=function(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))};
var esc=function(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})};
var ic=function(id,st){return '<svg class="i" aria-hidden="true"'+(st?' style="'+st+'"':'')+'><use href="#'+id+'"/></svg>'};
function hashColor(s){var h=0;for(var i=0;i<s.length;i++)h=(h*31+s.charCodeAt(i))>>>0;return 'hsl('+(h%360)+' 42% 45%)'}
var color=function(s){return (D&&D.colors&&D.colors[s])||hashColor(s||'')};
function md(src){return window.marked?marked.parse(String(src||'')):'<pre style="white-space:pre-wrap">'+esc(src)+'</pre>'}
function mdi(src){return window.marked?marked.parseInline(esc(src)):esc(src)}
function mathify(el){if(window.renderMathInElement&&el){try{renderMathInElement(el,{delimiters:[{left:'$$',right:'$$',display:true},{left:'\\(',right:'\\)',display:false}],throwOnError:false})}catch(e){}}}
function api(url,opts){return fetch(url,Object.assign({credentials:'same-origin'},opts||{})).then(function(r){if(r.status===401){location.reload()}return r.json()})}
function trunc(s,n){s=String(s||'');return s.length>n?s.slice(0,n-1)+'…':s}
function count(arr,key){var m={};arr.forEach(function(x){var k=x[key]||'Other';m[k]=(m[k]||0)+1});return m}
function keysBy(m){return Object.keys(m).sort(function(a,b){return m[b]-m[a]||a.localeCompare(b)})}
function ymd(d){return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)}
function today(){return ymd(new Date())}
function addDays(n){var d=new Date();d.setDate(d.getDate()+n);return ymd(d)}
function pill(s,extra){return '<span class="pill"><span class="dot" style="--c:'+color(s)+'"></span>'+esc(s)+(extra?' · '+esc(extra):'')+'</span>'}
function toast(t){var el=$('#toast');el.textContent=t;el.classList.add('on');clearTimeout(toast._t);toast._t=setTimeout(function(){el.classList.remove('on')},1800)}
function shuffle(a){a=a.slice();for(var i=a.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));var t=a[i];a[i]=a[j];a[j]=t}return a}
var isGuideline=function(a){return (a.type||'').toLowerCase()==='guideline'}, isPaper=function(a){return !isGuideline(a)};
function resTag(r){r=(r||'').toLowerCase();return r.indexOf('harm')>-1?'bad':r.indexOf('pos')>-1?'ok':r.indexOf('mix')>-1?'warn':'neu'}
function norm(s){return String(s||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim()}

/* =========================================================== progress */
var pending={cards:{},mcq:{},notes:{},activity_inc:0,last:null}, flushT=null;
function queue(kind,id,val){pending[kind][id]=val;PR[kind][id]=val;later()}
function bump(n){pending.activity_inc+=n||1;var t=today();PR.activity[t]=(PR.activity[t]||0)+(n||1);later();renderStreak()}
function setLast(o){pending.last=Object.assign(pending.last||{},o);PR.last=Object.assign(PR.last||{},o);later()}
function later(){clearTimeout(flushT);flushT=setTimeout(flush,1200)}
function flush(){
  var body={},any=false;
  ['cards','mcq','notes'].forEach(function(k){if(Object.keys(pending[k]).length){body[k]=pending[k];any=true}});
  if(pending.activity_inc){body.activity_inc=pending.activity_inc;any=true}
  if(pending.last){body.last=pending.last;any=true}
  if(!any)return;
  pending={cards:{},mcq:{},notes:{},activity_inc:0,last:null};
  fetch('/api/redefined/progress',{method:'PATCH',credentials:'same-origin',keepalive:true,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).catch(function(){});
}
window.addEventListener('pagehide',flush);
document.addEventListener('visibilitychange',function(){if(document.visibilityState==='hidden')flush()});
function streak(){var n=0,d=new Date();if(!(PR.activity[today()]>0))d.setDate(d.getDate()-1);
  for(var g=0;g<400;g++){var k=ymd(d);if(PR.activity[k]>0){n++;d.setDate(d.getDate()-1)}else break}return n}
function renderStreak(){$('#streakN').textContent=streak()}

/* SM-2 lite. card state {e:ease, i:interval days, d:due, r:reps, l:lapses} */
function sm2(st,q){
  st=Object.assign({e:2.5,i:0,r:0,l:0},st||{});
  if(q===1){st.r=0;st.l++;st.i=0;st.e=Math.max(1.3,st.e-0.2);st.d=today();return st}
  st.r++;
  if(st.r===1)st.i=q===4?3:1;
  else if(st.r===2)st.i=q===2?3:q===3?4:6;
  else st.i=Math.max(st.i+1,Math.round(st.i*st.e*(q===2?0.8:q===4?1.3:1)));
  st.e=Math.max(1.3,st.e+(q===2?-0.15:q===4?0.15:0));
  st.d=addDays(st.i);return st}
function previewIv(st,q){var s=sm2(JSON.parse(JSON.stringify(st||{})),q);return q===1?'<10m':s.i<30?s.i+'d':Math.round(s.i/30)+'mo'}
function cardState(id){return PR.cards[id]}
function isDue(id){var s=PR.cards[id];return !!(s&&s.d&&s.d<=today())}
function deckStats(d){var due=0,neu=0,learned=0,mast=0;d.cards.forEach(function(c){var s=PR.cards[c.id];if(!s)neu++;else{learned++;if(s.d<=today())due++;if(s.i>=21)mast++}});return {due:due,neu:neu,learned:learned,mast:mast,total:d.cards.length}}
function totalDue(){var n=0;D.decks.forEach(function(d){n+=deckStats(d).due});return n}
function totalNew(){return D.decks.reduce(function(a,d){return a+deckStats(d).neu},0)}

/* =========================================================== nav */
var NAV=[{sep:'Study'},{id:'today',label:'Today',icon:'i-home'},{id:'topics',label:'Topics',icon:'i-book',feat:'theory'},
  {id:'cards',label:'Flashcards',icon:'i-cards',feat:'theory'},{id:'mcq',label:'MCQs',icon:'i-quiz',feat:'theory'},
  {id:'pearls',label:'Pearls',icon:'i-pearl',feat:'pearls'},{sep:'Reference'},{id:'guidelines',label:'Guidelines',icon:'i-guide',feat:'guidelines'},
  {id:'saved',label:'Saved',icon:'i-bm',feat:'bookmarks'},{sep:'Evidence',ev:true},{id:'papers',label:'Papers',icon:'i-paper',feat:'papers'},
  {id:'trials',label:'Trials',icon:'i-trial',feat:'trials'}];
var TABS=['today','topics','cards','mcq','pearls'];
function navMeta(id){
  if(id==='topics')return '<span class="count">'+D.notes.length+'</span>';
  if(id==='cards'){var n=totalDue();return n?'<span class="due" title="cards due">'+n+'</span>':'<span class="count">'+D.decks.reduce(function(a,d){return a+d.cards.length},0)+'</span>'}
  if(id==='mcq')return '<span class="count">'+D.mcqs.length+'</span>';
  if(id==='pearls')return '<span class="count">'+D.pearl_count+'</span>';
  if(id==='guidelines')return '<span class="count">'+D.articles.filter(isGuideline).length+'</span>';
  if(id==='papers')return '<span class="count">'+D.articles.filter(isPaper).length+'</span>';
  if(id==='trials')return '<span class="count">'+(D.trials.length+D.condensed.length)+'</span>';
  if(id==='saved'){var k=Object.keys(BM.items||{}).length;return k?'<span class="count">'+k+'</span>':''}
  return ''}
function curNav(){return S.view==='topic'?'topics':S.view}
function renderNav(){
  var h='',t='',ev=false;
  NAV.forEach(function(n){
    if(n.sep){if(n.ev){h+='<div class="nav-evidence">';ev=true}h+='<div class="rail-label">'+n.sep+'</div>';return}
    if(n.feat&&!D.features[n.feat])return;
    var cur=curNav()===n.id?' aria-current="page"':'';
    h+='<button class="nav-btn" data-go="'+n.id+'"'+cur+'>'+ic(n.icon)+'<span>'+n.label+'</span>'+navMeta(n.id)+'</button>';
    if(TABS.indexOf(n.id)>-1)t+='<button data-go="'+n.id+'"'+cur+'>'+ic(n.icon)+'<span>'+(n.id==='cards'?'Cards':n.label)+'</span></button>';
  });
  if(ev)h+='</div>';
  $('#nav').innerHTML=h;$('#tabbar').innerHTML=t}
function setURL(view,params){var u=new URL(location);u.search='';u.searchParams.set('v',view);
  if(params)Object.keys(params).forEach(function(k){if(params[k]!=null&&params[k]!=='')u.searchParams.set(k,params[k])});history.pushState(null,'',u)}
function go(view,params){
  if(S.view==='topic'&&view!=='topic')saveReading();
  S.view=view;S.params=params||{};setURL(view,params);renderNav();render();window.scrollTo(0,0);$('#view').focus({preventScroll:true})}
window.addEventListener('popstate',function(){if(S.view==='topic')saveReading();readURL();renderNav();render()});
function readURL(){var u=new URL(location);S.view=u.searchParams.get('v')||'today';S.params={};u.searchParams.forEach(function(v,k){if(k!=='v')S.params[k]=v})}

document.addEventListener('click',function(e){
  var g=e.target.closest('[data-go]');if(g){e.preventDefault();var p={};Object.keys(g.dataset).forEach(function(k){if(/^p[A-Z]/.test(k))p[k.slice(1).toLowerCase()]=g.dataset[k]});closeReader();go(g.dataset.go,p);return}
  var a=e.target.closest('[data-act]');if(a&&ACT[a.dataset.act]){e.preventDefault();ACT[a.dataset.act](a);return}
  var b=e.target.closest('[data-bm]');if(b){var ref=b.dataset.bm,icon=b.classList.contains('save');toggleBM(ref,JSON.parse(b.dataset.meta)).then(function(){var on=!!BM.items[ref];b.classList.toggle(icon?'on':'saved',on);b.innerHTML=ic(on?'i-bmf':'i-bm')+(icon?'':(on?'Saved':'Save'));renderNav()});return}
  var o;
  if((o=e.target.closest('[data-article]'))){openArticle(D.articles.find(function(x){return x.id===o.dataset.article}));return}
  if((o=e.target.closest('[data-guideline]'))){openGuideline(D.articles.find(function(x){return x.id===o.dataset.guideline}));return}
  if((o=e.target.closest('[data-trial]'))){openTrial(o.dataset.trial);return}
  if((o=e.target.closest('[data-cond]'))){var p2=o.dataset.cond.split('|');openCond(p2[0],p2[1]);return}
  if((o=e.target.closest('[data-ref]'))){openRef(o.dataset.ref);return}
});
var ACT={
  about:function(){modal(md(D.disclaimer)+'<hr>'+md(D.credits),[['Close','']])},
  feedback:function(){window.open(D.links.feedback,'_blank','noopener')},
  classic:function(){location.href='/classic'},
  logout:function(){flush();fetch('/api/logout',{method:'POST',credentials:'same-origin'}).then(function(){location.href='/'})},
  palette:function(){openPalette()},
  closeReader:function(){closeReader()}
};

/* =========================================================== render */
var VIEWS={}, AFTER={};
function render(){var v=VIEWS[S.view]?S.view:'today';$('#view').innerHTML=VIEWS[v]();if(AFTER[v])AFTER[v]();$('#readbar').style.width='0'}

/* ---------------- Today ---------------- */
VIEWS.today=function(){
  var hr=new Date().getHours(), greet=hr<12?'Good morning':hr<17?'Good afternoon':'Good evening';
  var th=D.features.theory, due=th?totalDue():0, neu=th?totalNew():0;
  var last=PR.last&&PR.last.note&&noteById(PR.last.note), pick=last||suggestNote(), sk=streak();
  var week='', days=['S','M','T','W','T','F','S'];
  for(var i=6;i>=0;i--){var dd=new Date();dd.setDate(dd.getDate()-i);var k=ymd(dd),n=PR.activity[k]||0;
    week+='<div class="'+(i===0?'today':'')+'"><i class="'+(n?'on':'')+'" style="height:'+(8+Math.min(n,40))+'px" title="'+n+' items"></i>'+days[dd.getDay()]+'</div>'}
  var h='<section class="hello"><div><span class="eyebrow">'+esc(new Date().toLocaleDateString(undefined,{weekday:'long',day:'numeric',month:'long'}))+'</span>'+
    '<h1>'+greet+', '+esc(D.user.name)+'.</h1><p class="muted" style="margin:6px 0 0">'+(sk?sk+'-day streak — keep it going.':'Ten focused minutes today starts a streak.')+'</p></div>'+
    '<div class="week" role="img" aria-label="Study activity over the last 7 days">'+week+'</div></section>';
  if(th){
    h+='<section class="actions">';
    if(pick){var p=PR.notes[pick.id]||{};
      h+='<button class="card act feature" data-go="topic" data-pid="'+esc(pick.id)+'"><span class="eyebrow">'+(last?'Continue reading':'Suggested topic')+'</span>'+pill(pick.system,pick.subtopic)+
        '<h3 class="serif" style="font-size:24px">'+esc(pick.title)+'</h3><div class="bar" style="max-width:320px"><i class="b1" style="width:'+(p.p||0)+'%"></i></div>'+
        '<div class="foot"><span>'+(p.p?Math.round(p.p)+'% read':readMins(pick)+' min read')+'</span><span class="go">'+(last?'Resume':'Start')+ic('i-arrow')+'</span></div></button>'}
    h+='<button class="card act" data-act="reviewAll"><span class="ic">'+ic('i-cards')+'</span><span class="eyebrow">Flashcards</span><span class="big">'+due+'</span>'+
        '<div class="muted">'+(due?'cards due for review':'nothing due')+(neu?' · '+neu+' new':'')+'</div><div class="foot"><span>Spaced repetition</span><span class="go">'+(due?'Review':'Learn new')+ic('i-arrow')+'</span></div></button>';
    h+='<button class="card act" data-act="daily"><span class="ic">'+ic('i-quiz')+'</span><span class="eyebrow">Daily 10 MCQs</span><span class="big">'+Math.min(10,D.mcqs.length)+'</span>'+
        '<div class="muted">'+(D.mcqs.length?mcqAccuracyText():'No MCQs generated yet')+'</div><div class="foot"><span>Tutor mode</span><span class="go">'+(D.mcqs.length?'Start':'Set up')+ic('i-arrow')+'</span></div></button>';
    h+='</section>'}
  h+='<section class="twocol"><div>';
  if(th){h+='<h2 class="sec">Your topic map <a class="link" href="?v=topics" data-go="topics">All topics →</a></h2><div class="spec-map">';
    var sp=specSummary();keysBy(sp.notes).forEach(function(s){
      var read=D.notes.filter(function(n){return n.system===s&&PR.notes[n.id]&&PR.notes[n.id].r}).length;
      h+='<button class="spec" style="--c:'+color(s)+'" data-go="topics" data-pspec="'+esc(s)+'"><span class="hd"><span class="sw"></span>'+esc(s)+'</span>'+
        '<span class="nums"><span><b>'+sp.notes[s]+'</b> topics</span>'+(sp.cards[s]?'<span><b>'+sp.cards[s]+'</b> cards</span>':'')+(sp.mcq[s]?'<span><b>'+sp.mcq[s]+'</b> MCQs</span>':'')+'</span>'+
        '<span class="bar" title="'+read+' of '+sp.notes[s]+' read"><i class="b1" style="width:'+(read/sp.notes[s]*100)+'%"></i></span></button>'});
    h+='</div>'}
  else h+='<div class="card empty" style="margin-top:40px">Theory topics, flashcards and MCQs are not enabled for this account yet. Ask an admin to enable the <b>theory</b> feature.</div>';
  h+='</div><div>';
  var pod=D.pearl_of_day;
  if(pod)h+='<h2 class="sec">Pearl of the day</h2><div class="card pod">'+pill(pod.system,pod.subtopic&&pod.subtopic!==pod.system?trunc(pod.subtopic,28):'')+'<blockquote>“'+mdi(pod.pearl)+'”</blockquote>'+
      '<div class="muted" style="font-size:13.5px">'+esc(trunc(pod.source_paper,120))+'</div><div style="margin-top:14px"><button class="btn sm" data-go="pearls" data-pmode="quick">'+ic('i-bolt')+'Quick-fire pearls</button></div></div>';
  var gls=D.articles.filter(isGuideline).sort(function(a,b){return (b.date_added||'').localeCompare(a.date_added||'')}).slice(0,5);
  if(gls.length&&D.features.guidelines)h+='<h2 class="sec">Latest guidelines <a class="link" href="?v=guidelines" data-go="guidelines">All →</a></h2><div class="card list">'+gls.map(guidelineRow).join('')+'</div>';
  h+='</div></section>';
  return h};
function readMins(n){return Math.max(1,Math.round((n.words||800)/220))}
function noteById(id){return D.notes.find(function(n){return n.id===id||n.rel===id})}
function suggestNote(){var un=D.notes.filter(function(n){return !(PR.notes[n.id]&&PR.notes[n.id].r)});var a=un.length?un:D.notes;return a.length?a[Math.floor(Date.now()/864e5)%a.length]:null}
function specSummary(){var o={notes:count(D.notes,'system'),cards:{},mcq:count(D.mcqs.map(function(q){return {system:q.s}}),'system')};D.decks.forEach(function(d){o.cards[d.specialty]=(o.cards[d.specialty]||0)+d.cards.length});return o}
function mcqTotals(){var n=0,c=0;Object.keys(PR.mcq).forEach(function(k){n+=PR.mcq[k].n||0;c+=PR.mcq[k].c||0});return {n:n,c:c}}
function mcqAccuracyText(){var t=mcqTotals();return t.n?Math.round(t.c/t.n*100)+'% correct over '+t.n+' answers':'Mixed questions across your topics'}
ACT.daily=function(){if(!D.mcqs.length){go('mcq');return}startMcq(pickMcqs({spec:'',topic:'',n:10,filter:'unseen'}),'tutor')};

/* ---------------- Topics ---------------- */
VIEWS.topics=function(){
  var T=S.topics;if(S.params&&S.params.spec!=null){T.spec=S.params.spec;S.params={}}
  var specs=count(D.notes,'system');
  return '<span class="eyebrow">Study</span><h1 class="pt">Theory topics</h1><p class="psub">'+D.notes.length+' structured notes, each linked to its own flashcards, MCQs, pearls and guidelines. Read first, then practise.</p>'+
    '<div class="topics"><nav class="tree" aria-label="Specialties"><div class="rail-label" style="padding-top:0">Specialty</div>'+
    '<button data-tspec="" aria-pressed="'+(!T.spec)+'">All topics<span class="c">'+D.notes.length+'</span></button>'+
    keysBy(specs).map(function(s){return '<button data-tspec="'+esc(s)+'" aria-pressed="'+(T.spec===s)+'"><span class="dot" style="--c:'+color(s)+'"></span>'+esc(s)+'<span class="c">'+specs[s]+'</span></button>'}).join('')+
    '</nav><div><div class="toolbar"><label class="input">'+ic('i-search')+'<input id="tq" placeholder="Search topics, e.g. ARDS, ACLS, coagulopathy" value="'+esc(T.q)+'" aria-label="Search topics"></label></div><div id="tlist"></div></div></div>'};
AFTER.topics=function(){
  $$('[data-tspec]').forEach(function(b){b.onclick=function(){S.topics.spec=b.dataset.tspec;render()}});
  $('#tq').addEventListener('input',function(e){S.topics.q=e.target.value;tlist()});tlist()};
function topicBadges(n){var b='',dk=decksFor(n),mq=mcqsFor(n);
  if(dk.length)b+='<span class="tag acc">'+dk.reduce(function(a,d){return a+d.cards.length},0)+' cards</span>';
  if(mq.length)b+='<span class="tag info">'+mq.length+' MCQs</span>';
  b+='<span class="tag neu">'+readMins(n)+' min</span>';return b}
function ringHTML(n){var p=PR.notes[n.id]||{};if(p.r)return '<span class="ringwrap" title="Read"><span class="ring done"></span>'+ic('i-check','position:absolute;width:16px;height:16px;color:var(--accent-ink)')+'</span>';
  return '<span class="ring" style="--p:'+Math.round(p.p||0)+'" title="'+Math.round(p.p||0)+'% read"></span>'}
function tlist(){
  var T=S.topics,q=norm(T.q),rows=D.notes.filter(function(n){return (!T.spec||n.system===T.spec)&&(!q||q.split(' ').every(function(w){return norm(n.title+' '+n.subtopic+' '+n.system).indexOf(w)>-1}))});
  if(!rows.length){$('#tlist').innerHTML='<div class="card empty">No topics match.</div>';return}
  var groups={};rows.forEach(function(n){var k=(T.spec?'':n.system+' › ')+n.subtopic;(groups[k]=groups[k]||[]).push(n)});
  $('#tlist').innerHTML=Object.keys(groups).sort().map(function(k){var ns=groups[k];
    return '<section class="tgroup"><h3>'+(T.spec?'':'<span class="dot" style="--c:'+color(ns[0].system)+'"></span>')+esc(k)+'<span class="ln"></span><span class="mono muted" style="font-size:12px">'+ns.length+'</span></h3><div class="tcards">'+
      ns.map(function(n){return '<button class="tcard" data-go="topic" data-pid="'+esc(n.id)+'">'+ringHTML(n)+'<span><span class="tt">'+esc(n.title)+'</span><span class="tm">'+topicBadges(n)+'</span></span></button>'}).join('')+'</div></section>'}).join('')}
function decksFor(n){var st=norm(n.subtopic),tt=norm(n.title);return D.decks.filter(function(d){if(d.specialty!==n.system)return false;var dt=norm(d.title);
  return dt===st||(st&&st.indexOf(dt)>-1)||(st&&dt.indexOf(st)>-1)||(d.subtopics||[]).some(function(s){return norm(s)===st})||tt.indexOf(dt)>-1})}
function mcqsFor(n){return D.mcqs.filter(function(q){return q.src===n.rel||(q.s===n.system&&q.t===n.subtopic)})}

/* ---------------- Topic hub ---------------- */
VIEWS.topic=function(){
  var n=noteById((S.params||{}).id);if(!n)return '<div class="card empty">Topic not found. <a href="?v=topics" data-go="topics">Back to topics</a></div>';
  S.topic={note:n,maxP:(PR.notes[n.id]||{}).p||0};setLast({note:n.id,at:new Date().toISOString()});
  var ref='note:'+n.id,on=!!BM.items[ref],dk=decksFor(n),mq=mcqsFor(n),done=(PR.notes[n.id]||{}).r;
  return '<div class="crumbs"><button data-go="topics">Topics</button>›<button data-go="topics" data-pspec="'+esc(n.system)+'">'+esc(n.system)+'</button>›<span>'+esc(n.subtopic)+'</span></div>'+
   '<div class="hub"><nav class="toc" id="toc" aria-label="On this page"></nav><article><header class="hub-head"><h1>'+esc(n.title)+'</h1>'+
   '<div class="hub-meta">'+pill(n.system,n.subtopic)+'<span>'+ic('i-clock')+readMins(n)+' min read</span><span id="pctTxt">'+Math.round(S.topic.maxP)+'% read</span></div>'+
   '<div class="hub-actions"><button class="btn'+(done?' saved':' primary')+'" data-act="markRead">'+ic('i-check')+(done?'Read':'Mark as read')+'</button>'+
   '<button class="btn'+(on?' saved':'')+'" data-bm="'+esc(ref)+'" data-meta="'+esc(JSON.stringify({kind:'note',title:n.title,system:n.system,type:'Theory',locator:{note:n.id}}))+'">'+ic(on?'i-bmf':'i-bm')+(on?'Saved':'Save')+'</button>'+
   '<button class="btn" data-act="fs" data-d="-1" aria-label="Smaller text">A−</button><button class="btn" data-act="fs" data-d="1" aria-label="Larger text">A+</button>'+
   (D.features.print_notes?'<a class="btn" href="/export/print?kind=note&file_name='+encodeURIComponent(n.id)+'&title='+encodeURIComponent(n.title)+'" target="_blank" rel="noopener">'+ic('i-print')+'Print</a>':'')+'</div></header>'+
   '<div class="prose" id="noteBody"><div class="empty">Loading…</div></div></article>'+
   '<aside class="prac" aria-label="Practise this topic"><div class="card"><h4>Practise this topic</h4>'+
   dk.map(function(d){var st=deckStats(d);return '<button class="pa" data-act="studyDeck" data-deck="'+esc(d.id)+'"><span class="ic">'+ic('i-cards')+'</span><span><b>'+esc(d.title)+'</b><small>'+d.cards.length+' cards · '+st.due+' due · '+st.neu+' new</small></span></button>'}).join('')+
   (mq.length?'<button class="pa" data-act="topicMcq"><span class="ic">'+ic('i-quiz')+'</span><span><b>'+mq.length+' MCQs</b><small>Tutor mode, instant explanations</small></span></button>':'')+
   (!dk.length&&!mq.length?'<p class="muted" style="margin:0;font-size:14px">No flashcards or MCQs for this topic yet.</p>':'')+
   '</div><div class="card" id="tPearls"><h4>Pearls</h4><div class="muted" style="font-size:14px">Loading…</div></div><div class="card" id="tRel"><h4>Related</h4><div class="muted" style="font-size:14px">Loading…</div></div></aside></div>'};
AFTER.topic=function(){
  if(!S.topic||!$('#noteBody'))return;var n=S.topic.note;
  api('/api/redefined/note?id='+encodeURIComponent(n.id)).then(function(d){
    var el=$('#noteBody');if(!el)return;var body=String(d.md||'').replace(/^\s*(<img[^\n]*\n)?\s*#\s+.*\n/,'').replace(/\[\^[\w.-]+\](?!:)/g,'');el.innerHTML=md(body);mathify(el);buildToc(el);onScrollRead()});
  var pearlBox=function(rows,lbl){var el=$('#tPearls');if(!el)return;el.innerHTML='<h4>Pearls'+(lbl?' · '+esc(lbl):'')+'</h4>'+(rows.length?rows.map(function(p){return '<div class="mini-pearl">'+mdi(trunc(p.pearl,220))+'</div>'}).join('')+
      '<div style="margin-top:10px"><button class="btn sm" data-go="pearls" data-pmode="quick" data-psystem="'+esc(n.system)+'">'+ic('i-bolt')+'Quick-fire '+esc(n.system)+'</button></div>':'<p class="muted" style="margin:0;font-size:14px">No pearls yet.</p>')};
  if(D.features.pearls)api('/api/redefined/pearls?system='+encodeURIComponent(n.system)+'&subtopic='+encodeURIComponent(n.subtopic)+'&limit=5').then(function(r){
    if((r.pearls||[]).length)pearlBox(r.pearls,'');else api('/api/redefined/pearls?system='+encodeURIComponent(n.system)+'&limit=4&shuffle='+(new Date().getDate()+1)).then(function(r2){pearlBox(r2.pearls||[],n.system)})});
  else{var tp=$('#tPearls');if(tp)tp.remove()}
  api('/api/redefined/related?ref='+encodeURIComponent('theory:'+n.rel)+'&limit=8').then(function(r){var el=$('#tRel');if(!el)return;var it=r.items||[];
    var lbl={guideline:'Guideline',paper:'Paper',theory:'Topic',flashcard_deck:'Deck'};
    el.innerHTML='<h4>Related</h4>'+(it.length?it.map(function(x){return '<button class="rel" data-ref="'+esc(x.ref)+'">'+esc(trunc(x.title,90))+'<small>'+(lbl[x.kind]||x.kind)+' · '+esc(x.reason||'')+'</small></button>'}).join(''):'<p class="muted" style="margin:0;font-size:14px">No linked content yet.</p>')})};
function buildToc(el){var hs=$$('h2,h3',el),toc=$('#toc');if(!toc)return;if(hs.length<3){toc.innerHTML='';return}
  toc.innerHTML='<div class="eyebrow" style="margin-bottom:10px">On this page</div>'+hs.map(function(h,i){h.id='s'+i;return '<a href="#s'+i+'" class="'+h.tagName.toLowerCase()+'" data-toc="s'+i+'">'+esc(trunc(h.textContent.replace(/\*/g,''),60))+'</a>'}).join('');
  $$('a',toc).forEach(function(a){a.onclick=function(e){e.preventDefault();document.getElementById(a.dataset.toc).scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'})}})}
var readT=null;
function onScrollRead(){if(S.view!=='topic'||!S.topic)return;var el=$('#noteBody');if(!el)return;var r=el.getBoundingClientRect(),vh=innerHeight;if(r.height<200)return;
  var p=Math.max(0,Math.min(100,(vh-r.top)/r.height*100));$('#readbar').style.width=p+'%';
  if(p>S.topic.maxP+1){S.topic.maxP=p;var t=$('#pctTxt');if(t)t.textContent=Math.round(p)+'% read';clearTimeout(readT);readT=setTimeout(saveReading,1500)}
  var cur=null;$$('#noteBody h2,#noteBody h3').forEach(function(h){if(h.getBoundingClientRect().top<120)cur=h.id});$$('#toc a').forEach(function(a){a.classList.toggle('on',a.dataset.toc===cur)})}
function saveReading(){if(!S.topic)return;var n=S.topic.note,old=PR.notes[n.id]||{},p=Math.round(S.topic.maxP);if(p<=(old.p||0)&&!(p>=92&&!old.r))return;
  var v={p:Math.max(p,old.p||0)};if(old.r)v.r=old.r;if(p>=92&&!old.r){v.r=today();bump(1);toast('Topic marked as read')}queue('notes',n.id,v)}
window.addEventListener('scroll',function(){$('#topbar').classList.toggle('scrolled',scrollY>4);onScrollRead()},{passive:true});
ACT.markRead=function(b){var n=S.topic.note,old=PR.notes[n.id]||{};if(old.r){queue('notes',n.id,{p:old.p||0});b.classList.remove('saved');b.classList.add('primary');b.innerHTML=ic('i-check')+'Mark as read';return}
  queue('notes',n.id,{p:100,r:today()});S.topic.maxP=100;bump(1);b.classList.add('saved');b.classList.remove('primary');b.innerHTML=ic('i-check')+'Read';toast('Topic marked as read')};
ACT.fs=function(b){var cur=parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--read-fs'))||18,n=Math.max(15,Math.min(23,cur+(+b.dataset.d)));document.documentElement.style.setProperty('--read-fs',n+'px');localStorage.setItem('hc2-fs',n)};
ACT.studyDeck=function(b){startCards([D.decks.find(function(d){return d.id===b.dataset.deck})],'review')};
ACT.topicMcq=function(){startMcq(shuffle(mcqsFor(S.topic.note)).slice(0,20).map(function(q){return q.id}),'tutor')};

/* ---------------- Flashcards ---------------- */
VIEWS.cards=function(){
  var C=S.cards;if(C.session)return C.session.done?cardSummary():cardStudy();
  var due=totalDue(),neu=totalNew();
  var h='<span class="eyebrow">Study</span><h1 class="pt">Flashcards</h1><p class="psub">Spaced repetition: rate each card honestly and it returns just before you would forget it.</p>'+
   '<div class="card banner"><div><span class="eyebrow">Due today</span><div class="big">'+due+'</div></div><div class="muted" style="flex:1;min-width:200px">'+(due?'Cards scheduled for review across all decks.':'All caught up on reviews.')+(neu?' '+neu+' new cards waiting.':'')+'</div>'+
   '<button class="btn primary" data-act="reviewAll"'+(due+neu?'':' disabled')+'>'+ic('i-cards')+(due?'Review '+due+' due':'Learn 20 new cards')+'</button></div><div class="deckgrid">';
  D.decks.forEach(function(d){var st=deckStats(d);
    h+='<div class="card deck">'+(st.due?'<span class="tag acc due-b">'+st.due+' due</span>':'')+pill(d.specialty)+'<h3>'+esc(d.title)+'</h3>'+
     '<div class="stats"><span><b>'+st.total+'</b> cards</span><span><b>'+st.learned+'</b> learned</span><span><b>'+st.mast+'</b> mastered</span></div>'+
     '<div class="bar" title="'+st.mast+' mastered, '+st.learned+' learned"><i class="b1" style="width:'+(st.mast/st.total*100)+'%"></i><i class="b2" style="width:'+((st.learned-st.mast)/st.total*100)+'%"></i></div>'+
     '<div class="btns"><button class="btn primary sm" data-act="studyDeck" data-deck="'+esc(d.id)+'">'+(st.due?'Review '+st.due:'Study')+'</button><button class="btn sm" data-act="browseDeck" data-deck="'+esc(d.id)+'">Browse all</button></div></div>'});
  return h+'</div>'};
function startCards(decks,mode){
  var q=[],newq=[];decks.forEach(function(d){if(!d)return;d.cards.forEach(function(c){var it={deck:d,card:c};if(mode==='browse')q.push(it);else if(isDue(c.id))q.push(it);else if(!cardState(c.id))newq.push(it)})});
  if(mode!=='browse')q=shuffle(q).concat(newq.slice(0,Math.max(0,20-Math.min(q.length,20))));
  if(!q.length){toast('Nothing due right now');return}
  closeReader();S.cards.session={mode:mode,queue:q,i:0,flipped:false,done:false,stats:{1:0,2:0,3:0,4:0},n:0};
  if(S.view==='topic')saveReading();S.view='cards';S.params={};setURL('cards');renderNav();render();window.scrollTo(0,0)}
ACT.reviewAll=function(){startCards(D.decks,'review')};
ACT.browseDeck=function(b){startCards([D.decks.find(function(d){return d.id===b.dataset.deck})],'browse')};
function cardStudy(){var Sx=S.cards.session,it=Sx.queue[Sx.i],c=it.card,d=it.deck,st=cardState(c.id),bm='flashcard:'+c.id,on=!!BM.items[bm];
  var h='<div class="study"><div class="study-head"><button class="btn sm" data-act="endCards">'+ic('i-left')+'Decks</button><div><span class="eyebrow">'+esc(d.specialty)+(Sx.mode==='browse'?' · browse':' · review')+'</span><div class="serif" style="font-size:20px;font-weight:600">'+esc(d.title)+'</div></div>'+
   '<span class="mono muted" style="margin-left:auto">'+(Sx.i+1)+' / '+Sx.queue.length+'</span><button class="save'+(on?' on':'')+'" data-bm="'+esc(bm)+'" data-meta="'+esc(JSON.stringify({kind:'flashcard',title:c.front||d.title,system:d.specialty,type:'Flashcard',locator:{deck:d.id,card:c.id}}))+'" aria-label="Save card">'+ic(on?'i-bmf':'i-bm')+'</button></div>'+
   '<div class="progress" role="progressbar" aria-valuenow="'+Sx.i+'" aria-valuemax="'+Sx.queue.length+'"><i style="width:'+(Sx.i/Sx.queue.length*100)+'%"></i></div>'+
   '<div class="flip'+(Sx.flipped?' on':'')+'" id="flip" role="button" tabindex="0" aria-label="Flip card"><div class="flip-in">'+
   '<div class="card face front"><span class="eyebrow" style="margin-bottom:18px">'+esc(c.subtopic||'Question')+(st||Sx.mode==='browse'?'':' · new')+'</span><div class="q">'+esc(c.front||'Recall the key points')+'</div><span class="hint">tap or press space to reveal</span></div>'+
   '<div class="card face back"><span class="eyebrow" style="margin-bottom:4px">Answer</span><div class="prose">'+md(c.back)+'</div></div></div></div>';
  if(Sx.mode==='browse')h+='<div class="reveal" style="gap:10px"><button class="btn" data-act="cprev"'+(Sx.i?'':' disabled')+'>'+ic('i-left')+'Previous</button><button class="btn primary" data-act="cnext">'+(Sx.i<Sx.queue.length-1?'Next':'Finish')+ic('i-right')+'</button></div>';
  else if(!Sx.flipped)h+='<div class="reveal"><button class="btn primary" data-act="flip" style="min-width:220px">Show answer</button></div>';
  else h+='<div class="rate" role="group" aria-label="How well did you recall it?">'+[[1,'again','Again'],[2,'hard','Hard'],[3,'good','Good'],[4,'easy','Easy']].map(function(r){return '<button class="'+r[1]+'" data-act="rate" data-q="'+r[0]+'">'+r[2]+'<small>'+r[0]+' · '+previewIv(st,r[0])+'</small></button>'}).join('')+'</div>';
  return h+'</div>'}
function cardSummary(){var Sx=S.cards.session,s=Sx.stats,td=totalDue();
  return '<div class="study"><div class="card summary"><span class="eyebrow">Session complete</span><div class="big">'+Sx.n+'</div><div class="muted">cards '+(Sx.mode==='browse'?'browsed':'reviewed')+'</div>'+
   (Sx.mode==='browse'?'':'<div class="kgrid"><div><b style="color:var(--bad)">'+s[1]+'</b><span>Again</span></div><div><b style="color:var(--warn)">'+s[2]+'</b><span>Hard</span></div><div><b style="color:var(--ok)">'+s[3]+'</b><span>Good</span></div><div><b style="color:var(--info)">'+s[4]+'</b><span>Easy</span></div></div>')+
   '<div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-top:18px"><button class="btn" data-act="endCards">Back to decks</button>'+(td?'<button class="btn primary" data-act="reviewAll">Review '+td+' more due</button>':'<button class="btn primary" data-go="mcq">Try some MCQs</button>')+'</div></div></div>'}
AFTER.cards=function(){var f=$('#flip');if(f){f.onclick=function(){ACT.flip()};mathify(f)}};
ACT.flip=function(){var Sx=S.cards.session;if(!Sx||Sx.done)return;if(Sx.mode==='browse'){Sx.flipped=!Sx.flipped;$('#flip').classList.toggle('on',Sx.flipped);return}Sx.flipped=!Sx.flipped;render()};
ACT.rate=function(b){var Sx=S.cards.session,it=Sx.queue[Sx.i],q=typeof b==='number'?b:+b.dataset.q;queue('cards',it.card.id,sm2(cardState(it.card.id),q));Sx.stats[q]++;Sx.n++;bump(1);
  if(q===1&&Sx.queue.filter(function(x){return x.card.id===it.card.id}).length<3)Sx.queue.push(it);
  Sx.i++;Sx.flipped=false;if(Sx.i>=Sx.queue.length)Sx.done=true;render()};
ACT.cnext=function(){var Sx=S.cards.session;Sx.i++;Sx.n++;Sx.flipped=false;if(Sx.i>=Sx.queue.length){Sx.done=true;bump(Sx.n)}render()};
ACT.cprev=function(){var Sx=S.cards.session;if(Sx.i>0){Sx.i--;Sx.n=Math.max(0,Sx.n-1);Sx.flipped=false;render()}};
ACT.endCards=function(){S.cards.session=null;renderNav();render()};

/* ---------------- MCQ ---------------- */
VIEWS.mcq=function(){var M=S.mcq;if(M.run)return M.run.done?mcqResults():mcqQuestion();
  var h='<span class="eyebrow">Study</span><h1 class="pt">MCQ practice</h1><p class="psub">Single-best-answer questions written from your theory topics and guidelines. Tutor mode explains every answer; exam mode is timed and scored at the end.</p>';
  if(!D.mcqs.length)return h+'<div class="card empty"><b>No MCQs have been generated yet.</b><br>'+(D.user.is_admin?'Run <code class="mono">python mcq_generator.py</code> on the server to build them from theory notes and guidelines.':'They will appear here once your editors publish them.')+'</div>';
  var cfg=M.cfg,specs=count(D.mcqs.map(function(q){return {system:q.s}}),'system'),topics=cfg.spec?count(D.mcqs.filter(function(q){return q.s===cfg.spec}).map(function(q){return {t:q.t}}),'t'):{};
  var seen=D.mcqs.filter(function(q){return PR.mcq[q.id]}).length,wrong=D.mcqs.filter(function(q){var p=PR.mcq[q.id];return p&&p.a===0}).length,avail=pickMcqs(cfg,true).length,t=mcqTotals();
  h+='<div class="builder"><div class="card bpanel"><h3>Build a set</h3><p class="muted" style="margin:0">'+avail+' question'+(avail===1?'':'s')+' match these settings.</p>'+
   '<div class="field"><label class="lb" for="mSpec">Specialty</label><select class="sel" id="mSpec" style="width:100%"><option value="">All specialties</option>'+keysBy(specs).map(function(s){return '<option value="'+esc(s)+'"'+(cfg.spec===s?' selected':'')+'>'+esc(s)+' ('+specs[s]+')</option>'}).join('')+'</select></div>'+
   (cfg.spec?'<div class="field"><label class="lb" for="mTopic">Topic</label><select class="sel" id="mTopic" style="width:100%"><option value="">All topics</option>'+keysBy(topics).map(function(s){return '<option value="'+esc(s)+'"'+(cfg.topic===s?' selected':'')+'>'+esc(s)+' ('+topics[s]+')</option>'}).join('')+'</select></div>':'')+
   '<div class="field"><span class="lb" id="lbN">Questions</span><div class="seg" role="group" aria-labelledby="lbN">'+[5,10,20,40].map(function(n){return '<button data-mn="'+n+'" aria-pressed="'+(cfg.n===n)+'">'+n+'</button>'}).join('')+'</div></div>'+
   '<div class="field"><span class="lb" id="lbF">Include</span><div class="chips" role="group" aria-labelledby="lbF">'+[['all','All'],['unseen','Unseen'],['wrong','Previously wrong']].map(function(f){return '<button class="chip" data-mf="'+f[0]+'" aria-pressed="'+(cfg.filter===f[0])+'">'+f[1]+'</button>'}).join('')+'</div></div>'+
   '<div class="field"><span class="lb" id="lbM">Mode</span><div class="seg" role="group" aria-labelledby="lbM"><button data-mm="tutor" aria-pressed="'+(cfg.mode==='tutor')+'">Tutor</button><button data-mm="exam" aria-pressed="'+(cfg.mode==='exam')+'">Exam · 90 s/question</button></div></div>'+
   '<div class="field"><button class="btn primary" data-act="mStart" style="width:100%"'+(avail?'':' disabled')+'>'+ic('i-quiz')+'Start '+Math.min(cfg.n,avail)+' question'+(Math.min(cfg.n,avail)===1?'':'s')+'</button></div></div>'+
   '<div class="card bpanel"><h3>Your record</h3><div class="kgrid" style="grid-template-columns:1fr 1fr;margin:14px 0 0"><div><b>'+seen+'</b><span>Answered</span></div><div><b>'+D.mcqs.length+'</b><span>In bank</span></div><div><b>'+(t.n?Math.round(t.c/t.n*100)+'%':'—')+'</b><span>Accuracy</span></div><div><b style="color:var(--bad)">'+wrong+'</b><span>To revisit</span></div></div></div></div>';
  return h};
AFTER.mcq=function(){var cfg=S.mcq.cfg;
  var s=$('#mSpec');if(s)s.onchange=function(){cfg.spec=s.value;cfg.topic='';render()};
  var t=$('#mTopic');if(t)t.onchange=function(){cfg.topic=t.value;render()};
  $$('[data-mn]').forEach(function(b){b.onclick=function(){cfg.n=+b.dataset.mn;render()}});
  $$('[data-mf]').forEach(function(b){b.onclick=function(){cfg.filter=b.dataset.mf;render()}});
  $$('[data-mm]').forEach(function(b){b.onclick=function(){cfg.mode=b.dataset.mm;render()}});
  if(S.mcq.run&&!S.mcq.run.done)mathify($('.qcard'))};
function pickMcqs(cfg,all){var base=D.mcqs.filter(function(q){return (!cfg.spec||q.s===cfg.spec)&&(!cfg.topic||q.t===cfg.topic)});
  var a=base.filter(function(q){var p=PR.mcq[q.id];if(cfg.filter==='unseen'&&p)return false;if(cfg.filter==='wrong'&&!(p&&p.a===0))return false;return true});
  if(!a.length&&cfg.filter==='unseen'&&!all)a=base;
  return all?a:shuffle(a).slice(0,cfg.n).map(function(q){return q.id})}
ACT.mStart=function(){startMcq(pickMcqs(S.mcq.cfg),S.mcq.cfg.mode)};
function startMcq(ids,mode){if(!ids.length){toast('No questions match');return}mode=mode||'tutor';
  api('/api/redefined/mcqs?ids='+encodeURIComponent(ids.join(','))).then(function(r){var qs=(r.questions||[]).map(function(q){return Object.assign({},q,{shown:shuffle(q.options||[])})});
    if(!qs.length){toast('Could not load questions');return}
    closeReader();S.mcq.run={mode:mode,qs:qs,i:0,ans:{},flag:{},done:false,start:Date.now(),limit:mode==='exam'?qs.length*90:0};
    if(S.view==='topic')saveReading();S.view='mcq';S.params={};setURL('mcq');renderNav();render();window.scrollTo(0,0);tick()})}
function tick(){clearInterval(tick._t);var R=S.mcq.run;if(!R||R.mode!=='exam')return;tick._t=setInterval(function(){var R2=S.mcq.run;if(!R2||R2.done){clearInterval(tick._t);return}
  var left=R2.limit-Math.floor((Date.now()-R2.start)/1000),el=$('#timer');if(el){el.textContent=fmtT(left);el.style.color=left<60?'var(--bad)':''}if(left<=0){clearInterval(tick._t);finishMcq()}},1000)}
function fmtT(s){s=Math.max(0,s);return Math.floor(s/60)+':'+('0'+s%60).slice(-2)}
function mcqQuestion(){var R=S.mcq.run,q=R.qs[R.i],a=R.ans[q.id],tutor=R.mode==='tutor',revealed=tutor&&a!=null,L='ABCDE';
  var h='<div class="qwrap"><div class="qhead"><button class="btn sm" data-act="mQuit">'+ic('i-x')+'End</button><span class="eyebrow">Question '+(R.i+1)+' of '+R.qs.length+' · '+(tutor?'tutor':'exam')+'</span>'+
   (R.mode==='exam'?'<span class="timer" id="timer" aria-label="Time left">'+fmtT(R.limit-Math.floor((Date.now()-R.start)/1000))+'</span>':'<span class="timer muted">'+Object.keys(R.ans).length+' answered</span>')+'</div>'+
   '<div class="progress"><i style="width:'+((R.i+1)/R.qs.length*100)+'%"></i></div>'+
   '<div class="card qcard"><div style="display:flex;gap:8px;flex-wrap:wrap">'+pill(q.system,trunc(q.subtopic,30))+'<span class="tag '+({easy:'ok',medium:'warn',hard:'bad'}[q.difficulty]||'neu')+'">'+esc(q.difficulty||'')+'</span>'+(q.status==='draft'?'<span class="tag neu" title="Generated, awaiting editor review">draft</span>':'')+'</div>'+
   '<div class="stem">'+mdi(q.stem)+'</div><div class="opts" role="radiogroup" aria-label="Answer options">';
  q.shown.forEach(function(o,i){var cls='',fb='';
    if(revealed){if(o.key===q.answer){cls=' right';fb='<span class="fb" style="color:var(--ok)">CORRECT</span>'}else if(o.key===a){cls=' wrong';fb='<span class="fb" style="color:var(--bad)">YOUR PICK</span>'}}else if(o.key===a)cls=' sel';
    h+='<button class="opt'+cls+'" data-act="mPick" data-k="'+esc(o.key)+'" role="radio" aria-checked="'+(o.key===a)+'"'+(revealed?' disabled':'')+'><span class="k">'+L[i]+'</span><span>'+mdi(o.text)+'</span>'+fb+'</button>'});
  h+='</div>';
  if(revealed){var ok=a===q.answer,n=noteFromSrc(q),ci=q.shown.findIndex(function(o){return o.key===q.answer});
    h+='<div class="explain '+(ok?'ok':'bad')+'" aria-live="polite"><div class="verdict">'+ic(ok?'i-check':'i-x')+(ok?'Correct':'Not quite — the answer is '+L[ci])+'</div><p>'+mdi(q.explanation)+'</p>'+
    (n?'<div style="margin-top:12px"><button class="btn sm" data-go="topic" data-pid="'+esc(n.id)+'">'+ic('i-book')+'Read: '+esc(trunc(n.title,50))+'</button></div>':'')+'</div>'}
  h+='</div><div class="qnav"><button class="btn" data-act="mPrev"'+(R.i?'':' disabled')+'>'+ic('i-left')+'Back</button>'+
   (R.mode==='exam'?'<button class="btn'+(R.flag[q.id]?' saved':'')+'" data-act="mFlag" aria-pressed="'+!!R.flag[q.id]+'">'+ic('i-flag')+(R.flag[q.id]?'Flagged':'Flag')+'</button>':'')+
   '<div class="right">'+(R.i<R.qs.length-1?'<button class="btn primary" data-act="mNext"'+(tutor&&a==null?' disabled':'')+'>Next'+ic('i-right')+'</button>':'<button class="btn primary" data-act="mFinish"'+(tutor&&a==null?' disabled':'')+'>Finish'+ic('i-check')+'</button>')+'</div></div>';
  if(R.mode==='exam')h+='<div class="qdots" aria-label="Jump to question">'+R.qs.map(function(x,i){return '<button data-act="mJump" data-i="'+i+'" class="'+(i===R.i?'cur ':'')+(R.ans[x.id]!=null?'ans ':'')+(R.flag[x.id]?'flag':'')+'" aria-label="Question '+(i+1)+'">'+(i+1)+'</button>'}).join('')+'</div>';
  return h+'<p class="muted" style="font-size:13px;margin-top:16px">Keys: A–E or 1–5 to answer · Enter for next</p></div>'}
function noteFromSrc(q){var s=q.source||{};if(s.kind!=='theory')return null;return D.notes.find(function(n){return n.rel===s.ref})}
ACT.mPick=function(b){var R=S.mcq.run,q=R.qs[R.i];if(R.mode==='tutor'&&R.ans[q.id]!=null)return;R.ans[q.id]=b.dataset.k;if(R.mode==='tutor')record(q,b.dataset.k);render()};
function record(q,k){var p=PR.mcq[q.id]||{n:0,c:0},ok=k===q.answer;queue('mcq',q.id,{n:(p.n||0)+1,c:(p.c||0)+(ok?1:0),a:ok?1:0,t:today()});bump(1)}
ACT.mNext=function(){var R=S.mcq.run;if(R.i<R.qs.length-1){R.i++;render();window.scrollTo(0,0)}};
ACT.mPrev=function(){var R=S.mcq.run;if(R.i>0){R.i--;render()}};
ACT.mJump=function(b){S.mcq.run.i=+b.dataset.i;render()};
ACT.mFlag=function(){var R=S.mcq.run,q=R.qs[R.i];R.flag[q.id]=!R.flag[q.id];render()};
ACT.mFinish=function(){var R=S.mcq.run,un=R.qs.filter(function(q){return R.ans[q.id]==null}).length;
  if(R.mode==='exam'&&un)modal('<h3 style="margin-top:0">Submit with '+un+' unanswered?</h3><p>Unanswered questions count as incorrect.</p>',[['Keep going',''],['Submit',finishMcq]]);else finishMcq()};
ACT.mQuit=function(){var R=S.mcq.run;if(Object.keys(R.ans).length&&!R.done){modal('<h3 style="margin-top:0">End this set?</h3><p>'+(R.mode==='tutor'?'Answers so far are already saved to your record.':'Your answers will be scored now.')+'</p>',[['Cancel',''],['End set',finishMcq]])}else{clearInterval(tick._t);S.mcq.run=null;render()}};
function finishMcq(){var R=S.mcq.run;if(!R||R.done)return;clearInterval(tick._t);if(R.mode==='exam')R.qs.forEach(function(q){if(R.ans[q.id]!=null)record(q,R.ans[q.id])});R.done=true;R.secs=Math.floor((Date.now()-R.start)/1000);render();window.scrollTo(0,0)}
function mcqResults(){var R=S.mcq.run,ok=R.qs.filter(function(q){return R.ans[q.id]===q.answer}).length,pct=Math.round(ok/R.qs.length*100),by={};
  R.qs.forEach(function(q){var k=q.subtopic;by[k]=by[k]||{n:0,c:0};by[k].n++;if(R.ans[q.id]===q.answer)by[k].c++});
  return '<div class="qwrap"><span class="eyebrow">Set complete</span><h1 class="pt">'+(pct>=80?'Excellent work':pct>=60?'Solid effort':'Worth another pass')+'</h1>'+
   '<div class="card score"><div class="donut" style="--p:'+pct+'" role="img" aria-label="'+pct+' percent correct"><div><span><b>'+pct+'%</b><small>'+ok+' / '+R.qs.length+'</small></span></div></div><div style="width:100%"><div class="topicbars">'+
   Object.keys(by).map(function(k){var v=by[k];return '<div><span>'+esc(trunc(k,28))+'</span><span class="bar"><i style="width:'+(v.c/v.n*100)+'%;background:'+(v.c/v.n>=.6?'var(--ok)':'var(--bad)')+'"></i></span><span class="mono muted">'+v.c+'/'+v.n+'</span></div>'}).join('')+
   '</div><p class="muted" style="margin:16px 0 0;font-size:14px">'+fmtT(R.secs)+' total · '+R.mode+' mode</p></div></div>'+
   '<div style="display:flex;gap:10px;margin:18px 0;flex-wrap:wrap"><button class="btn" data-act="mNew">New set</button>'+(ok<R.qs.length?'<button class="btn primary" data-act="mRetry">'+ic('i-shuffle')+'Retry the '+(R.qs.length-ok)+' missed</button>':'')+'</div><h2 class="sec">Review answers</h2><div class="card list">'+
   R.qs.map(function(q,i){var a=R.ans[q.id],good=a===q.answer,ans=(q.options||[]).find(function(o){return o.key===q.answer});
     return '<details class="qrev"><summary><span class="tag '+(good?'ok':'bad')+'">'+(i+1)+'</span><span style="flex:1">'+mdi(trunc(q.stem,170))+'</span>'+ic('i-right','color:var(--muted)')+'</summary>'+
      '<div style="margin:10px 0 0 40px"><p style="margin:0 0 6px"><b>Answer:</b> '+mdi(ans?ans.text:q.answer)+'</p><p class="serif" style="margin:0;color:var(--ink-2);line-height:1.6">'+mdi(q.explanation)+'</p></div></details>'}).join('')+'</div></div>'}
ACT.mNew=function(){S.mcq.run=null;render()};
ACT.mRetry=function(){var R=S.mcq.run;startMcq(R.qs.filter(function(q){return R.ans[q.id]!==q.answer}).map(function(q){return q.id}),'tutor')};

/* ---------------- Pearls ---------------- */
VIEWS.pearls=function(){var P=S.pearls;if(S.params&&Object.keys(S.params).length){if(S.params.mode)P.mode=S.params.mode==='quick'?'quick':'grid';if(S.params.system!=null){P.system=S.params.system;P.subtopic='';P.items=[];P.qf=null}S.params={}}
  var tops=D.pearl_topics||{},sys={};Object.keys(tops).forEach(function(s){sys[s]=Object.keys(tops[s]).reduce(function(a,k){return a+tops[s][k]},0)});
  var h='<span class="eyebrow">Study</span><h1 class="pt">Clinical pearls</h1><p class="psub">'+Number(D.pearl_count).toLocaleString()+' one-line takeaways. Quick-fire them like flashcards, or browse with recall mode.</p>'+
   '<div class="toolbar"><div class="seg" role="group" aria-label="Mode"><button data-pm="quick" aria-pressed="'+(P.mode==='quick')+'">Quick-fire</button><button data-pm="grid" aria-pressed="'+(P.mode==='grid')+'">Browse</button></div>'+
   '<select class="sel" id="pSys" aria-label="Specialty"><option value="">All specialties</option>'+keysBy(sys).map(function(s){return '<option value="'+esc(s)+'"'+(P.system===s?' selected':'')+'>'+esc(s)+' ('+sys[s]+')</option>'}).join('')+'</select>'+
   (P.system?'<select class="sel" id="pSub" aria-label="Subtopic"><option value="">All subtopics</option>'+keysBy(tops[P.system]||{}).map(function(s){return '<option value="'+esc(s)+'"'+(P.subtopic===s?' selected':'')+'>'+esc(trunc(s,40))+' ('+tops[P.system][s]+')</option>'}).join('')+'</select>':'')+
   (P.mode==='grid'?'<label class="input">'+ic('i-search')+'<input id="pQ" placeholder="Search pearls" value="'+esc(P.q)+'" aria-label="Search pearls"></label><button class="btn'+(P.recall?' saved':'')+'" id="pRecall" aria-pressed="'+P.recall+'">'+ic('i-eye')+'Recall mode</button>':'')+'</div>';
  if(P.mode==='quick')return h+'<div id="qf" class="qf"><div class="card empty">Loading…</div></div>';
  return h+'<p class="count-line" id="pCount"></p><div class="pearls'+(P.recall?' recall':'')+'" id="pGrid"></div><div style="display:flex;justify-content:center;padding:16px" id="pMore"></div>'};
AFTER.pearls=function(){var P=S.pearls,t=null;
  $$('[data-pm]').forEach(function(b){b.onclick=function(){P.mode=b.dataset.pm;render()}});
  $('#pSys').onchange=function(e){P.system=e.target.value;P.subtopic='';P.items=[];P.qf=null;render()};
  var sub=$('#pSub');if(sub)sub.onchange=function(e){P.subtopic=e.target.value;P.items=[];P.qf=null;render()};
  if(P.mode==='quick'){qfLoad();return}
  $('#pQ').addEventListener('input',function(e){clearTimeout(t);t=setTimeout(function(){P.q=e.target.value;loadPearls(true)},220)});
  $('#pRecall').onclick=function(){P.recall=!P.recall;render()};
  $('#pGrid').addEventListener('click',function(e){var p=e.target.closest('.pearl');if(p&&P.recall&&!e.target.closest('.save'))p.classList.toggle('revealed')});
  if(P.items.length)drawPearls();else loadPearls(true)};
function pq(extra){var P=S.pearls;return '/api/redefined/pearls?q='+encodeURIComponent(P.q)+'&system='+encodeURIComponent(P.system)+'&subtopic='+encodeURIComponent(P.subtopic)+(extra||'')}
function loadPearls(reset){var P=S.pearls;if(reset){P.page=1;P.items=[]}api(pq('&limit=36&page='+P.page)).then(function(r){P.items=P.items.concat(r.pearls||[]);P.total=r.total||0;P.pages=r.pages||1;drawPearls()})}
function pearlSave(p){var ref='pearl:'+p.id,on=!!BM.items[ref];return '<button class="save'+(on?' on':'')+'" data-bm="'+esc(ref)+'" data-meta="'+esc(JSON.stringify({kind:'pearl',title:trunc(p.pearl,120),system:p.system||'',type:p.type||''}))+'" aria-label="Save pearl">'+ic(on?'i-bmf':'i-bm')+'</button>'}
function drawPearls(){var P=S.pearls;if(!$('#pGrid'))return;$('#pCount').textContent=P.total.toLocaleString()+' pearls';
  $('#pGrid').innerHTML=P.items.length?P.items.map(function(p){return '<article class="card pearl" style="--c:'+color(p.system)+'"><p>'+mdi(p.pearl)+'</p><div class="src"><span>'+pill(p.system)+'<span style="display:block;margin-top:8px">'+esc(trunc(p.source_paper,110))+'</span></span>'+pearlSave(p)+'</div></article>'}).join(''):'<div class="card empty">No pearls match.</div>';
  $('#pMore').innerHTML=P.page<P.pages?'<button class="btn" id="pMoreBtn">Load more pearls</button>':'';var m=$('#pMoreBtn');if(m)m.onclick=function(){P.page++;loadPearls(false)}}
function qfLoad(){var P=S.pearls;if(P.qf&&P.qf.items.length){qfDraw();return}
  api(pq('&limit=30&shuffle='+(1+Math.random()*1e6|0))).then(function(r){P.qf={items:r.pearls||[],i:0,knew:0,again:0};qfDraw()})}
function qfDraw(){var Q=S.pearls.qf,el=$('#qf');if(!el||!Q)return;if(!Q.items.length){el.innerHTML='<div class="card empty">No pearls match.</div>';return}
  if(Q.i>=Q.items.length){el.innerHTML='<div class="card summary"><span class="eyebrow">Round complete</span><div class="big">'+Q.knew+'</div><div class="muted">pearls you already knew · '+Q.again+' to revisit</div><div style="margin-top:18px"><button class="btn primary" data-act="qfAgain">'+ic('i-shuffle')+'Another round</button></div></div>';return}
  var p=Q.items[Q.i];
  el.innerHTML='<div class="progress"><i style="width:'+(Q.i/Q.items.length*100)+'%"></i></div><div class="card"><div style="display:flex;align-items:center;gap:8px">'+pill(p.system,p.subtopic&&p.subtopic!==p.system?trunc(p.subtopic,30):'')+'<span class="mono muted" style="margin-left:auto;font-size:13px">'+(Q.i+1)+' / '+Q.items.length+'</span>'+pearlSave(p)+'</div>'+
   '<blockquote>'+mdi(p.pearl)+'</blockquote><div class="muted" style="font-size:13.5px">'+esc(trunc(p.source_paper,140))+'</div></div>'+
   '<div class="actions2"><button class="btn" data-act="qfNo" style="color:var(--bad)">'+ic('i-x')+'Didn’t know</button><button class="btn primary" data-act="qfYes">'+ic('i-check')+'Knew it</button></div><p class="muted" style="text-align:center;font-size:13px">Keys: ← didn’t know · → knew it</p>'}
ACT.qfYes=function(){var Q=S.pearls.qf;Q.knew++;Q.i++;bump(1);qfDraw()};
ACT.qfNo=function(){var Q=S.pearls.qf;Q.again++;Q.items.push(Q.items[Q.i]);Q.i++;bump(1);qfDraw()};
ACT.qfAgain=function(){S.pearls.qf=null;qfLoad()};

/* ---------------- Guidelines ---------------- */
function guidelineRow(a){return '<button class="row" style="--c:'+color(a.system)+'" data-guideline="'+esc(a.id)+'"><span class="stripe"></span><span><div class="t serif">'+esc(a.title)+'</div><div class="m"><span>'+esc(a.system)+(a.subtopic&&a.subtopic!==a.system?' › '+esc(a.subtopic):'')+'</span>'+(a.year?'<span>'+esc(a.year)+'</span>':'')+'</div></span><span class="r">'+(BM.items['guideline:'+a.file_name]?ic('i-bmf','color:var(--accent)'):'')+ic('i-right','color:var(--muted)')+'</span></button>'}
VIEWS.guidelines=function(){var G=S.gl,all=D.articles.filter(isGuideline),specs=count(all,'system');
  return '<span class="eyebrow">Reference</span><h1 class="pt">Guidelines</h1><p class="psub">Society and consensus guidelines distilled into recommendation cards you can scan at the bedside.</p>'+
   '<div class="toolbar"><label class="input">'+ic('i-search')+'<input id="gQ" placeholder="Search guidelines" value="'+esc(G.q)+'" aria-label="Search guidelines"></label></div>'+
   '<div class="chips" style="margin-bottom:22px"><button class="chip" data-gs="" aria-pressed="'+(!G.spec)+'">All · '+all.length+'</button>'+keysBy(specs).map(function(s){return '<button class="chip" data-gs="'+esc(s)+'" aria-pressed="'+(G.spec===s)+'"><span class="dot" style="--c:'+color(s)+'"></span>'+esc(s)+' · '+specs[s]+'</button>'}).join('')+'</div><div id="gList"></div>'};
AFTER.guidelines=function(){$$('[data-gs]').forEach(function(b){b.onclick=function(){S.gl.spec=b.dataset.gs;render()}});$('#gQ').addEventListener('input',function(e){S.gl.q=e.target.value;gList()});gList()};
function gList(){var G=S.gl,q=norm(G.q),rows=D.articles.filter(isGuideline).filter(function(a){return (!G.spec||a.system===G.spec)&&(!q||q.split(' ').every(function(w){return norm(a.title+' '+a.subtopic+' '+a.journal).indexOf(w)>-1}))});
  var by={};rows.forEach(function(a){(by[a.system]=by[a.system]||[]).push(a)});
  $('#gList').innerHTML=rows.length?keysBy(count(rows,'system')).map(function(s){return '<section class="gl-spec"><h3><span class="dot" style="--c:'+color(s)+'"></span>'+esc(s)+' <span class="mono muted" style="font-size:12px">'+by[s].length+'</span></h3><div class="card list">'+by[s].sort(function(a,b){return (b.year||'').localeCompare(a.year||'')}).map(guidelineRow).join('')+'</div></section>'}).join(''):'<div class="card empty">No guidelines match.</div>'}
function strengthTag(s){return /strong|^1|high|recommend(ed)? for/i.test(s)?'ok':/weak|cond|^2|low|suggest/i.test(s)?'warn':'neu'}
function openGuideline(a){if(!a)return;var ref='guideline:'+a.file_name;
  var top=bmBtn(ref,{kind:'guideline',title:a.title,system:a.system,type:a.type,locator:{file_name:a.file_name,system:a.system,type:a.type}})+(a.doi?'<a class="btn sm" href="'+esc(a.doi)+'" target="_blank" rel="noopener">'+ic('i-ext')+'Source</a>':'')+
   '<a class="btn sm" href="/export/print?kind=paper&file_name='+encodeURIComponent(a.file_name)+'&title='+encodeURIComponent(a.title)+'" target="_blank" rel="noopener">'+ic('i-print')+'Print</a>';
  var head=pill(a.system,a.subtopic!==a.system?a.subtopic:'')+' <span class="tag acc">Guideline</span><h1 class="rt">'+esc(a.title)+'</h1>';
  openReader(top,head+'<div class="empty">Loading…</div>');
  api('/api/redefined/guideline?file_name='+encodeURIComponent(a.file_name)+'&system='+encodeURIComponent(a.system)+'&type='+encodeURIComponent(a.type)).then(function(d){
    if(d.error||d.detail){$('#readerBody').innerHTML=head+'<div class="card empty">'+esc(d.error||d.detail)+'</div>';return}
    var meta=[];if(d.issuing_bodies&&d.issuing_bodies.length)meta.push(d.issuing_bodies.join(', '));if(d.year||a.year)meta.push(d.year||a.year);if(d.consensus_method)meta.push(trunc(d.consensus_method,60));
    var h=head+'<div class="rmeta">'+meta.map(function(m){return '<span>'+esc(m)+'</span>'}).join('')+'</div>';
    if(d.one_line_summary){var ol=String(d.one_line_summary).trim();if(/^- /.test(ol))ol=ol.replace(/ - /g,'\n- ');h+='<div class="callout"><span class="eyebrow">Bottom line</span><div class="prose" style="font-size:17px;line-height:1.55">'+md(ol)+'</div></div>'}
    var kp=(d.key_pearls||[]).filter(Boolean);if(kp.length)h+='<div class="callout" style="background:var(--surface-2);border-color:var(--line)"><span class="eyebrow" style="color:var(--muted)">Key pearls</span><ul>'+kp.slice(0,6).map(function(p){return '<li>'+mdi(p)+'</li>'}).join('')+'</ul></div>';
    var blocks=d.recommendation_blocks||[];
    if(blocks.length){h+='<h2 style="font-size:19px;margin:26px 0 12px">Recommendations <span class="mono muted" style="font-size:13px;font-weight:400">'+blocks.length+' sections</span></h2>';
      blocks.forEach(function(b,i){h+='<section class="card rec-block"><h3><span class="n">'+('0'+(i+1)).slice(-2)+'</span>'+esc(b.topic||'Section')+'</h3>'+(b.narrative?'<p class="nar">'+mdi(trunc(b.narrative,600))+'</p>':'')+
        (b.recommendations||[]).map(function(r){var bd=[];if(r.strength)bd.push('<span class="tag '+strengthTag(r.strength)+'">'+esc(r.strength)+'</span>');if(r.evidence_grade)bd.push('<span class="tag info">'+esc(r.evidence_grade)+'</span>');
          return '<div class="rec"><span class="tick">'+ic('i-check')+'</span><div class="st">'+mdi(r.statement)+(bd.length?'<div class="bd">'+bd.join('')+'</div>':'')+'</div></div>'}).join('')+'</section>'})}
    var bp=d.bedside_protocol;if(bp&&((Array.isArray(bp)&&bp.length)||(!Array.isArray(bp)&&typeof bp==='object'&&Object.keys(bp).length)||typeof bp==='string'))h+='<h2 style="font-size:19px;margin:26px 0 12px">Bedside protocol</h2><div class="prose">'+renderAny(bp)+'</div>';
    h+='<details class="full"><summary>Full structured summary</summary><div class="prose" style="padding-bottom:16px">'+md(d.markdown)+'</div></details>';
    $('#readerBody').innerHTML=h;mathify($('#readerBody'))})}

/* ---------------- Saved ---------------- */
VIEWS.saved=function(){var items=Object.keys(BM.items||{}).map(function(k){return BM.items[k]}).sort(function(a,b){return (b.added_at||'').localeCompare(a.added_at||'')});
  var label={note:'Theory topics',flashcard:'Flashcards',pearl:'Pearls',guideline:'Guidelines',paper:'Papers',trial:'Trials',condensed:'Condensed trials'};
  var h='<span class="eyebrow">Your library</span><h1 class="pt">Saved</h1><p class="psub">Everything you bookmarked, synced to your account.</p>';
  if(!items.length)return h+'<div class="card empty">Nothing saved yet. Use the bookmark button on any topic, card, pearl or guideline.</div>';
  Object.keys(label).forEach(function(k){var g=items.filter(function(i){return i.kind===k});if(!g.length)return;
    h+='<h2 class="sec">'+label[k]+' <span class="mono muted" style="font-size:13px">'+g.length+'</span></h2><div class="card list">'+g.map(function(i){return '<button class="row" style="--c:'+color(i.system)+'" data-ref="'+esc(i.ref)+'"><span class="stripe"></span><span><div class="t">'+esc(i.title)+'</div><div class="m"><span>'+esc(i.system||'')+'</span></div></span><span class="r">'+ic('i-right','color:var(--muted)')+'</span></button>'}).join('')+'</div>'});
  return h};

/* ---------------- Evidence: papers + trials (secondary) ---------------- */
function articleRow(a){return '<button class="row" style="--c:'+color(a.system)+'" data-article="'+esc(a.id)+'"><span class="stripe"></span><span><div class="t serif">'+esc(a.title)+'</div><div class="m"><span>'+esc(a.system)+(a.subtopic&&a.subtopic!==a.system?' › '+esc(a.subtopic):'')+'</span><span>'+esc(trunc(a.journal,46))+'</span>'+(a.year?'<span>'+esc(a.year)+'</span>':'')+'</div></span><span class="r"><span class="pill">'+esc(a.type)+'</span></span></button>'}
VIEWS.papers=function(){var L=S.lib,base=D.articles.filter(isPaper),specs=count(base,'system'),types=count(base,'type');
  return '<span class="eyebrow">Evidence</span><h1 class="pt">Papers</h1><p class="psub">Reviews, RCTs and meta-analyses behind the topics — for when you want the primary source.</p>'+
   '<div class="toolbar"><label class="input">'+ic('i-search')+'<input id="lQ" placeholder="Title, journal, author or subtopic" value="'+esc(L.q)+'" aria-label="Filter papers"></label>'+
   '<select class="sel" id="lSpec" aria-label="Specialty"><option value="">All specialties</option>'+keysBy(specs).map(function(s){return '<option value="'+esc(s)+'"'+(L.spec===s?' selected':'')+'>'+esc(s)+' ('+specs[s]+')</option>'}).join('')+'</select>'+
   '<select class="sel" id="lType" aria-label="Study type"><option value="">All types</option>'+keysBy(types).map(function(s){return '<option value="'+esc(s)+'"'+(L.type===s?' selected':'')+'>'+esc(s)+' ('+types[s]+')</option>'}).join('')+'</select>'+
   '<select class="sel" id="lSort" aria-label="Sort"><option value="new">Newest</option><option value="az">A–Z</option><option value="year">Year</option></select></div><div id="lList"></div>'};
AFTER.papers=function(){var L=S.lib;$('#lSort').value=L.sort;
  $('#lQ').addEventListener('input',function(e){L.q=e.target.value;L.limit=40;lList()});
  [['lSpec','spec'],['lType','type'],['lSort','sort']].forEach(function(x){$('#'+x[0]).onchange=function(e){L[x[1]]=e.target.value;L.limit=40;lList()}});lList()};
function lList(){var L=S.lib,q=norm(L.q),rows=D.articles.filter(isPaper).filter(function(a){return (!L.spec||a.system===L.spec)&&(!L.type||a.type===L.type)&&(!q||q.split(' ').every(function(w){return norm(a.title+' '+a.journal+' '+a.authors+' '+a.subtopic).indexOf(w)>-1}))});
  rows.sort(L.sort==='az'?function(a,b){return a.title.localeCompare(b.title)}:L.sort==='year'?function(a,b){return (b.year||'').localeCompare(a.year||'')}:function(a,b){return (b.date_added||'').localeCompare(a.date_added||'')});
  $('#lList').innerHTML='<p class="count-line">'+rows.length+' papers</p>'+(rows.length?'<div class="card list">'+rows.slice(0,L.limit).map(articleRow).join('')+'</div>':'<div class="card empty">Nothing matches.</div>')+(rows.length>L.limit?'<div style="display:flex;justify-content:center;padding:16px"><button class="btn" id="lMore">Show more</button></div>':'');
  var m=$('#lMore');if(m)m.onclick=function(){L.limit+=40;lList()}}
VIEWS.trials=function(){var T=S.trials,hasC=D.features.condensed_trials&&D.condensed.length,cond=T.src==='condensed'&&hasC,src=cond?D.condensed:D.trials,specs=count(src,cond?'system':'specialty'),res=count(src,'result_category');
  return '<span class="eyebrow">Evidence</span><h1 class="pt">Landmark trials</h1><p class="psub">The trials that shaped ICU practice — design, result and the one line to remember.</p>'+
   '<div class="toolbar">'+(hasC?'<div class="seg" role="group" aria-label="Collection"><button data-ts="esbicm" aria-pressed="'+(!cond)+'">ESBICM · '+D.trials.length+'</button><button data-ts="condensed" aria-pressed="'+(!!cond)+'">Condensed · '+D.condensed.length+'</button></div>':'')+
   '<label class="input">'+ic('i-search')+'<input id="trQ" placeholder="Trial name or keyword" value="'+esc(T.q)+'" aria-label="Filter trials"></label>'+
   '<select class="sel" id="trSpec" aria-label="Area"><option value="">All areas</option>'+keysBy(specs).map(function(s){return '<option value="'+esc(s)+'"'+(T.spec===s?' selected':'')+'>'+esc(s)+'</option>'}).join('')+'</select>'+
   '<select class="sel" id="trRes" aria-label="Result"><option value="">All results</option>'+keysBy(res).map(function(s){return '<option value="'+esc(s)+'"'+(T.res===s?' selected':'')+'>'+esc(s)+' ('+res[s]+')</option>'}).join('')+'</select></div><div id="trList"></div>'};
AFTER.trials=function(){var T=S.trials;$$('[data-ts]').forEach(function(b){b.onclick=function(){T.src=b.dataset.ts;T.spec='';T.res='';render()}});
  $('#trQ').addEventListener('input',function(e){T.q=e.target.value;T.limit=40;trList()});$('#trSpec').onchange=function(e){T.spec=e.target.value;trList()};$('#trRes').onchange=function(e){T.res=e.target.value;trList()};trList()};
function trList(){var T=S.trials,cond=T.src==='condensed'&&D.condensed.length,q=norm(T.q),src=(cond?D.condensed:D.trials).filter(function(t){var sp=cond?t.system:t.specialty;return (!T.spec||sp===T.spec)&&(!T.res||t.result_category===T.res)&&(!q||norm(t.trial_name+' '+(t.one_liner||'')+' '+(t.keywords_str||'')).indexOf(q)>-1)}).sort(function(a,b){return (b.year||0)-(a.year||0)});
  $('#trList').innerHTML='<p class="count-line">'+src.length+' trials</p>'+(src.length?'<div class="card list">'+src.slice(0,T.limit).map(function(t){var sp=cond?t.system:t.specialty,attr=cond?'data-cond="'+esc(t.system)+'|'+esc(t.name)+'"':'data-trial="'+esc(t.slug)+'"';
    return '<button class="row" style="--c:'+color(sp)+'" '+attr+'><span class="stripe"></span><span><div class="t">'+esc(t.trial_name)+'</div>'+(t.one_liner?'<div class="one">'+esc(t.one_liner)+'</div>':'')+'<div class="m"><span>'+esc(sp)+'</span>'+(t.sample_size?'<span>n = '+Number(t.sample_size).toLocaleString()+'</span>':'')+(t.year?'<span>'+t.year+'</span>':'')+'</div></span><span class="r"><span class="tag '+resTag(t.result_category)+'">'+esc(t.result_category||'—')+'</span></span></button>'}).join('')+'</div>':'<div class="card empty">No trials match.</div>')+
   (src.length>T.limit?'<div style="display:flex;justify-content:center;padding:16px"><button class="btn" id="trMore">Show more</button></div>':'');var m=$('#trMore');if(m)m.onclick=function(){T.limit+=40;trList()}}

/* ---------------- Reader (slide-over for guidelines/papers/trials) ---------------- */
function openReader(top,body){$('#readerTop').innerHTML=top+'<button class="icon-btn" data-act="closeReader" aria-label="Close" style="margin-left:auto">'+ic('i-x')+'</button>';
  $('#readerBody').innerHTML=body;$('#readerBody').scrollTop=0;$('#reader').classList.add('on');$('#scrim').classList.add('on');setTimeout(function(){var b=$('#readerTop [data-act=closeReader]');if(b)b.focus()},50)}
function closeReader(){$('#reader').classList.remove('on');if(!$('#palette').classList.contains('on'))$('#scrim').classList.remove('on')}
$('#scrim').onclick=function(){closeReader();closePalette()};
function bmBtn(ref,meta){var on=!!BM.items[ref];return '<button class="btn sm'+(on?' saved':'')+'" data-bm="'+esc(ref)+'" data-meta="'+esc(JSON.stringify(meta))+'">'+ic(on?'i-bmf':'i-bm')+(on?'Saved':'Save')+'</button>'}
function renderAny(v){if(v==null||v==='')return '';if(typeof v==='string')return md(v);if(Array.isArray(v))return '<ul>'+v.map(function(x){return '<li>'+(typeof x==='object'?renderAny(x):mdi(x))+'</li>'}).join('')+'</ul>';
  if(typeof v==='object')return Object.keys(v).map(function(k){var x=v[k];if(x==null||x===''||(Array.isArray(x)&&!x.length))return '';return '<h4>'+esc(k.replace(/_/g,' '))+'</h4>'+renderAny(x)}).join('');return '<p>'+esc(v)+'</p>'}
function setReaderTop(btns){$('#readerTop').innerHTML=btns+'<button class="icon-btn" data-act="closeReader" aria-label="Close" style="margin-left:auto">'+ic('i-x')+'</button>'}
function openArticle(a){if(!a)return;if(isGuideline(a)){openGuideline(a);return}var ref='paper:'+a.file_name;
  var top=bmBtn(ref,{kind:'paper',title:a.title,system:a.system,type:a.type,locator:{file_name:a.file_name,system:a.system,type:a.type}})+(a.doi?'<a class="btn sm" href="'+esc(a.doi)+'" target="_blank" rel="noopener">'+ic('i-ext')+'Source</a>':'')+'<a class="btn sm" href="/export/print?kind=paper&file_name='+encodeURIComponent(a.file_name)+'&title='+encodeURIComponent(a.title)+'" target="_blank" rel="noopener">'+ic('i-print')+'Print</a>';
  var head=pill(a.system,a.subtopic!==a.system?a.subtopic:'')+' <span class="tag neu">'+esc(a.type)+'</span><h1 class="rt">'+esc(a.title)+'</h1><div class="rmeta"><span>'+esc(a.journal)+'</span>'+(a.year?'<span>'+esc(a.year)+'</span>':'')+'<span>'+esc(a.authors)+'</span></div>';
  openReader(top,head+'<div class="empty">Loading…</div>');
  api('/api/summary?file_name='+encodeURIComponent(a.file_name)+'&system='+encodeURIComponent(a.system)+'&type='+encodeURIComponent(a.type)).then(function(d){if(d.error||d.detail){$('#readerBody').innerHTML=head+'<div class="card empty">'+esc(d.error||d.detail)+'</div>';return}
    var kp=(d.key_pearls||[]).filter(Boolean);$('#readerBody').innerHTML=head+(kp.length?'<div class="callout"><span class="eyebrow">Key pearls</span><ul>'+kp.slice(0,5).map(function(p){return '<li>'+mdi(p)+'</li>'}).join('')+'</ul></div>':'')+'<div class="prose">'+md(d.content)+'</div>';mathify($('#readerBody'))})}
function doi(x){x=String(x||'');return /^https?:/.test(x)?x:'https://doi.org/'+x}
function trialKV(t){var kv=[['Design',t.trial_type],['Sample',t.sample_size?Number(t.sample_size).toLocaleString():''],['Year',t.year],['Evidence',t.evidence_level]];if(t.key_stats)Object.keys(t.key_stats).forEach(function(k){kv.push([k.replace(/_/g,' '),t.key_stats[k]])});
  return '<div class="kv">'+kv.filter(function(x){return x[1]}).map(function(x){return '<div><b>'+esc(x[0])+'</b><span>'+esc(trunc(x[1],60))+'</span></div>'}).join('')+'</div>'}
function bulletize(s){return String(s||'').replace(/^\s*•\s*\n?/gm,'- ').replace(/\n(?!\s*-)/g,' ').replace(/ - /g,'\n- ')}
function openTrial(slug){openReader('','<div class="empty">Loading…</div>');api('/api/trial/'+encodeURIComponent(slug)).then(function(d){if(d.error||d.detail){$('#readerBody').innerHTML='<div class="card empty">'+esc(d.error||d.detail)+'</div>';return}
  setReaderTop(bmBtn('trial:'+slug,{kind:'trial',title:d.trial_name,system:d.specialty||'General',type:d.trial_type||'Trial',locator:{slug:slug}})+(d.doi?'<a class="btn sm" href="'+esc(doi(d.doi))+'" target="_blank" rel="noopener">'+ic('i-ext')+'Source</a>':''));
  $('#readerBody').innerHTML=pill(d.specialty)+' <span class="tag '+resTag(d.result_category)+'">'+esc(d.result_category)+'</span><h1 class="rt">'+esc(d.trial_name)+'</h1><div class="rmeta"><span>'+esc(d.primary_author||'')+'</span><span>'+esc(d.published||'')+'</span></div>'+
   '<div class="callout"><span class="eyebrow">Bottom line</span><div class="serif" style="font-size:18px">'+esc(d.one_liner)+'</div></div>'+trialKV(d)+'<div class="prose">'+(d.sections||[]).map(function(s){return '<h2>'+esc(s.heading)+'</h2>'+md(bulletize(s.content))}).join('')+'</div>'})}
function openCond(system,name){openReader('','<div class="empty">Loading…</div>');api('/api/condensed-trial/'+encodeURIComponent(system)+'/'+encodeURIComponent(name)).then(function(d){if(d.error||d.detail){$('#readerBody').innerHTML='<div class="card empty">'+esc(d.error||d.detail)+'</div>';return}
  setReaderTop(bmBtn('condensed:'+system+':'+name,{kind:'condensed',title:d.trial_name,system:system,type:'Trial',locator:{system:system,name:name}})+(d.doi?'<a class="btn sm" href="'+esc(doi(d.doi))+'" target="_blank" rel="noopener">'+ic('i-ext')+'Source</a>':''));
  var body=d.pico?'<h2>PICO</h2><table><tbody>'+Object.keys(d.pico).map(function(k){return '<tr><th>'+esc(k)+'</th><td>'+esc(d.pico[k])+'</td></tr>'}).join('')+'</tbody></table>':'';var Sx=d.sections||{};Object.keys(Sx).forEach(function(k){body+='<h2>'+esc(k.replace(/_/g,' '))+'</h2>'+renderAny(Sx[k])});
  $('#readerBody').innerHTML=pill(d.specialty||system,d.subtopic)+' <span class="tag '+resTag(d.result_category)+'">'+esc(d.result_category)+'</span><h1 class="rt">'+esc(d.trial_name)+'</h1><div class="callout"><span class="eyebrow">Bottom line</span><div class="serif" style="font-size:18px">'+esc(d.one_liner)+'</div></div>'+trialKV(d)+'<div class="prose">'+body+'</div>'})}
function openRef(ref){var i=ref.indexOf(':'),k=ref.slice(0,i),v=ref.slice(i+1);
  if(k==='paper'||k==='guideline'){var a=D.articles.find(function(x){return x.file_name===v});if(a)openArticle(a);else toast('Not available');return}
  if(k==='theory'||k==='note'){var n=D.notes.find(function(x){return x.rel===v||x.id===v});if(n){closeReader();go('topic',{id:n.id})}else toast('Not available');return}
  if(k==='deck'){var d=D.decks.find(function(x){return x.id===v});if(d)startCards([d],'review');return}
  if(k==='trial'){openTrial(v);return}
  if(k==='condensed'){var j=v.indexOf(':');openCond(v.slice(0,j),v.slice(j+1));return}
  if(k==='pearl'){var it=BM.items[ref]||{};openReader('',pill(it.system||'Pearl')+'<h1 class="rt">Saved pearl</h1><div class="prose"><p>'+mdi(it.title)+'</p></div>');return}
  if(k==='flashcard'){var loc=(BM.items[ref]||{}).locator||{},dk=D.decks.find(function(x){return x.id===loc.deck});if(dk){var c=dk.cards.find(function(x){return x.id===v})||dk.cards[0];closeReader();S.cards.session={mode:'browse',queue:[{deck:dk,card:c}],i:0,flipped:false,done:false,stats:{1:0,2:0,3:0,4:0},n:0};S.view='cards';setURL('cards');renderNav();render()}}}

/* ---------------- Bookmarks ---------------- */
function loadBM(){if(!D.features.bookmarks)return Promise.resolve();return api('/api/bookmarks').then(function(r){BM=r&&r.items?r:{items:{},folders:{}}}).catch(function(){})}
function toggleBM(ref,meta){if(BM.items[ref])return fetch('/api/bookmarks?ref='+encodeURIComponent(ref),{method:'DELETE',credentials:'same-origin'}).then(function(){delete BM.items[ref];toast('Removed from Saved')});
  return fetch('/api/bookmarks',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.assign({ref:ref},meta))}).then(function(r){return r.json()}).then(function(r){if(r.item){BM.items[ref]=r.item;toast('Saved')}})}

/* ---------------- Command palette ---------------- */
var palSel=0,palItems=[],palT=null;
function openPalette(){$('#palette').classList.add('on');$('#scrim').classList.add('on');$('#palInput').value='';palSearch('');setTimeout(function(){$('#palInput').focus()},30)}
function closePalette(){$('#palette').classList.remove('on');if(!$('#reader').classList.contains('on'))$('#scrim').classList.remove('on')}
$('#palInput').addEventListener('input',function(e){clearTimeout(palT);var q=e.target.value;palT=setTimeout(function(){palSearch(q)},110)});
function score(h,w){h=norm(h);var s=0;for(var i=0;i<w.length;i++){var k=h.indexOf(w[i]);if(k<0)return 0;s+=k===0?3:1}return s}
function palSearch(q){var w=norm(q).split(' ').filter(Boolean),G=[];
  var take=function(arr,fn,lim){return arr.map(function(x){return [score(fn(x),w),x]}).filter(function(p){return p[0]}).sort(function(a,b){return b[0]-a[0]}).slice(0,lim).map(function(p){return p[1]})};
  if(!w.length){G.push({g:'Jump to',items:NAV.filter(function(n){return n.id&&(!n.feat||D.features[n.feat])}).map(function(n){return {t:n.label,s:'',run:function(){go(n.id)}}})})}
  else{var nt=take(D.notes,function(n){return n.title+' '+n.subtopic+' '+n.system},6);if(nt.length)G.push({g:'Topics',items:nt.map(function(n){return {t:n.title,s:n.system,run:function(){go('topic',{id:n.id})}}})});
    var dk=take(D.decks,function(d){return d.title+' '+d.specialty+' '+(d.subtopics||[]).join(' ')},3);if(dk.length)G.push({g:'Flashcard decks',items:dk.map(function(d){return {t:d.title,s:d.cards.length+' cards',run:function(){startCards([d],'review')}}})});
    var mt={};D.mcqs.forEach(function(x){var k=x.s+'|'+x.t;mt[k]=(mt[k]||0)+1});var mk=take(Object.keys(mt),function(k){return k.replace('|',' ')},3);if(mk.length)G.push({g:'MCQs',items:mk.map(function(k){var p=k.split('|');return {t:p[1],s:mt[k]+' MCQs',run:function(){startMcq(pickMcqs({spec:p[0],topic:p[1],n:20,filter:'all'}),'tutor')}}})});
    var gl=take(D.articles.filter(isGuideline),function(a){return a.title+' '+a.subtopic},4);if(gl.length)G.push({g:'Guidelines',items:gl.map(function(a){return {t:a.title,s:a.system,run:function(){openGuideline(a)}}})});
    if(D.features.pearls)G.push({g:'Pearls',items:[{t:'Search pearls for “'+q+'”',s:'↵',run:function(){S.pearls.q=q;S.pearls.mode='grid';S.pearls.items=[];go('pearls')}}]});
    var pp=take(D.articles.filter(isPaper),function(a){return a.title+' '+a.subtopic},3);if(pp.length)G.push({g:'Papers',items:pp.map(function(a){return {t:a.title,s:a.type,run:function(){openArticle(a)}}})});
    var tr=take(D.trials,function(t){return t.trial_name+' '+t.one_liner},3);if(tr.length)G.push({g:'Trials',items:tr.map(function(t){return {t:t.trial_name,s:t.result_category,run:function(){openTrial(t.slug)}}})})}
  palItems=[];var h='';G.forEach(function(g){h+='<div class="pal-group">'+g.g+'</div>';g.items.forEach(function(it){h+='<button class="pal-item" role="option" data-pi="'+palItems.length+'"><span class="pt">'+esc(it.t)+'</span><span class="ps">'+esc(it.s)+'</span></button>';palItems.push(it)})});
  $('#palRes').innerHTML=h||'<div class="empty">No matches.</div>';palSel=0;palMark()}
function palMark(){$$('.pal-item').forEach(function(b,i){b.setAttribute('aria-selected',i===palSel);if(i===palSel)b.scrollIntoView({block:'nearest'})})}
$('#palRes').addEventListener('click',function(e){var b=e.target.closest('.pal-item');if(b){var it=palItems[+b.dataset.pi];closePalette();it.run()}});

/* ---------------- Keyboard ---------------- */
document.addEventListener('keydown',function(e){var inF=/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName);
  if((e.key==='k'&&(e.metaKey||e.ctrlKey))||(e.key==='/'&&!inF)){e.preventDefault();openPalette();return}
  if($('#palette').classList.contains('on')){if(e.key==='Escape')closePalette();else if(e.key==='ArrowDown'){e.preventDefault();palSel=Math.min(palSel+1,palItems.length-1);palMark()}else if(e.key==='ArrowUp'){e.preventDefault();palSel=Math.max(palSel-1,0);palMark()}else if(e.key==='Enter'&&palItems[palSel]){var it=palItems[palSel];closePalette();it.run()}return}
  if($('#modal').classList.contains('on')){if(e.key==='Escape')closeModal();return}
  if(e.key==='Escape'){closeReader();return}
  if(inF||e.metaKey||e.ctrlKey||e.altKey||$('#reader').classList.contains('on'))return;
  var C=S.cards.session;
  if(S.view==='cards'&&C&&!C.done){
    if(e.key===' '){e.preventDefault();if(C.mode==='browse'||!C.flipped)ACT.flip();return}
    if(C.mode==='browse'){if(e.key==='ArrowRight')ACT.cnext();else if(e.key==='ArrowLeft')ACT.cprev();return}
    if(C.flipped&&/^[1-4]$/.test(e.key)){ACT.rate(+e.key);return}
    if(e.key==='Enter'&&!C.flipped){ACT.flip();return}}
  var R=S.mcq.run;
  if(S.view==='mcq'&&R&&!R.done){var q=R.qs[R.i],idx='ABCDE'.indexOf(e.key.toUpperCase());if(idx<0&&/^[1-5]$/.test(e.key))idx=+e.key-1;
    if(idx>-1&&q.shown[idx]){var btn=$$('.opt')[idx];if(btn&&!btn.disabled)ACT.mPick(btn);return}
    var can=!(R.mode==='tutor'&&R.ans[q.id]==null);
    if(e.key==='Enter'||e.key==='ArrowRight'){if(!can)return;if(R.i<R.qs.length-1)ACT.mNext();else ACT.mFinish();return}
    if(e.key==='ArrowLeft'){ACT.mPrev();return}}
  if(S.view==='pearls'&&S.pearls.mode==='quick'&&S.pearls.qf&&S.pearls.qf.i<S.pearls.qf.items.length){if(e.key==='ArrowRight')ACT.qfYes();else if(e.key==='ArrowLeft')ACT.qfNo()}
});

/* ---------------- Modal / theme / boot ---------------- */
function modal(html,buttons){$('#modalBody').innerHTML=html;$('#modalFoot').innerHTML=(buttons||[]).map(function(b,i){return '<button class="btn'+(i===buttons.length-1?' primary':'')+'" data-mb="'+i+'">'+b[0]+'</button>'}).join('');$('#modal').classList.add('on');
  $('#modalFoot').onclick=function(e){var b=e.target.closest('[data-mb]');if(!b)return;var fn=buttons[+b.dataset.mb][1];closeModal();if(typeof fn==='function')fn()};setTimeout(function(){var f=$('#modalFoot .primary');if(f)f.focus()},30)}
function closeModal(){$('#modal').classList.remove('on')}
function syncTheme(){var dark=document.documentElement.dataset.theme==='dark';$('#themeBtn').innerHTML=ic(dark?'i-sun':'i-moon');$('#themeBtn').setAttribute('aria-label',dark?'Switch to light mode':'Switch to dark mode')}
$('#themeBtn').onclick=function(){var t=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=t;localStorage.setItem('hc2-theme',t);syncTheme()};
$('#avatar').onclick=function(){modal('<h2 style="margin-top:0">'+esc(D.user.name)+'</h2><p class="mono muted">'+esc(D.user.email)+'</p><p><a href="'+esc(D.links.subscribe)+'" target="_blank" rel="noopener">Subscribe to the email digest</a> · <a href="'+esc(D.links.unsubscribe)+'" target="_blank" rel="noopener">Unsubscribe</a></p>',D.local_dev?[['Close','']]:[['Sign out',ACT.logout],['Close','']])};
syncTheme();
Promise.all([api('/api/redefined/bootstrap'),api('/api/redefined/progress').catch(function(){return null})]).then(function(r){
  D=r[0];if(r[1])PR=Object.assign(PR,r[1]);
  if(D.local_dev)$('#logoutBtn').style.display='none';
  $('#avatar').textContent=(D.user.name||'?').charAt(0).toUpperCase();
  readURL();renderStreak();renderNav();render();
  loadBM().then(function(){renderNav();if(S.view==='saved'||S.view==='topic')render()});
  if(D.disclaimer&&!localStorage.getItem('hc2-disclaimer-ok'))modal(md(D.disclaimer),[['I understand — proceed',function(){localStorage.setItem('hc2-disclaimer-ok','1')}]]);
});
})();
</script>
</body>
</html>
"""
