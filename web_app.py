import os
import json
import pandas as pd
import gradio as gr

# =====================================================================
# 🌐 CONFIGURATIONS & COMPONENT LINK METRICS
# =====================================================================
FEEDBACK_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSd6xRmmimmVc0Sv4AeNls-oxLR6k_zX8D_QERFZwPP6zlfjRw/viewform?usp=header"
SUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSffsrF8DPWaTa-03XisMqSU5Da_8QdE-JrINdDP5iRmvWAI8Q/viewform?usp=header"
UNSUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScz864mkLh5AqBYVzAh573hWu98NdmwwPC2vaU1lfBE3WHHHg/viewform?usp=header"

OUTPUT_DIR = "./output_files"
EXCEL_TRACKER_FILE = "./sent_summaries.xlsx"

# =====================================================================
# 📊 LEGER INVENTORY RETRIEVAL GATEWAY
# =====================================================================
def load_verified_inventory():
    if not os.path.exists(EXCEL_TRACKER_FILE):
        return []
    try:
        df = pd.read_excel(EXCEL_TRACKER_FILE, sheet_name="Registry Logs")
        df.columns = df.columns.str.strip()
        if "show_on_web" in df.columns:
            df_filtered = df[df["show_on_web"].astype(str).str.strip().str.lower() == "yes"]
            return df_filtered.to_dict(orient="records")
        return []
    except Exception as e:
        return []

# =====================================================================
# 🛠️ INTERACTIVE ROUTING CONTROLLERS
# =====================================================================
def filter_article_index(search_txt, specialty_val, type_val):
    """Filters the primary dataset dynamically based on active filter input keys."""
    raw_pool = load_verified_inventory()
    filtered_options = []
    
    for row in raw_pool:
        match_search = (not search_txt) or (search_txt.lower() in str(row["Paper/Guideline Name"]).lower())
        match_specialty = (specialty_val == "All Specialties") or (str(row["System"]).strip() == specialty_val)
        match_type = (type_val == "All Types") or (str(row["Type of Article"]).strip() == type_val)
        
        if match_search and match_specialty and match_type:
            filtered_options.append(row["Paper/Guideline Name"])
            
    return gr.update(choices=filtered_options, value=filtered_options[0] if filtered_options else None)

def display_selected_summary(article_title):
    """Loads the true context string payload from cached JSON elements."""
    if not article_title:
        return gr.update(value="### 📚 Select an article from the index layout pane to render summary."), gr.update(visible=False)
        
    raw_pool = load_verified_inventory()
    target_row = None
    for row in raw_pool:
        if str(row["Paper/Guideline Name"]).strip() == str(article_title).strip():
            target_row = row
            break
            
    if target_row is None:
        return gr.update(value="⚠️ Critical Error: Selected log missing from data indexes."), gr.update(visible=False)
        
    # Build target clean JSON reference route mapping
    base_json_name = os.path.splitext(target_row["File Name"])[0] + ".json"
    full_json_path = os.path.join(OUTPUT_DIR, base_json_name)
    
    # Metadata context injection array
    meta_html = f"""
    <div style='margin-bottom:15px;'>
        <span style='background:#E0F2FE; color:#0369A1; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:600; margin-right:8px;'>🧬 System: {target_row.get('System','General')}</span>
        <span style='background:#F3E8FF; color:#6B21A8; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:600; margin-right:8px;'>📖 Journal: {target_row.get('Journal Name','Unknown')}</span>
        <span style='background:#F1F5F9; color:#475569; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:600;'>📑 Type: {target_row.get('Type of Article','Unclassified')}</span>
    </div>
    """
    
    if os.path.exists(full_json_path):
        try:
            with open(full_json_path, "r", encoding="utf-8") as jf:
                payload = json.load(jf)
            markdown_content = payload.get("clinical_summary_markdown", "Empty summary metadata parsed.")
            
            # Form header composite layouts 
            rendered_header = f"## {target_row['Paper/Guideline Name']}\n{meta_html}\n\n"
            
            doi_link = str(target_row.get("DOI", "")).strip()
            show_button = gr.update(visible=True, link=doi_link) if doi_link.startswith("http") else gr.update(visible=False)
            
            return gr.update(value=rendered_header + markdown_content), show_button
        except Exception as e:
            return gr.update(value=f"❌ Ingestion break mapping JSON file: {e}"), gr.update(visible=False)
            
    return gr.update(value="⚠️ Context block file not cached locally on system server disk arrays yet."), gr.update(visible=False)

