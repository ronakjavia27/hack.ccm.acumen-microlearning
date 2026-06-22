import os
import json
import pandas as pd
import streamlit as st

# =====================================================================
# 🌐 GLOBAL LINKS CONFIGURATION
# =====================================================================
FEEDBACK_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSd6xRmmimmVc0Sv4AeNls-oxLR6k_zX8D_QERFZwPP6zlfjRw/viewform?usp=header"
SUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSffsrF8DPWaTa-03XisMqSU5Da_8QdE-JrINdDP5iRmvWAI8Q/viewform?usp=header"
UNSUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScz864mkLh5AqBYVzAh573hWu98NdmwwPC2vaU1lfBE3WHHHg/viewform?usp=header"

OUTPUT_DIR = "./output_files"
EXCEL_TRACKER_FILE = "./sent_summaries.xlsx"

# --- SYSTEM PAGE IDENTITY INITIALIZATION ---
st.set_page_config(page_title="hack.CCM | Knowledge Portal", page_icon="📚", layout="wide")

# =====================================================================
# 🎨 COLOR CODES SIGNIFICATION MAP & CSS DECK
# =====================================================================
# 🏷️ CANVAS_BG      = #FDFBF7 -> Main Application Page Background (Soft cream)
# 🏷️ PANEL_BG       = #EFECE6 -> Filter Containers Background (Subtle tan)
# 🏷️ CARD_BG        = #FFFFFF -> Safe Reading Card Canvas Background (Pure white)
# 🏷️ INK_PRIMARY    = #111827 -> absolute High-Contrast Reading Typography (Charcoal)
# 🏷️ INK_MUTED      = #4B5563 -> Secondary Metadata Labels / Subheadings (Muted grey)
# 🏷️ ACCENT_BLUE    = #1D4ED8 -> Clickable Action Links & Anchor Elements (Royal Blue)
# 🏷️ HOVER_BLUE     = #2563EB -> Button Hover Micro-Interactions (Mid Blue)
# =====================================================================
st.markdown('''
<style>
    /* 1. Global Page Canvas Setup */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #FDFBF7 !important;
    }
    
    /* 2. Global Type & Readability Settings */
    p, li, span, label, h1, h2, h3, h4 {
        color: #111827 !important;
        font-family: 'Georgia', serif !important;
    }

    /* 3. Top Header Navigation Ribbon Bar */
    .utility-bar {
        background-color: #FFFFFF;
        padding: 16px 24px;
        border-radius: 12px;
        border: 1px solid #EFECE6;
        margin-bottom: 25px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    
    /* 4. Structural Light Brown Filter Boxes */
    .tan-control-box {
        background-color: #EFECE6 !important;
        border: 1px solid #DCD9D2 !important;
        border-radius: 16px !important;
        padding: 20px !important;
        margin-bottom: 20px !important;
    }

    /* 5. Pure White Academic Document Card */
    .white-reading-card {
        background-color: #FFFFFF !important;
        padding: 35px !important;
        border-radius: 16px !important;
        border: 1px solid #EFECE6 !important;
        box-shadow: 0 4px 20px rgba(27, 23, 19, 0.02) !important;
    }

    /* 6. Text Selection Badges */
    .custom-pill {
        display: inline-block;
        font-weight: 600;
        font-size: 12px;
        padding: 4px 10px;
        border-radius: 6px;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    
    /* 7. Action Hyperlink Styling */
    .nav-link-item {
        color: #1D4ED8 !important;
        text-decoration: none !important;
        font-weight: 600 !important;
        font-size: 14px;
        margin-left: 15px;
    }
    .nav-link-item:hover { text-decoration: underline !important; color: #2563EB !important; }

    /* Streamlit Widget UI Overrides */
    div[data-baseweb="select"] > div, input {
        background-color: #FFFFFF !important;
        color: #111827 !important;
        border: 1px solid #DCD9D2 !important;
    }
    
    /* Hide native container paddings for tight absolute alignments */
    [data-testid="stVerticalBlock"] { gap: 0rem !important; }
</style>
''', unsafe_allow_html=True)

# --- DATA LEDGER MANAGEMENT ---
def load_verified_ledger():
    if not os.path.exists(EXCEL_TRACKER_FILE):
        return pd.DataFrame()
    try:
        df = pd.read_excel(EXCEL_TRACKER_FILE, sheet_name="Registry Logs")
        df.columns = df.columns.str.strip()
        return df[df["show_on_web"].astype(str).str.strip().str.lower() == "yes"]
    except Exception:
        return pd.DataFrame()

# =====================================================================
# 🖥️ VISUAL FRAMEWORK PRESENTATION
# =====================================================================

# Top Universal Navigation Bar
st.markdown(f'''
    <div class="utility-bar">
        <div style="font-size: 22px; font-weight: bold; color: #111827; letter-spacing: -0.5px;">🧠 hack.CCM | Knowledge Portal</div>
        <div>
            <a class="nav-link-item" href="{FEEDBACK_FORM_URL}" target="_blank">📝 Feedback</a>
            <a class="nav-link-item" href="{SUBSCRIBE_FORM_URL}" target="_blank">📢 Subscribe</a>
            <a class="nav-link-item" href="{UNSUBSCRIBE_FORM_URL}" target="_blank">❌ Unsubscribe</a>
        </div>
    </div>
''', unsafe_allow_html=True)

