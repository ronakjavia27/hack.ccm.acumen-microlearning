import os
import json
import pandas as pd
import streamlit as st

# =====================================================================
# 🌐 CONFIGURATION & SETTINGS
# =====================================================================
FEEDBACK_FORM_URL    = "https://docs.google.com/forms/d/1b5uifsDa73u42tlfKK3RGto_hLiwT-TtotQwov0O0b4"
SUBSCRIBE_FORM_URL   = "https://docs.google.com/forms/d/1s1UE1gHsTBOirAPW4beST3DS6D_ra-whkndTq5iIOHQ"
UNSUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/1uv_Xwymc8RFhsvK5L0oV9Rc16jdP0xRTrDW7zv_P5A0"

# --- STREAMLIT PAGE CONFIG ---
st.set_page_config(page_title="hack.CCM | Knowledge Portal", layout="wide")

# Paths
OUTPUT_DIR         = "./output_files"
EXCEL_TRACKER_FILE = "./sent_summaries.xlsx"

# =====================================================================
# 🎨 AESTHETIC CSS INJECTION
# =====================================================================
st.markdown("""
<style>

/* ── GLOBAL RESET & BASE ──────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

.stApp {
    background-color: #F4F1E8 !important;
}

/* Remove default Streamlit top padding */
.block-container {
    padding-top: 0rem !important;
    padding-bottom: 2rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 100% !important;
}

/* ── TOP NAVIGATION BAR ──────────────────────────────────────── */
.top-nav {
    background-color: #1A1A1A;
    padding: 0 2.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 62px;
    margin-bottom: 0;
    margin-left: -2rem;
    margin-right: -2rem;
    margin-top: -1rem;
    position: sticky;
    top: 0;
    z-index: 999;
}

.nav-logo {
    font-family: 'Playfair Display', Georgia, serif !important;
    font-size: 20px;
    font-weight: 700;
    color: #F4F1E8 !important;
    letter-spacing: 0.04em;
    text-transform: none;
}

.nav-logo span {
    color: #C8B88A !important;
}

.nav-links {
    display: flex;
    gap: 0;
    align-items: center;
}

.nav-link {
    color: #C8C0B0 !important;
    text-decoration: none !important;
    font-size: 12.5px;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 8px 18px;
    border: 1px solid transparent;
    border-radius: 3px;
    transition: all 0.2s ease;
    margin-left: 6px;
}

.nav-link:hover {
    color: #F4F1E8 !important;
    border-color: #C8B88A;
}

.nav-link.primary {
    background-color: #C8B88A;
    color: #1A1A1A !important;
    border-color: #C8B88A;
}

.nav-link.primary:hover {
    background-color: #B8A87A;
    border-color: #B8A87A;
    color: #1A1A1A !important;
}

/* ── THIN GOLD RULE BELOW NAV ─────────────────────────────────── */
.nav-rule {
    height: 2px;
    background: linear-gradient(to right, #C8B88A, #E8E0CC, #C8B88A);
    margin-left: -2rem;
    margin-right: -2rem;
    margin-bottom: 1.8rem;
}

/* ── LEFT FILTER PANEL ───────────────────────────────────────── */
.filter-panel {
    background-color: #EDEADF;
    border: 1px solid #D8D2C2;
    border-radius: 6px;
    padding: 24px 20px 28px 20px;
    min-height: 82vh;
}

.panel-section-label {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #7A7060 !important;
    margin-bottom: 10px;
    margin-top: 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #D0CAB8;
}

.article-count-badge {
    display: inline-block;
    background: #C8B88A;
    color: #1A1A1A !important;
    font-size: 10px;
    font-weight: 600;
    padding: 1px 7px;
    border-radius: 10px;
    margin-left: 6px;
    vertical-align: middle;
    letter-spacing: 0.05em;
}

/* ── ARTICLE LIST BUTTONS ────────────────────────────────────── */
.stButton > button {
    background-color: #FFFFFF !important;
    color: #2C2416 !important;
    border: 1px solid #D8D2C2 !important;
    border-radius: 4px !important;
    text-align: left !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    line-height: 1.45 !important;
    padding: 10px 13px !important;
    margin-bottom: 5px !important;
    width: 100% !important;
    transition: all 0.18s ease !important;
    box-shadow: none !important;
}

.stButton > button:hover {
    background-color: #C8B88A !important;
    border-color: #B8A87A !important;
    color: #1A1A1A !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08) !important;
}

.stButton > button:focus {
    outline: none !important;
    box-shadow: 0 0 0 2px #C8B88A !important;
}

/* ── STREAMLIT INPUTS RESTYLED ───────────────────────────────── */
.stTextInput > div > div > input {
    background-color: #FFFFFF !important;
    border: 1px solid #D0CAB8 !important;
    border-radius: 4px !important;
    color: #1A1A1A !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    padding: 8px 12px !important;
}

.stTextInput > div > div > input:focus {
    border-color: #C8B88A !important;
    box-shadow: 0 0 0 2px rgba(200, 184, 138, 0.25) !important;
}

.stSelectbox > div > div {
    background-color: #FFFFFF !important;
    border: 1px solid #D0CAB8 !important;
    border-radius: 4px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    color: #1A1A1A !important;
}

.stSelectbox > div > div:focus-within {
    border-color: #C8B88A !important;
    box-shadow: 0 0 0 2px rgba(200, 184, 138, 0.25) !important;
}

/* ── RIGHT VIEWER PANEL ──────────────────────────────────────── */
.viewer-panel {
    background-color: #FFFFFF;
    border: 1px solid #D8D2C2;
    border-radius: 6px;
    padding: 32px 36px 36px 36px;
    min-height: 82vh;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

/* Article title in viewer */
.article-title {
    font-family: 'Playfair Display', Georgia, serif !important;
    font-size: 24px !important;
    font-weight: 700 !important;
    color: #1A1A1A !important;
    line-height: 1.3 !important;
    margin-bottom: 0 !important;
    margin-top: 0 !important;
}

/* Tags row */
.meta-tags {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin: 10px 0 18px 0;
}

.meta-tag {
    background: #F0EDE3;
    border: 1px solid #D8D2C2;
    border-radius: 3px;
    font-size: 10.5px;
    font-weight: 500;
    color: #5A5040 !important;
    padding: 3px 10px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

/* Divider rule */
.content-rule {
    border: none;
    border-top: 1.5px solid #EAE6DC;
    margin: 16px 0 24px 0;
}

/* Summary content typography */
.summary-body h1, .summary-body h2, .summary-body h3,
.summary-body h4, .summary-body h5 {
    font-family: 'Playfair Display', Georgia, serif !important;
    color: #1A1A1A !important;
    margin-top: 1.4em !important;
    margin-bottom: 0.4em !important;
}

.summary-body h2 { font-size: 18px !important; }
.summary-body h3 { font-size: 15.5px !important; }

.summary-body p, .summary-body li {
    font-family: 'Inter', sans-serif !important;
    font-size: 14.5px !important;
    color: #2C2416 !important;
    line-height: 1.75 !important;
}

.summary-body strong {
    color: #1A1A1A !important;
    font-weight: 600 !important;
}

.summary-body ul, .summary-body ol {
    padding-left: 1.4em !important;
    margin-bottom: 0.8em !important;
}

/* ── EMPTY STATE ─────────────────────────────────────────────── */
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 60vh;
    text-align: center;
}

.empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
    opacity: 0.35;
}

.empty-title {
    font-family: 'Playfair Display', Georgia, serif !important;
    font-size: 20px !important;
    font-weight: 600 !important;
    color: #5A5040 !important;
    margin-bottom: 8px;
}

.empty-sub {
    font-size: 13.5px !important;
    color: #8A8070 !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── DOI LINK BUTTON (streamlit link_button) ─────────────────── */
.stLinkButton > a {
    background-color: #1A1A1A !important;
    color: #F4F1E8 !important;
    border: 1px solid #1A1A1A !important;
    border-radius: 4px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    padding: 7px 16px !important;
    text-decoration: none !important;
    transition: all 0.18s ease !important;
    white-space: nowrap !important;
}

.stLinkButton > a:hover {
    background-color: #C8B88A !important;
    border-color: #C8B88A !important;
    color: #1A1A1A !important;
}

/* ── HIDE STREAMLIT CHROME ───────────────────────────────────── */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }

/* Label styling for inputs */
.stTextInput label, .stSelectbox label {
    font-size: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: #7A7060 !important;
}

/* Scrollable article list */
.article-scroll-area {
    max-height: 52vh;
    overflow-y: auto;
    padding-right: 4px;
    margin-top: 8px;
}

.article-scroll-area::-webkit-scrollbar {
    width: 4px;
}

.article-scroll-area::-webkit-scrollbar-track {
    background: #EDEADF;
}

.article-scroll-area::-webkit-scrollbar-thumb {
    background: #C8B88A;
    border-radius: 2px;
}

</style>
""", unsafe_allow_html=True)


