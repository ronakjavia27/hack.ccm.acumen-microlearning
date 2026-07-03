#!/usr/bin/env python3
"""
pearl_updater_together.py — Batch-update pearl fields via Together AI.

A unified, extensible framework for correcting or polishing pearl fields
in pearls.json using Together AI (openai/gpt-oss-20b primary,
openai/gpt-oss-120b fallback). Supports multiple "modes" for different
correction operations.

Modes:
  correct_system   - Reclassify the system/specialty field
  correct_topic    - Generate/improve the topic field
  correct_type     - Reclassify the article type field
  polish_pearl     - Rewrite pearl text for grammar/clarity

Usage:
  python pearl_updater_together.py --mode correct_system
  python pearl_updater_together.py --mode correct_system --only-other
  python pearl_updater_together.py --mode correct_system --only-other --dry-run
  python pearl_updater_together.py --mode correct_topic --batch 50
  python pearl_updater_together.py --mode polish_pearl --batch 25 --verbose
  python pearl_updater_together.py --mode correct_type --resume
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
ENV_PATH = SCRIPT_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
PRIMARY_MODEL = "openai/gpt-oss-20b"
FALLBACK_MODEL = "openai/gpt-oss-120b"
BATCH_SIZE = 25
TEMPERATURE = 0.1
MAX_TOKENS = 8192
MAX_RETRIES = 2
RETRY_DELAY = 5
API_TIMEOUT = 300

SPECIALTIES_FILE = SCRIPT_DIR / "specialties.txt"
ARTICLE_TYPES_FILE = SCRIPT_DIR / "article_types.txt"
PEARLS_FILE = SCRIPT_DIR / "pearls.json"
PROGRESS_FILE = SCRIPT_DIR / "pearl_updater_progress.json"
CHANGE_LOG_FILE = SCRIPT_DIR / "pearl_updater_changes.jsonl"


# ── IO ──────────────────────────────────────────────────────────────────

def load_list(path):
    return [line.strip() for line in path.read_text(encoding="utf-8").strip().splitlines() if line.strip()]


def load_specialties():
    raw = load_list(SPECIALTIES_FILE)
    seen = set()
    deduped = []
    for s in raw:
        if s not in seen:
            seen.add(s)
            deduped.append(s)
    return deduped


def load_article_types():
    return load_list(ARTICLE_TYPES_FILE)


def load_pearls():
    return json.loads(PEARLS_FILE.read_text(encoding="utf-8"))


def save_pearls(pearls):
    tmp = str(PEARLS_FILE) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(pearls, f, indent=2, ensure_ascii=False)
    os.replace(tmp, str(PEARLS_FILE))


def load_progress():
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_progress(progress):
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2, ensure_ascii=False), encoding="utf-8")


def log_change(entry):
    entry["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CHANGE_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── Together AI ─────────────────────────────────────────────────────────

def call_together(prompt, system_prompt, model):
    from together import Together
    client = Together(api_key=TOGETHER_API_KEY)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        timeout=API_TIMEOUT,
    )
    raw = response.choices[0].message.content
    if not raw or not raw.strip():
        raise ValueError("Empty response from API")
    return json.loads(raw.strip())


def classify_batch(batch, system_prompt, user_message, primary_model=None):
    models = [primary_model or PRIMARY_MODEL, FALLBACK_MODEL]
    for model in models:
        for attempt in range(MAX_RETRIES):
            try:
                result = call_together(user_message, system_prompt, model)
                return result, model
            except Exception as e:
                print(f"  {model} attempt {attempt + 1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
    raise RuntimeError("All models and retries exhausted")


def _safe_get(response, pid):
    val = response.get(pid) or response.get(str(pid))
    return val if isinstance(val, dict) else None


# ── Mode: correct_system ────────────────────────────────────────────────

def _sys_prompt(specialties, _article_types):
    spec_list = "\n".join(f"  - {s}" for s in specialties)
    return (
        "You are a medical specialty classifier. Your task is to classify clinical pearls "
        "into the correct medical specialty.\n\n"
        "Allowed specialties:\n" + spec_list + "\n\n"
        "For each pearl you are given:\n"
        "- id: unique identifier\n"
        "- source_paper: title of the source paper\n"
        "- pearl: the clinical pearl content\n"
        "- topic: topic tags\n"
        "- current_system: the current classification\n\n"
        "Respond with a JSON object where each key is the pearl id, and the value is:\n"
        '  "system": the correct specialty from the allowed list\n'
        '  "confidence": "high", "medium", or "low"\n\n'
        "Rules:\n"
        "- Use ONLY specialties from the allowed list (exact spelling).\n"
        "- Base your decision primarily on the pearl content and source paper title.\n"
        "- If the current_system is already correct, return it unchanged.\n"
        "- Only suggest a different system if you are confident the current one is wrong.\n"
        "- For topics spanning multiple specialties, pick the single most relevant one.\n"
        '- When system is "Other", try to assign a specific specialty if possible.\n'
        "- Return ONLY valid JSON, no other text."
    )


def _sys_msg(batch):
    lines = []
    for p in batch:
        lines.append(json.dumps({
            "id": p["id"],
            "source_paper": p.get("source_paper", ""),
            "pearl": p.get("pearl", ""),
            "topic": p.get("topic", ""),
            "current_system": p.get("system", ""),
        }))
    return "Classify these pearls:\n" + "\n".join(lines)


def _sys_validate(response, batch):
    results = []
    for p in batch:
        pid = p["id"]
        s = _safe_get(response, pid)
        if not s:
            continue
        system = s.get("system", "").strip()
        conf = s.get("confidence", "low")
        if system:
            results.append((pid, {"system": system}, conf))
    return results


def _sys_apply(pearl, update):
    pearl["system"] = update["system"]


# ── Mode: correct_topic ─────────────────────────────────────────────────

def _top_prompt(_specialties, _article_types):
    return (
        "You are a medical topic classifier. Your task is to assign 1-3 topic keywords "
        "to each clinical pearl based on its content.\n\n"
        "For each pearl you are given:\n"
        "- id: unique identifier\n"
        "- source_paper: title of the source paper\n"
        "- pearl: the clinical pearl content\n"
        "- system: the medical specialty\n"
        "- current_topic: the current topic tags\n\n"
        "Respond with a JSON object where each key is the pearl id, and the value is:\n"
        '  "topic": 1-3 comma-separated topic keywords (e.g. "hypertension, blood pressure management")\n'
        '  "confidence": "high", "medium", or "low"\n\n'
        "Rules:\n"
        "- Topics should be 1-3 comma-separated keywords or short phrases.\n"
        "- Base topics on the pearl content and source paper title.\n"
        "- If current_topic is already accurate, return it unchanged.\n"
        "- Prefer clinically meaningful terms over broad categories.\n"
        "- Return ONLY valid JSON, no other text."
    )


def _top_msg(batch):
    lines = []
    for p in batch:
        lines.append(json.dumps({
            "id": p["id"],
            "source_paper": p.get("source_paper", ""),
            "pearl": p.get("pearl", ""),
            "system": p.get("system", ""),
            "current_topic": p.get("topic", ""),
        }))
    return "Assign topics to these pearls:\n" + "\n".join(lines)


def _top_validate(response, batch):
    results = []
    for p in batch:
        pid = p["id"]
        s = _safe_get(response, pid)
        if not s:
            continue
        topic = s.get("topic", "").strip()
        conf = s.get("confidence", "low")
        if topic:
            results.append((pid, {"topic": topic}, conf))
    return results


def _top_apply(pearl, update):
    pearl["topic"] = update["topic"]


# ── Mode: correct_type ──────────────────────────────────────────────────

def _typ_prompt(_specialties, article_types):
    type_list = "\n".join(f"  - {t}" for t in article_types)
    return (
        "You are a medical article type classifier. Your task is to classify clinical pearls "
        "by the type of article they were extracted from.\n\n"
        "Allowed types:\n" + type_list + "\n\n"
        "For each pearl you are given:\n"
        "- id: unique identifier\n"
        "- source_paper: title of the source paper\n"
        "- pearl: the clinical pearl content\n"
        "- system: the medical specialty\n"
        "- current_type: the current article type\n\n"
        "Respond with a JSON object where each key is the pearl id, and the value is:\n"
        '  "type": the correct article type from the allowed list\n'
        '  "confidence": "high", "medium", or "low"\n\n'
        "Rules:\n"
        "- Use ONLY types from the allowed list (exact spelling).\n"
        "- Base your decision on the source paper title and pearl content.\n"
        '- "Guideline" contains recommendations, protocols, or consensus statements.\n'
        '- "Review" summarizes existing literature without new recommendations.\n'
        '- "Trial" reports results from a clinical trial or study.\n'
        '- "Meta-analysis" pools data from multiple studies.\n'
        "- Return ONLY valid JSON, no other text."
    )


def _typ_msg(batch):
    lines = []
    for p in batch:
        lines.append(json.dumps({
            "id": p["id"],
            "source_paper": p.get("source_paper", ""),
            "pearl": p.get("pearl", ""),
            "system": p.get("system", ""),
            "current_type": p.get("type", ""),
        }))
    return "Classify these article types:\n" + "\n".join(lines)


def _typ_validate(response, batch):
    results = []
    for p in batch:
        pid = p["id"]
        s = _safe_get(response, pid)
        if not s:
            continue
        ptype = s.get("type", "").strip()
        conf = s.get("confidence", "low")
        if ptype:
            results.append((pid, {"type": ptype}, conf))
    return results


def _typ_apply(pearl, update):
    pearl["type"] = update["type"]


# ── Mode: polish_pearl ──────────────────────────────────────────────────

def _pol_prompt(_specialties, _article_types):
    return (
        "You are a medical copy editor. Your task is to polish clinical pearl text for "
        "grammar, clarity, and conciseness without changing any clinical content.\n\n"
        "For each pearl you are given:\n"
        "- id: unique identifier\n"
        "- pearl: the clinical pearl text to polish\n\n"
        "Respond with a JSON object where each key is the pearl id, and the value is:\n"
        '  "pearl": the polished pearl text\n'
        '  "confidence": "high", "medium", or "low"\n\n'
        "Rules:\n"
        "- Improve grammar, flow, and readability.\n"
        "- Do NOT change any clinical fact, number, drug name, or threshold.\n"
        "- Do NOT add or remove medical information.\n"
        "- Keep the same length roughly (don't truncate or expand substantially).\n"
        "- If the text is already well-written, return it unchanged.\n"
        "- Return ONLY valid JSON, no other text."
    )


def _pol_msg(batch):
    lines = []
    for p in batch:
        lines.append(json.dumps({
            "id": p["id"],
            "pearl": p.get("pearl", ""),
        }))
    return "Polish these pearls:\n" + "\n".join(lines)


def _pol_validate(response, batch):
    results = []
    for p in batch:
        pid = p["id"]
        s = _safe_get(response, pid)
        if not s:
            continue
        text = s.get("pearl", "").strip()
        conf = s.get("confidence", "low")
        if text:
            results.append((pid, {"pearl": text}, conf))
    return results


def _pol_apply(pearl, update):
    pearl["pearl"] = update["pearl"]


# ── Mode Registry ───────────────────────────────────────────────────────

MODES = {
    "correct_system": {
        "description": "Reclassify pearl system/specialty field",
        "fields_modified": ["system"],
        "requires_specialties": True,
        "requires_article_types": False,
        "build_prompt": _sys_prompt,
        "build_msg": _sys_msg,
        "validate": _sys_validate,
        "apply": _sys_apply,
    },
    "correct_topic": {
        "description": "Generate/improve pearl topic field",
        "fields_modified": ["topic"],
        "requires_specialties": False,
        "requires_article_types": False,
        "build_prompt": _top_prompt,
        "build_msg": _top_msg,
        "validate": _top_validate,
        "apply": _top_apply,
    },
    "correct_type": {
        "description": "Reclassify pearl article type field",
        "fields_modified": ["type"],
        "requires_specialties": False,
        "requires_article_types": True,
        "build_prompt": _typ_prompt,
        "build_msg": _typ_msg,
        "validate": _typ_validate,
        "apply": _typ_apply,
    },
    "polish_pearl": {
        "description": "Polish pearl text for grammar and clarity",
        "fields_modified": ["pearl"],
        "requires_specialties": False,
        "requires_article_types": False,
        "build_prompt": _pol_prompt,
        "build_msg": _pol_msg,
        "validate": _pol_validate,
        "apply": _pol_apply,
    },
}


# ── Main ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Batch-update pearl fields using Together AI"
    )
    parser.add_argument("--mode", required=True, choices=list(MODES.keys()),
                        help=f"Operation mode: {', '.join(MODES.keys())}")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without modifying pearls.json")
    parser.add_argument("--batch", type=int, default=BATCH_SIZE,
                        help=f"Pearls per API call (default: {BATCH_SIZE})")
    parser.add_argument("--model", default=None,
                        help=f"Override primary model (default: {PRIMARY_MODEL})")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from last saved progress (same flags as original run)")
    parser.add_argument("--only-other", action="store_true",
                        help="Only process pearls with system='Other' (correct_system mode only)")
    parser.add_argument("--max-pearls", type=int, default=None,
                        help="Limit total pearls processed")
    parser.add_argument("--verbose", action="store_true",
                        help="Detailed per-pearl output")
    args = parser.parse_args()

    if not TOGETHER_API_KEY:
        print("ERROR: TOGETHER_API_KEY not found in .env")
        sys.exit(1)

    if args.only_other and args.mode != "correct_system":
        print("ERROR: --only-other is only valid with --mode correct_system")
        sys.exit(1)

    mode = MODES[args.mode]
    primary_model = args.model or PRIMARY_MODEL

    # Load vocabularies
    specialties = load_specialties() if mode["requires_specialties"] else []
    article_types = load_article_types() if mode["requires_article_types"] else []

    # Load and filter pearls
    pearls = load_pearls()
    original_count = len(pearls)

    if args.only_other:
        pearls = [p for p in pearls if p.get("system", "").strip() == "Other"]
        print(f"Filtered to {len(pearls)} pearls with system='Other' "
              f"(from {original_count} total)")

    total = len(pearls)
    if total == 0:
        print("No pearls to process.")
        return

    # Resume: skip pearls whose id was already processed in a previous run
    progress_key = args.mode + ("_only_other" if args.only_other else "")
    progress = load_progress()
    last_processed_id = progress.get(progress_key, -1)

    if args.resume and last_processed_id >= 0:
        before = len(pearls)
        pearls = [p for p in pearls if int(p["id"]) > int(last_processed_id)]
        skipped = before - len(pearls)
        print(f"Resuming: skipped {skipped} already-processed pearls "
              f"(last processed id: {last_processed_id}, remaining: {len(pearls)})")
        if len(pearls) == 0:
            print("All pearls already processed. Nothing to do.")
            return

    # Limit max pearls
    if args.max_pearls and args.max_pearls < len(pearls):
        pearls = pearls[:args.max_pearls]

    total = len(pearls)

    # Print configuration
    if specialties:
        print(f"Specialties ({len(specialties)}): {', '.join(specialties)}")
    if article_types:
        print(f"Article types ({len(article_types)}): {', '.join(article_types)}")
    print(f"Mode: {args.mode} — {mode['description']}")
    print(f"Pearls to process: {total}")
    print(f"Batch size: {args.batch}")
    print(f"Primary model: {primary_model}  |  Fallback: {FALLBACK_MODEL}")
    if args.dry_run:
        print("DRY RUN — no changes will be saved")

    changes = []
    errors = []
    kept = 0
    low_conf = 0
    batches_processed = 0
    idx = 0

    while idx < total:
        batch = pearls[idx: idx + args.batch]
        batch_ids = [p["id"] for p in batch]

        print(f"\nBatch {batches_processed + 1} — "
              f"pearls {idx}–{idx + len(batch) - 1} "
              f"(ids: {batch_ids[0]}..{batch_ids[-1]})")

        system_prompt = mode["build_prompt"](specialties, article_types)
        user_msg = mode["build_msg"](batch)

        try:
            result, model_used = classify_batch(batch, system_prompt, user_msg, primary_model)
            batches_processed += 1
        except Exception as e:
            print(f"  FAILED after all retries: {e}")
            errors.extend(batch_ids)
            idx += args.batch
            continue

        if not isinstance(result, dict):
            print(f"  Unexpected response type: {type(result)}")
            errors.extend(batch_ids)
            idx += args.batch
            continue

        batch_change_ids = set()
        parsed = mode["validate"](result, batch)

        for pid, update, confidence in parsed:
            pearl = next((p for p in batch if p["id"] == pid), None)
            if not pearl:
                continue

            field = mode["fields_modified"][0]
            old_val = pearl.get(field, "")
            new_val = update.get(field, "")

            if args.mode == "polish_pearl":
                if new_val == old_val:
                    kept += 1
                    continue
            else:
                if confidence not in ("high", "medium"):
                    if args.verbose:
                        print(f"  [{pid}] skipped: confidence {confidence}")
                    low_conf += 1
                    continue
                if new_val == old_val:
                    kept += 1
                    continue

            change_entry = {
                "mode": args.mode,
                "id": pid,
                "field": field,
                "old": old_val,
                "new": new_val,
                "confidence": confidence,
            }
            changes.append(change_entry)
            batch_change_ids.add(pid)
            kept += 1

            if not args.dry_run:
                mode["apply"](pearl, update)
                log_change(change_entry)

            if args.verbose:
                o = old_val[:60] + ("..." if len(old_val) > 60 else "")
                n = new_val[:60] + ("..." if len(new_val) > 60 else "")
                print(f"  [{pid}] {field}: {o!r} -> {n!r} ({confidence})")

        if not args.dry_run:
            save_pearls(pearls)
            batch_max_id = max(int(pid) for pid in batch_ids)
            progress[progress_key] = batch_max_id
            save_progress(progress)

        batch_change_count = sum(1 for c in changes if c["id"] in batch_ids)
        print(f"  Model: {model_used}  |  Changes: {batch_change_count}")

        idx += args.batch

    # ── Summary ──
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Mode:                 {args.mode}")
    print(f"  Total processed:      {total}")
    print(f"  Batches completed:    {batches_processed}")
    print(f"  Changes applied:      {len(changes)}")
    print(f"  Already correct:      {kept - len(changes)}")
    print(f"  Low confidence:       {low_conf}")
    print(f"  Batch errors:         {len(errors)}")

    if changes:
        print(f"\n  Change log: {CHANGE_LOG_FILE}")
        if args.verbose:
            for c in changes:
                o = c["old"][:60] + ("..." if len(c["old"]) > 60 else "")
                n = c["new"][:60] + ("..." if len(c["new"]) > 60 else "")
                print(f"    [{c['id']}] {c['field']}: {o!r} -> {n!r} "
                      f"({c['confidence']})")

    if errors:
        print(f"\n  Failed pearl IDs: {errors}")

    if args.dry_run:
        print("\n  Dry run complete — no files modified")
    else:
        print(f"\n  Pearls saved:  {PEARLS_FILE}")
        print(f"  Progress:      {PROGRESS_FILE}")


if __name__ == "__main__":
    main()
