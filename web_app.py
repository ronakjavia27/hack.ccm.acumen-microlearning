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

app = FastAPI()

# =====================================================================
# 🎨 COLOR CODES DICTIONARY & SIGNIFICATION DESIGN LEDGER
# =====================================================================
# Theme Archetype: High-End Academic Editorial Beige & Tan
# 🏷️ #FDFBF7 -> Main Application Canvas (Soft cream color to eliminate eye strain)
# 🏷️ #EFECE6 -> Structural Control Panels (Subtle dark tan to create visual depth)
# 🏷️ #DCD9D2 -> Standard Selector Borders & Unselected Radio Card States (Light grey-tan)
# 🏷️ #D7CDB7 -> 🤎 LIGHT TAN SELECTION BUTTON (Warm light tan representing active choice)
# 🏷️ #5C5346 -> Text Contrast for Selected Tan Element (Deep brown-grey ink for clear visibility)
# 🏷️ #FFFFFF -> Safe Paper Reading Card (Crisp pure white surface for clinical text focus)
# 🏷️ #111827 -> Absolute Ink Primary Text (Deep charcoal black for elite readability)
# 🏷️ #1D4ED8 -> Interactive Action Button Link (Deep vibrant primary royal blue)
# =====================================================================

def load_approved_ledger():
    if not os.path.exists(EXCEL_TRACKER_FILE):
        return pd.DataFrame()
    try:
        df = pd.read_excel(EXCEL_TRACKER_FILE, sheet_name="Registry Logs")
        df.columns = df.columns.str.strip()
        return df[df["show_on_web"].astype(str).str.strip().str.lower() == "yes"]
    except Exception:
        return pd.DataFrame()

