"""
flashcard_engine.py - Generate structured study flashcards from theory notes.

Scans THEORY/processed/ recursively for .md files, sends each to OpenRouter
LLM for subtopic extraction, and saves results as structured JSON decks to
output_files/flashcards/{specialty}/{slug}.json.

Usage:
    python flashcard_engine.py                  # skip existing, only new
    python flashcard_engine.py --force           # re-generate all
    python flashcard_engine.py --max             # generate more cards (10-15 per note)
    python flashcard_engine.py --limit N         # process only first N files
    python flashcard_engine.py --model <model>   # override model
    python flashcard_engine.py --dry-run         # show what would be processed
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime

from acumen_core.config import FLASHCARDS_DIR, OPENROUTER_MODEL
from acumen_core.llm import call_openrouter_api, _get_openrouter_client

THEORY_DIR = "C:/RONAK/AI Projects/ACUMEN/THEORY/processed"

FLASHCARD_SYSTEM_PROMPT_TMPL = """You are an expert ICU clinician and medical educator. Your task is to distill a medical note into a set of dense, clinically actionable study cards.

Analyze the provided note and identify {card_count} high-yield subtopics that represent clinically meaningful domains of understanding.

Prioritize subtopics such as:
- Pathophysiology / hemodynamics
- Classification / phenotypes
- Diagnostic approach
- Hemodynamic monitoring
- Management (vasopressors, inotropes, fluids)
- Advanced therapies (MCS, ECMO/ECLS)
- Special situations / etiologies
- Prognosis or scoring systems
- Key trials / evidence
- Complications / contraindications
- Dosing quick-reference

For each subtopic, generate a concise structured summary ({word_range} words).

Output valid JSON with a "cards" array. Each card object has:
  - "subtopic": string (the subtopic name)
  - "content": string with this exact format:
**Core concept:** (1-2 lines explaining mechanism or principle)

**Key parameters:** (thresholds, definitions, hemodynamic targets)

**Clinical application:** (how it guides bedside decisions)

**Interventions:** (drug choices, doses if relevant, device strategies)

**Pitfalls:** (common errors, contraindications, or nuances)

Rules:
- Focus on ICU-relevant, decision-driving information only
- Avoid generic textbook descriptions
- Prefer mechanisms + thresholds over narrative
- Include drug doses or device criteria where applicable
- Avoid redundancy between subtopics
- Content must be dense, structured, and clinically actionable

Example card: {open_brace}
  "subtopic": "SCAI Classification",
  "content": "**Core concept:** SCAI stages classify cardiogenic shock severity from at risk to extremis, guiding escalation of therapy.\\n\\n**Key parameters:** Stage A (at risk), B (beginning: hypotension responding to fluids), C (classic: SBP <90, lactate >2, inotropes), D (deteriorating: escalating doses), E (extremis: refractory, ECPR).\\n\\n**Clinical application:** Stage dictates initial management pathway — fluids for B, inotropes for C, MCS consideration for D/E.\\n\\n**Interventions:** Stage C: dobutamine 2.5-20 mcg/kg/min + norepinephrine 0.01-3 mcg/kg/min. Stage D/E: escalate to MCS (Impella, VA-ECMO).\\n\\n**Pitfalls:** Do not delay MCS referral for stage D/E while awaiting improvement with drugs alone. Lactate clearance is the best marker of response."
{close_brace}

Output ONLY valid JSON with a "cards" key. No preamble, no markdown fences, no commentary."""


def slugify(text):
    """Convert text to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def extract_title_from_md(content, filepath):
    """Extract document title from the first few lines, or use filename."""
    lines = content.split('\n')
    for line in lines[:20]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('# '):
            return stripped[2:].strip()
        m = re.match(r'^\*\*(\d+\.?\s*)?([^*]+?)\*\*\s*:?\s*$', stripped)
        if m:
            candidate = m.group(2).strip()
            if candidate and not candidate.startswith(('•', '-', '*', '·')):
                return candidate
    name = os.path.splitext(os.path.basename(filepath))[0]
    name = re.sub(r'^\d+\s*', '', name)
    return name.strip()


