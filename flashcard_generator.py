"""
flashcard_generator.py - Ingest md/pdf/docx/txt/html sources, convert them via
LLM into markdown flashcard decks (flashcards_md/), convert to JSON decks, and
tag every card with subtopics from the subtopics.txt vocabulary.

Flow per file:
    flashcards_input/{Spec}/file.ext
        -> LLM refine/summarise/reformat -> flashcards_md/{Spec}/{slug}.md
        -> flashcard_md_importer          -> output_files/flashcards_md/{Spec}/{slug}.json
        -> LLM tagging                    -> card "tags" from subtopics vocab
    flashcards_ledger.json tracks source sha256 so unchanged files are skipped.

Usage:
    python flashcard_generator.py                      # all files in flashcards_input/
    python flashcard_generator.py --spec CVS           # one specialty folder
    python flashcard_generator.py --file "CVS/my.pdf"  # one file
    python flashcard_generator.py --dry-run            # preview only, no API calls
    python flashcard_generator.py --force              # re-run even if source unchanged
    python flashcard_generator.py --no-tag             # skip LLM tagging pass
    python flashcard_generator.py --tag-only           # re-tag existing decks only
    python flashcard_generator.py --llm gemini         # provider: openrouter|together|gemini
    python flashcard_generator.py --openrouter         # explicit provider flags (same as --llm)
    python flashcard_generator.py --gemini
    python flashcard_generator.py --together
    python flashcard_generator.py --api-key sk-xxx --model my/model --base-url https://...  # custom OpenAI-compatible endpoint
"""

import argparse
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from acumen_core.config import (
    FLASHCARDS_INPUT_DIR,
    FLASHCARDS_MD_DIR,
    CHUNK_FLASHCARD,
)
from acumen_core.flashcards import (
    SUPPORTED_EXTS,
    file_sha256,
    llm_convert_to_markdown,
    load_ledger,
    parse_llm_markdown,
    parse_source_file,
    save_ledger,
)
from acumen_core.llm import chunk_text
from flashcard_md_importer import convert_file, slugify


def build_deck_markdown(title, cards):
    parts = [f"# {title}"]
    for c in cards:
        parts.append(f"## {c['subtopic']}\n\n{c['content']}")
    return "\n\n".join(parts)


def generate_deck_markdown(path, title, text, llm, verbose=False, dry_run=False, api_key=None, model=None, base_url=None):
    """Run LLM convert pass over (possibly chunked) source text -> markdown."""
    if dry_run:
        return None
    chunks = chunk_text(text, chunk_size=CHUNK_FLASHCARD)
    all_cards = []
    for ci, chunk in enumerate(chunks):
        if verbose:
            print(f"    [i] Converting chunk {ci + 1}/{len(chunks)} ({len(chunk)} chars)")
        md = llm_convert_to_markdown(
            chunk, title if len(chunks) == 1 else f"{title} (part {ci + 1})",
            llm=llm, verbose=verbose, api_key=api_key, model=model, base_url=base_url,
        )
        if not md:
            return None
        cards = parse_llm_markdown(md, title)
        all_cards.extend(cards)
        if len(all_cards) > 60:
            break
    if not all_cards:
        return None
    return build_deck_markdown(title, all_cards)


def process_file(path, args):
    rel = os.path.relpath(path, FLASHCARDS_INPUT_DIR)
    parts = rel.split(os.sep)
    specialty = parts[0] if len(parts) > 1 else "Other"
    stem = os.path.splitext(os.path.basename(path))[0]

    try:
        title, text = parse_source_file(path)
    except ValueError as e:
        print(f"  [X] {rel}: {e}")
        return False
    except Exception as e:
        print(f"  [X] {rel}: parse failed ({e})")
        return False

    if len(text.strip()) < 50:
        print(f"  [~] Skip (too little text): {rel} ({len(text.strip())} chars)")
        return False

    slug = slugify(stem)
    md_path = os.path.join(FLASHCARDS_MD_DIR, specialty, f"{slug}.md")
    sha = file_sha256(path)

    ledger = load_ledger()
    entry = ledger.get(rel)
    unchanged = entry and entry.get("sha256") == sha and os.path.exists(md_path)
    if unchanged and not args.force:
        print(f"  [~] Unchanged (use --force to re-run): {rel}")
        return True

    print(f"  [+] {rel} ({specialty})")
    if args.dry_run:
        print(f"      Title: {title} | {len(text)} chars -> {os.path.relpath(md_path, FLASHCARDS_MD_DIR)}")
        return True

    markdown = generate_deck_markdown(
        path, title, text, args.llm,
        verbose=args.verbose, dry_run=False,
        api_key=args.api_key, model=args.model, base_url=args.base_url,
    )
    if not markdown:
        print(f"  [X] LLM produced no cards for: {rel}")
        return False

    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"      -> {os.path.relpath(md_path, FLASHCARDS_MD_DIR)}")

    if not convert_file(md_path, force=True, dry_run=False, verbose=args.verbose,
                        tag=not args.no_tag, llm=args.llm,
                        api_key=args.api_key, model=args.model, base_url=args.base_url):
        print(f"  [X] Importer failed for: {rel}")
        return False

    ledger[rel] = {
        "sha256": sha,
        "md": f"{specialty}/{slug}.md",
        "title": title,
        "processed_at": datetime.now().isoformat(),
    }
    save_ledger(ledger)
    return True


