import json, os, re, textwrap

INDEX_PATH = "output_files/esbicm_trials/esbicm_trials_index.json"
TRIALS_DIR = "output_files/esbicm_trials"

with open(INDEX_PATH, "r", encoding="utf-8") as f:
    index = json.load(f)

specialties = sorted(set(t["specialty"] for t in index))
spec_counts = {}
for t in index:
    spec_counts[t["specialty"]] = spec_counts.get(t["specialty"], 0) + 1

# Build subtopic map
subtopic_map = {}
for t in index:
    sp = t["specialty"]
    st = t.get("subtopic", "General")
    subtopic_map.setdefault(sp, set()).add(st)
subtopic_map = {k: sorted(v) for k, v in subtopic_map.items()}

# Read a few sample full trials for detail preview
sample_slugs = ["3mg", "65", "proseva"]
sample_trials = {}
for slug in sample_slugs:
    for t in index:
        if t["slug"] == slug:
            fp = os.path.join(TRIALS_DIR, t["file_path"])
            if os.path.exists(fp):
                with open(fp, "r", encoding="utf-8") as f:
                    sample_trials[slug] = json.load(f)
            break

INDEX_JSON = json.dumps(index)
SPECIALTIES_JSON = json.dumps(specialties)
SPEC_COUNTS_JSON = json.dumps(spec_counts)
SUBTOPIC_MAP_JSON = json.dumps(subtopic_map)
SAMPLE_TRIALS_JSON = json.dumps(sample_trials)

CREDITS_TEXT = """**Editor(s)**
**Dr. Ankur Gupta**, MBBS, EDIC, FCCCM, AFIC, PGDID, FICM, PGDMLE
Consultant Intensivist, Apollo Hospitals, Indore, INDIA
Founder President, Educational Society of Bedside Intensive Care Medicine (ESBICM)
**Dr. Pranay Bajpai**, MD (Medicine), FCCS, IDCC, MBA (HA)
Assistant Professor, Department of Medicine, MGM Medical College & M.Y. Group of Hospitals, Indore, INDIA
Consultant, Critical Care & Respiratory Medicine, Apollo Hospitals, Indore
**Co-Editor**
**Dr. Sonal Kaushika**, MBBS, FCCCM, AFIC
Associate Consultant, Critical Care, Shalby Hospital, Ahmedabad, Gujarat, INDIA
**A project by:**
Academic Committee of ESBICM (ACE)
**Contributors**
**Dr. Nikhilesh Jain**, DNB (Med), MRCPI, IDCCM, FCCCM, PGDHM, FIECMO
**Dr. Vivek Joshi**, DA, IDCCM, FCCCM, MBA (HA)
**Dr. Vivek Baxi**, MD, FCCCM, AFIC, PGCDM
**Dr. Prerna Bedi Lakhotia**, MBBS, DNB (Anesthesia), IDCCM, FGID
**Dr. Benjamin Baby Johnson**, MBBS, AFIC, PGDMLE
**Dr. Abhi Paliwal**, MBBS, DNB (Family Medicine), AFIC"""

DISCLAIMER_TEXT = """**Legal Disclaimer**
**Educational Purpose Only**
This website provides summaries of published clinical trials for informational and educational purposes only. It is not a substitute for professional medical advice, diagnosis, or treatment.
**No Warranties & Evolving Information**
Medical knowledge changes rapidly. While we aim for accuracy, the authors and publishers make no express or implied warranties regarding the completeness, accuracy, or currency of this content.
**Professional Duty**
Practitioners must exercise independent clinical judgment. Always consult original trial publications and manufacturer guidelines."""

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

