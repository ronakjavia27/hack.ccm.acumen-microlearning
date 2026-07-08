"""
subtopic_mapper.py - Interactive CLI for assigning subtopics to pending papers.

Reads pending_subtopics.json, shows the user one paper at a time with valid
subtopics for that system, and saves choices to subtopic_mapping.json.

Usage:
    python -m acumen_core.subtopic_mapper                    Interactive mode
    python -m acumen_core.subtopic_mapper --batch-llm        Auto-classify all pending via LLM
    python -m acumen_core.subtopic_mapper --status            Show pending count
    python -m acumen_core.subtopic_mapper --list-queue        List all pending entries
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from acumen_core.tracking import (
    load_pending_subtopics, save_pending_subtopics,
    load_subtopic_mapping, save_subtopic_mapping,
    append_subtopic_mapping,
    update_entry_in_json, update_pearls_by_file_name,
)
from acumen_core.subtopics_config import (
    get_subtopics_for_system, format_subtopics_for_prompt,
    get_all_systems,
)


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def _get_together_client():
    from acumen_core.config import TOGETHER_API_KEY
    if not TOGETHER_API_KEY:
        return None
    try:
        from together import Together
        return Together(api_key=TOGETHER_API_KEY, timeout=120)
    except Exception:
        return None


def call_llm_for_entry(title, system):
    """Classify a single paper using LLM with only its system's subtopics."""
    subtopics = get_subtopics_for_system(system)
    if not subtopics:
        return system

    subtopics_str = format_subtopics_for_prompt(system)

    system_prompt = (
        "You are a medical librarian classifying papers into clinical subtopics.\n"
        'For the speciality "%s", classify this paper title into exactly ONE subtopic.\n'
        "Valid subtopics:\n%s\n\n"
        'Return JSON: {"subtopic": "chosen subtopic"}'
    ) % (system, subtopics_str)

    user_content = "Title: %s" % title

    client = _get_together_client()
    if not client:
        return None

    try:
        from acumen_core.llm import call_chat_api
        result = call_chat_api(
            client, "openai/gpt-oss-20b", system_prompt, user_content,
            temperature=0.1, max_tokens=256,
        )
        if isinstance(result, dict):
            return result.get("subtopic", "")
        return ""
    except Exception as e:
        print("    LLM error: %s" % e)
        return None


def run_interactive():
    """Interactive mode: show one pending paper at a time, let user pick subtopic."""
    pending = load_pending_subtopics()
    # Filter to unprocessed
    unprocessed = [p for p in pending if not p.get("processed")]
    processed = [p for p in pending if p.get("processed")]

    if not unprocessed:
        print("  No pending papers awaiting subtopic assignment.")
        print("  All caught up!")
        return

    print("  Found %d pending papers (%d already processed)\n" % (len(unprocessed), len(processed)))
    input("  Press Enter to start assigning subtopics...")

    all_systems = get_all_systems()
    total = len(unprocessed)
    for idx, entry in enumerate(unprocessed, 1):
        title = entry.get("title", "Unknown")
        system = entry.get("system", "Other")
        type_val = entry.get("type", "Other")
        file_name = entry.get("file_name", "")

        # Step 1: Confirm / correct the specialty
        while True:
            clear_screen()
            print("=" * 60)
            print("  Paper %d of %d" % (idx, total))
            print("=" * 60)
            print("  Title:   %s" % title[:90])
            print("  System:  %s" % system)
            print("  Type:    %s" % type_val)
            print("  File:    %s" % file_name)
            print()
            resp = input("  Specialty is '%s'. Correct? [Y/n/s]kip/e[x]it: " % system).strip().lower()
            if resp in ("", "y", "yes"):
                break
            if resp in ("n", "no"):
                print("\n  Available specialties:")
                sys_list = all_systems
                for i, s in enumerate(sys_list, 1):
                    print("    %2d. %s" % (i, s))
                print("    %2d. Cancel (keep current)" % (len(sys_list) + 1))
                sys_choice = input("\n  Select correct specialty (1-%d): " % (len(sys_list) + 1)).strip()
                if sys_choice.isdigit():
                    n = int(sys_choice)
                    if 1 <= n <= len(sys_list):
                        system = sys_list[n - 1]
                        print("  Specialty updated to: %s" % system)
                        break
                # fall through to re-prompt
                continue
            if resp in ("s", "skip"):
                resp2 = input("  Skip means subtopic = system name. Proceed? [y/N]: ").strip().lower()
                if resp2 in ("", "y", "yes"):
                    chosen = system
                    entry["processed"] = True
                    entry["subtopic"] = chosen
                    save_pending_subtopics(pending)
                    print("\n  Skipped: %s -> %s" % (system, chosen))
                    if idx < total:
                        input("  Press Enter for next paper...")
                    break
                continue
            if resp in ("x", "exit", "e"):
                print("\n  Progress saved. Exiting.")
                return

        if entry.get("processed"):
            continue  # already handled via skip path

        # Step 2: Show subtopics for final specialty
        subtopics = get_subtopics_for_system(system)

        while True:
            clear_screen()
            print("=" * 60)
            print("  Paper %d of %d" % (idx, total))
            print("=" * 60)
            print("  Title:   %s" % title[:90])
            print("  System:  %s" % system)
            print("  Type:    %s" % type_val)
            print("  File:    %s" % file_name)
            print()

            if not subtopics:
                print("  [No subtopics defined for '%s']" % system)
                print("  Subtopic will be set to system name: %s" % system)
                chosen = system
                input("\n  Press Enter to continue...")
                break

            print("  Valid subtopics for %s:" % system)
            for i, st in enumerate(subtopics, 1):
                print("    %2d. %s" % (i, st))
            print("    %2d. Skip (keep placeholder)" % (len(subtopics) + 1))
            print("    %2d. Exit (save progress)" % (len(subtopics) + 2))
            print()

            choice = input("  Enter choice (1-%d): " % (len(subtopics) + 2)).strip()

            if not choice.isdigit():
                continue

            choice_num = int(choice)
            if 1 <= choice_num <= len(subtopics):
                chosen = subtopics[choice_num - 1]
                break
            elif choice_num == len(subtopics) + 1:
                chosen = system  # keep placeholder
                break
            elif choice_num == len(subtopics) + 2:
                print("\n  Progress saved. Exiting.")
                return
            else:
                print("  Invalid choice. Try again.")
                input("  Press Enter...")

        # Save to subtopic_mapping.json
        append_subtopic_mapping(
            title=title, system=system, type_val=type_val,
            file_name=file_name, subtopic=chosen,
        )

        # Mark as processed in pending
        entry["processed"] = True
        entry["subtopic"] = chosen
        save_pending_subtopics(pending)

        # Write back to sent_summaries.json and pearls.json
        sent_ok = update_entry_in_json(file_name, {"system": system, "subtopic": chosen})
        pearl_count = update_pearls_by_file_name(file_name, {"system": system, "subtopic": chosen})
        if sent_ok:
            print("  sent_summaries.json: updated")
        else:
            print("  sent_summaries.json: entry not found (file_name mismatch)")
        if pearl_count:
            print("  pearls.json: %d pearl(s) updated" % pearl_count)

        print("\n  Assigned: %s -> %s" % (system, chosen))
        if idx < total:
            input("  Press Enter for next paper...")

    print("\n  All %d papers assigned!" % total)


