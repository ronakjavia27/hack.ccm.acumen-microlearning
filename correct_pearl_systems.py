#!/usr/bin/env python3
"""
Correct pearl system classifications using Gemma 4 (local Ollama).
Reads pearls.json, cross-checks each pearl's content + source_paper against
its assigned system. Corrects mismatches and logs all changes.

Usage:
    python correct_pearl_systems.py              # interactive, asks before writing
    python correct_pearl_systems.py --apply      # writes corrections directly
    python correct_pearl_systems.py --dry-run    # only logs, no changes
    python correct_pearl_systems.py --fast       # skip pearls matching their source paper's system
    python correct_pearl_systems.py --only-other # only check pearls with system "Other"

Output:
    pearl_changes.json  — full audit log of every classification decision
    pearls.json         — (if --apply) overwritten with corrected systems
"""

import json
import os
import sys
import time
import urllib.request
import urllib.parse

# ── config ──────────────────────────────────────────────────────────────
PEARLS_JSON = "pearls.json"
SPECIALTIES_FILE = "specialties.txt"
SENT_SUMMARIES_JSON = "sent_summaries.json"
CHANGES_LOG = "pearl_changes.json"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma4:latest"
PROMPT_TEMPLATE = """You are a medical specialty classifier. Given a clinical pearl and its source paper title, determine which SINGLE specialty from the provided list best matches the pearl content.

Specialties:
{specialties}

Rules:
- Classify based on the pearl CONTENT (the clinical nugget), NOT the source paper's specialty.
- If the pearl content clearly belongs to a specific specialty, choose that one.
- If the pearl content is generic (e.g., basic sepsis management, general ICU care, ABCDE approach), classify as "General".
- If the pearl discusses multiple systems without a clear primary specialty, use "Multisystem".
- Only use specialties from the list above.
- Respond with ONLY the specialty name, nothing else.

Pearl content:
{pearl}

Source paper:
{source_paper}

Specialty:"""

BATCH_PROMPT_TEMPLATE = """You are a medical specialty classifier. Given a batch of clinical pearls with their source paper titles, determine which SINGLE specialty from the provided list best matches EACH pearl's content.

Specialties:
{specialties}

Rules:
- Classify based on the pearl CONTENT (the clinical nugget), NOT the source paper's specialty.
- If generic (ABC, sepsis basics, ICU basics, ABCDE), use "General".
- If multiple systems without a clear primary, use "Multisystem".
- Only use specialties from the list.
- Respond with one line per pearl, format: ID:SPECIALTY

Pearls:
{batch}

Respond with ONLY the lines, nothing else:"""

# ── helpers ────────────────────────────────────────────────────────────


def load_specialties():
    with open(SPECIALTIES_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]


def load_pearls():
    with open(PEARLS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def load_summary_system_map():
    """Build a map of file_name -> system from sent_summaries.json for fast skip."""
    if not os.path.exists(SENT_SUMMARIES_JSON):
        return {}
    with open(SENT_SUMMARIES_JSON, "r", encoding="utf-8") as f:
        summaries = json.load(f)
    m = {}
    for s in summaries:
        fn = str(s.get("file_name", "")).strip()
        sys = str(s.get("system", "")).strip()
        if fn and sys:
            m[fn] = sys
    return m


def parse_line_number(line):
    """Try to extract just the specialty name from a line like '3. Nephrology' or 'Nephrology'."""
    s = line.strip()
    parts = s.split(".", 1)
    if len(parts) > 1 and parts[1].strip():
        return parts[1].strip()
    return s


def classify_pearl(pearl_text, source_paper, specialties_list, dry_run=False, retries=5):
    """Call Ollama Gemma4 to classify a pearl. Returns (specialty_name, error)."""
    combined_specialties = "\n".join(
        "%d. %s" % (i + 1, s) for i, s in enumerate(specialties_list)
    )
    prompt = PROMPT_TEMPLATE.format(
        specialties=combined_specialties,
        pearl=pearl_text[:800] if pearl_text else "",
        source_paper=source_paper[:300] if source_paper else "",
    )

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "temperature": 0.1,
        "max_tokens": 64,
    }
    data = json.dumps(payload).encode("utf-8")

    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                OLLAMA_URL,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode())
            raw = result.get("response", "").strip()
            last_error = None
            break
        except Exception as e:
            last_error = str(e)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            raw = None

    if last_error:
        return None, last_error
    if raw is None:
        return None, "No response after retries"

    # Clean the response
    raw = raw.strip().rstrip(".")

    # Validate it's in our list
    for s in specialties_list:
        if raw.lower() == s.lower():
            return s, None

    # Try partial match
    for s in specialties_list:
        if s.lower() in raw.lower() or raw.lower() in s.lower():
            return s, None

    return raw, None  # return the raw response even if not in list


def log_change(changes, entry, dry_run=False):
    changes.append(entry)
    # Write incrementally so we don't lose data on crash
    if not dry_run:
        with open(CHANGES_LOG, "w", encoding="utf-8") as f:
            json.dump(changes, f, indent=2, ensure_ascii=False)


