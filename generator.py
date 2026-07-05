#!/usr/bin/env python3
"""
generator.py - hack.CCM Unified Ingestion Pipeline
====================================================
Watches input_pdfs/{articles,guidelines,other}/ for new PDFs and processes them in 2 passes:

  PASS 1 - Full Schema Extraction
    Extracts structured JSON (Article or Guideline schema) with markdown enrichment.
    Providers: Together AI (DeepSeek V4 Pro) -> Direct DeepSeek API
    Output: output_files/{system}/{type}/{filename}.json

  PASS 2 - Pearl Extraction (separate API call for quality)
    Uses cheaper models to extract high-yield clinical pearls.
    Providers: openai/gpt-oss-20b -> openai/gpt-oss-120b
    Output: pearls.json (appended atomically)

After processing, source PDFs are moved to quarantine/YYYY-MM-DD/{category}/.
All errors are logged to master_error_list_YYYY-MM.txt (monthly rotation).

USAGE:
    python generator.py                    # Watch loop (default)
    python generator.py --ocr               # Enable OCR fallback for scanned PDFs
    python generator.py --max 5             # Process max 5 files then exit
    python generator.py --once              # Process current queue once, no loop
    python generator.py --dry-run           # Preview what would be processed
    python generator.py --verbose            # Detailed per-file logging
    python generator.py --reprocess FILE.pdf # Force re-process a specific file
    python generator.py --extract-pearls JSON_FILE  # Only run Pass 2 on existing JSON
"""

import os
import sys
import time
import json
import shutil
import argparse
from datetime import datetime
from copy import deepcopy
from pypdf import PdfReader

from acumen_core.config import (
    BASE_INPUT_DIR, SUB_DIRS, OUTPUT_DIR, QUARANTINE_BASE,
    EXCEL_TRACKER_FILE, JSON_TRACKER_FILE, PEARLS_JSON, PEARLS_TRACKER,
    PEARLS_JSON_FIELDS, PROJECT_DIR,
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
from acumen_core.errors import write_error, classify_error
from acumen_core.llm import (
    execute_with_fallback, execute_pearl_extraction,
    chunk_text, merge_chunks_programmatically,
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

# --- Watch directories (keys must match SUB_DIRS in config.py) ---
CATEGORIES = ["articles", "guidelines", "other"]

# --- Processing behavior ---
POLL_INTERVAL = 5                  # seconds between polling cycles
FILE_STABILITY_WAIT = 1.5          # seconds to wait for file size to stabilize
MIN_TEXT_LENGTH = 150              # minimum chars to consider text extractable

# --- Chunking (large PDFs) ---
CHUNK_SIZE_OVERRIDE = None         # None = use config default (400000)
CHUNK_OVERLAP_OVERRIDE = None      # None = use config default (3000)

# --- OCR ---
OCR_ENABLED_DEFAULT = False        # default OCR state (can override with --ocr)
OCR_MINChars = 150                 # trigger page OCR if PyPDF returns < this

# --- Quarantine ---
QUARANTINE_AFTER_PROCESS = True    # move PDFs to quarantine after success
QUARANTINE_AFTER_FAILURE = False   # move PDFs to error quarantine after failure

# --- Error handling ---
MAX_RETRIES_OVERRIDE = None        # None = use config default (3)
RETRY_DELAY_OVERRIDE = None        # None = use config default (10s)

# --- Pearl extraction ---
PEARLS_ENABLED = True               # run Pass 2 (pearl extraction) after Pass 1
PEARLS_MAX_PER_FILE = 25            # maximum pearls to save per file


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

    if ocr_enabled and len(full_text) < OCR_MINChars:
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


def run_extraction_pass(file_path, category, ocr_enabled=False):
    """
    PASS 1: Extract structured JSON from PDF.
    Returns (payload_dict, error_or_None).
    """
    file_name = os.path.basename(file_path)

    try:
        full_text = extract_text_from_pdf(file_path, ocr_enabled)

        if len(full_text) < MIN_TEXT_LENGTH:
            error_msg = f"Extracted text too short ({len(full_text)} chars) or unreadable"
            write_error(
                file_name=file_name, stage="extraction", pass_number=1,
                error=error_msg, action="log_only",
                extra_fields={"text_chars": len(full_text)},
            )
            return None, error_msg

        text_chunks = chunk_text(full_text, CHUNK_SIZE_OVERRIDE, CHUNK_OVERLAP_OVERRIDE)

        if len(text_chunks) == 1:
            print(f"  Extracted {len(full_text)} chars, calling extraction model...")
            user_content = f"Extract and structure the following clinical document into JSON format. Return ONLY valid JSON following the schema from the system prompt:\n\n{full_text}"
            structured_payload = execute_with_fallback(
                EXTRACTION_SYSTEM_PROMPT, user_content, category,
                max_retries=MAX_RETRIES_OVERRIDE,
                retry_delay=RETRY_DELAY_OVERRIDE,
            )
        else:
            print(f"  Document large ({len(full_text)} chars). Splitting into {len(text_chunks)} chunks...")
            chunk_results = []
            for i, chunk in enumerate(text_chunks):
                print(f"  Chunk {i + 1}/{len(text_chunks)} ({len(chunk)} chars)...")
                user_content = f"Extract and structure the following clinical document chunk into JSON format. Return ONLY valid JSON:\n\n{chunk}"
                chunk_result = execute_with_fallback(
                    EXTRACTION_SYSTEM_PROMPT, user_content, category,
                    max_retries=MAX_RETRIES_OVERRIDE,
                    retry_delay=RETRY_DELAY_OVERRIDE,
                )
                chunk_results.append(chunk_result)
            structured_payload = merge_chunks_programmatically(chunk_results)
            print(f"  Merged {len(chunk_results)} chunks into single JSON")

        return structured_payload, None

    except Exception as e:
        write_error(
            file_name=file_name, stage="extraction", pass_number=1,
            error=e, action="log_only",
        )
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

    return destination_json_path, log_meta, clean_system, clean_type


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
            "id": str(next_id),
            "timestamp": now_ts,
            "source_paper": source_paper,
            "doi": metadata.get("doi", ""),
            "author": metadata.get("authors", metadata.get("primary_authors", "")),
            "system": metadata.get("system", ""),
            "type": metadata.get("type", metadata.get("article_subtype", "")),
            "pearl": text[:500],
            "remarks": "",
            "file_name": file_name,
            "topic": topic,
        })
        next_id += 1

    all_rows = existing_rows + rows_to_add
    save_json_atomic(PEARLS_JSON, all_rows)
    return len(rows_to_add)


