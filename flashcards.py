"""
flashcards.py - One script for all flashcard generation and maintenance.

Input:   flashcards_input/{Specialty}/   (.md = authored deck, pdf/txt/docx/html = raw material)
Output:  output_files/flashcards/{System}/{Subtopic}.json (unified store) + flashcards_index.json
Progress: flashcards_ledger.json (sha256 skip-if-unchanged)

Commands:
    python flashcards.py                 # generate: process every new/changed file
    python flashcards.py watch           # keep watching flashcards_input/ (new/changed only)
    python flashcards.py theory          # generate from theory notes (THEORY/processed)
    python flashcards.py tag             # LLM re-tag store cards missing subtopic tags
    python flashcards.py fronts          # generate missing front questions (QUESTION_LLM_* model)
    python flashcards.py status          # pending input + store summary
    python flashcards.py --dry-run       # preview only, no API calls (with any command)

Common flags: --spec CVS, --file CVS/x.pdf, --force, --max N, --no-tag, --no-fronts,
--llm {openrouter,gemini}, --openrouter/--gemini,
--api-key KEY --model NAME --base-url URL (custom OpenAI-compatible endpoint), --verbose
"""
import argparse
import os
import re
import sys
import time
from datetime import datetime

from acumen_core.config import (
    FLASHCARDS_DIR,
    FLASHCARDS_INPUT_DIR,
    FLASHCARDS_LEDGER_FILE,
    THEORY_PROCESSED_DIR,
    THEORY_SPEC_TO_CANONICAL,
    CHUNK_FLASHCARD,
    POLL_INTERVAL,
)
from acumen_core import flashcards as fc
from acumen_core.llm import chunk_text

MAX_RAW_CARDS = 60


# =====================================================================
# CLI helpers
# =====================================================================

def add_provider_args(parser):
    provider = parser.add_mutually_exclusive_group()
    provider.add_argument("--llm", choices=["openrouter", "gemini"],
                          help="LLM provider (default: openrouter)")
    provider.add_argument("--openrouter", action="store_true", help="Use OpenRouter (same as --llm openrouter)")
    provider.add_argument("--gemini", action="store_true", help="Use Google Gemini (same as --llm gemini)")
    parser.add_argument("--api-key", help="Override API key for an OpenAI-compatible endpoint")
    parser.add_argument("--model", help="Override model name (e.g. deepseek/deepseek-chat-v3-0324)")
    parser.add_argument("--base-url", help="Override endpoint base URL (default: OpenRouter)")


def resolve_llm(args):
    if args.llm is not None:
        return args.llm
    if args.gemini:
        return "gemini"
    return "openrouter"


def canonical_systems(specialty):
    return THEORY_SPEC_TO_CANONICAL.get(specialty) or [specialty]


def ledger_path(rel):
    return rel.replace("\\", "/")


# =====================================================================
# Core generation
# =====================================================================

def raw_cards_to_store(cards, title, system, source_file, args, tag=True):
    """Build store cards from parsed LLM cards, tag them, save, add fronts."""
    store_cards = []
    for card in cards:
        c = fc.build_card(
            "", card.get("content") or "", system, "General",
            tags=[], source="engine", source_file=source_file,
            slug_hint=card.get("subtopic") or title,
            data={"original_subtopic": card.get("subtopic") or title},
        )
        store_cards.append(c)
    if tag and store_cards:
        fc.tag_cards_with_llm(store_cards, [system], llm=args.llm, verbose=args.verbose,
                              api_key=args.api_key, model=args.model, base_url=args.base_url)
    for c in store_cards:
        c["subtopic"] = fc.canonical_subtopic(system, c["tags"][0]) if c["tags"] else "General"
    for c in store_cards:
        fc.upsert_card(c)
    if not args.no_fronts:
        fc.ensure_fronts(store_cards, verbose=args.verbose, persist=True,
                         api_key=args.api_key, model=args.model, base_url=args.base_url)
    return store_cards


def import_raw_source(path, title, text, systems, args, root=FLASHCARDS_INPUT_DIR):
    """LLM-convert a raw source file straight into store cards (no intermediate md)."""
    rel = os.path.relpath(path, root).replace("\\", "/")
    system = systems[0]
    chunks = chunk_text(text, chunk_size=CHUNK_FLASHCARD)
    all_cards = []
    for ci, chunk in enumerate(chunks):
        if args.verbose:
            print(f"    [i] Converting chunk {ci + 1}/{len(chunks)} ({len(chunk)} chars)")
        md = fc.llm_convert_to_markdown(
            chunk, title if len(chunks) == 1 else f"{title} (part {ci + 1})",
            llm=args.llm, verbose=args.verbose,
            api_key=args.api_key, model=args.model, base_url=args.base_url,
        )
        if not md:
            return None
        cards = fc.parse_llm_markdown(md, title)
        all_cards.extend(cards)
        if len(all_cards) >= MAX_RAW_CARDS:
            break
    if not all_cards:
        return None
    store_cards = raw_cards_to_store(all_cards, title, system, rel, args, tag=not args.no_tag)
    print(f"  [OK] {rel} -> store {system} ({len(store_cards)} cards)")
    return store_cards


