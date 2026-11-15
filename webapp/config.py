"""Constants for the portal: content paths, form links, disclaimer texts and colour maps."""
from pathlib import Path

WEBAPP_DIR = Path(__file__).resolve().parent


FEEDBACK_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSd6xRmmimmVc0Sv4AeNls-oxLR6k_zX8D_QERFZwPP6zlfjRw/viewform?usp=header"
SUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSffsrF8DPWaTa-03XisMqSU5Da_8QdE-JrINdDP5iRmvWAI8Q/viewform?usp=header"
UNSUBSCRIBE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScz864mkLh5AqBYVzAh573hWu98NdmwwPC2vaU1lfBE3WHHHg/viewform?usp=header"


DISCLAIMER_TEXT = """**Welcome to hack.CCM \U0001F9A9 — Please Read Before You Explore**

Welcome! This platform is a hobby passion project designed to make critical care education more structured, accessible, and easily retainable.

To help you get the most out of your study sessions, we use AI to condense massive volumes of medical text, guidelines, and open-source research papers into highly readable summaries. However, before you dive in, please note the following:

**\u26A0\uFE0F For Education, Not Consultation**
This is a tool for knowledge enhancement and personal study only. It is not a clinical decision-making tool. Always rely on official guidelines and your own institutional protocols for real-world patient care.

**\U0001F916 The AI Factor**
As the saying goes, "To err is human; to hallucinate is AI." While we have taken immense care to review the data and eliminate errors, AI-assisted formatting isn't always flawless.

**\U0001F6D1 Use Responsibly**
Double-check critical values and protocols. You are the clinician; this is just your study buddy.

**\U0001F50D Spotted a Discrepancy?**
If you find any errors, outdated data, or weird AI quirks, please help us improve! Report it via our Feedback button below.

The ultimate aim here is to format large information into quick, retainable reads. This does not replace the need to study original papers or guidelines in full detail. Adequate emphasis and credit have been given to the original authors and journals wherever possible—I claim no personal ownership over this data.

By clicking "Proceed" below, you acknowledge that you understand this tool's educational purpose and agree to use it responsibly."""
OUTPUT_DIR = "./output_files"
JSON_TRACKER_FILE = "./sent_summaries.json"
PEARLS_JSON = "./pearls.json"
ESBICM_INDEX_PATH = "./output_files/esbicm_trials/esbicm_trials_index.json"
CONDENSED_TRIALS_DIR = "./output_files/trials_database_condensed"


CREDITS_TEXT = """**Editor(s)**

**Dr. Ankur Gupta**, MBBS, EDIC, FCCCM, AFIC, PGDID, FICM, PGDMLE
Consultant Intensivist, Apollo Hospitals, Indore, INDIA
Founder President, Educational Society of Bedside Intensive Care Medicine (ESBICM)

**Dr. Pranay Bajpai**, MD (Medicine), FCCS, IDCC, MBA (HA)
Assistant Professor, Department of Medicine
MGM Medical College & M.Y. Group of Hospitals, Indore, INDIA
Consultant, Critical Care & Respiratory Medicine, Apollo Hospitals, Indore

**Co-Editor**

**Dr. Sonal Kaushika**, MBBS, FCCCM, AFIC
Associate Consultant, Critical Care
Shalby Hospital, Ahmedabad, Gujarat, INDIA

**A project by:**
Academic Committee of ESBICM (ACE)

**Contributors**

**Dr. Nikhilesh Jain**, DNB (Med), MRCPI, IDCCM, FCCCM, PGDHM, FIECMO
Director and Operational Head, Department of Critical Care Services
Care CHL Hospital, Indore

**Dr. Vivek Joshi**, DA, IDCCM, FCCCM, MBA (HA)
Medical Superintendent and Head, Critical Care
Shalby Hospital, Indore

**Dr. Vivek Baxi**, MD, FCCCM, AFIC, PGCDM
Head, Department of Critical Care Medicine
Consultant Intensivist and Physician
Shalby Hospitals (Naroda), Ahmedabad, Gujarat

**Dr. Prerna Bedi Lakhotia**, MBBS, DNB (Anesthesia), IDCCM, FGID
Consultant Intensivist
Apollo Hospitals, Indore

**Dr. Benjamin Baby Johnson**, MBBS, AFIC, PGDMLE
Consultant, Critical Care & ICU In-charge
Sankeshwar Mission Hospital

**Dr. Abhi Paliwal**, MBBS, DNB (Family Medicine), AFIC
Associate Consultant, Critical Care
Apollo Hospitals, Indore"""


TRIAL_DISCLAIMER_TEXT = """**Legal Disclaimer**

**Educational Purpose Only**
This website provides summaries of published clinical trials for informational and educational purposes only. It is not a substitute for professional medical advice, diagnosis, or treatment.

**No Warranties & Evolving Information**
Medical knowledge changes rapidly. While we aim for accuracy, the authors and publishers make no express or implied warranties regarding the completeness, accuracy, or currency of this content. We assume no liability for errors, omissions, or clinical outcomes resulting from the use of this data.

**Professional Duty**
Practitioners must exercise independent clinical judgment. Always consult original trial publications and manufacturer guidelines to verify dosages, contraindications, and administration methods before treating patients."""


ESBICM_SPEC_COLORS = {
    "Airway & Procedures": "#8B5CF6",
    "ARDS & Mechanical Ventilation": "#0EA5E9",
    "Cardiac Arrest & Post-Resuscitation Care": "#EF4444",
    "Cardiovascular Critical Care": "#C6554B",
    "General ICU & Miscellaneous": "#6B7280",
    "Hematology & Transfusion": "#E11D48",
    "Infection & Antibiotic Stewardship": "#10B981",
    "Neurological Critical Care": "#6B5B95",
    "Nutrition, GI & Glycemic Control": "#84CC16",
    "Renal & Electrolytes (AKI, RRT)": "#D97706",
    "Sedation, Analgesia & Delirium": "#F97316",
    "Sepsis & Septic Shock": "#DC2626",
    "Trauma, Hemorrhage, Coagulopathy & VTE": "#9333EA",
}


ECG_SVG = '''<svg width="0" height="0" style="position:absolute">
  <symbol id="ecg" viewBox="0 0 260 14">
    <path d="M0 7 L95 7 L104 1 L112 13 L120 3 L128 7 L260 7"/>
  </symbol>
</svg>'''


SPEC_COLORS = {
    "Cardiology": "#C6554B", "Pulmonology": "#3A7CA5", "Infectious Diseases": "#4F8A6D",
    "Neurology": "#6B5B95", "Nephrology": "#B08D57", "Gastroenterology": "#10B981",
    "Hematology": "#E11D48", "Hepatology": "#14B8A6", "Immunology": "#A855F7",
    "Sepsis": "#F97316", "Trauma": "#DC2626", "Endocrinology": "#06B6D4",
    "General": "#6B7280", "Multisystem": "#6366F1",
    "Nutrition": "#84CC16", "Obstetrics and Gynecology": "#D946EF", "Rheumatology": "#0EA5E9",
    "Toxicology": "#7C3AED", "Oncology": "#059669", "Surgery": "#D97706",
    "Cardiothoracic": "#C6554B", "Vascular": "#0891B2", "Other": "#9333EA",
}
