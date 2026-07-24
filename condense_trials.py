#!/usr/bin/env python3
"""
condense_trials.py - Condense raw scraped trial JSON into the hack.CCM schema.

Usage:
  python condense_trials.py                            # batch all (tencent default)
  python condense_trials.py --model deepseek            # use DeepSeek V4 Pro via Together
  python condense_trials.py --single Neuro/KRESS.json   # one trial
  python condense_trials.py --max 20                    # cap at 20 trials
  python condense_trials.py --model tencent --single Neuro/KRESS.json
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime

from acumen_core.config import (
    TRIALS_DATABASE_DIR,
    CONDENSED_TRIALS_DIR,
    CONDENSATION_PROGRESS_FILE,
    CONDENSATION_PROMPT_FILE,
    SYSTEM_TO_SPECIALTY,
    TEMPERATURE_CONDENSATION,
    MAX_TOKENS_CONDENSATION,
    CONDENSATION_MODELS,
    TOGETHER_API_KEY,
    OPENROUTER_API_KEY,
    MAX_RETRIES,
    RETRY_DELAY,
)
from acumen_core.subtopics_config import get_subtopics_for_system

# ---------------------------------------------------------------------------
# LLM clients (lazy imports to keep startup fast)
# ---------------------------------------------------------------------------

def _get_openrouter_client():
    if not OPENROUTER_API_KEY:
        return None
    from openai import OpenAI
    from acumen_core.config import OPENROUTER_BASE_URL
    return OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)


def _get_together_client():
    if not TOGETHER_API_KEY:
        return None
    from together import Together
    return Together(api_key=TOGETHER_API_KEY, timeout=300)


def _get_deepseek_client():
    from acumen_core.config import DEEPSEEK_API_KEY
    if not DEEPSEEK_API_KEY:
        return None
    from openai import OpenAI
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")


# ---------------------------------------------------------------------------
# API call helpers
# ---------------------------------------------------------------------------

def call_openrouter(system_prompt, user_content, temperature=0.1, max_tokens=16384):
    from acumen_core.config import OPENROUTER_MODEL
    client = _get_openrouter_client()
    if not client:
        raise RuntimeError("OpenRouter client not available (check OPENROUTER_API_KEY)")
    model = OPENROUTER_MODEL
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            raw = response.choices[0].message.content
            if not raw or not raw.strip():
                raise ValueError("Empty response")
            raw = raw.strip()
            raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
            raw = re.sub(r'\n?\s*```$', '', raw)
            return json.loads(raw)
        except json.JSONDecodeError as e:
            last_error = e
            print(f"    [X] JSON parse error: {e}")
            break
        except Exception as e:
            last_error = e
            msg = str(e).lower()
            if attempt < MAX_RETRIES - 1 and any(
                kw in msg for kw in ("timeout", "rate limit", "429", "503", "502", "500", "empty")
            ):
                wait = RETRY_DELAY * (attempt + 1)
                print(f"    [!] {e} — retrying in {wait}s")
                time.sleep(wait)
            else:
                print(f"    [X] OpenRouter failed: {e}")
                break
    raise last_error or RuntimeError("OpenRouter exhausted")


def call_deepseek_together(system_prompt, user_content, temperature=0.1, max_tokens=16384):
    from acumen_core.config import MODEL_TOGETHER_PRO as model
    client = _get_together_client()
    deepseek_client = _get_deepseek_client()
    last_error = None

    providers = []
    if client:
        providers.append(("Together AI", model, client, False))
    if deepseek_client:
        from acumen_core.config import MODEL_DEEPSEEK_DIRECT as ds_model
        providers.append(("DeepSeek Direct", ds_model, deepseek_client, True))

    for provider_name, model_name, llm_client, is_deepseek in providers:
        for attempt in range(MAX_RETRIES):
            try:
                print(f"    {provider_name}: {model_name} (attempt {attempt + 1}/{MAX_RETRIES})")
                kwargs = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if not is_deepseek:
                    kwargs["response_format"] = {"type": "json_object"}
                    kwargs["reasoning"] = {"enabled": False}
                response = llm_client.chat.completions.create(**kwargs)
                raw = response.choices[0].message.content
                if not raw or not raw.strip():
                    raise ValueError("Empty response")
                raw = raw.strip()
                raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
                raw = re.sub(r'\n?\s*```$', '', raw)
                return json.loads(raw)
            except json.JSONDecodeError as e:
                last_error = e
                print(f"    [X] JSON parse error: {e}")
                break
            except Exception as e:
                last_error = e
                msg = str(e).lower()
                if attempt < MAX_RETRIES - 1 and any(
                    kw in msg for kw in ("timeout", "rate limit", "429", "503", "502", "500", "empty")
                ):
                    wait = RETRY_DELAY * (attempt + 1)
                    print(f"    [!] {e} — retrying in {wait}s")
                    time.sleep(wait)
                else:
                    print(f"    [X] {provider_name} failed: {e}")
                    break

    raise last_error or RuntimeError("All DeepSeek providers exhausted")


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

def load_prompt():
    if not os.path.exists(CONDENSATION_PROMPT_FILE):
        raise FileNotFoundError(
            f"Prompt file not found: {CONDENSATION_PROMPT_FILE}\n"
            "Copy hackCCM_trial_condensation_prompt.md to the project root."
        )
    with open(CONDENSATION_PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def build_messages(raw_json, specialty):
    prompt = load_prompt()
    marker = "SOURCE TRIAL JSON TO CONVERT:"
    idx = prompt.find(marker)
    if idx == -1:
        system_prompt = prompt
        prefix = ""
    else:
        system_prompt = prompt[:idx].strip()
        prefix = prompt[idx:].strip()

    subtopics = get_subtopics_for_system(specialty)
    subtopic_block = ""
    if subtopics:
        lines = [f"{i+1}. {s}" for i, s in enumerate(subtopics)]
        subtopic_block = "Valid subtopics for this trial:\n" + "\n".join(lines) + "\n\n"

    user_content = subtopic_block + prefix + "\n\n" + json.dumps(raw_json, indent=2)
    return system_prompt, user_content


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def process_trial(source_path, source_rel, model_flag):
    with open(source_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if "sections" not in raw or not raw["sections"]:
        print(f"  SKIP (no detail page/sections)")
        return {"status": "skipped", "reason": "no sections"}

    system_name = raw.get("system", "")
    specialty = SYSTEM_TO_SPECIALTY.get(system_name, "Other")
    system_prompt, user_content = build_messages(raw, specialty)

    print(f"  Condensing ({model_flag})...", end=" ", flush=True)
    try:
        if model_flag == "tencent":
            result = call_openrouter(system_prompt, user_content)
        else:
            result = call_deepseek_together(system_prompt, user_content)

        # Ensure required top-level keys
        result["_source_id"] = raw.get("id")
        result["_source_system"] = system_name

        out_path = os.path.join(CONDENSED_TRIALS_DIR, source_rel)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print("OK")
        return {"status": "done"}

    except Exception as e:
        print(f"FAILED: {e}")
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Condense raw trial JSON into hack.CCM schema")
    parser.add_argument("--model", choices=list(CONDENSATION_MODELS.keys()), default="tencent",
                        help="LLM model to use (default: tencent)")
    parser.add_argument("--single", type=str, default=None,
                        help="Process a single trial, e.g. Neuro/KRESS.json")
    parser.add_argument("--max", type=int, default=0,
                        help="Max trials to process (0 = unlimited)")
    args = parser.parse_args()

    if not os.path.exists(TRIALS_DATABASE_DIR):
        print(f"Error: trials_database not found at {TRIALS_DATABASE_DIR}")
        sys.exit(1)

    # Collect files
    if args.single:
        single_path = os.path.join(TRIALS_DATABASE_DIR, args.single)
        if not os.path.exists(single_path):
            print(f"Error: {single_path} not found")
            sys.exit(1)
        files = [(single_path, args.single)]
    else:
        files = []
        for root, dirs, fnames in os.walk(TRIALS_DATABASE_DIR):
            for fname in sorted(fnames):
                if fname.endswith(".json"):
                    full = os.path.join(root, fname)
                    rel = os.path.relpath(full, TRIALS_DATABASE_DIR)
                    files.append((full, rel))
        print(f"Found {len(files)} trial files")

    # Load progress for resume
    progress = {}
    if os.path.exists(CONDENSATION_PROGRESS_FILE):
        with open(CONDENSATION_PROGRESS_FILE, "r", encoding="utf-8") as f:
            progress = json.load(f)

    done_count = 0
    error_count = 0
    skip_count = 0
    start_time = time.time()

    for i, (full_path, rel_path) in enumerate(files):
        # Skip if already completed
        if args.single is None and progress.get(rel_path, {}).get("status") == "done":
            continue

        # Cap
        if args.max > 0 and done_count >= args.max:
            print(f"Reached --max {args.max}, stopping")
            break

        system_name = rel_path.split(os.sep)[0]
        print(f"\n[{i+1}/{len(files)}] {rel_path}")

        result = process_trial(full_path, rel_path, args.model)

        progress[rel_path] = result
        with open(CONDENSATION_PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress, f, indent=2)

        if result["status"] == "done":
            done_count += 1
        elif result["status"] == "skipped":
            skip_count += 1
        else:
            error_count += 1

        if args.single is None:
            time.sleep(0.5)

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"  Done: {done_count} | Skipped: {skip_count} | Errors: {error_count}")
    print(f"  Time: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"  Output: {CONDENSED_TRIALS_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