def import_md_deck(path, systems, args):
    """Import an authored markdown deck into the store (curation preserved)."""
    rel = os.path.relpath(path, FLASHCARDS_INPUT_DIR).replace("\\", "/")
    store_cards = fc.cards_from_markdown_deck(
        path, rel, systems,
        tag=not args.no_tag, llm=args.llm, verbose=args.verbose,
        api_key=args.api_key, model=args.model, base_url=args.base_url,
    )
    if store_cards is None:
        return None
    print(f"  [OK] {rel} -> store {systems[0]} ({len(store_cards)} cards)")
    return store_cards


def import_markdown_as_is(path, systems, args):
    """--as-is: transport '==='-separated markdown blocks verbatim into the
    store (each block = one card), then LLM-enrich (tags + fronts)."""
    rel = os.path.relpath(path, FLASHCARDS_INPUT_DIR).replace("\\", "/")
    title, cards = fc.parse_separator_deck(path)
    if not cards:
        print(f"  [X] No markdown flashcards found in: {rel}")
        return None
    store_cards = fc.cards_from_parsed_deck(
        title, cards, rel, systems,
        tag=not args.no_tag, fronts=not args.no_fronts,
        llm=args.llm, verbose=args.verbose,
        api_key=args.api_key, model=args.model, base_url=args.base_url,
    )
    if store_cards is None:
        return None
    print(f"  [OK] {rel} -> store {systems[0]} ({len(store_cards)} cards, as-is)")
    return store_cards


def process_file(path, args, root=FLASHCARDS_INPUT_DIR, source="input"):
    """Process one file (md deck or raw source) with ledger skip-if-unchanged."""
    rel = os.path.relpath(path, root).replace("\\", "/")
    parts = rel.split("/")
    specialty = parts[0] if len(parts) > 1 else "Other"
    systems = canonical_systems(specialty)
    sha = fc.file_sha256(path)

    ledger = fc.load_ledger()
    entry = ledger.get(ledger_path(rel))
    if entry and entry.get("sha256") == sha and not args.force:
        print(f"  [~] Unchanged (use --force to re-run): {rel}")
        return True

    if args.dry_run:
        print(f"  [o] Would process: {rel} -> {systems[0]} ({source})")
        return True

    ext = os.path.splitext(path)[1].lower()
    try:
        if getattr(args, "as_is", False):
            if ext not in (".md", ".txt"):
                print(f"  [X] --as-is requires a .md/.txt markdown file: {rel}")
                return False
            store_cards = import_markdown_as_is(path, systems, args)
        elif ext in (".md",):
            store_cards = import_md_deck(path, systems, args)
        else:
            title, text = fc.parse_source_file(path)
            if len(text.strip()) < 50:
                print(f"  [~] Skip (too little text): {rel}")
                return False
            store_cards = import_raw_source(path, title, text, systems, args)
    except Exception as e:
        print(f"  [X] {rel}: {e}")
        return False
    if store_cards is None:
        print(f"  [X] No cards produced for: {rel}")
        return False

    ledger[ledger_path(rel)] = {
        "sha256": sha,
        "source": source,
        "processed_at": datetime.now().isoformat(),
    }
    fc.save_ledger(ledger)
    return True


def collect_targets(root, args, exts=fc.SUPPORTED_EXTS):
    if not os.path.isdir(root):
        print(f"[X] Input dir not found: {root}")
        return []
    targets = []
    if args.file:
        path = os.path.join(root, args.file)
        if not os.path.exists(path):
            print(f"[X] File not found: {path}")
            return []
        return [path]
    for r, dirs, files in os.walk(root):
        for fn in sorted(files):
            if not fn.lower().endswith(exts):
                continue
            rel = os.path.relpath(r, root)
            if args.spec and not rel.lower().startswith(args.spec.lower()):
                continue
            targets.append(os.path.join(r, fn))
    return sorted(targets)


def run_generate(args, root=FLASHCARDS_INPUT_DIR, source="input", label="flashcards_input"):
    targets = collect_targets(root, args)
    if not targets:
        print(f"[~] No supported files found in {label}.")
        return 0, 0, 0
    if args.max > 0:
        targets = targets[:args.max]
    done = skipped = failed = 0
    for t in targets:
        try:
            result = process_file(t, args, root=root, source=source)
            if result:
                done += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  [X] {t}: {e}")
            failed += 1
        time.sleep(0.3)
    return done, skipped, failed


