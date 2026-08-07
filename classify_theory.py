"""
classify_theory.py - Organize Theory Topics (output_files/Theory MDs/) into
specialty/subtopic subfolders and generate clean display titles via LLM.

Moves each flat note into:
    output_files/Theory MDs/{Specialty}/{Subtopic}/{filename}
and writes theory_notes_meta.json (sidecar index: titles + provenance).

Usage:
    python classify_theory.py              # classify & move all
    python classify_theory.py --dry-run    # preview only
    python classify_theory.py --max 3      # cap at N notes
    python classify_theory.py --file "X.md"
    python classify_theory.py --force
    python classify_theory.py --llm openai/gpt-oss-120b [--api-key KEY] [--base-url URL]
"""

import os
import sys
import re
import json
import time
import shutil
import argparse
from datetime import datetime

from openai import OpenAI

from acumen_core.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from acumen_core.flashcards import normalize_subtopic

THEORY_DIR = os.path.join("output_files", "Theory MDs")
META_FILE = os.path.join(THEORY_DIR, "theory_notes_meta.json")
DEFAULT_MODEL = "openai/gpt-oss-120b"
BATCH_SIZE = 6
SNIPPET_CHARS = 1500
MAX_RETRIES = 3

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

VALID_SPECIALTIES = [
    "Cardiology", "Pulmonology", "Infectious Diseases", "Neurology", "Nephrology",
    "Gastroenterology", "Hematology", "Hepatology", "Immunology", "Sepsis", "Trauma",
    "Endocrinology", "General", "Multisystem", "Nutrition",
    "Obstetrics And Gynecology", "Rheumatology", "Toxicology", "Oncology", "Surgery",
    "Cardiothoracic", "Vascular", "Other",
]

SYSTEM_PROMPT = """You are a critical care educator organizing a structured study library.
You receive several theory notes (file name + excerpt). For EACH note return:
- "title": a clean, exam-worthy display title (<=10 words, no file-name fragments, no markdown symbols)
- "specialty": the single best specialty chosen EXACTLY from: Cardiology, Pulmonology, Infectious Diseases, Neurology, Nephrology, Gastroenterology, Hematology, Hepatology, Immunology, Sepsis, Trauma, Endocrinology, General, Multisystem, Nutrition, Obstetrics And Gynecology, Rheumatology, Toxicology, Oncology, Surgery, Cardiothoracic, Vascular, Other
- "subtopic": the single best canonical subtopic for that specialty (2-5 words, e.g. "Sepsis and Septic Shock", "ACS", "Ventilation", "Renal Replacement Therapy")
Return ONLY valid JSON: {"notes": [{"file": "<exact input file name>", "title": "...", "specialty": "...", "subtopic": "..."}]}. Include EVERY input note exactly once. No preamble, no markdown fences, no commentary."""


def _client(api_key=None, base_url=None):
    return OpenAI(
        api_key=api_key or OPENROUTER_API_KEY,
        base_url=base_url or OPENROUTER_BASE_URL,
    )


def _strip_fences(raw):
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
    raw = re.sub(r"\n?\s*```$", "", raw)
    return raw.strip()


