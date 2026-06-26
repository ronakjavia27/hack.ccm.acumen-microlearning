import os
import json
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

# =====================================================================
# 🌐 GLOBAL CORE WORKSPACE SETTINGS & LINK MATRIX
# =====================================================================
FEEDBACK_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSd6xRmmimmVc0Sv4AeNls-oxLR6k_zX8D_QERFZwPP6zlfjRw/viewform?usp=header"
SUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSffsrF8DPWaTa-03XisMqSU5Da_8QdE-JrINdDP5iRmvWAI8Q/viewform?usp=header"
UNSUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScz864mkLh5AqBYVzAh573hWu98NdmwwPC2vaU1lfBE3WHHHg/viewform?usp=header"

OUTPUT_DIR = "./output_files"
EXCEL_TRACKER_FILE = "./sent_summaries.xlsx"
PEARLS_CSV = "./pearls.csv"

app = FastAPI()

def load_approved_ledger():
    if not os.path.exists(EXCEL_TRACKER_FILE):
        return pd.DataFrame()
    try:
        df = pd.read_excel(EXCEL_TRACKER_FILE, sheet_name="Registry Logs")
        df.columns = df.columns.str.strip()
        return df
    except Exception:
        return pd.DataFrame()

def load_pearls():
    if not os.path.exists(PEARLS_CSV):
        return []
    try:
        df = pd.read_csv(PEARLS_CSV)
        if "Unnamed: 9" in df.columns:
            df.rename(columns={"Unnamed: 9": "file_name"}, inplace=True)
        return df.to_dict(orient="records")
    except Exception:
        return []

