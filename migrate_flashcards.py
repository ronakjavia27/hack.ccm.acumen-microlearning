"""migrate_flashcards.py — one-shot migration to the unified flashcard store.

Moves legacy content into output_files/flashcards/{System}/{Subtopic}.json:
  - engine decks (output_files/flashcards/{CVS,...}/*.json)   -> source 'engine'
  - md deck JSONs (output_files/flashcards_md/*/*.json)       -> source 'md'
  - authored md sources stay in flashcards_md/ (import source)

Cards get persistent UUID ids, vocab-aligned subtopics (via LLM tags, fallback
'General'), explicit front/back (existing '---' dividers kept; missing fronts
batch-generated via the QUESTION_LLM_* model), and a data.original_subtopic
with the legacy label. Legacy JSON trees are archived (copied, then removed).

Usage:
  python migrate_flashcards.py --dry-run            # preview only (default)
  python migrate_flashcards.py --execute            # run the migration
  python migrate_flashcards.py --execute --no-tag --no-fronts   # no LLM calls
  python migrate_flashcards.py --execute --max 12 --verbose
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from acumen_core import flashcards as fc
from acumen_core.config import (
    FLASHCARDS_DIR,
    FLASHCARDS_LEGACY_DIR,
    FLASHCARDS_MD_LEGACY_DIR,
    FLASHCARDS_MD_OUT,
    THEORY_SPEC_TO_CANONICAL,
)


def discover_legacy_decks():
    """Return list of deck dicts from the legacy JSON trees."""
    decks = []
    if os.path.isdir(FLASHCARDS_DIR):
        for spec in sorted(os.listdir(FLASHCARDS_DIR)):
            spec_dir = os.path.join(FLASHCARDS_DIR, spec)
            if not os.path.isdir(spec_dir):
                continue
            if spec not in THEORY_SPEC_TO_CANONICAL:
                continue  # store system dirs, not legacy specialties
            for fname in sorted(os.listdir(spec_dir)):
                if not fname.endswith(".json"):
                    continue
                path = os.path.join(spec_dir, fname)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        deck = json.load(f)
                except (json.JSONDecodeError, OSError) as e:
                    print(f"  [X] skip unreadable {path}: {e}")
                    continue
                deck["_path"] = path
                deck["_source"] = "engine"
                decks.append(deck)
    if os.path.isdir(FLASHCARDS_MD_OUT):
        for spec in sorted(os.listdir(FLASHCARDS_MD_OUT)):
            spec_dir = os.path.join(FLASHCARDS_MD_OUT, spec)
            if not os.path.isdir(spec_dir):
                continue
            for fname in sorted(os.listdir(spec_dir)):
                if not fname.endswith(".json"):
                    continue
                path = os.path.join(spec_dir, fname)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        deck = json.load(f)
                except (json.JSONDecodeError, OSError) as e:
                    print(f"  [X] skip unreadable {path}: {e}")
                    continue
                deck["_path"] = path
                deck["_source"] = "md"
                decks.append(deck)
    return decks


def systems_for(spec):
    return THEORY_SPEC_TO_CANONICAL.get(spec) or [spec]


def deck_to_cards(deck, no_tag=False, verbose=False):
    """Convert one legacy deck into list of store card dicts."""
    spec = deck.get("specialty") or "General"
    systems = systems_for(spec)
    system = systems[0]
    title = deck.get("title") or os.path.basename(deck.get("_path", ""))
    source = deck.get("_source", "engine")
    source_file = deck.get("source_file")
    cards = []
    for c in deck.get("cards") or []:
        content = c.get("content") or ""
        front, back = fc.parse_card_content(content)
        card = fc.build_card(
            front or "", back or content, system, "General",
            tags=[], source=source, source_file=source_file,
            slug_hint=c.get("subtopic") or title,
            data={"original_subtopic": c.get("subtopic")},
        )
        if c.get("tags"):
            card["tags"] = [t for t in c["tags"] if isinstance(t, str)]
        cards.append(card)
        if verbose:
            print(f"    . {card['id'][:8]} {card['slug']} (front={'Y' if card['front'] else 'N'})")
    if not no_tag:
        if cards and (not all(c["tags"] for c in cards)):
            fc.tag_cards_with_llm(cards, systems, verbose=verbose)
    for c in cards:
        if c["tags"]:
            c["subtopic"] = fc.canonical_subtopic(system, c["tags"][0])
        else:
            c["subtopic"] = "General"
    return cards


def archive_legacy():
    """Copy legacy trees to archives, then remove live legacy files."""
    for src, dst, label in (
        (FLASHCARDS_DIR, FLASHCARDS_LEGACY_DIR, "engine"),
        (FLASHCARDS_MD_OUT, FLASHCARDS_MD_LEGACY_DIR, "md"),
    ):
        if not os.path.isdir(src):
            continue
        os.makedirs(dst, exist_ok=True)
        for spec in sorted(os.listdir(src)):
            spec_dir = os.path.join(src, spec)
            if not os.path.isdir(spec_dir):
                continue
            if label == "engine" and spec not in THEORY_SPEC_TO_CANONICAL:
                continue  # store system dirs stay
            target = os.path.join(dst, spec)
            if os.path.exists(target):
                shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(spec_dir, target)
            shutil.rmtree(spec_dir, ignore_errors=True)
            print(f"  [i] archived {spec_dir} -> {target}")


def load_engine_specs():
    specs = []
    if os.path.isdir(FLASHCARDS_DIR):
        specs = [s for s in os.listdir(FLASHCARDS_DIR)
                 if os.path.isdir(os.path.join(FLASHCARDS_DIR, s))
                 and s in THEORY_SPEC_TO_CANONICAL]
    md_specs = []
    if os.path.isdir(FLASHCARDS_MD_OUT):
        md_specs = [s for s in os.listdir(FLASHCARDS_MD_OUT)
                    if os.path.isdir(os.path.join(FLASHCARDS_MD_OUT, s))]
    return specs, md_specs


def main():
    ap = argparse.ArgumentParser(description="Migrate flashcards to the unified store")
    ap.add_argument("--execute", action="store_true", help="run the migration (default: dry-run)")
    ap.add_argument("--dry-run", action="store_true", dest="dry_run", help="preview only (default)")
    ap.add_argument("--no-tag", action="store_true", help="skip LLM subtopic tagging")
    ap.add_argument("--no-fronts", action="store_true", help="skip front-question generation")
    ap.add_argument("--no-archive", action="store_true", help="leave legacy trees in place (testing)")
    ap.add_argument("--max", type=int, default=0, help="cap at N cards (testing)")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--llm", default="openrouter", choices=["openrouter", "gemini", "together"])
    args = ap.parse_args()

    specs, md_specs = load_engine_specs()
    if not specs and not md_specs:
        idx = fc.load_flashcards_index()
        print(f"No legacy decks found. Store state: {idx.get('total_cards', 0)} cards "
              f"in {len(idx.get('systems', {}))} systems.")
        return

    decks = discover_legacy_decks()
    if args.max:
        decks = decks[: args.max]
    total = sum(len(d.get("cards") or []) for d in decks)
    print(f"Discovered {len(decks)} legacy decks ({total} cards):")
    for d in decks:
        print(f"  - [{d['_source']}] {d.get('specialty')}/{d.get('title')} "
              f"({len(d.get('cards') or [])} cards)")

    if args.dry_run and not args.execute:
        print("\nDry run — no changes made. Re-run with --execute to migrate.")
        return

    if not args.no_archive:
        print("\nArchiving legacy trees...")
        archive_legacy()
    else:
        print("\n--no-archive: legacy trees left in place.")

    print("Building store cards...")
    store_cards = []
    for d in decks:
        try:
            store_cards.extend(deck_to_cards(d, no_tag=args.no_tag, verbose=args.verbose))
        except Exception as e:
            print(f"  [X] deck failed ({d.get('title')}): {e}")
    if args.max and len(store_cards) > args.max:
        store_cards = store_cards[: args.max]

    groups = {}
    for c in store_cards:
        groups.setdefault((c["system"], c["subtopic"]), []).append(c)
    for (system, subtopic), cards in sorted(groups.items()):
        data = {"id": f"{system}/{subtopic}", "system": system, "subtopic": subtopic,
                "cards": cards, "card_count": len(cards),
                "created_at": cards[0]["created_at"]}
        fc.write_subtopic_file(data)
        print(f"  [i] store file: {system}/{subtopic} ({len(cards)} cards)")

    if not args.no_fronts:
        missing = [c for c in store_cards if not (c.get("front") or "").strip()]
        print(f"Generating fronts for {len(missing)} cards (QUESTION_LLM_* model)...")
        fc.ensure_fronts(store_cards, verbose=args.verbose, persist=True)

    idx = fc.rebuild_flashcards_index()
    print(f"\nMigration complete. Store: {idx['total_cards']} cards across "
          f"{len(idx['systems'])} systems / {sum(len(v) for v in idx['systems'].values())} subtopics.")
    print(f"Index: {fc.FLASHCARDS_INDEX_FILE}")
    print("Legacy archives: output_files/flashcards_legacy/ + output_files/flashcards_md_legacy/")


if __name__ == "__main__":
    main()
