"""
redefined_ui.py — hack.CCM portal, redesigned.

A new front end for the hack.CCM knowledge portal. It does NOT modify any
existing file: it imports `revamped_webapp` read-only, re-uses every API route
it defines (auth, bookmarks, summaries, pearls, trials, print export, admin),
and serves a brand-new single-page UI at `/`.

    uvicorn redefined_ui:app --port 8000      # new UI at  /
                                              # old UI at  /classic

Design system ("Ward Round"):
  * Paper-and-ink reading surface, one clinical teal accent, coral for alerts.
  * Newsreader (serif) for reading, Inter for interface, JetBrains Mono for data.
  * Left rail navigation on desktop, bottom tab bar on mobile.
  * Light + dark themes, command palette (Ctrl/Cmd-K or "/"), slide-over reader.
"""

import json
import os
import re
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

import revamped_webapp as legacy

app = FastAPI(title="hack.CCM — redefined UI")

# Re-use every legacy route except the old home page, which moves to /classic.
for _route in legacy.app.router.routes:
    if getattr(_route, "path", None) == "/":
        continue
    app.router.routes.append(_route)


@app.get("/classic", response_class=HTMLResponse)
async def classic_ui(request: Request):
    """The previous portal, unchanged."""
    from fastapi import Response
    return await legacy.render_dashboard(request, Response())


# ---------------------------------------------------------------------------
# Data helpers (read-only views over legacy loaders)
# ---------------------------------------------------------------------------

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


def _user_or_401(request):
    user = legacy._get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    return user


@app.get("/api/redefined/bootstrap")
async def redefined_bootstrap(request: Request):
    user = _user_or_401(request)
    has = lambda f: bool(legacy._user_has_feature(user, f))
    features = {f: has(f) for f in legacy.FEATURE_FLAGS}

    articles = _articles() if (features["papers"] or features["guidelines"]) else []
    pearls = legacy.load_pearls() if features["pearls"] else []
    pearl_systems = {}
    for p in pearls:
        s = p.get("system")
        if isinstance(s, str) and s.strip():
            pearl_systems[s] = pearl_systems.get(s, 0) + 1
    # Deterministic "pearl of the day"
    pearl_of_day = None
    if pearls:
        p = pearls[datetime.utcnow().toordinal() % len(pearls)]
        pearl_of_day = {k: p.get(k) for k in ("id", "pearl", "system", "source_paper", "type", "doi")}

    trials = legacy.load_trial_index() if features["trials"] else []
    condensed = legacy.load_condensed_trial_index() if features["condensed_trials"] else []
    decks = legacy.load_flashcard_decks() if features["theory"] else []
    notes = []
    if features["theory"]:
        for n in legacy.load_theory_notes():
            notes.append({k: n.get(k) for k in ("id", "title", "system", "subtopic", "date_added")})

    colors = dict(legacy.SPEC_COLORS)
    colors.update({k: v for k, v in legacy.ESBICM_SPEC_COLORS.items()})

    return {
        "user": {
            "name": (user.get("first_name") or user.get("email", "").split("@")[0]),
            "email": user.get("email", ""),
            "is_admin": bool(user.get("is_admin")),
        },
        "features": features,
        "articles": articles,
        "pearl_count": len(pearls),
        "pearl_systems": pearl_systems,
        "pearl_of_day": pearl_of_day,
        "trials": trials,
        "condensed": condensed,
        "decks": decks,
        "notes": notes,
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
    legacy._require_feature(user, "theory")
    for n in legacy.load_theory_notes():
        if n.get("id") == id:
            return n
    return JSONResponse(status_code=404, content={"error": "Note not found"})


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
<title>hack.CCM — Critical care, distilled</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<script>
  (function(){var t=localStorage.getItem('hc2-theme');if(!t){t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}document.documentElement.dataset.theme=t})();
</script>
<style>
:root{
  --bg:#F5F3EE; --bg-2:#EDEAE3; --surface:#FFFFFF; --surface-2:#FAF9F6;
  --ink:#141B22; --ink-2:#3A4550; --muted:#6B7580; --line:#E3DFD6; --line-2:#D5D0C5;
  --accent:#0F766E; --accent-ink:#FFFFFF; --accent-soft:#E3F1EF;
  --coral:#C2410C; --coral-soft:#FBEDE5; --amber:#B45309; --amber-soft:#FBF1DF;
  --pos:#15803D; --pos-soft:#E5F3EA; --neg:#64748B; --neg-soft:#EEF1F4;
  --shadow:0 1px 2px rgba(20,27,34,.04),0 4px 16px rgba(20,27,34,.06);
  --shadow-lg:0 24px 64px rgba(20,27,34,.18);
  --r:14px; --r-sm:9px;
  --serif:"Newsreader",Georgia,"Times New Roman",serif;
  --sans:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  --rail:252px;
}
[data-theme="dark"]{
  --bg:#0D1115; --bg-2:#12171C; --surface:#161C22; --surface-2:#1A2128;
  --ink:#E7EBEE; --ink-2:#BCC5CD; --muted:#87929D; --line:#242D36; --line-2:#2F3943;
  --accent:#2DD4BF; --accent-ink:#04211E; --accent-soft:#11302D;
  --coral:#FB923C; --coral-soft:#3A2216; --amber:#FBBF24; --amber-soft:#33280F;
  --pos:#4ADE80; --pos-soft:#14301F; --neg:#94A3B8; --neg-soft:#1E2730;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 6px 20px rgba(0,0,0,.25);
  --shadow-lg:0 24px 64px rgba(0,0,0,.55);
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none} a:hover{text-decoration:underline}
button{font:inherit;color:inherit;cursor:pointer}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:6px}
.mono{font-family:var(--mono)}
.serif{font-family:var(--serif)}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}

/* ---------- Shell ---------- */
.shell{display:grid;grid-template-columns:var(--rail) 1fr;min-height:100vh}
.rail{position:sticky;top:0;height:100vh;display:flex;flex-direction:column;gap:4px;padding:22px 14px 16px;border-right:1px solid var(--line);background:var(--bg)}
.brand{display:flex;align-items:center;gap:10px;padding:2px 10px 20px}
.brand-mark{width:34px;height:34px;border-radius:10px;background:var(--ink);color:var(--bg);display:grid;place-items:center}
.brand-mark svg{width:22px;height:22px}
.brand-name{font-family:var(--serif);font-size:22px;font-weight:600;letter-spacing:-.01em}
.brand-name b{color:var(--accent);font-weight:600}
.rail-label{font:500 11px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted);padding:16px 12px 8px}
.nav-btn{display:flex;align-items:center;gap:12px;width:100%;padding:9px 12px;border:0;background:none;border-radius:10px;font-weight:500;color:var(--ink-2);text-align:left}
.nav-btn svg{width:18px;height:18px;flex:none;opacity:.8}
.nav-btn .count{margin-left:auto;font:500 11px var(--mono);color:var(--muted)}
.nav-btn:hover{background:var(--bg-2);color:var(--ink)}
.nav-btn[aria-current="page"]{background:var(--surface);color:var(--ink);box-shadow:var(--shadow)}
.nav-btn[aria-current="page"] svg{color:var(--accent);opacity:1}
.rail-foot{margin-top:auto;display:flex;flex-direction:column;gap:2px;border-top:1px solid var(--line);padding-top:12px}
.rail-foot .nav-btn{font-size:13.5px;padding:7px 12px}

