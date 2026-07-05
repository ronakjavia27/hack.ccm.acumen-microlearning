#!/usr/bin/env python3
"""Reclassify articles with system='Other' by interactively assigning a specialty."""

import json
import shutil
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
SPECIALTIES_FILE = BASE_DIR / "specialties.txt"
SUMMARIES_FILE = BASE_DIR / "sent_summaries.json"
OUTPUT_DIR = BASE_DIR / "output_files"


def load_specialties():
    with open(SPECIALTIES_FILE, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def load_summaries():
    with open(SUMMARIES_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_summaries(data):
    with open(SUMMARIES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def json_name_from_pdf(file_name):
    stem = file_name[:-4] if file_name.lower().endswith(".pdf") else file_name
    return stem + ".json"


def find_source_file(file_name, article_type):
    jname = json_name_from_pdf(file_name)
    expected = OUTPUT_DIR / "Other" / article_type / jname
    if expected.exists():
        return expected
    return None


def move_file(src, specialty, article_type, file_name):
    jname = json_name_from_pdf(file_name)
    dst_dir = OUTPUT_DIR / specialty / article_type
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / jname
    if dst.exists():
        stem = dst.stem
        counter = 1
        while dst.exists():
            dst = dst_dir / f"{stem}_{counter}.json"
            counter += 1
    shutil.move(str(src), str(dst))
    return dst


def print_menu(specialties):
    print("\n" + "=" * 60)
    print("SPECIALTIES:")
    print("-" * 40)
    for i, s in enumerate(specialties, 1):
        print(f"  {i:2d}. {s}")
    print("-" * 40)
    print("  s  - Skip this article")
    print("  q  - Quit (progress saved)")
    print("=" * 60)


def main():
    specialties = load_specialties()
    data = load_summaries()

    other_idxs = [i for i, e in enumerate(data) if e.get("system", "").strip().lower() == "other"]

    if not other_idxs:
        print("No articles with system='Other' found.")
        return

    total = len(other_idxs)
    processed = 0
    skipped = 0

    print(f"\nFound {total} article(s) with system='Other'.\n")

    for pos, list_idx in enumerate(other_idxs, 1):
        entry = data[list_idx]
        title = entry.get("title", "?")
        file_name = entry.get("file_name", "")
        article_type = entry.get("type", "Other")

        print(f"\n--- Article {pos}/{total} ---")
        print(f"  Title: {title}")
        print(f"  File:  {file_name}")
        print(f"  Type:  {article_type}")

        src = find_source_file(file_name, article_type)
        if src is None:
            print(f"  [SKIP] JSON file not found in output_files for: {file_name}")
            skipped += 1
            continue

        print(f"  Found: {src.relative_to(BASE_DIR)}")

        while True:
            print_menu(specialties)
            choice = input("  Your choice: ").strip().lower()

            if choice == "q":
                save_summaries(data)
                print(f"\nDone. Processed: {processed}, Skipped: {skipped}, Remaining: {total - pos + 1}")
                return

            if choice == "s":
                print("  Skipped.")
                skipped += 1
                break

            try:
                num = int(choice)
                if 1 <= num <= len(specialties):
                    selected = specialties[num - 1]
                    if selected.strip().lower() == "other":
                        print("  Can't reclassify to 'Other'. Pick a different specialty.")
                        continue
                    try:
                        dst = move_file(src, selected, article_type, file_name)
                        entry["system"] = selected
                        save_summaries(data)
                        print(f"  Moved to: {dst.relative_to(BASE_DIR)}")
                        print(f"  Updated system -> {selected}")
                        processed += 1
                        break
                    except Exception as e:
                        print(f"  [ERROR] {e}")
                        skipped += 1
                        break
                else:
                    print(f"  Enter 1-{len(specialties)}, s, or q.")
            except ValueError:
                print(f"  Enter 1-{len(specialties)}, s, or q.")

    save_summaries(data)
    print(f"\n{'=' * 60}")
    print(f"Summary:  Processed={processed}  Skipped={skipped}  Total={total}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Progress saved in sent_summaries.json.")
        sys.exit(1)
