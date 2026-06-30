#!/usr/bin/env python3
"""
migrate_jsons.py - Migrate hack.CCM old-format JSON clinical summaries
to the new structured schema using Google Gemini (with fallback chain).

Usage:
    python migrate_jsons.py
    python migrate_jsons.py --max 5
    python migrate_jsons.py --force
    python migrate_jsons.py --model gemini-2.5-flash --fallback-models gemini-2.5-pro,gemini-2.0-flash
"""

import os
import sys
import json
import time
import re
import argparse
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.api_core import exceptions as google_exceptions

# ── Setup ─────────────────────────────────────────────────────────────
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path=env_path)

PRIMARY_API_KEY = os.getenv("PRIMARY_GEMINI_API_KEY")
BACKUP_API_KEY = os.getenv("BACKUP_GEMINI_API_KEY")

if not PRIMARY_API_KEY and not BACKUP_API_KEY:
    print("[X] No Gemini API keys found. Set PRIMARY_GEMINI_API_KEY in .env")
    sys.exit(1)

PRIMARY_CLIENT = genai.Client(api_key=PRIMARY_API_KEY) if PRIMARY_API_KEY else None
BACKUP_CLIENT = genai.Client(api_key=BACKUP_API_KEY) if BACKUP_API_KEY else None

# ── Directories ────────────────────────────────────────────────────────
INPUT_DIR = "output_files"
OUTPUT_DIR = "modified_output_files"
PROGRESS_FILE = "migration_progress.json"
ERROR_LOG = "migration_errors.jsonl"

# ── Model defaults ────────────────────────────────────────────────────
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_FALLBACKS = ["gemini-3.5-flash", "gemini-2.5-flash"]
MAX_RETRIES = 3
MIN_DELAY = 1.5
BACKOFF_CAP = 60
TEMPERATURE = 0.1
MAX_MARKDOWN_CHARS = 80000