def tag_existing_decks(args):
    """Re-tag all store cards (or those missing tags) without regenerating."""
    from acumen_core import flashcards as fc
    cards = [c for _, _, c in fc.store_cards_all()]
    if not cards:
        print("[~] No store cards found.")
        return 0
    missing = [c for c in cards if not (c.get("tags") or [])]
    targets = missing if not args.force else cards
    if not targets:
        print("[~] No untagged cards.")
        return 0
    print(f"  [+] Tagging {len(targets)} card(s)...")
    if args.dry_run:
        return len(targets)
    for c in targets:
        systems = [c.get("system") or "General"]
        fc.tag_cards_with_llm([c], systems, llm=args.llm, verbose=args.verbose,
                              api_key=args.api_key, model=args.model, base_url=args.base_url)
        if c["tags"]:
            c["subtopic"] = fc.canonical_subtopic(c["system"], c["tags"][0])
        else:
            c["subtopic"] = "General"
        fc.upsert_card(c)
    print(f"Done: {len(targets)} card(s) re-tagged.")
    return len(targets)


def collect_targets(args):
    if not os.path.isdir(FLASHCARDS_INPUT_DIR):
        print(f"[X] Input dir not found: {FLASHCARDS_INPUT_DIR}")
        print("    Create it, e.g. flashcards_input/CVS/my.pdf")
        sys.exit(1)
    targets = []
    if args.file:
        path = os.path.join(FLASHCARDS_INPUT_DIR, args.file)
        if not os.path.exists(path):
            print(f"[X] File not found: {path}")
            sys.exit(1)
        return [path]
    for root, dirs, files in os.walk(FLASHCARDS_INPUT_DIR):
        for fn in sorted(files):
            if not fn.lower().endswith(SUPPORTED_EXTS):
                continue
            rel = os.path.relpath(root, FLASHCARDS_INPUT_DIR)
            if args.spec and not rel.lower().startswith(args.spec.lower()):
                continue
            targets.append(os.path.join(root, fn))
    return targets


def main():
    parser = argparse.ArgumentParser(description="Generate tagged flashcard decks from md/pdf/docx/txt/html sources.")
    parser.add_argument("--dir", help="Input directory (default: flashcards_input/)")
    parser.add_argument("--spec", help="Only process this specialty subfolder (e.g. CVS)")
    parser.add_argument("--file", help="Only process one file (relative to input dir, e.g. CVS/x.pdf)")
    parser.add_argument("--force", action="store_true", help="Re-run even if source is unchanged")
    parser.add_argument("--dry-run", action="store_true", help="Preview only: parse + report, no API calls")
    parser.add_argument("--no-tag", action="store_true", help="Skip the LLM subtopic tagging pass")
    parser.add_argument("--tag-only", action="store_true", help="Re-tag existing decks only")
    provider = parser.add_mutually_exclusive_group()
    provider.add_argument("--llm", choices=["openrouter", "together", "gemini"], help="LLM provider (default: openrouter)")
    provider.add_argument("--openrouter", action="store_true", help="Use OpenRouter (same as --llm openrouter)")
    provider.add_argument("--together", action="store_true", help="Use Together AI (same as --llm together)")
    provider.add_argument("--gemini", action="store_true", help="Use Google Gemini (same as --llm gemini)")
    parser.add_argument("--api-key", help="Override API key for an OpenAI-compatible endpoint")
    parser.add_argument("--model", help="Override model name (e.g. openai/gpt-4o, anthropic/claude-x)")
    parser.add_argument("--base-url", help="Override endpoint base URL (default: OpenRouter https://openrouter.ai/api/v1)")
    parser.add_argument("--max", type=int, default=0, help="Process at most N files (0 = unlimited)")
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

    global FLASHCARDS_INPUT_DIR
    if args.dir:
        FLASHCARDS_INPUT_DIR = args.dir

    if args.tag_only:
        tag_existing_decks(args)
        return

    targets = collect_targets(args)
    if not targets:
        print("[~] No supported source files found.")
        return
    if args.max > 0:
        targets = targets[: args.max]

    override_note = ""
    if args.api_key or args.model:
        override_note = f" [custom endpoint{', model ' + args.model if args.model else ''}]"
    print(f"Processing {len(targets)} file(s) with --llm {args.llm}{override_note}...")
    done = 0
    for t in targets:
        try:
            if process_file(t, args):
                done += 1
        except Exception as e:
            print(f"  [X] {t}: {e}")
    print(f"Done: {done}/{len(targets)} file(s) {'previewed' if args.dry_run else 'processed'}.")


if __name__ == "__main__":
    main()
