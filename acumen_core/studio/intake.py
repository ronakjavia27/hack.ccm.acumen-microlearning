"""Intake: inbox files / pasted text → queued Studio items.

Two kinds of input (routing in ingest_folder):
  NOTES      {Subject}/<anything>.md|docx|txt|pdf|html  → ONE item per file (kind="note"); the note becomes
             the theory section and Q&A, flashcards and MCQs are derived from it.
  QUESTIONS  {Subject}/Questions/** and any .csv        → split into one item per question (below).

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
        if it["subject"] != subject or it.get("kind") == "note":
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


def docx_to_markdown(path: str) -> str:
    """docx → markdown keeping structure: headings, lists, bold/italic, tables (python-docx)."""
    from docx import Document
    doc = Document(path)
    out: List[str] = []

    def runs_md(par) -> str:
        parts = []
        for r in par.runs:
            t = r.text
            if not t:
                continue
            core, lead, trail = t.strip(), t[:len(t) - len(t.lstrip())], t[len(t.rstrip()):]
            if core and r.bold:
                core = f"**{core}**"
            elif core and r.italic:
                core = f"_{core}_"
            parts.append(lead + core + trail)
        return re.sub(r"\*\*\s*\*\*", "", "".join(parts)).strip()

    has_title = any((p.style is not None and (p.style.name or "").lower() == "title") for p in doc.paragraphs)
    body = doc.element.body
    tables = {t._tbl: t for t in doc.tables}
    paras = {p._p: p for p in doc.paragraphs}
    for child in body.iterchildren():
        if child in paras:
            par = paras[child]
            text = runs_md(par)
            if not text:
                if out and out[-1] != "":
                    out.append("")
                continue
            style = (par.style.name if par.style is not None else "") or ""
            m = re.match(r"Heading\s*(\d)", style, re.I)
            if (style.lower() == "title" or m) and out and out[-1] != "":
                out.append("")
            if style.lower() == "title":
                out += [f"# {text.strip('*_ ')}", ""]
            elif m:
                level = int(m.group(1)) + (1 if has_title else 0)   # a Title takes '#', headings move down
                out += [f"{'#' * min(level, 6)} {text.strip('*_ ')}", ""]
            elif "list number" in style.lower():
                out.append(f"1. {text}")
            elif "list" in style.lower() or par._p.pPr is not None and par._p.pPr.numPr is not None:
                level = 0
                try:
                    level = int(par._p.pPr.numPr.ilvl.val)
                except Exception:
                    pass
                out.append(f"{'  ' * level}- {text}")
            else:
                if out and out[-1] and not out[-1].startswith(("-", "1.", "  -")):
                    out.append("")
                out.append(text)
        elif child in tables:
            rows = [[c.text.strip().replace("\n", " ").replace("|", "/") for c in row.cells] for row in tables[child].rows]
            if rows:
                out += ["", "| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])]
                out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
                out.append("")
    md = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"


def read_note(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return docx_to_markdown(path)
    return read_file(path)


def note_title(md: str, filename: str) -> str:
    m = re.search(r"^\s*#{1,3}\s+(.+?)\s*$", md or "", re.M)
    if m:
        return m.group(1).strip("*_ ")[:160]
    return re.sub(r"[_-]+", " ", os.path.splitext(os.path.basename(filename))[0]).strip()[:160]


def ingest_note(text: str, subject: str, source_file: str, label: str = "", dry_run: bool = False) -> Dict[str, List[str]]:
    """One note file → one item. Re-saving the same file name with new content re-queues it as a new version."""
    import hashlib
    if subject not in set(config.STUDIO_SUBJECT_FOLDERS.values()):
        raise ValueError(f"unknown subject {subject}")
    text = (text or "").strip()
    if len(text) < 40:
        raise ValueError(f"{source_file}: note is empty or too short")
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    iid = store.make_note_id(subject, source_file)
    source = {"file": source_file, "label": label, "index": 0, "sha": sha}
    existing = store.load(iid)
    if existing:
        if existing.get("note_sha") == sha:
            return {"new": [], "merged": [iid], "updated": []}
        existing.update(note_md=text, note_sha=sha, question=note_title(text, source_file))
        existing["sources"].append(source)
        store.transition(existing, "queued", "studio", f"note updated ({source_file})")
        if not dry_run:
            store.save(existing)
        return {"new": [], "merged": [], "updated": [iid]}
    it = store.new_item(subject, note_title(text, source_file), "note", None, source)
    it.update(id=iid, kind="note", note_md=text, note_sha=sha)
    if not dry_run:
        store.save(it)
    return {"new": [iid], "merged": [], "updated": []}


def _is_question_list(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    return rel.lower().endswith(".csv") or any(p.lower() == config.STUDIO_QUESTIONS_FOLDER.lower() for p in parts[1:-1])


def _move_processed(path: str, rel: str) -> str:
    """Move an ingested file to <inbox>/Processed/<rel> (adds a suffix if the name exists)."""
    dest = os.path.join(config.STUDIO_INPUT_DIR, config.STUDIO_PROCESSED_FOLDER, rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    base, ext = os.path.splitext(dest)
    n = 1
    while os.path.exists(dest):
        dest = f"{base} ({n}){ext}"
        n += 1
    os.replace(path, dest)
    return dest


def ingest_folder(only_file: str = "", force: bool = False, dry_run: bool = False,
                  verbose: bool = False, move: Optional[bool] = None, now: Optional[float] = None) -> Dict[str, List[str]]:
    """Walk the inbox, ingest settled new/changed files, move them to Processed/.

    Ledger (studio/ledger.json) is keyed by file sha256, so a file dropped again unchanged is skipped
    (and still tidied into Processed/).
    """
    import time
    from acumen_core.flashcards import file_sha256
    move = (os.environ.get("STUDIO_MOVE_PROCESSED", "1") != "0") if move is None else move
    now = now or time.time()
    ledger = load_json_safe(config.STUDIO_LEDGER_FILE, default={}) or {}
    total: Dict[str, list] = {"new": [], "merged": [], "updated": [], "skipped_files": [], "settling": [],
                              "errors": []}
    os.makedirs(config.STUDIO_INPUT_DIR, exist_ok=True)
    for root, dirs, files in os.walk(config.STUDIO_INPUT_DIR):
        rel_root = os.path.relpath(root, config.STUDIO_INPUT_DIR)
        dirs[:] = [d for d in dirs if not d.startswith(".")
                   and not (rel_root == "." and d.lower() == config.STUDIO_PROCESSED_FOLDER.lower())]
        for fn in sorted(files):
            if fn.startswith((".", "~$")) or fn.lower() in ("readme.md", "desktop.ini") or fn.endswith((".tmp", ".gdoc")):
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, config.STUDIO_INPUT_DIR).replace(os.sep, "/")
            if only_file and rel != only_file.replace("\\", "/"):
                continue
            subject = subject_from_path(rel)
            if not subject:
                if verbose:
                    print(f"  [!] {rel}: put it under CCM/, Medicine/ or Microbiology/")
                continue
            if now - os.path.getmtime(path) < config.STUDIO_SETTLE_SECONDS:
                total["settling"].append(rel)      # Drive may still be writing it — next pass
                continue
            sha = file_sha256(path)
            if not force and sha in ledger:
                total["skipped_files"].append(rel)
                if move and not dry_run:
                    _move_processed(path, rel)
                continue
            label = os.path.splitext(fn)[0]
            try:
                if _is_question_list(rel):
                    r = ingest_text(read_file(path), subject, rel, label=label, is_csv=fn.lower().endswith(".csv"),
                                    dry_run=dry_run)
                    r.setdefault("updated", [])
                else:
                    r = ingest_note(read_note(path), subject, rel, label=label, dry_run=dry_run)
            except Exception as e:
                total["errors"].append({"file": rel, "error": str(e)})
                if verbose:
                    print(f"  [X] {rel}: {e}")
                continue
            if verbose:
                kind = "questions" if _is_question_list(rel) else "note"
                print(f"  {rel} ({kind}): {len(r['new'])} new, {len(r['updated'])} updated, {len(r['merged'])} unchanged")
            for k in ("new", "merged", "updated"):
                total[k] += r[k]
            if not dry_run:
                ledger[sha] = {"file": rel, "subject": subject, "items": r["new"] + r["updated"] + r["merged"],
                               "ingested_at": store.now()}
                if move:
                    _move_processed(path, rel)
    if not dry_run:
        os.makedirs(os.path.dirname(config.STUDIO_LEDGER_FILE), exist_ok=True)
        save_json_atomic(config.STUDIO_LEDGER_FILE, ledger)
    return total
