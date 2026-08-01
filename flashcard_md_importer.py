"""
flashcard_md_importer.py - Convert hand-written markdown flashcards into JSON decks.

Authoring convention (source of truth: flashcards_md/{Specialty}/{topic}.md):
    # Deck Title (optional - falls back to filename)
    ## Card title
    ... markdown content (tables, bullets, notes) ...
    ## Another card
    ...
    --- (optional divider inside a card -> front/back faces for flip mode)

Output: output_files/flashcards_md/{Specialty}/{slug}.json in the same deck
schema used by flashcard_engine.py, so the admin console CRUD (preserve /
discard / edit / regenerate) works unchanged.

Usage:
    python flashcard_md_importer.py                 # convert all files
    python flashcard_md_importer.py --spec CVS      # only one specialty
    python flashcard_md_importer.py --file "CVS/SCAI Shock Classification.md"
    python flashcard_md_importer.py --force         # overwrite existing decks
    python flashcard_md_importer.py --tag           # LLM-tag cards with subtopics vocab
    python flashcard_md_importer.py --gemini        # explicit provider flags (same as --llm)
    python flashcard_md_importer.py --api-key sk-xxx --model my/model --base-url https://...  # custom OpenAI-compatible endpoint
    python flashcard_md_importer.py --dry-run       # preview only
"""