def run_pearl_extraction_pass(payload, file_name, metadata):
    """
    PASS 2: Extract clinical pearls using separate cheaper model.
    Returns (pearl_count, error_or_None).
    """
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
        write_error(
            file_name=file_name, stage="pearl_extraction", pass_number=2,
            error=e, provider="together", action="log_only",
            extra_fields={"pearl_model_primary": "openai/gpt-oss-20b"},
        )
        return 0, str(e)


# =====================================================================
# SINGLE PDF PROCESSING (PASS 1 + PASS 2)
# =====================================================================
def process_single_pdf(file_path, category, processed_history, ocr_enabled=False, verbose=False):
    """
    Process one PDF file through both passes.
    Updates history set with file_name on success.
    """
    file_name = os.path.basename(file_path)
    if file_name in processed_history:
        if verbose:
            print(f"  SKIP (already processed): {file_name}")
        return False

    print(f"\n{'='*60}")
    print(f"  Ingesting [{category.upper()}]: {file_name}")
    print(f"{'='*60}")

    pass1_success = False
    pass2_success = False

    # ----- PASS 1: Full Schema Extraction -----
    payload, err1 = run_extraction_pass(file_path, category, ocr_enabled)
    if payload is None:
        print(f"  [X] Pass 1 failed: {err1}")
        if QUARANTINE_AFTER_FAILURE:
            move_to_quarantine(file_path, category, error=True)
        return False

    try:
        json_path, log_meta, clean_system, clean_type = save_extracted_json(payload, file_name)
        log_transaction_to_excel(file_name, log_meta, "Success")
        log_transaction_to_json(file_name, log_meta, "Success")
        processed_history.add(file_name)
        pass1_success = True
        print(f"  Pass 1: OK (system={clean_system}, type={clean_type})")
    except Exception as e:
        print(f"  [X] Failed to save/log Pass 1: {e}")
        write_error(file_name=file_name, stage="save", pass_number=1, error=e, action="log_only")
        return False

    # ----- PASS 2: Pearl Extraction (separate call) -----
    if PEARLS_ENABLED:
        pearl_count, err2 = run_pearl_extraction_pass(payload, file_name, log_meta)
        if err2:
            print(f"  [!] Pass 2 (pearls) failed: {err2} — summary still saved")
        else:
            pass2_success = True
    else:
        print("  Pass 2: Skipped (PEARLS_ENABLED=False)")

    # ----- Quarantine source PDF -----
    if QUARANTINE_AFTER_PROCESS and pass1_success:
        move_to_quarantine(file_path, category, error=False)

    status = "SUCCESS" if (pass1_success and (pass2_success or not PEARLS_ENABLED)) else "PARTIAL"
    print(f"  [{status}] {file_name} — Pass1={'OK' if pass1_success else 'FAIL'}, Pass2={'OK' if pass2_success else 'SKIP' if not PEARLS_ENABLED else 'FAIL'}")
    return True


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
# WATCHER LOOP
# =====================================================================
def run_watch_loop(ocr_enabled=False, max_files=0, verbose=False, once=False):
    """
    Continuously poll input directories for new PDFs.
    Set once=True to process current queue once and exit.
    """
    initialize_system()
    history_log = load_processed_files_from_json()

    print(f"\n{'#'*60}")
    print(f"  hack.CCM Ingestion Engine - Watch Mode")
    print(f"{'#'*60}")
    print(f"  Watching: {BASE_INPUT_DIR}/{{articles,guidelines,other}}/")
    print(f"  OCR: {'enabled' if ocr_enabled else 'disabled'}")
    print(f"  Pearls: {'enabled' if PEARLS_ENABLED else 'disabled'}")
    if max_files > 0:
        print(f"  Max files: {max_files}")
    print(f"  Mode: {'once' if once else 'continuous'}")
    print()

    try:
        loop_counter = 0
        files_processed = 0

        while True:
            loop_counter += 1
            history_log = load_processed_files_from_json()

            if loop_counter % 12 == 1:
                print(f"  [Heartbeat] {datetime.now().strftime('%H:%M:%S')} | Processed: {files_processed}")

            found_any = False
            for category in CATEGORIES:
                if max_files > 0 and files_processed >= max_files:
                    break
                folder_path = SUB_DIRS.get(category)
                if not folder_path or not os.path.exists(folder_path):
                    continue
                pdf_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]
                for file_name in pdf_files:
                    if max_files > 0 and files_processed >= max_files:
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
                        processed = process_single_pdf(path, category, history_log, ocr_enabled, verbose)
                        if processed:
                            files_processed += 1
                    except Exception as e:
                        print(f"  [X] Error processing {file_name}: {e}")
                        write_error(file_name=file_name, stage="watcher", error=e, action="log_only")
                        continue

            if once:
                if not found_any:
                    print("  No new files found in queue.")
                break

            if max_files > 0 and files_processed >= max_files:
                print(f"\n  Reached --max limit ({max_files}). Exiting.")
                break

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n  Stopped by user.")
        print(f"  Total processed this session: {files_processed}")


