import os
import json
import re
from fastapi import FastAPI, Request
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
# DATA LOADERS
# =====================================================================

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
async def render_dashboard(request: Request):
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

    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dim">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>hack.CCM — Knowledge Portal</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Atkinson+Hyperlegible:wght@400;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script defer src="/_vercel/insights/script.js"></script>
{ECG_SVG}
<style>
  :root{{
    --font-display:'Space Grotesk',sans-serif;
    --font-body:'Atkinson Hyperlegible',sans-serif;
    --font-mono:'JetBrains Mono',monospace;
    {spec_css_str}
    {trial_spec_str}
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
    </nav>
    <div class="header-actions">
      <button class="icon-btn" id="searchTrigger" aria-label="Search">&#128269;</button>
      <button class="icon-btn theme-btn" id="themeBtn" aria-label="Change theme">&#9712;</button>
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
  <section class="view" id="view-theory">
    <div class="coming-soon">
      <p class="coming-soon-icon">&#128679;</p>
      <h2>Coming Soon</h2>
      <p class="coming-soon-text">The Theory Library is under development. Check back soon.</p>
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

let _trialFilterState = {{ specialty: '', result_category: '', trial_type: '' }};
let _currentTrialList = [];
let _currentTrialIdx = -1;

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
    body.innerHTML = ''+
      pillHTML(entry.system||'General', (entry.system||'General')+' &middot; Pearl')+
      '<h2 style="font-size:1.15rem;line-height:1.4">"'+escapeHtml(entry.pearl||'')+'"</h2>'+
      '<p class="meta">'+(entry.source_paper||'Clinical pearl')+' &middot; '+(entry.timestamp||'')+'</p>'+
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
              evidenceHTML += '<div class="evidence-row"><div class="evidence-statement">'+escapeHtml(label)+'</div>'+(stat?'<div class="evidence-stat">'+escapeHtml(stat)+'</div>':'')+'</div>';
            }});
          }}
        }});
      }}

      // Build pearl box
      var pearlBoxHTML = '';
      if(data.key_pearls && data.key_pearls.length) {{
        pearlBoxHTML = '<div class="pearl-box"><strong>Key pearl &mdash;</strong> '+escapeHtml(data.key_pearls[0])+'</div>';
      }}

      body.innerHTML = ''+
        pillHTML(entry.system, entry.system+' &middot; '+entry.type)+
        '<h2>'+escapeHtml(entry.title)+'</h2>'+
        '<p class="meta">'+(authors!=='Unknown Authors'?'&mdash; '+escapeHtml(authors)+' &middot; ':'')+ (entry.journal||'')+'</p>'+
        '<div class="reader-actions">'+doiHTML+'</div>'+
        pearlBoxHTML+
        collapsible+
        evidenceHTML;
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
  if(!pMatches.length && !plMatches.length){{ box.innerHTML = '<div class="search-empty">No results for &ldquo;'+qRaw+'&rdquo;.</div>'; return; }}
  var html = '';
  if(pMatches.length) html += '<div class="search-group-label">Papers &amp; guidelines ('+pMatches.length+')</div>' + pMatches.map(function(p){{ return '<button class="search-result" data-open-paper="'+p.id+'" data-close-search>'+escapeHtml(p.title)+'</button>'; }}).join('');
  if(plMatches.length) html += '<div class="search-group-label">Pearls ('+plMatches.length+')</div>' + plMatches.map(function(p){{ return '<button class="search-result" data-open-pearl="'+p.id+'" data-close-search>'+escapeHtml((p.pearl||'').substring(0,80))+'</button>'; }}).join('');
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
    '<p class="one-liner">'+escapeHtml((t.one_liner||'').substring(0,200))+'</p>'+
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
document.getElementById('filterToggleBtn').addEventListener('click', openSheet);
document.getElementById('guidelinesFilterToggleBtn').addEventListener('click', openSheet);
document.getElementById('sheetBackdrop').addEventListener('click', closeSheet);
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
}});

document.addEventListener('change', function(e){{
  var container = e.target.closest('#filterPanelDesktop, #filterSheetBody, #filterPanelGuidelines');
  if(!container) return;
  if(e.target.classList.contains('all-check')){{
    container.querySelectorAll('[data-spec]').forEach(function(b){{ b.checked = e.target.checked; }});
  }}
  SPECS.forEach(function(s){{ var el = container.querySelector('[data-spec="'+s.name+'"]'); if(el) filterState.specialties[s.name] = el.checked; }});
  renderFilterCheckboxes();
}});

document.addEventListener('keydown', function(e){{
  if(e.key==='Escape'){{ closeSearch(); closeDrawer(); closeSheet(); closeReader(); document.body.classList.remove('ai-open'); }}
  if((e.ctrlKey||e.metaKey)&&e.key==='k'){{ e.preventDefault(); openSearch(); }}
  if((e.key==='Enter'||e.key===' ')&&e.target.matches('[role="button"]')){{ e.preventDefault(); e.target.click(); }}
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

  renderFilterCheckboxes();
  showView('home');
}})();
</script>
</body>
</html>"""
    return HTMLResponse(content=html)

# =====================================================================
# API ENDPOINTS
# =====================================================================

@app.get("/api/summary")
async def get_json_summary(file_name: str, system: str = "General", type: str = "Unclassified"):
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


@app.get("/api/search")
async def search_summaries(q: str = ""):
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
async def get_pearls(q: str = "", system: str = "", type: str = "", page: int = 1, limit: int = 50):
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
async def get_trials_stats():
    idx = load_trial_index()
    counts = {}
    for t in idx:
        sp = t.get("specialty", "Other")
        counts[sp] = counts.get(sp, 0) + 1
    return {"stats": counts}


@app.get("/api/trials")
async def get_trials(
    specialty: str = "",
    result_category: str = "",
    trial_type: str = "",
    q: str = "",
    page: int = 1,
    limit: int = 50
):
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
async def get_trial(slug: str):
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
    for s in payload.get("sections", []):
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
    return " ".join(text_parts).lower()


def extract_metadata(payload):
    title = payload.get("paper_name") or payload.get("title", "")
    system = payload.get("system") or ""
    if not system and payload.get("specialty"):
        system = ", ".join(payload["specialty"])
    article_type = payload.get("type_of_article") or ""
    if not article_type and payload.get("doc_type"):
        article_type = payload["doc_type"]
    journal = payload.get("journal_name") or payload.get("journal", "")
    if not journal:
        issuing = payload.get("issuing_bodies", [])
        if issuing:
            journal = ", ".join(issuing)
    if not journal:
        journal = "Unknown Journal"
    return title, system, article_type, journal
