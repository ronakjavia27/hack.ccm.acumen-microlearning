#!/usr/bin/env python3
"""
maintainer.py - hack.CCM Repository Maintenance & Health Engine
================================================================
Keeps output_files/, sent_summaries.json, pearls.json consistent and healthy.
Reads master_error_list_YYYY-MM.txt to prioritize repairs automatically.

USAGE (single commands or combine with --auto-fix):
    python maintainer.py                              # Full health report (default)
    python maintainer.py --reconcile                   # Sync disk <-> sent_summaries.json
    python maintainer.py --validate                    # Schema-check all JSONs
    python maintainer.py --repair                       # Auto-fix safe issues
    python maintainer.py --reclassify                   # Fix pearl systems from summaries
    python maintainer.py --reprocess-pearls             # Re-run Pass 2 for failed pearls
    python maintainer.py --error-priority                # Show prioritized error list
    python maintainer.py --auto-fix                      # Run reconcile + validate + repair + reprocess-pearls
    python maintainer.py --full-scan                     # Include all monthly error logs (not just current)
    python maintainer.py --dry-run                       # Preview only, no writes
    python maintainer.py --verbose                        # Detailed per-file logging
    python maintainer.py --report-only                     # Generate health report, no fixes
"""

import os
import sys
import json
import argparse
import unicodedata
from datetime import datetime
from collections import Counter, defaultdict

from acumen_core.config import (
    OUTPUT_DIR, JSON_TRACKER_FILE, REMOVED_TRACKER_FILE, PEARLS_JSON,
    PEARLS_TRACKER, SPECIALTIES_FILE, ARTICLE_TYPES_FILE, PROJECT_DIR,
    get_error_list_path, get_all_error_list_paths,
)
from acumen_core.vocabulary import (
    get_allowed_specialties, get_allowed_types,
    build_specialty_map, normalize_specialty, normalize_type,
)
from acumen_core.tracking import (
    load_all_entries_from_json, save_json_atomic, load_json_safe,
    append_removed_entries, load_removed_entries,
    load_pearl_tracker, update_pearl_tracker,
)
from acumen_core.errors import (
    read_current_month_errors, read_all_errors, read_errors_from_file,
    ERROR_PRIORITIES, write_error, get_priority,
)
from acumen_core.schema import (
    ARTICLE_REQUIRED_FIELDS, GUIDELINE_REQUIRED_FIELDS,
    VALID_ARTICLE_SUBTYPES, VALID_SPECIALTY_VALUES, VALID_EVIDENCE_LEVELS,
    VALID_STRENGTH_VALUES,
)
from acumen_core.markdown import enrich_payload_with_markdown
from acumen_core.llm import execute_pearl_extraction

# Fix stdout encoding
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


# =====================================================================
# CONFIGURATION - Edit these for easy changes
# =====================================================================

# --- Health report output ---
HEALTH_REPORT_JSON = os.path.join(PROJECT_DIR, "health_report.json")
HEALTH_REPORT_MD = os.path.join(PROJECT_DIR, "health_report.md")

# --- Reconcile settings ---
USE_DIRECTORY_AS_GROUND_TRUTH = True  # system/type from folder path overrides JSON

# --- Repair settings ---
AUTO_NORMALIZE_SPECIALTIES = True     # fix invalid specialty values
AUTO_FIX_DOI_FORMAT = True             # ensure doi starts with https://doi.org/ or "None"
AUTO_DEDUPLICATE_ENTRIES = True        # remove duplicate file_name entries in sent_summaries.json
AUTO_BACKUP_BEFORE_REPAIR = True       # save backup before modifying files

# --- Reprocess pearls ---
REPROCESS_PEARL_MAX = 50              # max files to re-extract pearls for in one run
REPROCESS_PEARL_MODEL_PRIMARY = "openai/gpt-oss-20b"
REPROCESS_PEARL_MODEL_FALLBACK = "openai/gpt-oss-120b"

# --- Error priority thresholds ---
REPEATED_FAILURE_THRESHOLD = 3        # files with >= N failures -> HIGH priority reprocess

# --- Error types that warrant automatic reprocessing ---
AUTOREPROCESS_TYPES = {"API_TIMEOUT", "EMPTY_RESPONSE", "JSON_PARSE_ERROR", "TEXT_EXTRACTION_FAILED"}

# --- Reset pearls settings ---
RESET_PEARL_BACKUP_BEFORE = True     # backup pearls.json before resetting a file


# =====================================================================
# DISK INDEX - Scan output_files/ for all JSONs
# =====================================================================
def build_disk_index(verbose=False):
    """
    Walk output_files/ and return dict: file_name -> (file_path, payload).
    file_name uses .pdf convention (strip .json -> +.pdf).
    """
    disk = {}
    if not os.path.exists(OUTPUT_DIR):
        return disk
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for fname in files:
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    payload = json.load(f)
            except (json.JSONDecodeError, Exception) as e:
                if verbose:
                    print(f"    [skip] Invalid JSON: {fpath} ({e})")
                continue
            base = os.path.splitext(fname)[0]
            pdf_name = base + ".pdf"
            if pdf_name in disk:
                if verbose:
                    print(f"    [warn] Duplicate basename '{pdf_name}' -> {fpath}")
                continue
            disk[pdf_name] = (fpath, payload)
    return disk