@app.get("/", response_class=HTMLResponse)
async def render_dashboard_portal(request: Request):
    df = load_approved_ledger()
    
    total_published = len(df)
    unique_systems = df["System"].dropna().nunique() if total_published > 0 else 0
    
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
                "system": str(row.get("System", "General")),
                "journal": str(row.get("Journal Name", "Unknown Source")),
                "type": str(row.get("Type of Article", "Unclassified")),
                "doi": clean_doi_url,
                "file_name": str(row.get("File Name", ""))
            })

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>hack.CCM | Knowledge Portal</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss-typography/0.5.10/typography.min.css" />
        <style>
            body {{ background-color: #FDFBF7; color: #111827; font-family: 'Georgia', serif; }}
            .custom-scrollbar::-webkit-scrollbar {{ width: 6px; }}
            .custom-scrollbar::-webkit-scrollbar-track {{ background: #FDFBF7; }}
            .custom-scrollbar::-webkit-scrollbar-thumb {{ background: #EFECE6; border-radius: 3px; }}
            
            /* Clean formatting styles for parsed summary strings */
            .summary-body h3 {{ font-size: 1.3em; font-weight: bold; margin-top: 1.5em; margin-bottom: 0.5em; color: #000000; border-bottom: 1px solid #EFECE6; padding-bottom: 0.3em; }}
            .summary-body p {{ margin-bottom: 1em; line-height: 1.6; text-align: justify; }}
            .summary-body ul, .summary-body ol {{ margin-left: 1.5em; margin-bottom: 1em; list-style-type: disc; }}
            .summary-body li {{ margin-bottom: 0.4em; line-height: 1.5; }}
            .summary-body strong {{ color: #000000; font-weight: 700; }}
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

        <main class="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            <div class="space-y-6">
                
                <div class="bg-[#EFECE6] p-5 rounded-2xl border border-[#DCD9D2]">
                    <h3 class="text-xs font-bold tracking-wider text-[#4B5563] uppercase mb-3">📊 Portal Status</h3>
                    <div class="flex gap-3">
                        <span class="bg-white px-3 py-1.5 rounded-lg text-xs font-bold border border-[#DCD9D2]">📋 {total_published} Live Papers</span>
                        <span class="bg-white px-3 py-1.5 rounded-lg text-xs font-bold border border-[#DCD9D2]">🧬 {unique_systems} Specialties</span>
                    </div>
                </div>

                <div class="bg-[#EFECE6] p-5 rounded-2xl border border-[#DCD9D2] space-y-4">
                    <h3 class="text-xs font-bold tracking-wider text-[#4B5563] uppercase mb-1">🔍 Filter Matrix</h3>
                    <div>
                        <label class="block text-xs font-bold mb-1 text-[#4B5563]">Keywords Search</label>
                        <input type="text" id="titleSearch" onkeyup="executeClientSideFilter()" placeholder="Type keywords..." class="w-full bg-white text-[#111827] text-sm p-2.5 rounded-lg border border-[#DCD9D2] focus:outline-none focus:ring-2 focus:ring-[#1D4ED8] transition">
                    </div>
                    <div>
                        <label class="block text-xs font-bold mb-1 text-[#4B5563]">Specialty Group</label>
                        <select id="systemFilter" onchange="executeClientSideFilter()" class="w-full bg-white text-[#111827] text-sm p-2.5 rounded-lg border border-[#DCD9D2] focus:outline-none focus:ring-2 focus:ring-[#1D4ED8] transition">
                            <option value="All">All Specialties</option>
                        </select>
                    </div>
                </div>

                <div class="space-y-2">
                    <h3 class="text-xs font-bold tracking-wider text-[#4B5563] uppercase px-2">📑 Document Selector</h3>
                    <div id="articlesListDeck" class="max-h-[450px] overflow-y-auto custom-scrollbar space-y-2 pr-1">
                        </div>
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
            let currentActiveSelectionId = null;

            function initializeAppMatrix() {{
                const systemSelect = document.getElementById("systemFilter");
                const uniqueSpecs = [...new Set(baseDataset.map(item => item.system))].sort();
                uniqueSpecs.forEach(sys => {{
                    let opt = document.createElement("option");
                    opt.value = sys; opt.textContent = sys;
                    systemSelect.appendChild(opt);
                }});
                executeClientSideFilter();
            }}

            function executeClientSideFilter() {{
                const searchVal = document.getElementById("titleSearch").value.toLowerCase();
                const systemVal = document.getElementById("systemFilter").value;
                const deckContainer = document.getElementById("articlesListDeck");
                
                deckContainer.innerHTML = "";
                
                const filtered = baseDataset.filter(item => {{
                    const matchSearch = item.title.toLowerCase().includes(searchVal);
                    const matchSystem = (systemVal === "All") || (item.system === systemVal);
                    return matchSearch && matchSystem;
                }});

                if(filtered.length === 0) {{
                    deckContainer.innerHTML = `<p class="text-xs text-[#4B5563] italic p-3 text-center">No matching records found.</p>`;
                    return;
                }}

                filtered.forEach(item => {{
                    const btn = document.createElement("button");
                    const isActive = item.id === currentActiveSelectionId;
                    
                    // 🛠️ FIXED: Active selection button overrides blue layout blocks to Light Tan (#D7CDB7)
                    btn.className = `w-full text-left p-4 rounded-xl text-sm transition border flex flex-col gap-1 shadow-2xs ${{
                        isActive 
                        ? 'bg-[#D7CDB7] text-[#5C5346] border-transparent font-bold ring-1 ring-[#BDB199]' 
                        : 'bg-white text-[#111827] border-[#EFECE6] hover:bg-[#EFECE6]'
                    }}`;
                    
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
                    const response = await fetch(`/api/summary?file_name=${{encodeURIComponent(fileName)}}`);
                    const data = await response.json();
                    
                    if (!response.ok || data.error) {{
                        viewer.innerHTML = `<div class="p-4 bg-red-50 text-red-700 rounded-lg text-sm">⚠️ Error loading summary payload dataset.</div>`;
                        return;
                    }}

                    let doiButtonHTML = "";
                    if(doiLink && doiLink !== "#") {{
                        doiButtonHTML = `<a href="${{doiLink}}" target="_blank" class="w-full sm:w-auto text-center bg-[#1D4ED8] hover:bg-[#2563EB] text-white font-semibold text-xs px-4 py-2.5 rounded-lg shadow-sm transition inline-block">🔗 Source Publication</a>`;
                    }}

                    // 🛠️ FIXED: Content maps safely inside an isolated .summary-body wrapper to guarantee immaculate text presentation metrics
                    viewer.innerHTML = `
                        <div class="flex flex-col sm:flex-row justify-between items-start gap-4 pb-4 border-b border-[#EFECE6] mb-6">
                            <div>
                                <h1 class="text-2xl font-bold tracking-tight text-black mb-2">📜 ${{title}}</h1>
                                <div class="flex flex-wrap gap-2 text-xs font-semibold">
                                    <span class="bg-[#EFF6FF] text-[#1E40AF] px-2.5 py-1 rounded-md border border-[#DBEAFE]">🧬 Specialty: ${{system}}</span>
                                    <span class="bg-[#FAF5FF] text-[#6B21A8] px-2.5 py-1 rounded-md border border-[#F3E8FF]">📖 Journal: ${{journal}}</span>
                                    <span class="bg-[#F1F5F9] text-[#475569] px-2.5 py-1 rounded-md border border-[#E2E8F0]">📑 Type: ${{type}}</span>
                                </div>
                            </div>
                            <div class="w-full sm:w-auto shrink-0">${{doiButtonHTML}}</div>
                        </div>
                        <div class="summary-body text-[#111827] text-[15px]">
                            ${{data.content}}
                        </div>
                    `;
                }} catch(err) {{
                    viewer.innerHTML = `<div class="p-4 bg-red-50 text-red-700 rounded-lg text-sm">❌ Network connection error: ${{err.message}}</div>`;
                }}
            }}

            window.onload = initializeAppMatrix;
        </script>
    </body>
    </html>
    """
    return html_content

@app.get("/api/summary")
async def get_cached_json_summary_contents(file_name: str):
    base_name = os.path.splitext(file_name)[0]
    target_json_path = os.path.join(OUTPUT_DIR, f"{base_name}.json")
    
    if not os.path.exists(target_json_path):
        return JSONResponse(status_code=404, content={"error": "Summary data asset missing from tracking registry."})
    try:
        with open(target_json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        summary_text = payload.get("clinical_summary_markdown", "No summary metadata object parsed.")
        return {"content": summary_text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})