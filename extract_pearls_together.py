#!/usr/bin/env python3
"""
extract_pearls_together.py — hack.CCM clinical pearl extraction engine
Extracts high-yield, evidence-based pearls from structured JSON summaries
using Ollama (local) with Together AI or local rule-based as fallback.

Usage:
    python extract_pearls_together.py
    python extract_pearls_together.py --max 5
    python extract_pearls_together.py --backend together
    python extract_pearls_together.py --backend local
    python extract_pearls_together.py --model gemma4:27b
"""

import os
import sys
import json
import csv
import re
import time
import argparse
import subprocess
from datetime import datetime

from dotenv import load_dotenv

script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path=env_path)



# =====================================================================
# ⚙️ CONFIG
# =====================================================================
OUTPUT_DIR = "./output_files"
PEARLS_CSV = "./pearls.csv"
PEARLS_TRACKER = "./pearls_processed.json"

TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

DEFAULT_OLLAMA_MODEL = "gemma4:latest"
DEFAULT_TOGETHER_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
TOGETHER_FALLBACK_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"

MAX_TOKENS = 4096
TEMPERATURE = 0.2
MAX_PAPERS = 0

# Specialties.txt mapping (standalone copy)
SPECIALTIES_ALIASES = {
    "infectious_disease": "Infectious Diseases",
    "infectious diseases": "Infectious Diseases",
    "multi_system": "Multisystem",
    "multisystem": "Multisystem",
    "obstetrics_and_gynecology": "Obstetrics and Gynecology",
    "obstetrics and gynecology": "Obstetrics and Gynecology",
    "cardio": "Cardiology",
    "neuro": "Neurology",
    "nephro": "Nephrology",
    "pulmo": "Pulmonology",
    "gi": "Gastroenterology",
    "heme": "Hematology",
    "onc": "Oncology",
}

PEARLS_CSV_HEADERS = [
    "id", "timestamp", "source_paper", "doi",
    "author", "system", "type", "pearl", "remarks", "file_name", "topic"
]

# =====================================================================
# 🧠 PEARL EXTRACTION PROMPT
# =====================================================================
PEARL_PROMPT = """You are an expert critical care clinician extracting high-yield clinical pearls from a structured medical summary (article or guideline). You will receive the full extracted content below.

Extract ALL high-yield, evidence-based pearls from the provided text. Prioritize:
- **Clinical updates** — recent practice changes, new guideline recommendations
- **Practice-changing concepts** — shifts in standard of care, updated thresholds
- **Bedside actionable items** — doses, cutoffs, protocols, diagnostic criteria, management algorithms you can apply immediately

Each pearl must be:
- Specific and concrete (thresholds, cutoffs, dosing ranges, timing, risk modifiers, diagnostic criteria, prognostic markers)
- Traceable to evidence when present in the text (RCTs, meta-analyses, guideline recommendations)
- Self-contained (1-2 sentences, maximally information-dense)
- NOT generic advice or truisms (avoid "always assess level of evidence" or "more research is needed")

Deduplicate: if the same finding appears in multiple sections, include it only once.

Return ONLY valid JSON. No preamble, no markdown fences, no commentary.
Format: {"pearls": [{"text": "...", "topic": "..."}]}

If no qualifying pearls can be extracted, return: {"pearls": []}

Each pearl's "topic" should be 1-3 comma-separated keywords (e.g., "hemodynamics, vasopressors", "ventilation, ARDS", "antibiotics, sepsis")."""


# =====================================================================
# 📎 SPECIALTY NORMALIZATION
# =====================================================================
def load_specialties_map():
    m = {}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "specialties.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or "." not in line:
                    continue
                name = line.split(".", 1)[1].strip()
                m[name.lower()] = name
    m.update({k.lower(): v for k, v in SPECIALTIES_ALIASES.items()})
    return m


def normalize_specialty(specialty_list, spec_map):
    if not isinstance(specialty_list, list) or not specialty_list:
        return "Other"
    raw = str(specialty_list[0]).strip().lower().replace("_", " ").replace("-", " ")
    mapped = spec_map.get(raw, "Other")
    return "".join(x for x in str(mapped) if x.isalnum() or x in "._- ").strip()