def main():
    apply = "--apply" in sys.argv
    dry_run = "--dry-run" in sys.argv
    fast = "--fast" in sys.argv
    only_other = "--only-other" in sys.argv

    if not apply and not dry_run:
        print("INFO: Running in interactive mode (no changes written without confirmation)")
        print("      Use --apply to write changes, --dry-run to simulate")
    if dry_run:
        print("INFO: Dry-run mode. No changes will be made to pearls.json")
    if fast:
        print("INFO: Fast mode. Will skip pearls whose current system matches their source paper's system.")
    if only_other:
        print("INFO: Only-other mode. Will only check pearls with system 'Other'.")

    specialties = load_specialties()
    specialties = [parse_line_number(s) for s in specialties]
    print("Loaded %d specialties: %s" % (len(specialties), ", ".join(specialties)))

    pearls = load_pearls()
    print("Loaded %d pearls from %s" % (len(pearls), PEARLS_JSON))

    summary_map = load_summary_system_map()
    print("Loaded %s entries from %s" % (len(summary_map), SENT_SUMMARIES_JSON))

    # Load previous changes log if exists
    changes = []
    if os.path.exists(CHANGES_LOG):
        with open(CHANGES_LOG, "r", encoding="utf-8") as f:
            changes = json.load(f)
        print("Loaded %d previous audit entries from %s" % (len(changes), CHANGES_LOG))

    corrected = 0
    skipped = 0
    errors = 0
    fast_skipped = 0
    total = len(pearls)

    for idx, pearl in enumerate(pearls):
        pearl_id = pearl.get("id", str(idx))
        current_system = pearl.get("system", "").strip()
        pearl_text = pearl.get("pearl", "")
        source_paper = pearl.get("source_paper", "")
        file_name = pearl.get("file_name", "")

        if not pearl_text:
            skipped += 1
            continue

        # only-other mode: skip if not system "Other"
        if only_other and current_system != "Other":
            fast_skipped += 1
            continue

        # Fast check: if current system matches the source paper's system, skip
        if fast and file_name:
            fn_pdf = file_name[:-5] + ".pdf" if file_name.endswith(".json") else file_name
            paper_system = summary_map.get(fn_pdf, "")
            if paper_system and current_system.lower() == paper_system.lower():
                fast_skipped += 1
                continue

        print("\r[%d/%d] Pearl %s (current: %s)..." % (idx + 1, total, pearl_id, current_system), end="")
        sys.stdout.flush()

        # Skip if already in "correct" state? We'll classify anyway for audit.
        new_system, error = classify_pearl(
            pearl_text, source_paper, specialties, dry_run=dry_run
        )

        if error:
            errors += 1
            entry = {
                "id": pearl_id,
                "current_system": current_system,
                "error": error,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            log_change(changes, entry, dry_run=dry_run)
            print("\n  ERROR: %s" % error)
            continue

        if new_system is None:
            errors += 1
            entry = {
                "id": pearl_id,
                "current_system": current_system,
                "error": "No response from model",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            log_change(changes, entry, dry_run=dry_run)
            print("\n  ERROR: No response")
            continue

        needs_change = new_system.lower() != current_system.lower()
        if needs_change:
            corrected += 1
            entry = {
                "id": pearl_id,
                "pearl": pearl_text[:100] + ("..." if len(pearl_text) > 100 else ""),
                "source_paper": source_paper[:100] + ("..." if len(source_paper) > 100 else ""),
                "old_system": current_system,
                "new_system": new_system,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            log_change(changes, entry, dry_run=dry_run)

            if not dry_run and (apply or input_changes(entry)):
                pearl["system"] = new_system

        # Small delay to avoid hammering Ollama
        if not dry_run:
            time.sleep(0.3)

    print("\n\nDone. %d corrected, %d errors, %d skipped, %d fast-skipped" % (corrected, errors, skipped, fast_skipped))

    if not dry_run and apply:
        with open(PEARLS_JSON, "w", encoding="utf-8") as f:
            json.dump(pearls, f, indent=2, ensure_ascii=False)
        print("Updated %s with %d corrections" % (PEARLS_JSON, corrected))

    print("Audit log written to %s" % CHANGES_LOG)
    print("Summary: %d total, %d corrected, %d errors, %d fast-skipped" % (total, corrected, errors, fast_skipped))


def input_changes(entry):
    """Ask user to confirm each change in interactive mode."""
    print("\n  Proposed change: %s -> %s" % (entry["old_system"], entry["new_system"]))
    print("  Pearl: %s" % entry["pearl"])
    print("  Paper: %s" % entry["source_paper"])
    while True:
        resp = input("  Apply? [Y/n/q]: ").strip().lower()
        if resp in ("", "y", "yes"):
            return True
        if resp in ("n", "no"):
            return False
        if resp in ("q", "quit"):
            print("  Quitting...")
            sys.exit(0)


if __name__ == "__main__":
    if not os.path.exists(SPECIALTIES_FILE):
        print("ERROR: %s not found. Create it with one specialty per line." % SPECIALTIES_FILE)
        sys.exit(1)
    if not os.path.exists(PEARLS_JSON):
        print("ERROR: %s not found." % PEARLS_JSON)
        sys.exit(1)
    main()