html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dim">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ESBICM Landmark Trials — Preview</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
:root {{
  --bg:#1F1B14; --bg-elev:#29241B; --bg-sunk:#241F17;
  --ink:#F1E4CE; --ink-muted:#C4B18C; --border:#3A3226;
  --accent:#E8B778; --accent-ink:#1F1B14;
  --font-display:'Segoe UI','Space Grotesk',sans-serif;
  --font-body:'Segoe UI','Atkinson Hyperlegible',sans-serif;
  --font-mono:'Consolas','JetBrains Mono',monospace;
  --radius:10px; --shadow:0 1px 2px rgba(0,0,0,.12),0 4px 16px rgba(0,0,0,.08);
}}
* {{box-sizing:border-box;}}
html,body {{margin:0;padding:0;}}
body {{background:var(--bg);color:var(--ink);font-family:var(--font-body);font-size:15px;line-height:1.5;}}
h1,h2,h3 {{font-family:var(--font-display);margin:0;}}
a {{color:var(--accent);text-decoration:none;}}
button {{font-family:inherit;cursor:pointer;}}

.header {{background:var(--bg-elev);border-bottom:1px solid var(--border);padding:16px 20px;text-align:center;}}
.header h1 {{font-size:1.3rem;}}
.header .sub {{color:var(--ink-muted);font-size:.85rem;margin-top:4px;}}
.header .badge-row {{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-top:10px;}}
.badge {{font-size:.72rem;font-family:var(--font-mono);padding:3px 10px;border-radius:99px;border:1px solid var(--border);color:var(--ink-muted);}}

