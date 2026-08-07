"""
config.py - Central configuration for paths, models, and API keys.
Edit values here to change behavior across all scripts.
"""

import os
from dotenv import load_dotenv

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
load_dotenv(dotenv_path=os.path.join(_PROJECT_DIR, ".env"))

# =====================================================================
# DIRECTORY PATHS
# =====================================================================
PROJECT_DIR = _PROJECT_DIR
BASE_INPUT_DIR = os.path.join(PROJECT_DIR, "input_pdfs")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output_files")
QUARANTINE_BASE = os.path.join(PROJECT_DIR, "quarantine")

SUB_DIRS = {
    "articles": os.path.join(BASE_INPUT_DIR, "articles"),
    "guidelines": os.path.join(BASE_INPUT_DIR, "guidelines"),
    "other": os.path.join(BASE_INPUT_DIR, "other"),
}

# =====================================================================
# TRACKER FILES
# =====================================================================
EXCEL_TRACKER_FILE = os.path.join(PROJECT_DIR, "sent_summaries.xlsx")
JSON_TRACKER_FILE = os.path.join(PROJECT_DIR, "sent_summaries.json")
REMOVED_TRACKER_FILE = os.path.join(PROJECT_DIR, "sent_summaries_removed.json")
PEARLS_JSON = os.path.join(PROJECT_DIR, "pearls.json")
PEARLS_TRACKER = os.path.join(PROJECT_DIR, "pearls_processed.xlsx")
SPECIALTIES_FILE = os.path.join(PROJECT_DIR, "specialties.txt")
ARTICLE_TYPES_FILE = os.path.join(PROJECT_DIR, "article_types.txt")
ERROR_LOG_FILE = os.path.join(PROJECT_DIR, "error_logs.txt")
FORMAT_LOG_FILE = os.path.join(PROJECT_DIR, "format_updates_log.txt")

# =====================================================================
# SUBTOPIC FILES
# =====================================================================
PENDING_SUBTOPICS_FILE = os.path.join(PROJECT_DIR, "pending_subtopics.json")
SUBTOPIC_MAPPING_FILE = os.path.join(PROJECT_DIR, "subtopic_mapping.json")

# =====================================================================
# ERROR LIST - Monthly rotation
# Format: master_error_list_YYYY-MM.txt
# =====================================================================
def get_error_list_path(year=None, month=None):
    """Return path to the error list for given year/month (defaults to current month)."""
    from datetime import datetime
    if year is None or month is None:
        now = datetime.now()
        year = now.year
        month = now.month
    return os.path.join(PROJECT_DIR, f"master_error_list_{year:04d}-{month:02d}.txt")


def get_all_error_list_paths():
    """Return all existing monthly error list files, sorted by name (newest first)."""
    import glob
    pattern = os.path.join(PROJECT_DIR, "master_error_list_*.txt")
    return sorted(glob.glob(pattern), reverse=True)


# =====================================================================
# API KEYS (loaded from .env)
# =====================================================================
PRIMARY_GEMINI_API_KEY = os.getenv("PRIMARY_GEMINI_API_KEY")
BACKUP_GEMINI_API_KEY = os.getenv("BACKUP_GEMINI_API_KEY")
CONDENSATION_GEMINI_API_KEY = os.getenv("CONDENSATION_GEMINI_API_KEY")


# =====================================================================
# PROVIDERS - OpenRouter + Gemini only (Together/DeepSeek removed)
# --llm openrouter | gemini picks the model set for BOTH passes.
# =====================================================================

# --- Pass 1: Summary extraction models ---
OPENROUTER_SUMMARY_MODEL = os.getenv("OPENROUTER_SUMMARY_MODEL", "deepseek-ai/DeepSeek-V4-Pro")
OPENROUTER_SUMMARY_FALLBACK = os.getenv("OPENROUTER_SUMMARY_FALLBACK", "") or OPENROUTER_SUMMARY_MODEL
GEMINI_SUMMARY_MODEL = os.getenv("GEMINI_SUMMARY_MODEL", "gemini-3.6-flash")

