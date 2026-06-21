import os
import json
import re
import pandas as pd
import streamlit as st

# --- CONFIGURATION ---
FEEDBACK_FORM_URL = "#"
SUBSCRIBE_FORM_URL = "#"
UNSUBSCRIBE_FORM_URL = "#"
OUTPUT_DIR = "./output_files"
EXCEL_TRACKER_FILE = "./sent_summaries.xlsx"

st.set_page_config(page_title="hack.CCM | Knowledge Portal", page_icon="🧠", layout="wide")

# --- AESTHETIC CSS REVAMP ---
st.markdown("""
    <style>
    .stApp { background-color: #FDFBF7 !important; color: #1F2937; }
    h1, h2, h3 { color: #111827 !important; font-family: 'Inter', sans-serif !important; }
    
    /* Top Utility Bar */
    .utility-bar { padding: 10px; background: #FFF; border-radius: 8px; border: 1px solid #E5E7EB; margin-bottom: 20px; }
    
    /* Article Card */
    .card { background: #FFFFFF; padding: 25px; border-radius: 12px; border: 1px solid #E5E7EB; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    
    /* Buttons */
    div.stButton > button { border-radius: 6px; background-color: #1D4ED8; color: white; border: none; }
    
    /* Filter Section */
    .filter-box { background: #F3F4F6; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- APP LOGIC ---
def load_data():
    if not os.path.exists(EXCEL_TRACKER_FILE): return []
    df = pd.read_excel(EXCEL_TRACKER_FILE, sheet_name="Registry Logs")
    df.columns = df.columns.str.strip()
    return df[df["show_on_web"].astype(str).str.lower() == "yes"].to_dict(orient="records")

# --- UI RENDER ---
st.markdown('<div class="utility-bar" style="display:flex; justify-content:space-between;">'
            '<strong>🧠 hack.CCM Portal</strong>'
            f'<div><a href="{FEEDBACK_FORM_URL}">Feedback</a> | <a href="{SUBSCRIBE_FORM_URL}">Subscribe</a> | <a href="{UNSUBSCRIBE_FORM_URL}">Unsub</a></div>'
            '</div>', unsafe_allow_html=True)

data = load_data()
if data:
    st.markdown('<div class="filter-box">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    systems = ["All"] + sorted(list(set(d["System"] for d in data)))
    sel_sys = col1.selectbox("Select System", systems)
    search = col2.text_input("🔍 Search Summaries")
    st.markdown('</div>', unsafe_allow_html=True)

    # Filtered View
    filtered = [d for d in data if (sel_sys == "All" or d["System"] == sel_sys) and 
                (search.lower() in d["Paper/Guideline Name"].lower())]
    
    for item in filtered:
        with st.expander(f"📖 {item['Paper/Guideline Name']} ({item['System']})"):
            st.markdown('<div class="card">', unsafe_allow_html=True)
            # Load JSON content
            json_path = os.path.join(OUTPUT_DIR, os.path.splitext(item["File Name"])[0] + ".json")
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    content = json.load(f)
                    st.markdown(content.get("clinical_summary_markdown", "No summary available."))
            st.markdown('</div>', unsafe_allow_html=True)
else:
    st.warning("No summaries published yet.")