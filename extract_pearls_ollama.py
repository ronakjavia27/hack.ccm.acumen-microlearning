#!/usr/bin/env python3
"""
extract_pearls_ollama.py — Extract clinical pearls via local Ollama.
Extracts high-yield, evidence-based pearls from structured JSON summaries
using Ollama (local LLM), with rule-based extraction as fallback.

Usage:
    python extract_pearls_ollama.py
    python extract_pearls_ollama.py --max 5
    python extract_pearls_ollama.py --model gemma4:27b
"""

import os
import sys
import json
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
# CONFIG
# =====================================================================
OUTPUT_DIR = "./output_files"
PEARLS_JSON = "./pearls.json"
PEARLS_TRACKER = "./pearls_processed.json"

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = "gemma4:latest"

MAX_TOKENS = 4096
TEMPERATURE = 0.2
MAX_PAPERS = 0

# Specialty aliases
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

TITLE_SPECIALTY_KEYWORDS = {
    "cardiologist": "Cardiology", "cardiology": "Cardiology", "cardiac": "Cardiology",
    "coronary": "Cardiology", "myocardial": "Cardiology", "heart": "Cardiology",
    "arrhythmia": "Cardiology", "ventricular": "Cardiology", "atrial": "Cardiology",
    "aortic": "Cardiology", "mitral": "Cardiology", "valvular": "Cardiology",
    "pericardial": "Cardiology", "defibrillator": "Cardiology", "stent": "Cardiology",
    "angioplasty": "Cardiology", "statin": "Cardiology",
    "neurologist": "Neurology", "neurology": "Neurology", "neurologic": "Neurology",
    "brain": "Neurology", "stroke": "Neurology", "cerebral": "Neurology",
    "intracranial": "Neurology", "cranial": "Neurology", "seizure": "Neurology",
    "epilepsy": "Neurology", "neurocritical": "Neurology", "subarachnoid": "Neurology",
    "intracerebral": "Neurology", "encephalopathy": "Neurology", "spinal": "Neurology",
    "neuromuscular": "Neurology",
    "nephrologist": "Nephrology", "nephrology": "Nephrology", "kidney": "Nephrology",
    "renal": "Nephrology", "dialysis": "Nephrology", "glomerular": "Nephrology",
    "creatinine": "Nephrology",
    "pulmonologist": "Pulmonology", "pulmonology": "Pulmonology", "lung": "Pulmonology",
    "respiratory": "Pulmonology", "pulmonary": "Pulmonology", "airway": "Pulmonology",
    "tracheostomy": "Pulmonology", "bronchoscopy": "Pulmonology", "pleural": "Pulmonology",
    "copd": "Pulmonology",
    "gastroenterologist": "Gastroenterology", "gastroenterology": "Gastroenterology",
    "biliary": "Gastroenterology", "pancreas": "Gastroenterology", "pancreatic": "Gastroenterology",
    "colon": "Gastroenterology", "colonic": "Gastroenterology", "gastric": "Gastroenterology",
    "esophageal": "Gastroenterology", "intestine": "Gastroenterology", "intestinal": "Gastroenterology",
    "hepatologist": "Hepatology", "hepatology": "Hepatology", "cirrhosis": "Hepatology",
    "portal": "Hepatology",
    "infectious": "Infectious Diseases", "tuberculosis": "Infectious Diseases",
    "hiv": "Infectious Diseases", "bacteremia": "Infectious Diseases",
    "antimicrobial": "Infectious Diseases", "fungal": "Infectious Diseases",
    "hematologist": "Hematology", "hematology": "Hematology", "coagulation": "Hematology",
    "thrombosis": "Hematology", "thromboembolism": "Hematology", "anemia": "Hematology",
    "hemoglobin": "Hematology", "platelet": "Hematology", "neutropenia": "Hematology",
    "oncologist": "Oncology", "oncology": "Oncology", "cancer": "Oncology",
    "tumor": "Oncology", "carcinoma": "Oncology", "malignancy": "Oncology",
    "neoplasm": "Oncology", "chemotherapy": "Oncology", "immunotherapy": "Oncology",
    "metastasis": "Oncology",
    "endocrinologist": "Endocrinology", "endocrinology": "Endocrinology",
    "diabetes": "Endocrinology", "thyroid": "Endocrinology", "hormone": "Endocrinology",
    "pituitary": "Endocrinology", "adrenal": "Endocrinology", "glycemic": "Endocrinology",
    "glucose": "Endocrinology", "insulin": "Endocrinology", "cortisol": "Endocrinology",
    "surgeon": "Surgery", "surgery": "Surgery", "surgical": "Surgery",
    "thoracotomy": "Surgery", "laparotomy": "Surgery", "laparoscopic": "Surgery",
    "resection": "Surgery", "bypass": "Surgery", "craniotomy": "Surgery",
    "traumatic": "Trauma", "hemorrhagic shock": "Trauma", "damage control": "Trauma",
    "obstetric": "Obstetrics and Gynecology", "obstetrics": "Obstetrics and Gynecology",
    "gynecology": "Obstetrics and Gynecology", "pregnancy": "Obstetrics and Gynecology",
    "pregnant": "Obstetrics and Gynecology", "fetal": "Obstetrics and Gynecology",
    "maternal": "Obstetrics and Gynecology", "placental": "Obstetrics and Gynecology",
    "preeclampsia": "Obstetrics and Gynecology", "eclampsia": "Obstetrics and Gynecology",
    "postpartum": "Obstetrics and Gynecology",
    "immunologist": "Immunology", "immunology": "Immunology", "autoimmune": "Immunology",
    "immunodeficiency": "Immunology", "immunosuppression": "Immunology",
    "rheumatologist": "Rheumatology", "rheumatology": "Rheumatology", "rheumatic": "Rheumatology",
    "vasculitis": "Rheumatology", "lupus": "Rheumatology", "scleroderma": "Rheumatology",
    "toxicologist": "Toxicology", "toxicology": "Toxicology", "poisoning": "Toxicology",
    "overdose": "Toxicology", "toxin": "Toxicology", "intoxication": "Toxicology",
    "nutritional": "Nutrition", "enteral": "Nutrition", "parenteral": "Nutrition",
    "malnutrition": "Nutrition",
    "septic shock": "Sepsis", "septic": "Sepsis",
}

