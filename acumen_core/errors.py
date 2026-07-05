"""
errors.py - Centralized error logging to monthly master_error_list files.
Format: JSONL (one JSON object per line).
"""

import os
import json
from datetime import datetime

from acumen_core.config import get_error_list_path, get_all_error_list_paths

# =====================================================================
# ERROR TYPES & PRIORITIES
# =====================================================================
ERROR_PRIORITIES = {
    "QUOTA_EXHAUSTED": "CRITICAL",
    "RATE_LIMIT": "CRITICAL",
    "API_KEY_MISSING": "CRITICAL",
    "MODEL_NOT_FOUND": "HIGH",
    "API_TIMEOUT": "MEDIUM",
    "SERVICE_UNAVAILABLE": "MEDIUM",
    "EMPTY_RESPONSE": "MEDIUM",
    "JSON_PARSE_ERROR": "HIGH",
    "SCHEMA_VIOLATION": "MEDIUM",
    "TEXT_EXTRACTION_FAILED": "HIGH",
    "OCR_FAILED": "LOW",
    "FILE_LOCKED": "LOW",
    "VALIDATION_ERROR": "MEDIUM",
    "UNKNOWN": "LOW",
}


def classify_error(error):
    """Classify an exception into an error_type string."""
    msg = str(error).lower()
    if "quota" in msg or "resource_exhausted" in msg or "429" in msg:
        return "QUOTA_EXHAUSTED"
    if "rate limit" in msg:
        return "RATE_LIMIT"
    if "api key" in msg or "api_key" in msg or "unauthorized" in msg or "401" in msg:
        return "API_KEY_MISSING"
    if "not found" in msg or "404" in msg or "model" in msg and "not" in msg:
        return "MODEL_NOT_FOUND"
    if "timeout" in msg or "timed out" in msg:
        return "API_TIMEOUT"
    if "503" in msg or "502" in msg or "service unavailable" in msg or "internal server" in msg or "500" in msg:
        return "SERVICE_UNAVAILABLE"
    if "empty response" in msg or "no content" in msg:
        return "EMPTY_RESPONSE"
    if "json" in msg and ("decode" in msg or "parse" in msg):
        return "JSON_PARSE_ERROR"
    if "too short" in msg or "unreadable" in msg or "extract" in msg:
        return "TEXT_EXTRACTION_FAILED"
    if "ocr" in msg:
        return "OCR_FAILED"
    if "permission" in msg or "locked" in msg:
        return "FILE_LOCKED"
    if "schema" in msg or "validation" in msg:
        return "VALIDATION_ERROR"
    return "UNKNOWN"


def get_priority(error_type):
    """Return priority level for an error_type."""
    return ERROR_PRIORITIES.get(error_type, "LOW")


def write_error(
    file_name,
    stage,
    error,
    pass_number=1,
    provider=None,
    model=None,
    retry_count=0,
    action=None,
    extra_fields=None,
):
    """
    Write one error entry to current month's master_error_list_YYYY-MM.txt.

    Args:
        file_name: PDF/JSON file being processed
        stage: 'extraction' | 'pearl_extraction' | 'validation' | 'reconcile' | 'sync'
        error: Exception object or error string
        pass_number: 1 (schema) or 2 (pearls)
        provider: 'together' | 'deepseek' | 'gemini'
        model: model ID string
        retry_count: number of retries attempted
        action: 'retry' | 'fallback' | 'quarantine' | 'auto_fix' | 'log_only'
        extra_fields: dict of additional context
    """
    error_type = classify_error(error) if isinstance(error, Exception) else (
        classify_error(Exception(error)) if isinstance(error, str) else "UNKNOWN"
    )
    priority = get_priority(error_type)

    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "file": file_name,
        "stage": stage,
        "pass": pass_number,
        "error_type": error_type,
        "priority": priority,
        "message": str(error)[:500],
        "provider": provider or "",
        "model": model or "",
        "retry_count": retry_count,
        "action": action or "log_only",
    }

    if extra_fields:
        entry.update(extra_fields)

    error_path = get_error_list_path()
    try:
        with open(error_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"  WARNING: Failed to write to error list: {e}")


def read_errors_from_file(file_path):
    """Read all error entries from a specific error list file."""
    entries = []
    if not os.path.exists(file_path):
        return entries
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return entries


def read_current_month_errors():
    """Read all errors from the current month's error list."""
    return read_errors_from_file(get_error_list_path())


def read_all_errors():
    """Read all errors from all monthly error list files (newest first)."""
    all_errors = []
    for path in get_all_error_list_paths():
        all_errors.extend(read_errors_from_file(path))
    return all_errors
