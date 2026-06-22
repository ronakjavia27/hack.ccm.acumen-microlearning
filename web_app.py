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

# --- PAGE SETUP ---
st.set_page_config(page_title="hack.CCM | Knowledge Portal", page_icon="📚", layout="wide")

# =====================================================================
# 🎨 FINISHED CONTRAST BEIGE CSS MATRIX
# =====================================================================
st.markdown('''
<style>
    /* Background Canvas Settings */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #F5F5DC !important;
    }
    
    /* Typography defaults */
    p, li, span, label, h1, h2, h3, h4 {
        color: #1A1A1A !important;
        font-family: 'Georgia', serif !important;
    }

    /* Top Ribbon Header Wrapper */
    .utility-bar {
        background-color: #FFFFFF;
        padding: 16px 24px;
        border-radius: 8px;
        border: 1px solid #D2C7B7;
        margin-bottom: 25px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
    }
    
    /* Light Brown Layout Panel Box */
    .filter-container {
        background-color: #E6DFD3 !important;
        border: 1px solid #D2C7B7 !important;
        border-radius: 12px !important;
        padding: 22px !important;
        margin-bottom: 20px;
    }

    /* White Paper Container Block */
    .white-paper-card {
        background-color: #FFFFFF !important;
        padding: 35px !important;
        border-radius: 8px !important;
        border: 1px solid #D2C7B7 !important;
        box-shadow: 2px 4px 12px rgba(27, 23, 19, 0.04) !important;
    }

    /* 🛠️ Dropdown Selectboxes Override Hook */
    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        color: #1A1A1A !important;
        border: 1px solid #D2C7B7 !important;
        border-radius: 6px !important;
    }
    div[data-baseweb="menu"] li {
        background-color: #FFFFFF !important;
        color: #1A1A1A !important;
    }
    
    /* 🛠️ DOI Link Button Override Hook */
    div[data-testid="stLinkButton"] > a {
        background-color: #1D4ED8 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        transition: background-color 0.2s ease;
    }
    div[data-testid="stLinkButton"] > a:hover {
        background-color: #1E40AF !important;
        color: #FFFFFF !important;
    }
    
    /* Analytics Mini Pill */
    .stat-badge {
        background-color: #FFFFFF;
        padding: 6px 12px;
        border-radius: 4px;
        border: 1px solid #D2C7B7;
        font-size: 13px;
        font-weight: 600;
        display: inline-block;
        margin-top: 8px;
    }
    
    .nav-anchor {
        color: #1D4ED8 !important;
        text-decoration: none !important;
        font-weight: 600 !important;
        font-size: 14px;
        margin-left: 15px;
    }
    .nav-anchor:hover { text-decoration: underline !important; }

    @media (max-width: 768px) {
        .utility-bar { flex-direction: column; align-items: flex-start; }
        .white-paper-card { padding: 20px !important; }
    }
</style>
''', unsafe_allow_html=True)

# --- DATA RETRIEVAL ---
def load_approved_ledger():
    if not os.path.exists(EXCEL_TRACKER_FILE):
        return pd.DataFrame()
    try:
        df = pd.read_excel(EXCEL_TRACKER_FILE, sheet_name="Registry Logs")
        df.columns = df.columns.str.strip()
        return df[df["show_on_web"].astype(str).str.strip().str.lower() == "yes"]
    except Exception:
        return pd.DataFrame()

# =====================================================================
# 🖥️ APPLICATION VISUAL INTERFACE
# =====================================================================
st.markdown(f'''
    <div class="utility-bar">
        <div style="font-size: 24px; font-weight: 800; color: #000000; letter-spacing: -0.5px;">hack.CCM | Knowledge Portal</div>
        <div>
            <a class="nav-anchor" href="{FEEDBACK_FORM_URL}" target="_blank">📝 Feedback</a>
            <a class="nav-anchor" href="{SUBSCRIBE_FORM_URL}" target="_blank">📢 Subscribe</a>
            <a class="nav-anchor" href="{UNSUBSCRIBE_FORM_URL}" target="_blank">❌ Unsubscribe</a>
        </div>
    </div>
''', unsafe_allow_html=True)