@app.get("/", response_class=HTMLResponse)
async def render_dashboard_portal(request: Request):
    df = load_approved_ledger()

    total_published = 0
    unique_systems = 0

    articles_list = []
    if not df.empty:
        for idx, row in df.iterrows():
            raw_doi = str(row.get("DOI", "")).strip()
            clean_doi_url = "#"
            if raw_doi and raw_doi.lower() not in ["none", "nan", ""]:
                if raw_doi.startswith("http://") or raw_doi.startswith("https://"):
                    clean_doi_url = raw_doi
                else:
                    clean_doi_url = f"https://doi.org/{raw_doi}"

            articles_list.append({
                "id": str(idx),
                "title": str(row.get("Paper/Guideline Name", "Unknown Title")),
                "authors": str(row.get("Primary Authors", "Unknown Authors")),
                "system": str(row.get("System", "General")),
                "journal": str(row.get("Journal Name", "Unknown Source")),
                "type": str(row.get("Type of Article", "Unclassified")),
                "doi": clean_doi_url,
                "file_name": str(row.get("File Name", "")),
                "show_on_web": str(row.get("show_on_web", "No")).strip().lower()
            })

    pearls = load_pearls()
    pearl_systems = sorted(set(
        p["system"] for p in pearls
        if isinstance(p.get("system"), str) and p["system"].strip()
    ))
    pearl_types = sorted(set(
        p["type"] for p in pearls
        if isinstance(p.get("type"), str) and p["type"].strip()
    ))

    paper_to_file = {}
    if not df.empty:
        for _, row in df.iterrows():
            name = str(row.get("Paper/Guideline Name", "")).strip()
            fname = str(row.get("File Name", "")).strip()
            if name and fname and fname.lower() != "nan":
                json_name = os.path.splitext(fname)[0] + ".json"
                paper_to_file[name] = json_name

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>hack.CCM | Knowledge Portal</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <style>
            body {{ background-color: #FDFBF7; color: #111827; font-family: 'Georgia', serif; }}
            .custom-scrollbar::-webkit-scrollbar {{ width: 6px; }}
            .custom-scrollbar::-webkit-scrollbar-track {{ background: #FDFBF7; }}
            .custom-scrollbar::-webkit-scrollbar-thumb {{ background: #EFECE6; border-radius: 3px; }}

            .summary-body h2 {{ font-size: 1.5em; font-weight: bold; margin-top: 1.6em; margin-bottom: 0.6em; color: #000000; border-bottom: 1px solid #EFECE6; padding-bottom: 0.4em; font-family: 'Georgia', serif; }}
            .summary-body h3 {{ font-size: 1.25em; font-weight: bold; margin-top: 1.4em; margin-bottom: 0.5em; color: #111827; font-family: 'Georgia', serif; }}
            .summary-body p {{ margin-bottom: 1.2em; line-height: 1.65; text-align: justify; font-family: system-ui, -apple-system, sans-serif; color: #111827; }}
            .summary-body ul {{ list-style-type: disc !important; margin-left: 1.5em !important; margin-bottom: 1.2em !important; padding-left: 0px !important; }}
            .summary-body ol {{ list-style-type: decimal !important; margin-left: 1.5em !important; margin-bottom: 1.2em !important; padding-left: 0px !important; }}
            .summary-body li {{ margin-bottom: 0.5em; line-height: 1.6; font-family: system-ui, -apple-system, sans-serif; color: #111827; display: list-item !important; }}
            .summary-body strong {{ color: #000000; font-weight: 700; }}
            .tab-panel {{ display: none; }}
            .tab-panel.active {{ display: block; }}
        </style>
    </head>
    <body class="p-4 md:p-8 max-w-7xl mx-auto">

        <header class="bg-white border border-[#EFECE6] p-4 rounded-xl shadow-sm mb-6 flex flex-col sm:flex-row justify-between items-center gap-4">
            <div class="text-xl font-bold tracking-tight text-[#111827]">🧠 hack.CCM | Knowledge Portal</div>
            <nav class="flex gap-6 text-sm font-semibold">
                <a href="{FEEDBACK_FORM_URL}" target="_blank" class="text-[#1D4ED8] hover:text-[#2563EB] hover:underline transition">📝 Feedback</a>
                <a href="{SUBSCRIBE_FORM_URL}" target="_blank" class="text-[#1D4ED8] hover:text-[#2563EB] hover:underline transition">📢 Subscribe</a>
                <a href="{UNSUBSCRIBE_FORM_URL}" target="_blank" class="text-[#1D4ED8] hover:text-[#2563EB] hover:underline transition">❌ Unsubscribe</a>
            </nav>
        </header>

        <div id="dailyPaperPanel" class="bg-white border border-[#EFECE6] p-4 rounded-xl shadow-sm mb-4 cursor-pointer transition hover:bg-[#FDFBF7] hover:border-[#DCD9D2]" onclick="openDailyPaper()">
            <div class="flex items-start gap-3">
                <div class="text-2xl shrink-0 mt-0.5">⭐</div>
                <div class="flex-1 min-w-0">
                    <div class="text-[10px] font-bold tracking-wider text-[#4B5563] uppercase mb-1">📌 Paper of the Day</div>
                    <div id="dailyPaperTitle" class="text-sm font-bold text-[#111827] leading-snug truncate">Loading...</div>
                    <div id="dailyPaperMeta" class="text-xs text-[#4B5563] mt-1 space-x-2">
                        <span id="dailyPaperAuthors" class="italic"></span>
                        <span id="dailyPaperSystem" class="bg-[#EFECE6] px-1.5 py-0.5 rounded text-[10px] font-bold uppercase"></span>
                        <span id="dailyPaperType" class="bg-[#EFECE6] px-1.5 py-0.5 rounded text-[10px] font-bold uppercase"></span>
                    </div>
                </div>
                <div class="text-xs font-semibold text-[#1D4ED8] shrink-0 self-center hover:underline">Read →</div>
            </div>
        </div>

        <div id="dailyPearlPanel" class="bg-white border border-[#EFECE6] p-4 rounded-xl shadow-sm mb-4 cursor-pointer transition hover:bg-[#FDFBF7] hover:border-[#DCD9D2]" onclick="openDailyPearl()">
            <div class="flex items-start gap-3">
                <div class="text-2xl shrink-0 mt-0.5">💎</div>
                <div class="flex-1 min-w-0">
                    <div class="text-[10px] font-bold tracking-wider text-[#4B5563] uppercase mb-1">💎 Pearl of the Day</div>
                    <div id="dailyPearlText" class="text-sm font-bold text-[#111827] leading-snug truncate">Loading...</div>
                    <div id="dailyPearlMeta" class="text-xs text-[#4B5563] mt-1 space-x-2">
                        <span id="dailyPearlSystem" class="bg-[#EFECE6] px-1.5 py-0.5 rounded text-[10px] font-bold uppercase"></span>
                        <span id="dailyPearlType" class="bg-[#EFECE6] px-1.5 py-0.5 rounded text-[10px] font-bold uppercase"></span>
                        <span id="dailyPearlSource" class="italic"></span>
                    </div>
                </div>
                <div class="text-xs font-semibold text-[#1D4ED8] shrink-0 self-center hover:underline">Read →</div>
            </div>
        </div>

        <div class="flex flex-wrap gap-2 mb-6" style="font-family: system-ui, sans-serif;">
            <button onclick="switchTab('papers')" id="tabBtn_papers" class="px-4 py-2 text-xs uppercase tracking-wider rounded-lg border font-bold transition bg-[#EFECE6] text-[#111827] border-[#DCD9D2] hover:bg-[#E2DFD7]">📄 Papers</button>
            <button onclick="switchTab('guidelines')" id="tabBtn_guidelines" class="px-4 py-2 text-xs uppercase tracking-wider rounded-lg border font-bold transition bg-white text-[#4B5563] border-[#EFECE6] hover:bg-[#EFECE6]">📋 Guidelines</button>
            <button onclick="switchTab('pearls')" id="tabBtn_pearls" class="px-4 py-2 text-xs uppercase tracking-wider rounded-lg border font-bold transition bg-white text-[#4B5563] border-[#EFECE6] hover:bg-[#EFECE6]">💡 Pearls</button>
        </div>

        <main class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="space-y-6">
                <div class="bg-[#EFECE6] p-5 rounded-2xl border border-[#DCD9D2]">
                    <h3 class="text-xs font-bold tracking-wider text-[#4B5563] uppercase mb-3">📊 Portal Status</h3>
                    <div class="flex gap-3">
                        <span class="bg-white px-3 py-1.5 rounded-lg text-xs font-bold border border-[#DCD9D2]"><span id="statusIcon">📋</span> <span id="statusCount">0</span> <span id="statusLabel">Papers</span></span>
                        <span class="bg-white px-3 py-1.5 rounded-lg text-xs font-bold border border-[#DCD9D2]">🧬 <span id="statusSystems">0</span> Specialties</span>
                    </div>
                </div>

                <!-- Papers Filter Panel -->
                <div id="filterPanel_papers" class="tab-panel active bg-[#EFECE6] p-5 rounded-2xl border border-[#DCD9D2] space-y-4">
                    <h3 class="text-xs font-bold tracking-wider text-[#4B5563] uppercase mb-1">🔍 Filter Papers</h3>
                    <div>
                        <label class="block text-xs font-bold mb-1 text-[#4B5563]">Keywords Search</label>
                        <div style="position:relative;">
                            <input type="text" id="titleSearch_papers" onkeyup="onSearchInput('papers')" placeholder="Type keywords..." class="w-full bg-white text-[#111827] text-sm p-2.5 rounded-lg border border-[#DCD9D2] focus:outline-none focus:ring-2 focus:ring-[#1D4ED8] transition pr-8">
                            <button id="clearSearch_papers" onclick="clearSearch('papers')" style="display:none; position:absolute; right:6px; top:50%; transform:translateY(-50%); background:none; border:none; cursor:pointer; font-size:14px; color:#4B5563; padding:4px; line-height:1;">✕</button>
                        </div>
                        <label class="flex items-center gap-2 mt-2 cursor-pointer">
                            <input type="checkbox" id="fulltextToggle_papers" onchange="onFullTextToggle('papers')" class="rounded border-[#DCD9D2] text-[#1D4ED8] focus:ring-[#1D4ED8]">
                            <span class="text-[10px] font-bold text-[#4B5563] uppercase tracking-wider">🔍 Search full text</span>
                        </label>
                    </div>
                    <div>
                        <label class="block text-xs font-bold mb-1 text-[#4B5563]">Specialty Group</label>
                        <select id="systemFilter_papers" onchange="executeClientSideFilter()" class="w-full bg-white text-[#111827] text-sm p-2.5 rounded-lg border border-[#DCD9D2] focus:outline-none focus:ring-2 focus:ring-[#1D4ED8] transition">
                            <option value="All">All Specialties</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold mb-1 text-[#4B5563]">Subtype</label>
                        <select id="typeFilter_papers" onchange="executeClientSideFilter()" class="w-full bg-white text-[#111827] text-sm p-2.5 rounded-lg border border-[#DCD9D2] focus:outline-none focus:ring-2 focus:ring-[#1D4ED8] transition">
                            <option value="All">All Types</option>
                        </select>
                    </div>
                </div>

                <!-- Guidelines Filter Panel -->
                <div id="filterPanel_guidelines" class="tab-panel bg-[#EFECE6] p-5 rounded-2xl border border-[#DCD9D2] space-y-4">
                    <h3 class="text-xs font-bold tracking-wider text-[#4B5563] uppercase mb-1">🔍 Filter Guidelines</h3>
                    <div>
                        <label class="block text-xs font-bold mb-1 text-[#4B5563]">Keywords Search</label>
                        <div style="position:relative;">
                            <input type="text" id="titleSearch_guidelines" onkeyup="onSearchInput('guidelines')" placeholder="Type keywords..." class="w-full bg-white text-[#111827] text-sm p-2.5 rounded-lg border border-[#DCD9D2] focus:outline-none focus:ring-2 focus:ring-[#1D4ED8] transition pr-8">
                            <button id="clearSearch_guidelines" onclick="clearSearch('guidelines')" style="display:none; position:absolute; right:6px; top:50%; transform:translateY(-50%); background:none; border:none; cursor:pointer; font-size:14px; color:#4B5563; padding:4px; line-height:1;">✕</button>
                        </div>
                        <label class="flex items-center gap-2 mt-2 cursor-pointer">
                            <input type="checkbox" id="fulltextToggle_guidelines" onchange="onFullTextToggle('guidelines')" class="rounded border-[#DCD9D2] text-[#1D4ED8] focus:ring-[#1D4ED8]">
                            <span class="text-[10px] font-bold text-[#4B5563] uppercase tracking-wider">🔍 Search full text</span>
                        </label>
                    </div>
                    <div>
                        <label class="block text-xs font-bold mb-1 text-[#4B5563]">System</label>
                        <select id="systemFilter_guidelines" onchange="executeClientSideFilter()" class="w-full bg-white text-[#111827] text-sm p-2.5 rounded-lg border border-[#DCD9D2] focus:outline-none focus:ring-2 focus:ring-[#1D4ED8] transition">
                            <option value="All">All Systems</option>
                        </select>
                    </div>
                </div>

                <!-- Pearls Filter Panel -->
                <div id="filterPanel_pearls" class="tab-panel bg-[#EFECE6] p-5 rounded-2xl border border-[#DCD9D2] space-y-4">
                    <h3 class="text-xs font-bold tracking-wider text-[#4B5563] uppercase mb-1">🔍 Filter Pearls</h3>
                    <div>
                        <label class="block text-xs font-bold mb-1 text-[#4B5563]">Specialty Group</label>
                        <select id="systemFilter_pearls" onchange="executePearlsFilter()" class="w-full bg-white text-[#111827] text-sm p-2.5 rounded-lg border border-[#DCD9D2] focus:outline-none focus:ring-2 focus:ring-[#1D4ED8] transition">
                            <option value="All">All Specialties</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold mb-1 text-[#4B5563]">Subtype</label>
                        <select id="typeFilter_pearls" onchange="executePearlsFilter()" class="w-full bg-white text-[#111827] text-sm p-2.5 rounded-lg border border-[#DCD9D2] focus:outline-none focus:ring-2 focus:ring-[#1D4ED8] transition">
                            <option value="All">All Types</option>
                        </select>
                    </div>
                    <div class="text-xs font-semibold text-[#4B5563]" id="pearlCountDisplay">Select filters above</div>
                </div>

                <div class="space-y-2">
                    <h3 class="text-xs font-bold tracking-wider text-[#4B5563] uppercase px-2">📑 Document Selector</h3>
                    <div id="articlesListDeck" class="max-h-[450px] overflow-y-auto custom-scrollbar space-y-2 pr-1"></div>
                </div>
            </div>

            <div class="md:col-span-2">
                <div id="documentSheetContainer" class="bg-white border border-[#EFECE6] p-6 md:p-8 rounded-2xl shadow-xs min-h-[550px]">
                    <div class="text-center py-24 text-[#4B5563]">
                        <p class="text-lg font-medium">👋 Welcome to hack.CCM Repository</p>
                        <p class="text-sm mt-1">Select a publication entry card from the index frame to unpack formatting layers.</p>
                    </div>
                </div>
            </div>
        </main>

        <script>
            const baseDataset = {json.dumps(articles_list)};
            const allPearls = {json.dumps(pearls)};
            const pearlSystems = {json.dumps(pearl_systems)};
            const pearlTypes = {json.dumps(pearl_types)};
            const paperToFile = {json.dumps(paper_to_file)};
            let currentActiveSelectionId = null;
            let activeTab = 'papers';
            let dailyPaperItem = null;
            let dailyPearlItem = null;
            let fullTextResults = null;
            let searchTimeout = null;
            let currentTitle = '';
            let currentAuthors = '';
            let currentSystem = '';
            let currentJournal = '';
            let currentType = '';
            let currentContent = '';
            let currentPearlIndex = 0;
            let filteredPearls = [];

            marked.setOptions({{ gfm: true, breaks: true }});

            function getDailyIndex() {{
                const today = new Date().toISOString().split('T')[0];
                let hash = 0;
                for (let i = 0; i < today.length; i++) {{
                    hash = ((hash << 5) - hash) + today.charCodeAt(i);
                    hash = hash & hash;
                }}
                return Math.abs(hash) % baseDataset.length;
            }}

            function pickDailyPaper() {{
                if (baseDataset.length === 0) return;
                const sorted = [...baseDataset].sort((a, b) => parseInt(a.id) - parseInt(b.id));
                const idx = getDailyIndex();
                dailyPaperItem = sorted[idx];
                document.getElementById("dailyPaperTitle").textContent = dailyPaperItem.title;
                document.getElementById("dailyPaperAuthors").textContent = dailyPaperItem.authors !== "Unknown Authors" ? "✍️ " + dailyPaperItem.authors : "";
                document.getElementById("dailyPaperSystem").textContent = dailyPaperItem.system;
                document.getElementById("dailyPaperType").textContent = dailyPaperItem.type;
            }}

            function openDailyPaper() {{
                if (!dailyPaperItem) return;
                switchTab('papers');
                fetchActiveDocumentSummary(
                    dailyPaperItem.id, dailyPaperItem.file_name,
                    dailyPaperItem.title, dailyPaperItem.doi,
                    dailyPaperItem.system, dailyPaperItem.journal, dailyPaperItem.type
                );
            }}

            function pickDailyPearl() {{
                if (allPearls.length === 0) {{
                    document.getElementById("dailyPearlPanel").style.display = 'none';
                    return;
                }}
                const idx = Math.floor(Math.random() * allPearls.length);
                dailyPearlItem = {{ index: idx, pearl: allPearls[idx] }};
                const p = dailyPearlItem.pearl;
                const text = p.pearl.length > 120 ? p.pearl.substring(0, 120) + '...' : p.pearl;
                document.getElementById("dailyPearlText").textContent = '\u201C' + text + '\u201D';
                document.getElementById("dailyPearlSystem").textContent = p.system || '';
                document.getElementById("dailyPearlType").textContent = p.type || '';
                document.getElementById("dailyPearlSource").textContent = p.source_paper ? '\u2014 ' + p.source_paper : '';
            }}

            function openDailyPearl() {{
                if (!dailyPearlItem) return;
                switchTab('pearls');
                document.getElementById("systemFilter_pearls").value = "All";
                document.getElementById("typeFilter_pearls").value = "All";
                executePearlsFilter();
                const foundIdx = filteredPearls.findIndex(function(p) {{ return p === dailyPearlItem.pearl; }});
                if (foundIdx !== -1) {{
                    currentPearlIndex = foundIdx;
                    renderPearl();
                }}
            }}

            function updateStatusPanel() {{
                let count, systems, icon, label;
                if (activeTab === 'papers') {{
                    const items = baseDataset.filter(i => i.type.toLowerCase() !== "guideline");
                    count = items.length;
                    systems = new Set(items.map(i => i.system)).size;
                    icon = '📋';
                    label = 'Papers';
                }} else if (activeTab === 'guidelines') {{
                    const items = baseDataset.filter(i => i.type.toLowerCase() === "guideline");
                    count = items.length;
                    systems = new Set(items.map(i => i.system)).size;
                    icon = '📋';
                    label = 'Guidelines';
                }} else {{
                    count = filteredPearls.length;
                    systems = new Set(filteredPearls.map(function(p) {{ return p.system; }})).size;
                    icon = '💎';
                    label = 'Pearls';
                }}
                document.getElementById('statusIcon').textContent = icon;
                document.getElementById('statusCount').textContent = count;
                document.getElementById('statusLabel').textContent = label;
                document.getElementById('statusSystems').textContent = systems;
            }}

            function switchTab(tab) {{
                activeTab = tab;

                const tabButtons = ['papers', 'guidelines', 'pearls'];
                tabButtons.forEach(btnKey => {{
                    const el = document.getElementById(`tabBtn_${{btnKey}}`);
                    if(btnKey === tab) {{
                        el.className = "px-4 py-2 text-xs uppercase tracking-wider rounded-lg border font-bold transition bg-[#EFECE6] text-[#111827] border-[#DCD9D2] hover:bg-[#E2DFD7]";
                    }} else {{
                        el.className = "px-4 py-2 text-xs uppercase tracking-wider rounded-lg border font-bold transition bg-white text-[#4B5563] border-[#EFECE6] hover:bg-[#EFECE6]";
                    }}
                }});

                const panels = ['filterPanel_papers', 'filterPanel_guidelines', 'filterPanel_pearls'];
                panels.forEach(panelId => {{
                    const el = document.getElementById(panelId);
                    if(panelId === `filterPanel_${{tab}}`) {{
                        el.classList.add('active');
                    }} else {{
                        el.classList.remove('active');
                    }}
                }});

                currentActiveSelectionId = null;
                fullTextResults = null;
                updateStatusPanel();

                const viewer = document.getElementById("documentSheetContainer");
                if (tab === 'pearls') {{
                    executePearlsFilter();
                }} else {{
                    executeClientSideFilter();
                    viewer.innerHTML = `<div class="text-center py-24 text-[#4B5563]">
                        <p class="text-lg font-medium">👋 Welcome to hack.CCM Repository</p>
                        <p class="text-sm mt-1">Select a publication entry card from the index frame to unpack formatting layers.</p>
                    </div>`;
                }}
            }}

            function initializeAppMatrix() {{
                // Papers - specialty dropdown
                const sysSelectPapers = document.getElementById("systemFilter_papers");
                const uniqueSpecs = [...new Set(baseDataset.map(item => item.system))].sort();
                uniqueSpecs.forEach(sys => {{
                    if(sys && sys !== "None" && sys !== "nan" && sys.trim() !== "") {{
                        let opt = document.createElement("option");
                        opt.value = sys; opt.textContent = sys;
                        sysSelectPapers.appendChild(opt);
                    }}
                }});

                // Papers - type dropdown (exclude Guideline)
                const typeSelectPapers = document.getElementById("typeFilter_papers");
                const uniqueTypes = [...new Set(baseDataset.map(item => item.type))].sort();
                uniqueTypes.forEach(t => {{
                    if(t && t !== "None" && t !== "nan" && t.trim() !== "" && t.toLowerCase() !== "guideline") {{
                        let opt = document.createElement("option");
                        opt.value = t; opt.textContent = t;
                        typeSelectPapers.appendChild(opt);
                    }}
                }});

                // Guidelines - system dropdown
                const sysSelectGuidelines = document.getElementById("systemFilter_guidelines");
                const guidelineSystems = [...new Set(
                    baseDataset.filter(item => item.type.toLowerCase() === "guideline").map(item => item.system)
                )].sort();
                guidelineSystems.forEach(sys => {{
                    if(sys && sys !== "None" && sys !== "nan" && sys.trim() !== "") {{
                        let opt = document.createElement("option");
                        opt.value = sys; opt.textContent = sys;
                        sysSelectGuidelines.appendChild(opt);
                    }}
                }});

                // Pearls - system dropdown
                const sysSelectPearls = document.getElementById("systemFilter_pearls");
                pearlSystems.forEach(sys => {{
                    if(sys && sys !== "None" && sys !== "nan" && sys.trim() !== "") {{
                        let opt = document.createElement("option");
                        opt.value = sys; opt.textContent = sys;
                        sysSelectPearls.appendChild(opt);
                    }}
                }});

                // Pearls - type dropdown
                const typeSelectPearls = document.getElementById("typeFilter_pearls");
                pearlTypes.forEach(t => {{
                    if(t && t !== "None" && t !== "nan" && t.trim() !== "") {{
                        let opt = document.createElement("option");
                        opt.value = t; opt.textContent = t;
                        typeSelectPearls.appendChild(opt);
                    }}
                }});

                updateStatusPanel();
                pickDailyPaper();
                pickDailyPearl();
                executeClientSideFilter();
            }}

            function onSearchInput(tab) {{
                const input = document.getElementById(`titleSearch_${{tab}}`);
                const clearBtn = document.getElementById(`clearSearch_${{tab}}`);
                clearBtn.style.display = input.value ? 'block' : 'none';

                const toggle = document.getElementById(`fulltextToggle_${{tab}}`);
                if (toggle.checked) {{
                    clearTimeout(searchTimeout);
                    searchTimeout = setTimeout(() => searchFullText(tab), 300);
                }} else {{
                    fullTextResults = null;
                    executeClientSideFilter();
                }}
            }}

            function clearSearch(tab) {{
                const input = document.getElementById(`titleSearch_${{tab}}`);
                input.value = '';
                document.getElementById(`clearSearch_${{tab}}`).style.display = 'none';
                const toggle = document.getElementById(`fulltextToggle_${{tab}}`);
                if (toggle.checked) {{
                    toggle.checked = false;
                }}
                fullTextResults = null;
                executeClientSideFilter();
            }}

            function onFullTextToggle(tab) {{
                const checkbox = document.getElementById(`fulltextToggle_${{tab}}`);
                const input = document.getElementById(`titleSearch_${{tab}}`);
                if (checkbox.checked && input.value) {{
                    clearTimeout(searchTimeout);
                    searchTimeout = setTimeout(() => searchFullText(tab), 300);
                }} else {{
                    fullTextResults = null;
                    executeClientSideFilter();
                }}
            }}

            async function searchFullText(tab) {{
                const input = document.getElementById(`titleSearch_${{tab}}`);
                const q = input.value.trim();
                if (!q) {{
                    fullTextResults = null;
                    executeClientSideFilter();
                    return;
                }}
                try {{
                    const resp = await fetch(`/api/search?q=${{encodeURIComponent(q)}}`);
                    const data = await resp.json();
                    if (data.matches) {{
                        fullTextResults = new Set(data.matches.map(m => m.file_name));
                    }} else {{
                        fullTextResults = new Set();
                    }}
                }} catch(e) {{
                    fullTextResults = null;
                }}
                executeClientSideFilter();
            }}

            function executeClientSideFilter() {{
                if (activeTab === 'pearls') return;
                updateStatusPanel();
                const deckContainer = document.getElementById("articlesListDeck");

                let searchVal, systemVal, typeFilterVal;

                if (activeTab === 'papers') {{
                    searchVal = document.getElementById("titleSearch_papers").value.toLowerCase();
                    systemVal = document.getElementById("systemFilter_papers").value;
                    typeFilterVal = document.getElementById("typeFilter_papers").value;
                }} else {{
                    searchVal = document.getElementById("titleSearch_guidelines").value.toLowerCase();
                    systemVal = document.getElementById("systemFilter_guidelines").value;
                    typeFilterVal = "All";
                }}

                deckContainer.innerHTML = "";
                const filtered = baseDataset.filter(item => {{
                    let tabMatches;
                    if (activeTab === 'papers') {{
                        tabMatches = item.type.toLowerCase() !== "guideline";
                    }} else {{
                        tabMatches = item.type.toLowerCase() === "guideline";
                    }}

                    const ftMatch = fullTextResults ? fullTextResults.has(item.file_name) : true;
                    const textMatches = fullTextResults ? true : item.title.toLowerCase().includes(searchVal);
                    const systemMatches = (systemVal === "All" || item.system === systemVal);
                    const typeMatches = (typeFilterVal === "All" || item.type === typeFilterVal);

                    return tabMatches && ftMatch && textMatches && systemMatches && typeMatches;
                }});

                if(filtered.length === 0) {{
                    deckContainer.innerHTML = `<p class="text-xs text-[#4B5563] italic p-3 text-center">No matching records found.</p>`;
                    return;
                }}

                filtered.forEach(item => {{
                    const btn = document.createElement("button");
                    const isActive = item.id === currentActiveSelectionId;
                    btn.className = `w-full text-left p-4 rounded-xl text-sm transition border flex flex-col gap-1 shadow-2xs ${{isActive ? 'bg-[#D7CDB7] text-[#5C5346] border-transparent font-bold ring-1 ring-[#BDB199]' : 'bg-white text-[#111827] border-[#EFECE6] hover:bg-[#EFECE6]'}}`;
                    btn.onclick = () => fetchActiveDocumentSummary(item.id, item.file_name, item.title, item.doi, item.system, item.journal, item.type);
                    btn.innerHTML = `
                        <span class="block text-sm leading-snug">${{item.title}}</span>
                        <div class="flex gap-2 mt-1 text-[10px] font-bold tracking-wider uppercase text-[#4B5563]">
                            <span class="${{isActive ? 'bg-[#FFFFFF]/50' : 'bg-[#EFECE6]'}} px-1.5 py-0.5 rounded">${{item.system}}</span>
                            <span class="${{isActive ? 'bg-[#FFFFFF]/50' : 'bg-[#EFECE6]'}} px-1.5 py-0.5 rounded">${{item.type}}</span>
                        </div>
                    `;
                    deckContainer.appendChild(btn);
                }});
            }}

            async function fetchActiveDocumentSummary(id, fileName, title, doiLink, system, journal, type) {{
                currentActiveSelectionId = id;
                executeClientSideFilter();

                const viewer = document.getElementById("documentSheetContainer");
                viewer.innerHTML = `<div class="text-center py-24 text-sm font-medium text-[#4B5563] animate-pulse">🔬 Processing structural markdown fields...</div>`;

                try {{
                    const response = await fetch(`/api/summary?file_name=${{encodeURIComponent(fileName)}}&system=${{encodeURIComponent(system)}}&type=${{encodeURIComponent(type)}}`);
                    const data = await response.json();

                    if (!response.ok || data.error) {{
                        viewer.innerHTML = `<div class="p-4 bg-red-50 text-red-700 rounded-lg text-sm">⚠️ Error loading summary payload dataset.</div>`;
                        return;
                    }}

                    currentTitle = title;
                    currentAuthors = data.authors || "Unknown Authors";
                    currentSystem = system;
                    currentJournal = journal;
                    currentType = type;
                    currentContent = data.content || "";

                    let doiButtonHTML = "";
                    if(doiLink && doiLink !== "#") {{
                        doiButtonHTML = `<a href="${{doiLink}}" target="_blank" class="w-full sm:w-auto text-center bg-[#1D4ED8] hover:bg-[#2563EB] text-white font-semibold text-xs px-4 py-2.5 rounded-lg shadow-sm transition inline-block">🔗 Source Publication</a>`;
                    }}

                    let pdfButtonHTML = `<button onclick="exportPDF()" class="w-full sm:w-auto text-center bg-white text-[#1D4ED8] font-semibold text-xs px-4 py-2.5 rounded-lg border border-[#1D4ED8] shadow-sm transition hover:bg-[#EFF6FF] inline-block">📄 Download PDF</button>`;

                    const parsedMarkdownHTML = marked.parse(data.content);
                    const authorsLine = data.authors && data.authors !== "Unknown Authors" ? `<p class="text-sm italic text-[#4B5563] mt-1 font-sans">✍️ Primary Authors: ${{data.authors}}</p>` : "";

                    viewer.innerHTML = `
                        <div class="flex flex-col sm:flex-row justify-between items-start gap-4 pb-4 border-b border-[#EFECE6] mb-6">
                            <div>
                                <h1 class="text-2xl font-bold tracking-tight text-black">📜 ${{title}}</h1>
                                ${{authorsLine}}
                                <div class="flex flex-wrap gap-2 text-xs font-semibold mt-3" style="font-family: system-ui, sans-serif;">
                                    <span class="bg-[#EFF6FF] text-[#1E40AF] px-2.5 py-1 rounded-md border border-[#DBEAFE]">🧬 Specialty: ${{system}}</span>
                                    <span class="bg-[#FAF5FF] text-[#6B21A8] px-2.5 py-1 rounded-md border border-[#F3E8FF]">📖 Journal: ${{journal}}</span>
                                    <span class="bg-[#F1F5F9] text-[#475569] px-2.5 py-1 rounded-md border border-[#E2E8F0]">📑 Type: ${{type}}</span>
                                </div>
                            </div>
                            <div class="w-full sm:w-auto shrink-0 flex gap-2">${{doiButtonHTML}}${{pdfButtonHTML}}</div>
                        </div>
                        <div class="summary-body text-[#111827] text-[15px]">
                            ${{parsedMarkdownHTML}}
                        </div>
                    `;
                }} catch(err) {{
                    viewer.innerHTML = `<div class="p-4 bg-red-50 text-red-700 rounded-lg text-sm">❌ Network connection error: ${{err.message}}</div>`;
                }}
            }}

            function exportPDF() {{
                if (!currentContent) return;
                const rendered = marked.parse(currentContent);
                const aLine = currentAuthors !== "Unknown Authors" ? '<p style="font-style:italic;color:#4B5563;">✍️ ' + currentAuthors + '</p>' : '';
                const html = '<!DOCTYPE html><html><head><title>' + currentTitle + '</title>'
                    + '<style>'
                    + '@page{{size:A4;margin:20mm;}}'
                    + 'body{{font-family:Georgia,serif;color:#111827;line-height:1.6;padding:20px;}}'
                    + 'h1{{font-size:24px;margin-bottom:8px;}}'
                    + '.meta{{color:#4B5563;font-size:14px;margin-bottom:20px;}}'
                    + '.meta span{{background:#EFECE6;padding:2px 8px;border-radius:4px;margin-right:8px;font-size:12px;font-weight:bold;}}'
                    + 'h2{{font-size:20px;border-bottom:1px solid #EFECE6;padding-bottom:4px;margin-top:24px;}}'
                    + 'h3{{font-size:16px;margin-top:18px;}}'
                    + 'p{{margin-bottom:12px;text-align:justify;}}'
                    + 'ul,ol{{margin-left:20px;margin-bottom:12px;}}'
                    + 'li{{margin-bottom:6px;}}'
                    + '@media print{{body{{padding:0;}}}}'
                    + '</style></head><body>'
                    + '<h1>📜 ' + currentTitle + '</h1>'
                    + aLine
                    + '<div class="meta"><span>🧬 ' + currentSystem + '</span><span>📖 ' + currentJournal + '</span><span>📑 ' + currentType + '</span></div>'
                    + '<hr style="border:none;border-top:1px solid #EFECE6;margin:20px 0;">'
                    + '<div>' + rendered + '</div>'
                    + '<p style="text-align:center;font-size:11px;color:#4B5563;margin-top:30px;">Generated by hack.CCM Knowledge Portal</p>'
                    + '</body></html>';
                const blob = new Blob([html], {{type:'text/html'}});
                const url = URL.createObjectURL(blob);
                const win = window.open(url, '_blank');
                win.onload = function() {{ win.print(); setTimeout(() => win.close(), 1000); }};
            }}

            // =====================================================================
            // 💎 PEARLS FUNCTIONS
            // =====================================================================

            function updatePearlCounter() {{
                const display = document.getElementById("pearlCountDisplay");
                if (filteredPearls.length === 0) {{
                    display.textContent = "No matching pearls";
                }} else {{
                    display.textContent = "Showing " + (currentPearlIndex + 1) + " of " + filteredPearls.length;
                }}
            }}

            function executePearlsFilter() {{
                const systemVal = document.getElementById("systemFilter_pearls").value;
                const typeVal = document.getElementById("typeFilter_pearls").value;
                filteredPearls = allPearls.filter(function(p) {{
                    if (systemVal !== "All" && p.system !== systemVal) return false;
                    if (typeVal !== "All" && p.type !== typeVal) return false;
                    return true;
                }});
                currentPearlIndex = 0;
                updateStatusPanel();
                updatePearlCounter();
                renderPearl();
            }}

            function renderPearl() {{
                const viewer = document.getElementById("documentSheetContainer");
                if (filteredPearls.length === 0) {{
                    viewer.innerHTML = '<div class="text-center py-24 text-[#4B5563]"><p class="text-lg font-medium">💎 No pearls match your filters.</p><p class="text-sm mt-1">Try adjusting the filters above.</p></div>';
                    return;
                }}
                const p = filteredPearls[currentPearlIndex];
                const paperName = (p.source_paper || '').replace(/[^a-zA-Z0-9 _-]/g, ' ').trim() || 'Unknown Source';
                const prevDisabled = currentPearlIndex === 0 ? 'disabled' : '';
                const nextDisabled = currentPearlIndex === filteredPearls.length - 1 ? 'disabled' : '';
                viewer.innerHTML = '<div class="flex flex-col items-center justify-center min-h-[400px] max-w-2xl mx-auto text-center">' +
                    '<div class="flex gap-2 mb-6">' +
                        (p.system ? '<span class="bg-[#EFF6FF] text-[#1E40AF] text-xs font-bold px-3 py-1 rounded-md">' + p.system + '</span>' : '') +
                        (p.type ? '<span class="bg-[#F0FDF4] text-[#15803D] text-xs font-bold px-3 py-1 rounded-md">' + p.type + '</span>' : '') +
                    '</div>' +
                    '<div class="text-xl leading-relaxed text-[#1F2937] mb-6 font-serif">\u201C' + p.pearl + '\u201D</div>' +
                    '<div class="text-sm text-[#6B7280] mb-8 font-sans">' +
                        '\u2014 ' + paperName +
                        ((p.file_name || p.source_paper) ? ' <button onclick="openPearlPaper()" class="ml-2 text-[#1D4ED8] hover:underline font-semibold text-xs">Open \u2197</button>' : '') +
                    '</div>' +
                    '<div class="flex gap-4 font-sans">' +
                        '<button onclick="prevPearl()" ' + prevDisabled + ' class="px-6 py-2 text-sm font-semibold rounded-lg border border-[#DCD9D2] bg-white text-[#4B5563] hover:bg-[#EFECE6] disabled:opacity-40 disabled:cursor-not-allowed transition">\u2190 Previous</button>' +
                        '<button onclick="nextPearl()" ' + nextDisabled + ' class="px-6 py-2 text-sm font-semibold rounded-lg border border-[#DCD9D2] bg-white text-[#4B5563] hover:bg-[#EFECE6] disabled:opacity-40 disabled:cursor-not-allowed transition">Next \u2192</button>' +
                    '</div>' +
                '</div>';
            }}

            function prevPearl() {{
                if (currentPearlIndex > 0) {{
                    currentPearlIndex--;
                    updatePearlCounter();
                    renderPearl();
                }}
            }}

            function nextPearl() {{
                if (currentPearlIndex < filteredPearls.length - 1) {{
                    currentPearlIndex++;
                    updatePearlCounter();
                    renderPearl();
                }}
            }}

            async function openPearlPaper() {{
                const p = filteredPearls[currentPearlIndex];
                if (!p) return;
                let file = p.file_name;
                if (!file && p.source_paper) {{
                    file = paperToFile[p.source_paper];
                }}
                if (!file && p.source_paper) {{
                    file = p.source_paper.replace(/[^a-zA-Z0-9_-]/g, '_') + '.json';
                }}
                if (!file) return;
                const system = encodeURIComponent(p.system || 'General');
                const type = encodeURIComponent(p.type || 'Unclassified');
                try {{
                    const resp = await fetch('/api/summary?file_name=' + encodeURIComponent(file) + '&system=' + system + '&type=' + type);
                    const data = await resp.json();
                    if (!resp.ok || data.error) {{ alert('Summary not available for this paper.'); return; }}
                    const html = '<!DOCTYPE html><html><head><title>' + p.source_paper + '</title>' +
                        '<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"><' + '/script>' +
                        '<style>body{{font-family:Georgia,serif;color:#111827;line-height:1.6;padding:24px;max-width:900px;margin:0 auto;background:#FDFBF7;}}' +
                        'h1{{font-size:1.5rem;margin-bottom:8px;}}' +
                        '.meta{{color:#6B7280;font-size:0.85rem;margin-bottom:20px;}}' +
                        '.summary-body h2{{font-size:1.4em;font-weight:bold;margin-top:1.4em;margin-bottom:0.5em;border-bottom:1px solid #EFECE6;padding-bottom:0.3em;}}' +
                        '.summary-body h3{{font-size:1.15em;font-weight:bold;margin-top:1.2em;margin-bottom:0.4em;}}' +
                        '.summary-body p{{margin-bottom:1em;text-align:justify;}}' +
                        '.summary-body ul{{margin-left:1.5em;margin-bottom:1em;}}' +
                        '.summary-body li{{margin-bottom:0.4em;}}' +
                        '.summary-body strong{{color:#000;}}' +
                        '</style></head><body>' +
                        '<h1>' + p.source_paper + '</h1>' +
                        '<div class="meta">By ' + (data.authors || 'Unknown Authors') + '</div>' +
                        '<hr style="border:none;border-top:1px solid #EFECE6;margin:20px 0;">' +
                        '<div class="summary-body">' + (data.content ? marked.parse(data.content) : 'No content available.') + '</div>' +
                        '</body></html>';
                    const win = window.open('', '_blank');
                    win.document.write(html);
                    win.document.close();
                }} catch(e) {{
                    alert('Failed to load paper summary.');
                }}
            }}

            window.onload = initializeAppMatrix;
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/summary")
async def get_cached_json_summary_contents(file_name: str, system: str = "General", type: str = "Unclassified"):
    base_name = os.path.splitext(file_name)[0]

    clean_system = "".join(x for x in str(system) if x.isalnum() or x in "._- ").strip()
    clean_type = "".join(x for x in str(type) if x.isalnum() or x in "._- ").strip()

    target_json_path = os.path.join(OUTPUT_DIR, clean_system, clean_type, f"{base_name}.json")

    if not os.path.exists(target_json_path):
        target_json_path = os.path.join(OUTPUT_DIR, f"{base_name}.json")

    if not os.path.exists(target_json_path):
        return JSONResponse(status_code=404, content={"error": f"Summary target path not found: {target_json_path}"})

    try:
        with open(target_json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return {
            "content": payload.get("clinical_summary_markdown", ""),
            "authors": payload.get("primary_authors", "Unknown Authors")
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/search")
async def search_summaries(q: str = ""):
    if not q.strip():
        return {"matches": []}
    query = q.strip().lower()
    results = []
    if not os.path.exists(OUTPUT_DIR):
        return {"matches": results}
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for fname in files:
            if not fname.endswith(".json"):
                continue
            try:
                fpath = os.path.join(root, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                paper_name = payload.get("paper_name", "")
                content = payload.get("clinical_summary_markdown", "")
                if query in paper_name.lower() or query in content.lower():
                    results.append({
                        "file_name": fname,
                        "title": paper_name,
                        "system": payload.get("system", "Other"),
                        "type": payload.get("type_of_article", "Other"),
                        "journal": payload.get("journal_name", "Unknown Journal")
                    })
            except Exception:
                continue
    return {"matches": results}

@app.get("/api/pearls")
async def get_pearls(q: str = "", system: str = "", type: str = ""):
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
    return {"pearls": filtered, "total": len(filtered)}
