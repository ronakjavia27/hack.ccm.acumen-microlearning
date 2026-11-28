"""
mcq_generator.py — build single-best-answer MCQs for the hack.CCM portal.

Sources
  * Theory notes   output_files/Theory MDs/{System}/{Subtopic}/*.md   (BOOKS/ skipped)
  * Guidelines     sent_summaries.json entries with type "Guideline"
                   -> output_files/{System}/Guideline/{stem}.json
                      (one_line_summary, key_pearls, recommendation_blocks)

Store (read by redefined_ui.py)
  output_files/mcqs/{System}/{Subtopic}.json
  {
    "system": "...", "subtopic": "...", "updated_at": "...",
    "questions": [{
      "id": uuid, "stem": "...",
      "options": [{"key": "A", "text": "..."}, ...],      # 4-5 options
      "answer": "B", "explanation": "...",
      "difficulty": "easy|medium|hard", "tags": [...],
      "source": {"kind": "theory|guideline", "ref": "...", "title": "..."},
      "status": "draft", "created_at": "..."
    }]
  }
Progress ledger: mcq_ledger.json  (sha256 of the source text -> question ids)

Usage
  python mcq_generator.py                       # generate for every new/changed source
  python mcq_generator.py status                # store + pending summary
  python mcq_generator.py --source theory --spec Pulmonology --max 3
  python mcq_generator.py --file "Pulmonology/ARDS/New Global Definition of ARDS (2023).md"
  python mcq_generator.py --per-source 10 --force
  python mcq_generator.py --dry-run --verbose   # preview, no API calls, no writes

  --llm openrouter|gemini (default openrouter, FLASHCARD_LLM_* cheap model)
  --api-key K --model M [--base-url U]          # direct OpenAI-compatible call
"""

import argparse
import hashlib
import json
import os
import random
import re
import sys
import uuid
from datetime import datetime

from acumen_core import config as _cfg
from acumen_core.llm import chunk_text, execute_openai_compat, execute_with_gemini
from acumen_core.tracking import save_json_atomic

OUTPUT_DIR = _cfg.OUTPUT_DIR
PROJECT_DIR = _cfg.PROJECT_DIR
THEORY_MDS_DIR = _cfg.THEORY_MDS_DIR
THEORY_BOOKS_FOLDER = getattr(_cfg, "THEORY_BOOKS_FOLDER", "BOOKS")
TRACKER_FILE = getattr(_cfg, "JSON_TRACKER_FILE", os.path.join(PROJECT_DIR, "sent_summaries.json"))

MCQ_DIR = os.getenv("MCQ_DIR", os.path.join(OUTPUT_DIR, "mcqs"))
MCQ_LEDGER_FILE = os.path.join(PROJECT_DIR, "mcq_ledger.json")
CHUNK_MCQ = 24000          # chars of source text per LLM call
TEMPERATURE_MCQ = 0.3
MAX_TOKENS_MCQ = 8192

SYSTEM_PROMPT = """You write single-best-answer multiple-choice questions for critical-care
physicians preparing for intensive-care exams (EDIC, IDCCM, FCICM style).

Rules:
- Use ONLY facts stated in the SOURCE text. Do not invent numbers, drugs or trials.
- Prefer short clinical vignettes (patient, findings, question). Pure recall is allowed
  for definitions, thresholds and landmark-trial results.
- Exactly one correct option. 4 or 5 options, all plausible, similar length,
  mutually exclusive. Never use "all of the above", "none of the above", "both A and B".
- The explanation (2-4 sentences) says why the answer is right AND why the strongest
  distractor is wrong, citing the source wording.
- difficulty: "easy" (recall), "medium" (apply), "hard" (integrate / exam trap).
- tags: 1-3 short clinical concepts.

Return JSON only:
{"questions": [{"stem": "...", "options": ["...", "...", "...", "..."],
  "answer_index": 0, "explanation": "...", "difficulty": "medium", "tags": ["..."]}]}"""

KEYS = "ABCDE"
BANNED = re.compile(r"\b(all|none) of the above\b|\bboth [a-e] and [a-e]\b", re.I)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def log(args, *msg):
    if args.verbose:
        print("  ", *msg)


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, type(default)) else default
    except (OSError, json.JSONDecodeError):
        return default


