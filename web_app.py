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

st.set_page_config(page_title="hack.CCM | Knowledge Portal", layout="wide")

OUTPUT_DIR         = "./output_files"
EXCEL_TRACKER_FILE = "./sent_summaries.xlsx"

# =====================================================================
# 🎨 CSS — global selectors only, no scoping inside div wrappers
# =====================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');

/* ── KILL DEFAULT STREAMLIT SHELL ─────────────────────────────── */
[data-testid="stHeader"]        { display: none !important; }
[data-testid="stToolbar"]       { display: none !important; }
[data-testid="stDecoration"]    { display: none !important; }
#MainMenu                        { visibility: hidden !important; }
footer                           { visibility: hidden !important; }

/* ── BASE ─────────────────────────────────────────────────────── */
html, body, .stApp {
    background-color: #F4F1E8 !important;
    font-family: 'Inter', sans-serif !important;
}

.block-container {
    padding: 0 1.5rem 2rem 1.5rem !important;
    max-width: 100% !important;
}

/* ── NAV BAR ──────────────────────────────────────────────────── */
.top-nav {
    background: #1A1A1A;
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 56px;
    padding: 0 2rem;
    margin: 0 -1.5rem 0 -1.5rem;
}
.nav-logo {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 18px;
    font-weight: 700;
    color: #F4F1E8 !important;
    letter-spacing: 0.03em;
}
.nav-logo .dot { color: #C8B88A !important; }
.nav-links { display: flex; gap: 6px; }
.nav-link {
    color: #B0A898 !important;
    text-decoration: none !important;
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 6px 14px;
    border: 1px solid transparent;
    border-radius: 3px;
}
.nav-link:hover { color: #F4F1E8 !important; border-color: #C8B88A; }
.nav-link.primary { background: #C8B88A; color: #1A1A1A !important; border-color: #C8B88A; }
.nav-link.primary:hover { background: #B8A87A; }

.gold-rule {
    height: 2px;
    background: linear-gradient(to right, #C8B88A, #EDE8D8, #C8B88A);
    margin: 0 -1.5rem 1.2rem -1.5rem;
}

/* ── COLUMN CONTAINERS — style via Streamlit's column wrappers ── */
/* Left column: beige panel */
[data-testid="stHorizontalBlock"] > div:first-child > [data-testid="stVerticalBlock"] {
    background-color: #EDEADF;
    border: 1px solid #D5CFBF;
    border-radius: 6px;
    padding: 20px 16px 24px 16px;
    min-height: 85vh;
}

/* Right column: white panel */
[data-testid="stHorizontalBlock"] > div:last-child > [data-testid="stVerticalBlock"] {
    background-color: #FFFFFF;
    border: 1px solid #D5CFBF;
    border-radius: 6px;
    padding: 28px 32px 32px 32px;
    min-height: 85vh;
    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

/* ── SECTION LABELS ───────────────────────────────────────────── */
.section-label {
    font-family: 'Inter', sans-serif;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #7A7060 !important;
    display: block;
    padding-bottom: 5px;
    border-bottom: 1px solid #CEC8B5;
    margin-bottom: 8px;
    margin-top: 0;
}

.badge {
    background: #C8B88A;
    color: #1A1A1A !important;
    font-size: 9.5px;
    font-weight: 700;
    padding: 1px 7px;
    border-radius: 10px;
    margin-left: 5px;
    vertical-align: middle;
    display: inline-block;
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
}
.stButton > button:hover {
    background-color: #C8B88A !important;
    border-color: #B8A87A !important;
    color: #1A1A1A !important;
}

/* ── TEXT INPUTS ──────────────────────────────────────────────── */
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
.stTextInput label, .stSelectbox label,
label[data-testid="stWidgetLabel"] p {
    font-size: 9px !important;
    font-weight: 700 !important;
    letter-spacing: 0.16em !important;
    text-transform: uppercase !important;
    color: #7A7060 !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── SELECT BOX ───────────────────────────────────────────────── */
.stSelectbox > div > div {
    background-color: #FFFFFF !important;
    border: 1px solid #CEC8B5 !important;
    border-radius: 4px !important;
    font-size: 13px !important;
    color: #1A1A1A !important;
}

/* ── ARTICLE TITLE IN VIEWER ──────────────────────────────────── */
.article-title {
    font-family: 'Playfair Display', Georgia, serif !important;
    font-size: 21px !important;
    font-weight: 700 !important;
    color: #1A1A1A !important;
    line-height: 1.3 !important;
    margin: 0 0 10px 0 !important;
}

/* ── META TAGS ────────────────────────────────────────────────── */
.meta-tags  { display: flex; gap: 7px; flex-wrap: wrap; margin: 0 0 14px 0; }
.meta-tag {
    background: #F0EDE3;
    border: 1px solid #D5CFBF;
    border-radius: 3px;
    font-family: 'Inter', sans-serif;
    font-size: 9.5px;
    font-weight: 700;
    color: #5A5040 !important;
    padding: 3px 9px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* ── DIVIDER ──────────────────────────────────────────────────── */
.content-rule { border: none; border-top: 1.5px solid #EAE6DC; margin: 0 0 20px 0; }

/* ── SUMMARY TEXT — GLOBAL, no scoping ───────────────────────── */
/* These rules apply to ALL markdown in the app, which is fine   */
/* since left panel has no markdown prose content                 */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    color: #2C2416 !important;
    line-height: 1.78 !important;
}

[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4 {
    font-family: 'Playfair Display', Georgia, serif !important;
    color: #1A1A1A !important;
    line-height: 1.3 !important;
    margin-top: 1.2em !important;
    margin-bottom: 0.3em !important;
}
[data-testid="stMarkdownContainer"] h2 { font-size: 17px !important; }
[data-testid="stMarkdownContainer"] h3 { font-size: 15px !important; }

[data-testid="stMarkdownContainer"] strong { color: #1A1A1A !important; font-weight: 600 !important; }
[data-testid="stMarkdownContainer"] ul,
[data-testid="stMarkdownContainer"] ol { padding-left: 1.4em !important; margin-bottom: 0.7em !important; }

/* ── DOI BUTTON ───────────────────────────────────────────────── */
.stLinkButton a {
    background-color: #1A1A1A !important;
    color: #F4F1E8 !important;
    border: 1px solid #1A1A1A !important;
    border-radius: 4px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 10.5px !important;
    font-weight: 600 !important;
    letter-spacing: 0.09em !important;
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
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; height: 55vh; text-align: center;
}
.empty-icon   { font-size: 42px; opacity: 0.28; margin-bottom: 14px; }
.empty-title  { font-family: 'Playfair Display', Georgia, serif; font-size: 18px; font-weight: 600; color: #5A5040 !important; margin-bottom: 6px; }
.empty-sub    { font-family: 'Inter', sans-serif; font-size: 13px; color: #8A8070 !important; }

/* ── SCROLLBAR ────────────────────────────────────────────────── */
::-webkit-scrollbar         { width: 4px; }
::-webkit-scrollbar-track   { background: #E8E4D8; }
::-webkit-scrollbar-thumb   { background: #C8B88A; border-radius: 2px; }

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
# 🖥️ UI — NAV FIRST, then columns
# =====================================================================

# ── NAVBAR ────────────────────────────────────────────────────────
st.markdown(f"""
<div class="top-nav">
  <div class="nav-logo">hack<span class="dot">.</span>CCM &nbsp;|&nbsp; Knowledge Portal</div>
  <div class="nav-links">
    <a href="{FEEDBACK_FORM_URL}"    class="nav-link"         target="_blank">Feedback</a>
    <a href="{SUBSCRIBE_FORM_URL}"   class="nav-link primary" target="_blank">Subscribe</a>
    <a href="{UNSUBSCRIBE_FORM_URL}" class="nav-link"         target="_blank">Unsubscribe</a>
  </div>
</div>
<div class="gold-rule"></div>
""", unsafe_allow_html=True)

df = get_data()

# ── TWO COLUMNS ───────────────────────────────────────────────────
col_left, col_right = st.columns([1, 2], gap="medium")


# ════════════════════════════════════════════════════════════════════
# LEFT COLUMN — filters live directly in the column, no HTML wrapper
# ════════════════════════════════════════════════════════════════════
with col_left:

    st.markdown('<span class="section-label">Search</span>', unsafe_allow_html=True)
    search_query = st.text_input("__search__", placeholder="Search articles...", label_visibility="collapsed")

    st.markdown('<span class="section-label" style="margin-top:14px;">Subject</span>', unsafe_allow_html=True)
    systems = ["All"] + (
        sorted(df["System"].dropna().unique().tolist())
        if not df.empty and "System" in df.columns else []
    )
    sel_sys = st.selectbox("__subject__", systems, label_visibility="collapsed")

    st.markdown('<span class="section-label" style="margin-top:12px;">Article Type</span>', unsafe_allow_html=True)
    types = ["All"] + (
        sorted(df["Type of Article"].dropna().unique().tolist())
        if not df.empty and "Type of Article" in df.columns else []
    )
    sel_type = st.selectbox("__type__", types, label_visibility="collapsed", key="type_sel")

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
        f'<span class="section-label" style="margin-top:16px;">'
        f'Articles <span class="badge">{count}</span></span>',
        unsafe_allow_html=True
    )

    if filtered_df.empty:
        st.markdown(
            '<p style="font-size:12px;color:#8A8070;text-align:center;padding:16px 0 0 0;">'
            'No articles match your filters.</p>',
            unsafe_allow_html=True
        )
    else:
        for _, row in filtered_df.iterrows():
            if st.button(row["Paper/Guideline Name"], key=row["File Name"], use_container_width=True):
                st.session_state.selected_file = row["File Name"]


# ════════════════════════════════════════════════════════════════════
# RIGHT COLUMN — article viewer
# ════════════════════════════════════════════════════════════════════
with col_right:
    selected_file = st.session_state.get("selected_file")

    if selected_file and not df.empty:
        row_match = df[df["File Name"] == selected_file]

        if not row_match.empty:
            row = row_match.iloc[0]

            # Title + DOI button
            t_col, d_col = st.columns([4, 1], gap="small")
            with t_col:
                st.markdown(
                    f'<h1 class="article-title">{row["Paper/Guideline Name"]}</h1>',
                    unsafe_allow_html=True
                )
            with d_col:
                doi_link = str(row.get("DOI", "")).strip()
                if doi_link and doi_link.lower() not in ("none", "nan", "") and doi_link.startswith("http"):
                    st.markdown("<div style='padding-top:2px;'>", unsafe_allow_html=True)
                    st.link_button("↗ View Paper", doi_link, use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)

            # Meta tags
            tags_html = "".join(
                f'<span class="meta-tag">{str(row.get(f, "")).strip()}</span>'
                for f in ["System", "Type of Article"]
                if str(row.get(f, "")).strip().lower() not in ("nan", "none", "")
            )
            if tags_html:
                st.markdown(f'<div class="meta-tags">{tags_html}</div>', unsafe_allow_html=True)

            st.markdown('<hr class="content-rule">', unsafe_allow_html=True)

            # Summary
            json_path = os.path.join(OUTPUT_DIR, os.path.splitext(selected_file)[0] + ".json")
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                st.markdown(content.get("clinical_summary_markdown", "No summary available."))
            else:
                st.markdown(
                    "*Summary data pending upload.*",
                )

        else:
            st.session_state.selected_file = None

    else:
        # Empty state
        st.markdown("""
        <div class="empty-state">
          <div class="empty-icon">📄</div>
          <div class="empty-title">Select an article to read</div>
          <div class="empty-sub">Use the filters on the left to browse the knowledge library.</div>
        </div>
        """, unsafe_allow_html=True)