# ── Consolidated System Prompt ────────────────────────────────────────
SYSTEM_PROMPT = """You are a structural migration engine for hack.CCM's clinical content database. You will be given an OLD-FORMAT JSON object containing a single free-text markdown field called "clinical_summary_markdown". Your job is to RESTRUCTURE this existing content into the new fixed schema below. Do NOT invent new clinical facts, do NOT omit facts that exist in the source markdown, and do NOT re-interpret the clinical content - only reorganize it.

CRITICAL RULES:
1. Output ONLY valid JSON. No preamble, no markdown fences, no commentary.
2. First determine doc_type: if the old "type_of_article" field is "Guideline", use the GUIDELINE schema. Otherwise (Review, RCT, Meta-analysis, Secondary Analysis, Observational study, etc.) use the ARTICLE schema. Map "type_of_article" to the correct controlled "article_subtype" or treat as a guideline accordingly.
3. Collapse ALL nested heading levels (H3/H4/H5/H6) found in the old markdown into the new schema's two-level-maximum structure: top-level sections/blocks, with any deeper sub-headers folded into that section's "content"/"narrative" field as prose or inline bullets. Do not create more top-level sections than the old document's own H2-level headers warrant - usually 4-10.
4. Extract "key_pearls" by scanning the OLD document's "Clinical Takeaways" / "Direct ICU/Clinical Application" section (or equivalent) and converting its bullet points into 4-7 atomic, standalone pearls. If that section contains more than 7 bullets, select the 4-7 most clinically decisive/specific ones (prioritize those with numbers, thresholds, or drug names over general statements).
5. For GUIDELINES specifically: scan the old markdown for any recommendation identifiers already embedded in headers or text (e.g. "(R1.1.1)", "(Q3)") and use these to reconstruct "recommendation_blocks" - each old H3/H4 subsection under the "SEQUENTIAL SUBSECTION ANALYSIS" (or equivalent) becomes one recommendation_block, with its constituent statements broken into individual "recommendations" entries. If no clean recommendation-level granularity exists in the source prose, create ONE recommendation entry per block using the block's core directive as the "statement", with strength/evidence_grade set to null.
6. For GUIDELINES: if the old markdown has a "Bedside Protocol Blueprint" or similar step-by-step section, map it directly into "bedside_protocol".
7. "specialty" must map the old "system" field (e.g. "Nephrology / Neurology") into the controlled list: ["pulmonology","nephrology","hepatology","neurology","cardiology","infectious_disease","hematology","endocrinology","gastroenterology","toxicology","trauma","surgery","multi_system","pharmacology","rehabilitation"]. Split combined fields into multiple array entries.
8. "one_line_summary" should be extracted/condensed from the old "Core Summary" section - do not copy it verbatim if it's longer than ~35 words; tighten it.
9. "strengths_limitations" maps directly from the old document's strengths/limitations bullet content, condensed to 1-3 sentences.
10. Preserve "doi", "journal"/"issuing_bodies" (split authors-as-society for guidelines if applicable), "primary_authors" -> "authors", and generate "id" as a slug from title + year if not already present.
11. Set "added_date" to today's date.
12. If genuinely unable to populate a field from the old content, use null or [] - never fabricate.

For ARTICLES (when type_of_article is Review, RCT, Meta-analysis, Secondary Analysis, Observational, Case Series, Narrative Review, Trial, etc.):
- Use the ARTICLE schema below.
- "sections" must contain ONLY top-level conceptual sections of the paper (typically 4-8 sections). Do NOT create nested sub-headers. Use inline "- " bullet text inside the "content" string for sub-points.
- "key_pearls" must be standalone, atomic, actionable facts (4-7 total). Each pearl should include numbers, thresholds, drug names where supported.
- "one_line_summary" must be a single sentence (max ~35 words).
- "evidence_level" must be exactly one of: "review", "rct", "meta_analysis", "secondary_analysis", "observational", "case_series", "narrative_review".
- "specialty" must be an array of 1-3 controlled strings from the list above.
- "sample_size" and "population" should be null if not clearly extractable - do not guess.
- "id" should be a URL-safe slug derived from the title + year.

ARTICLE SCHEMA:
{
  "id": "string",
  "doc_type": "article",
  "article_subtype": "review | rct | meta_analysis | secondary_analysis | observational | case_series | narrative_review",
  "title": "string - exact paper title",
  "authors": "string - first author + et al., or full list if short",
  "journal": "string",
  "year": number,
  "doi": "string",
  "specialty": ["array of controlled specialty strings, 1-3 items"],
  "tags": ["array of 3-8 free-text clinical keywords, lowercase"],
  "one_line_summary": "string, max ~35 words",
  "key_pearls": ["array of 4-7 atomic, standalone clinical pearls"],
  "evidence_level": "string, one of the controlled enum values",
  "sample_size": "number or null",
  "population": "string or null",
  "sections": [
    {
      "order": number,
      "heading": "string, plain title, no emoji, no markdown",
      "content": "string, 100-1000 words, plain prose, may include inline '- ' bullets for lists",
      "section_pearls": ["0-3 short pearls specific to this section, or empty array"]
    }
  ],
  "strengths_limitations": "string, details bulletted points for both strengths and limitations",
  "related_ids": [],
  "added_date": "YYYY-MM-DD"
}

For GUIDELINES (when type_of_article is "Guideline"):
- Use the GUIDELINE schema below.
- "recommendation_blocks" groups recommendations by clinical topic/domain (typically 4-10 blocks, e.g. "Diagnosis", "Initial Resuscitation"). Each block has a "narrative" field and an array of individual "recommendations".
- Each recommendation object has: "rec_id" (preserve if exists, else null), "statement" (clear directive), "strength" ("strong"|"conditional"|"weak"|"expert_opinion"|null), "evidence_grade" (string or null).
- "bedside_protocol" should only be populated if the source includes an explicit step-by-step workflow; otherwise return [].
- "consensus_method" captures methodology if stated (e.g. "GRADE", "modified Delphi") or null.
- "id" should be a URL-safe slug derived from issuing body + topic + year.

GUIDELINE SCHEMA:
{
  "id": "string",
  "doc_type": "guideline",
  "title": "string - exact guideline title",
  "issuing_bodies": ["array of society/organization acronyms, e.g. AHA, ACC, ESICM"],
  "year": number,
  "doi": "string",
  "specialty": ["array of controlled specialty strings, 1-3 items"],
  "tags": ["array of 3-8 free-text clinical keywords, lowercase"],
  "one_line_summary": "string, max ~35 words",
  "key_pearls": ["array of 4-7 atomic, standalone clinical pearls"],
  "consensus_method": "string or null",
  "search_period": "string or null",
  "recommendation_blocks": [
    {
      "order": number,
      "topic": "string, plain title, no emoji, no markdown",
      "narrative": "string, "100-500 words, no upper limit if the source contains specific trial data, statistics, or numeric thresholds — preserve all numbers, p-values, ORs, and trial names verbatim for this topic",
      "recommendations": [
        {
          "rec_id": "string or null",
          "statement": "string, the recommendation rewritten as a clear directive",
          "strength": "strong | conditional | weak | expert_opinion | null",
          "evidence_grade": "string preserving source's own grade label, or null"
        }
      ]
    }
  ],
  "bedside_protocol": [
    {
      "step": number,
      "title": "string",
      "action": "string, 1-3 sentences"
    }
  ],
  "strengths_limitations": "string, detailed bulletted points for both strengths and limitations",
  "related_ids": [],
  "added_date": "YYYY-MM-DD"
}"""