def run_batch_llm():
    """Auto-classify all pending via LLM."""
    pending = load_pending_subtopics()
    unprocessed = [p for p in pending if not p.get("processed")]

    if not unprocessed:
        print("  No pending papers.")
        return

    print("  Auto-classifying %d pending papers via LLM..." % len(unprocessed))

    for idx, entry in enumerate(unprocessed, 1):
        title = entry.get("title", "Unknown")
        system = entry.get("system", "Other")
        type_val = entry.get("type", "Other")
        file_name = entry.get("file_name", "")

        print("\n  [%d/%d] %s" % (idx, len(unprocessed), title[:60]))
        subtopic = call_llm_for_entry(title, system)

        if subtopic:
            print("    -> %s" % subtopic)
        else:
            subtopic = system
            print("    -> (fallback) %s" % subtopic)

        append_subtopic_mapping(
            title=title, system=system, type_val=type_val,
            file_name=file_name, subtopic=subtopic,
        )
        entry["processed"] = True
        entry["subtopic"] = subtopic
        save_pending_subtopics(pending)
        time.sleep(0.3)

    print("\n  Batch LLM classification complete!")


def show_status():
    """Show count of pending papers."""
    pending = load_pending_subtopics()
    unprocessed = [p for p in pending if not p.get("processed")]
    mapping = load_subtopic_mapping()
    print("  Pending subtopics:    %d" % len(unprocessed))
    print("  Already mapped:      %d" % len(mapping))
    print("  Total in queue:      %d" % len(pending))


def list_queue():
    """List all pending entries."""
    pending = load_pending_subtopics()
    unprocessed = [p for p in pending if not p.get("processed")]
    if not unprocessed:
        print("  Queue is empty.")
        return
    print("  Pending papers (%d):" % len(unprocessed))
    print()
    for i, p in enumerate(unprocessed, 1):
        print("  %2d. [%s] %s" % (i, p.get("system", "?"), p.get("title", "")[:70]))


def main():
    parser = argparse.ArgumentParser(description="Interactive subtopic mapper")
    parser.add_argument("--batch-llm", action="store_true", help="Auto-classify all pending via LLM")
    parser.add_argument("--status", action="store_true", help="Show pending count")
    parser.add_argument("--list-queue", action="store_true", help="List all pending entries")
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.list_queue:
        list_queue()
    elif args.batch_llm:
        run_batch_llm()
    else:
        run_interactive()


if __name__ == "__main__":
    main()
