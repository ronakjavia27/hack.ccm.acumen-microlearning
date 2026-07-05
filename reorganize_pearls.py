#!/usr/bin/env python3
"""
reorganize_pearls.py — Reclassify pearl systems by cross-referencing sent_summaries.

Reads pearls.json and sent_summaries.json, matches pearls to their source
paper title in sent_summaries, and updates the pearl's system field to match
the system assigned in sent_summaries.

Usage:
    python reorganize_pearls.py
    python reorganize_pearls.py --dry-run
    python reorganize_pearls.py --verbose
"""

import os
import sys
import json
import argparse
import unicodedata
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
PEARLS_FILE = SCRIPT_DIR / "pearls.json"
SUMMARIES_FILE = SCRIPT_DIR / "sent_summaries.json"


def normalize_title(s):
    """Normalize title for matching: lowercase, normalize unicode, strip."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.replace("\u2013", "-").replace("\u2014", "--")
    s = s.replace("\u2018", "'").replace("\u2019", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    return s.strip().lower()


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, str(path))


def main():
    parser = argparse.ArgumentParser(
        description="Reclassify pearl systems by cross-referencing sent_summaries"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without modifying pearls.json")
    parser.add_argument("--verbose", action="store_true",
                        help="List every unmatched pearl")
    args = parser.parse_args()

    # Load data
    pearls = load_json(PEARLS_FILE)
    summaries = load_json(SUMMARIES_FILE)

    print(f"Loaded {len(pearls)} pearls from {PEARLS_FILE.name}")
    print(f"Loaded {len(summaries)} entries from {SUMMARIES_FILE.name}")

    # Build lookup: normalized title -> (original title, system)
    lookup = {}
    for s in summaries:
        title = s.get("title", "").strip()
        system = s.get("system", "").strip()
        if not title or not system:
            continue
        key = normalize_title(title)
        if key not in lookup:
            lookup[key] = (title, system)

    print(f"Built lookup with {len(lookup)} titles\n")

    changes = []
    already_correct = 0
    unmatched = []
    errors = 0

    for pearl in pearls:
        source = pearl.get("source_paper", "").strip()
        if not source:
            errors += 1
            continue

        key = normalize_title(source)
        match = lookup.get(key)

        if not match:
            unmatched.append(source)
            continue

        _, correct_system = match
        current_system = pearl.get("system", "").strip()

        if current_system == correct_system:
            already_correct += 1
            continue

        changes.append({
            "id": pearl["id"],
            "source_paper": source[:80],
            "old_system": current_system,
            "new_system": correct_system,
        })

        if not args.dry_run:
            pearl["system"] = correct_system

    # Save if not dry-run
    if not args.dry_run and changes:
        save_json(PEARLS_FILE, pearls)

    # Summary
    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Total pearls:            {len(pearls)}")
    print(f"  Already correct:         {already_correct}")
    print(f"  Reclassified:            {len(changes)}")
    print(f"  Unmatched (no summary):  {len(unmatched)}")
    print(f"  Errors (empty title):    {errors}")

    if changes:
        print(f"\n  Reclassified pearls:")
        for c in changes:
            print(f"    [{c['id']}] {c['old_system']} -> {c['new_system']}  | {c['source_paper']}")

    if unmatched and args.verbose:
        print(f"\n  Unmatched source papers:")
        for t in sorted(unmatched):
            print(f"    {t}")

    if args.dry_run and changes:
        path_str = str(PEARLS_FILE)
        print(f"\n  Dry run complete — {path_str} not modified")
    elif changes:
        path_str = str(PEARLS_FILE)
        print(f"\n  Saved to {path_str}")


if __name__ == "__main__":
    main()