# =====================================================================
# 📦 DATA HANDLING
# =====================================================================
@st.cache_data
def get_data():
    if not os.path.exists(EXCEL_TRACKER_FILE):
        return pd.DataFrame()
    df = pd.read_excel(EXCEL_TRACKER_FILE, sheet_name="Registry Logs")
    df.columns = df.columns.str.strip()
    return df[df["show_on_web"].astype(str).str.lower() == "yes"]


# =====================================================================
# 🖥️ UI IMPLEMENTATION
# =====================================================================

# ── 1. TOP NAVIGATION BAR ─────────────────────────────────────────
st.markdown(f"""
<div class="top-nav">
    <div class="nav-logo">hack<span>.</span>CCM &nbsp;|&nbsp; Knowledge Portal</div>
    <div class="nav-links">
        <a href="{FEEDBACK_FORM_URL}"    class="nav-link"         target="_blank">Feedback</a>
        <a href="{SUBSCRIBE_FORM_URL}"   class="nav-link primary" target="_blank">Subscribe</a>
        <a href="{UNSUBSCRIBE_FORM_URL}" class="nav-link"         target="_blank">Unsubscribe</a>
    </div>
</div>
<div class="nav-rule"></div>
""", unsafe_allow_html=True)

df = get_data()

# ── 2. MAIN LAYOUT: 33% | 66% ─────────────────────────────────────
col_filter, col_view = st.columns([1, 2], gap="large")