# ── Rate-limit governor ──────────────────────────────────────────────
_last_call_time = 0.0

def enforce_rate_limit():
    global _last_call_time
    elapsed = time.time() - _last_call_time
    if elapsed < MIN_DELAY:
        time.sleep(MIN_DELAY - elapsed)
    _last_call_time = time.time()


# ── Progress tracker ─────────────────────────────────────────────────
class ProgressTracker:
    def __init__(self, path):
        self.path = path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def is_completed(self, rel_path):
        entry = self.data.get(rel_path)
        return entry and entry.get("status") == "ok"

    def mark_ok(self, rel_path):
        self.data[rel_path] = {"status": "ok", "timestamp": datetime.now().isoformat()}
        self._save()

    def mark_error(self, rel_path, error_msg):
        self.data[rel_path] = {"status": "error", "error": error_msg, "timestamp": datetime.now().isoformat()}
        self._save()

    def remove(self, rel_path):
        self.data.pop(rel_path, None)
        self._save()


# ── Error logger ─────────────────────────────────────────────────────
def log_error(rel_path, file_name, error_msg, details=None):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "rel_path": rel_path,
        "file_name": file_name,
        "error": error_msg,
    }
    if details:
        entry["details"] = str(details)[:2000]
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ── File discovery ───────────────────────────────────────────────────
def discover_json_files(input_dir):
    files = []
    for root, _dirs, fnames in os.walk(input_dir):
        for fname in fnames:
            if not fname.endswith(".json"):
                continue
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, input_dir)
            files.append((full, rel))
    files.sort(key=lambda x: x[1])
    return files


# ── Gemini API call (single attempt) ─────────────────────────────────
def call_gemini(client, model_name, prompt_content, use_json_mode=True):
    if use_json_mode:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=TEMPERATURE,
            response_mime_type="application/json",
        )
    else:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=TEMPERATURE,
        )

    enforce_rate_limit()

    response = client.models.generate_content(
        model=model_name,
        contents=prompt_content,
        config=config,
    )

    raw = response.text.strip()

    if not use_json_mode:
        raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
        raw = re.sub(r'\n?\s*```$', '', raw)

    return json.loads(raw)


def is_retryable_error(e):
    """Check if the error is retryable (rate limit, server error, timeout)."""
    if isinstance(e, google_exceptions.ResourceExhausted):
        return True, "rate_limit"
    if isinstance(e, google_exceptions.ServiceUnavailable):
        return True, "server_error"
    if isinstance(e, google_exceptions.DeadlineExceeded):
        return True, "timeout"
    if isinstance(e, google_exceptions.InternalServerError):
        return True, "server_error"
    if isinstance(e, google_exceptions.GoogleAPIError):
        code = e.code if hasattr(e, 'code') else 0
        if code in (429, 502, 503, 504):
            return True, f"http_{code}"
        if 500 <= code < 600:
            return True, f"http_{code}"
    # Non-retryable
    return False, "fatal"


def get_model_client(model_name):
    """Return (client, resolved_model_name) for a given model name."""
    if PRIMARY_CLIENT:
        return PRIMARY_CLIENT, model_name
    if BACKUP_CLIENT:
        return BACKUP_CLIENT, model_name
    return None, None