df = load_verified_ledger()

if df.empty:
    st.info("👋 Welcome! Verified clinical digests will appear here once they are dispatched via the email loop.")
else:
    # Responsive Column Layout Matrix (33% Filter Suite, 66% Document Sheet)
    col_filters, col_viewer = st.columns([1, 2], gap="large")

    with col_filters:
        # Left Panel Box A: Collection Metrics Card
        st.markdown('<div class="tan-control-box">', unsafe_allow_html=True)
        st.markdown('<h4 style="margin:0 0 10px 0; color:#4B5563; font-size:12px; font-weight:bold; tracking:0.05em;">📊 REPOSITORY STATUS</h4>', unsafe_allow_html=True)
        st.markdown(f'''
            <div style="display:flex; gap:8px;">
                <span style="background:#FFFFFF; border:1px solid #DCD9D2; padding:6px 12px; rounded-md; font-size:13px; font-weight:bold;">📋 {len(df)} Live Summaries</span>
                <span style="background:#FFFFFF; border:1px solid #DCD9D2; padding:6px 12px; rounded-md; font-size:13px; font-weight:bold;">🧬 {df["System"].dropna().nunique()} Systems</span>
            </div>
        ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Left Panel Box B: Multi-Input Filtering Logic
        st.markdown('<div class="tan-control-box">', unsafe_allow_html=True)
        st.markdown('<h4 style="margin:0 0 12px 0; color:#4B5563; font-size:12px; font-weight:bold; tracking:0.05em;">🔍 FILTER INVENTORY</h4>', unsafe_allow_html=True)
        
        search_query = st.text_input("Title Text Search", placeholder="Type title keywords...", label_visibility="collapsed")
        systems = ["All Specialties"] + sorted(df["System"].dropna().unique().tolist())
        selected_system = st.selectbox("Specialty", systems, label_visibility="visible")
        types = ["All Types"] + sorted(df["Type of Article"].dropna().unique().tolist())
        selected_type = st.selectbox("Article Archetype", types, label_visibility="visible")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Apply filter choices to the data collection subset
        filtered_df = df.copy()
        if selected_system != "All Specialties":
            filtered_df = filtered_df[filtered_df["System"] == selected_system]
        if selected_type != "All Types":
            filtered_df = filtered_df[filtered_df["Type of Article"] == selected_type]
        if search_query:
            filtered_df = filtered_df[filtered_df["Paper/Guideline Name"].str.contains(search_query, case=False, na=False)]
            
        # Left Panel List Selector Deck
        st.markdown('### 📑 Available Papers')
        if filtered_df.empty:
            st.warning("No entries match active parameters.")
            selected_paper = None
        else:
            selected_paper = st.radio(
                "Paper Select Navigation",
                filtered_df["Paper/Guideline Name"].tolist(),
                label_visibility="collapsed"
            )

    with col_viewer:
        if selected_paper:
            target_row = df[df["Paper/Guideline Name"] == selected_paper].iloc[0]
            
            # 🛠️ FIXED: Universal DOI Link Parser & Sanitizer
            raw_doi = str(target_row.get("DOI", "")).strip()
            clean_doi_url = None
            if raw_doi and raw_doi.lower() != "none":
                if raw_doi.startswith("http://") or raw_doi.startswith("https://"):
                    clean_doi_url = raw_doi
                else:
                    clean_doi_url = f"https://doi.org/{raw_doi}"

            # Document Viewer Header Grid
            title_box, action_box = st.columns([3, 1])
            with title_box:
                st.markdown(f'<h1 style="margin:0; padding:0; font-size:26px; font-weight:bold;">📜 {target_row["Paper/Guideline Name"]}</h1>', unsafe_allow_html=True)
            with action_box:
                if clean_doi_url:
                    st.link_button("🔗 Source Article", clean_doi_url, use_container_width=True)

            # Metadata Pill Badges Block
            st.markdown(f'''
                <div style="margin-top:12px; margin-bottom:20px;">
                    <span class="custom-pill" style="background-color:#EFF6FF; color:#1E40AF; border:1px solid #DBEAFE;">🧬 System: {target_row['System']}</span>
                    <span class="custom-pill" style="background-color:#FAF5FF; color:#6B21A8; border:1px solid #F3E8FF;">📖 Journal: {target_row['Journal Name']}</span>
                    <span class="custom-pill" style="background-color:#F1F5F9; color:#475569; border:1px solid #E2E8F0;">📑 Type: {target_row['Type of Article']}</span>
                </div>
            ''', unsafe_allow_html=True)

            # White Academic Paper Rendering Canvas
            st.markdown('<div class="white-reading-card">', unsafe_allow_html=True)
            
            # Fetch structured local summary texts
            json_filename = os.path.splitext(target_row["File Name"])[0] + ".json"
            json_path = os.path.join(OUTPUT_DIR, json_filename)
            
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as jf:
                        payload = json.load(jf)
                    st.markdown(payload.get("clinical_summary_markdown", "Empty markdown compiled."))
                except Exception as err:
                    st.error(f"Error parsing summary asset details: {err}")
            else:
                st.warning("Prerendered summary dataset is synchronizing downstream...")
                
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Pick an entry from the list index array on the left side to get started.")