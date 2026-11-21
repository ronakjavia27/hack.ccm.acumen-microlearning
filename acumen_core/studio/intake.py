"""Intake: uploaded files / pasted text → individual questions → queued items.

Accepted layouts (auto-detected, mixable within a file):
  1. Numbered lists     "1. Discuss ARDS (10 marks)"  "Q3) Short note on ..."  "Q.4 ..."
  2. Bullets            "- Define septic shock"
  3. Blank-line separated paragraphs (one question per paragraph)
  4. MCQs               a question line followed by 4–5 options "a) .." / "(B) .." and optional "Ans: c"
  5. CSV                header with `question` (+ optional marks, type, system, subtopic, source,
                        option_a..option_e, answer)
Sub-parts like "a) definition b) management" with fewer than 4 parts stay inside the question.
"""
from __future__ import annotations

import csv
import io
import os
import re
from typing import Dict, List, Optional, Tuple

from acumen_core import config
from acumen_core.tracking import load_json_safe, save_json_atomic

from . import items as store

_NUM = re.compile(r"^\s*(?:Q(?:uestion)?\.?\s*)?(\d{1,3})\s*[\.\):\-]\s+(.*)$", re.I)
_BUL = re.compile(r"^\s*[-*•]\s+(.*)$")
_OPT = re.compile(r"^\s*\(?([a-eA-E])[\)\.:]\s+(.+)$")
_ANS = re.compile(r"^\s*(?:ans(?:wer)?|key|correct)\s*[:\-.]?\s*\(?([a-eA-E](?:\s*[,&]\s*[a-eA-E])*)\)?\s*$", re.I)
_MARKS = re.compile(r"\(\s*(\d{1,2})\s*(?:marks?|m)\s*\)|\[\s*(\d{1,2})\s*\]|\b(\d{1,2})\s*marks?\b", re.I)
_VIVA = re.compile(r"\bviva\b", re.I)
NEAR_DUP_JACCARD = 0.85


def detect_marks(q: str) -> Optional[int]:
    m = _MARKS.search(q)
    if not m:
        return None
    return int(next(g for g in m.groups() if g))


def detect_qtype(q: str, marks: Optional[int], options) -> str:
    if options:
        return "mcq"
    if _VIVA.search(q):
        return "viva"
    if marks is None:
        return "short"
    if marks >= 10:
        return "long"
    if marks >= 5:
        return "short"
    return "very_short"


def clean_question(q: str) -> str:
    q = _MARKS.sub("", q)
    return re.sub(r"\s+", " ", q).strip(" -–:\t")


def _flush(buf: List[str], out: List[dict]):
    if not buf:
        return
    head, rest = buf[0], buf[1:]
    opts, key, extra = [], None, []
    for line in rest:
        mo, ma = _OPT.match(line), _ANS.match(line)
        if ma:
            key = [ord(c.lower()) - 97 for c in re.findall(r"[a-eA-E]", ma.group(1))]
        elif mo:
            opts.append(mo.group(2).strip())
        else:
            extra.append(line.strip())
    is_mcq = 4 <= len(opts) <= 5 and all(len(o) <= 160 for o in opts)
    text = " ".join([head.strip()] + extra)
    if not is_mcq and opts:  # sub-parts → keep in the stem
        text += " " + " ".join(f"({chr(97 + i)}) {o}" for i, o in enumerate(opts))
    out.append({"raw": text, "options": opts if is_mcq else None,
                "given_key": key if is_mcq and key else None})
    buf.clear()


def split_text(text: str) -> List[dict]:
    """Return [{raw, options, given_key}] from free text."""
    lines = (text or "").replace("\r\n", "\n").split("\n")
    structured = sum(bool(_NUM.match(l) or _BUL.match(l)) for l in lines)
    out: List[dict] = []
    buf: List[str] = []
    for line in lines:
        if not line.strip():
            if not structured:
                _flush(buf, out)
            continue
        mn, mb = _NUM.match(line), _BUL.match(line)
        starter = (mn.group(2) if mn else None) or (mb.group(1) if mb and not _OPT.match(line) else None)
        if structured and starter is not None:
            _flush(buf, out)
            buf.append(starter)
        elif buf or not structured:
            buf.append(line.strip())
        # text before the first numbered item (headers like "Paper II, 2023") is ignored
    _flush(buf, out)
    return [q for q in out if len(clean_question(q["raw"])) >= 8]


def split_csv(text: str) -> List[dict]:
    rows = list(csv.DictReader(io.StringIO(text)))
    out = []
    for r in rows:
        r = {str(k).strip().lower(): (v or "").strip() for k, v in r.items() if k}
        q = r.get("question") or r.get("q") or ""
        if not q:
            continue
        opts = [r[k] for k in ("option_a", "option_b", "option_c", "option_d", "option_e") if r.get(k)]
        key = None
        if r.get("answer"):
            key = [ord(c.lower()) - 97 for c in re.findall(r"[a-eA-E]", r["answer"])] or None
        out.append({"raw": q, "options": opts or None, "given_key": key if opts else None,
                    "marks": int(r["marks"]) if r.get("marks", "").isdigit() else None,
                    "qtype": r.get("type") or None, "system": r.get("system", ""),
                    "subtopic": r.get("subtopic", ""), "label": r.get("source", "")})
    return out


