import os
import json
import pandas as pd
import streamlit as st

# =====================================================================
# 🌐 CONFIGURATION & SETTINGS
# =====================================================================
FEEDBACK_FORM_URL = "https://docs.google.com/forms/d/1b5uifsDa73u42tlfKK3RGto_hLiwT-TtotQwov0O0b4"
SUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/1s1UE1gHsTBOirAPW4beST3DS6D_ra-whkndTq5iIOHQ"
UNSUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/1uv_Xwymc8RFhsvK5L0oV9Rc16jdP0xRTrDW7zv_P5A0"

# --- STREAMLIT PAGE CONFIG ---
st.set_page_config(page_title="hack.CCM | Knowledge Portal", layout="wide")

# Paths
OUTPUT_DIR = "./output_files"
EXCEL_TRACKER_FILE = "./sent_summaries.xlsx"

# =====================================================================
# 🎨 AESTHETIC CSS INJECTION
# =====================================================================
st.markdown("""
    <style>
    .stApp { background-color: #F5F5DC !important; }
    /* Font and Color Settings */
    body, p, li, div { color: #1A1A1A !important; font-family: 'Georgia', serif !important; }
    h1, h2, h3 { color: #000000 !important; font-weight: bold !important; }
    
    /* Utility Bar */
    .utility-bar { background-color: #FFFFFF; padding: 15px; border-radius: 8px; border: 1px solid #D1D5DB; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; }
    
    /* Summary Card Styling */
    .summary-card { background-color: #FFFFFF; padding: 30px; border-radius: 4px; border: 1px solid #D1D5DB; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    
    /* Sidebar/Filters Area */
    .sidebar-panel { background-color: #EFEFE0; padding: 20px; border-radius: 8px; border: 1px solid #D1D5DB; }
    </style>
""", unsafe_allow_html=True)

# --- DATA HANDLING ---
@st.cache_data
def get_data():
    if not os.path.exists(EXCEL_TRACKER_FILE): return pd.DataFrame()
    df = pd.read_excel(EXCEL_TRACKER_FILE, sheet_name="Registry Logs")
    df.columns = df.columns.str.strip()
    return df[df["show_on_web"].astype(str).str.lower() == "yes"]

# =====================================================================
# 🖥️ UI IMPLEMENTATION
# =====================================================================

# 1. Top Utility Header
st.markdown(f'''
    <div class="utility-bar">
        <div style="font-size: 24px; font-weight: 800;">hack.CCM | Knowledge Portal</div>
        <div>
            <a href="{FEEDBACK_FORM_URL}" style="margin-right:15px; color:#1A1A1A;">Feedback</a>
            <a href="{SUBSCRIBE_FORM_URL}" style="margin-right:15px; color:#1A1A1A;">Subscribe</a>
            <a href="{UNSUBSCRIBE_FORM_URL}" style="color:#1A1A1A;">Unsubscribe</a>
        </div>
    </div>
''', unsafe_allow_html=True)

df = get_data()

# Split Layout: 33% Left, 66% Right
col_filter, col_view = st.columns([1, 2])

# Left Panel (Filters)
with col_filter:
    st.markdown('<div class="sidebar-panel">', unsafe_allow_html=True)
    st.markdown("### 🔍 Filter Articles")
    search_query = st.text_input("Search titles...")
    
    systems = ["All"] + sorted(df["System"].unique().tolist())
    sel_sys = st.selectbox("Subject:", systems)
    
    types = ["All"] + sorted(df["Type of Article"].unique().tolist())
    sel_type = st.selectbox("Article Type:", types)
    
    # Filter Logic
    filtered_df = df.copy()
    if sel_sys != "All": filtered_df = filtered_df[filtered_df["System"] == sel_sys]
    if sel_type != "All": filtered_df = filtered_df[filtered_df["Type of Article"] == sel_type]
    if search_query: filtered_df = filtered_df[filtered_df["Paper/Guideline Name"].str.contains(search_query, case=False)]
    
    st.markdown("### 📜 Articles")
    for _, row in filtered_df.iterrows():
        # Store selection in session state
        if st.button(row["Paper/Guideline Name"], key=row["File Name"], use_container_width=True):
            st.session_state.selected_file = row["File Name"]
    st.markdown('</div>', unsafe_allow_html=True)

# Right Panel (The Summary Viewer)
with col_view:
    selected_file = st.session_state.get("selected_file")
    
    if selected_file:
        row = df[df["File Name"] == selected_file].iloc[0]
        
        # Title + DOI Button (Top Right alignment)
        title_top, doi_btn = st.columns([3, 1])
        title_top.markdown(f"## {row['Paper/Guideline Name']}")
        
        doi_link = str(row.get("DOI", "")).strip()
        if doi_link and doi_link.lower() != "none" and doi_link.startswith("http"):
            doi_btn.link_button("🔗 View Paper", doi_link, use_container_width=True)
            
        st.markdown('<div class="summary-card">', unsafe_allow_html=True)
        # Content
        json_path = os.path.join(OUTPUT_DIR, os.path.splitext(selected_file)[0] + ".json")
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                st.markdown(content.get("clinical_summary_markdown", "No summary available."))
        else:
            st.write("Summary data pending...")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Select an article from the left panel to begin reading.")