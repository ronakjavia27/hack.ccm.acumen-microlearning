
# V4 CSS patch for hack.CCM portal
# Fixes:
# - White selectboxes with black text
# - White dropdown menus
# - White DOI/View Paper button with black text
# - Consistent light theme

import os
import json
import pandas as pd
import streamlit as st

FEEDBACK_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSd6xRmmimmVc0Sv4AeNls-oxLR6k_zX8D_QERFZwPP6zlfjRw/viewform?usp=header"
SUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSffsrF8DPWaTa-03XisMqSU5Da_8QdE-JrINdDP5iRmvWAI8Q/viewform?usp=header"
UNSUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScz864mkLh5AqBYVzAh573hWu98NdmwwPC2vaU1lfBE3WHHHg/viewform?usp=header"

OUTPUT_DIR="./output_files"
EXCEL_TRACKER_FILE="./sent_summaries.xlsx"

st.set_page_config(page_title="hack.CCM | Knowledge Portal", page_icon="📚", layout="wide")

st.markdown('''
<style>
html, body, .stApp{
    background:#F4F1E8;
    color:#1A1A1A;
}

[data-testid="stSidebar"]{
    background:#EDEADF;
    border-right:1px solid #D5CFBF;
}

/* SELECTBOX FIX */
.stSelectbox div[data-baseweb="select"] > div{
    background:white !important;
    color:#1A1A1A !important;
    border:1px solid #D5CFBF !important;
}

.stSelectbox *{
    color:#1A1A1A !important;
}

/* TEXT INPUT FIX */
.stTextInput input{
    background:white !important;
    color:#1A1A1A !important;
}

/* DROPDOWN MENU FIX */
div[role="listbox"]{
    background:white !important;
}

div[role="option"]{
    background:white !important;
    color:#1A1A1A !important;
}

/* BUTTON FIX */
.stLinkButton a{
    background:white !important;
    color:#1A1A1A !important;
    border:1px solid #D5CFBF !important;
    border-radius:10px !important;
}

.stLinkButton a:hover{
    background:#F5F5F5 !important;
}

.topbar{
display:flex;
justify-content:space-between;
align-items:center;
padding:14px 22px;
background:#111111;
border-radius:12px;
margin-bottom:20px;
}

.logo{
font-size:30px;
font-weight:700;
color:white;
}

.btnrow a{
background:#C8B88A;
padding:8px 14px;
margin-left:8px;
border-radius:8px;
text-decoration:none;
color:#111 !important;
font-weight:600;
}

.badge{
display:inline-block;
padding:5px 12px;
background:#F0EDE3;
border-radius:999px;
margin-right:8px;
font-weight:600;
}
            
            /* ----- GLOBAL TEXT ----- */
body,
p,
span,
div,
label {
    color: #1A1A1A !important;
}

/* ----- SIDEBAR TEXT ----- */
[data-testid="stSidebar"] * {
    color: #1A1A1A !important;
}

/* ----- RADIO BUTTON LABELS (article names) ----- */
div[role="radiogroup"] label,
div[role="radiogroup"] span,
div[role="radiogroup"] p {
    color: #1A1A1A !important;
}

/* ----- WIDGET LABELS ----- */
label[data-testid="stWidgetLabel"],
label[data-testid="stWidgetLabel"] p {
    color: #1A1A1A !important;
    font-weight: 600;
}

/* ----- SIDEBAR HEADERS ----- */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4 {
    color: #1A1A1A !important;
}

/* ----- MARKDOWN TEXT ----- */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] li {
    color: #1A1A1A !important;
}

/* ----- ARTICLE COUNTER ----- */
[data-testid="stSidebar"] strong {
    color: #1A1A1A !important;
}
</style>
''', unsafe_allow_html=True)

st.markdown("<h1>hack.CCM presents ACUMEN</h1>", unsafe_allow_html=True)


@st.cache_data
def load_data():
    if not os.path.exists(EXCEL_TRACKER_FILE):
        return pd.DataFrame()
    df = pd.read_excel(EXCEL_TRACKER_FILE, sheet_name="Registry Logs")
    df.columns = df.columns.str.strip()
    return df[df["show_on_web"].astype(str).str.lower() == "yes"]

df = load_data()

st.markdown(f'''
<div class="topbar">
<div class="logo">hack.CCM | Knowledge Portal</div>
<div class="btnrow">
<a href="{FEEDBACK_FORM_URL}" target="_blank">Feedback</a>
<a href="{SUBSCRIBE_FORM_URL}" target="_blank">Subscribe</a>
<a href="{UNSUBSCRIBE_FORM_URL}" target="_blank">Unsubscribe</a>
</div>
</div>
''', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Search & Filters")

    search = st.text_input("Search")

    systems = ["All"]
    types = ["All"]

    if not df.empty:
        systems += sorted(df["System"].dropna().unique())
        types += sorted(df["Type of Article"].dropna().unique())

    system = st.selectbox("Subject", systems)
    article_type = st.selectbox("Article Type", types)

filtered = df.copy()

if not filtered.empty:

    if system != "All":
        filtered = filtered[filtered["System"] == system]

    if article_type != "All":
        filtered = filtered[filtered["Type of Article"] == article_type]

    if search:
        filtered = filtered[
            filtered["Paper/Guideline Name"]
            .str.contains(search, case=False, na=False)
        ]

selected = None

with st.sidebar:
    st.markdown(f"### Articles ({len(filtered)})")

    if not filtered.empty:
        selected = st.radio(
            "",
            filtered["Paper/Guideline Name"].tolist(),
            label_visibility="collapsed"
        )

if not selected:
    st.info("Select an article from the sidebar.")
    st.stop()

row = filtered[filtered["Paper/Guideline Name"] == selected].iloc[0]

st.markdown('<div class="card">', unsafe_allow_html=True)

st.markdown(f"# {row['Paper/Guideline Name']}")

st.markdown(
    f'''
    <span class="badge">{row.get("System","")}</span>
    <span class="badge">{row.get("Type of Article","")}</span>
    ''',
    unsafe_allow_html=True
)

doi = str(row.get("DOI","")).strip()

if doi.startswith("http"):
    st.link_button("📄 View Original Paper", doi)

json_path = os.path.join(
    OUTPUT_DIR,
    os.path.splitext(row["File Name"])[0] + ".json"
)

st.markdown('<div class="section">', unsafe_allow_html=True)
st.markdown("## 📋 Core Summary")

if os.path.exists(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        content = json.load(f)

    st.markdown(content.get("clinical_summary_markdown",""))
else:
    st.warning("Summary file not found")

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