def extract_metadata_from_payload(payload):
    """Extract title/system/type/journal/authors/doi/year from payload."""
    title = payload.get("paper_name") or payload.get("title", "")
    system = payload.get("system", "")
    if not system and payload.get("specialty"):
        spec_map = build_specialty_map(get_allowed_specialties())
        system = normalize_specialty(payload["specialty"], spec_map)
    article_type = payload.get("type_of_article") or payload.get("article_subtype") or payload.get("doc_type", "")
    journal = payload.get("journal_name") or payload.get("journal", "")
    if not journal:
        issuing = payload.get("issuing_bodies", [])
        if issuing:
            journal = ", ".join(issuing)
    if not journal:
        journal = "Unknown Journal"
    authors = payload.get("primary_authors") or payload.get("authors", "Unknown Authors")
    if not authors or authors == "Unknown Authors":
        issuing = payload.get("issuing_bodies", [])
        if issuing:
            authors = ", ".join(issuing)
    doi = payload.get("doi", "None")
    if not doi:
        doi = "None"
    year = payload.get("year", "")
    return title, system, article_type, journal, authors, doi, year


def entry_from_payload(file_name, payload, fpath=None):
    """Build a sent_summaries.json entry from a JSON payload on disk."""
    title, system, article_type, journal, authors, doi, year = extract_metadata_from_payload(payload)
    if fpath and USE_DIRECTORY_AS_GROUND_TRUTH:
        parts = fpath.replace("\\", "/").rstrip("/").split("/")
        if len(parts) >= 3:
            ps = parts[-3]
            if ps and ps != "output_files":
                system = ps
                pt = parts[-2]
                if pt:
                    article_type = pt
    return {
        "serial_number": 0,
        "file_name": file_name,
        "title": title,
        "authors": authors,
        "journal": journal,
        "doi": doi,
        "year": str(year) if year else "",
        "system": system or "Other",
        "type": article_type or "Other",
        "md_generated": "Yes",
        "email_pushed": "No",
        "date_added": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "email_pushed_date": "",
        "parsing_notes": "Added by maintainer.py",
        "show_on_web": "No",
    }


# =====================================================================
# RECONCILE - disk <-> sent_summaries.json
# =====================================================================
def reconcile(dry_run=False, verbose=False):
    """Reconcile output_files/ with sent_summaries.json."""
    print("\n  [RECONCILE] Scanning output_files/...")
    disk = build_disk_index(verbose)
    print(f"    Found {len(disk)} .json files on disk")

    repo = load_all_entries_from_json()
    print(f"    Loaded {len(repo)} entries from {os.path.basename(JSON_TRACKER_FILE)}")

    repo_by_file = {e["file_name"]: e for e in repo if e.get("file_name")}

    # Phase A: ADD - entries on disk not in repo
    to_add = []
    for file_name, (fpath, payload) in disk.items():
        if file_name not in repo_by_file:
            entry = entry_from_payload(file_name, payload, fpath)
            to_add.append(entry)
            if verbose:
                print(f"    [add] {file_name} -> {entry['title'][:60]}")

    # Phase B: REMOVE - entries in repo but missing from disk
    to_remove = []
    kept = []
    updated_count = 0
    for entry in repo:
        fname = entry.get("file_name", "")
        if fname and fname not in disk:
            to_remove.append(entry)
            if verbose:
                print(f"    [remove] {fname} -> {entry.get('title', '')[:60]}")
            continue

        # Phase C: NORMALIZE - use directory path as ground truth
        if fname and fname in disk:
            fpath, _ = disk[fname]
            parts = fpath.replace("\\", "/").rstrip("/").split("/")
            if len(parts) >= 3:
                path_system = parts[-3]
                if path_system and path_system != "output_files" and path_system != entry.get("system", ""):
                    old_system = entry["system"]
                    entry["system"] = path_system
                    updated_count += 1
                    if verbose:
                        print(f"    [update] {fname}: system '{old_system}' -> '{path_system}'")
                path_type = parts[-2]
                if path_type and path_type != entry.get("type", ""):
                    entry["type"] = path_type

        kept.append(entry)

    # Reassign serial numbers
    for i, entry in enumerate(kept):
        entry["serial_number"] = i + 1
    for i, entry in enumerate(to_add):
        entry["serial_number"] = len(kept) + i + 1

    new_repo = kept + to_add

    print(f"\n    Reconcile Summary:")
    print(f"      Added:   {len(to_add)}")
    print(f"      Removed: {len(to_remove)}")
    print(f"      Updated: {updated_count}")
    print(f"      Kept:    {len(kept)}")
    print(f"      Total:   {len(new_repo)}")

    if dry_run:
        print("    [Dry-run] No files written.")
        return {"added": len(to_add), "removed": len(to_remove), "updated": updated_count, "total": len(new_repo)}

    # Write updated repo
    if to_add or to_remove or updated_count > 0:
        if AUTO_BACKUP_BEFORE_REPAIR:
            backup_path = JSON_TRACKER_FILE + ".bak"
            save_json_atomic(backup_path, repo)
        save_json_atomic(JSON_TRACKER_FILE, new_repo)
        print(f"    Wrote {len(new_repo)} entries to {os.path.basename(JSON_TRACKER_FILE)}")

    # Log removed entries
    if to_remove:
        append_removed_entries(to_remove)
        print(f"    Logged {len(to_remove)} removed entries to {os.path.basename(REMOVED_TRACKER_FILE)}")

    return {"added": len(to_add), "removed": len(to_remove), "updated": updated_count, "total": len(new_repo)}