# =====================================================================
# 📊 BACKEND DETECTION
# =====================================================================
def detect_backend():
    """Auto-detect best available backend: ollama > together > local."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            models = [line.split()[0] for line in result.stdout.strip().split("\n")[1:] if line.strip()]
            if models:
                print(f"  Detected Ollama models: {', '.join(models)}")
                return "ollama", models
    except (FileNotFoundError, subprocess.TimeoutExpired, IndexError):
        pass

    if TOGETHER_API_KEY:
        print("  Ollama not available. Using Together AI.")
        return "together", [DEFAULT_TOGETHER_MODEL, TOGETHER_FALLBACK_MODEL]

    print("  No API backends available. Using local rule-based extraction.")
    return "local", []


# =====================================================================
# 📥 TRACKER (pearls_processed.xlsx)
# =====================================================================
def load_tracker():
    if not os.path.exists(PEARLS_TRACKER):
        return {}
    try:
        with open(PEARLS_TRACKER, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def update_tracker(file_name, count, mode):
    tracker = {}
    if os.path.exists(PEARLS_TRACKER):
        try:
            with open(PEARLS_TRACKER, "r", encoding="utf-8") as f:
                tracker = json.load(f)
        except Exception:
            tracker = {}
    tracker[file_name] = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode,
        "count": count
    }
    tmp = PEARLS_TRACKER + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(tracker, f, indent=2)
        os.replace(tmp, PEARLS_TRACKER)
    except Exception:
        pass


# =====================================================================
# 📖 CSV HELPERS
# =====================================================================
def load_existing_papers():
    if not os.path.exists(PEARLS_CSV):
        return set(), 1
    try:
        with open(PEARLS_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            papers = set()
            max_id = 0
            for row in reader:
                src = row.get("source_paper", "").strip()
                if src:
                    papers.add(src)
                try:
                    max_id = max(max_id, int(row.get("id", 0)))
                except (ValueError, TypeError):
                    pass
            return papers, max_id + 1
    except Exception:
        return set(), 1


def append_pearls_to_csv(pearls):
    existing_rows = []
    if os.path.exists(PEARLS_CSV):
        try:
            with open(PEARLS_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_rows.append(row)
        except Exception:
            pass

    next_id = 0
    if existing_rows:
        ids = []
        for r in existing_rows:
            try:
                ids.append(int(r.get("id", 0)))
            except (ValueError, TypeError):
                pass
        next_id = (max(ids) + 1) if ids else 1

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    all_rows = existing_rows + pearls

    with open(PEARLS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PEARLS_CSV_HEADERS)
        writer.writeheader()
        for i, row in enumerate(all_rows):
            out = {}
            for key in PEARLS_CSV_HEADERS:
                val = row.get(key, "")
                if key == "id":
                    val = str(i)
                elif key == "timestamp" and not val:
                    val = now_ts
                elif isinstance(val, float) and str(val) == "nan":
                    val = ""
                out[key] = str(val) if val is not None else ""
            writer.writerow(out)

    return len(all_rows)


# =====================================================================
# 📡 AI CALLERS
# =====================================================================
def try_parse_ollama_response(raw):
    """Attempt multiple strategies to extract valid JSON from Ollama output."""
    if not raw:
        return None

    # Strategy 1: direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strategy 2: strip markdown fences
    cleaned = re.sub(r'^```(?:json)?\s*', '', raw.strip())
    cleaned = re.sub(r'\s*```$', '', cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 3: fix truncated JSON — append missing closing brackets
    opens = raw.count('{') + raw.count('[')
    closes = raw.count('}') + raw.count(']')
    missing = opens - closes
    if 0 < missing < 20:
        repaired = raw.strip()
        # Append closing brackets in reverse nesting order (] first, then })
        repaired += ']' * (repaired.count('[') - repaired.count(']'))
        repaired += '}' * (repaired.count('{') - repaired.count('}'))
        # Also close unfinished string at end
        if repaired.count('"') % 2 != 0:
            repaired += '"'
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            # Strategy 3b: try extracting first valid JSON object block
            brace_start = repaired.find('{')
            if brace_start >= 0:
                depth = 0
                for i in range(brace_start, len(repaired)):
                    if repaired[i] == '{':
                        depth += 1
                    elif repaired[i] == '}':
                        depth -= 1
                        if depth == 0:
                            candidate = repaired[brace_start:i + 1]
                            try:
                                return json.loads(candidate)
                            except json.JSONDecodeError:
                                break
        except Exception:
            pass

    # Strategy 4: regex search for first JSON object or array
    for pattern in [r'\{.*\}', r'\[.*\]']:
        match = re.search(pattern, raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except (json.JSONDecodeError, ValueError):
                pass

    return None


def call_ollama(prompt, model, is_retry=False):
    """Call Ollama API with JSON format constraint."""
    if is_retry and len(prompt) > 4000:
        print(f"  Truncating prompt to 4000 chars and retrying...")
        prompt = prompt[:4000]

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": PEARL_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": TEMPERATURE,
            "num_predict": MAX_TOKENS
        }
    }
    try:
        import requests
        resp = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json=payload,
            timeout=300
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data.get("message", {}).get("content", "").strip()
        if not raw:
            raise ValueError("Empty response from Ollama")

        result = try_parse_ollama_response(raw)
        if result is not None:
            return result

        # Retry once with truncated prompt if parse fails
        if not is_retry and len(prompt) > 4000:
            print(f"  JSON parse failed, retrying with truncated prompt...")
            return call_ollama(prompt, model, is_retry=True)

        raise ValueError("Could not parse JSON from Ollama response")

    except Exception as e:
        raise RuntimeError(f"Ollama call failed: {e}")


def call_together(prompt, model):
    """Call Together AI with fallback chain."""
    from together import Together
    client = Together(api_key=TOGETHER_API_KEY)
    fallback_models = [model, TOGETHER_FALLBACK_MODEL]
    last_error = None

    for m in fallback_models:
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                    model=m,
                    messages=[
                        {"role": "system", "content": PEARL_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
            timeout=300
                )
                raw = response.choices[0].message.content
                if raw is None or raw.strip() == "":
                    raise ValueError("Empty response")
                raw = raw.strip()
                if raw.startswith("```"):
                    raw = re.sub(r'^```(?:json)?\s*', '', raw)
                    raw = re.sub(r'\s*```$', '', raw)
                return json.loads(raw)
            except Exception as e:
                last_error = e
                time.sleep(2)
        if len(fallback_models) > 1:
            print(f"    {m} failed, trying fallback model...")
    raise RuntimeError(f"Together AI failed: {last_error}")


def extract_local(payload):
    """Rule-based extraction from payload fields."""
    text_parts = []
    for p in payload.get("key_pearls", []):
        if isinstance(p, str):
            text_parts.append(p)
    for s in payload.get("sections", []):
        if isinstance(s.get("content"), str):
            text_parts.append(s["content"])
        for sp in s.get("section_pearls", []):
            if isinstance(sp, str):
                text_parts.append(sp)
    for b in payload.get("recommendation_blocks", []):
        if isinstance(b.get("narrative"), str):
            text_parts.append(b["narrative"])
        for r in b.get("recommendations", []):
            if isinstance(r.get("statement"), str):
                text_parts.append(r["statement"])

    full_text = "\n".join(text_parts)
    lines = full_text.split("\n")
    candidates = []
    seen = set()

    for line in lines:
        s = line.strip()
        if s.startswith("-") or s.startswith("*"):
            content = s.lstrip("-* ").strip()
            if content and len(content) > 20:
                key = content[:80].lower()
                if key not in seen:
                    seen.add(key)
                    candidates.append(content)
        elif any(kw in s.lower() for kw in ["mg", "mmhg", "cmh2o", "%", "p=", "p <", "p<", "ci ", "nnt", "nnh", "rr ", "or ", "hr="]):
            key = s[:80].lower()
            if key not in seen:
                seen.add(key)
                candidates.append(s)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    spec_map = load_specialties_map()
    specialty_list = payload.get("specialty", [])
    system = normalize_specialty(specialty_list, spec_map)
    source = payload.get("title") or payload.get("paper_name", "")
    doi = payload.get("doi", "")
    author = payload.get("authors") or payload.get("primary_authors", "")
    ptype = payload.get("article_subtype") or payload.get("doc_type", "")

    result = []
    for c in candidates[:25]:
        result.append({
            "timestamp": timestamp,
            "source_paper": source,
            "doi": doi,
            "author": author,
            "system": system,
            "type": ptype,
            "pearl": c[:500],
            "remarks": "",
            "file_name": "",
            "topic": ""
        })
    return result


# =====================================================================
# 📝 PROMPT BUILDER
# =====================================================================
def build_prompt(payload):
    parts = []

    title = payload.get("title") or payload.get("paper_name", "")
    doc_type = payload.get("doc_type", "")
    subtype = payload.get("article_subtype", "")
    summary = payload.get("one_line_summary", "")
    strengths = payload.get("strengths_limitations", "")

    if title:
        parts.append(f"Title: {title}")
    if doc_type or subtype:
        parts.append(f"Type: {doc_type} / {subtype}")
    if summary:
        parts.append(f"Summary: {summary}")

    key_pearls = payload.get("key_pearls", [])
    if key_pearls:
        parts.append("\nKey Pearls:\n" + "\n".join(f"- {p}" for p in key_pearls))

    sections = payload.get("sections", [])
    for s in sections:
        heading = s.get("heading", "")
        content = s.get("content", "")
        sp = s.get("section_pearls", [])
        block = ""
        if heading:
            block += f"\n## {heading}\n"
        if content:
            block += content + "\n"
        if sp:
            block += "Section Pearls:\n" + "\n".join(f"- {p}" for p in sp) + "\n"
        if block:
            parts.append(block)

    rec_blocks = payload.get("recommendation_blocks", [])
    for b in rec_blocks:
        topic = b.get("topic", "")
        narrative = b.get("narrative", "")
        block = ""
        if topic:
            block += f"\n## {topic}\n"
        if narrative:
            block += narrative + "\n"
        for r in b.get("recommendations", []):
            rid = r.get("rec_id", "")
            stmt = r.get("statement", "")
            strength = r.get("strength", "")
            grade = r.get("evidence_grade", "")
            meta = f" [{strength}, {grade}]" if strength or grade else ""
            if stmt:
                block += f"- {rid}: {stmt}{meta}\n" if rid else f"- {stmt}{meta}\n"
        if block:
            parts.append(block)

    protocol = payload.get("bedside_protocol", [])
    if protocol:
        block = "\nBedside Protocol:\n"
        for step in protocol:
            sn = step.get("step", "")
            stitle = step.get("title", "")
            action = step.get("action", "")
            block += f"Step {sn}: {stitle} -> {action}\n"
        parts.append(block)

    drugs_doses = payload.get("drugs_doses", [])
    if drugs_doses:
        block = "\nDrugs & Doses:\n"
        for dd in drugs_doses:
            drug = dd.get("drug", "")
            dose = dd.get("dose", "")
            indication = dd.get("indication", "")
            adverse = dd.get("adverse_effects", "")
            block += f"- {drug}"
            if dose:
                block += f" | Dose: {dose}"
            if indication:
                block += f" | Indication: {indication}"
            if adverse:
                block += f" | Adverse: {adverse}"
            block += "\n"
        parts.append(block)

    if strengths:
        parts.append(f"\nStrengths & Limitations:\n{strengths}")

    return "\n".join(parts)


# =====================================================================
# 🚀 MAIN
# =====================================================================
def main():
    parser = argparse.ArgumentParser(description="Extract clinical pearls from JSON summaries.")
    parser.add_argument("--max", type=int, default=None,
                        help=f"Max papers to process (default: {'all' if MAX_PAPERS == 0 else MAX_PAPERS})")
    parser.add_argument("--backend", choices=["ollama", "together", "local"], default=None,
                        help="Force a specific backend (default: auto-detect)")
    parser.add_argument("--model", type=str, default=None,
                        help="Model name for Ollama or Together AI")
    args = parser.parse_args()

    max_papers = args.max if args.max is not None else MAX_PAPERS
    force_backend = args.backend
    force_model = args.model

    print("[AI] hack.CCM Pearl Extractor (Together/Ollama)")
    print(f"  Backend: {force_backend or 'auto-detect'}")

    if force_backend == "ollama" and not force_model:
        force_model = DEFAULT_OLLAMA_MODEL
    elif force_backend == "together" and not force_model:
        force_model = DEFAULT_TOGETHER_MODEL

    # Backend detection
    if force_backend:
        backend = force_backend
        available_models = [force_model] if force_model else []
        if backend == "ollama" and not force_model:
            available_models = [DEFAULT_OLLAMA_MODEL]
        elif backend == "together" and not force_model:
            available_models = [DEFAULT_TOGETHER_MODEL, TOGETHER_FALLBACK_MODEL]
    else:
        backend, available_models = detect_backend()

    model = force_model or (available_models[0] if available_models else None)
    print(f"  Model: {model or 'N/A (local)'}")
    print(f"  Max papers: {'all' if max_papers == 0 else max_papers}")
    print()

    processed_files = load_tracker()
    existing_papers, _ = load_existing_papers()

    json_files = []
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for fname in files:
            if fname.endswith(".json"):
                json_files.append(os.path.join(root, fname))

    print(f"  Found {len(json_files)} total JSON files")
    print(f"  Already processed: {len(processed_files)} files")
    print(f"  Already in CSV: {len(existing_papers)} papers")

    to_process = []
    for fpath in json_files:
        fname = os.path.basename(fpath)
        if fname in processed_files:
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                payload = json.load(f)
            paper_name = payload.get("title") or payload.get("paper_name", "")
            if paper_name in existing_papers:
                continue
            to_process.append((fpath, payload, fname))
        except Exception as e:
            print(f"  Skipping {os.path.basename(fpath)}: {e}")
            continue

    if max_papers > 0:
        to_process = to_process[:max_papers]

    print(f"  To process this run: {len(to_process)} files")
    print()

    if not to_process:
        print("[OK] No new files to process. Exiting.")
        return

    spec_map = load_specialties_map()
    total_pearls = 0

    for idx, (fpath, payload, fname) in enumerate(to_process, start=1):
        paper_name = payload.get("title") or payload.get("paper_name", fname)
        print(f"[{idx}/{len(to_process)}] {paper_name}")

        # Build AI prompt from full payload
        prompt = build_prompt(payload)
        if len(prompt.strip()) < 30:
            print(f"  [SKIP] Skipping (no content)")
            update_tracker(fname, 0, backend)
            continue

        # Extract metadata for CSV
        source = payload.get("title") or payload.get("paper_name", "")
        doi = payload.get("doi", "")
        author = payload.get("authors") or payload.get("primary_authors", "")
        specialty_list = payload.get("specialty", [])
        system = normalize_specialty(specialty_list, spec_map)
        ptype = payload.get("article_subtype") or payload.get("doc_type", "")

        # Extract pearls via selected backend
        try:
            if backend == "ollama":
                result = call_ollama(prompt, model)
            elif backend == "together":
                result = call_together(prompt, model)
            else:
                result = extract_local(payload)

            if isinstance(result, dict) and "pearls" in result:
                raw_pearls = result["pearls"]
            elif isinstance(result, list):
                raw_pearls = result
            else:
                print(f"  [SKIP] No pearls extracted (unexpected format)")
                update_tracker(fname, 0, backend)
                continue

            if not raw_pearls or len(raw_pearls) == 0:
                print(f"  [SKIP] No pearls extracted")
                update_tracker(fname, 0, backend)
                continue

        except Exception as e:
            print(f"  [WARN] AI extraction failed: {e}, falling back to local...")
            result = extract_local(payload)
            raw_pearls = result if isinstance(result, list) else result.get("pearls", [])
            if not raw_pearls:
                print(f"  [SKIP] No pearls extracted (local fallback also empty)")
                update_tracker(fname, 0, "local")
                continue

        # Format as CSV rows
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dedup_seen = set()
        pearl_rows = []

        for p in raw_pearls[:25]:
            if isinstance(p, dict):
                text = p.get("text", "").strip()
                topic = p.get("topic", "").strip()
            elif isinstance(p, str):
                text = p.strip()
                topic = ""
            else:
                continue

            if len(text) < 15:
                continue

            key = text[:100].lower()
            if key in dedup_seen:
                continue
            dedup_seen.add(key)

            pearl_rows.append({
                "id": "",
                "timestamp": timestamp,
                "source_paper": source,
                "doi": doi,
                "author": author,
                "system": system,
                "type": ptype,
                "pearl": text[:500],
                "remarks": "",
                "file_name": fname,
                "topic": topic,
            })

        if not pearl_rows:
            print(f"  [SKIP] No new pearls after dedup")
            update_tracker(fname, 0, backend)
            continue

        count = append_pearls_to_csv(pearl_rows)
        update_tracker(fname, count, backend)
        total_pearls += count
        print(f"  [OK] {count} pearls saved")

    print()
    print(f"[DONE] {total_pearls} new pearls written to {PEARLS_CSV}")

    # Validate CSV
    try:
        with open(PEARLS_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if reader.fieldnames != PEARLS_CSV_HEADERS:
            print(f"  [WARN] Header mismatch: expected {PEARLS_CSV_HEADERS}, got {reader.fieldnames}")
        else:
            print(f"  [OK] CSV validated: {len(rows)} rows, {len(reader.fieldnames)} columns")
    except Exception as e:
        print(f"  [WARN] CSV validation failed: {e}")


if __name__ == "__main__":
    main()