# --- Pass 2: Pearl extraction models ---
OPENROUTER_PEARLS_MODEL = os.getenv("OPENROUTER_PEARLS_MODEL", "openai/gpt-oss-20b")
OPENROUTER_PEARLS_FALLBACK = os.getenv("OPENROUTER_PEARLS_FALLBACK", "openai/gpt-oss-120b")
GEMINI_PEARLS_MODEL = os.getenv("GEMINI_PEARLS_MODEL", "gemini-3.6-flash")

# =====================================================================
# OCR / VISION MODELS
# =====================================================================
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-2.0-flash")

# =====================================================================
# EXTRACTION PARAMETERS
# =====================================================================
TEMPERATURE_EXTRACTION = 0.3
TEMPERATURE_PEARLS = 0.2
MAX_TOKENS_EXTRACTION = 16384
MAX_TOKENS_PEARLS = 8192
MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds
CHUNK_SIZE = 400000  # chars per chunk (~100K tokens)
CHUNK_OVERLAP = 3000  # chars of overlap

# =====================================================================
# WATCHER LOOP
# =====================================================================
POLL_INTERVAL = 5  # seconds between polling cycles
FILE_STABILITY_WAIT = 1.5  # seconds to wait for file size to stabilize

# =====================================================================
# PEARL JSON FIELDS
# =====================================================================
# =====================================================================
# FLASHCARD PATHS
# =====================================================================
FLASHCARDS_DIR = os.path.join(OUTPUT_DIR, "flashcards")           # unified store: {System}/{Subtopic}.json
FLASHCARDS_INPUT_DIR = os.path.join(PROJECT_DIR, "flashcards_input")  # ONLY input: md = authored deck, other = raw material
FLASHCARDS_LEDGER_FILE = os.path.join(PROJECT_DIR, "flashcards_ledger.json")
FLASHCARDS_INDEX_FILE = os.path.join(OUTPUT_DIR, "flashcards_index.json")   # derived master index
THEORY_MDS_DIR = os.path.join(OUTPUT_DIR, "Theory MDs")                     # theory notes rendered by portal
THEORY_PROCESSED_DIR = os.getenv("THEORY_PROCESSED_DIR", "C:/RONAK/AI Projects/ACUMEN/THEORY/processed")  # theory notes for flashcards.py theory

# THEORY folder abbreviations -> canonical subtopic-vocab system(s)
# (used by flashcards.py tagging; composite dirs get union vocab)
THEORY_SPEC_TO_CANONICAL = {
    "CVS": ["Cardiology"],
    "RS": ["Pulmonology"],
    "Neuro": ["Neurology"],
    "Renal and Acid Base": ["Nephrology"],
    "Liver GIT Nutrition": ["Gastroenterology", "Hepatology", "Nutrition"],
    "Infectious Diseases": ["Infectious Diseases"],
    "Hematology Rheumatology Oncology": ["Hematology", "Rheumatology", "Oncology"],
    "Endocrine Miscellaneous": ["Endocrinology", "Other"],
    "Pregnancy Trauma": ["Obstetrics and Gynecology", "Trauma"],
    "Scoring Systems": ["Multisystem", "Other"],
    "Toxicology": ["Toxicology"],
    "Sepsis": ["Sepsis"],
}

CHUNK_FLASHCARD = 30000  # chars per LLM convert call
MAX_CARDS_PER_DECK = 25

# =====================================================================
# OPENROUTER CONFIG
# =====================================================================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
# General-purpose OpenRouter model used by flashcards etc. (same as Pass 1 summary model)
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "") or OPENROUTER_SUMMARY_MODEL
TEMPERATURE_FLASHCARDS = 0.2
MAX_TOKENS_FLASHCARDS = 8192

# Dedicated flashcard-processing LLM (convert/tag/regenerate) — a cheap model so
# the flashcard layer never burns the high-end default. Override in .env:
#   FLASHCARD_LLM_MODEL="..."  FLASHCARD_LLM_API_KEY="..."  FLASHCARD_LLM_BASE_URL="..."
FLASHCARD_LLM_MODEL = os.getenv("FLASHCARD_LLM_MODEL") or OPENROUTER_MODEL
FLASHCARD_LLM_API_KEY = os.getenv("FLASHCARD_LLM_API_KEY") or OPENROUTER_API_KEY
FLASHCARD_LLM_BASE_URL = os.getenv("FLASHCARD_LLM_BASE_URL") or OPENROUTER_BASE_URL

