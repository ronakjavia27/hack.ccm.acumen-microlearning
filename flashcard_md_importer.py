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
    python flashcard_md_importer.py --questions     # LLM front questions in the md (idempotent, separate model via QUESTION_LLM_*)
    python flashcard_md_importer.py --gemini        # explicit provider flags (same as --llm)
    python flashcard_md_importer.py --api-key sk-xxx --model my/model --base-url https://...  # custom OpenAI-compatible endpoint
    python flashcard_md_importer.py --dry-run       # preview only
"""

import os
import re
import sys
import argparse
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from acumen_core.config import FLASHCARDS_MD_DIR


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


def _load_existing_meta(source_file):
    """Load {card_index: (tags, status)} from the store for a given source md
    so re-converts keep console curation (tags, preserve/discard) by position.
    The authored md is the source of truth, so card order is stable."""
    from acumen_core import flashcards as fc
    meta = {}
    try:
        for system, subtopic, c in fc.store_cards_all():
            if c.get("source_file") != source_file:
                continue
            idx = len(meta)
            meta[idx] = (c.get("tags") or [], c.get("status") or "pending",
                         c.get("edit_history") or [])
    except Exception:
        pass
    return meta


def convert_file(md_path, force=False, dry_run=False, verbose=False, tag=False, llm="openrouter",
                 api_key=None, model=None, base_url=None):
    """Convert one markdown file into store cards (source 'md')."""
    from acumen_core import flashcards as fc
    from acumen_core.config import THEORY_SPEC_TO_CANONICAL
    rel_path = os.path.relpath(md_path, FLASHCARDS_MD_DIR).replace("\\", "/")
    parts = rel_path.split("/")
    specialty = parts[0] if len(parts) > 1 else "Other"
    stem = os.path.splitext(os.path.basename(md_path))[0]

    title, cards = parse_markdown_deck(md_path)
    if not cards:
        if verbose:
            print(f"  [~] Skip (no card content): {rel_path}")
        return False

    slug = slugify(stem)
    systems = THEORY_SPEC_TO_CANONICAL.get(specialty) or [specialty]
    system = systems[0]
    meta = _load_existing_meta(rel_path)
    store_cards = []
    for i, card in enumerate(cards):
        front, back = fc.parse_card_content(card["content"])
        c = fc.build_card(
            front or "", back or card["content"], system, "General",
            tags=card.get("tags") or [], source="md", source_file=rel_path,
            slug_hint=card["subtopic"],
            data={"original_subtopic": card["subtopic"]},
        )
        old_tags, old_status, old_history = meta.get(i, ([], "pending", []))
        c["tags"] = old_tags
        c["status"] = old_status
        c["edit_history"] = list(old_history or [])
        store_cards.append(c)

    if dry_run:
        print(f"  [o] Would store: {rel_path} -> {system} ({len(cards)} cards)")
        return True

    if tag:
        fc.tag_cards_with_llm(store_cards, systems, llm=llm, verbose=verbose,
                              api_key=api_key, model=model, base_url=base_url)
    for c in store_cards:
        if c["tags"]:
            c["subtopic"] = fc.canonical_subtopic(system, c["tags"][0])
        else:
            c["subtopic"] = "General"
    for c in store_cards:
        fc.upsert_card(c)
    print(f"  [+] {rel_path} -> store {system} ({len(cards)} cards)")
    return True


def _body_has_divider(body):
    """True if the card body already contains a front/back divider."""
    return bool(re.search(r"\n\s*(?:---|\*\*\*)\s*\n", "\n" + (body or "") + "\n"))


def _write_atomic(path, text):
    """Atomic UTF-8 write with LF line endings (preserves repo convention)."""
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".mdq-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def add_card_questions(md_path, dry_run=False, verbose=False, api_key=None, model=None, base_url=None):
    """LLM-generate a front question per card and write it into the markdown
    as '<question>\n\n---\n\n<body>' so portal flip mode has real fronts.

    Uses the separate QUESTION_LLM_* config (a different provider/model than
    every other pipeline; override via --api-key/--model/--base-url).
    Idempotent: cards already containing a --- divider are skipped. The file
    is rewritten in the authoring convention, then re-converted to JSON with
    console curation (tags/status/edit_history) preserved.

    Returns (updated_cards, total_cards)."""
    from acumen_core.flashcards import generate_card_question

    with open(md_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().split("\n")

    title, cards = parse_markdown_deck(md_path)
    if not cards:
        return 0, 0

    updated = 0
    for card in cards:
        if _body_has_divider(card["content"]):
            continue
        if dry_run:
            updated += 1
            continue
        question = generate_card_question(title, card["subtopic"], card["content"],
                                          api_key=api_key, model=model, base_url=base_url,
                                          verbose=verbose)
        if not question:
            if verbose:
                print(f"    [~] No question for '{card['subtopic']}' (skipped)")
            continue
        card["content"] = f"{question}\n\n---\n\n{card['content']}"
        updated += 1
        if verbose:
            print(f"    [i] Question: {question}")

    if dry_run:
        print(f"  [o] Would add questions to {os.path.relpath(md_path, FLASHCARDS_MD_DIR)}: {updated}/{len(cards)} cards")
        return updated, len(cards)
    if updated == 0:
        if verbose:
            print(f"  [~] No new questions for {os.path.relpath(md_path, FLASHCARDS_MD_DIR)} (already divided or LLM skipped)")
        return 0, len(cards)

    first_card_line = None
    for i, line in enumerate(lines):
        if line.strip().startswith("## "):
            first_card_line = i
            break
    if first_card_line is None:
        prefix = []
        if not lines or not lines[0].lstrip().startswith("# "):
            prefix = ["# " + title]
    else:
        prefix = lines[:first_card_line]

    sections = []
    for card in cards:
        sections.append(f"## {card['subtopic']}")
        sections.append("")
        sections.append(card["content"])
        sections.append("")

    rebuilt = ("\n".join(ln.rstrip() for ln in prefix).rstrip() + "\n\n" + "\n".join(sections)).rstrip() + "\n"
    _write_atomic(md_path, rebuilt)
    print(f"  [+] Questions written: {os.path.relpath(md_path, FLASHCARDS_MD_DIR)} ({updated}/{len(cards)} cards)")
    return updated, len(cards)


def main():
    parser = argparse.ArgumentParser(description="Convert markdown flashcard decks to JSON.")
    parser.add_argument("--spec", help="Only convert files under this specialty folder")
    parser.add_argument("--file", help="Only convert one file (relative to flashcards_md/, e.g. CVS/x.md)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing decks")
    parser.add_argument("--tag", action="store_true", help="LLM-tag cards with subtopics from subtopics.txt vocab")
    parser.add_argument("--questions", action="store_true", help="LLM-generate front questions per card (writes '<question> --- <body>' in the md, idempotent)")
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
        if args.questions:
            add_card_questions(t, dry_run=args.dry_run, verbose=args.verbose,
                               api_key=args.api_key, model=args.model, base_url=args.base_url)
            if args.dry_run:
                continue
            convert_file(t, force=True, verbose=args.verbose, tag=args.tag, llm=args.llm,
                         api_key=args.api_key, model=args.model, base_url=args.base_url)
            continue
        if convert_file(t, force=args.force, dry_run=args.dry_run, verbose=args.verbose,
                        tag=args.tag, llm=args.llm,
                        api_key=args.api_key, model=args.model, base_url=args.base_url):
            converted += 1
    print(f"Done: {converted} deck(s) {'prepared' if args.dry_run else 'written'}.")


if __name__ == "__main__":
    main()