# =====================================================================
# 🎨 HIGH-END ACCADEMIC TAILWIND & GRADIO UI LAYOUT DESIGN
# =====================================================================
CUSTOM_THEME_CSS = """
    /* Main application container backdrop setup */
    .gradio-container { background-color: #F5F5DC !important; font-family: 'Georgia', serif !important; }
    
    /* 🛠️ LIGHT BROWN CONTRAST BLOCKS (Replaced harsh blacks) */
    .light-brown-panel { background-color: #E6DFD3 !important; border: 1px solid #D2C7B7 !important; border-radius: 12px !important; padding: 20px !important; }
    
    /* Document Sheet Panel */
    .white-paper-pane { background-color: #FFFFFF !important; border: 1px solid #D2C7B7 !important; border-radius: 8px !important; padding: 30px !important; box-shadow: 2px 4px 12px rgba(27, 23, 19, 0.04) !important; }
    
    /* Text Color overrides for optimal baseline high-contrast parsing */
    p, li, span, label { color: #1A1A1A !important; font-size: 15px !important; }
    h1, h2, h3 { color: #000000 !important; font-weight: bold !important; font-family: 'Georgia', serif !important; }
    
    /* Top Utility Header Ribbon bar */
    .header-ribbon { background-color: #FFFFFF !important; border-bottom: 2px solid #E6DFD3 !important; padding: 15px 25px !important; border-radius: 8px !important; margin-bottom: 20px !important; }
    .nav-anchor { color: #1D4ED8 !important; text-decoration: none !important; font-weight: 600 !important; margin-left: 20px !important; font-size: 14px !important; }
    .nav-anchor:hover { text-decoration: underline !important; }
"""

# Initial database compile matrices
init_pool = load_verified_inventory()
specialties = sorted(list(set(str(r["System"]).strip() for r in init_pool if r.get("System"))))
types = sorted(list(set(str(r["Type of Article"]).strip() for r in init_pool if r.get("Type of Article"))))
default_options = [r["Paper/Guideline Name"] for r in init_pool]

with gr.Blocks(css=CUSTOM_THEME_CSS, title="hack.CCM Portal") as demo:
    
    # 1. Unified Universal Ribbon Header
    with gr.Row(elem_classes="header-ribbon"):
        gr.HTML(f"""
            <div style='display: flex; justify-content: space-between; align-items: center; width: 100%;'>
                <div style='font-size: 24px; font-weight: 800; color: #000000; letter-spacing: -0.5px;'>hack.CCM | Knowledge Portal</div>
                <div>
                    <a class='nav-anchor' href='{FEEDBACK_FORM_URL}' target='_blank'>📝 Feedback</a>
                    <a class='nav-anchor' href='{SUBSCRIBE_FORM_URL}' target='_blank'>📢 Subscribe</a>
                    <a class='nav-anchor' href='{UNSUBSCRIBE_FORM_URL}' target='_blank'>❌ Unsubscribe</a>
                </div>
            </div>
        """)
        
    # 2. Asymmetric Flex Column Deck Layout (Adaptive scaling for mobile stacking)
    with gr.Row():
        
        # Left Grid Panel (33% scale allocation)
        with gr.Column(scale=1, elem_classes="light-brown-panel"):
            gr.Markdown("### 🔍 Search & Filter Matrix")
            search_input = gr.Textbox(label="Keywords Search", placeholder="Type title keywords or topics...", show_label=True)
            
            specialty_filter = gr.Dropdown(choices=["All Specialties"] + specialties, value="All Specialties", label="Specialty Filter")
            type_filter = gr.Dropdown(choices=["All Types"] + types, value="All Types", label="Article Type Filter")
            
            gr.Markdown("---")
            gr.Markdown("### 📑 Dispatched Summaries Index")
            article_selector = gr.Radio(choices=default_options, label="Select brief below:", value=default_options[0] if default_options else None, interactive=True)
            
        # Right Grid Panel (66% scale allocation)
        with gr.Column(scale=2, elem_classes="white-paper-pane"):
            with gr.Row():
                with gr.Column(scale=4):
                    # Houses interactive headings and raw parsed markup
                    viewer_pane = gr.Markdown(value="### 📚 Choose a topic profile inside the index navigation layout to read details.")
                with gr.Column(scale=1):
                    doi_button = gr.Button("🔗 View Original Paper (DOI)", variant="primary", visible=False)
                    
    # =====================================================================
    # ⚡ CORE EVENT ENGINE HOOKS (REAL-TIME REACTIVE STREAMFLOW)
    # =====================================================================
    # Filter change array bindings
    filter_inputs = [search_input, specialty_filter, type_filter]
    for element in filter_inputs:
        element.change(fn=filter_article_index, inputs=filter_inputs, outputs=article_selector)
        
    # Content display bindings
    article_selector.change(fn=display_selected_summary, inputs=article_selector, outputs=[viewer_pane, doi_button])
    demo.load(fn=display_selected_summary, inputs=article_selector, outputs=[viewer_pane, doi_button])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=8501)