import json
import os
import re
import sys
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from acumen_core.config import FLASHCARDS_MD_DIR, FLASHCARDS_MD_OUT
from acumen_core.tracking import save_json_atomic


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def parse_markdown_deck(md_path):
    """Split a markdown file into a deck dict (title + cards)."""
    with open(md_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    lines = content.split("\n")

    title = None
    card_starts = []  # (index, heading)
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not title and stripped.startswith("# ") and not stripped.startswith("## "):
            title = stripped[2:].strip()
        if stripped.startswith("## "):
            card_starts.append((i, stripped[3:].strip()))

    if not title:
        name = os.path.splitext(os.path.basename(md_path))[0]
        title = re.sub(r"^\d+\s*", "", name).strip()

    if not card_starts:
        body = "\n".join(lines)
        body = re.sub(r"^#\s+.*$", "", body, count=1).strip()
        card_starts = [(0, title)] if body.strip() else []

    cards = []
    for idx, (start_line, heading) in enumerate(card_starts):
        end_line = card_starts[idx + 1][0] if idx + 1 < len(card_starts) else len(lines)
        body = "\n".join(lines[start_line + 1:end_line]).strip()
        if not body:
            continue
        cards.append({
            "subtopic": heading,
            "content": body,
            "id": "",
            "status": "pending",
            "tags": [],
        })

    return title, cards


def _load_existing_tags(out_path):
    """Load {card_id: tags} from an existing deck JSON so re-converts keep tags."""
    if not os.path.exists(out_path):
        return {}
    try:
        with open(out_path, "r", encoding="utf-8") as f:
            old = json.load(f)
        return {str(c.get("id", "")): c.get("tags") or [] for c in old.get("cards", []) if isinstance(c, dict)}
    except (json.JSONDecodeError, Exception):
        return {}


def convert_file(md_path, force=False, dry_run=False, verbose=False, tag=False, llm="openrouter",
                 api_key=None, model=None, base_url=None):
    """Convert one markdown file into a JSON deck file."""
    rel_path = os.path.relpath(md_path, FLASHCARDS_MD_DIR)
    parts = rel_path.split(os.sep)
    specialty = parts[0] if len(parts) > 1 else "Other"
    stem = os.path.splitext(os.path.basename(md_path))[0]

    title, cards = parse_markdown_deck(md_path)
    if not cards:
        if verbose:
            print(f"  [~] Skip (no card content): {rel_path}")
        return False

    slug = slugify(stem)
    slug_base = slug[:30]
    out_path = os.path.join(FLASHCARDS_MD_OUT, specialty, f"{slug}.json")
    old_tags = _load_existing_tags(out_path)
    for i, card in enumerate(cards):
        card["id"] = f"{slug_base}-{i}"
        card["tags"] = old_tags.get(card["id"], [])

    deck = {
        "id": slug,
        "source_file": rel_path,
        "specialty": specialty,
        "title": title,
        "cards": cards,
        "subtopics": sorted({t for c in cards for t in c["tags"]}),
        "status": "pending",
        "edit_history": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    if os.path.exists(out_path) and not force:
        if verbose:
            print(f"  [~] Already exists (use --force): {rel_path}")
        return False

    if dry_run:
        print(f"  [o] Would write: {out_path} ({len(cards)} cards)")
        return True

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    if tag:
        from acumen_core.flashcards import tag_deck_with_llm
        tag_deck_with_llm(deck, llm=llm, verbose=verbose,
                          api_key=api_key, model=model, base_url=base_url)
        deck["subtopics"] = sorted({t for c in deck["cards"] for t in c["tags"]})
    save_json_atomic(out_path, deck)
    print(f"  [+] {rel_path} -> {os.path.relpath(out_path, os.path.dirname(FLASHCARDS_MD_OUT))} ({len(cards)} cards)")
    return True


def main():
    parser = argparse.ArgumentParser(description="Convert markdown flashcard decks to JSON.")
    parser.add_argument("--spec", help="Only convert files under this specialty folder")
    parser.add_argument("--file", help="Only convert one file (relative to flashcards_md/, e.g. CVS/x.md)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing decks")
    parser.add_argument("--tag", action="store_true", help="LLM-tag cards with subtopics from subtopics.txt vocab")
    provider = parser.add_mutually_exclusive_group()
    provider.add_argument("--llm", choices=["openrouter", "together", "gemini"], help="LLM provider for tagging (default: openrouter)")
    provider.add_argument("--openrouter", action="store_true", help="Use OpenRouter (same as --llm openrouter)")
    provider.add_argument("--together", action="store_true", help="Use Together AI (same as --llm together)")
    provider.add_argument("--gemini", action="store_true", help="Use Google Gemini (same as --llm gemini)")
    parser.add_argument("--api-key", help="Override API key for an OpenAI-compatible endpoint")
    parser.add_argument("--model", help="Override model name (e.g. openai/gpt-4o, anthropic/claude-x)")
    parser.add_argument("--base-url", help="Override endpoint base URL (default: OpenRouter https://openrouter.ai/api/v1)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes")
    parser.add_argument("--verbose", action="store_true", help="Detailed logging")
    args = parser.parse_args()

    if args.llm is None:
        if args.together:
            args.llm = "together"
        elif args.gemini:
            args.llm = "gemini"
        elif args.openrouter:
            args.llm = "openrouter"
        else:
            args.llm = "openrouter"

    if not os.path.isdir(FLASHCARDS_MD_DIR):
        print(f"[X] Source dir not found: {FLASHCARDS_MD_DIR}")
        print("    Create it and drop markdown files in, e.g. flashcards_md/CVS/My Topic.md")
        sys.exit(1)

    targets = []
    if args.file:
        target = os.path.join(FLASHCARDS_MD_DIR, args.file)
        if not os.path.exists(target):
            print(f"[X] File not found: {target}")
            sys.exit(1)
        targets.append(target)
    else:
        for root, dirs, files in os.walk(FLASHCARDS_MD_DIR):
            for fn in sorted(files):
                if not fn.lower().endswith(".md"):
                    continue
                rel = os.path.relpath(root, FLASHCARDS_MD_DIR)
                if args.spec and not rel.lower().startswith(args.spec.lower()):
                    continue
                targets.append(os.path.join(root, fn))

    if not targets:
        print("[~] No markdown files found to convert.")
        return

    print(f"Converting {len(targets)} markdown file(s)...")
    converted = 0
    for t in targets:
        if convert_file(t, force=args.force, dry_run=args.dry_run, verbose=args.verbose,
                        tag=args.tag, llm=args.llm,
                        api_key=args.api_key, model=args.model, base_url=args.base_url):
            converted += 1
    print(f"Done: {converted} deck(s) {'prepared' if args.dry_run else 'written'}.")


if __name__ == "__main__":
    main()
