#!/usr/bin/env python3
"""
migrate_pearls_to_json.py — One-time migration of pearls.csv → pearls.json.

Reads existing pearls.csv using stdlib csv module and writes pearls.json
using the same atomic pattern (tmp + os.replace).

Usage:
    python migrate_pearls_to_json.py
"""

import os
import csv
import json

PEARLS_CSV = "./pearls.csv"
PEARLS_JSON = "./pearls.json"


def _atomic_write_json(file_path, data):
    tmp = file_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, file_path)


def main():
    if not os.path.exists(PEARLS_CSV):
        print(f"Source not found: {PEARLS_CSV}")
        return

    if os.path.exists(PEARLS_JSON):
        print(f"Target already exists: {PEARLS_JSON} ({len(json.load(open(PEARLS_JSON, encoding='utf-8')))} entries)")
        print("Delete it first to re-migrate, or skip.")
        return

    with open(PEARLS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("No rows found in CSV")
        return

    # Clean NaN floats that pandas might have written
    cleaned = []
    for row in rows:
        clean = {}
        for k, v in row.items():
            if v is None:
                clean[k] = ""
            elif isinstance(v, float) and str(v) == "nan":
                clean[k] = ""
            else:
                clean[k] = str(v) if v is not None else ""
        cleaned.append(clean)

    _atomic_write_json(PEARLS_JSON, cleaned)
    print(f"Migrated {len(cleaned)} pearls from {PEARLS_CSV} to {PEARLS_JSON}")


if __name__ == "__main__":
    main()