def _extract_json(raw):
    raw = _strip_fences(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            return json.loads(m.group(0))
        raise


def classify_batch(client, model, notes):
    lines = []
    for n in notes:
        stem = os.path.splitext(n["name"])[0]
        lines.append("--- note file: {}\nTitle hint: {}\nExcerpt:\n{}".format(n["name"], stem, n["snippet"]))
    user_content = "\n\n".join(lines)
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.2,
                max_tokens=4000,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or ""
            data = _extract_json(content)
            if not isinstance(data.get("notes"), list):
                raise ValueError("Missing 'notes' array")
            return data["notes"]
        except Exception as e:
            last_error = e
            print("    [X] classify attempt {} failed: {}".format(attempt + 1, e))
            if attempt < MAX_RETRIES - 1:
                time.sleep(3 * (attempt + 1))
    raise last_error or RuntimeError("Classification exhausted")


def clean_specialty(cand):
    if not cand:
        return "General"
    c = str(cand).strip().lower()
    for v in VALID_SPECIALTIES:
        if v.lower() == c or v.lower().replace(" ", "") == c.replace(" ", ""):
            return v
    for v in VALID_SPECIALTIES:
        if c in v.lower() or v.lower() in c:
            return v
    return "General"


def clean_title(cand, fallback):
    t = str(cand or "").strip()
    t = re.sub(r"^#{1,6}\s*", "", t)
    t = t.replace("**", "").replace("`", "")
    t = re.sub(r"\s+", " ", t)
    if len(t) < 3 or len(t) > 120:
        t = os.path.splitext(os.path.basename(fallback))[0].replace("_", " ").strip()
    return t[:120]


def clean_subtopic(cand):
    s = str(cand or "").strip()
    s = re.sub(r"[\\/:*?\"<>|\n\r\t]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:60] if s else "General"


def scan_notes(theory_dir):
    out = []
    for root, dirs, files in os.walk(theory_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        if root == theory_dir:
            files = [f for f in files if f != "theory_notes_meta.json"]
        for fn in sorted(files):
            path = os.path.join(root, fn)
            if not os.path.isfile(path) or fn.startswith("."):
                continue
            if fn == "theory_notes_meta.json":
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    md = f.read()
            except Exception:
                continue
            snippet = md.strip()
            snippet = re.sub(r"^\s*<img[^>]*>\s*", "", snippet)
            snippet = snippet[:SNIPPET_CHARS]
            rel = os.path.relpath(path, theory_dir)
            parts = rel.split(os.sep)
            out.append({
                "name": fn,
                "path": path,
                "rel": rel.replace(os.sep, "/"),
                "in_subfolder": len(parts) > 1,
                "snippet": snippet,
            })
    return out


def load_meta():
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_meta(meta):
    tmp = META_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    os.replace(tmp, META_FILE)


def main():
    ap = argparse.ArgumentParser(description="Classify & organize theory notes")
    ap.add_argument("--dry-run", action="store_true", help="preview only, no moves/writes")
    ap.add_argument("--max", type=int, default=0, help="cap at N notes (0 = unlimited)")
    ap.add_argument("--file", default="", help="only process one file name")
    ap.add_argument("--force", action="store_true", help="re-process even if already indexed")
    ap.add_argument("--llm", default=DEFAULT_MODEL, help="OpenRouter model (default: gpt-oss-120b)")
    ap.add_argument("--api-key", default="", help="override API key")
    ap.add_argument("--base-url", default="", help="override base URL")
    args = ap.parse_args()

    if not os.path.isdir(THEORY_DIR):
        print("[X] Theory directory not found: {}".format(THEORY_DIR))
        sys.exit(1)

    meta = load_meta()
    all_notes = scan_notes(THEORY_DIR)
    indexed = {v.get("original", k) for k, v in meta.items()}
    if args.file:
        all_notes = [n for n in all_notes if args.file in n["name"]]
    flat = [n for n in all_notes if not n["in_subfolder"] and n["name"] not in indexed]
    placed = [n for n in all_notes if n["in_subfolder"] and n["name"] not in indexed]
    if args.max > 0:
        flat = flat[: args.max]

    # Notes already organised into {Specialty}/{Subtopic}/ but missing a meta
    # entry (e.g. an interrupted earlier run): derive their index cheaply
    # without a second LLM pass.
    now = datetime.now().isoformat(timespec="seconds")
    for n in placed:
        parts = n["rel"].split("/")
        system = parts[0]
        sub = parts[1] if len(parts) > 1 else "General"
        title = clean_title("", n["name"])
        body_head = n["snippet"].lstrip()
        if body_head.startswith("<img") and "\n" in body_head:
            body_head = body_head.split("\n", 1)[1]
        m = re.search(r"^\s*#{1,6}\s+(.+?)\s*$", body_head, re.M)
        if m:
            title = m.group(1).strip()
        if len(title) < 3 or len(title) > 120:
            title = os.path.splitext(n["name"])[0].replace("_", " ").strip()
        meta[n["rel"]] = {
            "title": title[:120],
            "system": system,
            "subtopic": sub,
            "original": n["name"],
            "processed_at": now,
        }
        print("  INDEX {} {:<50} -> {}/{}".format("KEPT ", n["name"], system, sub))
    if placed:
        save_meta(meta)

    if not flat:
        if placed:
            print("\nDone. {} already-placed note(s) re-indexed; {} left to classify.".format(len(placed), len(flat)))
        else:
            print("[~] No unprocessed flat notes found. Use --force to re-run.")
        return

    print("Found {} note(s) to classify ({})".format(len(flat), args.llm))
    client = None
    if not args.dry_run:
        client = _client(args.api_key, args.base_url)

    results = []
    for i in range(0, len(flat), BATCH_SIZE):
        batch = flat[i : i + BATCH_SIZE]
        print("  Classifying batch {} ({} notes)...".format(i // BATCH_SIZE + 1, len(batch)))
        if args.dry_run:
            for n in batch:
                results.append({"file": n["name"], "title": os.path.splitext(n["name"])[0].replace("_", " "),
                                "specialty": "General", "subtopic": "General"})
            continue
        try:
            batch_results = classify_batch(client, args.llm, batch)
            results.extend(batch_results)
        except Exception as e:
            print("    [X] Batch failed: {}".format(e))
            continue

    if args.dry_run:
        for r in sorted(results, key=lambda x: x.get("file", "")):
            print("  DRY-RUN  {:<58} -> {} / {} / {}".format(
                r.get("file"), r.get("specialty"), r.get("subtopic"), r.get("title")))
        print("\n(dry run only — nothing moved or written)")
        return

    changed = 0
    for r in results:
        fname = r.get("file", "")
        system = clean_specialty(r.get("specialty"))
        sub = r.get("subtopic")
        matched = normalize_subtopic(system, sub) if sub else None
        sub_clean = clean_subtopic(matched if matched else sub)
        title = clean_title(r.get("title"), fname)
        dest_dir = os.path.join(THEORY_DIR, system, sub_clean)
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, fname)
        src = os.path.join(THEORY_DIR, fname)
        if not os.path.abspath(src) == os.path.abspath(dest):
            if os.path.exists(dest):
                base, ext = os.path.splitext(fname)
                dest = os.path.join(dest_dir, base + " (2)" + ext)
            shutil.move(src, dest)
            changed += 1
        rel = os.path.relpath(dest, THEORY_DIR).replace(os.sep, "/")
        meta[rel] = {
            "title": title,
            "system": system,
            "subtopic": sub_clean,
            "original": fname,
            "processed_at": now,
        }
        print("  {} {:<50} -> {}/{}".format("MOVED" if dest != src else "KEPT ", fname, system, sub_clean))

    meta = {k: v for k, v in meta.items() if os.path.exists(os.path.join(
        os.path.dirname(META_FILE), k.replace("/", os.sep)))}
    save_meta(meta)
    print("\nDone. {} note(s) moved; index updated at {}".format(changed, META_FILE))


if __name__ == "__main__":
    main()