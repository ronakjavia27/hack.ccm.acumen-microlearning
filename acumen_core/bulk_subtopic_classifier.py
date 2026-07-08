"""
bulk_subtopic_classifier.py - One-time LLM classification of all existing papers.

Reads sent_summaries.json, groups by system, sends only that system's subtopic
list to the LLM, and writes results to subtopic_mapping.json.

Usage:
    python -m acumen_core.bulk_subtopic_classifier
    python -m acumen_core.bulk_subtopic_classifier --show N  (show first N results only, dry-run)
    python -m acumen_core.bulk_subtopic_classifier --max N    (classify at most N papers)
"""

import os
import sys
import json
import argparse
import re
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from acumen_core.config import TOGETHER_API_KEY, SUBTOPIC_MAPPING_FILE
from acumen_core.tracking import (
    load_all_entries_from_json, save_subtopic_mapping, load_subtopic_mapping,
)
from acumen_core.subtopics_config import (
    get_subtopics_for_system, get_all_systems, format_subtopics_for_prompt,
    subtopics_exist,
)


def _get_together_client():
    if not TOGETHER_API_KEY:
        return None
    try:
        from together import Together
        return Together(api_key=TOGETHER_API_KEY, timeout=120)
    except Exception:
        return None


def call_llm_classify(titles, system):
    """Send a batch of titles for one system to the LLM and get classifications."""
    subtopics = get_subtopics_for_system(system)
    if not subtopics:
        print(f"    [SKIP] No subtopics defined for '{system}'")
        return []

    subtopics_str = format_subtopics_for_prompt(system)

    system_prompt = f"""You are a medical librarian classifying papers into clinical subtopics.

For the speciality "{system}", classify each paper title into exactly ONE of these subtopics:
{subtopics_str}

Rules:
- Choose the single best-matching subtopic
- If unsure, pick the closest match
- Return raw titles exactly as provided
- Always choose from the list above — never invent a subtopic

Return a JSON object with a "classifications" key containing an array of objects:
[{{"title": "exact paper title", "subtopic": "chosen subtopic"}}]"""

    titles_text = "\n".join(f"- {t}" for t in titles)
    user_content = f"Classify these {len(titles)} paper titles into subtopics for {system}:\n\n{titles_text}"

    client = _get_together_client()
    if not client:
        print(f"    [X] No Together AI client available")
        return []

    model = "openai/gpt-oss-20b"
    print(f"    Calling {model} for {len(titles)} titles ({system})...")

    try:
        from acumen_core.llm import call_chat_api
        result = call_chat_api(
            client, model, system_prompt, user_content,
            temperature=0.1, max_tokens=4096,
        )
        if isinstance(result, dict):
            for key in ("classifications", "results", "items", "mappings", "data"):
                if key in result and isinstance(result[key], list):
                    return result[key]
            # If it's a flat dict with title->subtopic keys
            first_val = next(iter(result.values()), None)
            if first_val and isinstance(first_val, str):
                return [{"title": k, "subtopic": v} for k, v in result.items()]
            # If values are dicts with title/subtopic keys
            if first_val and isinstance(first_val, dict):
                items = []
                for k, v in result.items():
                    if isinstance(v, dict):
                        items.append({"title": v.get("title", k), "subtopic": v.get("subtopic", v.get("topic", ""))})
                if items:
                    return items
            print(f"    [X] Unexpected dict format (first keys: {list(result.keys())[:5]})")
            return []
        elif isinstance(result, list):
            return result
        else:
            print(f"    [X] Unexpected response format: {type(result)}")
            return []
    except Exception as e:
        print(f"    [X] LLM call failed: {e}")
        return []