# =====================================================================
# REPROCESS SINGLE FILE
# =====================================================================
def reprocess_file(file_path, ocr_enabled=False):
    """Force re-process a single specific PDF file."""
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
    process_single_pdf(file_path, category, dummy_history, ocr_enabled, verbose=True)


# =====================================================================
# EXTRACT PEARLS ONLY (from existing JSON)
# =====================================================================
def extract_pearls_from_json(json_path):
    """Run only Pass 2 on an existing JSON file (skip Pass 1)."""
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
Examples:
  python generator.py                       # Watch loop (default)
  python generator.py --ocr                 # Watch loop with OCR for scanned PDFs
  python generator.py --max 5               # Process max 5 files then exit
  python generator.py --once                # Process current queue once, no loop
  python generator.py --dry-run             # Preview files that would be processed
  python generator.py --verbose             # Detailed per-file logging
  python generator.py --reprocess FILE.pdf  # Force re-process a specific file
  python generator.py --extract-pearls X.json # Only run Pass 2 on existing JSON
        """,
    )
    parser.add_argument("--ocr", action="store_true", help="Enable OCR fallback for scanned PDFs")
    parser.add_argument("--max", type=int, default=0, help="Max files to process (0 = unlimited)")
    parser.add_argument("--once", action="store_true", help="Process current queue once, no loop")
    parser.add_argument("--dry-run", action="store_true", help="Preview files that would be processed")
    parser.add_argument("--verbose", action="store_true", help="Detailed per-file logging")
    parser.add_argument("--reprocess", type=str, default=None, help="Force re-process a specific PDF file")
    parser.add_argument("--extract-pearls", type=str, default=None, help="Only run Pass 2 (pearls) on an existing JSON file")
    args = parser.parse_args()

    # --- Mode: Extract pearls only from JSON ---
    if args.extract_pearls:
        if not PEARLS_ENABLED:
            print("  PEARLS_ENABLED is False. Set it to True in generator.py config.")
            return
        print("  Mode: Extract pearls from existing JSON")
        extract_pearls_from_json(args.extract_pearls)
        return

    # --- Mode: Re-process single file ---
    if args.reprocess:
        print("  Mode: Re-process single file")
        reprocess_file(args.reprocess, ocr_enabled=args.ocr)
        return

    # --- Mode: Dry run (preview only) ---
    if args.dry_run:
        print("  Mode: Dry run (preview only)\n")
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
        print(f"\n  Total pending: {total_pending}")
        if total_pending == 0:
            print("  No files to process.")
        return

    # --- Mode: Watch loop or once ---
    ocr_enabled = args.ocr or OCR_ENABLED_DEFAULT
    run_watch_loop(
        ocr_enabled=ocr_enabled,
        max_files=args.max,
        verbose=args.verbose,
        once=args.once,
    )


if __name__ == "__main__":
    main()