# =====================================================================
# Commands
# =====================================================================

def cmd_generate(args):
    done, skipped, failed = run_generate(args)
    print(f"Done: {done} processed, {skipped} skipped/failed, {failed} errors.")


def cmd_theory(args):
    if not os.path.isdir(THEORY_PROCESSED_DIR):
        print(f"[X] Theory directory not found: {THEORY_PROCESSED_DIR}")
        print("    Set THEORY_PROCESSED_DIR in .env to override.")
        return
    targets = collect_targets(THEORY_PROCESSED_DIR, args, exts=(".md",))
    if not targets:
        print(f"[~] No .md notes found in {THEORY_PROCESSED_DIR}")
        return
    if args.max > 0:
        targets = targets[:args.max]
    print(f"Found {len(targets)} note(s) in {THEORY_PROCESSED_DIR}")
    done = skipped = failed = 0
    for t in targets:
        rel = os.path.relpath(t, THEORY_PROCESSED_DIR).replace("\\", "/")
        if not args.force:
            existing = [1 for _s, _sub, c in fc.store_cards_all() if c.get("source_file") == rel]
            if existing:
                print(f"  [~] Already in store (use --force to regenerate): {rel}")
                skipped += 1
                continue
        try:
            title, text = fc.parse_source_file(t)
            if len(text.strip()) < 50:
                print(f"  [~] Too short, skipping: {rel}")
                skipped += 1
                continue
            specialty = rel.split("/")[0]
            systems = canonical_systems(specialty)
            if args.dry_run:
                print(f"  [o] Would process: {rel} -> {systems[0]}")
                done += 1
                continue
            store_cards = import_raw_source(t, title, text, systems, args,
                                            root=THEORY_PROCESSED_DIR)
            if store_cards:
                done += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [X] {rel}: {e}")
            failed += 1
        time.sleep(0.3)
    print(f"Done: {done} processed, {skipped} skipped, {failed} failed.")


def cmd_tag(args):
    cards = list(fc.store_cards_all())
    if not cards:
        print("[~] No store cards found.")
        return
    missing = [c for _s, _sub, c in cards if not (c.get("tags") or [])]
    targets = missing if not args.force else [c for _s, _sub, c in cards]
    if not targets:
        print("[~] No untagged cards.")
        return
    print(f"  [+] Tagging {len(targets)} card(s)...")
    if args.dry_run:
        print(f"  [o] Would tag {len(targets)} card(s).")
        return
    by_system = {}
    for c in targets:
        by_system.setdefault(c.get("system") or "General", []).append(c)
    for system, group in by_system.items():
        fc.tag_cards_with_llm(group, [system], llm=args.llm, verbose=args.verbose,
                              api_key=args.api_key, model=args.model, base_url=args.base_url)
        for c in group:
            c["subtopic"] = fc.canonical_subtopic(system, c["tags"][0]) if c["tags"] else "General"
            fc.upsert_card(c)
    tagged = sum(1 for c in targets if c.get("tags"))
    print(f"Done: {tagged}/{len(targets)} card(s) tagged.")


def cmd_fronts(args):
    cards = [c for _s, _sub, c in fc.store_cards_all()]
    missing = [c for c in cards if not (c.get("front") or "").strip()]
    if not missing:
        print("[~] All cards already have fronts.")
        return
    print(f"  [+] Generating fronts for {len(missing)} card(s)...")
    if args.dry_run:
        print(f"  [o] Would generate {len(missing)} front(s).")
        return
    n = fc.ensure_fronts(missing, verbose=args.verbose, persist=True,
                         api_key=args.api_key, model=args.model, base_url=args.base_url)
    print(f"Done: {n}/{len(missing)} front(s) generated.")


def cmd_status(args):
    def pending(root):
        out = []
        if not os.path.isdir(root):
            return out
        ledger = fc.load_ledger()
        for r, dirs, files in os.walk(root):
            for fn in sorted(files):
                if not fn.lower().endswith(fc.SUPPORTED_EXTS):
                    continue
                path = os.path.join(r, fn)
                rel = os.path.relpath(path, root).replace("\\", "/")
                entry = ledger.get(ledger_path(rel))
                if not entry or entry.get("sha256") != fc.file_sha256(path):
                    out.append(rel)
        return out

    input_pending = pending(FLASHCARDS_INPUT_DIR)
    theory_files = collect_targets(THEORY_PROCESSED_DIR, args, exts=(".md",)) if os.path.isdir(THEORY_PROCESSED_DIR) else []
    in_store = {c.get("source_file") for _s, _sub, c in fc.store_cards_all()}
    theory_pending = [os.path.relpath(t, THEORY_PROCESSED_DIR).replace("\\", "/")
                      for t in theory_files
                      if os.path.relpath(t, THEORY_PROCESSED_DIR).replace("\\", "/") not in in_store]
    idx = fc.load_flashcards_index()
    cards = list(fc.store_cards_all())
    by_source = {}
    for _s, _sub, c in cards:
        by_source[c.get("source") or "?"] = by_source.get(c.get("source") or "?", 0) + 1
    print(f"flashcards_input: {len(input_pending)} pending / {len(collect_targets(FLASHCARDS_INPUT_DIR, args))} total")
    print(f"theory notes:     {len(theory_pending)} pending / {len(theory_files)} total")
    print(f"store:            {idx.get('total_cards', len(cards))} cards, {len(idx.get('systems', {}))} systems, "
          f"{sum(len(s) for s in idx.get('systems', {}).values())} decks  ({by_source})")
    if input_pending:
        print("pending input files:")
        for rel in input_pending:
            print(f"  - {rel}")


