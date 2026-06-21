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
# 🎨 CSS INJECTION
# =====================================================================
st.markdown("""
<style>

/* ── FONTS ────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');

/* ── APP BACKGROUND ───────────────────────────────────────────── */
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background-color: #F4F1E8 !important;
}

/* ── KILL STREAMLIT'S OWN HEADER BAR (the white void) ─────────── */
[data-testid="stHeader"] {
    display: none !important;
    height: 0 !important;
}

/* ── BLOCK CONTAINER: zero top padding so nav sits at top ──────── */
.block-container {
    padding-top: 0 !important;
    padding-bottom: 2rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    max-width: 100% !important;
}

/* ── TOP NAV ──────────────────────────────────────────────────── */
.top-nav {
    background-color: #1A1A1A;
    padding: 0 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 58px;
    margin-left: -1.5rem;
    margin-right: -1.5rem;
    margin-bottom: 0;
}

.nav-logo {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 19px;
    font-weight: 700;
    color: #F4F1E8;
    letter-spacing: 0.03em;
}

.nav-logo .dot { color: #C8B88A; }

.nav-links { display: flex; gap: 6px; align-items: center; }

.nav-link {
    color: #B8B0A0;
    text-decoration: none;
    font-family: 'Inter', sans-serif;
    font-size: 11.5px;
    font-weight: 500;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    padding: 6px 15px;
    border: 1px solid transparent;
    border-radius: 3px;
    transition: all 0.18s ease;
}

.nav-link:hover { color: #F4F1E8; border-color: #C8B88A; }

.nav-link.primary {
    background-color: #C8B88A;
    color: #1A1A1A;
    border-color: #C8B88A;
}

.nav-link.primary:hover { background-color: #B8A87A; }

/* Gold rule under nav */
.nav-rule {
    height: 2px;
    background: linear-gradient(to right, #C8B88A, #EDE8D8, #C8B88A);
    margin-left: -1.5rem;
    margin-right: -1.5rem;
    margin-bottom: 1.4rem;
}

/* ── LEFT FILTER PANEL ────────────────────────────────────────── */
.filter-panel {
    background-color: #EDEADF;
    border: 1px solid #D5CFBF;
    border-radius: 6px;
    padding: 22px 18px 26px 18px;
    min-height: 84vh;
}

.section-label {
    font-family: 'Inter', sans-serif;
    font-size: 9.5px;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #7A7060;
    margin: 0 0 8px 0;
    padding-bottom: 5px;
    border-bottom: 1px solid #CEC8B5;
    display: block;
}

.article-count-badge {
    background: #C8B88A;
    color: #1A1A1A;
    font-size: 10px;
    font-weight: 700;
    padding: 1px 7px;
    border-radius: 10px;
    margin-left: 5px;
    vertical-align: middle;
}

/* ── ARTICLE BUTTONS ──────────────────────────────────────────── */
.stButton > button {
    background-color: #FFFFFF !important;
    color: #2C2416 !important;
    border: 1px solid #D5CFBF !important;
    border-radius: 4px !important;
    text-align: left !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 12.5px !important;
    font-weight: 400 !important;
    line-height: 1.4 !important;
    padding: 9px 12px !important;
    margin-bottom: 4px !important;
    width: 100% !important;
    box-shadow: none !important;
    transition: background-color 0.15s, border-color 0.15s !important;
}

.stButton > button:hover {
    background-color: #C8B88A !important;
    border-color: #B8A87A !important;
    color: #1A1A1A !important;
}

/* ── STREAMLIT INPUT RESTYLING ────────────────────────────────── */
.stTextInput > div > div > input {
    background-color: #FFFFFF !important;
    border: 1px solid #CEC8B5 !important;
    border-radius: 4px !important;
    color: #1A1A1A !important;
    font-size: 13px !important;
    padding: 7px 11px !important;
}

.stTextInput > div > div > input:focus {
    border-color: #C8B88A !important;
    box-shadow: 0 0 0 2px rgba(200,184,138,0.2) !important;
    outline: none !important;
}

.stSelectbox > div > div {
    background-color: #FFFFFF !important;
    border: 1px solid #CEC8B5 !important;
    border-radius: 4px !important;
    font-size: 13px !important;
    color: #1A1A1A !important;
}

/* ── SCROLLABLE ARTICLE LIST ──────────────────────────────────── */
.article-scroll {
    max-height: 48vh;
    overflow-y: auto;
    padding-right: 3px;
    margin-top: 6px;
}

.article-scroll::-webkit-scrollbar { width: 3px; }
.article-scroll::-webkit-scrollbar-track { background: #E4E1D5; }
.article-scroll::-webkit-scrollbar-thumb { background: #C8B88A; border-radius: 2px; }

/* ── RIGHT VIEWER PANEL ───────────────────────────────────────── */
.viewer-panel {
    background-color: #FFFFFF;
    border: 1px solid #D5CFBF;
    border-radius: 6px;
    padding: 30px 34px 34px 34px;
    min-height: 84vh;
    box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}

/* Article title */
.article-title {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 22px;
    font-weight: 700;
    color: #1A1A1A;
    line-height: 1.32;
    margin: 0;
}

/* Meta tags row */
.meta-tags { display: flex; gap: 7px; flex-wrap: wrap; margin: 10px 0 16px 0; }

.meta-tag {
    background: #F0EDE3;
    border: 1px solid #D5CFBF;
    border-radius: 3px;
    font-family: 'Inter', sans-serif;
    font-size: 10px;
    font-weight: 600;
    color: #5A5040;
    padding: 3px 9px;
    letter-spacing: 0.07em;
    text-transform: uppercase;
}

/* Divider */
.content-rule {
    border: none;
    border-top: 1.5px solid #EAE6DC;
    margin: 14px 0 22px 0;
}

/* ── SUMMARY BODY TYPOGRAPHY ──────────────────────────────────── */
/* Target Streamlit's rendered markdown elements directly */
.viewer-panel [data-testid="stMarkdownContainer"] h1,
.viewer-panel [data-testid="stMarkdownContainer"] h2,
.viewer-panel [data-testid="stMarkdownContainer"] h3,
.viewer-panel [data-testid="stMarkdownContainer"] h4 {
    font-family: 'Playfair Display', Georgia, serif !important;
    color: #1A1A1A !important;
    margin-top: 1.3em !important;
    margin-bottom: 0.35em !important;
}

.viewer-panel [data-testid="stMarkdownContainer"] h2 { font-size: 18px !important; }
.viewer-panel [data-testid="stMarkdownContainer"] h3 { font-size: 15.5px !important; }
.viewer-panel [data-testid="stMarkdownContainer"] h4 { font-size: 14px !important; font-style: italic; }

.viewer-panel [data-testid="stMarkdownContainer"] p,
.viewer-panel [data-testid="stMarkdownContainer"] li {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    color: #2C2416 !important;
    line-height: 1.78 !important;
}

.viewer-panel [data-testid="stMarkdownContainer"] strong {
    color: #1A1A1A !important;
    font-weight: 600 !important;
}

.viewer-panel [data-testid="stMarkdownContainer"] ul,
.viewer-panel [data-testid="stMarkdownContainer"] ol {
    padding-left: 1.4em !important;
    margin-bottom: 0.75em !important;
}

/* Also catch the generic .stMarkdown class for older Streamlit versions */
.viewer-panel .stMarkdown h1,
.viewer-panel .stMarkdown h2,
.viewer-panel .stMarkdown h3,
.viewer-panel .stMarkdown h4 {
    font-family: 'Playfair Display', Georgia, serif !important;
    color: #1A1A1A !important;
}

.viewer-panel .stMarkdown p,
.viewer-panel .stMarkdown li {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    color: #2C2416 !important;
    line-height: 1.78 !important;
}

/* ── DOI LINK BUTTON ──────────────────────────────────────────── */
.stLinkButton a {
    background-color: #1A1A1A !important;
    color: #F4F1E8 !important;
    border: 1px solid #1A1A1A !important;
    border-radius: 4px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    padding: 7px 14px !important;
    text-decoration: none !important;
    white-space: nowrap !important;
    display: inline-block !important;
}

.stLinkButton a:hover {
    background-color: #C8B88A !important;
    border-color: #C8B88A !important;
    color: #1A1A1A !important;
}

/* ── EMPTY STATE ──────────────────────────────────────────────── */
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 58vh;
    text-align: center;
}

.empty-icon { font-size: 44px; opacity: 0.3; margin-bottom: 14px; }

.empty-title {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 19px;
    font-weight: 600;
    color: #5A5040;
    margin-bottom: 6px;
}

.empty-sub {
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    color: #8A8070;
}

/* ── HIDE STREAMLIT CHROME ────────────────────────────────────── */
#MainMenu  { visibility: hidden; }
footer     { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

/* ── LABEL OVERRIDES ──────────────────────────────────────────── */
label[data-testid="stWidgetLabel"] p,
.stTextInput label,
.stSelectbox label {
    font-family: 'Inter', sans-serif !important;
    font-size: 9.5px !important;
    font-weight: 600 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    color: #7A7060 !important;
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

# ── 1. NAVBAR (renders at absolute top — no sticky needed since header is hidden) ──
st.markdown(f"""
<div class="top-nav">
    <div class="nav-logo">hack<span class="dot">.</span>CCM &nbsp;|&nbsp; Knowledge Portal</div>
    <div class="nav-links">
        <a href="{FEEDBACK_FORM_URL}"    class="nav-link"         target="_blank">Feedback</a>
        <a href="{SUBSCRIBE_FORM_URL}"   class="nav-link primary" target="_blank">Subscribe</a>
        <a href="{UNSUBSCRIBE_FORM_URL}" class="nav-link"         target="_blank">Unsubscribe</a>
    </div>
</div>
<div class="nav-rule"></div>
""", unsafe_allow_html=True)

df = get_data()

# ── 2. MAIN LAYOUT: 33% | 66% ──────────────────────────────────────
col_filter, col_view = st.columns([1, 2], gap="large")


# ── LEFT PANEL ─────────────────────────────────────────────────────
with col_filter:
    st.markdown('<div class="filter-panel">', unsafe_allow_html=True)

    # Search
    st.markdown('<span class="section-label">Search</span>', unsafe_allow_html=True)
    search_query = st.text_input("search", placeholder="Search articles...", label_visibility="collapsed")

    # Subject
    st.markdown('<span class="section-label" style="margin-top:16px;display:block;">Subject</span>', unsafe_allow_html=True)
    systems = ["All"] + (sorted(df["System"].dropna().unique().tolist()) if not df.empty and "System" in df.columns else [])
    sel_sys = st.selectbox("subject", systems, label_visibility="collapsed")

    # Article type
    st.markdown('<span class="section-label" style="margin-top:14px;display:block;">Article Type</span>', unsafe_allow_html=True)
    types = ["All"] + (sorted(df["Type of Article"].dropna().unique().tolist()) if not df.empty and "Type of Article" in df.columns else [])
    sel_type = st.selectbox("type", types, label_visibility="collapsed", key="type_select")

    # Filter logic
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
        f'<span class="section-label" style="margin-top:20px;display:block;">'
        f'Articles <span class="article-count-badge">{count}</span></span>',
        unsafe_allow_html=True
    )

    # Article list
    st.markdown('<div class="article-scroll">', unsafe_allow_html=True)
    if filtered_df.empty:
        st.markdown(
            '<p style="font-size:12.5px;color:#8A8070;text-align:center;padding:20px 0;">No articles match your filters.</p>',
            unsafe_allow_html=True
        )
    else:
        for _, row in filtered_df.iterrows():
            if st.button(row["Paper/Guideline Name"], key=row["File Name"], use_container_width=True):
                st.session_state.selected_file = row["File Name"]
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # /filter-panel


# ── RIGHT PANEL ─────────────────────────────────────────────────────
with col_view:
    selected_file = st.session_state.get("selected_file")

    st.markdown('<div class="viewer-panel">', unsafe_allow_html=True)

    if selected_file and not df.empty:
        row_match = df[df["File Name"] == selected_file]
        if not row_match.empty:
            row = row_match.iloc[0]

            # Title + DOI button in same row
            title_col, doi_col = st.columns([4, 1], gap="small")

            with title_col:
                st.markdown(
                    f'<h1 class="article-title">{row["Paper/Guideline Name"]}</h1>',
                    unsafe_allow_html=True
                )

            with doi_col:
                doi_link = str(row.get("DOI", "")).strip()
                if doi_link and doi_link.lower() != "none" and doi_link.startswith("http"):
                    st.markdown("<div style='padding-top:4px;'>", unsafe_allow_html=True)
                    st.link_button("↗ View Paper", doi_link, use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)

            # Meta tags
            tags_html = ""
            for field in ["System", "Type of Article"]:
                val = str(row.get(field, "")).strip()
                if val and val.lower() not in ("nan", "none", ""):
                    tags_html += f'<span class="meta-tag">{val}</span>'
            if tags_html:
                st.markdown(f'<div class="meta-tags">{tags_html}</div>', unsafe_allow_html=True)

            st.markdown('<hr class="content-rule">', unsafe_allow_html=True)

            # Summary content
            json_path = os.path.join(OUTPUT_DIR, os.path.splitext(selected_file)[0] + ".json")
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                summary_md = content.get("clinical_summary_markdown", "No summary available.")
                st.markdown(summary_md)
            else:
                st.markdown(
                    '<p style="color:#8A8070;font-size:14px;font-style:italic;font-family:Inter,sans-serif;">Summary data pending upload.</p>',
                    unsafe_allow_html=True
                )
        else:
            st.session_state.selected_file = None

    # Empty state
    if not selected_file:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">📄</div>
            <div class="empty-title">Select an article to read</div>
            <div class="empty-sub">Use the filters on the left to browse the knowledge library.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # /viewer-panel
