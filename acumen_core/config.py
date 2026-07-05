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
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
PRIMARY_GEMINI_API_KEY = os.getenv("PRIMARY_GEMINI_API_KEY")
BACKUP_GEMINI_API_KEY = os.getenv("BACKUP_GEMINI_API_KEY")


# =====================================================================
# EXTRACTION MODELS - Main schema extraction (Pass 1)
# =====================================================================
MODEL_TOGETHER_PRO = "deepseek-ai/DeepSeek-V4-Pro"
MODEL_TOGETHER_FLASH = "deepseek-ai/DeepSeek-V4-Pro"
MODEL_DEEPSEEK_DIRECT = "deepseek-v4-pro"
MODEL_GEMINI_ARTICLES = "gemini-2.5-flash"
MODEL_GEMINI_GUIDELINES = "gemini-2.5-pro"
MODEL_GEMINI_BACKUP = "gemini-2.5-flash"

# =====================================================================
# PEARL EXTRACTION MODELS - Pass 2 (separate call)
# =====================================================================
MODEL_PEARL_PRIMARY = "openai/gpt-oss-20b"
MODEL_PEARL_FALLBACK = "openai/gpt-oss-120b"

# =====================================================================
# OCR / VISION MODELS
# =====================================================================
MODEL_VISION = "gemini-2.0-flash"

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
PEARLS_JSON_FIELDS = [
    "id", "timestamp", "source_paper", "doi",
    "author", "system", "type", "pearl", "remarks", "file_name", "topic"
]

# =====================================================================
# EXCEL HEADERS
# =====================================================================
EXCEL_HEADERS = [
    "Serial Number", "File Name", "Paper/Guideline Name", "Primary Authors",
    "Journal Name", "DOI", "Year", "System", "Type of Article", "MD Generated",
    "Email Pushed", "Summary Saved Date", "Email Pushed Date", "Parsing Notes", "show_on_web"
]
