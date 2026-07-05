#!/usr/bin/env python3
"""
json_repo_updater.py — Reconcile sent_summaries.json with output_files/ on disk.

Scans output_files/ for all .json files, cross-references against
sent_summaries.json, adds missing entries, removes stale ones, and
logs removed entries to sent_summaries_removed.json.

Usage:
    python json_repo_updater.py              # normal run
    python json_repo_updater.py --dry-run     # preview only, no writes
    python json_repo_updater.py --verbose     # detailed per-file logging
"""

import os
import json
import sys
import argparse
from datetime import datetime

OUTPUT_DIR = "./output_files"
JSON_TRACKER_FILE = "./sent_summaries.json"
REMOVED_TRACKER_FILE = "./sent_summaries_removed.json"
SPECIALTIES_FILE = "./specialties.txt"
ARTICLE_TYPES_FILE = "./article_types.txt"

DEFAULT_SPECIALTIES = ["Critical Care Medicine", "Cardiovascular", "Neurology", "Nephrology", "Pulmonology", "Other"]
DEFAULT_TYPES = ["Guideline", "Review", "Meta-Analysis", "Trial", "Other"]


def load_allowed_vocabulary(file_path, default_list):
    if not os.path.exists(file_path):
        return default_list
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def build_specialty_map(allowed):
    m = {s.lower(): s for s in allowed}
    m.update({
        "infectious_disease": m.get("infectious diseases", "Infectious Diseases"),
        "multi_system": m.get("multisystem", "Multisystem"),
        "multisystem": m.get("multisystem", "Multisystem"),
        "obstetrics_and_gynecology": m.get("obstetrics and gynecology", "Obstetrics and Gynecology"),
        "cardio": m.get("cardiology", "Cardiology"),
        "neuro": m.get("neurology", "Neurology"),
        "nephro": m.get("nephrology", "Nephrology"),
        "pulmo": m.get("pulmonology", "Pulmonology"),
        "gi": m.get("gastroenterology", "Gastroenterology"),
        "heme": m.get("hematology", "Hematology"),
        "onc": m.get("oncology", "Oncology"),
    })
    return m


def normalize_specialty(specialty_list, spec_map):
    if not isinstance(specialty_list, list) or not specialty_list:
        return "Other"
    raw = str(specialty_list[0]).strip().lower().replace("_", " ").replace("-", " ")
    mapped = spec_map.get(raw, "Other")
    if mapped == "Other":
        raw_orig = str(specialty_list[0]).strip().lower()
        mapped = spec_map.get(raw_orig, "Other")
    return "".join(x for x in str(mapped) if x.isalnum() or x in "._- ").strip()


def _atomic_write_json(file_path, data):
    tmp = file_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, file_path)


def extract_metadata(payload):
    """Extract title/system/type/journal/authors/doi/year from old or new format."""
    title = payload.get("paper_name") or payload.get("title", "")
    system = payload.get("system", "")
    if not system and payload.get("specialty"):
        spec_map = build_specialty_map(load_allowed_vocabulary(SPECIALTIES_FILE, DEFAULT_SPECIALTIES))
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


def build_disk_index(verbose=False):
    """Walk output_files/ and return dict mapping file_name → (file_path, payload)."""
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
            # file_name = PDF filename (strip .json → .pdf convention)
            base = os.path.splitext(fname)[0]
            pdf_name = base + ".pdf"
            if pdf_name in disk:
                if verbose:
                    print(f"    [warn] Duplicate basename '{pdf_name}' → {fpath} (keeping first)")
                continue
            disk[pdf_name] = (fpath, payload)
    return disk


def load_repo():
    if not os.path.exists(JSON_TRACKER_FILE):
        return []
    try:
        with open(JSON_TRACKER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return []


def load_removed():
    if not os.path.exists(REMOVED_TRACKER_FILE):
        return []
    try:
        with open(REMOVED_TRACKER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return []


def entry_from_payload(file_name, payload, fpath=None):
    """Build a sent_summaries.json entry from a JSON payload on disk.
    Uses the directory path (output_files/{system}/{type}/...) as ground truth
    for system and type when fpath is provided.
    """
    title, system, article_type, journal, authors, doi, year = extract_metadata(payload)
    if fpath:
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
        "parsing_notes": "Added by json_repo_updater",
        "show_on_web": "No",
    }


def main():
    parser = argparse.ArgumentParser(description="Reconcile sent_summaries.json with output_files/")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--verbose", action="store_true", help="Detailed per-file logging")
    args = parser.parse_args()

    print(f"Scanning {OUTPUT_DIR}/...")
    disk = build_disk_index(args.verbose)
    print(f"  Found {len(disk)} .json files on disk")

    repo = load_repo()
    print(f"  Loaded {len(repo)} entries from {JSON_TRACKER_FILE}")

    repo_by_file = {e["file_name"]: e for e in repo if e.get("file_name")}

    # Phase A: ADD — entries on disk not in repo
    to_add = []
    for file_name, (fpath, payload) in disk.items():
        if file_name not in repo_by_file:
            entry = entry_from_payload(file_name, payload, fpath)
            to_add.append(entry)
            if args.verbose:
                print(f"  [add] {file_name} -> {entry['title'][:60]}")

    # Phase B: REMOVE — entries in repo but missing from disk
    to_remove = []
    kept = []
    updated_count = 0
    for entry in repo:
        fname = entry.get("file_name", "")
        if fname and fname not in disk:
            to_remove.append(entry)
            if args.verbose:
                print(f"  [remove] {fname} -> {entry.get('title', '')[:60]}")
            continue

        # Phase C: NORMALIZE — use directory path as ground truth for system/type
        if fname and fname in disk:
            fpath, _ = disk[fname]
            parts = fpath.replace("\\", "/").rstrip("/").split("/")
            if len(parts) >= 3:
                path_system = parts[-3]
                if path_system and path_system != "output_files" and path_system != entry.get("system", ""):
                    old_system = entry["system"]
                    entry["system"] = path_system
                    updated_count += 1
                    if args.verbose:
                        print(f"  [update] {fname}: system \"{old_system}\" -> \"{path_system}\"")
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

    print(f"\nSummary:")
    print(f"  Added:   {len(to_add)}")
    print(f"  Removed: {len(to_remove)}")
    print(f"  Updated: {updated_count}")
    print(f"  Kept:    {len(kept)}")
    print(f"  Total:   {len(new_repo)}")

    if args.dry_run:
        print("\n[Dry-run] No files written.")
        if to_remove:
            print(f"  Would log {len(to_remove)} removed entries to {REMOVED_TRACKER_FILE}")
        return

    # Write updated repo
    _atomic_write_json(JSON_TRACKER_FILE, new_repo)
    print(f"\n  Wrote {len(new_repo)} entries to {JSON_TRACKER_FILE}")

    # Append removed entries to removed tracker
    if to_remove:
        removed = load_removed()
        for entry in to_remove:
            entry["removed_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            removed.append(entry)
        _atomic_write_json(REMOVED_TRACKER_FILE, removed)
        print(f"  Logged {len(to_remove)} removed entries to {REMOVED_TRACKER_FILE}")


if __name__ == "__main__":
    main()