def classify_all(max_papers=0, show_only=0):
    """Main classification routine."""
    entries = load_all_entries_from_json()
    print(f"Loaded {len(entries)} entries from sent_summaries.json")

    # Normalize system name to match subtopics.json keys
    _system_aliases = {
        "obstetrics and gynecology": "Obstetrics and Gynecology",
        "obstetrics & gynecology": "Obstetrics and Gynecology",
    }

    def _normalize_system(name):
        low = name.lower().strip()
        return _system_aliases.get(low, name)

    by_system = {}
    for e in entries:
        sys_name = _normalize_system(e.get("system", "Other").strip())
        if sys_name not in by_system:
            by_system[sys_name] = []
        by_system[sys_name].append(e)

    print(f"Found {len(by_system)} distinct systems\n")

    all_results = []

    for system in sorted(by_system.keys()):
        papers = by_system[system]
        titles = [p.get("title", "").strip() for p in papers if p.get("title")]
        if not titles:
            continue

        print(f"\n[{system}] {len(titles)} papers")

        if not subtopics_exist(system):
            print(f"    No subtopics defined — using system name as placeholder")
            for t in titles:
                all_results.append({"title": t, "subtopic": system})
            continue

        # If show_only, only do first few to preview
        batch = titles[:max_papers] if max_papers > 0 else titles
        if show_only > 0:
            batch = batch[:show_only]

        classifications = call_llm_classify(batch, system)
        classified_titles = set()
        if classifications:
            all_results.extend(classifications)
            print(f"    Got {len(classifications)} classifications")
            for c in classifications:
                if isinstance(c, dict) and c.get("title"):
                    classified_titles.add(c["title"].strip().lower())
        else:
            print(f"    LLM returned nothing — using system name")

        # Fallback: any titles the LLM missed get the system name as placeholder
        fallback_count = 0
        for t in batch:
            if t.strip().lower() not in classified_titles:
                all_results.append({"title": t, "subtopic": system})
                fallback_count += 1
        if fallback_count:
            print(f"    Fallback (unclassified): {fallback_count} titles set to system name")

        # Rate limit protection
        time.sleep(0.5)

    # Build output mapping
    mapping_entries = []
    seen_titles = set()
    for r in all_results:
        if not isinstance(r, dict):
            continue
        title_raw = r.get("title", "")
        subtopic_raw = r.get("subtopic", "")
        title = title_raw.strip() if isinstance(title_raw, str) else str(title_raw).strip()
        subtopic = subtopic_raw.strip() if isinstance(subtopic_raw, str) else str(subtopic_raw).strip()
        if not title or not subtopic:
            continue
        if title in seen_titles:
            continue
        seen_titles.add(title)

        # Find matching entry for system/type
        match = None
        for e in entries:
            if e.get("title", "").strip().lower() == title.lower():
                match = e
                break
        raw_system = match.get("system", "Other") if match else "Other"
        system = _normalize_system(raw_system)
        type_val = match.get("type", "Other") if match else "Other"
        file_name = match.get("file_name", "") if match else ""

        mapping_entries.append({
            "title": title,
            "system": system,
            "type": type_val,
            "file_name": file_name,
            "subtopic": subtopic,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "processed": True,
        })

    if show_only > 0:
        print(f"\n{'='*60}")
        print(f"  PREVIEW: First {show_only} results (dry-run — nothing saved)")
        print(f"{'='*60}")
        for i, m in enumerate(mapping_entries[:show_only], 1):
            print(f"  {i:2d}. [{m['system']}] {m['title'][:70]}")
            print(f"      -> {m['subtopic']}")
        print(f"\n  Total entries that would be saved: {len(mapping_entries)}")
        return mapping_entries

    # Save to subtopic_mapping.json
    existing = load_subtopic_mapping()
    existing_titles = set(e["title"].lower().strip() for e in existing if e.get("title"))

    # Merge, avoiding duplicates
    merged = list(existing)
    new_count = 0
    for m in mapping_entries:
        if m["title"].lower().strip() not in existing_titles:
            merged.append(m)
            existing_titles.add(m["title"].lower().strip())
            new_count += 1

    save_subtopic_mapping(merged)
    print(f"\n{'='*60}")
    print(f"  Complete!")
    print(f"  Previously mapped: {len(existing)}")
    print(f"  Newly mapped:      {new_count}")
    print(f"  Total in registry: {len(merged)}")
    print(f"  Saved to:          subtopic_mapping.json")
    print(f"{'='*60}")

    return merged


def main():
    parser = argparse.ArgumentParser(description="Bulk classify existing papers into subtopics via LLM")
    parser.add_argument("--show", type=int, default=0, help="Preview first N results only (dry-run)")
    parser.add_argument("--max", type=int, default=0, help="Max papers per system to classify")
    args = parser.parse_args()

    classify_all(max_papers=args.max, show_only=args.show)


if __name__ == "__main__":
    main()