df = load_approved_ledger()

if df.empty:
    st.info("👋 Welcome! Clinical summaries will update here once they pass verification constraints.")
else:
    col_filters, col_viewer = st.columns([1, 2], gap="large")

    with col_filters:
        # 🤎 POPULATED LEFT UPPER BOX: Metrics Display Card
        st.markdown('<div class="filter-container">', unsafe_allow_html=True)
        st.markdown('<h4 style="margin:0; padding:0; font-size:16px; letter-spacing:0.3px;">📊 COLLECTION METRICS</h4>', unsafe_allow_html=True)
        
        total_published = len(df)
        unique_specialties = df["System"].dropna().nunique()
        
        st.markdown(f'''
            <div style="margin-top:10px;">
                <div class="stat-badge" style="margin-right:10px;">📋 {total_published} Digests Live</div>
                <div class="stat-badge">🧬 {unique_specialties} Specialties</div>
            </div>
            <div style="margin-top: 15px; font-size: 12px; color: #64748B;">
                📱 <i>On mobile? Use the selector box below, then scroll down to read.</i>
            </div>
        ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Ingestion Filter Controls Box
        st.markdown('<div class="filter-container">', unsafe_allow_html=True)
        st.markdown('<h3 style="margin-top:0; padding-top:0;">🔍 Filter Inventory</h3>', unsafe_allow_html=True)
        
        search_query = st.text_input("Search Titles", placeholder="Type keywords or paper titles...", label_visibility="collapsed")
        
        systems = ["All Specialties"] + sorted(df["System"].dropna().unique().tolist())
        selected_system = st.selectbox("Specialty Subject Field", systems)
        
        types = ["All Types"] + sorted(df["Type of Article"].dropna().unique().tolist())
        selected_type = st.selectbox("Article Archetype", types)
        
        # Execution of layout queries
        filtered_df = df.copy()
        if selected_system != "All Specialties":
            filtered_df = filtered_df[filtered_df["System"] == selected_system]
        if selected_type != "All Types":
            filtered_df = filtered_df[filtered_df["Type of Article"] == selected_type]
        if search_query:
            filtered_df = filtered_df[filtered_df["Paper/Guideline Name"].str.contains(search_query, case=False, na=False)]
            
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Live selector deck list
        st.markdown('### 📑 Available Papers')
        if filtered_df.empty:
            st.warning("No entries match active matrix query.")
            selected_paper = None
        else:
            selected_paper = st.radio(
                "Select Paper",
                filtered_df["Paper/Guideline Name"].tolist(),
                label_visibility="collapsed"
            )

    with col_viewer:
        if selected_paper:
            target_row = df[df["Paper/Guideline Name"] == selected_paper].iloc[0]
            
            title_block, doi_block = st.columns([3, 1])
            with title_block:
                st.markdown(f'<h2 style="margin:0; padding:0; font-size:24px;">📜 {target_row["Paper/Guideline Name"]}</h2>', unsafe_allow_html=True)
            with doi_block:
                doi_url = str(target_row.get("DOI", "")).strip()
                if doi_url.startswith("http"):
                    st.link_button("🔗 Source Article", doi_url, use_container_width=True)

            st.markdown(f'''
                <div style="margin-top: 10px; margin-bottom: 20px;">
                    <span style="background-color:#EFF6FF; color:#1E40AF; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:600; margin-right:8px; border:1px solid #DBEAFE;">🧬 System: {target_row['System']}</span>
                    <span style="background-color:#FAF5FF; color:#6B21A8; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:600; margin-right:8px; border:1px solid #F3E8FF;">📖 {target_row['Journal Name']}</span>
                    <span style="background-color:#F1F5F9; color:#475569; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:600; border:1px solid #E2E8F0;">📑 {target_row['Type of Article']}</span>
                </div>
            ''', unsafe_allow_html=True)

            st.markdown('<div class="white-paper-card">', unsafe_allow_html=True)
            
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