import json
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

def load_json(path, encoding="utf-8"):
    with open(path, encoding=encoding) as f:
        return json.load(f)

def save_json(path, data, encoding="utf-8"):
    with open(path, "w", encoding=encoding) as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def build_summary_lookup(summaries):
    """Build lookup dicts from sent_summaries entries."""
    by_file = {}
    by_title = {}
    for s in summaries:
        fname = s.get("file_name", "")
        stem = Path(fname).stem
        sys_val = s.get("system", "")
        by_file[stem] = sys_val
        title = s.get("title", "").strip().lower()
        if title:
            by_title[title] = sys_val
    return by_file, by_title

def match_pearl(pearl, by_file, by_title):
    """Find the correct system for a pearl by matching against summaries."""
    pearl_file = pearl.get("file_name", "")
    pearl_stem = Path(pearl_file).stem

    if pearl_stem in by_file:
        return by_file[pearl_stem]

    source = pearl.get("source_paper", "").strip().lower()
    if source in by_title:
        return by_title[source]

    return None

def main():
    summaries_path = SCRIPT_DIR / "sent_summaries.json"
    pearls_path = SCRIPT_DIR / "pearls.json"

    print("Loading sent_summaries.json...")
    summaries = load_json(summaries_path)
    by_file, by_title = build_summary_lookup(summaries)
    print(f"  Loaded {len(summaries)} summary entries")

    print("Loading pearls.json...")
    pearls = load_json(pearls_path)
    print(f"  Loaded {len(pearls)} pearls")

    changes = []
    no_match = []
    already_correct = 0

    for i, pearl in enumerate(pearls):
        old_system = pearl.get("system", "")
        matched_system = match_pearl(pearl, by_file, by_title)

        if matched_system is None:
            no_match.append((i, pearl.get("source_paper", ""), pearl.get("file_name", "")))
            continue

        if old_system == matched_system:
            already_correct += 1
            continue

        pearl["system"] = matched_system
        changes.append({
            "id": pearl.get("id"),
            "source_paper": pearl.get("source_paper", ""),
            "old_system": old_system,
            "new_system": matched_system,
        })

    print(f"\nResults:")
    print(f"  Already correct:         {already_correct}")
    print(f"  Updated:                 {len(changes)}")
    print(f"  No match found:          {len(no_match)}")

    if changes:
        print(f"\nChanges made:")
        for c in changes:
            print(f"  [{c['id']}] {c['old_system']} -> {c['new_system']} | {c['source_paper'][:60]}")

    if no_match:
        print(f"\nPearls with no match ({len(no_match)}):")
        for idx, src, fname in no_match[:20]:
            print(f"  [{idx}] file={fname} | {src[:80]}")
        if len(no_match) > 20:
            print(f"  ... and {len(no_match) - 20} more")

    save_json(pearls_path, pearls)
    print(f"\nSaved updated pearls to {pearls_path}")

if __name__ == "__main__":
    main()