PEARLS_JSON_FIELDS = [
    "id", "timestamp", "source_paper", "doi",
    "author", "system", "type", "pearl", "remarks", "file_name", "topic"
]

# =====================================================================
# PEARL EXTRACTION PROMPT
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
# SPECIALTY NORMALIZATION
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


def infer_specialty_from_title(title, spec_map):
    if not title:
        return "Other"
    title_lower = title.lower()
    scores = {}
    for keyword, specialty in TITLE_SPECIALTY_KEYWORDS.items():
        if keyword.lower() in title_lower:
            scores[specialty] = scores.get(specialty, 0) + 1
    if not scores:
        return "Other"
    best = max(scores, key=scores.get)
    return spec_map.get(best.lower(), best)


# =====================================================================
# BACKEND DETECTION
# =====================================================================
def detect_ollama():
    """Check if Ollama is available."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            models = [line.split()[0] for line in result.stdout.strip().split("\n")[1:] if line.strip()]
            if models:
                print(f"  Detected Ollama models: {', '.join(models)}")
                return True, models
    except (FileNotFoundError, subprocess.TimeoutExpired, IndexError):
        pass
    return False, []


# =====================================================================
# TRACKER
# =====================================================================
def load_tracker():
    if not os.path.exists(PEARLS_TRACKER):
        return {}
    try:
        with open(PEARLS_TRACKER, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def update_tracker(file_name, count):
    tracker = {}
    if os.path.exists(PEARLS_TRACKER):
        try:
            with open(PEARLS_TRACKER, "r", encoding="utf-8") as f:
                tracker = json.load(f)
        except Exception:
            tracker = {}
    tracker[file_name] = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "ollama",
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
# JSON HELPERS
# =====================================================================
def _atomic_write_json(file_path, data):
    tmp = file_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, file_path)


def load_existing_papers():
    if not os.path.exists(PEARLS_JSON):
        return set(), 1
    try:
        with open(PEARLS_JSON, "r", encoding="utf-8") as f:
            rows = json.load(f)
        papers = set()
        max_id = 0
        for row in rows:
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


def append_pearls_to_json(pearls):
    existing_rows = []
    if os.path.exists(PEARLS_JSON):
        try:
            with open(PEARLS_JSON, "r", encoding="utf-8") as f:
                existing_rows = json.load(f)
        except Exception:
            pass

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    all_rows = existing_rows + pearls

    for i, row in enumerate(all_rows):
        out = {}
        for key in PEARLS_JSON_FIELDS:
            val = row.get(key, "")
            if key == "id":
                val = str(i)
            elif key == "timestamp" and not val:
                val = now_ts
            out[key] = str(val) if val is not None else ""
        all_rows[i] = out

    _atomic_write_json(PEARLS_JSON, all_rows)
    return len(all_rows)


# =====================================================================
# AI CALLER
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

    # Strategy 3: fix truncated JSON
    opens = raw.count('{') + raw.count('[')
    closes = raw.count('}') + raw.count(']')
    missing = opens - closes
    if 0 < missing < 20:
        repaired = raw.strip()
        repaired += ']' * (repaired.count('[') - repaired.count(']'))
        repaired += '}' * (repaired.count('{') - repaired.count('}'))
        if repaired.count('"') % 2 != 0:
            repaired += '"'
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            # Strategy 3b: extract first valid JSON object
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

    # Strategy 4: regex search
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

        if not is_retry and len(prompt) > 4000:
            print(f"  JSON parse failed, retrying with truncated prompt...")
            return call_ollama(prompt, model, is_retry=True)

        raise ValueError("Could not parse JSON from Ollama response")

    except Exception as e:
        raise RuntimeError(f"Ollama call failed: {e}")


# =====================================================================
# LOCAL FALLBACK
# =====================================================================
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
    source = payload.get("title") or payload.get("paper_name", "")
    specialty_list = payload.get("specialty", [])
    system = normalize_specialty(specialty_list, spec_map)
    if system == "Other":
        inferred = infer_specialty_from_title(source, spec_map)
        if inferred != "Other":
            system = inferred
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
# PROMPT BUILDER
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
# MAIN
# =====================================================================
def main():
    parser = argparse.ArgumentParser(description="Extract clinical pearls from JSON summaries using Ollama")
    parser.add_argument("--max", type=int, default=None,
                        help="Max papers to process (default: all)")
    parser.add_argument("--limit", type=str, default=None,
                        help="Comma-separated filenames to process (bypasses tracker)")
    parser.add_argument("--model", type=str, default=None,
                        help="Ollama model name (default: gemma4:latest)")
    parser.add_argument("--force-local", action="store_true",
                        help="Skip Ollama, use rule-based extraction only")
    args = parser.parse_args()

    max_papers = args.max if args.max is not None else MAX_PAPERS
    model = args.model or DEFAULT_OLLAMA_MODEL
    limit_files = set(f.strip() for f in args.limit.split(",")) if args.limit else None

    print("[AI] hack.CCM Pearl Extractor (Ollama)")
    print(f"  Model: {model}")

    if args.force_local:
        backend = "local"
        print("  Backend: local (rule-based)")
    else:
        available, _ = detect_ollama()
        if available:
            backend = "ollama"
            print(f"  Backend: Ollama ({model})")
        else:
            backend = "local"
            print("  Ollama not available. Using rule-based extraction.")

    print(f"  Max papers: {'all' if max_papers == 0 else max_papers}")
    if limit_files:
        print(f"  Limit to {len(limit_files)} specific file(s)")
    print()

    processed_files = load_tracker()
    existing_papers, _ = load_existing_papers()

    json_files = []
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for fname in files:
            if not fname.endswith(".json"):
                continue
            if limit_files and fname not in limit_files:
                continue
            json_files.append(os.path.join(root, fname))

    if limit_files:
        found = set(os.path.basename(f) for f in json_files)
        missing = limit_files - found
        if missing:
            print(f"  Warning: {len(missing)} file(s) not found in {OUTPUT_DIR}: {', '.join(sorted(missing))}")

    print(f"  Found {len(json_files)} total JSON files")
    print(f"  Already processed: {len(processed_files)} files")
    print(f"  Already in CSV: {len(existing_papers)} papers")

    to_process = []
    for fpath in json_files:
        fname = os.path.basename(fpath)
        if not limit_files and fname in processed_files:
            continue
        if limit_files and fname in processed_files:
            print(f"  [NOTE] {fname} was already processed — force-processing due to --limit")
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                payload = json.load(f)
            paper_name = payload.get("title") or payload.get("paper_name", "")
            if not limit_files and paper_name in existing_papers:
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

        prompt = build_prompt(payload)
        if len(prompt.strip()) < 30:
            print(f"  [SKIP] Skipping (no content)")
            update_tracker(fname, 0)
            continue

        source = payload.get("title") or payload.get("paper_name", "")
        doi = payload.get("doi", "")
        author = payload.get("authors") or payload.get("primary_authors", "")
        specialty_list = payload.get("specialty", [])
        system = normalize_specialty(specialty_list, spec_map)
        if system == "Other":
            inferred = infer_specialty_from_title(source, spec_map)
            if inferred != "Other":
                system = inferred
        ptype = payload.get("article_subtype") or payload.get("doc_type", "")

        try:
            if backend == "ollama":
                result = call_ollama(prompt, model)
            else:
                result = extract_local(payload)

            if isinstance(result, dict) and "pearls" in result:
                raw_pearls = result["pearls"]
            elif isinstance(result, list):
                raw_pearls = result
            else:
                print(f"  [SKIP] No pearls extracted (unexpected format)")
                update_tracker(fname, 0)
                continue

            if not raw_pearls or len(raw_pearls) == 0:
                print(f"  [SKIP] No pearls extracted")
                update_tracker(fname, 0)
                continue

        except Exception as e:
            print(f"  [WARN] AI extraction failed: {e}, falling back to local...")
            result = extract_local(payload)
            raw_pearls = result if isinstance(result, list) else result.get("pearls", [])
            if not raw_pearls:
                print(f"  [SKIP] No pearls extracted (local fallback also empty)")
                update_tracker(fname, 0)
                continue

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
            update_tracker(fname, 0)
            continue

        count = append_pearls_to_json(pearl_rows)
        update_tracker(fname, count)
        total_pearls += count
        print(f"  [OK] {count} pearls saved")

    print()
    print(f"[DONE] {total_pearls} new pearls written to {PEARLS_JSON}")

    try:
        with open(PEARLS_JSON, "r", encoding="utf-8") as f:
            rows = json.load(f)
        if rows and not all(k in rows[0] for k in PEARLS_JSON_FIELDS):
            missing = [k for k in PEARLS_JSON_FIELDS if k not in rows[0]]
            print(f"  [WARN] Missing fields in first row: {missing}")
        else:
            print(f"  [OK] JSON validated: {len(rows)} entries")
    except Exception as e:
        print(f"  [WARN] JSON validation failed: {e}")


if __name__ == "__main__":
    main()