.preview-banner {{background:#2D1F00;border:1px solid #E8B778;border-radius:8px;padding:10px 16px;margin:14px auto;max-width:800px;text-align:center;font-size:.85rem;color:var(--accent);}}

.container {{max-width:960px;margin:0 auto;padding:16px 20px 40px;}}

/* Stats strip */
.stats {{display:flex;gap:18px;flex-wrap:wrap;padding:14px 0;margin-bottom:8px;}}
.stat-item {{font-size:.82rem;color:var(--ink-muted);}}
.stat-item b {{color:var(--ink);font-size:1.2rem;font-family:var(--font-display);display:block;}}

/* Specialty grid */
.spec-grid {{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:10px;margin-bottom:20px;}}
.spec-tile {{border:1px solid var(--border);background:var(--bg-elev);border-radius:var(--radius);padding:14px 12px;cursor:pointer;text-align:left;width:100%;font:inherit;color:var(--ink);border-left:3px solid var(--tile-color,var(--accent));transition:border-color .2s;}}
.spec-tile:hover {{border-color:var(--tile-color,var(--accent));}}
.spec-tile .dot {{width:10px;height:10px;border-radius:50%;margin-bottom:8px;display:block;}}
.spec-tile .count {{color:var(--ink-muted);font-size:.72rem;font-family:var(--font-mono);margin-top:2px;}}

/* Filter bar */
.filter-bar {{display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin-bottom:16px;padding:12px;background:var(--bg-sunk);border-radius:var(--radius);border:1px solid var(--border);}}
.filter-group {{display:flex;flex-direction:column;gap:3px;min-width:140px;flex:1;}}
.filter-group label {{font-size:.68rem;font-family:var(--font-mono);text-transform:uppercase;letter-spacing:.06em;color:var(--ink-muted);}}
.filter-group select {{padding:6px 8px;border-radius:6px;border:1px solid var(--border);background:var(--bg-elev);color:var(--ink);font-size:.85rem;font-family:inherit;}}
.filter-actions {{display:flex;gap:6px;align-items:flex-end;padding-bottom:2px;}}
.btn {{border:1px solid var(--border);background:var(--bg-elev);color:var(--ink);padding:7px 12px;border-radius:8px;font-size:.82rem;font-weight:600;cursor:pointer;}}
.btn:hover {{background:var(--bg-sunk);}}
.btn.primary {{background:var(--accent);color:var(--accent-ink);border-color:var(--accent);}}

/* Trial card */
.trial-card {{border:1px solid var(--border);border-radius:var(--radius);background:var(--bg-elev);padding:12px 14px;cursor:pointer;transition:border-color .2s;margin-bottom:8px;}}
.trial-card:hover {{border-color:var(--accent);}}
.trial-card h4 {{font-size:.9rem;margin:0 0 3px;}}
.trial-card .one-liner {{color:var(--ink-muted);font-size:.82rem;margin:0 0 6px;}}
.trial-card .meta-row {{display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:.72rem;}}

.result-badge {{font-size:.68rem;font-family:var(--font-mono);padding:2px 7px;border-radius:99px;border:1px solid;}}
.result-badge.pos {{color:#10B981;border-color:#10B981;}}
.result-badge.neg {{color:#EF4444;border-color:#EF4444;}}
.result-badge.neu {{color:#A855F7;border-color:#A855F7;}}
.result-badge.negneu {{color:#D97706;border-color:#D97706;}}

/* Back header */
.back-header {{display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap;}}
.back-header h2 {{font-size:1.1rem;flex:1;}}
.back-btn {{background:none;border:none;color:var(--accent);cursor:pointer;font-size:.85rem;font-weight:600;padding:6px 10px;border-radius:6px;}}
.back-btn:hover {{background:var(--bg-sunk);}}

/* Subtopic chips */
.chip-row {{display:flex;gap:6px;flex-wrap:wrap;padding:0 0 12px;margin-bottom:8px;border-bottom:1px solid var(--border);}}
.chip {{border:1px solid var(--border);background:var(--bg-elev);color:var(--ink-muted);padding:4px 11px;border-radius:99px;font-size:.7rem;cursor:pointer;font-family:var(--font-mono);white-space:nowrap;transition:all .15s;}}
.chip:hover {{border-color:var(--accent);color:var(--ink);}}
.chip.active {{background:var(--accent);color:var(--accent-ink);border-color:var(--accent);}}

/* Trial detail */
.trial-detail {{max-width:800px;margin:0 auto;}}
.trial-detail h1 {{font-size:1.2rem;margin-bottom:4px;}}
.trial-journal {{color:var(--ink-muted);font-size:.82rem;margin-bottom:10px;}}
.trial-meta {{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;}}
.trial-quote {{font-style:italic;color:var(--ink-muted);border-left:3px solid var(--accent);padding:10px 14px;margin:0 0 16px;background:var(--bg-sunk);border-radius:0 8px 8px 0;font-size:.9rem;}}

.section-details {{margin-bottom:.6rem;border:1px solid var(--border);border-radius:8px;overflow:hidden;}}
.section-details summary {{padding:.7rem 1rem;font-weight:700;font-size:.82rem;cursor:pointer;background:var(--bg-sunk);user-select:none;font-family:var(--font-display);}}
.section-details .section-body {{padding:.7rem 1rem;}}
.section-details .section-body p {{margin:.4em 0;font-size:.88rem;}}
.section-details .section-body ul {{padding-left:1.2em;}}

/* Actions bar */
.actions-bar {{display:flex;gap:8px;justify-content:center;margin-top:12px;flex-wrap:wrap;}}
.actions-bar .icon-btn {{background:none;border:1px solid var(--border);border-radius:6px;cursor:pointer;padding:5px 10px;font-size:.76rem;color:var(--ink-muted);display:inline-flex;align-items:center;gap:4px;font-family:inherit;}}
.actions-bar .icon-btn:hover {{background:var(--bg-elev);color:var(--ink);}}

/* Empty state */
.empty {{text-align:center;padding:50px 20px;color:var(--ink-muted);}}
.empty .icon {{font-size:2.2rem;display:block;margin-bottom:8px;}}

/* Overlay */
.overlay-backdrop {{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:90;display:flex;align-items:center;justify-content:center;padding:20px;display:none;}}
.overlay-box {{background:var(--bg-elev);border:1px solid var(--border);border-radius:14px;max-width:520px;width:100%;padding:24px;box-shadow:var(--shadow);max-height:80vh;overflow-y:auto;}}
.overlay-box h2 {{font-size:1.1rem;margin-bottom:12px;}}
.overlay-box p {{font-size:.85rem;color:var(--ink-muted);line-height:1.6;margin-bottom:10px;white-space:pre-wrap;}}

@media (min-width:720px) {{
  .spec-grid {{grid-template-columns:repeat(auto-fill,minmax(190px,1fr));}}
}}
</style>
</head>
<body>

<div class="header">
  <h1>&#127942; ESBICM Landmark Trials in Critical Care</h1>
  <p class="sub">A curated collection of {len(index)} landmark clinical trials across {len(specialties)} critical care specialties</p>
  <div class="badge-row">
    <span class="badge">{len(index)} Trials</span>
    <span class="badge">{len(specialties)} Specialties</span>
    <span class="badge">Curated by ESBICM</span>
  </div>
</div>

<div class="preview-banner">
  &#128640; <strong>Preview for Author Review</strong> &mdash; This is a static preview of the ESBICM Landmark Trials feature.
  Full interactive version with live API and admin dashboard coming soon.
</div>

<div class="container">

  <!-- Stats -->
  <div class="stats">
    <div class="stat-item"><b>{len(index)}</b>Total Trials</div>
    <div class="stat-item"><b>{len(specialties)}</b>Specialties</div>
    <div class="stat-item"><b>{sum(1 for t in index if t.get('result_category')=='Positive')}</b>Positive Results</div>
    <div class="stat-item"><b>{sum(1 for t in index if t.get('result_category','').startswith('Neg'))}</b>Negative/Neutral</div>
  </div>

  <!-- Actions -->
  <div class="actions-bar" style="margin-bottom:16px">
    <button class="icon-btn" onclick="showGrid()">&#9776; Specialty Grid</button>
    <button class="icon-btn" onclick="showAllTrials()">&#128196; All Trials</button>
    <button class="icon-btn" onclick="openOverlay('credits')">&#127942; Credits</button>
    <button class="icon-btn" onclick="openOverlay('disclaimer')">&#8505;&#65039; Disclaimer</button>
  </div>

  <!-- Filter bar -->
  <div class="filter-bar" id="filterBar">
    <div class="filter-group">
      <label>Specialty</label>
      <select id="filterSpec" onchange="applyFilters()">
        <option value="">All Specialties</option>
      </select>
    </div>
    <div class="filter-group">
      <label>Result</label>
      <select id="filterResult" onchange="applyFilters()">
        <option value="">All Results</option>
        <option value="Positive">Positive</option>
        <option value="Negative/Neutral">Negative/Neutral</option>
        <option value="Negative">Negative</option>
        <option value="Neutral">Neutral</option>
      </select>
    </div>
    <div class="filter-group">
      <label>Trial Type</label>
      <select id="filterType" onchange="applyFilters()">
        <option value="">All Types</option>
        <option value="RCT">RCT</option>
        <option value="Observational">Observational</option>
        <option value="Meta-analysis">Meta-analysis</option>
      </select>
    </div>
    <div class="filter-actions">
      <button class="btn" onclick="clearFilters()">&#10005; Clear</button>
    </div>
  </div>

  <!-- Specialty grid view -->
  <div id="specGridView"></div>

  <!-- Trial list view (hidden by default) -->
  <div id="trialListView" style="display:none">
    <div class="back-header">
      <button class="back-btn" onclick="showGrid()">&larr; Back to Grid</button>
      <h2 id="listViewTitle">All Trials</h2>
      <span style="color:var(--ink-muted);font-size:.82rem" id="listViewCount"></span>
    </div>
    <div id="trialListBody"></div>
  </div>

  <!-- Back header for specialty drill-down -->
  <div id="specDetail" style="display:none">
    <div class="back-header">
      <button class="back-btn" onclick="showGrid()">&larr; Back to Grid</button>
      <span class="dot" id="specDetailDot" style="width:14px;height:14px;border-radius:50%;display:inline-block"></span>
      <h2 id="specDetailTitle"></h2>
      <span style="color:var(--ink-muted);font-size:.82rem" id="specDetailCount"></span>
    </div>
    <div class="chip-row" id="specDetailChips"></div>
    <div id="specDetailList"></div>
  </div>

  <!-- Trial detail view -->
  <div id="trialDetail" style="display:none">
    <div class="back-header">
      <button class="back-btn" id="trialDetailBack">&larr; Back</button>
      <div style="flex:1"></div>
      <button class="back-btn" id="trialPrevBtn" style="display:none">&larr; Prev</button>
      <button class="back-btn" id="trialNextBtn" style="display:none">Next &rarr;</button>
    </div>
    <div id="trialDetailBody" class="trial-detail"></div>
  </div>
</div>

<div class="preview-banner" style="margin:20px auto">
  &#127942; <strong>ESBICM</strong> &mdash; Educational Society of Bedside Intensive Care Medicine
</div>

<!-- Overlays -->
<div class="overlay-backdrop" id="creditsOverlay" onclick="if(event.target===this)closeOverlay('creditsOverlay')">
  <div class="overlay-box">
    <h2>&#127942; Credits</h2>
    <div id="creditsBody"></div>
    <button class="btn" onclick="closeOverlay('creditsOverlay')" style="margin-top:12px">Close</button>
  </div>
</div>
<div class="overlay-backdrop" id="disclaimerOverlay" onclick="if(event.target===this)closeOverlay('disclaimerOverlay')">
  <div class="overlay-box">
    <h2>&#8505;&#65039; Disclaimer</h2>
    <div id="disclaimerBody"></div>
    <button class="btn" onclick="closeOverlay('disclaimerOverlay')" style="margin-top:12px">Close</button>
  </div>
</div>

<script>
// Embedded data
const INDEX = {INDEX_JSON};
const SPECIALTIES = {SPECIALTIES_JSON};
const SPEC_COUNTS = {SPEC_COUNTS_JSON};
const SUBTOPIC_MAP = {SUBTOPIC_MAP_JSON};
const SAMPLE_TRIALS = {SAMPLE_TRIALS_JSON};

const CREDITS_MD = `{CREDITS_TEXT.replace('`','\\`').replace('$','\\$')}`;
const DISCLAIMER_MD = `{DISCLAIMER_TEXT.replace('`','\\`').replace('$','\\$')}`;

const COLORS = {json.dumps(ESBICM_SPEC_COLORS)};

let _currentList = [];
let _currentIdx = -1;

function renderMarkdown(md) {{
  if (typeof marked !== 'undefined' && marked.parse) return marked.parse(md);
  return '<p>'+md.replace(/\\n\\n/g, '</p><p>').replace(/\\n/g, '<br>')+'</p>';
}}

function renderBoldText(text) {{
  return text.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>').replace(/\\n\\n/g, '</p><p>').replace(/\\n/g, '<br>');
}}

// ====== SPECIALTY GRID ======
function showGrid() {{
  document.getElementById('specGridView').style.display = '';
  document.getElementById('trialListView').style.display = 'none';
  document.getElementById('specDetail').style.display = 'none';
  document.getElementById('trialDetail').style.display = 'none';
  document.getElementById('filterBar').style.display = '';
  renderSpecGrid();
}}

function renderSpecGrid() {{
  var html = '<div class="spec-grid">';
  SPECIALTIES.forEach(function(s) {{
    var c = SPEC_COUNTS[s] || 0;
    var color = COLORS[s] || '#6B7280';
    html += '<button class="spec-tile" style="--tile-color:'+color+'" onclick="openSpecialty(\''+s.replace(/'/g,"\\\\'")+'\')">'+
      '<span class="dot" style="background:'+color+'"></span>'+
      '<div style="font-weight:700;font-size:.9rem">'+s+'</div>'+
      '<div class="count">'+c+' trial'+(c!==1?'s':'')+'</div>'+
      '</button>';
  }});
  html += '</div>';
  document.getElementById('specGridView').innerHTML = html;
}}

// ====== ALL TRIALS VIEW ======
function showAllTrials() {{
  document.getElementById('specGridView').style.display = 'none';
  document.getElementById('trialListView').style.display = '';
  document.getElementById('specDetail').style.display = 'none';
  document.getElementById('trialDetail').style.display = 'none';
  document.getElementById('filterBar').style.display = '';
  renderTrialList(INDEX, 'All Trials');
}}

function renderTrialList(list, title) {{
  _currentList = list;
  document.getElementById('listViewTitle').textContent = title;
  document.getElementById('listViewCount').textContent = list.length + ' trial' + (list.length!==1?'s':'');
  var html = '';
  list.forEach(function(t, i) {{
    html += trialCardHTML(t, i);
  }});
  if (!html) html = '<div class="empty"><span class="icon">&#128270;</span><p>No trials match your filters.</p></div>';
  document.getElementById('trialListBody').innerHTML = html;
}}

function trialCardHTML(t, idx) {{
  var resClass = (t.result_category||'').toLowerCase().replace(/[^a-z]/g,'');
  var resColor = 'neu';
  if(resClass.indexOf('pos')>=0) resColor = 'pos';
  else if(resClass.indexOf('neg')>=0 && resClass.indexOf('neu')>=0) resColor = 'negneu';
  else if(resClass.indexOf('neg')>=0) resColor = 'neg';
  return '<div class="trial-card" onclick="openTrialDetail('+idx+')">'+
    '<h4>'+esc(t.trial_name)+'</h4>'+
    '<p class="one-liner">'+esc((t.one_liner||'').substring(0,200))+'</p>'+
    '<div class="meta-row">'+
      '<span class="badge">'+esc(t.trial_type||'')+'</span>'+
      '<span class="result-badge '+resColor+'">'+esc(t.result_category||'')+'</span>'+
      (t.sample_size ? '<span class="badge">n='+t.sample_size+'</span>' : '')+
      '<span class="badge">'+t.year+'</span>'+
    '</div>'+
    '</div>';
}}

function esc(s) {{
  if(!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

// ====== SPECIALTY DRILL-DOWN ======
function openSpecialty(name) {{
  document.getElementById('specGridView').style.display = 'none';
  document.getElementById('trialListView').style.display = 'none';
  document.getElementById('specDetail').style.display = '';
  document.getElementById('trialDetail').style.display = 'none';
  document.getElementById('filterBar').style.display = 'none';

  document.getElementById('specDetailTitle').textContent = name;
  var color = COLORS[name] || '#6B7280';
  document.getElementById('specDetailDot').style.background = color;
  var filtered = INDEX.filter(function(t){{ return t.specialty === name; }});
  _currentList = filtered;
  document.getElementById('specDetailCount').textContent = filtered.length + ' trial' + (filtered.length!==1?'s':'');

  // Subtopic chips
  var sts = SUBTOPIC_MAP[name] || ['General'];
  var chipHtml = '<button class="chip active" onclick="filterSubtopic(this,\\'')">All</button>';
  sts.forEach(function(st) {{
    chipHtml += '<button class="chip" onclick="filterSubtopic(this,\\''+st.replace(/'/g,"\\\\'")+'\\')">'+esc(st)+'</button>';
  }});
  document.getElementById('specDetailChips').innerHTML = chipHtml;

  renderSpecTrials(name, '');
}}

function filterSubtopic(el, st) {{
  document.querySelectorAll('#specDetailChips .chip').forEach(function(c){{ c.classList.remove('active'); }});
  el.classList.add('active');
  var name = document.getElementById('specDetailTitle').textContent;
  renderSpecTrials(name, st);
}}

function renderSpecTrials(name, subtopic) {{
  var filtered = INDEX.filter(function(t) {{
    if (t.specialty !== name) return false;
    if (subtopic && t.subtopic !== subtopic) return false;
    return true;
  }});
  _currentList = filtered;
  var html = '';
  filtered.forEach(function(t, i) {{ html += trialCardHTML(t, i); }});
  if (!html) html = '<div class="empty"><span class="icon">&#128270;</span><p>No trials in this category.</p></div>';
  document.getElementById('specDetailList').innerHTML = html;
}}

// ====== FILTERS ======
function applyFilters() {{
  var spec = document.getElementById('filterSpec').value;
  var res = document.getElementById('filterResult').value;
  var typ = document.getElementById('filterType').value;
  var filtered = INDEX.filter(function(t) {{
    if (spec && t.specialty !== spec) return false;
    if (res && t.result_category !== res) return false;
    if (typ && t.trial_type !== typ) return false;
    return true;
  }});
  document.getElementById('specGridView').style.display = 'none';
  document.getElementById('trialListView').style.display = '';
  document.getElementById('specDetail').style.display = 'none';
  document.getElementById('trialDetail').style.display = 'none';
  var title = 'Filtered Results';
  if (spec) title = spec;
  renderTrialList(filtered, title);
}}

function clearFilters() {{
  document.getElementById('filterSpec').value = '';
  document.getElementById('filterResult').value = '';
  document.getElementById('filterType').value = '';
  showGrid();
}}

// ====== TRIAL DETAIL ======
function openTrialDetail(idx) {{
  var t = _currentList[idx];
  if (!t) return;
  _currentIdx = idx;

  document.getElementById('specGridView').style.display = 'none';
  document.getElementById('trialListView').style.display = 'none';
  document.getElementById('specDetail').style.display = 'none';
  document.getElementById('trialDetail').style.display = '';
  document.getElementById('filterBar').style.display = 'none';

  // Prev/Next
  document.getElementById('trialPrevBtn').style.display = idx > 0 ? '' : 'none';
  document.getElementById('trialNextBtn').style.display = idx < _currentList.length - 1 ? '' : 'none';
  document.getElementById('trialPrevBtn').onclick = function(){{ openTrialDetail(idx-1); }};
  document.getElementById('trialNextBtn').onclick = function(){{ openTrialDetail(idx+1); }};
  document.getElementById('trialDetailBack').onclick = function(){{ document.getElementById('trialDetail').style.display = 'none'; document.getElementById('trialListView').style.display=''; }};

  // Render from sample data or index
  var full = SAMPLE_TRIALS[t.slug];
  if (full) {{
    renderFullTrial(full);
  }} else {{
    renderIndexTrial(t);
  }}
}}

function renderFullTrial(data) {{
  var html = '<h1>'+esc(data.trial_name || data.trial_title || '')+'</h1>';
  html += '<div class="trial-journal">';
  if(data.journal) html += esc(data.journal);
  if(data.year) html += ' &middot; '+data.year;
  if(data.doi) {{
    var doi = data.doi;
    if(doi && doi!=='#' && !doi.startsWith('http')) doi = 'https://doi.org/'+doi;
    if(doi && doi!=='#') html += ' &middot; <a href="'+doi+'" target="_blank">&#128279; DOI</a>';
  }}
  html += '</div>';

  html += '<div class="trial-meta">';
  if(data.trial_type) html += '<span class="badge">'+esc(data.trial_type)+'</span>';
  if(data.result_category) {{
    var rc = data.result_category.toLowerCase().replace(/[^a-z]/g,'');
    var rcls = 'neu';
    if(rc.indexOf('pos')>=0) rcls = 'pos';
    else if(rc.indexOf('neg')>=0 && rc.indexOf('neu')>=0) rcls = 'negneu';
    else if(rc.indexOf('neg')>=0) rcls = 'neg';
    html += '<span class="result-badge '+rcls+'">'+esc(data.result_category)+'</span>';
  }}
  if(data.sample_size) html += '<span class="badge">n='+data.sample_size+'</span>';
  if(data.evidence_level) html += '<span class="badge">&#11088; '+esc(data.evidence_level)+'</span>';
  html += '</div>';

  if(data.one_liner) html += '<div class="trial-quote">'+esc(data.one_liner)+'</div>';

  if(data.sections && data.sections.length) {{
    data.sections.forEach(function(s) {{
      var secContent = (s.content||'').replace(/^\\u2022\\s*/gm, '- ').replace(/^o\\s*/gm, '  - ');
      html += '<details class="section-details"'+(s.id<=2?' open':'')+'><summary>'+esc(s.heading||'')+'</summary><div class="section-body">'+renderMarkdown(secContent)+'</div></details>';
    }});
  }}
  // Also show sample size statement etc.
  html += '<p style="font-size:.78rem;color:var(--ink-muted);margin-top:14px"><em>Full trial data shown for preview. &#128279; DOI link opens original publication.</em></p>';

  document.getElementById('trialDetailBody').innerHTML = html;
}}

function renderIndexTrial(t) {{
  var resClass = (t.result_category||'').toLowerCase().replace(/[^a-z]/g,'');
  var resColor = 'neu';
  if(resClass.indexOf('pos')>=0) resColor = 'pos';
  else if(resClass.indexOf('neg')>=0 && resClass.indexOf('neu')>=0) resColor = 'negneu';
  else if(resClass.indexOf('neg')>=0) resColor = 'neg';

  var html = '<h1>'+esc(t.trial_name)+'</h1>';
  html += '<div class="trial-journal">';
  if(t.journal) html += esc(t.journal);
  if(t.year) html += ' &middot; '+t.year;
  if(t.doi) {{
    var doi = t.doi;
    if(doi && doi!=='#' && !doi.startsWith('http')) doi = 'https://doi.org/'+doi;
    if(doi && doi!=='#') html += ' &middot; <a href="'+doi+'" target="_blank">&#128279; DOI</a>';
  }}
  html += '</div>';

  html += '<div class="trial-meta">';
  if(t.trial_type) html += '<span class="badge">'+esc(t.trial_type)+'</span>';
  html += '<span class="result-badge '+resColor+'">'+esc(t.result_category||'')+'</span>';
  if(t.sample_size) html += '<span class="badge">n='+t.sample_size+'</span>';
  if(t.primary_author) html += '<span class="badge">'+esc(t.primary_author)+'</span>';
  html += '</div>';

  if(t.one_liner) html += '<div class="trial-quote">'+esc(t.one_liner)+'</div>';

  html += '<div class="empty"><span class="icon">&#128221;</span><p>Full trial data with detailed sections (study design, results, statistics, limitations, etc.) will be available in the live version. This preview shows metadata from the trial index.</p></div>';

  document.getElementById('trialDetailBody').innerHTML = html;
}}

function renderBoldText(text) {{
  return text.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>').replace(/\\n\\n/g, '</p><p>').replace(/\\n/g, '<br>');
}}

// ====== OVERLAYS ======
function openOverlay(kind) {{
  if (kind === 'credits') {{
    document.getElementById('creditsBody').innerHTML = '<p>' + renderBoldText(CREDITS_MD) + '</p>';
    document.getElementById('creditsOverlay').style.display = 'flex';
  }} else if (kind === 'disclaimer') {{
    document.getElementById('disclaimerBody').innerHTML = '<p>' + renderBoldText(DISCLAIMER_MD) + '</p>';
    document.getElementById('disclaimerOverlay').style.display = 'flex';
  }}
}}

function closeOverlay(id) {{
  document.getElementById(id).style.display = 'none';
}}

// Populate filter dropdown
document.addEventListener('DOMContentLoaded', function() {{
  var sel = document.getElementById('filterSpec');
  SPECIALTIES.forEach(function(s) {{
    var opt = document.createElement('option');
    opt.value = s;
    opt.textContent = s + ' (' + (SPEC_COUNTS[s]||0) + ')';
    sel.appendChild(opt);
  }});
  renderSpecGrid();
}});
</script>
</body>
</html>
"""

output_path = "esbicm_trials_preview.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)

file_size = os.path.getsize(output_path)
print(f"Static preview generated: {output_path}")
print(f"File size: {file_size/1024:.0f} KB")
print(f"Trials in index: {len(index)}")
print(f"Sample trials with full data: {list(sample_trials.keys())}")
