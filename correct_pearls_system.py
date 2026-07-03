#!/usr/bin/env python3
"""
correct_pearls_system.py — Reclassify pearl specialties using Together AI.

Reads pearls.json, sends batches to Together AI (openai/gpt-oss-20b primary,
openai/gpt-oss-120b fallback) to correct the 'system' field based on pearl
content, source paper, and topic tags. Only modifies where AI is confident
the current classification is wrong.
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
PEARLS_FILE = SCRIPT_DIR / "pearls.json"


def load_specialties():
    raw = SPECIALTIES_FILE.read_text(encoding="utf-8").strip().splitlines()
    seen = set()
    deduped = []
    for s in raw:
        s = s.strip()
        if s and s not in seen:
            seen.add(s)
            deduped.append(s)
    return deduped


def load_pearls():
    return json.loads(PEARLS_FILE.read_text(encoding="utf-8"))


def save_pearls(pearls):
    PEARLS_FILE.write_text(
        json.dumps(pearls, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def build_system_prompt(specialties):
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
        "- Return ONLY valid JSON, no other text."
    )


def build_user_message(batch):
    lines = []
    for p in batch:
        lines.append(
            json.dumps({
                "id": p["id"],
                "source_paper": p.get("source_paper", ""),
                "pearl": p.get("pearl", ""),
                "topic": p.get("topic", ""),
                "current_system": p.get("system", ""),
            })
        )
    return "Classify these pearls:\n" + "\n".join(lines)


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


def classify_batch(batch, specialties, primary_model=None):
    system_prompt = build_system_prompt(specialties)
    user_msg = build_user_message(batch)
    models = [primary_model or PRIMARY_MODEL, FALLBACK_MODEL]

    for model in models:
        for attempt in range(MAX_RETRIES):
            try:
                result = call_together(user_msg, system_prompt, model)
                return result, model
            except Exception as e:
                print(f"  {model} attempt {attempt+1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
    raise RuntimeError("All models and retries exhausted")


def main():
    parser = argparse.ArgumentParser(
        description="Reclassify pearl specialties using Together AI"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would change without modifying pearls.json"
    )
    parser.add_argument(
        "--batch-size", type=int, default=BATCH_SIZE,
        help=f"Pearls per API call (default: {BATCH_SIZE})"
    )
    parser.add_argument(
        "--model", default=None,
        help=f"Override primary model (default: {PRIMARY_MODEL})"
    )
    parser.add_argument(
        "--resume", type=str, default=None,
        help="Resume from a last_processed.txt file"
    )
    args = parser.parse_args()

    if not TOGETHER_API_KEY:
        print("ERROR: TOGETHER_API_KEY not found in .env")
        sys.exit(1)

    primary_model = args.model or PRIMARY_MODEL

    specialties = load_specialties()
    pearls = load_pearls()
    total = len(pearls)

    print(f"Specialties ({len(specialties)}): {', '.join(specialties)}")
    print(f"Pearls loaded: {total}")
    print(f"Batch size: {args.batch_size}")
    print(f"Primary model: {primary_model}")
    print(f"Fallback model: {FALLBACK_MODEL}")
    if args.dry_run:
        print("DRY RUN — no changes will be saved")

    resume_from = 0
    if args.resume and Path(args.resume).exists():
        resume_from = int(Path(args.resume).read_text().strip())
        print(f"Resuming from pearl index {resume_from}")

    changes = []
    errors = []
    skipped = 0
    confirmed = 0
    batches_processed = 0

    idx = resume_from
    while idx < total:
        batch = pearls[idx: idx + args.batch_size]
        batch_ids = [p["id"] for p in batch]

        print(f"\nBatch {batches_processed + 1} — pearls {idx}–{idx + len(batch) - 1} (ids: {batch_ids[0]}..{batch_ids[-1]})")

        try:
            result, model_used = classify_batch(batch, specialties, primary_model)
            batches_processed += 1
        except Exception as e:
            print(f"  FAILED after all retries: {e}")
            errors.extend(batch_ids)
            idx += args.batch_size
            continue

        if not isinstance(result, dict):
            print(f"  Unexpected response type: {type(result)}")
            errors.extend(batch_ids)
            idx += args.batch_size
            continue

        for pearl in batch:
            pid = pearl["id"]
            suggestion = result.get(pid) or result.get(str(pid))
            if not suggestion:
                skipped += 1
                continue

            suggested_system = suggestion.get("system", "").strip()
            confidence = suggestion.get("confidence", "low")
            current_system = pearl.get("system", "")

            if confidence in ("high", "medium") and suggested_system and suggested_system != current_system:
                changes.append({
                    "id": pid,
                    "index": idx + batch.index(pearl),
                    "source_paper": pearl.get("source_paper", "")[:60],
                    "old": current_system,
                    "new": suggested_system,
                    "confidence": confidence,
                })
                if not args.dry_run:
                    pearl["system"] = suggested_system
                confirmed += 1
            else:
                confirmed += 1

        if not args.dry_run:
            save_pearls(pearls)

        with open("last_processed.txt", "w") as f:
            f.write(str(idx + args.batch_size))

        print(f"  Model: {model_used} | Changed: {sum(1 for c in changes if c['index'] >= idx)}")

        idx += args.batch_size

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total pearls:           {total}")
    print(f"Batches processed:      {batches_processed}")
    print(f"Changes made:           {len(changes)}")
    print(f"Confirmed/no-change:    {confirmed}")
    print(f"Errors (batch failed):  {len(errors)}")

    if changes:
        print(f"\nChanges:")
        for c in changes:
            print(f"  [{c['id']}] idx={c['index']}  {c['old']} -> {c['new']}  ({c['confidence']})  | {c['source_paper']}")

    if errors:
        print(f"\nFailed pearl IDs: {errors}")

    if args.dry_run:
        print("\nDry run complete — no files modified")
    else:
        print(f"\nSaved to {PEARLS_FILE}")


if __name__ == "__main__":
    main()
