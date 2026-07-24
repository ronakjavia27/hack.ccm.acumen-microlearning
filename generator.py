#!/usr/bin/env python3
"""
generator.py - hack.CCM Unified Ingestion Pipeline
====================================================
Processes medical PDFs into structured JSON summaries + clinical pearls.

TWO PASSES (separate API calls for quality):
  PASS 1 - Full Schema Extraction (DeepSeek V4 Pro / fallback DeepSeek API)
           -> output_files/{system}/{type}/{filename}.json
  PASS 2 - Pearl Extraction (openai/gpt-oss-20b -> fallback gpt-oss-120b)
           -> pearls.json

MODES:
  --mode watch           Watch input folder for new PDFs, run both passes (default)
  --mode summary         Only run Pass 1 (extract summaries). Skip pearls entirely
  --mode pearls          Only run Pass 2 on files with summary but no pearls yet
  --mode summary_pearls  Run Pass 1 on pending PDFs, then Pass 2 on all files
                         missing pearls (new + existing)

MODIFIERS:
  --ocr                  Enable OCR fallback for scanned PDFs + figure transcription
  --max N                Process at most N files (0 = unlimited)
  --once                 Process current queue once then exit (no loop)
  --dry-run              Preview what would be processed, no API calls
  --verbose              Detailed per-file logging
  --status               Show quick dashboard: pending PDFs, missing pearls, errors
  --reprocess FILE.pdf   Force re-process a single specific PDF file
  --extract-pearls X.json  Run Pass 2 only on one specific existing JSON

ERRORS:
  All errors are logged to master_error_list_YYYY-MM.txt (monthly rotation).
  maintainer.py reads these to prioritize repairs.

EXAMPLES:
  python generator.py                                   # watch mode, openrouter (default)
  python generator.py --mode summary                    # only summaries, no pearls
  python generator.py --mode pearls                     # only pearls for pending files
  python generator.py --mode summary_pearls             # both, sequential
  python generator.py --mode summary --ocr              # summaries with OCR
  python generator.py --mode pearls --max 20            # cap at 20 pearls files
  python generator.py --mode summary_pearls --once      # both passes, no loop
  python generator.py --status                          # quick dashboard
  python generator.py --reprocess input_pdfs/articles/paper.pdf
  python generator.py --extract-pearls output_files/Cardiology/Review/paper.json
"""

import os
import sys
import time
import json
import shutil
import argparse
from datetime import datetime
from pypdf import PdfReader

from acumen_core.config import (
    BASE_INPUT_DIR, SUB_DIRS, OUTPUT_DIR, QUARANTINE_BASE,
    EXCEL_TRACKER_FILE, JSON_TRACKER_FILE, PEARLS_JSON, PEARLS_TRACKER,
    PEARLS_JSON_FIELDS, PROJECT_DIR,
    OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL,
    get_error_list_path,
)
from acumen_core.vocabulary import (
    get_allowed_specialties, get_allowed_types,
    build_specialty_map, normalize_specialty, normalize_type,
)
from acumen_core.tracking import (
    initialize_excel_tracker, log_transaction_to_excel, log_transaction_to_json,
    load_processed_files_from_json, load_all_entries_from_json,
    load_pearl_tracker, update_pearl_tracker,
    save_json_atomic, load_json_safe,
)
from acumen_core.markdown import enrich_payload_with_markdown
from acumen_core.errors import write_error, read_current_month_errors
from acumen_core.llm import (
    execute_with_fallback, execute_with_gemini, execute_with_custom,
    execute_pearl_extraction, chunk_text,
    merge_chunks_programmatically,
)
from acumen_core.schema import EXTRACTION_SYSTEM_PROMPT
from acumen_core.ocr import fallback_page_ocr, extract_figure_text

# Fix stdout encoding for Unicode
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


# =====================================================================
# CONFIGURATION - Edit these for easy changes
# =====================================================================

# --- Operation modes ---
DEFAULT_MODE = "watch"                # watch | summary | pearls | summary_pearls
# In summary_pearls mode, run Pass 2 immediately after Pass 1 (vs in a second phase):
RUN_PASS_2_IMMEDIATELY = True
# In pearls mode: skip files that already have pearls in pearls.json
SKIP_FILES_WITH_PEARLS = True
# In pearls mode: also re-try files where pearl extraction previously failed
INCLUDE_PREVIOUSLY_FAILED = True

# --- Watch directories (keys must match SUB_DIRS in config.py) ---
CATEGORIES = ["articles", "guidelines", "other"]

# --- Processing behavior ---
POLL_INTERVAL = 5                     # seconds between polling cycles (watch mode)
FILE_STABILITY_WAIT = 1.5             # seconds to wait for file size to stabilize
MIN_TEXT_LENGTH = 150                 # minimum chars to consider text extractable

# --- Chunking (large PDFs) ---
CHUNK_SIZE_OVERRIDE = None             # None = use config default (400000)
CHUNK_OVERLAP_OVERRIDE = None          # None = use config default (3000)

# --- OCR ---
OCR_ENABLED_DEFAULT = False           # default OCR state (can override with --ocr)
OCR_MIN_CHARS = 150                    # trigger page OCR if PyPDF returns < this

# --- Quarantine ---
QUARANTINE_AFTER_PROCESS = True        # move PDFs to quarantine after success
QUARANTINE_AFTER_FAILURE = False        # move PDFs to error quarantine after failure

# --- Error handling ---
MAX_RETRIES_OVERRIDE = None            # None = use config default (3)
RETRY_DELAY_OVERRIDE = None            # None = use config default (10s)

# --- Pearl extraction ---
PEARLS_ENABLED = True                  # master toggle for Pass 2
PEARLS_MAX_PER_FILE = 25               # maximum pearls to save per file