def safe_name(s):
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", str(s or "General")).strip(" .")
    return s or "General"


def store_path(system, subtopic):
    return os.path.join(MCQ_DIR, safe_name(system), safe_name(subtopic) + ".json")


def norm_stem(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------

def theory_sources(args):
    """Theory notes exactly as the portal sees them (same system/subtopic/title
    taxonomy, BOOKS/ skipped) via revamped_webapp.load_theory_notes()."""
    try:
        import revamped_webapp as portal
        notes = portal.load_theory_notes()
    except Exception as e:
        print(f"Could not load theory notes via revamped_webapp: {e}")
        return []
    out = []
    for n in notes:
        text = str(n.get("md") or "")
        if len(text) < 400:
            continue
        rel = str(n.get("rel") or n.get("id"))
        system = n.get("system") or "General"
        out.append({"kind": "theory", "ref": rel, "title": n.get("title") or rel, "system": system,
                    "subtopic": n.get("subtopic") or system, "text": text, "match": rel})
    return out


def guideline_sources(args):
    out = []
    entries = load_json(TRACKER_FILE, [])
    for e in entries:
        if str(e.get("type", "")).lower() != "guideline":
            continue
        system = str(e.get("system", "General")).strip() or "General"
        stem = os.path.splitext(str(e.get("file_name", "")))[0]
        if not stem:
            continue
        path = os.path.join(OUTPUT_DIR, system, "Guideline", stem + ".json")
        if not os.path.exists(path):
            path = next((os.path.join(r, stem + ".json") for r, _, fs in os.walk(OUTPUT_DIR)
                         if stem + ".json" in fs), None)
        if not path:
            continue
        d = load_json(path, {})
        lines = [f"# {d.get('title') or e.get('title')}", "", str(d.get("one_line_summary", ""))]
        for p in d.get("key_pearls") or []:
            lines.append(f"- {p}")
        for b in d.get("recommendation_blocks") or []:
            lines += ["", f"## {b.get('topic', '')}", str(b.get("narrative", ""))]
            for r in b.get("recommendations") or []:
                tag = " ".join(x for x in (r.get("strength"), r.get("evidence_grade")) if x)
                lines.append(f"- {r.get('statement', '')}" + (f" ({tag})" if tag else ""))
        text = "\n".join(lines).strip()
        if len(text) < 400:
            continue
        out.append({"kind": "guideline", "ref": str(e.get("file_name")), "title": str(e.get("title", stem)),
                    "system": system, "subtopic": str(e.get("subtopic", system) or system).strip(),
                    "text": text, "match": f"{system}/{e.get('file_name')}"})
    return out


def collect(args):
    srcs = []
    if args.source in ("theory", "all"):
        srcs += theory_sources(args)
    if args.source in ("guidelines", "all"):
        srcs += guideline_sources(args)
    if args.spec:
        srcs = [s for s in srcs if s["system"].lower() == args.spec.lower()]
    if args.file:
        f = args.file.replace("\\", "/").lower()
        srcs = [s for s in srcs if s["match"].lower().endswith(f) or s["ref"].lower() == f]
    return srcs


# ---------------------------------------------------------------------------
# LLM + validation
# ---------------------------------------------------------------------------

def call_llm(args, user_content):
    if args.api_key or args.model or args.llm != "gemini":
        return execute_openai_compat(
            SYSTEM_PROMPT, user_content,
            api_key=args.api_key or FLASHCARD_LLM_API_KEY_(),
            model=args.model or FLASHCARD_LLM_MODEL_(),
            base_url=args.base_url or FLASHCARD_LLM_BASE_URL_(),
            temperature=TEMPERATURE_MCQ, max_tokens=MAX_TOKENS_MCQ, json_mode=True,
        )
    return execute_with_gemini(SYSTEM_PROMPT, user_content, "mcq")


def FLASHCARD_LLM_API_KEY_():
    return getattr(_cfg, "FLASHCARD_LLM_API_KEY", None) or getattr(_cfg, "OPENROUTER_API_KEY", None)


def FLASHCARD_LLM_MODEL_():
    return getattr(_cfg, "FLASHCARD_LLM_MODEL", None) or getattr(_cfg, "OPENROUTER_MODEL", None)


def FLASHCARD_LLM_BASE_URL_():
    return getattr(_cfg, "FLASHCARD_LLM_BASE_URL", None) or getattr(_cfg, "OPENROUTER_BASE_URL", None)


def validate(raw, seen):
    """Return (question_dict | None, reason)."""
    stem = str(raw.get("stem", "")).strip()
    opts = [str(o).strip() for o in (raw.get("options") or []) if str(o).strip()]
    expl = str(raw.get("explanation", "")).strip()
    try:
        ai = int(raw.get("answer_index"))
    except (TypeError, ValueError):
        return None, "answer_index missing"
    if len(stem) < 20:
        return None, "stem too short"
    if not 4 <= len(opts) <= 5:
        return None, f"{len(opts)} options"
    if len({o.lower() for o in opts}) != len(opts):
        return None, "duplicate options"
    if not 0 <= ai < len(opts):
        return None, "answer_index out of range"
    if any(BANNED.search(o) for o in opts):
        return None, "banned option wording"
    if len(expl) < 30:
        return None, "explanation too short"
    key = norm_stem(stem)
    if key in seen:
        return None, "duplicate stem"
    seen.add(key)
    diff = str(raw.get("difficulty", "medium")).lower()
    # Shuffle so the correct answer is not always in the LLM's favourite slot.
    correct = opts[ai]
    random.shuffle(opts)
    ai = opts.index(correct)
    return {
        "id": str(uuid.uuid4()),
        "stem": stem,
        "options": [{"key": KEYS[i], "text": o} for i, o in enumerate(opts)],
        "answer": KEYS[ai],
        "explanation": expl,
        "difficulty": diff if diff in ("easy", "medium", "hard") else "medium",
        "tags": [str(t).strip()[:40] for t in (raw.get("tags") or []) if str(t).strip()][:3],
        "status": "draft",
        "created_at": datetime.utcnow().isoformat(timespec="seconds"),
    }, "ok"


# ---------------------------------------------------------------------------
# store
# ---------------------------------------------------------------------------

def load_store(system, subtopic):
    d = load_json(store_path(system, subtopic), {})
    d.setdefault("system", system)
    d.setdefault("subtopic", subtopic)
    d.setdefault("questions", [])
    return d


def write_store(d):
    d["updated_at"] = datetime.utcnow().isoformat(timespec="seconds")
    path = store_path(d["system"], d["subtopic"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    save_json_atomic(path, d)


def process(src, args, ledger):
    digest = sha256_text(src["text"])
    lkey = f"{src['kind']}:{src['ref']}"
    prev = ledger.get(lkey) or {}
    if prev.get("sha256") == digest and not args.force:
        log(args, "unchanged, skip:", lkey)
        return 0
    chunks = chunk_text(src["text"], chunk_size=CHUNK_MCQ, overlap=400)
    per_chunk = max(2, -(-args.per_source // len(chunks)))
    print(f"[{src['kind']}] {src['system']} / {src['subtopic']} :: {src['title'][:70]}  "
          f"({len(chunks)} chunk{'s' if len(chunks) > 1 else ''}, ~{per_chunk}/chunk)")
    if args.dry_run:
        return 0

    store = load_store(src["system"], src["subtopic"])
    # Replace this source's previous questions (re-generation on change / --force).
    old_ids = set(prev.get("ids") or [])
    store["questions"] = [q for q in store["questions"] if q.get("id") not in old_ids]
    seen = {norm_stem(q.get("stem", "")) for q in store["questions"]}

    made = []
    for i, chunk in enumerate(chunks, 1):
        user = (f"Write {per_chunk} questions.\nTOPIC: {src['system']} > {src['subtopic']} > {src['title']}\n\n"
                f"SOURCE ({src['kind']}, part {i}/{len(chunks)}):\n{chunk}")
        try:
            res = call_llm(args, user)
        except Exception as e:  # network / quota / parse — keep going with other sources
            print(f"   LLM error: {e}")
            continue
        items = res.get("questions") if isinstance(res, dict) else res
        for raw in items or []:
            if not isinstance(raw, dict):
                continue
            q, why = validate(raw, seen)
            if not q:
                log(args, "rejected:", why, "|", str(raw.get("stem", ""))[:70])
                continue
            q["source"] = {"kind": src["kind"], "ref": src["ref"], "title": src["title"]}
            made.append(q)
    made = made[: args.per_source]
    if not made:
        print("   no valid questions")
        return 0
    store["questions"].extend(made)
    write_store(store)
    ledger[lkey] = {"sha256": digest, "ids": [q["id"] for q in made],
                    "store": os.path.relpath(store_path(src["system"], src["subtopic"]), PROJECT_DIR),
                    "updated_at": datetime.utcnow().isoformat(timespec="seconds")}
    save_json_atomic(MCQ_LEDGER_FILE, ledger)
    print(f"   +{len(made)} questions")
    return len(made)


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def cmd_generate(args):
    ledger = load_json(MCQ_LEDGER_FILE, {})
    srcs = collect(args)
    if not args.force:
        srcs = [s for s in srcs if (ledger.get(f"{s['kind']}:{s['ref']}") or {}).get("sha256") != sha256_text(s["text"])]
    if args.max:
        srcs = srcs[: args.max]
    print(f"{len(srcs)} source(s) to process -> {MCQ_DIR}" + ("  [dry run]" if args.dry_run else ""))
    total = 0
    for s in srcs:
        total += process(s, args, ledger)
    print(f"Done. {total} new questions.")


def cmd_status(args):
    ledger = load_json(MCQ_LEDGER_FILE, {})
    srcs = collect(args)
    pending = [s for s in srcs if (ledger.get(f"{s['kind']}:{s['ref']}") or {}).get("sha256") != sha256_text(s["text"])]
    counts, total = {}, 0
    if os.path.isdir(MCQ_DIR):
        for root, _, files in os.walk(MCQ_DIR):
            for fn in files:
                if fn.endswith(".json"):
                    d = load_json(os.path.join(root, fn), {})
                    n = len(d.get("questions") or [])
                    counts[d.get("system", "?")] = counts.get(d.get("system", "?"), 0) + n
                    total += n
    print(f"MCQ store: {MCQ_DIR}")
    print(f"  questions: {total}")
    for k in sorted(counts):
        print(f"    {k:<28} {counts[k]}")
    print(f"  sources: {len(srcs)} total, {len(pending)} new/changed")


def main():
    p = argparse.ArgumentParser(description="Generate MCQs from theory notes and guidelines.")
    p.add_argument("command", nargs="?", default="generate", choices=["generate", "status"])
    p.add_argument("--source", choices=["theory", "guidelines", "all"], default="all")
    p.add_argument("--spec", help="Only this specialty/system (e.g. Pulmonology)")
    p.add_argument("--file", help="Only one source (theory rel path or guideline file name)")
    p.add_argument("--per-source", type=int, default=8, help="Questions per source (default 8)")
    p.add_argument("--max", type=int, default=0, help="Process at most N sources (0 = unlimited)")
    p.add_argument("--force", action="store_true", help="Regenerate even if unchanged")
    p.add_argument("--dry-run", action="store_true", help="Preview only: no API calls, no writes")
    p.add_argument("--verbose", action="store_true")
    prov = p.add_mutually_exclusive_group()
    prov.add_argument("--llm", choices=["openrouter", "gemini"], default="openrouter")
    prov.add_argument("--gemini", action="store_true", help="Same as --llm gemini")
    p.add_argument("--api-key", help="Direct OpenAI-compatible API key")
    p.add_argument("--model", help="Model name override")
    p.add_argument("--base-url", help="Endpoint override (default: OpenRouter)")
    args = p.parse_args()
    if args.gemini:
        args.llm = "gemini"
    args.per_source = max(1, args.per_source)
    (cmd_status if args.command == "status" else cmd_generate)(args)


if __name__ == "__main__":
    sys.exit(main())
