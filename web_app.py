
import os
import json
import pandas as pd
import streamlit as st

FEEDBACK_FORM_URL = "https://docs.google.com/forms/d/1b5uifsDa73u42tlfKK3RGto_hLiwT-TtotQwov0O0b4"
SUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/1s1UE1gHsTBOirAPW4beST3DS6D_ra-whkndTq5iIOHQ"
UNSUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/1uv_Xwymc8RFhsvK5L0oV9Rc16jdP0xRTrDW7zv_P5A0"

OUTPUT_DIR = "./output_files"
EXCEL_TRACKER_FILE = "./sent_summaries.xlsx"

st.set_page_config(
    page_title="hack.CCM | Knowledge Portal",
    page_icon="📚",
    layout="wide"
)

st.markdown('''
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@300;400;500;600&display=swap');

html,body,.stApp{
background:#F4F1E8;
color:#1A1A1A;
font-family:'Inter',sans-serif;
}

[data-testid="stSidebar"]{
background:#EDEADF;
border-right:1px solid #D5CFBF;
}

h1,h2,h3,h4,p,span,div,label{
color:#1A1A1A;
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
font-family:'Playfair Display',serif;
font-size:30px;
font-weight:700;
color:#F4F1E8;
}

.btnrow{
display:flex;
gap:10px;
}

.btnrow a{
background:#C8B88A;
color:#111111 !important;
padding:8px 16px;
border-radius:8px;
text-decoration:none;
font-weight:600;
}

.card{
background:white;
padding:2rem;
border-radius:14px;
border:1px solid #D5CFBF;
}

.badge{
display:inline-block;
padding:5px 12px;
margin-right:8px;
background:#F0EDE3;
border-radius:999px;
font-size:12px;
font-weight:600;
}

.section{
margin-top:24px;
padding-top:12px;
border-top:1px solid #ECE7DA;
}

.sidebar-title{
font-weight:700;
margin-top:10px;
margin-bottom:10px;
}

</style>
''', unsafe_allow_html=True)

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