# Flashcard front-question generator — deliberately a DIFFERENT provider/model
# than every other pipeline. Override via .env:
#   QUESTION_LLM_MODEL="..."  QUESTION_LLM_API_KEY="..."  QUESTION_LLM_BASE_URL="..."
# Defaults to the flashcard model so a single cheap FLASHCARD_LLM_MODEL covers
# convert/tag/fronts unless a dedicated question model is set.
QUESTION_LLM_MODEL = os.getenv("QUESTION_LLM_MODEL") or FLASHCARD_LLM_MODEL
QUESTION_LLM_API_KEY = os.getenv("QUESTION_LLM_API_KEY") or OPENROUTER_API_KEY
QUESTION_LLM_BASE_URL = os.getenv("QUESTION_LLM_BASE_URL") or OPENROUTER_BASE_URL
TEMPERATURE_QUESTION = 0.2
MAX_TOKENS_QUESTION = 256

# =====================================================================
# TRIAL CONDENSATION
# =====================================================================
CONDENSED_TRIALS_DIR = os.path.join(PROJECT_DIR, "output_files", "trials_database_condensed")
CONDENSATION_PROGRESS_FILE = os.path.join(PROJECT_DIR, "trial_condensation_progress.json")
CONDENSATION_PROMPT_FILE = os.path.join(PROJECT_DIR, "trial_condensation_prompt.md")
TRIALS_DATABASE_DIR = os.path.join(PROJECT_DIR, "trials_database")
TEMPERATURE_CONDENSATION = 0.1
MAX_TOKENS_CONDENSATION = 16384

SYSTEM_TO_SPECIALTY = {
    "Neuro": "Neurology",
    "Circulatory": "Cardiology",
    "Resuscitation": "Multisystem",
    "Airway": "Pulmonology",
    "Respiratory": "Pulmonology",
    "Gastrointestinal": "Gastroenterology",
    "Nutrition": "Nutrition",
    "Liver": "Hepatology",
    "Renal": "Nephrology",
    "Haematology": "Hematology",
    "Sepsis": "Sepsis",
    "Trauma": "Trauma",
    "Endocrine": "Endocrinology",
    "Miscellaneous": "Other",
}

# Model aliases for condense_trials.py --model flag
CONDENSATION_MODELS = {
    "deepseek": os.getenv("CONDENSATION_DEEPSEEK_MODEL", "") or OPENROUTER_SUMMARY_MODEL,  # OpenRouter
    "tencent": os.getenv("CONDENSATION_TENCENT_MODEL", "tencent/hy3:free"),               # OpenRouter
    "gemini": os.getenv("GEMINI_CONDENSATION_MODEL", "gemini-3.6-flash"),                 # Gemini API
}

GEMINI_CONDENSATION_MODEL = os.getenv("GEMINI_CONDENSATION_MODEL", "gemini-3.6-flash")
CONDENSATION_TENCENT_MODEL = os.getenv("CONDENSATION_TENCENT_MODEL", "tencent/hy3:free")

# Subtopic assignment/classification model (subtopic_mapper.py + bulk_subtopic_classifier.py)
SUBTOPIC_LLM_MODEL = os.getenv("SUBTOPIC_LLM_MODEL", "openai/gpt-oss-20b")

PEARLS_JSON_FIELDS = [
    "id", "timestamp", "source_paper", "doi",
    "author", "system", "type", "pearl", "remarks", "file_name", "topic", "subtopic"
]

# =====================================================================
# EXCEL HEADERS
# =====================================================================
EXCEL_HEADERS = [
    "Serial Number", "File Name", "Paper/Guideline Name", "Primary Authors",
    "Journal Name", "DOI", "Year", "System", "Type of Article", "MD Generated",
    "Email Pushed", "Summary Saved Date", "Email Pushed Date", "Parsing Notes", "show_on_web"
]