# ── LEFT PANEL: FILTERS + ARTICLE LIST ────────────────────────────
with col_filter:
    st.markdown('<div class="filter-panel">', unsafe_allow_html=True)

    st.markdown('<p class="panel-section-label">Search</p>', unsafe_allow_html=True)
    search_query = st.text_input("", placeholder="Type to search articles...", label_visibility="collapsed")

    st.markdown('<p class="panel-section-label" style="margin-top:18px;">Subject</p>', unsafe_allow_html=True)
    if not df.empty and "System" in df.columns:
        systems  = ["All"] + sorted(df["System"].dropna().unique().tolist())
    else:
        systems  = ["All"]
    sel_sys = st.selectbox("", systems, label_visibility="collapsed")

    st.markdown('<p class="panel-section-label" style="margin-top:14px;">Article Type</p>', unsafe_allow_html=True)
    if not df.empty and "Type of Article" in df.columns:
        types = ["All"] + sorted(df["Type of Article"].dropna().unique().tolist())
    else:
        types = ["All"]
    sel_type = st.selectbox("", types, label_visibility="collapsed", key="type_select")

    # ── FILTER LOGIC ──
    filtered_df = df.copy()
    if not filtered_df.empty:
        if sel_sys  != "All": filtered_df = filtered_df[filtered_df["System"] == sel_sys]
        if sel_type != "All": filtered_df = filtered_df[filtered_df["Type of Article"] == sel_type]
        if search_query:
            filtered_df = filtered_df[
                filtered_df["Paper/Guideline Name"].str.contains(search_query, case=False, na=False)
            ]

    count = len(filtered_df)
    st.markdown(
        f'<p class="panel-section-label" style="margin-top:22px;">'
        f'Articles <span class="article-count-badge">{count}</span></p>',
        unsafe_allow_html=True
    )

    # Scrollable article list
    st.markdown('<div class="article-scroll-area">', unsafe_allow_html=True)
    if filtered_df.empty:
        st.markdown('<p style="font-size:13px; color:#8A8070; text-align:center; padding-top:24px;">No articles match your filters.</p>', unsafe_allow_html=True)
    else:
        for _, row in filtered_df.iterrows():
            if st.button(row["Paper/Guideline Name"], key=row["File Name"], use_container_width=True):
                st.session_state.selected_file = row["File Name"]
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # end filter-panel


# ── RIGHT PANEL: ARTICLE VIEWER ────────────────────────────────────
with col_view:
    selected_file = st.session_state.get("selected_file")

    st.markdown('<div class="viewer-panel">', unsafe_allow_html=True)

    if selected_file and not df.empty:
        row_match = df[df["File Name"] == selected_file]
        if not row_match.empty:
            row = row_match.iloc[0]

            # ── Title row + DOI button ──
            title_col, doi_col = st.columns([4, 1], gap="small")

            with title_col:
                st.markdown(
                    f'<h1 class="article-title">{row["Paper/Guideline Name"]}</h1>',
                    unsafe_allow_html=True
                )

            doi_link = str(row.get("DOI", "")).strip()
            with doi_col:
                if doi_link and doi_link.lower() != "none" and doi_link.startswith("http"):
                    st.markdown("<div style='padding-top:6px;'>", unsafe_allow_html=True)
                    st.link_button("↗ View Paper", doi_link, use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)

            # ── Meta tags ──
            system_val = str(row.get("System", "")).strip()
            type_val   = str(row.get("Type of Article", "")).strip()
            tags_html  = ""
            if system_val and system_val.lower() != "nan":
                tags_html += f'<span class="meta-tag">{system_val}</span>'
            if type_val and type_val.lower() != "nan":
                tags_html += f'<span class="meta-tag">{type_val}</span>'
            if tags_html:
                st.markdown(f'<div class="meta-tags">{tags_html}</div>', unsafe_allow_html=True)

            st.markdown('<hr class="content-rule">', unsafe_allow_html=True)

            # ── Summary content ──
            json_path = os.path.join(OUTPUT_DIR, os.path.splitext(selected_file)[0] + ".json")
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                summary_md = content.get("clinical_summary_markdown", "No summary available.")
                st.markdown(f'<div class="summary-body">', unsafe_allow_html=True)
                st.markdown(summary_md)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    '<p style="color:#8A8070; font-size:14px; font-style:italic;">Summary data pending upload.</p>',
                    unsafe_allow_html=True
                )
        else:
            # Article no longer in filtered data
            st.session_state.selected_file = None

    # ── EMPTY STATE ──
    if not selected_file:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">📄</div>
            <div class="empty-title">Select an article to read</div>
            <div class="empty-sub">Use the filters on the left to browse the knowledge library.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # end viewer-panel
