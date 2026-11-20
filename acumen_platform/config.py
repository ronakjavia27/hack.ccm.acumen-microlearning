"""Central config for the v2 learning platform.

Everything a product decision touches (subjects, tiers, quotas, paths) lives
here so changing the paywall or adding a subject is a one-file edit.
"""
from __future__ import annotations

import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIR = os.path.join(ROOT, "output_files")

# ---- Feature switch -------------------------------------------------------
# Off on Vercel unless PLATFORM_V2=1; on locally unless PLATFORM_V2=0.
_ON_VERCEL = os.environ.get("VERCEL", "").strip() == "1"
_FLAG = os.environ.get("PLATFORM_V2", "").strip().lower()
PLATFORM_ENABLED = _FLAG in ("1", "true", "yes") or (not _ON_VERCEL and _FLAG not in ("0", "false", "no"))

# Seed demo questions/videos/modules so the skeleton is clickable before
# real content exists. Off in production by default.
USE_SAMPLE_DATA = os.environ.get("PLATFORM_SAMPLE_DATA", "" if _ON_VERCEL else "1").strip().lower() in ("1", "true", "yes")

API_PREFIX = "/api/v2"
KV_PREFIX = "v2"

# ---- Content locations (all optional; empty dirs = no content yet) --------
QUESTION_BANK_DIR = os.path.join(OUTPUT_DIR, "question_bank")      # {Subject}/*.json  (list of questions)
THEORY_MODULES_DIR = os.path.join(OUTPUT_DIR, "theory_modules")    # {Subject}/*.json  (one module per file)
VIDEO_CATALOG_PATH = os.path.join(OUTPUT_DIR, "videos", "catalog.json")
FLASHCARD_STORE_DIR = os.path.join(OUTPUT_DIR, "flashcards")      # existing unified store
SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_data")

# ---- Subjects --------------------------------------------------------------
# A subject is the top-level learning track. `systems` maps onto the existing
# organ-system vocabulary (acumen_core/subtopics.json keys), so all existing
# papers/pearls/flashcards slot into a subject without re-tagging.
SUBJECTS = {
    "medicine": {
        "label": "Medicine",
        "systems": ["Cardiology", "Pulmonology", "Nephrology", "Neurology", "Gastroenterology",
                    "Hepatology", "Hematology", "Endocrinology", "Rheumatology", "Immunology",
                    "Oncology", "Infectious Diseases", "Nutrition", "Multisystem"],
    },
    "microbiology": {
        "label": "Microbiology",
        # Organism-centric; borrows the ID vocab until a micro-specific one exists.
        "systems": ["Infectious Diseases", "Sepsis", "Immunology"],
        "axes": ["Bacteriology", "Virology", "Mycology", "Parasitology", "Immunology",
                 "Antimicrobials", "Lab Diagnosis", "Infection Control"],
    },
    "ccm": {
        "label": "Critical Care Medicine",
        "systems": ["Sepsis", "Pulmonology", "Cardiology", "Nephrology", "Neurology", "Trauma",
                    "Toxicology", "Hematology", "Nutrition", "Multisystem", "Surgery",
                    "Obstetrics And Gynecology", "Infectious Diseases"],
    },
}

# ---- Tiers & quotas --------------------------------------------------------
# None = unlimited, True/False = capability, int = quota per period in the key name.
# Prices are intentionally unset: pricing is a business decision, not code.
TIERS = {
    "free": {
        "label": "Free",
        "price_inr_month": 0,
        "limits": {
            "srs_reviews_per_day": None,          # the habit loop stays free
            "personalised_exams_per_week": 2,
            "exam_max_questions": 20,
            "written_ai_grading_per_month": 0,
            "doubt_posts_per_month": 3,
            "doubt_ai_answer": False,
            "video_pro_library": False,
            "live_exams_pro": False,             # free-tier live events still joinable
            "proctored_exams": False,
            "voice_minutes_per_month": 0,
            "theory_pro_modules": False,
            "push_email": "weekly",
            "push_whatsapp": False,
        },
    },
    "pro": {
        "label": "Pro",
        "price_inr_month": None,
        "limits": {
            "srs_reviews_per_day": None,
            "personalised_exams_per_week": None,
            "exam_max_questions": 200,
            "written_ai_grading_per_month": 100,
            "doubt_posts_per_month": 30,
            "doubt_ai_answer": True,
            "video_pro_library": True,
            "live_exams_pro": True,
            "proctored_exams": True,
            "voice_minutes_per_month": 60,
            "theory_pro_modules": True,
            "push_email": "daily",
            "push_whatsapp": True,
        },
    },
    "institution": {
        "label": "Institution",
        "price_inr_month": None,
        "limits": {
            "srs_reviews_per_day": None,
            "personalised_exams_per_week": None,
            "exam_max_questions": 300,
            "written_ai_grading_per_month": 500,
            "doubt_posts_per_month": None,
            "doubt_ai_answer": True,
            "video_pro_library": True,
            "live_exams_pro": True,
            "proctored_exams": True,
            "voice_minutes_per_month": 300,
            "theory_pro_modules": True,
            "push_email": "daily",
            "push_whatsapp": True,
            "cohort_admin": True,                # create cohort exams, see reports
        },
    },
}
DEFAULT_TIER = "free"

# ---- Notifications ---------------------------------------------------------
CRON_SECRET = os.environ.get("CRON_SECRET", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")              # Meta Cloud API
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_DIGEST_TEMPLATE = os.environ.get("WHATSAPP_DIGEST_TEMPLATE", "daily_digest")

# ---- Voice / realtime ------------------------------------------------------
STT_PROVIDER = os.environ.get("STT_PROVIDER", "")          # e.g. whisper | deepgram
TTS_PROVIDER = os.environ.get("TTS_PROVIDER", "")          # e.g. openai | elevenlabs
REALTIME_SERVICE_URL = os.environ.get("REALTIME_SERVICE_URL", "")  # separate websocket service (live exams, viva)

# ---- Billing ---------------------------------------------------------------
BILLING_PROVIDER = os.environ.get("BILLING_PROVIDER", "")  # razorpay | stripe
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