# =====================================================================
# VALIDATE - schema check all JSONs in output_files/
# =====================================================================
def validate_json_file(fpath, verbose=False):
    """
    Validate a single JSON file against schema.
    Returns list of (field, issue, value) tuples.
    """
    issues = []
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        return [("_file", "JSON_PARSE_ERROR", str(e))]

    doc_type = (payload.get("doc_type") or "").lower()
    is_guideline = doc_type == "guideline"
    required = GUIDELINE_REQUIRED_FIELDS if is_guideline else ARTICLE_REQUIRED_FIELDS

    # Check required fields
    for field in required:
        if field not in payload:
            issues.append((field, "MISSING_FIELD", None))
        elif payload[field] is None and field not in ("sample_size", "population", "consensus_method", "search_period"):
            issues.append((field, "NULL_FIELD", None))

    # Check article_subtype for articles
    if not is_guideline:
        subtype = payload.get("article_subtype", "")
        if subtype and subtype not in VALID_ARTICLE_SUBTYPES:
            issues.append(("article_subtype", "INVALID_ENUM_VALUE", subtype))

    # Check specialty values
    specialties = payload.get("specialty", [])
    if not isinstance(specialties, list):
        issues.append(("specialty", "NOT_ARRAY", specialties))
    else:
        for sp in specialties:
            if sp and sp.lower().replace(" ", "_") not in VALID_SPECIALTY_VALUES:
                issues.append(("specialty", "INVALID_VALUE", sp))

    # Check evidence_level for articles
    if not is_guideline:
        ev = payload.get("evidence_level", "")
        if ev and ev not in VALID_EVIDENCE_LEVELS:
            issues.append(("evidence_level", "INVALID_ENUM_VALUE", ev))

    # Check sections have content
    sections = payload.get("sections", [])
    for i, s in enumerate(sections):
        content = s.get("content", "")
        if not content or (isinstance(content, str) and len(content.strip()) < 10):
            issues.append((f"sections[{i}].content", "EMPTY_CONTENT", None))

    # Check recommendation strengths for guidelines
    if is_guideline:
        for i, b in enumerate(payload.get("recommendation_blocks", [])):
            for j, r in enumerate(b.get("recommendations", [])):
                strength = r.get("strength")
                if strength and strength not in VALID_STRENGTH_VALUES:
                    issues.append((f"recommendation_blocks[{i}].recommendations[{j}].strength", "INVALID_ENUM_VALUE", strength))

    if verbose and issues:
        for field, issue, value in issues:
            print(f"      [{issue}] {field}: {value}")

    return issues


def validate_all(dry_run=False, verbose=False):
    """Validate all JSON files in output_files/."""
    print("\n  [VALIDATE] Checking all JSONs in output_files/...")
    if not os.path.exists(OUTPUT_DIR):
        print("    output_files/ not found")
        return {}

    json_files = []
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for fname in files:
            if fname.endswith(".json"):
                json_files.append(os.path.join(root, fname))

    print(f"    Found {len(json_files)} JSON files")

    all_issues = {}
    files_ok = 0
    files_with_issues = 0

    for fpath in json_files:
        relpath = os.path.relpath(fpath, OUTPUT_DIR)
        issues = validate_json_file(fpath, verbose)
        if issues:
            files_with_issues += 1
            all_issues[relpath] = issues
            if verbose:
                print(f"    [ISSUES] {relpath}: {len(issues)} issue(s)")
        else:
            files_ok += 1

    print(f"\n    Validation Summary:")
    print(f"      Files OK:           {files_ok}")
    print(f"      Files with issues:  {files_with_issues}")
    print(f"      Total issues:       {sum(len(v) for v in all_issues.values())}")

    return all_issues


# =====================================================================
# REPAIR - auto-fix safe issues
# =====================================================================
def repair_all(dry_run=False, verbose=False):
    """Auto-fix safe issues in output_files/ and sent_summaries.json."""
    print("\n  [REPAIR] Auto-fixing safe issues...")
    fixes_applied = 0

    # --- Repair sent_summaries.json: deduplicate, fix specialties ---
    repo = load_all_entries_from_json()
    if repo:
        if AUTO_DEDUPLICATE_ENTRIES:
            seen = set()
            deduped = []
            dupes = 0
            for entry in repo:
                fn = entry.get("file_name", "")
                if fn and fn in seen:
                    dupes += 1
                    continue
                seen.add(fn)
                deduped.append(entry)
            if dupes > 0:
                print(f"    Dedup: removed {dupes} duplicate entries from {os.path.basename(JSON_TRACKER_FILE)}")
                fixes_applied += dupes
                if not dry_run:
                    if AUTO_BACKUP_BEFORE_REPAIR:
                        save_json_atomic(JSON_TRACKER_FILE + ".bak", repo)
                    save_json_atomic(JSON_TRACKER_FILE, deduped)
                repo = deduped

    # --- Repair JSON files in output_files/ ---
    spec_map = build_specialty_map(get_allowed_specialties())

    if not os.path.exists(OUTPUT_DIR):
        return fixes_applied

    json_files = []
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for fname in files:
            if fname.endswith(".json"):
                json_files.append(os.path.join(root, fname))

    files_fixed = 0
    for fpath in json_files:
        relpath = os.path.relpath(fpath, OUTPUT_DIR)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            continue

        original = json.dumps(payload, sort_keys=True)
        modified = False

        # Fix specialty normalization
        if AUTO_NORMALIZE_SPECIALTIES and payload.get("specialty"):
            if isinstance(payload["specialty"], list):
                new_specs = []
                for sp in payload["specialty"]:
                    normalized = normalize_specialty([sp], spec_map)
                    if normalized != sp:
                        modified = True
                        if verbose:
                            print(f"    [fix] {relpath}: specialty '{sp}' -> '{normalized}'")
                    new_specs.append(normalized)
                payload["specialty"] = new_specs

        # Fix DOI format
        if AUTO_FIX_DOI_FORMAT:
            doi = payload.get("doi", "None")
            if doi and doi != "None" and not doi.startswith("http"):
                payload["doi"] = doi
                modified = True
                if verbose:
                    print(f"    [fix] {relpath}: doi kept as-is '{doi}'")

        if modified:
            after = json.dumps(payload, sort_keys=True)
            if original != after:
                files_fixed += 1
                fixes_applied += 1
                if not dry_run:
                    save_json_atomic(fpath, payload)

    print(f"\n    Repair Summary:")
    print(f"      Files fixed:       {files_fixed}")
    print(f"      Total fixes:       {fixes_applied}")

    return fixes_applied