def read_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".pdf", ".docx", ".html", ".htm"):
        from acumen_core.flashcards import parse_source_file
        _title, text = parse_source_file(path)   # -> (title, text)
        return text or ""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def subject_from_path(rel: str) -> Optional[str]:
    top = rel.replace("\\", "/").split("/")[0].strip().lower()
    return config.STUDIO_SUBJECT_FOLDERS.get(top)


def _tokens(s: str) -> set:
    return set(store.normalize_question(s).split())


def find_duplicate(subject: str, question: str, existing: List[dict]) -> Optional[dict]:
    iid = store.make_id(subject, question)
    toks = _tokens(question)
    for it in existing:
        if it["subject"] != subject:
            continue
        if it["id"] == iid:
            return it
        other = _tokens(it["question"])
        if toks and other and len(toks & other) / len(toks | other) >= NEAR_DUP_JACCARD:
            return it
    return None


def ingest_text(text: str, subject: str, source_file: str, label: str = "", is_csv: bool = False,
                dry_run: bool = False) -> Dict[str, List[str]]:
    """Split text into questions and create/merge items. Returns {"new": ids, "merged": ids}."""
    if subject not in set(config.STUDIO_SUBJECT_FOLDERS.values()):
        raise ValueError(f"unknown subject {subject}")
    parsed = split_csv(text) if is_csv else split_text(text)
    existing = store.all_items(subject)
    res: Dict[str, List[str]] = {"new": [], "merged": []}
    for idx, p in enumerate(parsed, 1):
        q = clean_question(p["raw"])
        marks = p.get("marks") or detect_marks(p["raw"])
        qtype = p.get("qtype") or detect_qtype(p["raw"], marks, p.get("options"))
        source = {"file": source_file, "label": p.get("label") or label, "index": idx}
        dup = find_duplicate(subject, q, existing)
        if dup:
            if not any(s.get("file") == source_file and s.get("index") == idx for s in dup["sources"]):
                dup["sources"].append(source)
                store.log(dup, "duplicate_upload", note=f"{source_file}#{idx}")
                if not dry_run:
                    store.save(dup)
            res["merged"].append(dup["id"])
            continue
        it = store.new_item(subject, q, qtype, marks, source, options=p.get("options"),
                            given_key=p.get("given_key"), system=p.get("system", ""),
                            subtopic=p.get("subtopic", ""))
        existing.append(it)
        if not dry_run:
            store.save(it)
        res["new"].append(it["id"])
    return res


def ingest_folder(only_file: str = "", force: bool = False, dry_run: bool = False,
                  verbose: bool = False) -> Dict[str, List[str]]:
    """Walk studio_input/{Subject}/..., ingest new/changed files (sha256 ledger)."""
    from acumen_core.flashcards import file_sha256
    ledger = load_json_safe(config.STUDIO_LEDGER_FILE, default={}) or {}
    total: Dict[str, List[str]] = {"new": [], "merged": [], "skipped_files": []}
    if not os.path.isdir(config.STUDIO_INPUT_DIR):
        os.makedirs(config.STUDIO_INPUT_DIR, exist_ok=True)
    for root, dirs, files in os.walk(config.STUDIO_INPUT_DIR):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fn in sorted(files):
            if fn.startswith(".") or fn.lower() == "readme.md":
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, config.STUDIO_INPUT_DIR).replace(os.sep, "/")
            if only_file and rel != only_file.replace("\\", "/"):
                continue
            subject = subject_from_path(rel)
            if not subject:
                if verbose:
                    print(f"  [!] {rel}: put it under Medicine/, Microbiology/ or CCM/")
                continue
            sha = file_sha256(path)
            if not force and ledger.get(rel, {}).get("sha256") == sha:
                total["skipped_files"].append(rel)
                continue
            text = read_file(path)
            label = os.path.splitext(fn)[0]
            r = ingest_text(text, subject, rel, label=label, is_csv=fn.lower().endswith(".csv"), dry_run=dry_run)
            if verbose:
                print(f"  {rel}: {len(r['new'])} new, {len(r['merged'])} already known")
            total["new"] += r["new"]
            total["merged"] += r["merged"]
            if not dry_run:
                ledger[rel] = {"sha256": sha, "subject": subject, "items": r["new"] + r["merged"],
                               "ingested_at": store.now()}
    if not dry_run:
        os.makedirs(os.path.dirname(config.STUDIO_LEDGER_FILE), exist_ok=True)
        save_json_atomic(config.STUDIO_LEDGER_FILE, ledger)
    return total
