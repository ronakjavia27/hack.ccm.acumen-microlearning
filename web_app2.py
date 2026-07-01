import os
import json
import re
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

# =====================================================================
# 🌐 GLOBAL CORE WORKSPACE SETTINGS & LINK MATRIX
# =====================================================================
FEEDBACK_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSd6xRmmimmVc0Sv4AeNls-oxLR6k_zX8D_QERFZwPP6zlfjRw/viewform?usp=header"
SUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSffsrF8DPWaTa-03XisMqSU5Da_8QdE-JrINdDP5iRmvWAI8Q/viewform?usp=header"
UNSUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScz864mkLh5AqBYVzAh573hWu98NdmwwPC2vaU1lfBE3WHHHg/viewform?usp=header"

OUTPUT_DIR = "./output_files"
JSON_TRACKER_FILE = "./sent_summaries.json"
PEARLS_JSON = "./pearls.json"

app = FastAPI()

def load_approved_ledger():
    """Load all entries from sent_summaries.json (sole source of truth)."""
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
        # Ensure all expected keys exist with defaults
        expected_keys = ["id", "timestamp", "source_paper", "doi", "author", "system", "type", "pearl", "remarks", "file_name", "topic"]
        for entry in data:
            for k in expected_keys:
                if k not in entry:
                    entry[k] = ""
        return data
    except (json.JSONDecodeError, Exception):
        return []