# =====================================================================
# RECLASSIFY PEARLS - cross-reference with sent_summaries
# =====================================================================
def normalize_title(s):
    """Normalize title for matching."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.replace("\u2013", "-").replace("\u2014", "--")
    s = s.replace("\u2018", "'").replace("\u2019", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    return s.strip().lower()


def reclassify_pearls(dry_run=False, verbose=False):
    """Cross-reference pearls with sent_summaries to fix system field."""
    print("\n  [RECLASSIFY] Fixing pearl systems from sent_summaries...")

    pearls = load_json_safe(PEARLS_JSON, [])
    summaries = load_all_entries_from_json()

    if not pearls or not summaries:
        print("    No pearls or summaries to process.")
        return 0

    print(f"    Loaded {len(pearls)} pearls")
    print(f"    Loaded {len(summaries)} summaries")

    # Build lookup: normalized title -> system
    lookup = {}
    for s in summaries:
        title = s.get("title", "").strip()
        system = s.get("system", "").strip()
        if not title or not system:
            continue
        key = normalize_title(title)
        if key not in lookup:
            lookup[key] = system

    print(f"    Built lookup with {len(lookup)} titles")

    changes = []
    already_correct = 0
    unmatched = 0

    for pearl in pearls:
        source = pearl.get("source_paper", "").strip()
        if not source:
            unmatched += 1
            continue

        key = normalize_title(source)
        correct_system = lookup.get(key)

        if not correct_system:
            unmatched += 1
            continue

        current_system = pearl.get("system", "").strip()
        if current_system == correct_system:
            already_correct += 1
            continue

        changes.append({
            "id": pearl.get("id", ""),
            "source_paper": source[:80],
            "old_system": current_system,
            "new_system": correct_system,
        })

        if not dry_run:
            pearl["system"] = correct_system

    if changes and not dry_run:
        save_json_atomic(PEARLS_JSON, pearls)

    print(f"\n    Reclassify Summary:")
    print(f"      Total pearls:            {len(pearls)}")
    print(f"      Already correct:         {already_correct}")
    print(f"      Reclassified:            {len(changes)}")
    print(f"      Unmatched (no summary):  {unmatched}")

    if verbose and changes:
        for c in changes:
            print(f"      [{c['id']}] {c['old_system']} -> {c['new_system']}  | {c['source_paper']}")

    return len(changes)


# =====================================================================
# REPROCESS PEARLS - re-run Pass 2 for failed/missing pearls
# =====================================================================
def build_markdown_for_pearls_from_payload(payload):
    """Build condensed markdown from payload for pearl extraction."""
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


def reprocess_pearls(dry_run=False, verbose=False, max_files=None):
    """Re-run Pass 2 (pearl extraction) for files with failed/missing pearls."""
    print("\n  [REPROCESS-PEARLS] Re-extracting pearls for failed/missing files...")
    max_files = max_files or REPROCESS_PEARL_MAX

    # Identify files needing pearl reprocessing
    errors = read_current_month_errors()
    pearl_failures = [e for e in errors if e.get("stage") == "pearl_extraction"]

    # Count failures per file
    failure_counts = Counter(e.get("file", "") for e in pearl_failures)
    files_to_reprocess = [f for f, c in failure_counts.items() if f and f.endswith(".json")]

    # Also check files with no pearls in pearls.json
    existing_pearls = load_json_safe(PEARLS_JSON, [])
    files_with_pearls = set(p.get("file_name", "") for p in existing_pearls)

    # Scan output_files/ for JSONs not in pearls set
    disk = build_disk_index()
    for pdf_name, (fpath, payload) in disk.items():
        json_name = pdf_name.replace(".pdf", ".json")
        if json_name not in files_with_pearls and json_name not in files_to_reprocess:
            files_to_reprocess.append(json_name)

    # Limit
    files_to_reprocess = files_to_reprocess[:max_files]

    print(f"    Files with pearl failures in error log: {sum(1 for f in files_to_reprocess if f in failure_counts)}")
    print(f"    Files with no pearls in pearls.json: {sum(1 for f in files_to_reprocess if f not in failure_counts)}")
    print(f"    Total to reprocess: {len(files_to_reprocess)} (max={max_files})")

    if not files_to_reprocess:
        print("    No files need pearl reprocessing.")
        return 0

    if dry_run:
        for f in files_to_reprocess:
            print(f"    [would reprocess] {f}")
        return len(files_to_reprocess)

    reprocessed = 0
    total_pearls_added = 0

    for json_name in files_to_reprocess:
        # Find the JSON file on disk
        json_path = None
        for pdf_name, (fpath, payload) in disk.items():
            if pdf_name.replace(".pdf", ".json") == json_name:
                json_path = fpath
                break

        if not json_path or not os.path.exists(json_path):
            print(f"    [skip] JSON not found: {json_name}")
            continue

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as e:
            print(f"    [skip] Failed to load {json_name}: {e}")
            continue

        markdown_text = build_markdown_for_pearls_from_payload(payload)
        if not markdown_text or len(markdown_text) < 50:
            print(f"    [skip] {json_name} - insufficient content")
            continue

        metadata = {
            "doi": payload.get("doi", ""),
            "authors": payload.get("authors", ""),
            "system": payload.get("specialty", [""])[0] if isinstance(payload.get("specialty"), list) else payload.get("system", ""),
            "type": payload.get("article_subtype", payload.get("doc_type", "")),
        }

        source_paper = payload.get("title", json_name)
        print(f"    [{reprocessed + 1}] Re-extracting pearls: {source_paper[:60]}")

        try:
            pearls = execute_pearl_extraction(markdown_text, json_name)
            if pearls:
                # Remove existing pearls for this file first
                existing = load_json_safe(PEARLS_JSON, [])
                existing = [p for p in existing if p.get("file_name") != json_name]
                save_json_atomic(PEARLS_JSON, existing)

                # Append new pearls
                next_id = 1
                if existing:
                    all_ids = []
                    for r in existing:
                        try:
                            all_ids.append(int(r.get("id", 0)))
                        except (ValueError, TypeError):
                            pass
                    next_id = (max(all_ids) + 1) if all_ids else 1

                now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                rows_to_add = []
                for p in pearls[:25]:
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
                        "doi": metadata["doi"],
                        "author": metadata["authors"],
                        "system": metadata["system"],
                        "type": metadata["type"],
                        "pearl": text[:500],
                        "remarks": "",
                        "file_name": json_name,
                        "topic": topic,
                    })
                    next_id += 1

                all_rows = existing + rows_to_add
                save_json_atomic(PEARLS_JSON, all_rows)
                update_pearl_tracker(PEARLS_TRACKER, json_name, len(rows_to_add), "maintainer")
                total_pearls_added += len(rows_to_add)
                print(f"      OK - {len(rows_to_add)} pearls saved")
            else:
                print(f"      No pearls extracted")
        except Exception as e:
            print(f"      [X] Failed: {e}")
            write_error(file_name=json_name, stage="pearl_extraction", pass_number=2, error=e, action="log_only")

        reprocessed += 1

    print(f"\n    Reprocess Pearls Summary:")
    print(f"      Files reprocessed:  {reprocessed}")
    print(f"      Total pearls added: {total_pearls_added}")

    return reprocessed


# =====================================================================
# ERROR PRIORITY REPORT
# =====================================================================
def error_priority_report(full_scan=False, verbose=False, since_date=None):
    """
    Read master_error_list files and display prioritized action plan.
    Reads current month only, unless full_scan=True.
    If since_date is provided, only errors on or after that date are included.
    """
    print("\n  [ERROR-PRIORITY] Analyzing master_error_list...")
    if since_date:
        errors = read_all_errors()
        errors = [e for e in errors if e.get("timestamp") and _is_on_or_after(e["timestamp"], since_date)]
        print(f"    Filtered from ALL monthly logs (since {since_date})")
    elif full_scan:
        errors = read_all_errors()
        print(f"    Reading ALL monthly error lists ({len(get_all_error_list_paths())} files)")
    else:
        errors = read_current_month_errors()
        print(f"    Reading current month: {os.path.basename(get_error_list_path())}")

    if not errors:
        print("    No errors found. System healthy.")
        return {"total": 0, "by_priority": {}, "by_type": {}, "repeated_failures": [], "action_plan": []}

    # Group by priority
    by_priority = Counter(e.get("priority", "LOW") for e in errors)
    by_type = Counter(e.get("error_type", "UNKNOWN") for e in errors)
    by_stage = Counter(e.get("stage", "unknown") for e in errors)

    # Count failures per file
    file_failures = defaultdict(list)
    for e in errors:
        file_failures[e.get("file", "")].append(e)

    # Identify repeated failures (>= threshold)
    repeated = []
    for fname, errs in file_failures.items():
        if len(errs) >= REPEATED_FAILURE_THRESHOLD and fname:
            repeated.append({
                "file": fname,
                "failure_count": len(errs),
                "error_types": list(set(e.get("error_type", "") for e in errs)),
                "last_error": errs[-1].get("message", "")[:100],
                "priority": "HIGH",
            })

    repeated.sort(key=lambda x: x["failure_count"], reverse=True)

    # Build action plan
    action_plan = []

    # CRITICAL: quota exhaustion
    critical = [e for e in errors if e.get("priority") == "CRITICAL"]
    if critical:
        action_plan.append({
            "priority": "CRITICAL",
            "action": "Check API keys and quota - generation likely blocked",
            "count": len(critical),
            "files": list(set(e.get("file", "") for e in critical))[:5],
        })

    # HIGH: repeated failures
    if repeated:
        action_plan.append({
            "priority": "HIGH",
            "action": f"Reprocess {len(repeated)} files with repeated failures (>= {REPEATED_FAILURE_THRESHOLD}x)",
            "files": [r["file"] for r in repeated[:10]],
        })

    # HIGH: pearl extraction failures
    pearl_fails = [e for e in errors if e.get("stage") == "pearl_extraction"]
    if pearl_fails:
        action_plan.append({
            "priority": "MEDIUM",
            "action": f"Re-run pearl extraction for {len(set(e.get('file', '') for e in pearl_fails))} files",
            "command": "python maintainer.py --reprocess-pearls",
        })

    # MEDIUM: schema violations
    schema_issues = [e for e in errors if e.get("error_type") == "SCHEMA_VIOLATION"]
    if schema_issues:
        action_plan.append({
            "priority": "MEDIUM",
            "action": f"Auto-fix {len(schema_issues)} schema violations",
            "command": "python maintainer.py --repair",
        })

    # Print report
    print(f"\n    Error Priority Report:")
    print(f"      Total errors:        {len(errors)}")
    print(f"      By priority:")
    for p in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        if by_priority.get(p, 0) > 0:
            print(f"        {p:10s}: {by_priority[p]}")
    print(f"      By type (top 5):")
    for et, cnt in by_type.most_common(5):
        print(f"        {et:25s}: {cnt}")
    print(f"      By stage:")
    for st, cnt in by_stage.most_common():
        print(f"        {st:25s}: {cnt}")

    if repeated:
        print(f"\n      Repeated failures (>= {REPEATED_FAILURE_THRESHOLD}x):")
        for r in repeated[:10]:
            print(f"        [{r['failure_count']}x] {r['file']}")
            print(f"               types: {', '.join(r['error_types'])}")
            print(f"               last:  {r['last_error']}")

    if action_plan:
        print(f"\n      ACTION PLAN:")
        for ap in action_plan:
            print(f"        [{ap['priority']}] {ap['action']}")
            if "command" in ap:
                print(f"               -> {ap['command']}")
            if "files" in ap:
                for f in ap["files"][:3]:
                    print(f"               - {f}")

    return {
        "total": len(errors),
        "by_priority": dict(by_priority),
        "by_type": dict(by_type),
        "by_stage": dict(by_stage),
        "repeated_failures": repeated,
        "action_plan": action_plan,
    }


# =====================================================================
# HEALTH REPORT GENERATION
# =====================================================================
def generate_health_report(full_scan=False, verbose=False, since_date=None):
    """Generate health_report.json + health_report.md."""
    print("\n  [HEALTH-REPORT] Generating health report...")

    # Collect data
    if since_date:
        errors = read_all_errors()
        errors = [e for e in errors if e.get("timestamp") and _is_on_or_after(e["timestamp"], since_date)]
    elif full_scan:
        errors = read_all_errors()
    else:
        errors = read_current_month_errors()

    # Count files on disk
    disk = build_disk_index()
    total_files = len(disk)

    # Count by system and type (from directory structure)
    by_system = Counter()
    by_type = Counter()
    for pdf_name, (fpath, _) in disk.items():
        parts = fpath.replace("\\", "/").rstrip("/").split("/")
        if len(parts) >= 3:
            by_system[parts[-3]] += 1
            by_type[parts[-2]] += 1

    # Count pearls
    pearls = load_json_safe(PEARLS_JSON, [])
    pearl_count = len(pearls)
    pearl_by_system = Counter(p.get("system", "") for p in pearls if p.get("system"))

    # Error stats
    now = datetime.now()
    errors_7d = [e for e in errors if _is_within_days(e.get("timestamp", ""), 7)]
    errors_30d = [e for e in errors if _is_within_days(e.get("timestamp", ""), 30)]
    errors_by_type = Counter(e.get("error_type", "UNKNOWN") for e in errors)

    # Check API key status
    from acumen_core.config import TOGETHER_API_KEY, DEEPSEEK_API_KEY, PRIMARY_GEMINI_API_KEY
    api_status = {
        "together": "ok" if TOGETHER_API_KEY else "missing_key",
        "deepseek": "ok" if DEEPSEEK_API_KEY else "missing_key",
        "gemini": "ok" if PRIMARY_GEMINI_API_KEY else "missing_key",
    }

    # Check for quota errors
    quota_errors = [e for e in errors if e.get("error_type") == "QUOTA_EXHAUSTED"]
    if quota_errors:
        # Check recency (last 24h)
        recent_quota = [e for e in quota_errors if _is_within_days(e.get("timestamp", ""), 1)]
        if recent_quota:
            api_status["gemini"] = "quota_exhausted"

    # Quarantine stats
    quarantine_count = 0
    if os.path.exists(os.path.join(os.path.dirname(OUTPUT_DIR), "quarantine")):
        for root, dirs, files in os.walk(os.path.join(os.path.dirname(OUTPUT_DIR), "quarantine")):
            quarantine_count += sum(1 for f in files if f.endswith(".pdf"))

    # Build JSON report
    report = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total_json_files": total_files,
            "total_pearls": pearl_count,
            "quarantined_pdfs": quarantine_count,
        },
        "by_system": dict(by_system),
        "by_type": dict(by_type),
        "pearls_by_system": dict(pearl_by_system),
        "errors": {
            "total": len(errors),
            "last_7_days": len(errors_7d),
            "last_30_days": len(errors_30d),
            "by_type": dict(errors_by_type),
        },
        "api_status": api_status,
        "error_list_files": [os.path.basename(p) for p in get_all_error_list_paths()],
    }

    # Save JSON report
    save_json_atomic(HEALTH_REPORT_JSON, report)
    print(f"    Saved: {os.path.basename(HEALTH_REPORT_JSON)}")

    # Generate Markdown report
    md = _generate_markdown_report(report)
    with open(HEALTH_REPORT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"    Saved: {os.path.basename(HEALTH_REPORT_MD)}")

    if verbose:
        print(f"\n    Health Report Summary:")
        print(f"      Total JSON files:     {total_files}")
        print(f"      Total pearls:         {pearl_count}")
        print(f"      Quarantined PDFs:     {quarantine_count}")
        print(f"      Errors (7d / 30d):    {len(errors_7d)} / {len(errors_30d)}")
        print(f"      API status:           {api_status}")

    return report


def _is_within_days(timestamp_str, days):
    """Check if ISO timestamp is within N days of now."""
    if not timestamp_str:
        return False
    try:
        ts = datetime.fromisoformat(timestamp_str)
        return (datetime.now() - ts).days <= days
    except Exception:
        return False


def _is_on_or_after(timestamp_str, cutoff_date):
    """Check if ISO timestamp is on or after a given date."""
    if not timestamp_str:
        return False
    try:
        ts = datetime.fromisoformat(timestamp_str)
        return ts.date() >= cutoff_date
    except Exception:
        return False


def _generate_markdown_report(report):
    """Generate Markdown string from health report data."""
    lines = []
    lines.append(f"# hack.CCM Repository Health Report")
    lines.append(f"")
    lines.append(f"**Generated:** {report['timestamp']}")
    lines.append(f"")
    lines.append(f"## Summary")
    lines.append(f"")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total JSON Files | {report['summary']['total_json_files']} |")
    lines.append(f"| Total Pearls | {report['summary']['total_pearls']} |")
    lines.append(f"| Quarantined PDFs | {report['summary']['quarantined_pdfs']} |")
    lines.append(f"| Errors (Total) | {report['errors']['total']} |")
    lines.append(f"| Errors (Last 7 days) | {report['errors']['last_7_days']} |")
    lines.append(f"| Errors (Last 30 days) | {report['errors']['last_30_days']} |")
    lines.append(f"")
    lines.append(f"## Files by System")
    lines.append(f"")
    lines.append(f"| System | Count |")
    lines.append(f"|--------|-------|")
    for sys_name, cnt in sorted(report["by_system"].items(), key=lambda x: -x[1]):
        lines.append(f"| {sys_name} | {cnt} |")
    lines.append(f"")
    lines.append(f"## Files by Type")
    lines.append(f"")
    lines.append(f"| Type | Count |")
    lines.append(f"|------|-------|")
    for t, cnt in sorted(report["by_type"].items(), key=lambda x: -x[1]):
        lines.append(f"| {t} | {cnt} |")
    lines.append(f"")
    lines.append(f"## Pearls by System")
    lines.append(f"")
    lines.append(f"| System | Pearl Count |")
    lines.append(f"|--------|-------------|")
    for sys_name, cnt in sorted(report["pearls_by_system"].items(), key=lambda x: -x[1]):
        lines.append(f"| {sys_name} | {cnt} |")
    lines.append(f"")
    lines.append(f"## Error Breakdown")
    lines.append(f"")
    if report["errors"]["by_type"]:
        lines.append(f"| Error Type | Count |")
        lines.append(f"|------------|-------|")
        for et, cnt in sorted(report["errors"]["by_type"].items(), key=lambda x: -x[1]):
            lines.append(f"| {et} | {cnt} |")
    else:
        lines.append(f"No errors recorded.")
    lines.append(f"")
    lines.append(f"## API Status")
    lines.append(f"")
    lines.append(f"| Provider | Status |")
    lines.append(f"|----------|--------|")
    for prov, status in report["api_status"].items():
        icon = "OK" if status == "ok" else "WARNING"
        lines.append(f"| {prov} | {icon} ({status}) |")
    lines.append(f"")
    lines.append(f"## Error List Files")
    lines.append(f"")
    for f in report["error_list_files"]:
        lines.append(f"- `{f}`")
    if not report["error_list_files"]:
        lines.append(f"- (none yet)")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"*Generated by maintainer.py*")
    return "\n".join(lines)


# =====================================================================
# RESET PEARLS - remove and re-extract pearls for a specific JSON file
# =====================================================================
def reset_pearls_for_file(json_path, dry_run=False, verbose=False):
    """
    Remove all pearls belonging to a specific JSON file from pearls.json,
    then re-run Pass 2 to extract fresh pearls.
    """
    print(f"\n  [RESET-PEARLS] Resetting pearls for: {json_path}")
    json_name = os.path.basename(json_path)

    # 1. Load current pearls
    all_pearls = load_json_safe(PEARLS_JSON, [])
    before_count = len(all_pearls)

    # 2. Remove pearls belonging to this file
    kept = [p for p in all_pearls if p.get("file") != json_name]
    removed = before_count - len(kept)
    if removed == 0:
        print(f"    No existing pearls found for {json_name}")
    else:
        print(f"    Removed {removed} existing pearls for {json_name}")

    if not dry_run:
        # 3. Save backup
        backup_path = PEARLS_JSON + ".reset_backup"
        if RESET_PEARL_BACKUP_BEFORE and not os.path.exists(backup_path):
            save_json_atomic(backup_path, all_pearls)
            print(f"    Backup saved to: {os.path.basename(backup_path)}")
        # 4. Save cleaned pearls.json
        save_json_atomic(PEARLS_JSON, kept)
        # 5. Reset the pearl tracker entry so generator knows to re-process
        update_pearl_tracker(PEARLS_TRACKER, json_name, 0, "maintainer-reset")
        print(f"    Pearl tracker reset for {json_name}")

    # 6. Re-run pearl extraction
    if not os.path.exists(json_path):
        print(f"    [X] JSON file not found: {json_path}")
        return 0

    with open(json_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    pdf_name = payload.get("file_name") or payload.get("pdf_filename") or json_name.replace(".json", ".pdf")
    abstract = payload.get("abstract") or payload.get("summary") or ""
    full_text = payload.get("full_text") or payload.get("text") or ""

    if not abstract and not full_text:
        print(f"    [X] No text content in {json_name} to extract pearls from")
        return 0

    if verbose:
        print(f"    Extracting pearls from {len(full_text or abstract)} chars of text...")

    if not dry_run:
        try:
            result = execute_pearl_extraction(
                text=full_text or abstract,
                abstract=abstract,
                payload=payload,
                verbose=verbose,
            )
            new_pearls_raw = result if isinstance(result, list) else []
            # Re-attach file/system info
            new_pearls = []
            for p in new_pearls_raw:
                p["file"] = json_name
                p["system"] = payload.get("specialty", [""])[0] if isinstance(payload.get("specialty"), list) else payload.get("system", "")
                new_pearls.append(p)

            if new_pearls:
                current_all = load_json_safe(PEARLS_JSON, [])
                current_all.extend(new_pearls)
                save_json_atomic(PEARLS_JSON, current_all)
                update_pearl_tracker(PEARLS_TRACKER, json_name, len(new_pearls), "maintainer-reset")
                print(f"    Extracted {len(new_pearls)} new pearls")
            else:
                print(f"    No pearls extracted")
                update_pearl_tracker(PEARLS_TRACKER, json_name, 0, "maintainer-reset")
        except Exception as e:
            print(f"    [X] Re-extraction failed: {e}")

    return removed


# =====================================================================
# AUTO-FIX - run all maintenance operations
# =====================================================================
def auto_fix(dry_run=False, verbose=False, full_scan=False, since_date=None):
    """Run reconcile + validate + repair + reprocess-pearls in sequence."""
    print("\n  [AUTO-FIX] Running full maintenance sequence...")
    print("  " + "=" * 50)

    results = {}

    # 1. Error priority (read-only, informs what to fix)
    error_report = error_priority_report(full_scan=full_scan, verbose=verbose, since_date=since_date)
    results["error_priority"] = error_report

    # 2. Reconcile
    results["reconcile"] = reconcile(dry_run=dry_run, verbose=verbose)

    # 3. Validate
    results["validation"] = validate_all(dry_run=dry_run, verbose=verbose)

    # 4. Repair
    results["repair"] = repair_all(dry_run=dry_run, verbose=verbose)

    # 5. Reclassify pearls
    results["reclassify"] = reclassify_pearls(dry_run=dry_run, verbose=verbose)

    # 6. Reprocess pearls (only if there are failures)
    if error_report.get("action_plan"):
        has_pearl_action = any("pearl" in ap.get("action", "").lower() for ap in error_report["action_plan"])
        if has_pearl_action:
            results["reprocess_pearls"] = reprocess_pearls(dry_run=dry_run, verbose=verbose)

    # 7. Generate health report
    results["health_report"] = generate_health_report(full_scan=full_scan, verbose=verbose, since_date=since_date)

    print("\n  " + "=" * 50)
    print("  [AUTO-FIX] Complete!\n")

    return results


# =====================================================================
# MAIN ENTRY POINT
# =====================================================================
def main():
    parser = argparse.ArgumentParser(
        description="hack.CCM Repository Maintenance & Health Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python maintainer.py                       # Generate health report (default)
  python maintainer.py --reconcile             # Sync disk <-> sent_summaries.json
  python maintainer.py --validate              # Schema-check all JSONs
  python maintainer.py --repair                # Auto-fix safe issues
  python maintainer.py --reclassify             # Fix pearl systems from summaries
  python maintainer.py --reprocess-pearls       # Re-run Pass 2 for failed pearls
  python maintainer.py --error-priority          # Show prioritized error list
  python maintainer.py --auto-fix                # Run all fixes in sequence
  python maintainer.py --full-scan               # Include all monthly error logs
  python maintainer.py --dry-run                 # Preview only, no writes
  python maintainer.py --verbose                  # Detailed per-file logging
  python maintainer.py --report-only               # Health report only, no fixes
  python maintainer.py --reset-pearls FILE        # Remove & re-extract pearls for a file
  python maintainer.py --since YYYY-MM-DD         # Filter errors/reports since a date
  python maintainer.py --error-priority --since 2026-06-01  # Errors since June 1
        """,
    )
    parser.add_argument("--reconcile", action="store_true", help="Sync disk <-> sent_summaries.json")
    parser.add_argument("--validate", action="store_true", help="Schema-check all JSONs")
    parser.add_argument("--repair", action="store_true", help="Auto-fix safe issues")
    parser.add_argument("--reclassify", action="store_true", help="Fix pearl systems from summaries")
    parser.add_argument("--reprocess-pearls", action="store_true", help="Re-run Pass 2 for failed/missing pearls")
    parser.add_argument("--error-priority", action="store_true", help="Show prioritized error list")
    parser.add_argument("--auto-fix", action="store_true", help="Run reconcile + validate + repair + reprocess-pearls")
    parser.add_argument("--full-scan", action="store_true", help="Include all monthly error logs (not just current)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes")
    parser.add_argument("--verbose", action="store_true", help="Detailed per-file logging")
    parser.add_argument("--report-only", action="store_true", help="Generate health report, no fixes")
    parser.add_argument("--reset-pearls", type=str, metavar="FILE", help="Remove & re-extract pearls for a JSON file")
    parser.add_argument("--since", type=str, metavar="YYYY-MM-DD", help="Filter errors/reports since a specific date")
    args = parser.parse_args()

    # Parse --since date if provided
    since_date = None
    if args.since:
        try:
            since_date = datetime.strptime(args.since, "%Y-%m-%d").date()
        except ValueError:
            print(f"  [X] Invalid --since date format: {args.since}. Use YYYY-MM-DD.")
            sys.exit(1)

    # --- Mode: Reset pearls ---
    if args.reset_pearls:
        reset_pearls_for_file(args.reset_pearls, dry_run=args.dry_run, verbose=args.verbose)
        return

    # --- Mode: Auto-fix (run everything) ---
    if args.auto_fix:
        auto_fix(dry_run=args.dry_run, verbose=args.verbose, full_scan=args.full_scan, since_date=since_date)
        return

    # --- Mode: Error priority ---
    if args.error_priority:
        error_priority_report(full_scan=args.full_scan, verbose=args.verbose, since_date=since_date)
        return

    # --- Mode: Reconcile ---
    if args.reconcile:
        reconcile(dry_run=args.dry_run, verbose=args.verbose)

    # --- Mode: Validate ---
    if args.validate:
        validate_all(dry_run=args.dry_run, verbose=args.verbose)

    # --- Mode: Repair ---
    if args.repair:
        repair_all(dry_run=args.dry_run, verbose=args.verbose)

    # --- Mode: Reclassify ---
    if args.reclassify:
        reclassify_pearls(dry_run=args.dry_run, verbose=args.verbose)

    # --- Mode: Reprocess pearls ---
    if args.reprocess_pearls:
        reprocess_pearls(dry_run=args.dry_run, verbose=args.verbose)

    # --- Default / Report-only: Generate health report ---
    no_action = not any([args.reconcile, args.validate, args.repair, args.reclassify,
                         args.reprocess_pearls, args.error_priority, args.auto_fix,
                         args.reset_pearls])
    if no_action or args.report_only:
        generate_health_report(full_scan=args.full_scan, verbose=args.verbose, since_date=since_date)


if __name__ == "__main__":
    main()
