#!/usr/bin/env python3
"""
json_summary_updater.py — Reformat unformatted text in output_files JSONs.

Scans all nested JSON files in output_files/, checks if content fields
(one_line_summary, key_pearls, sections[].content, strengths_limitations,
recommendation_blocks[].narrative, bedside_protocol[].action, etc.) have
proper markdown formatting (bold, italics, underline, bullet lists).

Files already well-formatted (processed by DeepSeek) are SKIPPED.
Poorly formatted fields are sent to Together AI (openai/gpt-oss-120b)
which reformats WITHOUT changing any content — just adding markdown structure.

Usage:
    python json_summary_updater.py                    # normal run
    python json_summary_updater.py --dry-run           # preview only
    python json_summary_updater.py --force             # reprocess all files
    python json_summary_updater.py --limit 5           # max 5 files
    python json_summary_updater.py --model openai/gpt-oss-120b
"""

import os
import json
import re
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Fix stdout encoding for Unicode characters
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

load_dotenv()

OUTPUT_DIR = "./output_files"
CHANGE_LOG = "format_updates_log.txt"
PROCESSED_TRACKER = "format_progress.json"

SYSTEM_PROMPT = """You are a medical text formatting assistant. Your task is to reformat plain/unstructured medical text into clean, scannable markdown WITHOUT changing any clinical content.

Rules:
1. Convert plain paragraph text into structured bullet points where items/findings are listed
2. Bold key clinical terms, numbers, thresholds, drug names, and values using **double asterisks**
3. Use numbered steps (1. 2. 3.) for protocols or sequential actions
4. Add "- " bullet points for lists of findings, criteria, or items
5. Preserve ALL text — do NOT add, remove, or alter any medical facts, words, or numbers
6. Do NOT change the meaning or wording of any sentence
7. Keep the same voice and tense
8. If text already has good structure (bullet points, bold labels, numbering), leave it as-is

Output ONLY the reformatted text, no explanations, no preamble."""

# Fields that contain content and should be checked for formatting
CONTENT_FIELDS = {
    "one_line_summary",
    "key_pearls",
    "section_pearls",
    "content",
    "strengths_limitations",
    "narrative",
    "action",
    "dose",
    "indication",
    "adverse_effects",
}


def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filepath, data):
    tmp = filepath + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, filepath)


def log_change(log_path, entry):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {json.dumps(entry, ensure_ascii=False)}"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_processed(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_processed(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_content_field(path):
    """Check if a dot-path corresponds to a content-bearing field."""
    parts = re.split(r'[\.\[\]]+', path)
    base_key = parts[-1] if parts else ""
    return base_key in CONTENT_FIELDS


def is_well_formatted(text):
    """Check if a text string already has proper markdown formatting."""
    if not text or len(text) < 80:
        return True
    lines = text.split("\n")
    non_empty = sum(1 for l in lines if l.strip())
    if non_empty == 0:
        return True
    bullet_count = sum(1 for l in lines if l.strip().startswith("- ") or l.strip().startswith("* "))
    bold_count = sum(1 for l in lines if "**" in l)
    numbered_count = sum(1 for l in lines if re.match(r"^\s*\d+[.\)]\s", l))
    structured = bullet_count + bold_count + numbered_count
    ratio = structured / non_empty
    return ratio >= 0.15


def collect_text_fields(data, prefix=""):
    """Walk JSON and collect content-bearing text fields with their paths."""
    fields = []
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, str):
                if is_content_field(path) and len(value) > 80:
                    fields.append((path, value))
            else:
                fields.extend(collect_text_fields(value, path))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            path = f"{prefix}[{i}]"
            if isinstance(item, str):
                if is_content_field(path) and len(item) > 80:
                    fields.append((path, item))
            else:
                fields.extend(collect_text_fields(item, path))
    return fields


def set_nested(data, path_str, value):
    """Set value in nested dict using dot-path notation."""
    parts = re.split(r'\.(?![^\[]*\])', path_str)
    current = data
    for i, part in enumerate(parts):
        is_last = i == len(parts) - 1
        if '[' in part and part.endswith(']'):
            key = part[:part.index('[')]
            idx_str = part[part.index('[')+1:part.index(']')]
            try:
                idx = int(idx_str)
            except ValueError:
                return
            if key:
                if isinstance(current, dict):
                    current = current.get(key)
                else:
                    return
            if isinstance(current, list) and 0 <= idx < len(current):
                if is_last:
                    current[idx] = value
                    return
                current = current[idx]
            else:
                return
        else:
            if isinstance(current, dict):
                if is_last:
                    current[part] = value
                    return
                current = current.get(part)
            else:
                return
            if current is None:
                return