.main{min-width:0;display:flex;flex-direction:column}
.topbar{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:12px;padding:14px 36px;background:color-mix(in srgb,var(--bg) 86%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid transparent}
.topbar.scrolled{border-bottom-color:var(--line)}
.search-trigger{flex:1;min-width:0;max-width:560px;display:flex;align-items:center;gap:10px;padding:10px 14px;border:1px solid var(--line);background:var(--surface);border-radius:12px;color:var(--muted);text-align:left;box-shadow:var(--shadow)}
.search-trigger svg{width:17px;height:17px}
.kbd{margin-left:auto;font:500 11px var(--mono);padding:2px 7px;border:1px solid var(--line-2);border-radius:6px;color:var(--muted)}
.top-actions{margin-left:auto;display:flex;gap:6px;align-items:center}
.icon-btn{width:38px;height:38px;display:grid;place-items:center;border:1px solid var(--line);background:var(--surface);border-radius:11px;color:var(--ink-2)}
.icon-btn:hover{color:var(--ink);border-color:var(--line-2)}
.icon-btn svg{width:18px;height:18px}
.avatar{width:38px;height:38px;border-radius:50%;background:var(--accent-soft);color:var(--accent);display:grid;place-items:center;font-weight:600;border:0}
.content{padding:8px 36px 80px;max-width:1280px;width:100%}

/* ---------- Typography ---------- */
.eyebrow{font:500 11.5px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
h1.page-title{font-family:var(--serif);font-weight:500;font-size:40px;line-height:1.1;letter-spacing:-.02em;margin:10px 0 6px}
.page-sub{color:var(--muted);margin:0 0 26px;max-width:640px}
h2.sec{font-family:var(--serif);font-weight:500;font-size:24px;letter-spacing:-.01em;margin:44px 0 14px;display:flex;align-items:baseline;gap:12px}
h2.sec .link{margin-left:auto;font:500 13px var(--sans)}

/* ---------- Cards & atoms ---------- */
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--shadow)}
.pill{width:fit-content;display:inline-flex;align-items:center;gap:6px;font:500 11.5px/1 var(--mono);padding:5px 9px;border-radius:999px;background:var(--bg-2);color:var(--ink-2);white-space:nowrap}
.dot{width:8px;height:8px;border-radius:50%;flex:none;background:var(--c,var(--muted))}
.res{font:600 11px/1 var(--mono);padding:5px 8px;border-radius:6px;letter-spacing:.02em;white-space:nowrap}
.res.pos{background:var(--pos-soft);color:var(--pos)}
.res.neg{background:var(--neg-soft);color:var(--neg)}
.res.harm{background:var(--coral-soft);color:var(--coral)}
.res.mix{background:var(--amber-soft);color:var(--amber)}
.btn{display:inline-flex;align-items:center;gap:8px;padding:9px 15px;border-radius:10px;border:1px solid var(--line);background:var(--surface);font-weight:500;font-size:14px}
.btn:hover{border-color:var(--line-2)}
.btn.primary{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.btn.accent{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
.btn svg{width:16px;height:16px}
.btn.saved{color:var(--accent);border-color:var(--accent)}
.chip{border:1px solid var(--line);background:var(--surface);padding:6px 12px;border-radius:999px;font-size:13px;font-weight:500;color:var(--ink-2);display:inline-flex;align-items:center;gap:7px}
.chip:hover{border-color:var(--line-2)}
.chip[aria-pressed="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.chip[aria-pressed="true"] .dot{box-shadow:0 0 0 2px var(--bg)}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.empty{padding:48px 20px;text-align:center;color:var(--muted)}

/* ---------- Home ---------- */
.hero{display:grid;grid-template-columns:1.35fr 1fr;gap:20px;margin-top:6px}
.hero-main{padding:30px 32px;position:relative;overflow:hidden}
.hero-main::after{content:"";position:absolute;right:-40px;bottom:-30px;width:320px;height:120px;background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 320 120'%3E%3Cpath d='M0 70h90l12-22 14 52 18-90 16 78 10-18h160' fill='none' stroke='%230F766E' stroke-width='2.5' stroke-linejoin='round' opacity='.22'/%3E%3C/svg%3E") no-repeat;pointer-events:none}
.hero-main h1{font-family:var(--serif);font-weight:500;font-size:44px;line-height:1.05;letter-spacing:-.025em;margin:12px 0 10px}
.hero-main h1 em{font-style:italic;color:var(--accent)}
.hero-main p{color:var(--ink-2);margin:0 0 22px;max-width:520px;font-size:16px}
.hero-search svg{width:18px;height:18px;flex:none}
.hero-search span:not(.kbd){overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.search-trigger span:not(.kbd){overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hero-search{display:flex;align-items:center;gap:10px;padding:13px 16px;border:1px solid var(--line-2);border-radius:12px;background:var(--surface-2);max-width:520px;color:var(--muted);width:100%;text-align:left}
.stats{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.stat{padding:18px 20px;display:flex;flex-direction:column;justify-content:space-between;gap:14px;text-align:left;border:1px solid var(--line);position:relative;overflow:hidden}
.stat::after{content:"";position:absolute;left:20px;right:20px;bottom:0;height:3px;border-radius:3px 3px 0 0;background:var(--sc,var(--accent));opacity:.7}
.stat:hover{border-color:var(--line-2)}
.stat .n{font-family:var(--serif);font-size:46px;font-weight:500;letter-spacing:-.02em;line-height:1.1}
.stat .l{font:500 11.5px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.stat .h{color:var(--muted);font-size:13px;margin-top:2px}
.daily{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.daily .card{padding:22px;display:flex;flex-direction:column;gap:12px;text-align:left;border:1px solid var(--line);min-height:200px}
.daily .card:hover{border-color:var(--line-2);transform:translateY(-1px)}
.daily h3{font-family:var(--serif);font-size:20px;font-weight:500;line-height:1.25;margin:0}
.daily .quote{font-family:var(--serif);font-size:17px;line-height:1.45;margin:0;color:var(--ink)}
.daily .meta{margin-top:auto;color:var(--muted);font-size:13px}
.spec-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px}
.spec{display:flex;align-items:center;gap:12px;padding:14px 16px;text-align:left;border:1px solid var(--line);background:var(--surface);border-radius:12px}
.spec:hover{border-color:var(--c);box-shadow:var(--shadow)}
.spec .sw{width:30px;height:30px;border-radius:8px;background:color-mix(in srgb,var(--c) 14%,transparent);display:grid;place-items:center}
.spec .sw i{width:10px;height:10px;border-radius:3px;background:var(--c)}
.spec b{font-weight:600;font-size:14px;display:block}
.spec .sc{display:block;font:12px var(--mono);color:var(--muted)}
.recent{display:flex;flex-direction:column}
.roadmap{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.roadmap .card{padding:18px 20px;box-shadow:none;background:transparent;border-style:dashed}
.roadmap b{font-family:var(--serif);font-weight:500;font-size:17px;display:block;margin:8px 0 4px}
.roadmap p{margin:0;color:var(--muted);font-size:13.5px}

/* ---------- Library ---------- */
.lib{display:grid;grid-template-columns:240px 1fr;gap:28px;align-items:start}
.filters{position:sticky;top:84px;display:flex;flex-direction:column;gap:22px}
.f-group h4{margin:0 0 8px;font:500 11px var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.f-list{display:flex;flex-direction:column;gap:1px;max-height:48vh;overflow:auto;margin:0 -8px;padding:0 8px}
.f-item{display:flex;align-items:center;gap:10px;padding:6px 8px;border:0;background:none;border-radius:8px;text-align:left;font-size:13.5px;color:var(--ink-2)}
.f-item:hover{background:var(--bg-2)}
.f-item[aria-pressed="true"]{background:var(--surface);color:var(--ink);font-weight:600;box-shadow:var(--shadow)}
.f-item .c{margin-left:auto;font:11.5px var(--mono);color:var(--muted)}
.toolbar{display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap}
.input{flex:1;min-width:200px;display:flex;align-items:center;gap:9px;padding:10px 13px;border:1px solid var(--line);background:var(--surface);border-radius:11px}
.input input{border:0;outline:0;background:none;flex:1;font:inherit;color:var(--ink);min-width:0}
.input svg{width:16px;height:16px;color:var(--muted)}
select.sel{padding:10px 12px;border:1px solid var(--line);background:var(--surface);border-radius:11px;font:inherit;color:var(--ink)}
.result-count{font:12px var(--mono);color:var(--muted);margin:0 0 8px}
.list{overflow:hidden}
.row{display:grid;grid-template-columns:4px 1fr auto;gap:16px;align-items:center;padding:16px 20px 16px 0;border:0;border-bottom:1px solid var(--line);background:none;text-align:left;width:100%}
.row:last-child{border-bottom:0}
.row:hover{background:var(--surface-2)}
.row .bar{align-self:stretch;background:var(--c,var(--line));border-radius:0 3px 3px 0;opacity:.85}
.row .t{font-family:var(--serif);font-size:18px;font-weight:500;line-height:1.3;letter-spacing:-.005em;color:var(--ink)}
.row .m{margin-top:5px;display:flex;flex-wrap:wrap;gap:6px 14px;font:12.5px var(--mono);color:var(--muted)}
.row .m .s{color:var(--ink-2)}
.row .one{margin-top:6px;color:var(--ink-2);font-size:14px}
.row .r{display:flex;flex-direction:column;align-items:flex-end;gap:6px}
.more{display:flex;justify-content:center;padding:18px}

/* ---------- Pearls ---------- */
.pearls{columns:3 300px;column-gap:16px}
.pearl{break-inside:avoid;margin:0 0 16px;padding:20px 20px 16px;position:relative;border-top:3px solid var(--c,var(--accent))}
.pearl p{font-family:var(--serif);font-size:16.5px;line-height:1.5;margin:0 0 14px;transition:filter .2s}
.recall .pearl p{filter:blur(5px);cursor:pointer;user-select:none}
.recall .pearl.revealed p{filter:none}
.pearl .src{font-size:12.5px;color:var(--muted);display:flex;gap:10px;align-items:flex-start}
.pearl .src span{flex:1}
.pearl .save{border:0;background:none;color:var(--muted);padding:2px}
.pearl .save.on{color:var(--accent)}
.pearl .save svg{width:17px;height:17px}

/* ---------- Theory ---------- */
.tabs{display:inline-flex;padding:4px;border-radius:12px;background:var(--bg-2);gap:2px;margin-bottom:22px}
.tab{border:0;background:none;padding:8px 16px;border-radius:9px;font-weight:500;color:var(--muted)}
.tab[aria-selected="true"]{background:var(--surface);color:var(--ink);box-shadow:var(--shadow)}
.decks{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}
.deck{padding:20px;text-align:left;display:flex;flex-direction:column;gap:10px;min-height:150px;border:1px solid var(--line);position:relative;overflow:hidden}
.deck::before{content:"";position:absolute;inset:0 0 auto 0;height:3px;background:var(--c)}
.deck:hover{border-color:var(--line-2);transform:translateY(-1px)}
.deck h3{font-family:var(--serif);font-weight:500;font-size:20px;margin:0;line-height:1.2}
.deck .meta{margin-top:auto;display:flex;justify-content:space-between;font:12px var(--mono);color:var(--muted)}
.study{max-width:760px;margin:0 auto}
.study-head{display:flex;align-items:center;gap:12px;margin-bottom:16px}
.progress{height:4px;background:var(--bg-2);border-radius:4px;overflow:hidden;margin-bottom:22px}
.progress i{display:block;height:100%;background:var(--accent);transition:width .25s}
.flip{perspective:1600px;cursor:pointer;min-height:380px}
.flip-in{position:relative;min-height:380px;transition:transform .5s cubic-bezier(.2,.7,.2,1);transform-style:preserve-3d}
.flip.on .flip-in{transform:rotateY(180deg)}
.face{position:absolute;inset:0;backface-visibility:hidden;-webkit-backface-visibility:hidden;padding:34px 38px;overflow:auto;display:flex;flex-direction:column}
.face.front{justify-content:center;align-items:center;text-align:center}
.face.front .q{font-family:var(--serif);font-size:27px;line-height:1.3;font-weight:500;letter-spacing:-.01em;max-width:560px}
.face.back{transform:rotateY(180deg)}
.face .hint{position:absolute;bottom:14px;left:0;right:0;text-align:center;font:11.5px var(--mono);color:var(--muted)}
.study-nav{display:flex;align-items:center;justify-content:center;gap:12px;margin-top:20px}

/* ---------- Reader (slide-over) ---------- */
.scrim{position:fixed;inset:0;background:rgba(10,14,18,.38);opacity:0;pointer-events:none;transition:opacity .2s;z-index:40}
.scrim.on{opacity:1;pointer-events:auto}
.reader{position:fixed;top:0;right:0;bottom:0;width:min(780px,100vw);background:var(--surface);z-index:41;transform:translateX(100%);transition:transform .28s cubic-bezier(.2,.7,.2,1);display:flex;flex-direction:column;box-shadow:var(--shadow-lg)}
.reader.on{transform:none}
.reader-top{display:flex;align-items:center;gap:8px;padding:14px 20px;border-bottom:1px solid var(--line)}
.reader-body{overflow:auto;padding:30px 48px 80px}
.reader-body h1.rt{font-family:var(--serif);font-weight:500;font-size:32px;line-height:1.15;letter-spacing:-.02em;margin:14px 0 10px}
.reader-meta{display:flex;flex-wrap:wrap;gap:8px 16px;font:12.5px var(--mono);color:var(--muted);margin-bottom:22px}
.callout{padding:16px 18px;border-radius:12px;background:var(--accent-soft);border:1px solid color-mix(in srgb,var(--accent) 25%,transparent);margin:0 0 24px}
.callout .eyebrow{color:var(--accent);margin-bottom:8px;display:block}
.callout ul{margin:0;padding-left:18px}
.callout li{margin:4px 0;font-family:var(--serif);font-size:16px}
.prose{font-family:var(--serif);font-size:17.5px;line-height:1.65;color:var(--ink)}
.prose h1,.prose h2,.prose h3,.prose h4{font-family:var(--sans);letter-spacing:-.01em;line-height:1.25;margin:1.8em 0 .6em}
.prose h1{font-size:22px}.prose h2{font-size:19px;padding-bottom:6px;border-bottom:1px solid var(--line)}.prose h3{font-size:16.5px}.prose h4{font-size:15px;color:var(--ink-2)}
.prose p{margin:.75em 0}
.prose ul,.prose ol{padding-left:1.3em}
.prose li{margin:.3em 0}
.prose strong{font-weight:600;color:var(--ink)}
.prose blockquote{margin:1em 0;padding:4px 18px;border-left:3px solid var(--accent);color:var(--ink-2)}
.prose code{font:14px var(--mono);background:var(--bg-2);padding:1px 5px;border-radius:5px}
.prose table{border-collapse:collapse;width:100%;font:14px var(--sans);margin:1.2em 0;display:block;overflow:auto}
.prose th,.prose td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
.prose th{background:var(--bg-2);font-weight:600}
.prose hr{border:0;border-top:1px solid var(--line);margin:2em 0}
.kv{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin:0 0 24px}
.kv div{padding:12px 14px;border:1px solid var(--line);border-radius:10px}
.kv b{display:block;font:500 10.5px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:4px}
.kv span{font-weight:600}

/* ---------- Palette ---------- */
.palette{position:fixed;left:50%;top:12vh;transform:translate(-50%,-8px) scale(.98);width:min(680px,94vw);z-index:51;opacity:0;pointer-events:none;transition:.16s;overflow:hidden;box-shadow:var(--shadow-lg)}
.palette.on{opacity:1;pointer-events:auto;transform:translate(-50%,0) scale(1)}
.palette .input{border:0;border-bottom:1px solid var(--line);border-radius:0;padding:16px 18px;font-size:16px;box-shadow:none}
.pal-res{max-height:56vh;overflow:auto;padding:8px}
.pal-group{font:500 10.5px var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted);padding:12px 12px 6px}
.pal-item{display:flex;gap:12px;align-items:center;width:100%;border:0;background:none;text-align:left;padding:10px 12px;border-radius:10px}
.pal-item[aria-selected="true"],.pal-item:hover{background:var(--bg-2)}
.pal-item .pt{font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pal-item .ps{font:12px var(--mono);color:var(--muted);margin-left:auto;white-space:nowrap}
.pal-foot{display:flex;gap:16px;padding:10px 16px;border-top:1px solid var(--line);font:11.5px var(--mono);color:var(--muted)}

/* ---------- Modal ---------- */
.modal{position:fixed;inset:0;display:grid;place-items:center;z-index:60;padding:20px;background:rgba(10,14,18,.5);opacity:0;pointer-events:none;transition:.2s}
.modal.on{opacity:1;pointer-events:auto}
.modal .card{width:min(620px,100%);max-height:86vh;display:flex;flex-direction:column;box-shadow:var(--shadow-lg)}
.modal .mb{overflow:auto;padding:28px 32px 8px}
.modal .mf{padding:16px 32px 24px;display:flex;justify-content:flex-end;gap:10px;border-top:1px solid var(--line)}
.modal .prose{font-size:16px}

/* ---------- Mobile ---------- */
.tabbar{display:none}
@media (max-width:1100px){
  .hero{grid-template-columns:1fr}
  .daily{grid-template-columns:1fr 1fr}
  .roadmap{grid-template-columns:1fr 1fr}
}
@media (max-width:860px){
  .shell{grid-template-columns:1fr}
  .rail{display:none}
  .topbar{padding:12px 16px;gap:8px}
  .top-actions{flex:none}
  .content{padding:4px 16px 110px}
  .hero-main{padding:24px 22px}
  .hero-main h1{font-size:34px}
  .hero-main::after{display:none}
  .stat .n{font-size:34px}
  .stats{gap:10px}
  h1.page-title{font-size:32px}
  .daily,.roadmap{grid-template-columns:1fr}
  .lib{grid-template-columns:1fr}
  .filters{position:static;flex-direction:row;overflow:auto;gap:14px}
  .filters .f-group{min-width:220px}
  .f-list{max-height:180px}
  .reader-body{padding:22px 20px 80px}
  .reader-body h1.rt{font-size:26px}
  .kbd{display:none}
  .tabbar{display:flex;position:fixed;left:0;right:0;bottom:0;z-index:30;background:var(--surface);border-top:1px solid var(--line);padding:6px 6px calc(6px + env(safe-area-inset-bottom))}
  .tabbar button{flex:1;border:0;background:none;display:flex;flex-direction:column;align-items:center;gap:3px;padding:6px 0;font-size:10.5px;font-weight:500;color:var(--muted)}
  .tabbar button svg{width:21px;height:21px}
  .tabbar button[aria-current="page"]{color:var(--accent)}
  .face{padding:26px 22px}
  .face.front .q{font-size:22px}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <defs>
    <symbol id="i-home" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/></symbol>
    <symbol id="i-paper" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z"/><path d="M14 3v5h5M8 13h8M8 17h5"/></symbol>
    <symbol id="i-guide" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 21V5M9 8h6M9 12h4"/></symbol>
    <symbol id="i-pearl" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8"/><circle cx="9.5" cy="9.5" r="2"/></symbol>
    <symbol id="i-trial" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3h6M10 3v6L4.5 18.5A1.7 1.7 0 0 0 6 21h12a1.7 1.7 0 0 0 1.5-2.5L14 9V3"/><path d="M7 15h10"/></symbol>
    <symbol id="i-theory" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 6.5C10 5 7 4.5 3 5v14c4-.5 7 0 9 1.5 2-1.5 5-2 9-1.5V5c-4-.5-7 0-9 1.5z"/><path d="M12 6.5v14"/></symbol>
    <symbol id="i-cards" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="7" width="14" height="13" rx="2"/><path d="M7 4h12a2 2 0 0 1 2 2v11"/></symbol>
    <symbol id="i-bookmark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12v18l-6-4-6 4z"/></symbol>
    <symbol id="i-bookmark-f" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="M6 3h12v18l-6-4-6 4z"/></symbol>
    <symbol id="i-search" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></symbol>
    <symbol id="i-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></symbol>
    <symbol id="i-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z"/></symbol>
    <symbol id="i-x" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></symbol>
    <symbol id="i-ext" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></symbol>
    <symbol id="i-print" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M7 9V3h10v6M7 17H4v-6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v6h-3"/><path d="M7 14h10v7H7z"/></symbol>
    <symbol id="i-left" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></symbol>
    <symbol id="i-right" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></symbol>
    <symbol id="i-eye" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></symbol>
    <symbol id="i-shuffle" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5"/></symbol>
    <symbol id="i-info" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/></symbol>
    <symbol id="i-msg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a8 8 0 0 1-11.8 7L3 21l2-6.2A8 8 0 1 1 21 12z"/></symbol>
    <symbol id="i-logout" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h4M16 17l5-5-5-5M21 12H9"/></symbol>
    <symbol id="i-classic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/></symbol>
  </defs>
</svg>

<div class="shell">
  <aside class="rail" aria-label="Primary">
    <div class="brand">
      <div class="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 13h4l2-4 3 9 3-13 2.5 8H22"/></svg></div>
      <div class="brand-name">hack<b>.</b>CCM</div>
    </div>
    <nav id="nav"></nav>
    <div class="rail-foot">
      <button class="nav-btn" data-act="about"><svg><use href="#i-info"/></svg>About &amp; credits</button>
      <button class="nav-btn" data-act="feedback"><svg><use href="#i-msg"/></svg>Send feedback</button>
      <button class="nav-btn" data-act="classic"><svg><use href="#i-classic"/></svg>Classic view</button>
      <button class="nav-btn" data-act="logout" id="logoutBtn"><svg><use href="#i-logout"/></svg>Sign out</button>
    </div>
  </aside>

  <div class="main">
    <header class="topbar" id="topbar">
      <button class="search-trigger" id="openPalette" aria-label="Search everything">
        <svg><use href="#i-search"/></svg><span>Search papers, pearls, trials, theory…</span><span class="kbd">Ctrl K</span>
      </button>
      <div class="top-actions">
        <button class="icon-btn" id="themeBtn" aria-label="Toggle theme"><svg><use href="#i-moon"/></svg></button>
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
  <label class="input"><svg><use href="#i-search"/></svg><input id="palInput" placeholder="Search everything…" autocomplete="off"><span class="kbd">Esc</span></label>
  <div class="pal-res" id="palRes" role="listbox"></div>
  <div class="pal-foot"><span>↑↓ move</span><span>↵ open</span><span>/ or Ctrl K anywhere</span></div>
</div>

<div class="modal" id="modal" role="dialog" aria-modal="true">
  <div class="card"><div class="mb prose" id="modalBody"></div><div class="mf" id="modalFoot"></div></div>
</div>

<script>
(function(){
"use strict";
var D = null;                 // bootstrap payload
var BM = {items:{}, folders:{}};
var state = {view:'home', lib:{kind:'paper', spec:'', type:'', q:'', sort:'new', limit:40},
             pearls:{q:'', system:'', page:1, items:[], total:0, recall:false},
             trials:{src:'esbicm', q:'', spec:'', res:'', limit:40},
             theory:{tab:'notes', q:'', spec:''}, study:null};

var $ = function(s, r){ return (r||document).querySelector(s); };
var esc = function(s){ return String(s==null?'':s).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); };
var icon = function(id){ return '<svg><use href="#'+id+'"/></svg>'; };
var color = function(s){ return (D && D.colors && D.colors[s]) || hashColor(s||''); };
function hashColor(s){ var h=0; for(var i=0;i<s.length;i++) h=(h*31+s.charCodeAt(i))>>>0; return 'hsl('+(h%360)+' 45% 48%)'; }
function mdi(src){ return window.marked ? marked.parseInline(esc(src)) : esc(src); }
function md(src){
  var html = window.marked ? marked.parse(String(src||'')) : '<pre>'+esc(src)+'</pre>';
  return html;
}
function mathify(el){ if(window.renderMathInElement){ try{ renderMathInElement(el,{delimiters:[{left:'$$',right:'$$',display:true},{left:'\\(',right:'\\)',display:false}],throwOnError:false}); }catch(e){} } }
function api(url, opts){ return fetch(url, Object.assign({credentials:'same-origin'}, opts||{})).then(function(r){ if(r.status===401){ location.reload(); } return r.json(); }); }
function resClass(r){ r=(r||'').toLowerCase(); if(r.indexOf('harm')>-1) return 'harm'; if(r.indexOf('pos')>-1) return 'pos'; if(r.indexOf('mix')>-1) return 'mix'; return 'neg'; }
function fmtDate(s){ if(!s) return ''; var d=new Date(s.replace(' ','T')); return isNaN(d)?s:d.toLocaleDateString(undefined,{day:'numeric',month:'short',year:'numeric'}); }
function count(arr, key){ var m={}; arr.forEach(function(x){ var k=x[key]||'Other'; m[k]=(m[k]||0)+1; }); return m; }
function sortedKeys(m){ return Object.keys(m).sort(function(a,b){ return m[b]-m[a] || a.localeCompare(b); }); }
function dayPick(arr, salt){ if(!arr.length) return null; var d=Math.floor(Date.now()/864e5)+(salt||0); return arr[d % arr.length]; }

/* ---------------- Navigation ---------------- */
var NAV = [
  {id:'home', label:'Today', icon:'i-home'},
  {sep:'Library'},
  {id:'papers', label:'Papers', icon:'i-paper', feat:'papers'},
  {id:'guidelines', label:'Guidelines', icon:'i-guide', feat:'guidelines'},
  {id:'pearls', label:'Pearls', icon:'i-pearl', feat:'pearls'},
  {id:'trials', label:'Trials', icon:'i-trial', feat:'trials'},
  {sep:'Study'},
  {id:'theory', label:'Theory', icon:'i-theory', feat:'theory'},
  {id:'cards', label:'Flashcards', icon:'i-cards', feat:'theory'},
  {id:'saved', label:'Saved', icon:'i-bookmark', feat:'bookmarks'}
];
function navCount(id){
  if(!D) return '';
  if(id==='papers') return D.articles.filter(isPaper).length;
  if(id==='guidelines') return D.articles.filter(isGuideline).length;
  if(id==='pearls') return D.pearl_count;
  if(id==='trials') return D.trials.length + D.condensed.length;
  if(id==='theory') return D.notes.length;
  if(id==='cards') return D.decks.reduce(function(a,d){ return a+d.cards.length; },0);
  if(id==='saved') return Object.keys(BM.items||{}).length || '';
  return '';
}
function renderNav(){
  var html='', tab='';
  NAV.forEach(function(n){
    if(n.sep){ html += '<div class="rail-label">'+n.sep+'</div>'; return; }
    if(n.feat && D && !D.features[n.feat]) return;
    var cur = state.view===n.id ? ' aria-current="page"' : '';
    html += '<button class="nav-btn" data-go="'+n.id+'"'+cur+'>'+icon(n.icon)+'<span>'+n.label+'</span><span class="count">'+navCount(n.id)+'</span></button>';
    if(['home','papers','pearls','trials','theory'].indexOf(n.id)>-1)
      tab += '<button data-go="'+n.id+'"'+cur+'>'+icon(n.icon)+'<span>'+n.label+'</span></button>';
  });
  $('#nav').innerHTML = html; $('#tabbar').innerHTML = tab;
}
function go(view, opts){
  state.view = view;
  if(opts) Object.assign(state, opts);
  var u = new URL(location); u.searchParams.set('v', view); history.replaceState(null,'',u);
  renderNav(); render(); window.scrollTo(0,0);
}
document.addEventListener('click', function(e){
  var g = e.target.closest('[data-go]'); if(g){ e.preventDefault(); var v=g.dataset.go; if(g.dataset.spec!=null){ if(v==='papers'||v==='guidelines'){ state.lib.spec=g.dataset.spec; } } go(v); return; }
  var a = e.target.closest('[data-act]'); if(a){ ACT[a.dataset.act] && ACT[a.dataset.act](a); }
});

var ACT = {
  about: function(){ modal(md(D.disclaimer)+'<hr>'+md(D.credits), [['Close','']]); },
  feedback: function(){ window.open(D.links.feedback,'_blank','noopener'); },
  classic: function(){ location.href='/classic'; },
  logout: function(){ fetch('/api/logout',{method:'POST',credentials:'same-origin'}).then(function(){ location.href='/'; }); }
};

/* ---------------- Views ---------------- */
function isGuideline(a){ return (a.type||'').toLowerCase()==='guideline'; }
function isPaper(a){ return !isGuideline(a); }

function render(){
  var v = state.view, el = $('#view');
  var fn = {home:vHome, papers:vLib, guidelines:vLib, pearls:vPearls, trials:vTrials, theory:vTheory, cards:vCards, saved:vSaved}[v] || vHome;
  el.innerHTML = fn();
  (AFTER[v]||function(){})();
}
var AFTER = {};

function vHome(){
  var hr = new Date().getHours();
  var greet = hr<12?'Good morning':hr<17?'Good afternoon':'Good evening';
  var papers = D.articles.filter(isPaper), guides = D.articles.filter(isGuideline);
  var newest = D.articles.slice().sort(function(a,b){ return (b.date_added||'').localeCompare(a.date_added||''); });
  var pod = dayPick(papers, 3), tod = dayPick(D.trials, 7), pearl = D.pearl_of_day;
  var specs = count(D.articles,'system');
  var html = ''+
  '<section class="hero">'+
    '<div class="card hero-main">'+
      '<span class="eyebrow">'+esc(new Date().toLocaleDateString(undefined,{weekday:'long',day:'numeric',month:'long'}))+'</span>'+
      '<h1>'+greet+', '+esc(D.user.name)+'.<br><em>What are we learning</em> today?</h1>'+
      '<p>Critical-care papers, guidelines, trials and clinical pearls, distilled into quick, retainable reads.</p>'+
      '<button class="hero-search" data-act="palette">'+icon('i-search')+'<span>Try “vasopressin septic shock” or “ARDS prone”</span><span class="kbd">/</span></button>'+
    '</div>'+
    '<div class="stats">'+
      stat('papers', papers.length, 'Papers', 'Reviews, RCTs & meta-analyses', 'var(--accent)') + stat('guidelines', guides.length, 'Guidelines', 'Society recommendations', '#3A7CA5') +
      stat('pearls', D.pearl_count, 'Pearls', 'One-line takeaways', 'var(--amber)') + stat('trials', D.trials.length+D.condensed.length, 'Trials', 'Landmark ICU evidence', 'var(--coral)')+
    '</div>'+
  '</section>';

  html += '<h2 class="sec">On the unit today</h2><div class="daily">';
  if(pod) html += '<button class="card" data-open-article="'+esc(pod.id)+'">'+
    '<span class="eyebrow">Paper of the day</span>'+pill(pod.system, pod.type)+
    '<h3>'+esc(pod.title)+'</h3><div class="meta">'+esc(pod.journal)+' · '+esc(pod.authors)+'</div></button>';
  if(pearl) html += '<button class="card" data-go="pearls">'+
    '<span class="eyebrow">Pearl of the day</span>'+pill(pearl.system)+
    '<p class="quote">“'+mdi(trunc(pearl.pearl, 220))+'”</p><div class="meta">'+esc(trunc(pearl.source_paper,90))+'</div></button>';
  if(tod) html += '<button class="card" data-open-trial="'+esc(tod.slug)+'">'+
    '<span class="eyebrow">Trial of the day</span><div style="display:flex;gap:8px;flex-wrap:wrap">'+pill(tod.specialty)+'<span class="res '+resClass(tod.result_category)+'">'+esc(tod.result_category)+'</span></div>'+
    '<h3>'+esc(tod.trial_name)+'</h3><div class="meta">'+esc(trunc(tod.one_liner,140))+'</div></button>';
  html += '</div>';

  html += '<h2 class="sec">Browse by specialty <a class="link" href="#" data-go="papers">All papers →</a></h2><div class="spec-grid">';
  sortedKeys(specs).forEach(function(s){
    html += '<button class="spec" style="--c:'+color(s)+'" data-go="papers" data-spec="'+esc(s)+'"><span class="sw"><i></i></span><span><b>'+esc(s)+'</b><span class="sc">'+specs[s]+' reads</span></span></button>';
  });
  html += '</div>';

  html += '<h2 class="sec">Recently added <a class="link" href="#" data-go="papers">See all →</a></h2><div class="card list">';
  newest.slice(0,6).forEach(function(a){ html += articleRow(a); });
  html += '</div>';

  html += '<h2 class="sec">Building out next</h2><div class="roadmap">'+
    road('Antibiotics hub','Spectrum, dosing and renal adjustment for ICU antimicrobials.')+
    road('RRT companion','CRRT prescriptions, anticoagulation and troubleshooting.')+
    road('AI assistant','Ask questions grounded in the hack.CCM library.')+'</div>';
  return html;
}
function stat(go, n, l, h, c){ return '<button class="card stat" style="--sc:'+c+'" data-go="'+go+'"><span class="l">'+l+'</span><span><span class="n">'+Number(n).toLocaleString()+'</span><span class="h" style="display:block">'+h+'</span></span></button>'; }
function road(t, p){ return '<div class="card"><span class="eyebrow">Coming soon</span><b>'+t+'</b><p>'+p+'</p></div>'; }
function pill(s, extra){ return '<span class="pill"><span class="dot" style="--c:'+color(s)+'"></span>'+esc(s)+(extra?' · '+esc(extra):'')+'</span>'; }
function trunc(s,n){ s=String(s||''); return s.length>n? s.slice(0,n-1)+'…' : s; }

function articleRow(a){
  var saved = BM.items[(isGuideline(a)?'guideline:':'paper:')+a.file_name];
  return '<button class="row" style="--c:'+color(a.system)+'" data-open-article="'+esc(a.id)+'">'+
    '<span class="bar"></span><span><div class="t">'+esc(a.title)+'</div>'+
    '<div class="m"><span class="s">'+esc(a.system)+(a.subtopic && a.subtopic!==a.system?' › '+esc(a.subtopic):'')+'</span><span>'+esc(trunc(a.journal,48))+'</span>'+(a.year?'<span>'+esc(a.year)+'</span>':'')+'</div></span>'+
    '<span class="r"><span class="pill">'+esc(a.type)+'</span>'+(saved?'<span style="color:var(--accent)">'+icon('i-bookmark-f').replace('<svg>','<svg width="16" height="16">')+'</span>':'')+'</span></button>';
}

/* Library: papers + guidelines */
function vLib(){
  var L = state.lib, guide = state.view==='guidelines';
  var base = D.articles.filter(guide?isGuideline:isPaper);
  var specs = count(base,'system'), types = count(base,'type');
  if(L.spec && !specs[L.spec]) L.spec='';
  var html = '<span class="eyebrow">Library</span><h1 class="page-title">'+(guide?'Guidelines':'Papers')+'</h1>'+
    '<p class="page-sub">'+(guide?'Society and consensus guidelines, structured into recommendation-first summaries.':'Reviews, RCTs and meta-analyses, summarised for the bedside.')+'</p>'+
    '<div class="lib"><aside class="filters">'+
      '<div class="f-group"><h4>Specialty</h4><div class="f-list">'+
        fItem('spec','', 'All specialties', base.length, !L.spec)+
        sortedKeys(specs).map(function(s){ return fItem('spec', s, s, specs[s], L.spec===s); }).join('')+
      '</div></div>'+
      (guide?'':'<div class="f-group"><h4>Study type</h4><div class="f-list">'+
        fItem('type','', 'All types', base.length, !L.type)+
        sortedKeys(types).map(function(s){ return fItem('type', s, s, types[s], L.type===s); }).join('')+
      '</div></div>')+
    '</aside><div>'+
      '<div class="toolbar"><label class="input">'+icon('i-search')+'<input id="libQ" placeholder="Filter by title, journal, author or subtopic" value="'+esc(L.q)+'"></label>'+
      '<select class="sel" id="libSort" aria-label="Sort"><option value="new">Newest first</option><option value="az">Title A–Z</option><option value="year">Publication year</option></select></div>'+
      '<div id="libList"></div></div></div>';
  return html;
}
function fItem(k, v, label, n, on){
  return '<button class="f-item" data-f="'+k+'" data-v="'+esc(v)+'" aria-pressed="'+on+'">'+(k==='spec'&&v?'<span class="dot" style="--c:'+color(v)+'"></span>':'')+'<span>'+esc(label)+'</span><span class="c">'+n+'</span></button>';
}
AFTER.papers = AFTER.guidelines = function(){
  $('#libSort').value = state.lib.sort;
  $('#libQ').addEventListener('input', function(e){ state.lib.q=e.target.value; state.lib.limit=40; libList(); });
  $('#libSort').addEventListener('change', function(e){ state.lib.sort=e.target.value; libList(); });
  document.querySelectorAll('.f-item').forEach(function(b){ b.addEventListener('click', function(){
    state.lib[b.dataset.f]=b.dataset.v; state.lib.limit=40; render(); }); });
  libList();
};
function libList(){
  var L=state.lib, guide=state.view==='guidelines', q=L.q.toLowerCase().trim();
  var rows = D.articles.filter(guide?isGuideline:isPaper).filter(function(a){
    if(L.spec && a.system!==L.spec) return false;
    if(!guide && L.type && a.type!==L.type) return false;
    if(q){ var h=(a.title+' '+a.journal+' '+a.authors+' '+a.subtopic).toLowerCase(); return q.split(/\s+/).every(function(w){ return h.indexOf(w)>-1; }); }
    return true;
  });
  rows.sort(L.sort==='az'? function(a,b){ return a.title.localeCompare(b.title); } :
            L.sort==='year'? function(a,b){ return (b.year||'').localeCompare(a.year||''); } :
            function(a,b){ return (b.date_added||'').localeCompare(a.date_added||''); });
  var html = '<p class="result-count">'+rows.length+' result'+(rows.length===1?'':'s')+'</p>';
  html += rows.length? '<div class="card list">'+rows.slice(0,L.limit).map(articleRow).join('')+'</div>' : '<div class="card empty">Nothing matches. Try a broader term.</div>';
  if(rows.length>L.limit) html += '<div class="more"><button class="btn" id="libMore">Show more ('+(rows.length-L.limit)+' left)</button></div>';
  $('#libList').innerHTML = html;
  var m=$('#libMore'); if(m) m.onclick=function(){ L.limit+=40; libList(); };
}

/* Pearls */
function vPearls(){
  var P=state.pearls, sys=D.pearl_systems;
  var html='<span class="eyebrow">Library</span><h1 class="page-title">Clinical pearls</h1>'+
    '<p class="page-sub">'+Number(D.pearl_count).toLocaleString()+' one-line takeaways extracted from every paper and guideline. Turn on recall mode to test yourself.</p>'+
    '<div class="toolbar"><label class="input">'+icon('i-search')+'<input id="pQ" placeholder="Search pearls" value="'+esc(P.q)+'"></label>'+
    '<select class="sel" id="pSys" aria-label="Specialty"><option value="">All specialties</option>'+sortedKeys(sys).map(function(s){ return '<option'+(P.system===s?' selected':'')+' value="'+esc(s)+'">'+esc(s)+' ('+sys[s]+')</option>'; }).join('')+'</select>'+
    '<button class="btn'+(P.recall?' saved':'')+'" id="pRecall" aria-pressed="'+P.recall+'">'+icon('i-eye')+'Recall mode</button></div>'+
    '<p class="result-count" id="pCount"></p><div class="pearls'+(P.recall?' recall':'')+'" id="pGrid"></div><div class="more" id="pMore"></div>';
  return html;
}
AFTER.pearls = function(){
  var P=state.pearls, t=null;
  $('#pQ').addEventListener('input', function(e){ clearTimeout(t); t=setTimeout(function(){ P.q=e.target.value; loadPearls(true); }, 220); });
  $('#pSys').addEventListener('change', function(e){ P.system=e.target.value; loadPearls(true); });
  $('#pRecall').addEventListener('click', function(){ P.recall=!P.recall; render(); });
  $('#pGrid').addEventListener('click', function(e){
    var s=e.target.closest('.save'); if(s){ toggleBM(s.dataset.ref, JSON.parse(s.dataset.meta)).then(function(){ s.classList.toggle('on', !!BM.items[s.dataset.ref]); s.innerHTML=icon(BM.items[s.dataset.ref]?'i-bookmark-f':'i-bookmark'); }); return; }
    var p=e.target.closest('.pearl'); if(p && P.recall) p.classList.toggle('revealed');
  });
  if(P.items.length) drawPearls(); else loadPearls(true);
};
function loadPearls(reset){
  var P=state.pearls; if(reset){ P.page=1; P.items=[]; }
  var u='/api/pearls?limit=36&page='+P.page+'&q='+encodeURIComponent(P.q)+'&system='+encodeURIComponent(P.system);
  api(u).then(function(r){ P.items=P.items.concat(r.pearls||[]); P.total=r.total||0; P.pages=r.totalPages||1; drawPearls(); });
}
function drawPearls(){
  var P=state.pearls; if(!$('#pGrid')) return;
  $('#pCount').textContent = P.total.toLocaleString()+' pearls';
  $('#pGrid').innerHTML = P.items.length? P.items.map(function(p){
    var ref='pearl:'+p.id, on=!!BM.items[ref];
    var meta=JSON.stringify({kind:'pearl',title:trunc(p.pearl,120),system:p.system||'',type:p.type||''});
    return '<article class="card pearl" style="--c:'+color(p.system)+'"><p>'+mdi(p.pearl)+'</p>'+
      '<div class="src"><span>'+pill(p.system)+'<br><span style="display:block;margin-top:8px">'+esc(trunc(p.source_paper,110))+'</span></span>'+
      '<button class="save'+(on?' on':'')+'" data-ref="'+esc(ref)+'" data-meta="'+esc(meta)+'" aria-label="Save pearl">'+icon(on?'i-bookmark-f':'i-bookmark')+'</button></div></article>';
  }).join('') : '<div class="card empty">No pearls match.</div>';
  $('#pMore').innerHTML = P.page<P.pages ? '<button class="btn" id="pMoreBtn">Load more pearls</button>' : '';
  var m=$('#pMoreBtn'); if(m) m.onclick=function(){ P.page++; loadPearls(false); };
}

/* Trials */
function vTrials(){
  var T=state.trials, hasC=D.features.condensed_trials && D.condensed.length;
  var src = T.src==='condensed' && hasC ? D.condensed : D.trials;
  var specKey = T.src==='condensed'?'system':'specialty';
  var specs=count(src, specKey), res=count(src,'result_category');
  var html='<span class="eyebrow">Evidence</span><h1 class="page-title">Landmark trials</h1>'+
    '<p class="page-sub">The trials that shaped ICU practice — design, result and the one line to remember.</p>'+
    (hasC?'<div class="tabs" role="tablist"><button class="tab" data-tsrc="esbicm" aria-selected="'+(T.src!=='condensed')+'">ESBICM collection · '+D.trials.length+'</button><button class="tab" data-tsrc="condensed" aria-selected="'+(T.src==='condensed')+'">Condensed database · '+D.condensed.length+'</button></div>':'')+
    '<div class="toolbar"><label class="input">'+icon('i-search')+'<input id="tQ" placeholder="Trial name, keyword or one-liner" value="'+esc(T.q)+'"></label>'+
    '<select class="sel" id="tSpec" aria-label="Area"><option value="">All areas</option>'+sortedKeys(specs).map(function(s){ return '<option'+(T.spec===s?' selected':'')+' value="'+esc(s)+'">'+esc(s)+' ('+specs[s]+')</option>'; }).join('')+'</select></div>'+
    '<div class="chips" style="margin-bottom:16px">'+['', ].concat(sortedKeys(res)).map(function(r){ return '<button class="chip" data-tres="'+esc(r)+'" aria-pressed="'+(T.res===r)+'">'+(r?'<span class="res '+resClass(r)+'" style="padding:2px 6px">●</span>'+esc(r)+' · '+res[r]:'All results')+'</button>'; }).join('')+'</div>'+
    '<div id="tList"></div>';
  return html;
}
AFTER.trials = function(){
  var T=state.trials;
  document.querySelectorAll('[data-tsrc]').forEach(function(b){ b.onclick=function(){ T.src=b.dataset.tsrc; T.spec=''; T.res=''; T.limit=40; render(); }; });
  document.querySelectorAll('[data-tres]').forEach(function(b){ b.onclick=function(){ T.res=b.dataset.tres; T.limit=40; render(); }; });
  $('#tQ').addEventListener('input', function(e){ T.q=e.target.value; T.limit=40; tList(); });
  $('#tSpec').addEventListener('change', function(e){ T.spec=e.target.value; T.limit=40; tList(); });
  tList();
};
function tList(){
  var T=state.trials, cond=T.src==='condensed', q=T.q.toLowerCase().trim();
  var src=(cond?D.condensed:D.trials).filter(function(t){
    var sp=cond?t.system:t.specialty;
    if(T.spec && sp!==T.spec) return false;
    if(T.res && t.result_category!==T.res) return false;
    if(q){ var h=(t.trial_name+' '+(t.one_liner||'')+' '+(t.keywords_str||'')+' '+(t.journal||'')).toLowerCase(); return q.split(/\s+/).every(function(w){ return h.indexOf(w)>-1; }); }
    return true;
  }).sort(function(a,b){ return (b.year||0)-(a.year||0); });
  var html='<p class="result-count">'+src.length+' trials</p>';
  html += src.length? '<div class="card list">'+src.slice(0,T.limit).map(function(t){
    var sp=cond?t.system:t.specialty, attr=cond?'data-open-cond="'+esc(t.system)+'|'+esc(t.name)+'"':'data-open-trial="'+esc(t.slug)+'"';
    return '<button class="row" style="--c:'+color(sp)+'" '+attr+'><span class="bar"></span><span><div class="t">'+esc(t.trial_name)+'</div>'+
      (t.one_liner?'<div class="one">'+esc(t.one_liner)+'</div>':'')+
      '<div class="m"><span class="s">'+esc(sp)+'</span>'+(t.trial_type?'<span>'+esc(trunc(t.trial_type,40))+'</span>':'')+(t.sample_size?'<span>n = '+Number(t.sample_size).toLocaleString()+'</span>':'')+(t.year?'<span>'+t.year+'</span>':'')+'</div></span>'+
      '<span class="r"><span class="res '+resClass(t.result_category)+'">'+esc(t.result_category||'—')+'</span></span></button>';
  }).join('')+'</div>' : '<div class="card empty">No trials match.</div>';
  if(src.length>T.limit) html+='<div class="more"><button class="btn" id="tMore">Show more ('+(src.length-T.limit)+' left)</button></div>';
  $('#tList').innerHTML=html; var m=$('#tMore'); if(m) m.onclick=function(){ T.limit+=40; tList(); };
}

/* Theory notes */
function vTheory(){
  var Th=state.theory, specs=count(D.notes,'system');
  return '<span class="eyebrow">Study</span><h1 class="page-title">Theory topics</h1>'+
    '<p class="page-sub">Long-form notes on core critical-care concepts — read like a textbook chapter, built for revision.</p>'+
    '<div class="toolbar"><label class="input">'+icon('i-search')+'<input id="nQ" placeholder="Search topics" value="'+esc(Th.q)+'"></label></div>'+
    '<div class="chips" style="margin-bottom:18px">'+fChip('', 'All', D.notes.length, !Th.spec)+sortedKeys(specs).map(function(s){ return fChip(s, s, specs[s], Th.spec===s); }).join('')+'</div>'+
    '<div id="nList"></div>';
}
function fChip(v,l,n,on){ return '<button class="chip" data-nspec="'+esc(v)+'" aria-pressed="'+on+'">'+(v?'<span class="dot" style="--c:'+color(v)+'"></span>':'')+esc(l)+' <span class="mono" style="opacity:.6;font-size:11px">'+n+'</span></button>'; }
AFTER.theory=function(){
  var Th=state.theory;
  document.querySelectorAll('[data-nspec]').forEach(function(b){ b.onclick=function(){ Th.spec=b.dataset.nspec; render(); }; });
  $('#nQ').addEventListener('input', function(e){ Th.q=e.target.value; nList(); });
  nList();
};
function nList(){
  var Th=state.theory, q=Th.q.toLowerCase();
  var rows=D.notes.filter(function(n){ return (!Th.spec||n.system===Th.spec) && (!q || (n.title+' '+(n.subtopic||'')).toLowerCase().indexOf(q)>-1); })
    .sort(function(a,b){ return a.title.localeCompare(b.title); });
  $('#nList').innerHTML = rows.length? '<div class="card list">'+rows.map(function(n){
    return '<button class="row" style="--c:'+color(n.system)+'" data-open-note="'+esc(n.id)+'"><span class="bar"></span><span><div class="t">'+esc(n.title)+'</div><div class="m"><span class="s">'+esc(n.system||'General')+'</span>'+(n.subtopic?'<span>'+esc(n.subtopic)+'</span>':'')+'</div></span><span class="r">'+(BM.items['note:'+n.id]?'<span style="color:var(--accent)">●</span>':'')+'</span></button>';
  }).join('')+'</div>' : '<div class="card empty">No topics match.</div>';
}

/* Flashcards */
function vCards(){
  if(state.study) return vStudy();
  return '<span class="eyebrow">Study</span><h1 class="page-title">Flashcards</h1>'+
    '<p class="page-sub">Active recall decks, one per subtopic. Tap a card to flip; use ← → and space on a keyboard.</p>'+
    '<div class="decks">'+D.decks.map(function(d,i){
      return '<button class="card deck" style="--c:'+color(d.specialty)+'" data-deck="'+i+'">'+pill(d.specialty)+'<h3>'+esc(d.title)+'</h3>'+
        '<div class="meta"><span>'+d.cards.length+' cards</span><span>'+((d.subtopics||[]).length)+' subtopics</span></div></button>';
    }).join('')+'</div>';
}
function vStudy(){
  var S=state.study, d=D.decks[S.deck], c=d.cards[S.order[S.i]];
  return '<div class="study"><div class="study-head"><button class="btn" data-act="endStudy">'+icon('i-left')+'Decks</button>'+
    '<div><span class="eyebrow">'+esc(d.specialty)+'</span><div class="serif" style="font-size:22px">'+esc(d.title)+'</div></div>'+
    '<button class="btn" data-act="shuffle" style="margin-left:auto">'+icon('i-shuffle')+'Shuffle</button></div>'+
    '<div class="progress"><i style="width:'+((S.i+1)/S.order.length*100)+'%"></i></div>'+
    '<div class="flip'+(S.flipped?' on':'')+'" id="flip" role="button" tabindex="0" aria-label="Flip card">'+
      '<div class="flip-in"><div class="card face front"><span class="eyebrow" style="margin-bottom:18px">'+esc(c.subtopic||'Question')+'</span><div class="q">'+esc(c.front||'Recall the key points')+'</div><span class="hint">tap or press space to reveal</span></div>'+
      '<div class="card face back"><span class="eyebrow" style="margin-bottom:6px">Answer</span><div class="prose">'+md(c.back)+'</div></div></div></div>'+
    '<div class="study-nav"><button class="icon-btn" data-act="prev" aria-label="Previous">'+icon('i-left')+'</button>'+
    '<span class="mono" style="color:var(--muted);min-width:90px;text-align:center">'+(S.i+1)+' / '+S.order.length+'</span>'+
    '<button class="icon-btn" data-act="next" aria-label="Next">'+icon('i-right')+'</button>'+
    '<button class="btn" data-act="saveCard" style="margin-left:14px">'+icon(BM.items['flashcard:'+c.id]?'i-bookmark-f':'i-bookmark')+(BM.items['flashcard:'+c.id]?'Saved':'Save')+'</button></div></div>';
}
AFTER.cards=function(){
  document.querySelectorAll('[data-deck]').forEach(function(b){ b.onclick=function(){ var d=D.decks[+b.dataset.deck]; state.study={deck:+b.dataset.deck,i:0,flipped:false,order:d.cards.map(function(_,i){return i;})}; render(); }; });
  var f=$('#flip'); if(f){ f.onclick=function(){ state.study.flipped=!state.study.flipped; f.classList.toggle('on'); }; mathify(f); }
};
ACT.endStudy=function(){ state.study=null; render(); };
ACT.next=function(){ var S=state.study; if(S && S.i<S.order.length-1){ S.i++; S.flipped=false; render(); } };
ACT.prev=function(){ var S=state.study; if(S && S.i>0){ S.i--; S.flipped=false; render(); } };
ACT.shuffle=function(){ var S=state.study; for(var i=S.order.length-1;i>0;i--){ var j=Math.floor(Math.random()*(i+1)); var t=S.order[i]; S.order[i]=S.order[j]; S.order[j]=t; } S.i=0; S.flipped=false; render(); };
ACT.saveCard=function(){ var S=state.study, d=D.decks[S.deck], c=d.cards[S.order[S.i]];
  toggleBM('flashcard:'+c.id,{kind:'flashcard',title:c.front||d.title,system:d.specialty,type:'Flashcard',locator:{deck:d.id,card:c.id,cardIdx:S.order[S.i]}}).then(render); };
ACT.palette=function(){ openPalette(); };

/* Saved */
function vSaved(){
  var items=Object.keys(BM.items||{}).map(function(k){ return BM.items[k]; }).sort(function(a,b){ return (b.added_at||'').localeCompare(a.added_at||''); });
  var label={paper:'Papers',guideline:'Guidelines',pearl:'Pearls',trial:'Trials',condensed:'Condensed trials',flashcard:'Flashcards',note:'Theory notes'};
  var html='<span class="eyebrow">Your library</span><h1 class="page-title">Saved</h1><p class="page-sub">Everything you bookmarked, synced to your account.</p>';
  if(!items.length) return html+'<div class="card empty">Nothing saved yet. Use the bookmark button in any reader.</div>';
  Object.keys(label).forEach(function(k){
    var g=items.filter(function(i){ return i.kind===k; }); if(!g.length) return;
    html+='<h2 class="sec">'+label[k]+' <span class="mono" style="font-size:13px;color:var(--muted)">'+g.length+'</span></h2><div class="card list">'+g.map(function(i){
      return '<button class="row" style="--c:'+color(i.system)+'" data-open-ref="'+esc(i.ref)+'"><span class="bar"></span><span><div class="t">'+esc(i.title)+'</div><div class="m"><span class="s">'+esc(i.system||'')+'</span><span>'+esc(fmtDate(i.added_at))+'</span></div></span><span class="r"><span class="pill">'+esc(i.type||k)+'</span></span></button>';
    }).join('')+'</div>';
  });
  return html;
}

/* ---------------- Reader ---------------- */
function openReader(top, body){
  $('#readerTop').innerHTML = top + '<button class="icon-btn" data-act="closeReader" aria-label="Close" style="margin-left:auto">'+icon('i-x')+'</button>';
  $('#readerBody').innerHTML = body; $('#readerBody').scrollTop=0;
  $('#reader').classList.add('on'); $('#scrim').classList.add('on');
  mathify($('#readerBody'));
}
function closeReader(){ $('#reader').classList.remove('on'); $('#scrim').classList.remove('on'); }
ACT.closeReader=closeReader; $('#scrim').onclick=function(){ closeReader(); closePalette(); };
function loading(){ return '<div class="empty">Loading…</div>'; }
function bmBtn(ref, meta){
  var on=!!BM.items[ref];
  return '<button class="btn'+(on?' saved':'')+'" data-bm="'+esc(ref)+'" data-meta="'+esc(JSON.stringify(meta))+'">'+icon(on?'i-bookmark-f':'i-bookmark')+(on?'Saved':'Save')+'</button>';
}
document.addEventListener('click', function(e){
  var b=e.target.closest('[data-bm]'); if(b){ toggleBM(b.dataset.bm, JSON.parse(b.dataset.meta)).then(function(){ var on=!!BM.items[b.dataset.bm]; b.classList.toggle('saved',on); b.innerHTML=icon(on?'i-bookmark-f':'i-bookmark')+(on?'Saved':'Save'); renderNav(); }); return; }
  var a=e.target.closest('[data-open-article]'); if(a){ openArticle(D.articles.find(function(x){ return x.id===a.dataset.openArticle; })); return; }
  var t=e.target.closest('[data-open-trial]'); if(t){ openTrial(t.dataset.openTrial); return; }
  var c=e.target.closest('[data-open-cond]'); if(c){ var p=c.dataset.openCond.split('|'); openCond(p[0],p[1]); return; }
  var n=e.target.closest('[data-open-note]'); if(n){ openNote(n.dataset.openNote); return; }
  var r=e.target.closest('[data-open-ref]'); if(r){ openRef(r.dataset.openRef); return; }
});

function openArticle(a){
  if(!a) return;
  var kind=isGuideline(a)?'guideline':'paper', ref=kind+':'+a.file_name;
  var top = bmBtn(ref,{kind:kind,title:a.title,system:a.system,type:a.type,locator:{file_name:a.file_name,system:a.system,type:a.type}})+
    (a.doi?'<a class="btn" href="'+esc(a.doi)+'" target="_blank" rel="noopener">'+icon('i-ext')+'Source</a>':'')+
    '<a class="btn" href="/export/print?kind=paper&file_name='+encodeURIComponent(a.file_name)+'&title='+encodeURIComponent(a.title)+'" target="_blank">'+icon('i-print')+'Print</a>';
  var head = pill(a.system, a.subtopic!==a.system?a.subtopic:'')+' <span class="pill">'+esc(a.type)+'</span><h1 class="rt">'+esc(a.title)+'</h1>'+
    '<div class="reader-meta"><span>'+esc(a.journal)+'</span>'+(a.year?'<span>'+esc(a.year)+'</span>':'')+'<span id="rAuth">'+esc(a.authors)+'</span></div>';
  openReader(top, head+loading());
  api('/api/summary?file_name='+encodeURIComponent(a.file_name)+'&system='+encodeURIComponent(a.system)+'&type='+encodeURIComponent(a.type)).then(function(d){
    if(d.error){ $('#readerBody').innerHTML=head+'<div class="card empty">'+esc(d.error)+'</div>'; return; }
    var pearls=(d.key_pearls||[]).filter(Boolean);
    $('#readerBody').innerHTML = head +
      (pearls.length?'<div class="callout"><span class="eyebrow">Key pearls</span><ul>'+pearls.slice(0,5).map(function(p){ return '<li>'+mdi(p)+'</li>'; }).join('')+'</ul></div>':'')+
      '<div class="prose">'+md(d.content)+'</div>';
    mathify($('#readerBody'));
  });
}
function trialKV(t){
  var kv=[['Design',t.trial_type],['Sample',t.sample_size?Number(t.sample_size).toLocaleString():''],['Year',t.year],['Evidence',t.evidence_level],['Journal',t.journal]];
  if(t.key_stats) Object.keys(t.key_stats).forEach(function(k){ kv.push([k.replace(/_/g,' '), t.key_stats[k]]); });
  return '<div class="kv">'+kv.filter(function(x){ return x[1]; }).map(function(x){ return '<div><b>'+esc(x[0])+'</b><span>'+esc(trunc(x[1],60))+'</span></div>'; }).join('')+'</div>';
}
function openTrial(slug){
  var t=D.trials.find(function(x){ return x.slug===slug; })||{trial_name:slug};
  openReader('', '<h1 class="rt">'+esc(t.trial_name)+'</h1>'+loading());
  api('/api/trial/'+encodeURIComponent(slug)).then(function(d){
    if(d.error||d.detail){ $('#readerBody').innerHTML='<div class="card empty">'+esc(d.error||d.detail)+'</div>'; return; }
    var ref='trial:'+slug;
    $('#readerTop').innerHTML = bmBtn(ref,{kind:'trial',title:d.trial_name,system:d.specialty||'General',type:d.trial_type||'Trial',locator:{slug:slug}})+
      (d.doi?'<a class="btn" href="'+esc(_doi(d.doi))+'" target="_blank" rel="noopener">'+icon('i-ext')+'Source</a>':'')+
      '<button class="icon-btn" data-act="closeReader" aria-label="Close" style="margin-left:auto">'+icon('i-x')+'</button>';
    var secs=(d.sections||[]).map(function(s){ return '<h2>'+esc(s.heading)+'</h2>'+md(bulletize(s.content)); }).join('');
    $('#readerBody').innerHTML = pill(d.specialty, d.subtopic!=='General'?d.subtopic:'')+' <span class="res '+resClass(d.result_category)+'">'+esc(d.result_category)+'</span>'+
      '<h1 class="rt">'+esc(d.trial_name)+'</h1><div class="reader-meta"><span>'+esc(d.primary_author||'')+'</span><span>'+esc(d.published||'')+'</span></div>'+
      '<div class="callout"><span class="eyebrow">Bottom line</span><div class="serif" style="font-size:18px">'+esc(d.one_liner)+'</div></div>'+trialKV(d)+
      '<div class="prose">'+secs+'</div>';
  });
}
function _doi(x){ x=String(x||''); return /^https?:/.test(x)?x:'https://doi.org/'+x; }
function bulletize(s){ return String(s||'').replace(/^\s*•\s*\n?/gm,'- ').replace(/\n(?!\s*-)/g,' ').replace(/ - /g,'\n- '); }
function openCond(system, name){
  openReader('', loading());
  api('/api/condensed-trial/'+encodeURIComponent(system)+'/'+encodeURIComponent(name)).then(function(d){
    if(d.error||d.detail){ $('#readerBody').innerHTML='<div class="card empty">'+esc(d.error||d.detail)+'</div>'; return; }
    var ref='condensed:'+system+':'+name;
    $('#readerTop').innerHTML = bmBtn(ref,{kind:'condensed',title:d.trial_name,system:system,type:'Trial',locator:{system:system,name:name}})+
      (d.doi?'<a class="btn" href="'+esc(_doi(d.doi))+'" target="_blank" rel="noopener">'+icon('i-ext')+'Source</a>':'')+
      '<button class="icon-btn" data-act="closeReader" aria-label="Close" style="margin-left:auto">'+icon('i-x')+'</button>';
    var body='';
    if(d.pico){ body+='<h2>PICO</h2><table><tbody>'+Object.keys(d.pico).map(function(k){ return '<tr><th>'+esc(k)+'</th><td>'+esc(d.pico[k])+'</td></tr>'; }).join('')+'</tbody></table>'; }
    var S=d.sections||{};
    Object.keys(S).forEach(function(k){ var v=S[k]; body+='<h2>'+esc(k.replace(/_/g,' ').replace(/\b\w/g,function(c){return c.toUpperCase();}))+'</h2>'+renderAny(v); });
    $('#readerBody').innerHTML = pill(d.specialty||system, d.subtopic)+' <span class="res '+resClass(d.result_category)+'">'+esc(d.result_category)+'</span><h1 class="rt">'+esc(d.trial_name)+'</h1>'+
      '<div class="reader-meta"><span>'+esc(trunc(d.citation||'',160))+'</span></div><div class="callout"><span class="eyebrow">Bottom line</span><div class="serif" style="font-size:18px">'+esc(d.one_liner)+'</div></div>'+trialKV(d)+'<div class="prose">'+body+'</div>';
  });
}
function renderAny(v){
  if(v==null||v==='') return '';
  if(typeof v==='string') return md(v);
  if(Array.isArray(v)) return '<ul>'+v.map(function(x){ return '<li>'+(typeof x==='object'?renderAny(x):esc(x))+'</li>'; }).join('')+'</ul>';
  if(typeof v==='object') return Object.keys(v).map(function(k){ var x=v[k]; if(x==null||x===''||(Array.isArray(x)&&!x.length)) return ''; return '<h4>'+esc(k.replace(/_/g,' '))+'</h4>'+renderAny(x); }).join('');
  return '<p>'+esc(v)+'</p>';
}
function openNote(id){
  var n=D.notes.find(function(x){ return x.id===id; })||{title:id};
  openReader('', '<h1 class="rt">'+esc(n.title)+'</h1>'+loading());
  api('/api/redefined/note?id='+encodeURIComponent(id)).then(function(d){
    var ref='note:'+id;
    $('#readerTop').innerHTML = bmBtn(ref,{kind:'note',title:n.title,system:n.system||'',type:'Theory',locator:{note:id}})+
      '<a class="btn" href="/export/print?kind=note&file_name='+encodeURIComponent(id)+'&title='+encodeURIComponent(n.title)+'" target="_blank">'+icon('i-print')+'Print</a>'+
      '<button class="icon-btn" data-act="closeReader" aria-label="Close" style="margin-left:auto">'+icon('i-x')+'</button>';
    var body=String(d.md||'').replace(/^\s*#\s+.*\n/, '');
    $('#readerBody').innerHTML = pill(n.system||'General', n.subtopic)+'<h1 class="rt">'+esc(n.title)+'</h1><div class="prose">'+md(body)+'</div>';
    mathify($('#readerBody'));
  });
}
function openRef(ref){
  var i=ref.indexOf(':'), k=ref.slice(0,i), v=ref.slice(i+1);
  if(k==='paper'||k==='guideline'){ openArticle(D.articles.find(function(a){ return a.file_name===v; })); }
  else if(k==='trial') openTrial(v);
  else if(k==='condensed'){ var j=v.indexOf(':'); openCond(v.slice(0,j), v.slice(j+1)); }
  else if(k==='note') openNote(v);
  else if(k==='pearl'){ var it=BM.items[ref]; openReader('', pill(it.system)+'<h1 class="rt">Saved pearl</h1><div class="prose"><p>'+esc(it.title)+'</p></div>'); }
  else if(k==='flashcard'){ var loc=(BM.items[ref]||{}).locator||{}; var di=D.decks.findIndex(function(d){ return d.id===loc.deck; }); if(di>-1){ var d=D.decks[di]; var ci=d.cards.findIndex(function(c){ return c.id===v; }); state.study={deck:di,i:Math.max(ci,0),flipped:false,order:d.cards.map(function(_,i){return i;})}; go('cards'); } }
}

/* ---------------- Bookmarks ---------------- */
function loadBM(){ if(!D.features.bookmarks) return Promise.resolve(); return api('/api/bookmarks').then(function(r){ BM=r&&r.items?r:{items:{},folders:{}}; renderNav(); }).catch(function(){}); }
function toggleBM(ref, meta){
  if(BM.items[ref]) return fetch('/api/bookmarks?ref='+encodeURIComponent(ref),{method:'DELETE',credentials:'same-origin'}).then(function(){ delete BM.items[ref]; renderNav(); });
  return fetch('/api/bookmarks',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.assign({ref:ref},meta))})
    .then(function(r){ return r.json(); }).then(function(r){ if(r.item) BM.items[ref]=r.item; renderNav(); });
}

/* ---------------- Command palette ---------------- */
var palSel=0, palItems=[];
function openPalette(){ $('#palette').classList.add('on'); $('#scrim').classList.add('on'); $('#palInput').value=''; palSearch(''); setTimeout(function(){ $('#palInput').focus(); },30); }
function closePalette(){ $('#palette').classList.remove('on'); if(!$('#reader').classList.contains('on')) $('#scrim').classList.remove('on'); }
$('#openPalette').onclick=openPalette;
var palT=null;
$('#palInput').addEventListener('input', function(e){ clearTimeout(palT); var q=e.target.value; palT=setTimeout(function(){ palSearch(q); },120); });
function score(h, words){ h=h.toLowerCase(); var s=0; for(var i=0;i<words.length;i++){ var k=h.indexOf(words[i]); if(k<0) return 0; s+= k===0?3:1; } return s; }
function palSearch(q){
  var words=q.toLowerCase().trim().split(/\s+/).filter(Boolean), groups=[];
  if(!words.length){
    groups.push({g:'Jump to', items:NAV.filter(function(n){ return n.id && (!n.feat||D.features[n.feat]); }).map(function(n){ return {t:n.label, s:'', run:function(){ go(n.id); }}; })});
  } else {
    var take=function(arr, fn, lim){ return arr.map(function(x){ return [score(fn(x),words),x]; }).filter(function(p){ return p[0]; }).sort(function(a,b){ return b[0]-a[0]; }).slice(0,lim).map(function(p){ return p[1]; }); };
    var arts=take(D.articles, function(a){ return a.title+' '+a.subtopic+' '+a.system; }, 6);
    if(arts.length) groups.push({g:'Papers & guidelines', items:arts.map(function(a){ return {t:a.title, s:a.system+' · '+a.type, run:function(){ openArticle(a); }}; })});
    var tr=take(D.trials, function(t){ return t.trial_name+' '+t.one_liner; }, 5);
    if(tr.length) groups.push({g:'Trials', items:tr.map(function(t){ return {t:t.trial_name, s:t.result_category, run:function(){ openTrial(t.slug); }}; })});
    var nt=take(D.notes, function(n){ return n.title+' '+(n.subtopic||''); }, 4);
    if(nt.length) groups.push({g:'Theory', items:nt.map(function(n){ return {t:n.title, s:n.system||'', run:function(){ openNote(n.id); }}; })});
    var dk=take(D.decks, function(d){ return d.title+' '+d.specialty+' '+(d.subtopics||[]).join(' '); }, 3);
    if(dk.length) groups.push({g:'Flashcard decks', items:dk.map(function(d){ return {t:d.title, s:d.cards.length+' cards', run:function(){ var i=D.decks.indexOf(d); state.study={deck:i,i:0,flipped:false,order:d.cards.map(function(_,i){return i;})}; go('cards'); }}; })});
    if(D.features.pearls) groups.push({g:'Pearls', items:[{t:'Search pearls for “'+q+'”', s:'↵', run:function(){ state.pearls.q=q; state.pearls.items=[]; go('pearls'); }}]});
  }
  palItems=[]; var html='';
  groups.forEach(function(g){ html+='<div class="pal-group">'+g.g+'</div>'; g.items.forEach(function(it){ html+='<button class="pal-item" role="option" data-pi="'+palItems.length+'"><span class="pt">'+esc(it.t)+'</span><span class="ps">'+esc(it.s)+'</span></button>'; palItems.push(it); }); });
  $('#palRes').innerHTML = html || '<div class="empty">No matches.</div>';
  palSel=0; palMark();
}
function palMark(){ document.querySelectorAll('.pal-item').forEach(function(b,i){ b.setAttribute('aria-selected', i===palSel); if(i===palSel) b.scrollIntoView({block:'nearest'}); }); }
$('#palRes').addEventListener('click', function(e){ var b=e.target.closest('.pal-item'); if(b){ var it=palItems[+b.dataset.pi]; closePalette(); it.run(); } });
document.addEventListener('keydown', function(e){
  var inField = /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName);
  if((e.key==='k'&&(e.metaKey||e.ctrlKey)) || (e.key==='/'&&!inField)){ e.preventDefault(); openPalette(); return; }
  if($('#palette').classList.contains('on')){
    if(e.key==='Escape') closePalette();
    else if(e.key==='ArrowDown'){ e.preventDefault(); palSel=Math.min(palSel+1, palItems.length-1); palMark(); }
    else if(e.key==='ArrowUp'){ e.preventDefault(); palSel=Math.max(palSel-1,0); palMark(); }
    else if(e.key==='Enter' && palItems[palSel]){ var it=palItems[palSel]; closePalette(); it.run(); }
    return;
  }
  if(e.key==='Escape'){ closeReader(); closeModal(); return; }
  if(state.view==='cards' && state.study && !inField){
    if(e.key==='ArrowRight') ACT.next(); else if(e.key==='ArrowLeft') ACT.prev();
    else if(e.key===' '){ e.preventDefault(); var f=$('#flip'); if(f){ state.study.flipped=!state.study.flipped; f.classList.toggle('on'); } }
  }
});

/* ---------------- Modal ---------------- */
function modal(html, buttons){
  $('#modalBody').innerHTML=html;
  $('#modalFoot').innerHTML=(buttons||[]).map(function(b,i){ return '<button class="btn'+(i===buttons.length-1?' primary':'')+'" data-mb="'+i+'">'+b[0]+'</button>'; }).join('');
  $('#modal').classList.add('on');
  $('#modalFoot').onclick=function(e){ var b=e.target.closest('[data-mb]'); if(!b) return; var fn=buttons[+b.dataset.mb][1]; closeModal(); if(typeof fn==='function') fn(); };
}
function closeModal(){ $('#modal').classList.remove('on'); }

/* ---------------- Theme / chrome ---------------- */
function syncTheme(){ var dark=document.documentElement.dataset.theme==='dark'; $('#themeBtn').innerHTML=icon(dark?'i-sun':'i-moon'); }
$('#themeBtn').onclick=function(){ var t=document.documentElement.dataset.theme==='dark'?'light':'dark'; document.documentElement.dataset.theme=t; localStorage.setItem('hc2-theme',t); syncTheme(); };
$('#avatar').onclick=function(){ modal('<h2 style="margin-top:0">'+esc(D.user.name)+'</h2><p class="mono" style="color:var(--muted)">'+esc(D.user.email)+'</p>'+
  '<p><a href="'+esc(D.links.subscribe)+'" target="_blank" rel="noopener">Subscribe to the email digest</a> · <a href="'+esc(D.links.unsubscribe)+'" target="_blank" rel="noopener">Unsubscribe</a></p>',
  [['Sign out', ACT.logout],['Close','']]); };
window.addEventListener('scroll', function(){ $('#topbar').classList.toggle('scrolled', scrollY>4); }, {passive:true});

/* ---------------- Boot ---------------- */
syncTheme();
api('/api/redefined/bootstrap').then(function(d){
  D=d;
  if(D.local_dev) $('#logoutBtn').style.display='none';
  $('#avatar').textContent=(D.user.name||'?').charAt(0).toUpperCase();
  var v=new URL(location).searchParams.get('v'); if(v) state.view=v;
  renderNav(); render(); loadBM();
  if(D.disclaimer && !localStorage.getItem('hc2-disclaimer-ok')){
    modal(md(D.disclaimer), [['I understand — proceed', function(){ localStorage.setItem('hc2-disclaimer-ok','1'); }]]);
  }
});
})();
</script>
</body>
</html>
"""
