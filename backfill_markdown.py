#!/usr/bin/env python3
"""
backfill_markdown.py — Apply markdown emphasis (bold numbers/units/keywords)
to all existing JSON files in output_files/ that were saved before enrichment.

Usage:
    python backfill_markdown.py              # normal run
    python backfill_markdown.py --dry-run     # preview only
    python backfill_markdown.py --verbose     # per-file logging
"""

import os
import json
import argparse
from copy import deepcopy

# Reuse the enrichment logic from the ingestion engine
from master_app_together import enrich_payload_with_markdown

OUTPUT_DIR = "./output_files"


def _atomic_write_json(file_path, data):
    tmp = file_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, file_path)


def main():
    parser = argparse.ArgumentParser(
        description="Backfill markdown emphasis on existing JSON files"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--verbose", action="store_true", help="Per-file logging")
    args = parser.parse_args()

    if not os.path.exists(OUTPUT_DIR):
        print(f"Output directory not found: {OUTPUT_DIR}")
        return

    total = 0
    updated = 0
    skipped = 0
    errors = 0

    for root, dirs, files in os.walk(OUTPUT_DIR):
        for fname in files:
            if not fname.endswith(".json"):
                continue
            total += 1
            fpath = os.path.join(root, fname)

            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    payload = json.load(f)
            except (json.JSONDecodeError, Exception) as e:
                if args.verbose:
                    safe = fpath.encode('ascii', 'replace').decode('ascii')
                    print(f"  [skip] Invalid JSON: {safe} ({e})")
                skipped += 1
                continue

            original = json.dumps(payload, sort_keys=True)
            enriched = enrich_payload_with_markdown(deepcopy(payload))
            after = json.dumps(enriched, sort_keys=True)

            if original == after:
                skipped += 1
                if args.verbose:
                    safe = fpath.encode('ascii', 'replace').decode('ascii')
                    print(f"  [skip] No change: {safe}")
                continue

            updated += 1
            if args.verbose:
                safe = fpath.encode('ascii', 'replace').decode('ascii')
                print(f"  [update] {safe}")

            if not args.dry_run:
                _atomic_write_json(fpath, enriched)

    print(f"\nSummary:")
    print(f"  Total:   {total}")
    print(f"  Updated: {updated}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors:  {errors}")

    if args.dry_run:
        print("\n[Dry-run] No files written.")


if __name__ == "__main__":
    main()