def clean_markdown(text):
    """Strip excessive repeated content. Some notes have the same content repeated."""
    text = text.encode('utf-8', errors='replace').decode('utf-8')
    lines = text.split('\n')
    seen = set()
    cleaned = []
    for line in lines:
        key = line.strip().lower()
        if key and len(key) > 20 and key in seen:
            continue
        if len(key) > 20:
            seen.add(key)
        cleaned.append(line)
    return '\n'.join(cleaned)


def generate_flashcards(md_content, filepath, model_override=None, max_mode=False):
    """Send markdown content to LLM and return parsed cards."""
    title = extract_title_from_md(md_content, filepath)
    cleaned = clean_markdown(md_content)

    if max_mode:
        card_count = "10-15"
        word_range = "40-80"
    else:
        card_count = "5-8"
        word_range = "50-120"

    system_prompt = FLASHCARD_SYSTEM_PROMPT_TMPL.format(card_count=card_count, word_range=word_range, open_brace="{", close_brace="}")

    user_prompt = f"""Medical note title: {title}

Note content:
{cleaned[:12000]}

Generate {card_count} high-yield study cards from this note following the specified format."""

    try:
        if model_override:
            from acumen_core.llm import execute_openai_compat
            from acumen_core.config import (
                FLASHCARD_LLM_API_KEY,
                FLASHCARD_LLM_BASE_URL,
                TEMPERATURE_FLASHCARDS,
                MAX_TOKENS_FLASHCARDS,
            )
            raw = execute_openai_compat(
                system_prompt, user_prompt,
                api_key=FLASHCARD_LLM_API_KEY, model=model_override,
                base_url=FLASHCARD_LLM_BASE_URL, json_mode=False,
                temperature=TEMPERATURE_FLASHCARDS, max_tokens=MAX_TOKENS_FLASHCARDS,
            )
        else:
            from acumen_core.flashcards import flashcard_llm
            raw = flashcard_llm(system_prompt, user_prompt)
    except Exception as e:
        print(f"  [X] LLM call failed: {e}")
        return None

    import json
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        import re
        m = re.search(r'(\{.*"cards".*\})', raw, re.DOTALL)
        if m:
            try:
                result = json.loads(m.group(1))
            except json.JSONDecodeError:
                print(f"  [X] Could not parse LLM response as JSON")
                return None
        else:
            print(f"  [X] No JSON found in LLM response")
            return None

    if not result or "cards" not in result:
        print(f"  [X] No 'cards' key in LLM response")
        return None

    cards = result["cards"]
    if not isinstance(cards, list) or len(cards) == 0:
        print(f"  [X] Empty or invalid cards array")
        return None

    for i, card in enumerate(cards):
        card.setdefault("status", "pending")

    return cards