def cmd_watch(args):
    print(f"Watching {FLASHCARDS_INPUT_DIR} (Ctrl+C to stop)...")
    tick = 0
    try:
        while True:
            tick += 1
            try:
                cmd_generate(args)
            except Exception as e:
                print(f"  [X] watch cycle {tick}: {e}")
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\nStopped.")


# =====================================================================
# Main
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate and maintain flashcards (one script).")
    parser.add_argument("--spec", help="Only process this specialty subfolder (e.g. CVS)")
    parser.add_argument("--file", help="Only process one file (relative to input dir, e.g. CVS/x.pdf)")
    parser.add_argument("--force", action="store_true", help="Re-run even if unchanged")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no API calls")
    parser.add_argument("--max", type=int, default=0, help="Process at most N files (0 = unlimited)")
    parser.add_argument("--no-tag", action="store_true", help="Skip LLM subtopic tagging")
    parser.add_argument("--no-fronts", action="store_true", help="Skip front-question generation (raw sources)")
    parser.add_argument("--verbose", action="store_true", help="Detailed logging")
    parser.add_argument("--as-is", action="store_true",
                        help="Import one '==='-separated markdown file verbatim (requires --file)")
    add_provider_args(parser)

    sub = parser.add_subparsers(dest="command")
    for name, help_text, func in [
        ("generate", "Process every new/changed file in flashcards_input/ (default)", cmd_generate),
        ("watch", "Keep watching flashcards_input/ for new/changed files", cmd_watch),
        ("theory", "Generate flashcards from theory notes (THEORY/processed)", cmd_theory),
        ("tag", "Re-tag store cards missing subtopic tags", cmd_tag),
        ("fronts", "Generate missing front questions for store cards", cmd_fronts),
        ("status", "Show pending input and store summary", cmd_status),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--spec", help="Only process this specialty subfolder (e.g. CVS)")
        p.add_argument("--file", help="Only process one file (relative to input dir, e.g. CVS/x.pdf)")
        p.add_argument("--force", action="store_true", help="Re-run even if unchanged")
        p.add_argument("--dry-run", action="store_true", help="Preview only, no API calls")
        p.add_argument("--max", type=int, default=0, help="Process at most N files (0 = unlimited)")
        p.add_argument("--no-tag", action="store_true", help="Skip LLM subtopic tagging")
        p.add_argument("--no-fronts", action="store_true", help="Skip front-question generation (raw sources)")
        p.add_argument("--verbose", action="store_true", help="Detailed logging")
        if name == "generate":
            p.add_argument("--as-is", action="store_true",
                           help="Import one '==='-separated markdown file verbatim (requires --file)")
        add_provider_args(p)
        p.set_defaults(func=func)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        args.func = cmd_generate
        args.command = "generate"
    args.llm = resolve_llm(args)

    if args.as_is:
        if not args.file:
            print("[X] --as-is requires --file (e.g. --as-is --file CVS/deck.md)")
            sys.exit(1)
        path = os.path.join(FLASHCARDS_INPUT_DIR, args.file)
        ext = os.path.splitext(path)[1].lower()
        if not os.path.isfile(path):
            print(f"[X] --as-is file not found: {path}")
            sys.exit(1)
        if ext not in (".md", ".txt"):
            print("[X] --as-is requires a .md/.txt markdown file.")
            sys.exit(1)

    if not args.dry_run and args.command in ("generate", "watch", "theory", "tag", "fronts"):
        from acumen_core.config import FLASHCARD_LLM_API_KEY, OPENROUTER_API_KEY
        if not (FLASHCARD_LLM_API_KEY or OPENROUTER_API_KEY or args.api_key):
            print("[X] No flashcard LLM key set. Add FLASHCARD_LLM_API_KEY/OPENROUTER_API_KEY to .env or pass --api-key.")
            sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