# --- Audit log ---
GENERATOR_LOG_FILE = os.path.join(PROJECT_DIR, "generator.log")


# =====================================================================
# AUDIT LOG - append one line per run for tracking
# =====================================================================
def append_to_log(message):
    """Append a timestamped line to generator.log."""
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(GENERATOR_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
    except Exception:
        pass


# =====================================================================
# INITIALIZATION
# =====================================================================
def initialize_system():
    """Create all required directories and trackers."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for folder_path in SUB_DIRS.values():
        os.makedirs(folder_path, exist_ok=True)
    os.makedirs(QUARANTINE_BASE, exist_ok=True)
    initialize_excel_tracker()

    allowed_specs = get_allowed_specialties()
    allowed_types = get_allowed_types()
    print(f"  Specialties: {len(allowed_specs)} loaded")
    print(f"  Article Types: {len(allowed_types)} loaded")
    return allowed_specs, allowed_types


# =====================================================================
# PASS 1 - FULL SCHEMA EXTRACTION
# =====================================================================
def extract_text_from_pdf(file_path, ocr_enabled=False):
    """Extract text from PDF with optional OCR fallback."""
    print("  Reading PDF...")
    reader = PdfReader(file_path)
    chunks = [page.extract_text() or "" for page in reader.pages]
    full_text = "\n".join(chunks).strip()

    if ocr_enabled and len(full_text) < OCR_MIN_CHARS:
        print(f"  PyPDF returned only {len(full_text)} chars, trying page-level OCR...")
        full_text = fallback_page_ocr(file_path)
        print(f"  OCR extracted {len(full_text)} chars")

    if ocr_enabled:
        print("  Extracting embedded figures...")
        figure_text = extract_figure_text(file_path)
        if figure_text:
            print(f"  Found {len(figure_text)} chars from figures/flowcharts")
            full_text += f"\n\n--- FIGURE AND FLOWCHART TRANSCRIPTIONS ---\n{figure_text}"

    return full_text


def run_extraction_pass(file_path, category, ocr_enabled=False,
                        llm_choice="together", custom_key="", custom_model=""):
    """PASS 1: Extract structured JSON from PDF. Returns (payload, error)."""
    file_name = os.path.basename(file_path)
    try:
        full_text = extract_text_from_pdf(file_path, ocr_enabled)

        if len(full_text) < MIN_TEXT_LENGTH:
            error_msg = f"Extracted text too short ({len(full_text)} chars) or unreadable"
            write_error(file_name=file_name, stage="extraction", pass_number=1,
                        error=error_msg, action="log_only",
                        extra_fields={"text_chars": len(full_text)})
            return None, error_msg

        text_chunks = chunk_text(full_text, CHUNK_SIZE_OVERRIDE, CHUNK_OVERLAP_OVERRIDE)

        def _call_llm(system, user, cat):
            if llm_choice == "gemini":
                return execute_with_gemini(
                    system, user, cat,
                    max_retries=MAX_RETRIES_OVERRIDE, retry_delay=RETRY_DELAY_OVERRIDE,
                )
            elif llm_choice in ("openrouter", "other"):
                base_url = "https://openrouter.ai/api/v1" if llm_choice == "openrouter" else None
                return execute_with_custom(
                    custom_key, custom_model, system, user,
                    base_url=base_url,
                    max_retries=MAX_RETRIES_OVERRIDE, retry_delay=RETRY_DELAY_OVERRIDE,
                )
            else:
                return execute_with_fallback(
                    system, user, cat,
                    max_retries=MAX_RETRIES_OVERRIDE, retry_delay=RETRY_DELAY_OVERRIDE,
                )

        if len(text_chunks) == 1:
            print(f"  Extracted {len(full_text)} chars, calling extraction model...")
            user_content = f"Extract and structure the following clinical document into JSON format. Return ONLY valid JSON following the schema from the system prompt:\n\n{full_text}"
            structured_payload = _call_llm(EXTRACTION_SYSTEM_PROMPT, user_content, category)
        else:
            print(f"  Document large ({len(full_text)} chars). Splitting into {len(text_chunks)} chunks...")
            chunk_results = []
            for i, chunk in enumerate(text_chunks):
                print(f"  Chunk {i + 1}/{len(text_chunks)} ({len(chunk)} chars)...")
                user_content = f"Extract and structure the following clinical document chunk into JSON format. Return ONLY valid JSON:\n\n{chunk}"
                chunk_result = _call_llm(EXTRACTION_SYSTEM_PROMPT, user_content, category)
                chunk_results.append(chunk_result)
            structured_payload = merge_chunks_programmatically(chunk_results)
            print(f"  Merged {len(chunk_results)} chunks into single JSON")

        return structured_payload, None

    except Exception as e:
        write_error(file_name=file_name, stage="extraction", pass_number=1,
                    error=e, action="log_only")
        return None, str(e)


def save_extracted_json(payload, file_name, output_dir=None):
    """Normalize, enrich, and save the extracted JSON to disk."""
    output_dir = output_dir or OUTPUT_DIR
    allowed_specs = get_allowed_specialties()
    allowed_types = get_allowed_types()

    spec_map = build_specialty_map(allowed_specs)
    clean_system = normalize_specialty(payload.get("specialty", []), spec_map)
    clean_type_raw = normalize_type(payload, allowed_types)
    clean_type = "".join(x for x in str(clean_type_raw) if x.isalnum() or x in "._- ").strip() or "Other"

    payload = enrich_payload_with_markdown(payload)

    # Set subtopic = system name as placeholder (to be refined later via subtopic_mapper)
    subtopic = clean_system
    payload["subtopic"] = subtopic

    sharded_output_dir = os.path.join(output_dir, clean_system, clean_type)
    os.makedirs(sharded_output_dir, exist_ok=True)
    base_name = os.path.splitext(file_name)[0]
    destination_json_path = os.path.join(sharded_output_dir, f"{base_name}.json")

    with open(destination_json_path, "w", encoding="utf-8") as jf:
        json.dump(payload, jf, indent=2, ensure_ascii=False)
    print(f"  Saved: {destination_json_path}")

    log_meta = dict(payload)
    log_meta["specialty"] = [clean_system]
    log_meta["system"] = clean_system
    return destination_json_path, log_meta, clean_system, clean_type, subtopic


# =====================================================================
# PASS 2 - PEARL EXTRACTION (separate API call)
# =====================================================================
def build_markdown_for_pearls(payload):
    """Build a condensed markdown string from the payload for pearl extraction."""
    lines = []
    title = payload.get("title", "")
    if title:
        lines.append(f"# {title}")

    one_line = payload.get("one_line_summary", "")
    if one_line:
        lines.append(f"\n## Summary\n{one_line}")

    for pearl in payload.get("key_pearls", []):
        lines.append(f"- {pearl}")

    for s in payload.get("sections", []):
        heading = s.get("heading", "")
        content = s.get("content", "")
        if heading:
            lines.append(f"\n## {heading}")
        if content:
            lines.append(content)
        for sp in s.get("section_pearls", []):
            if sp:
                lines.append(f"- {sp}")

    for b in payload.get("recommendation_blocks", []):
        topic = b.get("topic", "")
        narrative = b.get("narrative", "")
        if topic:
            lines.append(f"\n## {topic}")
        if narrative:
            lines.append(narrative)
        for r in b.get("recommendations", []):
            stmt = r.get("statement", "")
            if stmt:
                lines.append(f"- {stmt}")

    sl = payload.get("strengths_limitations", "")
    if sl:
        lines.append(f"\n## Strengths & Limitations\n{sl}")

    return "\n".join(lines)


def append_pearls_to_json(new_pearls, source_paper, metadata, file_name):
    """Append pearls to pearls.json atomically with sequential IDs."""
    existing_rows = load_json_safe(PEARLS_JSON, [])
    next_id = 1
    if existing_rows:
        all_ids = []
        for r in existing_rows:
            try:
                all_ids.append(int(r.get("id", 0)))
            except (ValueError, TypeError):
                pass
        next_id = (max(all_ids) + 1) if all_ids else 1

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows_to_add = []

    for p in new_pearls[:PEARLS_MAX_PER_FILE]:
        if isinstance(p, dict):
            text = p.get("text", "").strip()
            topic = p.get("topic", "").strip()
        elif isinstance(p, str):
            text = p.strip()
            topic = ""
        else:
            continue
        if len(text) < 15:
            continue
        rows_to_add.append({
            "id": str(next_id), "timestamp": now_ts,
            "source_paper": source_paper,
            "doi": metadata.get("doi", ""),
            "author": metadata.get("authors", metadata.get("primary_authors", "")),
            "system": metadata.get("system", ""),
            "type": metadata.get("type", metadata.get("article_subtype", "")),
            "subtopic": metadata.get("subtopic", metadata.get("system", "")),
            "pearl": text[:500], "remarks": "",
            "file_name": file_name, "topic": topic,
        })
        next_id += 1

    all_rows = existing_rows + rows_to_add
    save_json_atomic(PEARLS_JSON, all_rows)
    return len(rows_to_add)


def run_pearl_extraction_pass(payload, file_name, metadata):
    """PASS 2: Extract clinical pearls using separate cheaper model."""
    try:
        markdown_text = build_markdown_for_pearls(payload)
        if not markdown_text or len(markdown_text) < 50:
            print("  Pass 2: Skipping pearls (insufficient content)")
            return 0, None

        print(f"  Pass 2: Extracting pearls ({len(markdown_text)} chars)...")
        pearls = execute_pearl_extraction(markdown_text, file_name)

        if not pearls:
            print("  Pass 2: No pearls extracted")
            return 0, None

        source_paper = payload.get("title", payload.get("paper_name", file_name))
        count = append_pearls_to_json(pearls, source_paper, metadata, file_name)
        update_pearl_tracker(PEARLS_TRACKER, file_name, count, "generator")
        print(f"  Pass 2: {count} pearls saved to {PEARLS_JSON}")
        return count, None

    except Exception as e:
        write_error(file_name=file_name, stage="pearl_extraction", pass_number=2,
                    error=e, provider="together", action="log_only",
                    extra_fields={"pearl_model_primary": "openai/gpt-oss-20b"})
        return 0, str(e)


# =====================================================================
# SINGLE PDF PROCESSING
# =====================================================================
def process_single_pdf(file_path, category, processed_history, ocr_enabled=False,
                       verbose=False, run_pearls=True,
                       llm_choice="together", custom_key="", custom_model=""):
    """Process one PDF through Pass 1 (and optionally Pass 2)."""
    file_name = os.path.basename(file_path)
    if file_name in processed_history:
        if verbose:
            print(f"  SKIP (already processed): {file_name}")
        return False, 0, 0

    print(f"\n{'='*60}")
    print(f"  Ingesting [{category.upper()}]: {file_name}")
    print(f"{'='*60}")

    pass1_success = False
    pearls_added = 0

    # ----- PASS 1 -----
    payload, err1 = run_extraction_pass(file_path, category, ocr_enabled,
                                        llm_choice=llm_choice, custom_key=custom_key,
                                        custom_model=custom_model)
    if payload is None:
        print(f"  [X] Pass 1 failed: {err1}")
        if QUARANTINE_AFTER_FAILURE:
            move_to_quarantine(file_path, category, error=True)
        return False, 0, 0

    try:
        json_path, log_meta, clean_system, clean_type, subtopic = save_extracted_json(payload, file_name)
        log_transaction_to_excel(file_name, log_meta, "Success")
        log_transaction_to_json(file_name, log_meta, "Success", subtopic=subtopic)
        processed_history.add(file_name)
        pass1_success = True
        print(f"  Pass 1: OK (system={clean_system}, type={clean_type})")

        # Queue to pending_subtopics.json for later assignment
        from acumen_core.tracking import append_pending_subtopic
        paper_title = payload.get("title", payload.get("paper_name", file_name))
        append_pending_subtopic(
            title=paper_title,
            system=clean_system,
            type_val=clean_type,
            file_name=file_name,
        )
    except Exception as e:
        print(f"  [X] Failed to save/log Pass 1: {e}")
        write_error(file_name=file_name, stage="save", pass_number=1, error=e, action="log_only")
        return False, 0, 0

    # ----- PASS 2 (optional) -----
    pearl_err = None
    if run_pearls and PEARLS_ENABLED:
        pearls_added, pearl_err = run_pearl_extraction_pass(payload, file_name, log_meta)
        if pearl_err:
            print(f"  [!] Pass 2 (pearls) failed: {pearl_err} - summary still saved")
    else:
        if run_pearls and not PEARLS_ENABLED:
            print("  Pass 2: Skipped (PEARLS_ENABLED=False)")

    # ----- Quarantine source PDF -----
    if QUARANTINE_AFTER_PROCESS and pass1_success:
        move_to_quarantine(file_path, category, error=False)

    pass2_ok = (pearl_err is None) if (run_pearls and PEARLS_ENABLED) else True
    status = "SUCCESS" if (pass1_success and pass2_ok) else "PARTIAL"
    print(f"  [{status}] {file_name} - Pass1={'OK' if pass1_success else 'FAIL'}, "
          f"Pass2={'OK' if pass2_ok else 'SKIP' if not (run_pearls and PEARLS_ENABLED) else 'FAIL'}, "
          f"pearls={pearls_added}")
    return True, 1, pearls_added


def move_to_quarantine(file_path, category, error=False):
    """Move processed (or errored) PDF to quarantine folder."""
    try:
        processed_date = datetime.now().strftime("%Y-%m-%d")
        subfolder = "errors" if error else category
        dest_dir = os.path.join(QUARANTINE_BASE, processed_date, subfolder)
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, os.path.basename(file_path))
        shutil.move(file_path, dest_path)
        print(f"  Moved to quarantine: {dest_path}")
    except Exception as e:
        print(f"  Warning: could not move to quarantine: {e}")


# =====================================================================
# SCAN: Files with summaries but no pearls
# =====================================================================
def find_files_missing_pearls(verbose=False):
    """
    Scan output_files/ for JSON summaries that don't have pearls yet.
    Returns list of (json_path, file_name) tuples.
    """
    # Build set of file_names that already have pearls
    existing_pearls = load_json_safe(PEARLS_JSON, [])
    files_with_pearls = set(p.get("file_name", "") for p in existing_pearls if p.get("file_name"))

    # Also check the pearls_processed.xlsx tracker
    try:
        tracked = load_pearl_tracker(PEARLS_TRACKER)
        files_with_pearls.update(tracked)
    except Exception:
        pass

    # Scan output_files/
    missing = []
    if not os.path.exists(OUTPUT_DIR):
        return missing
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for fname in files:
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(root, fname)
            if SKIP_FILES_WITH_PEARLS and fname in files_with_pearls:
                if verbose:
                    print(f"    [has pearls] {fname}")
                continue
            missing.append((fpath, fname))

    return missing


# =====================================================================
# MODE: SUMMARY ONLY (Pass 1, no pearls)
# =====================================================================
def run_summary_mode(ocr_enabled=False, max_files=0, verbose=False, once=False, dry_run=False,
                     llm_choice="together", custom_key="", custom_model=""):
    """Run only Pass 1 (extraction). No pearls."""
    print(f"\n{'#'*60}")
    print(f"  hack.CCM Generator - SUMMARY MODE (Pass 1 only)")
    print(f"{'#'*60}")
    print(f"  Pearls: DISABLED for this run")
    print(f"  OCR: {'enabled' if ocr_enabled else 'disabled'}")
    print(f"  LLM: {llm_choice}{f' [{custom_model}]' if llm_choice in ('openrouter', 'other') else ''}")
    if max_files > 0:
        print(f"  Max files: {max_files}")
    print()

    if dry_run:
        _dry_run_preview()
        return

    initialize_system()
    history_log = load_processed_files_from_json()
    total_processed = 0
    total_pearls = 0
    start_time = datetime.now()

    try:
        loop_counter = 0
        while True:
            loop_counter += 1
            history_log = load_processed_files_from_json()

            if loop_counter % 12 == 1:
                print(f"  [Heartbeat] {datetime.now().strftime('%H:%M:%S')} | Processed: {total_processed}")

            for category in CATEGORIES:
                if max_files > 0 and total_processed >= max_files:
                    break
                folder_path = SUB_DIRS.get(category)
                if not folder_path or not os.path.exists(folder_path):
                    continue
                pdf_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]
                for file_name in pdf_files:
                    if max_files > 0 and total_processed >= max_files:
                        break
                    path = os.path.join(folder_path, file_name)
                    if file_name in history_log:
                        if verbose:
                            print(f"  SKIP (in history): {file_name}")
                        continue
                    try:
                        initial_size = os.path.getsize(path)
                        time.sleep(FILE_STABILITY_WAIT)
                        if os.path.getsize(path) != initial_size:
                            continue
                        processed, p1, p2 = process_single_pdf(
                            path, category, history_log, ocr_enabled, verbose,
                            run_pearls=False,
                            llm_choice=llm_choice, custom_key=custom_key, custom_model=custom_model,
                        )
                        if processed:
                            total_processed += 1
                    except Exception as e:
                        print(f"  [X] Error processing {file_name}: {e}")
                        write_error(file_name=file_name, stage="watcher", error=e, action="log_only")
                        continue

            if once:
                break
            if max_files > 0 and total_processed >= max_files:
                print(f"\n  Reached --max limit ({max_files}). Exiting.")
                break
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\n\n  Stopped by user.")

    elapsed = (datetime.now() - start_time).total_seconds()
    append_to_log(f"mode=summary ocr={ocr_enabled} files={total_processed} pearls=0 errors_logged elapsed={elapsed:.0f}s")
    print(f"\n  Done. Processed {total_processed} files in {elapsed:.0f}s.")


# =====================================================================
# MODE: PEARLS ONLY (Pass 2 only, from existing JSONs)
# =====================================================================
def run_pearls_mode(max_files=0, verbose=False, dry_run=False):
    """Run only Pass 2 on files with summaries but no pearls."""
    print(f"\n{'#'*60}")
    print(f"  hack.CCM Generator - PEARLS MODE (Pass 2 only)")
    print(f"{'#'*60}")

    initialize_system()

    missing = find_files_missing_pearls(verbose=verbose)
    print(f"  Found {len(missing)} files missing pearls")

    # Also include previously failed pearl extractions if requested
    if INCLUDE_PREVIOUSLY_FAILED:
        errors = read_current_month_errors()
        pearl_fails = [e for e in errors if e.get("stage") == "pearl_extraction"]
        failed_files = set(e.get("file", "") for e in pearl_fails if e.get("file"))
        # Add failed files not already in missing
        existing_names = set(fn for _, fn in missing)
        for fname in failed_files:
            if fname and fname not in existing_names:
                # Try to find the file on disk
                for root, dirs, files in os.walk(OUTPUT_DIR):
                    if fname in files:
                        missing.append((os.path.join(root, fname), fname))
                        existing_names.add(fname)
                        break
        print(f"  Including {len(failed_files)} previously failed files")

    if max_files > 0:
        missing = missing[:max_files]
        print(f"  Capped at {max_files} files")

    print()

    if not missing:
        print("  No files need pearl extraction. All caught up!")
        append_to_log("mode=pearls files=0 pearls=0 - nothing to do")
        return

    if dry_run:
        print("  [Dry-run] Would extract pearls from:")
        for fpath, fname in missing:
            print(f"    - {fname}")
        append_to_log(f"mode=pearls dry_run files={len(missing)} pearls=0")
        return

    total_pearls = 0
    total_files = 0
    error_count = 0
    start_time = datetime.now()

    for i, (json_path, file_name) in enumerate(missing, start=1):
        print(f"\n  [{i}/{len(missing)}] {file_name}")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as e:
            print(f"  [X] Failed to load: {e}")
            write_error(file_name=file_name, stage="pearl_extraction", pass_number=2,
                        error=e, action="log_only")
            error_count += 1
            continue

        metadata = {
            "doi": payload.get("doi", ""),
            "authors": payload.get("authors", ""),
            "system": payload.get("specialty", [""])[0] if isinstance(payload.get("specialty"), list) else payload.get("system", ""),
            "type": payload.get("article_subtype", payload.get("doc_type", "")),
            "subtopic": payload.get("subtopic", payload.get("system", "")),
        }
        count, err = run_pearl_extraction_pass(payload, file_name, metadata)
        total_pearls += count
        if err:
            error_count += 1
        else:
            total_files += 1

    elapsed = (datetime.now() - start_time).total_seconds()
    append_to_log(f"mode=pearls files={total_files} pearls={total_pearls} errors={error_count} elapsed={elapsed:.0f}s")
    print(f"\n{'='*60}")
    print(f"  Pearls mode complete!")
    print(f"  Files processed:  {total_files}")
    print(f"  Pearls added:      {total_pearls}")
    print(f"  Errors:            {error_count}")
    print(f"  Time:              {elapsed:.0f}s")


# =====================================================================
# MODE: SUMMARY + PEARLS (both passes, sequential)
# =====================================================================
def run_summary_pearls_mode(ocr_enabled=False, max_files=0, verbose=False, once=False, dry_run=False,
                            llm_choice="together", custom_key="", custom_model=""):
    """
    Run Pass 1 on pending PDFs, then Pass 2 on ALL files missing pearls
    (both the newly generated ones and any pre-existing ones).
    """
    print(f"\n{'#'*60}")
    print(f"  hack.CCM Generator - SUMMARY+PEARLS MODE (both passes)")
    print(f"{'#'*60}")
    print(f"  OCR: {'enabled' if ocr_enabled else 'disabled'}")
    print(f"  LLM: {llm_choice}{f' [{custom_model}]' if llm_choice in ('openrouter', 'other') else ''}")
    if max_files > 0:
        print(f"  Max files (Pass 1): {max_files}")
    print()

    if dry_run:
        _dry_run_preview()
        print("\n  After Pass 1, would also run Pass 2 on all files missing pearls.")
        missing = find_files_missing_pearls(verbose=False)
        print(f"  Files currently missing pearls: {len(missing)}")
        return

    initialize_system()
    history_log = load_processed_files_from_json()
    total_p1 = 0
    total_pearls = 0
    start_time = datetime.now()

    # ----- PHASE 1: Pass 1 on pending PDFs -----
    print(f"\n  {'='*40}")
    print(f"  PHASE 1: Extract summaries from pending PDFs")
    print(f"  {'='*40}")

    try:
        loop_counter = 0
        while True:
            loop_counter += 1
            history_log = load_processed_files_from_json()
            if loop_counter % 12 == 1:
                print(f"  [Heartbeat] {datetime.now().strftime('%H:%M:%S')} | Pass1 done: {total_p1}")

            for category in CATEGORIES:
                if max_files > 0 and total_p1 >= max_files:
                    break
                folder_path = SUB_DIRS.get(category)
                if not folder_path or not os.path.exists(folder_path):
                    continue
                pdf_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]
                for file_name in pdf_files:
                    if max_files > 0 and total_p1 >= max_files:
                        break
                    path = os.path.join(folder_path, file_name)
                    if file_name in history_log:
                        if verbose:
                            print(f"  SKIP (in history): {file_name}")
                        continue
                    try:
                        initial_size = os.path.getsize(path)
                        time.sleep(FILE_STABILITY_WAIT)
                        if os.path.getsize(path) != initial_size:
                            continue
                        # Pass 1 only in this phase; pearls come in Phase 2
                        processed, p1, p2 = process_single_pdf(
                            path, category, history_log, ocr_enabled, verbose,
                            run_pearls=False,
                            llm_choice=llm_choice, custom_key=custom_key, custom_model=custom_model,
                        )
                        if processed:
                            total_p1 += 1
                    except Exception as e:
                        print(f"  [X] Error processing {file_name}: {e}")
                        write_error(file_name=file_name, stage="watcher", error=e, action="log_only")
                        continue

            if once:
                break
            if max_files > 0 and total_p1 >= max_files:
                break
            # If no new files found in this iteration in once mode, break
            if once:
                break
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\n\n  Phase 1 stopped by user.")

    print(f"\n  Phase 1 complete: {total_p1} summaries generated.")

    # ----- PHASE 2: Pass 2 on all files missing pearls -----
    print(f"\n  {'='*40}")
    print(f"  PHASE 2: Extract pearls from files missing pearls")
    print(f"  {'='*40}")

    missing = find_files_missing_pearls(verbose=verbose)
    print(f"  Found {len(missing)} files missing pearls (new + existing)")

    if not missing:
        print("  All files already have pearls!")
    else:
        for i, (json_path, file_name) in enumerate(missing, start=1):
            print(f"\n  [{i}/{len(missing)}] {file_name}")
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
            except Exception as e:
                print(f"  [X] Failed to load: {e}")
                write_error(file_name=file_name, stage="pearl_extraction", pass_number=2,
                            error=e, action="log_only")
                continue
            metadata = {
                "doi": payload.get("doi", ""),
                "authors": payload.get("authors", ""),
                "system": payload.get("specialty", [""])[0] if isinstance(payload.get("specialty"), list) else payload.get("system", ""),
                "type": payload.get("article_subtype", payload.get("doc_type", "")),
                "subtopic": payload.get("subtopic", payload.get("system", "")),
            }
            count, err = run_pearl_extraction_pass(payload, file_name, metadata)
            total_pearls += count

    elapsed = (datetime.now() - start_time).total_seconds()
    append_to_log(f"mode=summary_pearls ocr={ocr_enabled} pass1={total_p1} pearls={total_pearls} elapsed={elapsed:.0f}s")
    print(f"\n{'='*60}")
    print(f"  Summary+Pearls complete!")
    print(f"  Pass 1 files:    {total_p1}")
    print(f"  Pearls added:    {total_pearls}")
    print(f"  Time:            {elapsed:.0f}s")


# =====================================================================
# MODE: WATCH (default loop with both passes per file)
# =====================================================================
def run_watch_mode(ocr_enabled=False, max_files=0, verbose=False, once=False, dry_run=False,
                   llm_choice="together", custom_key="", custom_model=""):
    """Watch input folder, process PDFs with both passes."""
    print(f"\n{'#'*60}")
    print(f"  hack.CCM Generator - WATCH MODE (Pass 1 + Pass 2 per file)")
    print(f"{'#'*60}")
    print(f"  Watching: {SUB_DIRS}")
    print(f"  OCR: {'enabled' if ocr_enabled else 'disabled'}")
    print(f"  Pearls: {'enabled' if PEARLS_ENABLED else 'disabled'}")
    print(f"  LLM: {llm_choice}{f' [{custom_model}]' if llm_choice in ('openrouter', 'other') else ''}")
    if max_files > 0:
        print(f"  Max files: {max_files}")
    print(f"  Loop: {'once' if once else 'continuous'}")
    print()

    if dry_run:
        _dry_run_preview()
        return

    initialize_system()
    history_log = load_processed_files_from_json()
    total_processed = 0
    total_pearls = 0
    start_time = datetime.now()

    try:
        loop_counter = 0
        while True:
            loop_counter += 1
            history_log = load_processed_files_from_json()
            if loop_counter % 12 == 1:
                print(f"  [Heartbeat] {datetime.now().strftime('%H:%M:%S')} | Processed: {total_processed}")

            found_any = False
            for category in CATEGORIES:
                if max_files > 0 and total_processed >= max_files:
                    break
                folder_path = SUB_DIRS.get(category)
                if not folder_path or not os.path.exists(folder_path):
                    continue
                pdf_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]
                for file_name in pdf_files:
                    if max_files > 0 and total_processed >= max_files:
                        break
                    path = os.path.join(folder_path, file_name)
                    if file_name in history_log:
                        if verbose:
                            print(f"  SKIP (in history): {file_name}")
                        continue
                    found_any = True
                    try:
                        initial_size = os.path.getsize(path)
                        time.sleep(FILE_STABILITY_WAIT)
                        if os.path.getsize(path) != initial_size:
                            continue
                        processed, p1, p2 = process_single_pdf(
                            path, category, history_log, ocr_enabled, verbose,
                            run_pearls=True,
                            llm_choice=llm_choice, custom_key=custom_key, custom_model=custom_model,
                        )
                        if processed:
                            total_processed += 1
                            total_pearls += p2
                    except Exception as e:
                        print(f"  [X] Error processing {file_name}: {e}")
                        write_error(file_name=file_name, stage="watcher", error=e, action="log_only")
                        continue

            if once:
                if not found_any:
                    print("  No new files found in queue.")
                break
            if max_files > 0 and total_processed >= max_files:
                print(f"\n  Reached --max limit ({max_files}). Exiting.")
                break
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\n\n  Stopped by user.")

    elapsed = (datetime.now() - start_time).total_seconds()
    append_to_log(f"mode=watch ocr={ocr_enabled} files={total_processed} pearls={total_pearls} elapsed={elapsed:.0f}s")
    print(f"\n  Session complete. Processed {total_processed} files, {total_pearls} pearls in {elapsed:.0f}s.")


# =====================================================================
# STATUS DASHBOARD
# =====================================================================
def status_report():
    """Quick dashboard: pending PDFs, missing pearls, errors, API status."""
    print(f"\n{'='*60}")
    print(f"  hack.CCM STATUS DASHBOARD")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # Pending PDFs in input
    history = load_processed_files_from_json()
    pending_total = 0
    print(f"\n  PENDING PDFs (in input_pdfs/):")
    for category in CATEGORIES:
        folder_path = SUB_DIRS.get(category)
        if not folder_path or not os.path.exists(folder_path):
            continue
        pdf_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]
        pending = [f for f in pdf_files if f not in history]
        print(f"    {category:12s}: {len(pending)} pending / {len(pdf_files)} total")
        pending_total += len(pending)
    print(f"    {'TOTAL':12s}: {pending_total} pending")

    # Summaries without pearls
    missing = find_files_missing_pearls(verbose=False)
    print(f"\n  SUMMARIES MISSING PEARLS: {len(missing)}")

    # Errors this month
    errors = read_current_month_errors()
    if errors:
        from collections import Counter
        by_priority = Counter(e.get("priority", "LOW") for e in errors)
        print(f"\n  ERRORS (current month: {os.path.basename(get_error_list_path())}):")
        print(f"    Total: {len(errors)}")
        for p in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            if by_priority.get(p, 0) > 0:
                print(f"    {p:10s}: {by_priority[p]}")
    else:
        print(f"\n  ERRORS: None this month")

    # API key status
    from acumen_core.config import (
        TOGETHER_API_KEY, DEEPSEEK_API_KEY, PRIMARY_GEMINI_API_KEY,
    )
    print(f"\n  API KEY STATUS:")
    print(f"    OpenRouter: {'OK' if OPENROUTER_API_KEY else 'MISSING (default --llm)'}")
    print(f"    Together:  {'OK' if TOGETHER_API_KEY else 'MISSING'}")
    print(f"    Gemini:    {'OK' if PRIMARY_GEMINI_API_KEY else 'MISSING'}")
    print(f"    DeepSeek:  {'OK' if DEEPSEEK_API_KEY else 'MISSING (optional)'}")

    # Recent log entries
    if os.path.exists(GENERATOR_LOG_FILE):
        print(f"\n  RECENT RUNS (last 5 from generator.log):")
        try:
            with open(GENERATOR_LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()[-5:]
            for line in lines:
                print(f"    {line.strip()}")
        except Exception:
            pass
    else:
        print(f"\n  RECENT RUNS: (no generator.log yet)")

    print(f"\n{'='*60}\n")


# =====================================================================
# DRY RUN PREVIEW
# =====================================================================
def _dry_run_preview():
    """Preview what would be processed."""
    print("  [Dry-run] Preview only - no API calls, no file changes\n")
    history = load_processed_files_from_json()
    print(f"  Already processed: {len(history)} files\n")
    total_pending = 0
    for category in CATEGORIES:
        folder_path = SUB_DIRS.get(category)
        if not folder_path or not os.path.exists(folder_path):
            continue
        pdf_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]
        pending = [f for f in pdf_files if f not in history]
        print(f"  [{category.upper()}] {len(pending)} pending / {len(pdf_files)} total")
        for f in pending:
            print(f"    - {f}")
        total_pending += len(pending)
    print(f"\n  Total pending PDFs: {total_pending}")
    missing = find_files_missing_pearls()
    print(f"  Files missing pearls: {len(missing)}")


# =====================================================================
# REPROCESS SINGLE FILE
# =====================================================================
def reprocess_file(file_path, ocr_enabled=False, llm_choice="together", custom_key="", custom_model=""):
    """Force re-process a single specific PDF file (both passes)."""
    if not os.path.exists(file_path):
        print(f"  File not found: {file_path}")
        return
    category = "articles"
    for cat, folder in SUB_DIRS.items():
        if os.path.commonpath([os.path.abspath(folder), os.path.abspath(file_path)]) == os.path.abspath(folder):
            category = cat
            break
    initialize_system()
    dummy_history = set()
    process_single_pdf(file_path, category, dummy_history, ocr_enabled, verbose=True, run_pearls=True,
                       llm_choice=llm_choice, custom_key=custom_key, custom_model=custom_model)


# =====================================================================
# EXTRACT PEARLS FROM ONE JSON
# =====================================================================
def extract_pearls_from_one_json(json_path):
    """Run only Pass 2 on one existing JSON file."""
    if not os.path.exists(json_path):
        print(f"  JSON not found: {json_path}")
        return
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        print(f"  Failed to load JSON: {e}")
        return
    file_name = os.path.basename(json_path)
    metadata = {
        "doi": payload.get("doi", ""),
        "authors": payload.get("authors", ""),
        "system": payload.get("specialty", [""])[0] if isinstance(payload.get("specialty"), list) else payload.get("system", ""),
        "type": payload.get("article_subtype", payload.get("doc_type", "")),
        "subtopic": payload.get("subtopic", payload.get("system", "")),
    }
    initialize_system()
    run_pearl_extraction_pass(payload, file_name, metadata)


# =====================================================================
# MAIN ENTRY POINT
# =====================================================================
def main():
    parser = argparse.ArgumentParser(
        description="hack.CCM Unified Ingestion Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
MODES:
  --mode watch           Watch folder, run both passes per PDF (default)
  --mode summary         Only run Pass 1 (summaries). Skip pearls
  --mode pearls          Only run Pass 2 on files missing pearls
  --mode summary_pearls  Run Pass 1 on pending PDFs, then Pass 2 on all missing

LLM PROVIDER (for Pass 1 extraction):
  --llm openrouter       Use OpenRouter (default, reads OPENROUTER_API_KEY + OPENROUTER_MODEL from .env)
  --llm together         Use Together AI (requires TOGETHER_API_KEY)
  --llm gemini           Use Google Gemini (requires PRIMARY_GEMINI_API_KEY)
  --llm other            Custom OpenAI-compatible API (provide --api-key and --model)

EXAMPLES:
  python generator.py                                   # openrouter, deepseek-ai/DeepSeek-V4-Pro (default)
  python generator.py --mode summary                    # only summaries
  python generator.py --mode pearls                     # only pearls for pending files
  python generator.py --mode summary_pearls             # both sequential
  python generator.py --mode summary --ocr               # summaries with OCR
  python generator.py --mode pearls --max 20            # cap pearls at 20 files
  python generator.py --status                          # quick dashboard
  python generator.py --reprocess input_pdfs/articles/paper.pdf
  python generator.py --extract-pearls output_files/Cardiology/Review/paper.json
  python generator.py --llm together                     # use Together AI instead
  python generator.py --llm gemini                       # use Gemini instead
  python generator.py --llm openrouter --model anthropic/claude-3.5-sonnet  # override model
        """,
    )
    parser.add_argument("--mode", choices=["watch", "summary", "pearls", "summary_pearls"],
                        default=DEFAULT_MODE, help="Operation mode (default: watch)")
    parser.add_argument("--ocr", action="store_true", help="Enable OCR fallback for scanned PDFs")
    parser.add_argument("--max", type=int, default=0, help="Max files to process (0 = unlimited)")
    parser.add_argument("--once", action="store_true", help="Process current queue once, no loop")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no API calls")
    parser.add_argument("--verbose", action="store_true", help="Detailed per-file logging")
    parser.add_argument("--status", action="store_true", help="Show dashboard and exit")
    parser.add_argument("--reprocess", type=str, default=None, help="Force re-process a specific PDF")
    parser.add_argument("--extract-pearls", type=str, default=None,
                        help="Run Pass 2 only on one specific existing JSON file")
    parser.add_argument("--llm", choices=["together", "gemini", "openrouter", "other"], default="openrouter",
                        help="LLM provider for Pass 1 extraction (default: openrouter)")
    parser.add_argument("--api-key", type=str, default="",
                        help="API key for --llm openrouter/other (falls back to OPENROUTER_API_KEY from .env)")
    parser.add_argument("--model", type=str, default=OPENROUTER_MODEL,
                        help=f"Model name for --llm openrouter/other (default: {OPENROUTER_MODEL})")
    args = parser.parse_args()

    # --- Status dashboard ---
    if args.status:
        status_report()
        return

    # --- Extract pearls from one JSON ---
    if args.extract_pearls:
        if not PEARLS_ENABLED:
            print("  PEARLS_ENABLED is False. Set it to True in generator.py config.")
            return
        print("  Mode: Extract pearls from one JSON")
        extract_pearls_from_one_json(args.extract_pearls)
        return

    # --- Validate --llm openrouter/other: use config key if no --api-key, require model ---
    if args.llm in ("openrouter", "other"):
        api_key = args.api_key or OPENROUTER_API_KEY
        if not api_key:
            print("  [X] --llm openrouter/other requires an API key. Provide --api-key or set OPENROUTER_API_KEY in .env")
            sys.exit(1)
        if not args.model:
            print(f"  [X] --llm openrouter/other requires a model. Provide --model or set OPENROUTER_MODEL in .env / config.py")
            sys.exit(1)
        # Patch resolved key back for downstream use
        args.api_key = api_key

    # --- Re-process single PDF ---
    if args.reprocess:
        print("  Mode: Re-process single PDF")
        reprocess_file(args.reprocess, ocr_enabled=args.ocr,
                       llm_choice=args.llm, custom_key=args.api_key, custom_model=args.model)
        return

    # --- Mode dispatch ---
    ocr_enabled = args.ocr or OCR_ENABLED_DEFAULT

    if args.mode == "watch":
        run_watch_mode(ocr_enabled=ocr_enabled, max_files=args.max,
                       verbose=args.verbose, once=args.once, dry_run=args.dry_run,
                       llm_choice=args.llm, custom_key=args.api_key, custom_model=args.model)
    elif args.mode == "summary":
        run_summary_mode(ocr_enabled=ocr_enabled, max_files=args.max,
                         verbose=args.verbose, once=args.once, dry_run=args.dry_run,
                         llm_choice=args.llm, custom_key=args.api_key, custom_model=args.model)
    elif args.mode == "pearls":
        run_pearls_mode(max_files=args.max, verbose=args.verbose, dry_run=args.dry_run)
    elif args.mode == "summary_pearls":
        run_summary_pearls_mode(ocr_enabled=ocr_enabled, max_files=args.max,
                                verbose=args.verbose, once=args.once, dry_run=args.dry_run,
                                llm_choice=args.llm, custom_key=args.api_key, custom_model=args.model)


if __name__ == "__main__":
    main()