def call_together_api(text, api_key, model="openai/gpt-oss-120b"):
    import urllib.request
    import ssl

    url = "https://api.together.xyz/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        "temperature": 0.1,
        "max_tokens": 8192,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    ctx = ssl.create_default_context()
    resp = urllib.request.urlopen(req, context=ctx, timeout=180)
    result = json.loads(resp.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"].strip()


def main():
    parser = argparse.ArgumentParser(description="Reformat unformatted text in output_files JSONs")
    parser.add_argument("--api-key", help="Together API key (defaults to TOGETHER_API_KEY env var)")
    parser.add_argument("--model", default="openai/gpt-oss-120b", help="Together model name")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no changes")
    parser.add_argument("--force", action="store_true", help="Reprocess even well-formatted files")
    parser.add_argument("--limit", type=int, default=None, help="Max files to process")
    parser.add_argument("--verbose", action="store_true", help="Detailed per-field logging")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("TOGETHER_API_KEY")
    if not api_key:
        print("ERROR: Provide --api-key or set TOGETHER_API_KEY in .env")
        return

    if not os.path.isdir(OUTPUT_DIR):
        print(f"ERROR: {OUTPUT_DIR} not found")
        return

    # Collect all JSON files
    json_files = []
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for fname in files:
            if fname.endswith(".json"):
                json_files.append(os.path.join(root, fname))

    print(f"Found {len(json_files)} JSON files in {OUTPUT_DIR}/")

    processed = load_processed(PROCESSED_TRACKER)
    change_log_path = CHANGE_LOG

    stats = {"reformatted": 0, "skipped_formatted": 0, "skipped_processed": 0, "errors": 0, "fields_fixed": 0}
    processed_count = 0

    for filepath in sorted(json_files):
        if args.limit and processed_count >= args.limit:
            break

        relpath = os.path.relpath(filepath, OUTPUT_DIR)

        if not args.force and relpath in processed:
            if args.verbose:
                print(f"  SKIP {relpath} (already processed)")
            stats["skipped_processed"] += 1
            continue

        try:
            data = load_json(filepath)
        except Exception as e:
            print(f"  ERROR {relpath}: failed to load ({e})")
            stats["errors"] += 1
            continue

        all_fields = collect_text_fields(data)
        if not all_fields:
            stats["skipped_formatted"] += 1
            continue

        needs_reformat = []
        for path, text in all_fields:
            if not is_well_formatted(text):
                needs_reformat.append((path, text))

        if not needs_reformat:
            if args.verbose:
                print(f"  SKIP {relpath} (all fields well-formatted)")
            stats["skipped_formatted"] += 1
            processed[relpath] = {
                "status": "skipped_well_formatted",
                "timestamp": datetime.now().isoformat()
            }
            if not args.dry_run:
                save_processed(PROCESSED_TRACKER, processed)
            continue

        print(f"  REFORMAT {relpath} ({len(needs_reformat)} field(s))")

        if args.dry_run:
            for path, text in needs_reformat:
                print(f"    {path} ({len(text)} chars)")
            processed_count += 1
            stats["reformatted"] += 1
            continue

        all_ok = True
        for path, text in needs_reformat:
            if args.verbose:
                print(f"    -> {path} ({len(text)} chars)...", end=" ", flush=True)
            else:
                print(f"    -> {path}...", end=" ", flush=True)

            try:
                reformatted = call_together_api(text, api_key, args.model)
                set_nested(data, path, reformatted)
                print(f"OK ({len(reformatted)} chars)")
                stats["fields_fixed"] += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"ERROR: {e}")
                all_ok = False
                stats["errors"] += 1
                time.sleep(2)
                continue

        data["_format_version"] = "reformatted_via_gpt-oss" if all_ok else "partial_reformat"

        save_json(filepath, data)

        log_change(change_log_path, {
            "file": relpath,
            "action": "reformatted",
            "fields": [p for p, _ in needs_reformat],
            "status": "ok" if all_ok else "partial",
            "timestamp": datetime.now().isoformat()
        })

        processed[relpath] = {
            "status": "reformatted" if all_ok else "partial",
            "fields_processed": len(needs_reformat),
            "timestamp": datetime.now().isoformat()
        }
        save_processed(PROCESSED_TRACKER, processed)

        stats["reformatted"] += 1
        processed_count += 1

    print()
    print("=" * 50)
    print("  Summary")
    print("=" * 50)
    print(f"  Reformatted:           {stats['reformatted']}")
    print(f"  Skipped (formatted):   {stats['skipped_formatted']}")
    print(f"  Skipped (processed):   {stats['skipped_processed']}")
    print(f"  Errors:                {stats['errors']}")
    print(f"  Total fields fixed:    {stats['fields_fixed']}")
    print(f"  Change log:            {change_log_path}")
    print(f"  Progress tracker:      {PROCESSED_TRACKER}")


if __name__ == "__main__":
    main()