# ── Process file with fallback chain ──────────────────────────────────
def process_with_fallback(prompt_content, models_chain):
    """Try each model in chain; per model retry MAX_RETRIES times with backoff."""
    last_error = None

    for model_name in models_chain:
        client, resolved = get_model_client(model_name)
        if not client:
            continue

        print(f"    Model: {model_name}")

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = call_gemini(client, resolved, prompt_content, use_json_mode=True)
                return result

            except google_exceptions.GoogleAPIError as e:
                retryable, reason = is_retryable_error(e)
                last_error = e

                if retryable and attempt < MAX_RETRIES:
                    wait = min(2 ** attempt * 2, BACKOFF_CAP)
                    print(f"    [WAIT] {reason} - retry {attempt}/{MAX_RETRIES} in {wait}s")
                    time.sleep(wait)
                elif retryable:
                    print(f"    [!] {reason} - all retries exhausted for {model_name}")
                    break
                else:
                    print(f"    [X] {reason}: {e}")
                    break

            except json.JSONDecodeError as e:
                last_error = e
                print(f"    [X] JSON parse error: {e}")
                # Try once more without JSON mode
                if attempt < MAX_RETRIES:
                    try:
                        result = call_gemini(client, resolved, prompt_content, use_json_mode=False)
                        return result
                    except Exception:
                        pass
                break

            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    wait = min(2 ** attempt * 2, BACKOFF_CAP)
                    print(f"    [!] Error: {e} - retry {attempt}/{MAX_RETRIES} in {wait}s")
                    time.sleep(wait)
                else:
                    print(f"    [X] Failed after {MAX_RETRIES} retries: {e}")
                    break

    raise last_error or RuntimeError("All models exhausted")


# ── Validate response ────────────────────────────────────────────────
def validate_response(data, is_guideline):
    required_top = ["doc_type", "id", "specialty", "tags", "one_line_summary", "key_pearls", "strengths_limitations", "related_ids", "added_date"]

    if is_guideline:
        required_top += ["title", "issuing_bodies", "year", "doi", "consensus_method", "recommendation_blocks", "bedside_protocol"]
    else:
        required_top += ["title", "authors", "journal", "year", "doi", "article_subtype", "evidence_level", "sections"]

    missing = [f for f in required_top if f not in data]
    if missing:
        raise ValueError(f"Missing fields: {', '.join(missing)}")

    # Validate doc_type
    expected_doc_type = "guideline" if is_guideline else "article"
    if data.get("doc_type") != expected_doc_type:
        raise ValueError(f"Expected doc_type '{expected_doc_type}', got '{data.get('doc_type')}'")

    return True