def process_file(md_path, force=False, model_override=None, dry_run=False, max_mode=False):
    """Process a single .md file and upsert its cards into the unified store."""
    from acumen_core import flashcards as fc
    from acumen_core.config import THEORY_SPEC_TO_CANONICAL
    rel_path = os.path.relpath(md_path, THEORY_DIR).replace("\\", "/")
    specialty = rel_path.split("/")[0] if "/" in rel_path else "Other"
    base_name = os.path.splitext(os.path.basename(md_path))[0]
    slug = slugify(base_name)

    systems = THEORY_SPEC_TO_CANONICAL.get(specialty) or [specialty]
    system = systems[0]

    existing = [c for _, _, c in fc.store_cards_all() if c.get("source_file") == rel_path]
    if not force and existing:
        print(f"  [SKIP] {rel_path} — already in store ({len(existing)} cards, use --force to regenerate)")
        return None

    if dry_run:
        print(f"  [DRY-RUN] Would process: {rel_path} -> store {system}")
        return None

    print(f"  [READ] {rel_path}")
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"  [X] Read error: {e}")
        return None

    if len(content.strip()) < 50:
        print(f"  [X] Too short, skipping")
        return None

    title = extract_title_from_md(content, md_path)
    print(f"  [GEN] Generating flashcards for: {title}")

    cards = generate_flashcards(content, md_path, model_override, max_mode=max_mode)
    if cards is None:
        return None

    store_cards = []
    for card in cards:
        c = fc.build_card(
            "", card.get("content") or "", system, "General",
            tags=[], source="engine", source_file=rel_path,
            slug_hint=card.get("subtopic") or title,
            data={"original_subtopic": card.get("subtopic")},
        )
        store_cards.append(c)

    fc.tag_cards_with_llm(store_cards, systems, verbose=True)
    for c in store_cards:
        if c["tags"]:
            c["subtopic"] = fc.canonical_subtopic(system, c["tags"][0])
        else:
            c["subtopic"] = "General"
        fc.upsert_card(c)

    print(f"  [OK] {len(store_cards)} cards -> store {system}")
    return {"title": title, "cards": store_cards}


def main():
    parser = argparse.ArgumentParser(description="Generate flashcards from theory notes")
    parser.add_argument("--force", action="store_true", help="Re-generate existing flashcards")
    parser.add_argument("--max", action="store_true", help="Max mode: generate 10-15 cards per note instead of 5-8")
    parser.add_argument("--limit", type=int, default=0, help="Process only first N files")
    parser.add_argument("--model", type=str, default=None, help="Override LLM model")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")
    args = parser.parse_args()

    if not args.dry_run:
        from acumen_core.config import OPENROUTER_API_KEY
        if not OPENROUTER_API_KEY:
            print("[X] OPENROUTER_API_KEY not set in .env")
            print("    Add your key to .env or use --dry-run to preview")
            sys.exit(1)

    if not os.path.isdir(THEORY_DIR):
        print(f"[X] Theory directory not found: {THEORY_DIR}")
        sys.exit(1)

    md_files = []
    for root, dirs, files in os.walk(THEORY_DIR):
        for f in sorted(files):
            if f.endswith(".md"):
                md_files.append(os.path.join(root, f))
    if args.limit:
        md_files = md_files[:args.limit]

    print(f"Found {len(md_files)} .md files in {THEORY_DIR}")
    print(f"Output directory: {FLASHCARDS_DIR}")
    if args.model:
        print(f"Model override: {args.model}")
    if args.max:
        print(f"Max mode: 10-15 cards per note")
    if args.limit:
        print(f"Limit: first {args.limit} files")
    print()

    if args.dry_run:
        print(f"\n{'='*40}")
        print(f"Dry run complete. Would process up to {len(md_files)} files.")
        print(f"Flashcards would be saved to: {FLASHCARDS_DIR}")
        print(f"Use --force to regenerate existing files.")
        return

    processed = 0
    skipped = 0
    failed = 0

    for md_path in md_files:
        rel_path = os.path.relpath(md_path, THEORY_DIR).replace("\\", "/")
        specialty = rel_path.split("/")[0] if "/" in rel_path else "Other"
        from acumen_core import flashcards as fc
        existing = [c for _, _, c in fc.store_cards_all() if c.get("source_file") == rel_path]
        if not args.force and existing:
            skipped += 1
            continue
        result = process_file(md_path, force=args.force, model_override=args.model, dry_run=False, max_mode=args.max)
        if result is None:
            failed += 1
        else:
            processed += 1
        time.sleep(0.5)

    print(f"\n{'='*40}")
    print(f"Done: {processed} generated, {skipped} skipped, {failed} failed")
    print(f"Flashcards in: {FLASHCARDS_DIR}")


if __name__ == "__main__":
    main()
