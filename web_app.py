
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
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@300;400;500;600&display=swap');

html,body,.stApp{
background:#F4F1E8;
font-family:Inter,sans-serif;
}

[data-testid="stSidebar"]{
background:#EDEADF;
}

h1,h2,h3{
font-family:'Playfair Display',serif;
color:#1A1A1A;
}

.main-card{
background:white;
padding:2rem;
border-radius:12px;
border:1px solid #D5CFBF;
}

.tag{
display:inline-block;
background:#F0EDE3;
padding:4px 10px;
margin-right:6px;
border-radius:5px;
font-size:12px;
font-weight:600;
}

.small{
color:#6A6255;
font-size:12px;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def get_data():
    if not os.path.exists(EXCEL_TRACKER_FILE):
        return pd.DataFrame()

    df = pd.read_excel(EXCEL_TRACKER_FILE, sheet_name="Registry Logs")
    df.columns = df.columns.str.strip()

    return df[df["show_on_web"].astype(str).str.lower() == "yes"]


df = get_data()

st.title("hack.CCM | Knowledge Portal")

with st.sidebar:
    st.header("Search")

    query = st.text_input("Search article")

    systems = ["All"]
    if not df.empty:
        systems += sorted(df["System"].dropna().unique())

    system = st.selectbox("Subject", systems)

    types = ["All"]
    if not df.empty:
        types += sorted(df["Type of Article"].dropna().unique())

    article_type = st.selectbox("Article type", types)

filtered = df.copy()

if not filtered.empty:

    if system != "All":
        filtered = filtered[filtered["System"] == system]

    if article_type != "All":
        filtered = filtered[filtered["Type of Article"] == article_type]

    if query:
        filtered = filtered[filtered["Paper/Guideline Name"].str.contains(query, case=False, na=False)]

article = None

with st.sidebar:
    st.markdown("---")
    names = filtered["Paper/Guideline Name"].tolist() if not filtered.empty else []

    if names:
        article = st.radio("Articles", names)

if article:

    row = filtered[filtered["Paper/Guideline Name"] == article].iloc[0]

    st.markdown('<div class="main-card">', unsafe_allow_html=True)

    st.markdown(f"# {row['Paper/Guideline Name']}")

    st.markdown(
        f'<span class="tag">{row["System"]}</span>'
        f'<span class="tag">{row["Type of Article"]}</span>',
        unsafe_allow_html=True
    )

    doi = str(row.get("DOI", "")).strip()

    if doi.startswith("http"):
        st.link_button("View Paper", doi)

    st.divider()

    json_path = os.path.join(
        OUTPUT_DIR,
        os.path.splitext(row["File Name"])[0] + ".json"
    )

    if os.path.exists(json_path):
        with open(json_path, encoding="utf-8") as f:
            content = json.load(f)

        st.markdown(content.get("clinical_summary_markdown", ""))

    else:
        st.info("Summary not available")

    st.markdown("</div>", unsafe_allow_html=True)

else:
    st.info("Select an article from the sidebar.")
