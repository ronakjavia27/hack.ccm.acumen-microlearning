import os
import json
import pandas as pd
import streamlit as st

# =====================================================================
# 🌐 GLOBAL CONFIGURATIONS & INTERACTIVE BOUNDARY LAYERS
# =====================================================================
# Set up your tracking form variables directly at the start of the deck:
FEEDBACK_FORM_URL = "https://docs.google.com/forms/d/e/your-feedback-form-id/viewform"
SUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/e/your-subscription-form-id/viewform"
UNSUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/e/your-unsubscribe-form-id/viewform"

# --- STREAMLIT PAGE CONFIG DECK ---
st.set_page_config(
    page_title="hack.CCM | Clinical Knowledge Portal",
    page_icon="🧠",
    layout="wide"
)

# Workspace Paths Mapping (Reads from root folder directly)
OUTPUT_DIR = "./output_files"
EXCEL_TRACKER_FILE = "./sent_summaries.xlsx"

# =====================================================================
# 🎨 RE-ENGINEERED WEB WORKSPACE STYLING BLOCKS (CSS OVERPOLISH)
# =====================================================================
st.markdown("""
    <style>
    /* Premium slate background palette configuration */
    .stApp { background-color: #F8FAFC !important; }
    
    /* Document Display Card Frame wrapper */
    .display-card-pane {
        background-color: #ffffff;
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(15, 23, 42, 0.04);
        border: 1px solid #E2E8F0;
        margin-top: 10px;
    }
    
    /* Metadata Pills Deck */
    .pill-badge {
        display: inline-block;
        background-color: #F0Fdf4;
        color: #166534;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        margin-right: 10px;
        border: 1px solid #DCFCE7;
    }
    .pill-specialty { background-color: #EFF6FF; color: #1E40AF; border-color: #DBEAFE; }
    .pill-journal { background-color: #FAF5FF; color: #6B21A8; border-color: #F3E8FF; }
    
    /* Layout clean text spacing metrics */
    h1, h2, h3 { color: #0F172A !important; font-weight: 700 !important; }
    p, li { color: #334155 !important; line-height: 1.7 !important; font-size: 15px !important; }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# 📊 LEGER INVENTORY RETRIEVALPASSE GATES
# =====================================================================
def load_verified_web_inventory():
    """Reads ledger workbook tables, fetching exclusively articles pushed via email."""
    if not os.path.exists(EXCEL_TRACKER_FILE):
        return []
    try:
        # Load from sheet name layer
        df = pd.read_excel(EXCEL_TRACKER_FILE, sheet_name="Registry Logs")
        df.columns = df.columns.str.strip()
        
        # Gate filter: restrict output explicitly to rows where show_on_web maps to 'Yes'
        if "show_on_web" in df.columns:
            df_filtered = df[df["show_on_web"].astype(str).str.strip().str.lower() == "yes"]
            return df_filtered.to_dict(orient="records")
        return []
    except Exception as e:
        st.error(f"⚠️ Tracking workbook registry read error: {e}")
        return []

# =====================================================================
# 🖥️ CORE PORTAL INTERFACE HEADER & COLUMN INTERACTION MATRIX
# =====================================================================
# Split header space into asymmetric layout fields 
title_col, utilities_col = st.columns([0.55, 0.45], gap="medium")

with title_col:
    st.markdown('<h1 style="margin:0; padding:0; font-size:32px;">🧠 hack.CCM Wiki Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:#64748B; margin-top:2px; font-size:14px;">Clinical Intelligence Feed & Live Dispatch Registries Matrix</p>', unsafe_allow_html=True)

with utilities_col:
    # Anchor multi-button rows at the base right side using Streamlit sub-columns
    st.write("") # Padding offset push
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    with btn_col1:
        st.link_button("📝 Submit Feedback", FEEDBACK_FORM_URL, use_container_width=True)
    with btn_col2:
        st.link_button("📢 Subscribe Feed", SUBSCRIBE_FORM_URL, use_container_width=True)
    with btn_col3:
        # Unsubscribe rendered via a distinct styled warning profile border boundary layer
        st.link_button("❌ Opt Out / Unsub", UNSUBSCRIBE_FORM_URL, use_container_width=True)

# =====================================================================
# 🎛️ SIDEBAR MENU SELECTION MATRIX & SYSTEM FILTERS
# =====================================================================
st.sidebar.markdown('### 🎛️ Clinical Filter Matrix')
approved_pool = load_verified_web_inventory()

if not approved_pool:
    st.markdown('<hr style="margin:20px 0;">', unsafe_allow_html=True)
    st.info("👋 System Standby: No verified, email-pushed clinical digest records are presently cached inside the public web-portal vector paths.")
else:
    # 1. Compile clean list options for Organ Systems & Article Types
    organ_systems_list = sorted(list(set(str(row["System"]).strip() for row in approved_pool if row.get("System"))))
    article_types_list = sorted(list(set(str(row["Type of Article"]).strip() for row in approved_pool if row.get("Type of Article"))))
    
    # 2. Add 'ALL' categories default fields to allow wide directory indexing maps
    selected_system = st.sidebar.selectbox("Filter Specialty Organ System:", ["All Specialties"] + organ_systems_list)
    selected_type = st.sidebar.selectbox("Filter Article Archetype Type:", ["All Types"] + article_types_list)
    
    # 3. Process database item list filter logic matching dropdown properties
    filtered_articles = []
    for row in approved_pool:
        match_system = (selected_system == "All Specialties" or str(row["System"]).strip() == selected_system)
        match_type = (selected_type == "All Types" or str(row["Type of Article"]).strip() == selected_type)
        if match_system and match_type:
            filtered_articles.append(row)
            
    st.sidebar.markdown('---')
    st.sidebar.markdown('### 📑 Available Summaries')
    
    if not filtered_articles:
        st.sidebar.warning("⚠️ No matches map to the picked combination filter keys.")
    else:
        # Compile a clean index list layout dictionary mapping
        article_options = {
            f"💡 [{row['System']}] {row['Paper/Guideline Name']}": row 
            for row in filtered_articles
        }
        
        selected_label = st.sidebar.radio(
            "Select specific topic brief below:", 
            list(article_options.keys()),
            label_visibility="collapsed"
        )
        
        # =====================================================================
        # 📖 RENDERING DOCUMENT PANE DOCK 
        # =====================================================================
        if selected_label:
            target_entry = article_options[selected_label]
            file_name = target_entry["File Name"]
            
            # Form path pointers targeting static json output context paths
            base_json_name = os.path.splitext(file_name)[0] + ".json"
            full_json_path = os.path.join(OUTPUT_DIR, base_json_name)
            
            # Draw primary white sheet panel container layout frame card
            st.markdown('<div class="display-card-pane">', unsafe_allow_html=True)
            st.markdown(f'<h2>📜 {target_entry["Paper/Guideline Name"]}</h2>', unsafe_allow_html=True)
            
            # Injection of organized medical tracking pill badges
            st.markdown(f"""
                <div style="margin-bottom: 20px;">
                    <span class="pill-badge pill-specialty">🧬 System: {target_entry['System']}</span>
                    <span class="pill-badge">✍️ Lead: {target_entry['Primary Authors']}</span>
                    <span class="pill-badge pill-journal">📖 Journal: {target_entry['Journal Name']}</span>
                    <span class="pill-badge" style="background-color:#F8FAFC; color:#475569; border-color:#CBD5E1;">📑 Type: {target_entry['Type of Article']}</span>
                </div>
            """, unsafe_allow_html=True)
            
            # External Gateway Routing Call Button Decks
            doi_string = str(target_entry.get("DOI", "")).strip()
            if doi_string and doi_string.lower() != "none" and doi_string.startswith("http"):
                st.link_button("🔗 Open Full Source Publication (DOI Gateway Link)", doi_string, type="primary")
            else:
                st.link_button("🔍 Query Title Reference Context on PubMed", f"https://pubmed.ncbi.nlm.nih.gov/?term={target_entry['Paper/Guideline Name']}", type="secondary")
                
            st.markdown('<hr style="border-top:1px solid #E2E8F0; margin: 25px 0;">', unsafe_allow_html=True)
            
            # Extract content string stored inside JSON files cleanly
            if os.path.exists(full_json_path):
                try:
                    with open(full_json_path, "r", encoding="utf-8") as jf:
                        summary_json_payload = json.load(jf)
                    
                    raw_summary_markdown = summary_json_payload.get("clinical_summary_markdown", "No content structured inside asset.")
                    
                    # Direct Streamlit Markdown Parsing prevents any text boundary truncation bugs!
                    st.markdown(raw_summary_markdown)
                    
                except Exception as read_error:
                    st.error(f"❌ Failed loading data fields text matrix: {read_error}")
            else:
                st.warning("⚠️ Information Notice: The structural data file for this entry is not cached in server workspace records yet.")
                
            st.markdown('</div>', unsafe_allow_html=True)