@app.get("/", response_class=HTMLResponse)
async def render_dashboard_portal(request: Request):
    entries = load_approved_ledger()

    total_published = 0
    unique_systems = 0

    articles_list = []
    if entries:
        for idx, entry in enumerate(entries):
            raw_doi = str(entry.get("doi", "")).strip()
            clean_doi_url = "#"
            if raw_doi and raw_doi.lower() not in ["none", "nan", ""]:
                if raw_doi.startswith("http://") or raw_doi.startswith("https://"):
                    clean_doi_url = raw_doi
                else:
                    clean_doi_url = f"https://doi.org/{raw_doi}"

            articles_list.append({
                "id": str(idx),
                "title": str(entry.get("title", "Unknown Title")),
                "authors": str(entry.get("authors", "Unknown Authors")),
                "system": str(entry.get("system", "General")),
                "journal": str(entry.get("journal", "Unknown Source")),
                "type": str(entry.get("type", "Unclassified")),
                "doi": clean_doi_url,
                "file_name": str(entry.get("file_name", "")),
                "date_added": str(entry.get("date_added", "")),
                "year": str(entry.get("year", "")),
                "show_on_web": str(entry.get("show_on_web", "No")).strip().lower()
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
    if entries:
        for entry in entries:
            name = str(entry.get("title", "")).strip()
            fname = str(entry.get("file_name", "")).strip()
            if name and fname and fname.lower() != "nan":
                json_name = os.path.splitext(fname)[0] + ".json"
                paper_to_file[name] = json_name

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en" data-theme="light" data-font-size="md">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>hack.CCM | Knowledge Portal</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <style>
            :root {{
                --color-body: #FDFBF7;
                --color-card: #FFFFFF;
                --color-muted: #EFECE6;
                --color-muted-hover: #E2DFD7;
                --color-active-card: #D7CDB7;
                --color-nav: #F5F3F0;
                --color-primary: #111827;
                --color-secondary: #4B5563;
                --color-active-text: #5C5346;
                --color-accent: #1D4ED8;
                --color-accent-hover: #2563EB;
                --color-border: #EFECE6;
                --color-border-dark: #DCD9D2;
                --color-border-hover: #BDB199;
                --color-overlay: rgba(0,0,0,0.3);
                --color-shadow: rgba(0,0,0,0.04);
                --color-badge-blue-bg: #EFF6FF;
                --color-badge-blue-text: #1E40AF;
                --color-badge-blue-border: #DBEAFE;
                --font-scale: 1;
            }}
            [data-theme="dark"] {{
                --color-body: #0F172A;
                --color-card: #1E293B;
                --color-muted: #334155;
                --color-muted-hover: #475569;
                --color-active-card: #475569;
                --color-nav: #1E293B;
                --color-primary: #F1F5F9;
                --color-secondary: #94A3B8;
                --color-active-text: #F1F5F9;
                --color-accent: #60A5FA;
                --color-accent-hover: #93C5FD;
                --color-border: #475569;
                --color-border-dark: #64748B;
                --color-border-hover: #94A3B8;
                --color-overlay: rgba(0,0,0,0.5);
                --color-shadow: rgba(0,0,0,0.3);
                --color-badge-blue-bg: #1E3A5F;
                --color-badge-blue-text: #93C5FD;
                --color-badge-blue-border: #1E40AF;
            }}
            [data-font-size="sm"] {{ --font-scale: 0.85; }}
            [data-font-size="lg"] {{ --font-scale: 1.15; }}

            body {{ background-color: var(--color-body); color: var(--color-primary); font-family: 'Georgia', serif; font-size: calc(16px * var(--font-scale)); }}
            .bg-body {{ background-color: var(--color-body); }}
            .bg-card {{ background-color: var(--color-card); }}
            .bg-muted {{ background-color: var(--color-muted); }}
            .bg-muted-hover {{ background-color: var(--color-muted-hover); }}
            .bg-active-card {{ background-color: var(--color-active-card); }}
            .bg-nav {{ background-color: var(--color-nav); }}
            .bg-accent {{ background-color: var(--color-accent); }}
            .bg-badge-blue {{ background-color: var(--color-badge-blue-bg); }}
            .text-primary {{ color: var(--color-primary); }}
            .text-secondary {{ color: var(--color-secondary); }}
            .text-active-card {{ color: var(--color-active-text); }}
            .text-accent {{ color: var(--color-accent); }}
            .text-badge-blue {{ color: var(--color-badge-blue-text); }}
            .border-muted {{ border-color: var(--color-border); }}
            .border-dark {{ border-color: var(--color-border-dark); }}
            .border-hover {{ border-color: var(--color-border-hover); }}
            .border-accent {{ border-color: var(--color-accent); }}
            .border-badge-blue {{ border-color: var(--color-badge-blue-bg); }}
            .hover\:bg-muted-hover:hover {{ background-color: var(--color-muted-hover); }}
            .hover\:bg-body:hover {{ background-color: var(--color-body); }}
            .hover\:bg-accent-hover:hover {{ background-color: var(--color-accent-hover); }}
            .hover\:bg-badge-blue:hover {{ background-color: var(--color-badge-blue-bg); }}
            .hover\:text-accent-hover:hover {{ color: var(--color-accent-hover); }}
            .hover\:border-dark:hover {{ border-color: var(--color-border-dark); }}
            .hover\:border-hover:hover {{ border-color: var(--color-border-hover); }}
            .focus\:ring-accent:focus {{ --tw-ring-color: var(--color-accent); }}
            .ring-hover {{ --tw-ring-color: var(--color-border-hover); }}

            .custom-scrollbar::-webkit-scrollbar {{ width: 6px; }}
            .custom-scrollbar::-webkit-scrollbar-track {{ background: var(--color-body); }}
            .custom-scrollbar::-webkit-scrollbar-thumb {{ background: var(--color-muted); border-radius: 3px; }}
            .summary-body h2 {{ font-size: 1.5em; font-weight: bold; margin-top: 1.6em; margin-bottom: 0.6em; color: #000000; border-bottom: 1px solid var(--color-border); padding-bottom: 0.4em; font-family: 'Georgia', serif; }}
            .summary-body h3 {{ font-size: 1.25em; font-weight: bold; margin-top: 1.4em; margin-bottom: 0.5em; color: var(--color-primary); font-family: 'Georgia', serif; }}
            .summary-body p {{ margin-bottom: 1.2em; line-height: 1.65; text-align: justify; font-family: system-ui, -apple-system, sans-serif; color: var(--color-primary); }}
            .summary-body ul {{ list-style-type: disc !important; margin-left: 1.5em !important; margin-bottom: 1.2em !important; padding-left: 0px !important; }}
            .summary-body ol {{ list-style-type: decimal !important; margin-left: 1.5em !important; margin-bottom: 1.2em !important; padding-left: 0px !important; }}
            .summary-body li {{ margin-bottom: 0.5em; line-height: 1.6; font-family: system-ui, -apple-system, sans-serif; color: var(--color-primary); display: list-item !important; }}
            .summary-body strong {{ color: #000000; font-weight: 700; }}
            .summary-section {{ margin-bottom: 0.75rem; border: 1px solid var(--color-border); border-radius: 0.75rem; overflow: hidden; background: var(--color-card); }}
            .summary-section[open] {{ border-color: var(--color-border-dark); }}
            .summary-heading {{ padding: 0.75rem 1rem; font-weight: 700; font-size: 0.9375em; cursor: pointer; background: var(--color-muted); color: var(--color-primary); user-select: none; font-family: system-ui, -apple-system, sans-serif; transition: background 0.15s; }}
            .summary-heading:hover {{ background: var(--color-muted-hover); }}
            .summary-heading::-webkit-details-marker {{ color: var(--color-secondary); }}
            .summary-content {{ padding: 1rem 1.25rem; }}
            .summary-content-intro {{ padding: 0 0.25rem 1rem 0.25rem; }}
            .tab-panel {{ display: none; }}
            .tab-panel.active {{ display: block; }}
            .no-scroll {{ overflow: hidden; }}
            .scrollbar-none::-webkit-scrollbar {{ display: none; }}
            .scrollbar-none {{ -ms-overflow-style: none; scrollbar-width: none; }}
            @keyframes fadeIn {{ from{{opacity:0;transform:translateY(-10px)}} to{{opacity:1;transform:translateY(0)}} }}
            @keyframes slideDown {{ from{{opacity:0;transform:translateY(-8px)}} to{{opacity:1;transform:translateY(0)}} }}
            .modal-animate {{ animation: fadeIn 0.2s ease-out; }}
            #tabDropdown {{ animation: slideDown 0.15s ease-out; }}
            #tabDropdown button.active-tab {{ background-color: var(--color-accent); color: white; }}
        </style>
    </head>
    <body class="p-4 md:p-8 max-w-7xl mx-auto">

        <!-- Sidebar Overlay -->
        <div id="sidebarOverlay" class="fixed inset-0 z-50 bg-black/30 hidden transition-opacity" onclick="toggleSidebar()"></div>

        <!-- Sidebar Drawer -->
        <div id="sidebar" class="fixed top-0 left-0 z-50 h-full w-72 bg-card shadow-xl border-r border-muted transform -translate-x-full transition-transform duration-300 p-6 overflow-y-auto flex flex-col">
            <div class="flex justify-between items-start mb-6">
                <div class="text-lg font-extrabold text-primary">🧠 hack.CCM</div>
                <button onclick="toggleSidebar()" class="text-xl p-1 hover:bg-muted-hover rounded-lg transition leading-none">✕</button>
            </div>
            <nav class="space-y-1 flex-1">
                <a onclick="switchTabAndClose('papers')" class="block px-4 py-3 rounded-xl hover:bg-muted-hover font-semibold text-primary cursor-pointer transition text-sm">📄 Papers</a>
                <a onclick="switchTabAndClose('guidelines')" class="block px-4 py-3 rounded-xl hover:bg-muted-hover font-semibold text-primary cursor-pointer transition text-sm">📋 Guidelines</a>
                <a onclick="switchTabAndClose('pearls')" class="block px-4 py-3 rounded-xl hover:bg-muted-hover font-semibold text-primary cursor-pointer transition text-sm">💡 Pearls</a>
                <a onclick="switchTabAndClose('antibiotics')" class="block px-4 py-3 rounded-xl hover:bg-muted-hover font-semibold text-primary cursor-pointer transition text-sm">💊 Antibiotics <span class="text-secondary text-[10px] font-normal">(soon)</span></a>
                <a onclick="switchTabAndClose('theory')" class="block px-4 py-3 rounded-xl hover:bg-muted-hover font-semibold text-primary cursor-pointer transition text-sm">🧠 Theory <span class="text-secondary text-[10px] font-normal">(soon)</span></a>
                <a onclick="switchTabAndClose('ask-ai')" class="block px-4 py-3 rounded-xl hover:bg-muted-hover font-semibold text-secondary cursor-pointer transition text-sm opacity-60">🤖 Ask AI <span class="text-secondary text-[10px] font-normal">(soon)</span></a>
            </nav>
            <hr class="my-4 border-muted">
            <nav class="space-y-1">
                <a onclick="openBookmarksModal()" class="block px-4 py-3 rounded-xl hover:bg-muted-hover font-semibold text-primary cursor-pointer transition text-sm">🔖 Bookmarks</a>
                <a onclick="openAboutModal()" class="block px-4 py-3 rounded-xl hover:bg-muted-hover font-semibold text-primary cursor-pointer transition text-sm">ℹ️ About</a>
                <a onclick="openSettingsModal()" class="block px-4 py-3 rounded-xl hover:bg-muted-hover font-semibold text-primary cursor-pointer transition text-sm">⚙️ Settings</a>
            </nav>
            <hr class="my-4 border-muted">
            <nav class="space-y-1">
                <a href="{FEEDBACK_FORM_URL}" target="_blank" class="block px-4 py-2 rounded-xl hover:bg-muted-hover text-secondary cursor-pointer transition text-sm">📝 Feedback</a>
                <a href="{SUBSCRIBE_FORM_URL}" target="_blank" class="block px-4 py-2 rounded-xl hover:bg-muted-hover text-secondary cursor-pointer transition text-sm">📢 Subscribe</a>
                <a href="{UNSUBSCRIBE_FORM_URL}" target="_blank" class="block px-4 py-2 rounded-xl hover:bg-muted-hover text-secondary cursor-pointer transition text-sm">❌ Unsubscribe</a>
            </nav>
            <hr class="my-4 border-muted">
            <a onclick="toast('🔑 Login — coming in a future update')" class="block px-4 py-2 rounded-xl text-secondary opacity-50 cursor-pointer transition text-sm hover:bg-muted-hover">🔑 Login <span class="text-[10px]">(future)</span></a>
        </div>

        <!-- Universal Search Modal -->
        <div id="searchOverlay" class="fixed inset-0 z-50 bg-black/30 hidden" onclick="closeUniversalSearch()"></div>
        <div id="searchModal" class="modal-animate fixed top-[15%] left-1/2 -translate-x-1/2 w-[90%] max-w-2xl z-50 bg-card rounded-2xl shadow-2xl border border-muted max-h-[65vh] flex flex-col hidden">
            <div class="p-4 border-b border-muted flex items-center gap-3">
                <span class="text-lg">🔍</span>
                <input type="text" id="universalSearchInput" placeholder="Search Papers, Guidelines, Pearls..." class="flex-1 text-sm sm:text-base bg-transparent border-none outline-none text-primary" oninput="performUniversalSearch(this.value)">
                <button onclick="closeUniversalSearch()" class="text-lg p-1 hover:bg-muted-hover rounded-lg transition leading-none">✕</button>
            </div>
            <div id="universalSearchResults" class="flex-1 overflow-y-auto p-4 space-y-4">
                <p class="text-xs text-secondary text-center py-8">Type to search across all content...</p>
            </div>
        </div>

        <!-- Bookmarks Modal -->
        <div id="bookmarksOverlay" class="fixed inset-0 z-50 bg-black/30 hidden" onclick="closeBookmarksModal()"></div>
        <div id="bookmarksModal" class="modal-animate fixed top-[15%] left-1/2 -translate-x-1/2 w-[90%] max-w-xl z-50 bg-card rounded-2xl shadow-2xl border border-muted max-h-[65vh] flex flex-col hidden">
            <div class="p-4 border-b border-muted flex justify-between items-center">
                <h3 class="text-sm font-bold text-primary">🔖 Bookmarks</h3>
                <button onclick="closeBookmarksModal()" class="text-lg p-1 hover:bg-muted-hover rounded-lg transition leading-none">✕</button>
            </div>
            <div class="px-4 py-2 border-b border-muted">
                <input type="text" id="bookmarkSearchInput" placeholder="Search bookmarks..." class="w-full text-sm bg-muted text-primary px-3 py-2 rounded-lg border border-dark outline-none focus:ring-2 focus:ring-accent transition" oninput="filterBookmarks()">
            </div>
            <div id="bookmarksList" class="flex-1 overflow-y-auto p-4 space-y-2">
                <p class="text-xs text-secondary text-center py-8">Loading...</p>
            </div>
        </div>

        <!-- About Modal -->
        <div id="aboutOverlay" class="fixed inset-0 z-50 bg-black/30 hidden" onclick="closeAboutModal()"></div>
        <div id="aboutModal" class="modal-animate fixed top-[20%] left-1/2 -translate-x-1/2 w-[90%] max-w-md z-50 bg-card rounded-2xl shadow-2xl border border-muted p-6 hidden">
            <div class="flex justify-between items-start mb-4">
                <h3 class="text-lg font-extrabold text-primary">🧠 hack.CCM</h3>
                <button onclick="closeAboutModal()" class="text-lg p-1 hover:bg-muted-hover rounded-lg transition leading-none">✕</button>
            </div>
            <p class="text-sm text-secondary mb-4">Critical Care Knowledge Portal — a curated repository of critical care publications, guidelines, and clinical pearls for rapid point-of-care reference.</p>
            <p class="text-xs text-secondary">Version 2.0</p>
        </div>

        <!-- Settings Modal -->
        <div id="settingsOverlay" class="fixed inset-0 z-50 bg-black/30 hidden" onclick="closeSettingsModal()"></div>
        <div id="settingsModal" class="modal-animate fixed top-[15%] left-1/2 -translate-x-1/2 w-[90%] max-w-md z-50 bg-card rounded-2xl shadow-2xl border border-muted p-6 hidden">
            <div class="flex justify-between items-start mb-6">
                <h3 class="text-lg font-bold text-primary">⚙️ Settings</h3>
                <button onclick="closeSettingsModal()" class="text-lg p-1 hover:bg-muted-hover rounded-lg transition leading-none">✕</button>
            </div>
            <div class="space-y-6">
                <div>
                    <label class="block text-sm font-bold text-primary mb-3">🌙 Dark Mode</label>
                    <div class="flex gap-3">
                        <button onclick="setTheme('light')" id="themeBtn_light" class="flex-1 px-4 py-2.5 text-sm font-semibold rounded-xl border-2 transition-all bg-card text-primary border-dark hover:bg-muted-hover">☀️ Light</button>
                        <button onclick="setTheme('dark')" id="themeBtn_dark" class="flex-1 px-4 py-2.5 text-sm font-semibold rounded-xl border-2 transition-all bg-accent text-white border-accent">🌙 Dark</button>
                    </div>
                </div>
                <div>
                    <label class="block text-sm font-bold text-primary mb-3">🔤 Font Size</label>
                    <div class="flex gap-3">
                        <button onclick="setFontSize('sm')" id="fontBtn_sm" class="flex-1 px-4 py-2.5 text-sm font-semibold rounded-xl border-2 transition-all bg-card text-primary border-dark hover:bg-muted-hover">A⁻ Small</button>
                        <button onclick="setFontSize('md')" id="fontBtn_md" class="flex-1 px-4 py-2.5 text-sm font-semibold rounded-xl border-2 transition-all bg-accent text-white border-accent">A Medium</button>
                        <button onclick="setFontSize('lg')" id="fontBtn_lg" class="flex-1 px-4 py-2.5 text-sm font-semibold rounded-xl border-2 transition-all bg-card text-primary border-dark hover:bg-muted-hover">A⁺ Large</button>
                    </div>
                </div>
                <p class="text-xs text-secondary text-center pt-2">Preferences are saved automatically.</p>
            </div>
        </div>

        <!-- Toast container -->
        <div id="toastContainer" class="fixed bottom-6 left-1/2 -translate-x-1/2 z-[60] hidden"></div>

        <header class="bg-card border border-muted p-5 md:p-6 rounded-2xl shadow-md mb-6 flex flex-col sm:flex-row justify-between items-center gap-4">
            <div class="flex items-start gap-4 w-full sm:w-auto">
                <button onclick="toggleSidebar()" class="shrink-0 text-3xl md:text-5xl p-0 -ml-1.5 mt-0 leading-none hover:bg-muted-hover rounded-lg transition" title="Menu">☰</button>
                <div class="w-1 h-12 md:h-16 bg-accent rounded-full shrink-0 mt-1"></div>
                <div>
                    <div class="text-2xl md:text-4xl font-extrabold tracking-tight text-primary">🧠 hack.CCM</div>
                    <div class="text-sm md:text-base font-medium text-secondary tracking-wide">Critical Care Knowledge Portal</div>
                </div>
            </div>
            <nav class="flex flex-wrap gap-2 md:gap-3 text-xs md:text-sm font-semibold">
                <a href="{FEEDBACK_FORM_URL}" target="_blank" class="bg-nav px-3 py-1.5 rounded-lg text-accent hover:bg-muted-hover hover:text-accent-hover transition">📝 Feedback</a>
                <a href="{SUBSCRIBE_FORM_URL}" target="_blank" class="bg-nav px-3 py-1.5 rounded-lg text-accent hover:bg-muted-hover hover:text-accent-hover transition">📢 Subscribe</a>
                <a href="{UNSUBSCRIBE_FORM_URL}" target="_blank" class="bg-nav px-3 py-1.5 rounded-lg text-accent hover:bg-muted-hover hover:text-accent-hover transition">❌ Unsubscribe</a>
            </nav>
        </header>

        <div id="dailyPaperPanel" class="bg-card border border-muted p-4 rounded-xl shadow-sm mb-4 cursor-pointer transition hover:bg-body hover:border-dark" onclick="openDailyPaper()">
            <div class="flex items-start gap-3">
                <div class="text-2xl shrink-0 mt-0.5">⭐</div>
                <div class="flex-1 min-w-0">
                    <div class="text-[10px] font-bold tracking-wider text-secondary uppercase mb-1">📌 Paper of the Day</div>
                    <div id="dailyPaperTitle" class="text-sm font-bold text-primary leading-snug">Loading...</div>
                    <div id="dailyPaperMeta" class="text-xs text-secondary mt-1 space-x-2">
                        <span id="dailyPaperAuthors" class="italic"></span>
                        <span id="dailyPaperSystem" class="bg-muted px-1.5 py-0.5 rounded text-[10px] font-bold uppercase"></span>
                        <span id="dailyPaperType" class="bg-muted px-1.5 py-0.5 rounded text-[10px] font-bold uppercase"></span>
                    </div>
                </div>
                <div class="text-xs font-semibold text-accent shrink-0 self-center hover:underline">Read →</div>
            </div>
        </div>

        <div id="dailyPearlPanel" class="bg-card border border-muted p-4 rounded-xl shadow-sm mb-4 cursor-pointer transition hover:bg-body hover:border-dark" onclick="openDailyPearl()">
            <div class="flex items-start gap-3">
                <div class="text-2xl shrink-0 mt-0.5">💎</div>
                <div class="flex-1 min-w-0">
                    <div class="text-[10px] font-bold tracking-wider text-secondary uppercase mb-1">💎 Pearl of the Day</div>
                    <div id="dailyPearlText" class="text-sm font-bold text-primary leading-snug">Loading...</div>
                    <div id="dailyPearlMeta" class="text-xs text-secondary mt-1 space-x-2">
                        <span id="dailyPearlSystem" class="bg-muted px-1.5 py-0.5 rounded text-[10px] font-bold uppercase"></span>
                        <span id="dailyPearlType" class="bg-muted px-1.5 py-0.5 rounded text-[10px] font-bold uppercase"></span>
                        <span id="dailyPearlSource" class="italic"></span>
                    </div>
                </div>
                <div class="text-xs font-semibold text-accent shrink-0 self-center hover:underline">Read →</div>
            </div>
        </div>

        <nav id="stickyTabBar" class="sticky top-0 z-40 bg-card/95 backdrop-blur-md border-b border-muted shadow-sm mb-6 -mx-4 md:-mx-8 px-4 md:px-8 flex items-center gap-1 py-2 scrollbar-none" style="font-family: system-ui, sans-serif;">
            <button onclick="toggleTabDropdown()" class="shrink-0 p-1.5 rounded-lg hover:bg-muted-hover transition text-lg leading-none" title="All Tabs">≡</button>
            <div id="tabDropdown" class="hidden absolute top-full left-0 mt-1 w-48 bg-card border border-muted rounded-xl shadow-xl z-50 py-1.5" style="min-width:170px;">
                <button onclick="switchTabAndCloseDropdown('papers')" class="w-full text-left px-4 py-2.5 text-sm font-semibold rounded-lg hover:bg-muted-hover transition text-primary">📄 Papers</button>
                <button onclick="switchTabAndCloseDropdown('guidelines')" class="w-full text-left px-4 py-2.5 text-sm font-semibold rounded-lg hover:bg-muted-hover transition text-primary">📋 Guidelines</button>
                <button onclick="switchTabAndCloseDropdown('pearls')" class="w-full text-left px-4 py-2.5 text-sm font-semibold rounded-lg hover:bg-muted-hover transition text-primary">💡 Pearls</button>
                <button onclick="switchTabAndCloseDropdown('antibiotics')" class="w-full text-left px-4 py-2.5 text-sm font-semibold rounded-lg hover:bg-muted-hover transition text-primary">💊 Antibiotics</button>
                <button onclick="switchTabAndCloseDropdown('theory')" class="w-full text-left px-4 py-2.5 text-sm font-semibold rounded-lg hover:bg-muted-hover transition text-primary">🧠 Theory</button>
                <button onclick="switchTabAndCloseDropdown('ask-ai')" class="w-full text-left px-4 py-2.5 text-sm font-semibold rounded-lg hover:bg-muted-hover transition text-secondary opacity-60">🤖 Ask AI</button>
                <hr class="my-1 mx-2 border-muted">
                <button onclick="document.getElementById('tabDropdown').classList.add('hidden');openBookmarksModal()" class="w-full text-left px-4 py-2.5 text-sm font-semibold rounded-lg hover:bg-muted-hover transition text-primary">🔖 Bookmarks</button>
            </div>
            <div class="flex gap-1 flex-1 overflow-x-auto scrollbar-none" style="scrollbar-width:none;">
                <button onclick="switchTab('papers')" id="tabBtn_papers" class="shrink-0 px-3 py-1.5 sm:px-5 sm:py-2.5 text-xs sm:text-sm font-bold rounded-full transition-all whitespace-nowrap bg-accent text-white shadow-sm">📄<span class="hidden sm:inline ml-1">Papers</span></button>
                <button onclick="switchTab('guidelines')" id="tabBtn_guidelines" class="shrink-0 px-3 py-1.5 sm:px-5 sm:py-2.5 text-xs sm:text-sm font-bold rounded-full transition-all whitespace-nowrap bg-transparent text-secondary hover:bg-muted-hover">📋<span class="hidden sm:inline ml-1">Guidelines</span></button>
                <button onclick="switchTab('pearls')" id="tabBtn_pearls" class="shrink-0 px-3 py-1.5 sm:px-5 sm:py-2.5 text-xs sm:text-sm font-bold rounded-full transition-all whitespace-nowrap bg-transparent text-secondary hover:bg-muted-hover">💡<span class="hidden sm:inline ml-1">Pearls</span></button>
                <button onclick="switchTab('antibiotics')" id="tabBtn_antibiotics" class="shrink-0 px-3 py-1.5 sm:px-5 sm:py-2.5 text-xs sm:text-sm font-bold rounded-full transition-all whitespace-nowrap bg-transparent text-secondary hover:bg-muted-hover">💊<span class="hidden sm:inline ml-1">Antibiotics</span></button>
                <button onclick="switchTab('theory')" id="tabBtn_theory" class="shrink-0 px-3 py-1.5 sm:px-5 sm:py-2.5 text-xs sm:text-sm font-bold rounded-full transition-all whitespace-nowrap bg-transparent text-secondary hover:bg-muted-hover">🧠<span class="hidden sm:inline ml-1">Theory</span></button>
                <button onclick="switchTab('ask-ai')" id="tabBtn_ask-ai" class="shrink-0 px-3 py-1.5 sm:px-5 sm:py-2.5 text-xs sm:text-sm font-bold rounded-full transition-all whitespace-nowrap bg-transparent text-secondary hover:bg-muted-hover opacity-60">🤖<span class="hidden sm:inline ml-1">Ask AI</span></button>
            </div>
            <button onclick="openUniversalSearch()" class="shrink-0 p-1.5 rounded-lg hover:bg-muted-hover transition text-lg leading-none" title="Search (Ctrl+K)">🔍</button>
        </nav>

        <main class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="space-y-6">
                <div class="bg-muted p-5 rounded-2xl border border-dark">
                    <h3 class="text-xs font-bold tracking-wider text-secondary uppercase mb-3">📊 Portal Status</h3>
                    <div class="flex gap-3">
                        <span class="bg-card px-3 py-1.5 rounded-lg text-xs font-bold border border-dark"><span id="statusIcon">📋</span> <span id="statusCount">0</span> <span id="statusLabel">Papers</span></span>
                        <span class="bg-card px-3 py-1.5 rounded-lg text-xs font-bold border border-dark">🧬 <span id="statusSystems">0</span> Specialties</span>
                    </div>
                </div>

                <!-- Papers Filter Panel -->
                <div id="filterPanel_papers" class="tab-panel active bg-muted p-5 rounded-2xl border border-dark space-y-4">
                    <h3 class="text-xs font-bold tracking-wider text-secondary uppercase mb-1">🔍 Filter Papers</h3>
                    <div>
                        <label class="block text-xs font-bold mb-1 text-secondary">Keywords Search</label>
                        <div style="position:relative;">
                            <input type="text" id="titleSearch_papers" onkeyup="onSearchInput('papers')" placeholder="Type keywords..." class="w-full bg-card text-primary text-sm p-2.5 rounded-lg border border-dark focus:outline-none focus:ring-2 focus:ring-accent transition pr-8">
                            <button id="clearSearch_papers" onclick="clearSearch('papers')" style="display:none; position:absolute; right:6px; top:50%; transform:translateY(-50%); background:none; border:none; cursor:pointer; font-size:14px; color:var(--color-secondary); padding:4px; line-height:1;">✕</button>
                        </div>
                        <label class="flex items-center gap-2 mt-2 cursor-pointer">
                            <input type="checkbox" id="fulltextToggle_papers" onchange="onFullTextToggle('papers')" class="rounded border-dark text-accent focus:ring-accent">
                            <span class="text-[10px] font-bold text-secondary uppercase tracking-wider">🔍 Search full text</span>
                        </label>
                    </div>
                    <div>
                        <label class="block text-xs font-bold mb-1 text-secondary">Specialty Group</label>
                        <select id="systemFilter_papers" onchange="executeClientSideFilter()" class="w-full bg-card text-primary text-sm p-2.5 rounded-lg border border-dark focus:outline-none focus:ring-2 focus:ring-accent transition">
                            <option value="All">All Specialties</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold mb-1 text-secondary">Subtype</label>
                        <select id="typeFilter_papers" onchange="executeClientSideFilter()" class="w-full bg-card text-primary text-sm p-2.5 rounded-lg border border-dark focus:outline-none focus:ring-2 focus:ring-accent transition">
                            <option value="All">All Types</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold mb-1 text-secondary">Sort By</label>
                        <select id="sortBy_papers" onchange="setSortBy(this.value)" class="w-full bg-card text-primary text-sm p-2.5 rounded-lg border border-dark focus:outline-none focus:ring-2 focus:ring-accent transition">
                            <option value="added">Date Added (newest)</option>
                            <option value="published">Year Published (newest)</option>
                        </select>
                    </div>
                </div>

                <!-- Guidelines Filter Panel -->
                <div id="filterPanel_guidelines" class="tab-panel bg-muted p-5 rounded-2xl border border-dark space-y-4">
                    <h3 class="text-xs font-bold tracking-wider text-secondary uppercase mb-1">🔍 Filter Guidelines</h3>
                    <div>
                        <label class="block text-xs font-bold mb-1 text-secondary">Keywords Search</label>
                        <div style="position:relative;">
                            <input type="text" id="titleSearch_guidelines" onkeyup="onSearchInput('guidelines')" placeholder="Type keywords..." class="w-full bg-card text-primary text-sm p-2.5 rounded-lg border border-dark focus:outline-none focus:ring-2 focus:ring-accent transition pr-8">
                            <button id="clearSearch_guidelines" onclick="clearSearch('guidelines')" style="display:none; position:absolute; right:6px; top:50%; transform:translateY(-50%); background:none; border:none; cursor:pointer; font-size:14px; color:var(--color-secondary); padding:4px; line-height:1;">✕</button>
                        </div>
                        <label class="flex items-center gap-2 mt-2 cursor-pointer">
                            <input type="checkbox" id="fulltextToggle_guidelines" onchange="onFullTextToggle('guidelines')" class="rounded border-dark text-accent focus:ring-accent">
                            <span class="text-[10px] font-bold text-secondary uppercase tracking-wider">🔍 Search full text</span>
                        </label>
                    </div>
                    <div>
                        <label class="block text-xs font-bold mb-1 text-secondary">System</label>
                        <select id="systemFilter_guidelines" onchange="executeClientSideFilter()" class="w-full bg-card text-primary text-sm p-2.5 rounded-lg border border-dark focus:outline-none focus:ring-2 focus:ring-accent transition">
                            <option value="All">All Systems</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold mb-1 text-secondary">Sort By</label>
                        <select id="sortBy_guidelines" onchange="setSortBy(this.value)" class="w-full bg-card text-primary text-sm p-2.5 rounded-lg border border-dark focus:outline-none focus:ring-2 focus:ring-accent transition">
                            <option value="added">Date Added (newest)</option>
                            <option value="published">Year Published (newest)</option>
                        </select>
                    </div>
                </div>

                <!-- Pearls Filter Panel -->
                <div id="filterPanel_pearls" class="tab-panel bg-muted p-5 rounded-2xl border border-dark space-y-4">
                    <h3 class="text-xs font-bold tracking-wider text-secondary uppercase mb-1">🔍 Filter Pearls</h3>
                    <div>
                        <label class="block text-xs font-bold mb-1 text-secondary">Keywords Search</label>
                        <div style="position:relative;">
                            <input type="text" id="topicSearch_pearls" oninput="onPearlSearchInput()" placeholder="Search topic or pearl text..." class="w-full bg-card text-primary text-sm p-2.5 rounded-lg border border-dark focus:outline-none focus:ring-2 focus:ring-accent transition pr-8">
                            <button id="clearPearlSearch" onclick="clearPearlSearch()" style="display:none; position:absolute; right:6px; top:50%; transform:translateY(-50%); background:none; border:none; cursor:pointer; font-size:14px; color:var(--color-secondary); padding:4px; line-height:1;">✕</button>
                        </div>
                    </div>
                    <div>
                        <label class="block text-xs font-bold mb-1 text-secondary">Specialty Group</label>
                        <select id="systemFilter_pearls" onchange="executePearlsFilter()" class="w-full bg-card text-primary text-sm p-2.5 rounded-lg border border-dark focus:outline-none focus:ring-2 focus:ring-accent transition">
                            <option value="All">All Specialties</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-bold mb-1 text-secondary">Subtype</label>
                        <select id="typeFilter_pearls" onchange="executePearlsFilter()" class="w-full bg-card text-primary text-sm p-2.5 rounded-lg border border-dark focus:outline-none focus:ring-2 focus:ring-accent transition">
                            <option value="All">All Types</option>
                        </select>
                    </div>
                    <div class="text-xs font-semibold text-secondary" id="pearlCountDisplay">Select filters above</div>
                </div>

                <!-- Antibiotics Filter Panel -->
                <div id="filterPanel_antibiotics" class="tab-panel bg-muted p-5 rounded-2xl border border-dark space-y-4">
                    <h3 class="text-xs font-bold tracking-wider text-secondary uppercase">💊 Antibiotics</h3>
                    <p class="text-xs text-secondary">Coming soon</p>
                </div>

                <!-- Theory Filter Panel -->
                <div id="filterPanel_theory" class="tab-panel bg-muted p-5 rounded-2xl border border-dark space-y-4">
                    <h3 class="text-xs font-bold tracking-wider text-secondary uppercase">🧠 Theory</h3>
                    <p class="text-xs text-secondary">Coming soon</p>
                </div>

                <!-- Ask AI Filter Panel -->
                <div id="filterPanel_ask-ai" class="tab-panel bg-muted p-5 rounded-2xl border border-dark space-y-4">
                    <h3 class="text-xs font-bold tracking-wider text-secondary uppercase">🤖 Ask AI</h3>
                    <p class="text-xs text-secondary">Coming soon</p>
                </div>

                <div class="space-y-2">
                    <h3 id="deckLabel" class="text-xs font-bold tracking-wider text-secondary uppercase px-2">📑 Document Selector</h3>
                    <div id="articlesListDeck" class="max-h-[450px] overflow-y-auto custom-scrollbar space-y-2 pr-1"></div>
                </div>
            </div>

            <div class="md:col-span-2">
                <div id="documentSheetContainer" class="bg-card border border-muted p-6 md:p-8 rounded-2xl shadow-xs min-h-[550px]">
                    <div class="text-center py-24 text-secondary">
                        <p class="text-sm md:text-lg font-medium">👋 Welcome to hack.CCM Repository</p>
                        <p class="text-xs md:text-sm mt-1">Select a publication entry card from the index frame to unpack formatting layers.</p>
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

            // =====================================================================
            // SPECIALTY COLOR MAP
            // =====================================================================
            const SYSTEM_COLOR_MAP = {{
                "Cardiology": "#EF4444", "Neurology": "#8B5CF6", "Nephrology": "#F59E0B",
                "Pulmonology": "#3B82F6", "Gastroenterology": "#10B981", "Infectious Diseases": "#EC4899",
                "Hematology": "#E11D48", "Hepatology": "#14B8A6", "Immunology": "#A855F7",
                "Sepsis": "#F97316", "Trauma": "#DC2626", "Endocrinology": "#06B6D4",
                "General": "#6B7280", "Multi-system": "#6366F1", "Multisystem": "#6366F1",
                "Nutrition": "#84CC16", "Obstetrics and Gynecology": "#D946EF", "Rheumatology": "#0EA5E9",
                "Toxicology": "#7C3AED", "Oncology": "#059669", "Surgery": "#D97706", "Other": "#9333EA"
            }};
            function getSystemColor(system) {{ return SYSTEM_COLOR_MAP[system] || '#6B7280'; }}

            // =====================================================================
            // BOOKMARKS (localStorage)
            // =====================================================================
            function loadBookmarks() {{
                try {{ return JSON.parse(localStorage.getItem('hackCCM_bookmarks')) || []; }} catch(e) {{ return []; }}
            }}
            function saveBookmarks(bookmarks) {{
                localStorage.setItem('hackCCM_bookmarks', JSON.stringify(bookmarks));
            }}
            function isBookmarked(id) {{
                return loadBookmarks().some(function(b) {{ return b.id === id; }});
            }}
            function toggleBookmark(id, type, title, system) {{
                var bookmarks = loadBookmarks();
                var idx = -1;
                bookmarks.some(function(b, i) {{ if (b.id === id) {{ idx = i; return true; }} return false; }});
                if (idx !== -1) {{
                    bookmarks.splice(idx, 1);
                }} else {{
                    bookmarks.push({{id:id, type:type, title:title, system:system, timestamp:new Date().toISOString()}});
                }}
                saveBookmarks(bookmarks);
                // Re-render current view to reflect bookmark star
                if (activeTab === 'pearls') {{ renderPearlList(); renderPearl(); }}
                else if (activeTab === 'papers' || activeTab === 'guidelines') {{ executeClientSideFilter(); }}
            }}

            // =====================================================================
            // SIDEBAR
            // =====================================================================
            function toggleSidebar() {{
                var sidebar = document.getElementById('sidebar');
                var overlay = document.getElementById('sidebarOverlay');
                var open = sidebar.classList.contains('translate-x-0');
                sidebar.classList.toggle('-translate-x-full', open);
                sidebar.classList.toggle('translate-x-0', !open);
                overlay.classList.toggle('hidden', open);
                document.body.classList.toggle('no-scroll', !open);
            }}
            function switchTabAndClose(tab) {{
                toggleSidebar();
                switchTab(tab);
            }}
            function toggleTabDropdown() {{
                var dd = document.getElementById('tabDropdown');
                var isOpen = !dd.classList.contains('hidden');
                dd.classList.toggle('hidden', isOpen);
                if (!isOpen) {{
                    var close = function(e) {{
                        if (!dd.contains(e.target) && !e.target.closest('#tabDropdown')) {{
                            dd.classList.add('hidden');
                            document.removeEventListener('click', close);
                        }}
                    }};
                    setTimeout(function() {{ document.addEventListener('click', close); }}, 10);
                }}
            }}
            function switchTabAndCloseDropdown(tab) {{
                document.getElementById('tabDropdown').classList.add('hidden');
                switchTab(tab);
            }}

            // =====================================================================
            // UNIVERSAL SEARCH
            // =====================================================================
            function openUniversalSearch() {{
                document.getElementById('searchOverlay').classList.remove('hidden');
                document.getElementById('searchModal').classList.remove('hidden');
                document.getElementById('universalSearchInput').value = '';
                document.getElementById('universalSearchResults').innerHTML = '<p class="text-xs text-secondary text-center py-8">Type to search across all content...</p>';
                setTimeout(function() {{ document.getElementById('universalSearchInput').focus(); }}, 100);
            }}
            function closeUniversalSearch() {{
                document.getElementById('searchOverlay').classList.add('hidden');
                document.getElementById('searchModal').classList.add('hidden');
            }}
            function performUniversalSearch(q) {{
                if (q.length < 2) {{
                    document.getElementById('universalSearchResults').innerHTML = '<p class="text-xs text-secondary text-center py-8">Type at least 2 characters...</p>';
                    return;
                }}
                var lq = q.toLowerCase();
                var paperRes = baseDataset.filter(function(i) {{ return i.type.toLowerCase() !== 'guideline' && i.title.toLowerCase().indexOf(lq) !== -1; }});
                var guidelineRes = baseDataset.filter(function(i) {{ return i.type.toLowerCase() === 'guideline' && i.title.toLowerCase().indexOf(lq) !== -1; }});
                var pearlRes = allPearls.filter(function(p) {{
                    return (p.pearl && p.pearl.toLowerCase().indexOf(lq) !== -1) ||
                           (p.topic && p.topic.toLowerCase().indexOf(lq) !== -1) ||
                           (p.system && p.system.toLowerCase().indexOf(lq) !== -1);
                }});
                renderUniversalResults(paperRes, guidelineRes, pearlRes);
            }}
            function renderUniversalResults(papers, guidelines, pearls) {{
                var html = '';
                if (papers.length) {{
                    html += '<div class="mb-3"><h4 class="text-xs font-bold text-secondary uppercase tracking-wider mb-2">📋 Papers (' + papers.length + ')</h4>';
                    papers.forEach(function(item) {{
                        var bm = isBookmarked(item.id) ? '★' : '☆';
                        html += '<div onclick="closeUniversalSearch();switchTab(\\'papers\\');fetchActiveDocumentSummary(\\'' + item.id + '\\',\\'' + item.file_name.replace(/'/g,"") + '\\',\\'' + item.title.replace(/'/g,"\\\\'") + '\\',\\'' + item.doi.replace(/'/g,"") + '\\',\\'' + item.system + '\\',\\'' + item.journal.replace(/'/g,"") + '\\',\\'' + item.type + '\\')" class="flex items-start gap-2 px-3 py-2.5 rounded-xl hover:bg-muted-hover cursor-pointer transition text-sm text-primary">' +
                            '<span>' + item.title + '</span>' +
                            '<span class="ml-auto shrink-0 text-xs cursor-pointer" onclick="event.stopPropagation();toggleBookmark(\\'' + item.id + '\\',\\'paper\\',\\'' + item.title.replace(/'/g,"\\'") + '\\',\\'' + item.system + '\\')">' + bm + '</span>' +
                        '</div>';
                    }});
                    html += '</div>';
                }}
                if (guidelines.length) {{
                    html += '<div class="mb-3"><h4 class="text-xs font-bold text-secondary uppercase tracking-wider mb-2">📋 Guidelines (' + guidelines.length + ')</h4>';
                    guidelines.forEach(function(item) {{
                        var bm = isBookmarked(item.id) ? '★' : '☆';
                        html += '<div onclick="closeUniversalSearch();switchTab(\\'guidelines\\');fetchActiveDocumentSummary(\\'' + item.id + '\\',\\'' + item.file_name.replace(/'/g,"") + '\\',\\'' + item.title.replace(/'/g,"\\\\'") + '\\',\\'' + item.doi.replace(/'/g,"") + '\\',\\'' + item.system + '\\',\\'' + item.journal.replace(/'/g,"") + '\\',\\'' + item.type + '\\')" class="flex items-start gap-2 px-3 py-2.5 rounded-xl hover:bg-muted-hover cursor-pointer transition text-sm text-primary">' +
                            '<span>' + item.title + '</span>' +
                            '<span class="ml-auto shrink-0 text-xs cursor-pointer" onclick="event.stopPropagation();toggleBookmark(\\'' + item.id + '\\',\\'guideline\\',\\'' + item.title.replace(/'/g,"\\'") + '\\',\\'' + item.system + '\\')">' + bm + '</span>' +
                        '</div>';
                    }});
                    html += '</div>';
                }}
                if (pearls.length) {{
                    html += '<div class="mb-3"><h4 class="text-xs font-bold text-secondary uppercase tracking-wider mb-2">💎 Pearls (' + pearls.length + ')</h4>';
                    pearls.forEach(function(p, i) {{
                        var text = (p.pearl || '').length > 80 ? p.pearl.substring(0, 80) + '...' : p.pearl;
                        var pid = 'pearl_' + i;
                        var bm = isBookmarked(pid) ? '★' : '☆';
                        html += '<div onclick="closeUniversalSearch();switchTab(\\'pearls\\');document.getElementById(\\'systemFilter_pearls\\').value=\\'All\\';document.getElementById(\\'typeFilter_pearls\\').value=\\'All\\';executePearlsFilter();var idx=filteredPearls.indexOf(p);if(idx!==-1){{currentPearlIndex=idx;renderPearlList();renderPearl();}}" class="flex items-start gap-2 px-3 py-2.5 rounded-xl hover:bg-muted-hover cursor-pointer transition text-sm text-primary">' +
                            '<span class="italic">\u201C' + text + '\u201D</span>' +
                            '<span class="ml-auto shrink-0 text-xs cursor-pointer" onclick="event.stopPropagation();toggleBookmark(\\'' + pid + '\\',\\'pearl\\',\\'' + (p.pearl || '').substring(0,40).replace(/'/g,"\\\\'") + '\\',\\'' + (p.system||'') + '\\')">' + bm + '</span>' +
                        '</div>';
                    }});
                    html += '</div>';
                }}
                if (!html) {{
                    html = '<p class="text-xs text-secondary text-center py-8">No results found.</p>';
                }}
                document.getElementById('universalSearchResults').innerHTML = html;
            }}

            // =====================================================================
            // ABOUT MODAL
            // =====================================================================
            function openAboutModal() {{
                document.getElementById('aboutOverlay').classList.remove('hidden');
                document.getElementById('aboutModal').classList.remove('hidden');
            }}
            function closeAboutModal() {{
                document.getElementById('aboutOverlay').classList.add('hidden');
                document.getElementById('aboutModal').classList.add('hidden');
            }}

            // =====================================================================
            // SETTINGS MODAL — Dark Mode + Font Size
            // =====================================================================
            function openSettingsModal() {{
                document.getElementById('settingsOverlay').classList.remove('hidden');
                document.getElementById('settingsModal').classList.remove('hidden');
            }}
            function closeSettingsModal() {{
                document.getElementById('settingsOverlay').classList.add('hidden');
                document.getElementById('settingsModal').classList.add('hidden');
            }}
            function setTheme(theme) {{
                document.documentElement.setAttribute('data-theme', theme);
                localStorage.setItem('hackCCM_theme', theme);
                document.getElementById('themeBtn_light').className = 'flex-1 px-4 py-2.5 text-sm font-semibold rounded-xl border-2 transition-all ' + (theme === 'light' ? 'bg-accent text-white border-accent' : 'bg-card text-primary border-dark hover:bg-muted-hover');
                document.getElementById('themeBtn_dark').className = 'flex-1 px-4 py-2.5 text-sm font-semibold rounded-xl border-2 transition-all ' + (theme === 'dark' ? 'bg-accent text-white border-accent' : 'bg-card text-primary border-dark hover:bg-muted-hover');
            }}
            function setFontSize(size) {{
                document.documentElement.setAttribute('data-font-size', size);
                localStorage.setItem('hackCCM_fontSize', size);
                ['sm','md','lg'].forEach(function(s) {{
                    var el = document.getElementById('fontBtn_' + s);
                    el.className = 'flex-1 px-4 py-2.5 text-sm font-semibold rounded-xl border-2 transition-all ' + (s === size ? 'bg-accent text-white border-accent' : 'bg-card text-primary border-dark hover:bg-muted-hover');
                }});
            }}
            function loadPreferences() {{
                var theme = localStorage.getItem('hackCCM_theme');
                if (theme) setTheme(theme);
                var fontSize = localStorage.getItem('hackCCM_fontSize');
                if (fontSize) setFontSize(fontSize);
            }}

            // =====================================================================
            // TOAST NOTIFICATION
            // =====================================================================
            function toast(msg) {{
                var c = document.getElementById('toastContainer');
                c.textContent = msg;
                c.className = 'fixed bottom-6 left-1/2 -translate-x-1/2 z-[60] bg-card text-primary px-5 py-3 rounded-xl shadow-lg border border-muted text-sm font-semibold modal-animate';
                c.style.display = 'block';
                setTimeout(function() {{ c.style.display = 'none'; }}, 3000);
            }}

            // =====================================================================
            // BOOKMARKS MODAL
            // =====================================================================
            function openBookmarksModal() {{
                document.getElementById('bookmarksOverlay').classList.remove('hidden');
                document.getElementById('bookmarksModal').classList.remove('hidden');
                document.getElementById('bookmarkSearchInput').value = '';
                renderBookmarksList();
            }}
            function closeBookmarksModal() {{
                document.getElementById('bookmarksOverlay').classList.add('hidden');
                document.getElementById('bookmarksModal').classList.add('hidden');
            }}
            function renderBookmarksList(filter) {{
                var bookmarks = loadBookmarks();
                var container = document.getElementById('bookmarksList');
                if (!bookmarks.length) {{
                    container.innerHTML = '<p class="text-xs text-secondary text-center py-8">No bookmarks yet. Click \u2606 on any paper or pearl to save it.</p>';
                    return;
                }}
                bookmarks.sort(function(a, b) {{ return new Date(b.timestamp) - new Date(a.timestamp); }});
                if (filter) {{
                    var lf = filter.toLowerCase();
                    bookmarks = bookmarks.filter(function(b) {{ return (b.title||'').toLowerCase().indexOf(lf) !== -1 || (b.system||'').toLowerCase().indexOf(lf) !== -1 || (b.type||'').toLowerCase().indexOf(lf) !== -1; }});
                }}
                if (!bookmarks.length) {{
                    container.innerHTML = '<p class="text-xs text-secondary text-center py-8">No bookmarks match your search.</p>';
                    return;
                }}
                var html = '';
                bookmarks.forEach(function(b) {{
                    var icon = b.type === 'pearl' ? '💎' : '📄';
                    html += '<div class="flex items-start gap-2 px-3 py-2.5 rounded-xl hover:bg-muted-hover cursor-pointer transition text-sm" onclick="closeBookmarksModal();navigateToBookmark(\\'' + b.id + '\\',\\'' + b.type + '\\')">' +
                        '<span class="shrink-0">' + icon + '</span>' +
                        '<div class="flex-1 min-w-0">' +
                            '<div class="text-primary font-medium truncate">' + b.title + '</div>' +
                            '<div class="text-[10px] text-secondary">' + (b.system || '') + '</div>' +
                        '</div>' +
                        '<span class="shrink-0 text-xs cursor-pointer text-accent" onclick="event.stopPropagation();removeBookmark(\\'' + b.id + '\\')">\u2605</span>' +
                    '</div>';
                }});
                container.innerHTML = html;
            }}
            function filterBookmarks() {{
                var q = document.getElementById('bookmarkSearchInput').value;
                renderBookmarksList(q);
            }}
            function removeBookmark(id) {{
                var bookmarks = loadBookmarks();
                bookmarks = bookmarks.filter(function(b) {{ return b.id !== id; }});
                saveBookmarks(bookmarks);
                renderBookmarksList();
            }}
            function navigateToBookmark(id, type) {{
                if (type === 'pearl') {{
                    switchTab('pearls');
                    // Try to find and select the pearl
                    allPearls.forEach(function(p, i) {{
                        if (('pearl_' + i) === id) {{
                            document.getElementById('systemFilter_pearls').value = 'All';
                            document.getElementById('typeFilter_pearls').value = 'All';
                            executePearlsFilter();
                            var found = filteredPearls.indexOf(p);
                            if (found !== -1) {{ currentPearlIndex = found; renderPearlList(); renderPearl(); }}
                        }}
                    }});
                }} else {{
                    // Find paper/guideline by id and open it
                    var item = baseDataset.filter(function(i) {{ return i.id === id; }});
                    if (item.length) {{
                        item = item[0];
                        switchTab(item.type.toLowerCase() === 'guideline' ? 'guidelines' : 'papers');
                        fetchActiveDocumentSummary(item.id, item.file_name, item.title, item.doi, item.system, item.journal, item.type);
                    }}
                }}
            }}

            // =====================================================================
            // KEYBOARD SHORTCUT
            // =====================================================================
            document.addEventListener('keydown', function(e) {{
                if ((e.ctrlKey || e.metaKey) && e.key === 'k') {{
                    e.preventDefault();
                    if (document.getElementById('searchModal').classList.contains('hidden')) {{
                        openUniversalSearch();
                    }} else {{
                        closeUniversalSearch();
                    }}
                }}
                if (e.key === 'Escape') {{
                    closeUniversalSearch();
                    closeBookmarksModal();
                    closeAboutModal();
                    closeSettingsModal();
                    var sidebar = document.getElementById('sidebar');
                    if (sidebar.classList.contains('translate-x-0')) toggleSidebar();
                }}
            }});

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
            let sortBy = 'added';

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

            function setSortBy(val) {{
                sortBy = val;
                executeClientSideFilter();
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
                // Apply system color to badge
                var badge = document.getElementById("dailyPaperSystem");
                var c = getSystemColor(dailyPaperItem.system);
                badge.style.backgroundColor = c + '18';
                badge.style.color = c;
                badge.style.border = '1px solid ' + c + '30';
                badge.style.borderRadius = '4px';
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
                // Apply system color to badge
                var badge = document.getElementById("dailyPearlSystem");
                var c = getSystemColor(p.system || '');
                badge.style.backgroundColor = c + '18';
                badge.style.color = c;
                badge.style.border = '1px solid ' + c + '30';
                badge.style.borderRadius = '4px';
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
                    if (window.innerWidth < 640) document.getElementById("documentSheetContainer").scrollIntoView({{ behavior: 'smooth' }});
                }}
            }}

            function updateStatusPanel() {{
                let count, systems, icon, label;
                if (activeTab === 'papers') {{
                    const items = baseDataset.filter(i => i.type.toLowerCase() !== "guideline");
                    count = items.length;
                    systems = new Set(items.map(i => i.system)).size;
                    icon = '📋'; label = 'Papers';
                }} else if (activeTab === 'guidelines') {{
                    const items = baseDataset.filter(i => i.type.toLowerCase() === "guideline");
                    count = items.length;
                    systems = new Set(items.map(i => i.system)).size;
                    icon = '📋'; label = 'Guidelines';
                }} else if (activeTab === 'pearls') {{
                    count = filteredPearls.length;
                    systems = new Set(filteredPearls.map(function(p) {{ return p.system; }})).size;
                    icon = '💎'; label = 'Pearls';
                }} else {{
                    count = 0; systems = 0;
                    icon = '🚧';
                    label = activeTab === 'antibiotics' ? 'Antibiotics' : activeTab === 'theory' ? 'Theory' : 'Ask AI';
                }}
                document.getElementById('statusIcon').textContent = icon;
                document.getElementById('statusCount').textContent = count;
                document.getElementById('statusLabel').textContent = label;
                document.getElementById('statusSystems').textContent = systems;
            }}

            function switchTab(tab) {{
                activeTab = tab;

                var tabKeys = ['papers', 'guidelines', 'pearls', 'antibiotics', 'theory', 'ask-ai'];
                tabKeys.forEach(function(key) {{
                    var el = document.getElementById('tabBtn_' + key);
                    if (!el) return;
                    if (key === tab) {{
                        el.className = 'shrink-0 px-3 py-1.5 sm:px-5 sm:py-2.5 text-xs sm:text-sm font-bold rounded-full transition-all whitespace-nowrap bg-accent text-white shadow-sm';
                    }} else {{
                        el.className = 'shrink-0 px-3 py-1.5 sm:px-5 sm:py-2.5 text-xs sm:text-sm font-bold rounded-full transition-all whitespace-nowrap bg-transparent text-secondary hover:bg-muted-hover' + (key === 'ask-ai' ? ' opacity-60' : '');
                    }}
                }});

                var filterPanels = ['filterPanel_papers', 'filterPanel_guidelines', 'filterPanel_pearls', 'filterPanel_antibiotics', 'filterPanel_theory', 'filterPanel_ask-ai'];
                filterPanels.forEach(function(pid) {{
                    var el = document.getElementById(pid);
                    if (el) {{
                        if (pid === 'filterPanel_' + tab) el.classList.add('active');
                        else el.classList.remove('active');
                    }}
                }});

                var deckContainer = document.getElementById("articlesListDeck");
                document.getElementById("deckLabel").textContent =
                    tab === 'pearls' ? '💎 Pearl Selector' : '📑 Document Selector';

                currentActiveSelectionId = null;
                fullTextResults = null;
                updateStatusPanel();

                var viewer = document.getElementById("documentSheetContainer");

                // Handle coming-soon tabs
                if (tab === 'antibiotics' || tab === 'theory' || tab === 'ask-ai') {{
                    deckContainer.innerHTML = '';
                    var emoji = tab === 'antibiotics' ? '💊' : tab === 'theory' ? '🧠' : '🤖';
                    var name = tab === 'antibiotics' ? 'Antibiotics Hub' : tab === 'theory' ? 'Theory Library' : 'Ask AI';
                    viewer.innerHTML = '<div class="text-center py-24 text-secondary">' +
                        '<p class="text-4xl mb-4">' + emoji + '</p>' +
                        '<p class="text-lg font-bold mb-2">' + name + '</p>' +
                        '<p class="text-sm">Coming soon</p></div>';
                    return;
                }}

                if (tab === 'pearls') {{
                    deckContainer.innerHTML = '';
                    executePearlsFilter();
                }} else {{
                    executeClientSideFilter();
                    viewer.innerHTML = '<div class="text-center py-24 text-secondary">' +
                        '<p class="text-sm md:text-lg font-medium">👋 Welcome to hack.CCM Repository</p>' +
                        '<p class="text-xs md:text-sm mt-1">Select a publication entry card from the index frame to unpack formatting layers.</p></div>';
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

            function onPearlSearchInput() {{
                const input = document.getElementById("topicSearch_pearls");
                document.getElementById("clearPearlSearch").style.display = input.value ? 'block' : 'none';
                executePearlsFilter();
            }}

            function clearPearlSearch() {{
                document.getElementById("topicSearch_pearls").value = '';
                document.getElementById("clearPearlSearch").style.display = 'none';
                executePearlsFilter();
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
                if (activeTab !== 'papers' && activeTab !== 'guidelines') return;
                if (!document.getElementById("filterPanel_papers").classList.contains("active") &&
                    !document.getElementById("filterPanel_guidelines").classList.contains("active")) return;
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

                filtered.sort(function(a, b) {{
                    if (sortBy === 'published') {{
                        return (parseInt(b.year) || 0) - (parseInt(a.year) || 0);
                    }}
                    return (b.date_added || '').localeCompare(a.date_added || '');
                }});

                if(filtered.length === 0) {{
                    deckContainer.innerHTML = `<p class="text-xs text-secondary italic p-3 text-center">No matching records found.</p>`;
                    return;
                }}

                filtered.forEach(item => {{
                    const btn = document.createElement("button");
                    const isActive = item.id === currentActiveSelectionId;
                    const sysColor = getSystemColor(item.system);
                    btn.className = `w-full text-left p-4 rounded-xl text-sm transition border flex flex-col gap-1 shadow-2xs ${{isActive ? 'bg-active-card text-active-card border-transparent font-bold ring-1 ring-hover' : 'bg-card text-primary border-muted hover:bg-muted-hover'}}`;
                    btn.style.borderLeft = '4px solid ' + sysColor;
                    btn.onclick = () => fetchActiveDocumentSummary(item.id, item.file_name, item.title, item.doi, item.system, item.journal, item.type);
                    const bmIcon = isBookmarked(item.id) ? '★' : '☆';
                    btn.innerHTML = `
                        <span class="flex items-start justify-between gap-2">
                            <span class="block text-xs md:text-sm leading-snug">${{item.title}}</span>
                            <span class="bookmark-star shrink-0 text-xs cursor-pointer select-none" style="${{isBookmarked(item.id) ? 'color:var(--color-accent)' : ''}}" onclick="event.stopPropagation();toggleBookmark('${{item.id}}','paper','${{item.title.replace(/'/g, "\\\\'")}}','${{item.system}}')">${{bmIcon}}</span>
                        </span>
                        <div class="flex gap-2 mt-1 text-[10px] font-bold tracking-wider uppercase" style="color:var(--color-secondary)">
                            <span style="background:${{sysColor}}18;color:${{sysColor}};border:1px solid ${{sysColor}}30;border-radius:0.375rem" class="px-1.5 py-0.5 rounded">${{item.system}}</span>
                            <span class="${{isActive ? 'bg-white/50' : 'bg-muted'}} px-1.5 py-0.5 rounded">${{item.type}}</span>
                        </div>
                    `;
                    deckContainer.appendChild(btn);
                }});
            }}

            async function fetchActiveDocumentSummary(id, fileName, title, doiLink, system, journal, type) {{
                currentActiveSelectionId = id;
                executeClientSideFilter();

                const viewer = document.getElementById("documentSheetContainer");
                viewer.innerHTML = `<div class="text-center py-24 text-sm font-medium text-secondary animate-pulse">🔬 Processing structural markdown fields...</div>`;

                try {{
                    const response = await fetch(`/api/summary?file_name=${{encodeURIComponent(fileName)}}&system=${{encodeURIComponent(system)}}&type=${{encodeURIComponent(type)}}`);
                    if (activeTab !== 'papers' && activeTab !== 'guidelines' && activeTab !== 'pearls') return;
                    const data = await response.json();

                    if (!response.ok || data.error) {{
                        viewer.innerHTML = `<div class="p-4 bg-red-50 text-red-700 rounded-lg text-sm">⚠️ Error loading summary payload dataset.</div>`;
                        if (window.innerWidth < 640) viewer.scrollIntoView({{ behavior: 'smooth' }});
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
                        doiButtonHTML = `<a href="${{doiLink}}" target="_blank" class="w-full sm:w-auto text-center bg-accent hover:bg-accent-hover text-white font-semibold text-xs px-4 py-2.5 rounded-lg shadow-sm transition inline-block">🔗 Source Publication</a>`;
                    }}

                    let pdfButtonHTML = `<button onclick="exportPDF()" class="w-full sm:w-auto text-center bg-card text-accent font-semibold text-xs px-4 py-2.5 rounded-lg border border-accent shadow-sm transition hover:bg-badge-blue inline-block">📄 Download PDF</button>`;

                    const rawHTML = marked.parse(data.content);
                    const parsedMarkdownHTML = makeCollapsible(rawHTML);
                    const authorsLine = data.authors && data.authors !== "Unknown Authors" ? `<p class="text-sm italic text-secondary mt-1 font-sans">✍️ Primary Authors: ${{data.authors}}</p>` : "";

                    const sysColor = getSystemColor(system);
                    const bmIcon = isBookmarked(id) ? '★' : '☆';

                    viewer.innerHTML = `
                        <div class="flex flex-col sm:flex-row justify-between items-start gap-4 pb-4 border-b border-muted mb-6" style="border-top:3px solid ${{sysColor}};padding-top:1rem;">
                            <div class="w-full">
                                <div class="flex items-start justify-between gap-2">
                                    <h1 class="text-lg md:text-2xl font-bold tracking-tight text-black" style="color:var(--color-primary)">📜 ${{title}}</h1>
                                    <span class="bookmark-star shrink-0 text-lg cursor-pointer select-none" onclick="toggleBookmark('${{id}}','paper','${{title.replace(/'/g, "\\\\'")}}','${{system}}')" style="color:var(--color-accent)">${{bmIcon}}</span>
                                </div>
                                ${{authorsLine}}
                                <div class="flex flex-wrap gap-2 text-xs font-semibold mt-3" style="font-family: system-ui, sans-serif;">
                                    <span style="background:${{sysColor}}18;color:${{sysColor}};border:1px solid ${{sysColor}}30" class="px-2.5 py-1 rounded-md">🧬 Specialty: ${{system}}</span>
                                    <span class="bg-[#FAF5FF] text-[#6B21A8] px-2.5 py-1 rounded-md border border-[#F3E8FF]">📖 Journal: ${{journal}}</span>
                                    <span class="bg-[#F1F5F9] text-[#475569] px-2.5 py-1 rounded-md border border-[#E2E8F0]">📑 Type: ${{type}}</span>
                                </div>
                            </div>
                            <div class="w-full sm:w-auto shrink-0 flex gap-2">${{doiButtonHTML}}${{pdfButtonHTML}}</div>
                        </div>
                        <div class="summary-body" style="color:var(--color-primary);">
                            ${{parsedMarkdownHTML}}
                        </div>
                    `;
                    if (window.innerWidth < 640) viewer.scrollIntoView({{ behavior: 'smooth' }});
                }} catch(err) {{
                    viewer.innerHTML = `<div class="p-4 bg-red-50 text-red-700 rounded-lg text-sm">❌ Network connection error: ${{err.message}}</div>`;
                    if (window.innerWidth < 640) viewer.scrollIntoView({{ behavior: 'smooth' }});
                }}
            }}

            function makeCollapsible(html) {{
                var parts = html.split(/(<h2[^>]*>[\s\S]*?<\/h2>)/i);
                if (parts.length < 2) return html;
                var result = '';
                if (parts[0].trim()) {{
                    result += '<div class="summary-content-intro">' + parts[0] + '</div>';
                }}
                var first = true;
                for (var i = 1; i < parts.length; i += 2) {{
                    var headingTag = parts[i];
                    var content = parts[i + 1] || '';
                    var textMatch = headingTag.match(/>([^<]*)</);
                    var titleText = textMatch ? textMatch[1] : 'Section';
                    result += '<details class="summary-section"' + (first ? ' open' : '') + '>' +
                        '<summary class="summary-heading">' + titleText + '</summary>' +
                        '<div class="summary-content">' + content.replace(headingTag, '') + '</div>' +
                        '</details>';
                    first = false;
                }}
                return result;
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
                const keyword = document.getElementById("topicSearch_pearls").value.toLowerCase().trim();
                filteredPearls = allPearls.filter(function(p) {{
                    if (systemVal !== "All" && p.system !== systemVal) return false;
                    if (typeVal !== "All" && p.type !== typeVal) return false;
                    if (keyword) {{
                        const haystack = (p.pearl || '') + ' ' + (p.topic || '') + ' ' + (p.source_paper || '');
                        if (haystack.toLowerCase().indexOf(keyword) === -1) return false;
                    }}
                    return true;
                }});
                currentPearlIndex = 0;
                updateStatusPanel();
                updatePearlCounter();
                renderPearlList();
                renderPearl();
            }}

            function renderPearlList() {{
                const deck = document.getElementById("articlesListDeck");
                if (filteredPearls.length === 0) {{
                    deck.innerHTML = '<p class="text-xs text-secondary italic p-3 text-center">No matching pearls.</p>';
                    return;
                }}
                deck.innerHTML = filteredPearls.map(function(p, idx) {{
                    const isActive = idx === currentPearlIndex;
                    const truncated = (p.pearl || '').length > 80 ? p.pearl.substring(0, 80) + '...' : p.pearl;
                    const sysColor = getSystemColor(p.system || '');
                    const cls = isActive
                        ? 'bg-active-card text-active-card border-transparent font-bold ring-1 ring-hover'
                        : 'bg-card text-primary border-muted hover:bg-muted-hover';
                    const bmIcon = isBookmarked('pearl_' + idx) ? '★' : '☆';
                    return '<button onclick="selectPearl(' + idx + ')" '
                        + 'class="w-full text-left p-3 rounded-xl text-xs transition border flex flex-col gap-0.5 shadow-2xs ' + cls + '"'
                        + ' style="border-left:4px solid ' + sysColor + '">'
                        + '<span class="flex items-start justify-between gap-2">'
                        + '<span class="leading-snug">' + truncated + '</span>'
                        + '<span class="bookmark-star shrink-0 text-xs cursor-pointer select-none" style="' + (isBookmarked('pearl_' + idx) ? 'color:var(--color-accent)' : '') + '" onclick="event.stopPropagation();toggleBookmark(\\'pearl_' + idx + '\\',\\'pearl\\',\\'' + (p.pearl||'').substring(0,40).replace(/'/g, "\\\\'") + '\\',\\'' + (p.system||'') + '\\')">' + bmIcon + '</span>'
                        + '</span>'
                        + '<span class="flex gap-1 mt-0.5 text-[9px] font-bold tracking-wider uppercase" style="color:var(--color-secondary)">'
                        + '<span style="background:' + sysColor + '18;color:' + sysColor + ';border:1px solid ' + sysColor + '30;border-radius:0.375rem" class="px-1 py-0.5 rounded">' + (p.system || '') + '</span>'
                        + '<span class="bg-muted px-1 py-0.5 rounded">' + (p.type || '') + '</span>'
                        + (p.topic ? p.topic.split(',').map(function(t) {{ return '<span class="bg-[#FEF3C7] text-[#92400E] px-1 py-0.5 rounded">' + t.trim() + '</span>'; }}).join('') : '')
                        + '</span></button>';
                }}).join('');
            }}

            function selectPearl(idx) {{
                currentPearlIndex = idx;
                updatePearlCounter();
                renderPearlList();
                renderPearl();
                if (window.innerWidth < 640) {{
                    document.getElementById("documentSheetContainer").scrollIntoView({{ behavior: 'smooth' }});
                }}
            }}

            function renderPearl() {{
                const viewer = document.getElementById("documentSheetContainer");
                if (filteredPearls.length === 0) {{
                    viewer.innerHTML = '<div class="text-center py-24 text-secondary"><p class="text-sm md:text-lg font-medium">💎 No pearls match your filters.</p><p class="text-xs md:text-sm mt-1">Try adjusting the filters above.</p></div>';
                    return;
                }}
                const p = filteredPearls[currentPearlIndex];
                const paperName = (p.source_paper || '').replace(/[^a-zA-Z0-9 _-]/g, ' ').trim() || 'Unknown Source';
                const prevDisabled = currentPearlIndex === 0 ? 'disabled' : '';
                const nextDisabled = currentPearlIndex === filteredPearls.length - 1 ? 'disabled' : '';
                const sysColor = getSystemColor(p.system || '');
                const bmIcon = isBookmarked('pearl_' + currentPearlIndex) ? '★' : '☆';
                viewer.innerHTML = '<div class="flex flex-col items-center justify-center min-h-[400px] max-w-2xl mx-auto text-center" style="border-top:3px solid ' + sysColor + ';padding-top:1rem;">' +
                    '<div class="flex gap-2 mb-4 flex-wrap justify-center">' +
                        (p.system ? '<span style="background:' + sysColor + '18;color:' + sysColor + ';border:1px solid ' + sysColor + '30" class="text-xs font-bold px-3 py-1 rounded-md">' + p.system + '</span>' : '') +
                        (p.type ? '<span class="bg-[#F0FDF4] text-[#15803D] text-xs font-bold px-3 py-1 rounded-md">' + p.type + '</span>' : '') +
                        (p.topic ? p.topic.split(',').map(function(t) {{ return '<span class="bg-[#FEF3C7] text-[#92400E] text-xs font-bold px-3 py-1 rounded-md">' + t.trim() + '</span>'; }}).join('') : '') +
                    '</div>' +
                    '<div class="flex items-start justify-center gap-2 w-full max-w-lg">' +
                        '<div class="text-sm md:text-xl leading-relaxed text-[#1F2937] mb-4 font-serif" style="color:var(--color-primary)">\u201C' + p.pearl + '\u201D</div>' +
                        '<span class="bookmark-star shrink-0 text-lg cursor-pointer select-none mt-1" onclick="toggleBookmark(\\'pearl_' + currentPearlIndex + '\\',\\'pearl\\',\\'' + (p.pearl||'').substring(0,40).replace(/'/g, "\\\\'") + '\\',\\'' + (p.system||'') + '\\')" style="color:var(--color-accent)">' + bmIcon + '</span>' +
                    '</div>' +
                    '<div class="text-sm text-[#6B7280] mb-6 font-sans">' +
                        '\u2014 ' + paperName +
                        ((p.file_name || p.source_paper) ? ' <button onclick="openPearlPaper()" class="ml-2 text-accent hover:underline font-semibold text-xs">Open \u2197</button>' : '') +
                    '</div>' +
                    '<div class="flex gap-4 font-sans">' +
                        '<button onclick="prevPearl()" ' + prevDisabled + ' class="px-6 py-2 text-sm font-semibold rounded-lg border border-dark bg-card text-secondary hover:bg-muted-hover disabled:opacity-40 disabled:cursor-not-allowed transition">\u2190 Previous</button>' +
                        '<button onclick="nextPearl()" ' + nextDisabled + ' class="px-6 py-2 text-sm font-semibold rounded-lg border border-dark bg-card text-secondary hover:bg-muted-hover disabled:opacity-40 disabled:cursor-not-allowed transition">Next \u2192</button>' +
                    '</div>' +
                '</div>';
            }}

            function prevPearl() {{
                if (currentPearlIndex > 0) {{
                    currentPearlIndex--;
                    updatePearlCounter();
                    renderPearlList();
                    renderPearl();
                }}
            }}

            function nextPearl() {{
                if (currentPearlIndex < filteredPearls.length - 1) {{
                    currentPearlIndex++;
                    updatePearlCounter();
                    renderPearlList();
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

            window.onload = function() {{ loadPreferences(); initializeAppMatrix(); }};
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

def bold_labels(text):
    """Bold common clinical labels before colons."""
    return re.sub(
        r'\b(Strengths|Limitations|Dose|Indication|Adverse effects?|Route|Frequency|'
        r'Duration|Monitoring|Contraindications?|Precautions?|Key Point|Note|Finding|'
        r'Result|Recommendation)\s*:',
        r'**\1:**',
        text
    )


def format_new_schema_as_markdown(payload):
    """Convert new-format JSON payload into a markdown string for the frontend viewer."""
    parts = []

    # One-line summary at the top if present
    summary = payload.get("one_line_summary", "")
    if summary:
        parts.append(f"> **One-Line Summary:** {summary}\n")

    # Key pearls if present
    pearls = payload.get("key_pearls", [])
    if pearls:
        parts.append("## Key Pearls\n" + "\n".join(f"- {p}" for p in pearls) + "\n")

    # Article format: sections[]
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

    # Guideline format: recommendation_blocks[]
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

    # Bedside protocol (guidelines)
    protocol = payload.get("bedside_protocol", [])
    if protocol:
        protocol_parts = ["## Bedside Protocol"]
        for step in protocol:
            step_num = step.get("step", "")
            title = step.get("title", "")
            action = step.get("action", "")
            protocol_parts.append(f"**Step {step_num}: {title}**  \n{action}")
        parts.append("\n".join(protocol_parts))

    # Drugs & Doses
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

    # Strengths & limitations
    strengths = payload.get("strengths_limitations", "")
    if strengths:
        parts.append(f"## Strengths & Limitations\n{bold_labels(strengths)}")

    return "\n\n".join(parts)


@app.get("/api/summary")
async def get_cached_json_summary_contents(file_name: str, system: str = "General", type: str = "Unclassified"):
    base_name = os.path.splitext(file_name)[0]

    clean_system = "".join(x for x in str(system) if x.isalnum() or x in "._- ").strip()
    clean_type = "".join(x for x in str(type) if x.isalnum() or x in "._- ").strip()

    target_json_path = os.path.join(OUTPUT_DIR, clean_system, clean_type, f"{base_name}.json")

    if not os.path.exists(target_json_path):
        # Fallback: search all subdirectories by basename
        target_json_path = ""
        for root, dirs, files in os.walk(OUTPUT_DIR):
            if f"{base_name}.json" in files:
                target_json_path = os.path.join(root, f"{base_name}.json")
                break

    if not target_json_path or not os.path.exists(target_json_path):
        return JSONResponse(status_code=404, content={"error": f"Summary target path not found: {base_name}.json"})

    try:
        with open(target_json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        # Old format (pre-migration)
        content = payload.get("clinical_summary_markdown", "")
        authors = payload.get("primary_authors", "")

        # New format fallback
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

        return {"content": content, "authors": authors}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

def extract_search_text(payload):
    """Build a combined lowercase search string from both old and new format fields."""
    text_parts = []

    # Old format
    text_parts.append(payload.get("paper_name", ""))
    text_parts.append(payload.get("clinical_summary_markdown", ""))
    text_parts.append(payload.get("primary_authors", ""))
    text_parts.append(payload.get("journal_name", ""))

    # New format (article)
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

    # New format (guideline)
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
    """Extract title/system/type/journal from old or new format."""
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
                search_text = extract_search_text(payload)
                if query in search_text:
                    title, system, article_type, journal = extract_metadata(payload)
                    results.append({
                        "file_name": fname,
                        "title": title,
                        "system": system or "Other",
                        "type": article_type or "Other",
                        "journal": journal
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