# ── Process single file ──────────────────────────────────────────────
def process_file(filepath, rel_path, progress, models_chain, force=False):
    fname = os.path.basename(filepath)

    if not force and progress.is_completed(rel_path):
        return "skipped"

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            old_data = json.load(f)
    except Exception as e:
        print(f"  [X] Read error: {e}")
        progress.mark_error(rel_path, str(e))
        log_error(rel_path, fname, "read_error", e)
        return "error"

    # Determine if guideline
    article_type = old_data.get("type_of_article", "")
    is_guideline = article_type.lower() == "guideline"

    # Check content exists
    markdown = old_data.get("clinical_summary_markdown", "")
    if not markdown or len(str(markdown).strip()) < 50:
        print(f"  [SKIP]  Empty/too short content, skipping")
        progress.mark_error(rel_path, "empty_content")
        return "skipped"

    # Safety truncation
    if len(str(markdown)) > MAX_MARKDOWN_CHARS:
        print(f"  [!]  Markdown truncated ({len(markdown)} chars -> {MAX_MARKDOWN_CHARS})")
        old_data["clinical_summary_markdown"] = str(markdown)[:MAX_MARKDOWN_CHARS] + "\n\n[TRUNCATED]"

    prompt_content = f"Now migrate the following old-format document:\n\n{json.dumps(old_data, indent=2)}"

    try:
        result = process_with_fallback(prompt_content, models_chain)
    except Exception as e:
        print(f"  [X] All models failed: {e}")
        progress.mark_error(rel_path, str(e))
        log_error(rel_path, fname, "all_models_failed", e)
        return "error"

    # Validate
    try:
        validate_response(result, is_guideline)
    except ValueError as e:
        print(f"  [X] Validation failed: {e}")
        progress.mark_error(rel_path, str(e))
        log_error(rel_path, fname, "validation_error", {"error": str(e), "response": json.dumps(result)[:1000]})
        return "error"

    # Ensure added_date is today
    result["added_date"] = date.today().strftime("%Y-%m-%d")

    # Write output
    out_path = os.path.join(OUTPUT_DIR, rel_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    progress.mark_ok(rel_path)
    return "ok"


# ── Main ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Migrate old-format JSONs to new hack.CCM schema")
    parser.add_argument("--max", type=int, default=0, help="Max files to process (0 = all)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Primary model (default: {DEFAULT_MODEL})")
    parser.add_argument("--fallback-models", default=",".join(DEFAULT_FALLBACKS), help=f"Comma-separated fallback models (default: {','.join(DEFAULT_FALLBACKS)})")
    parser.add_argument("--force", action="store_true", help="Reprocess already-migrated files")
    parser.add_argument("--min-delay", type=float, default=1.5, help="Min seconds between API calls (default: 1.5)")
    parser.add_argument("--retries", type=int, default=3, help="Retries per model (default: 3)")

    args = parser.parse_args()

    global MIN_DELAY, MAX_RETRIES
    MIN_DELAY = args.min_delay
    MAX_RETRIES = args.retries

    fallback_list = [args.model] + [m.strip() for m in args.fallback_models.split(",") if m.strip()]
    models_chain = list(dict.fromkeys(fallback_list))  # deduplicate preserving order

    print("=" * 60)
    print("  hack.CCM - JSON Migration Engine")
    print("=" * 60)
    print(f"  Primary model:  {args.model}")
    print(f"  Fallback chain: {', '.join(models_chain[1:])}")
    print(f"  Input:     {INPUT_DIR}/")
    print(f"  Output:    {OUTPUT_DIR}/")
    print(f"  Progress:  {PROGRESS_FILE}")
    print(f"  Errors:    {ERROR_LOG}")
    print(f"  Min delay: {MIN_DELAY}s | Retries: {MAX_RETRIES} | Force: {args.force}")
    print()

    # Discover files
    all_files = discover_json_files(INPUT_DIR)
    valid_files = [(fp, rp) for fp, rp in all_files if not rp.startswith("..")]

    if not valid_files:
        print("[X] No JSON files found in", INPUT_DIR)
        return

    print(f"  Found {len(valid_files)} JSON files")

    # Load progress
    progress = ProgressTracker(PROGRESS_FILE)

    # Filter
    to_process = []
    skipped_count = 0
    for fp, rp in valid_files:
        if not args.force and progress.is_completed(rp):
            skipped_count += 1
        else:
            to_process.append((fp, rp))

    if args.max > 0:
        to_process = to_process[:args.max]

    print(f"  Already done: {skipped_count} | To process: {len(to_process)}")
    print()

    if not to_process:
        print("[OK] Nothing to process.")
        return

    # Process
    ok_count = 0
    error_count = 0
    skip_count = 0
    start_time = time.time()

    for idx, (fp, rp) in enumerate(to_process, start=1):
        fname = os.path.basename(fp)
        print(f"[{idx}/{len(to_process)}] {rp}")

        status = process_file(fp, rp, progress, models_chain, force=args.force)

        if status == "ok":
            ok_count += 1
            print(f"  [OK] Done")
        elif status == "skipped":
            skip_count += 1
        else:
            error_count += 1

        # Brief pause between files even on error (rate limiting)
        time.sleep(0.5)

    elapsed = time.time() - start_time
    print()
    print("=" * 60)
    print(f"  Summary")
    print("=" * 60)
    print(f"  Total files:   {len(to_process)}")
    print(f"  [OK] Success:     {ok_count}")
    print(f"  [X] Errors:      {error_count}")
    print(f"  [SKIP]  Skipped:     {skip_count}")
    print(f"  Time:        {elapsed:.1f}s ({elapsed/60:.1f}min)")
    print(f"  [DIR] Output:      {OUTPUT_DIR}/")
    print()

    if error_count > 0:
        print(f"  [!]  {error_count} file(s) failed. Check {ERROR_LOG} for details.")
        print(f"     Fix issues and re-run: python migrate_jsons.py --force")


if __name__ == "__main__":
    main()
