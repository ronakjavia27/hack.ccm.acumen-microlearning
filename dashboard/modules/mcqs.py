"""MCQ review module.

Store: output_files/mcqs/{System}/{Subtopic}.json (written by mcq_generator.py)
    {"system", "subtopic", "updated_at", "questions": [{id, stem, options[{key,text}],
      answer, explanation, difficulty, tags, source{kind,ref,title}, status, created_at}]}

Item id = the question uuid. Listing flattens every subtopic file. Status flows
draft -> approved | rejected (the learner portal hides `rejected`).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import ModuleSpec, ItemNotFound
from ..storage import REPO_ROOT, read_json, write_json_atomic, audit

MCQ_DIR = Path(os.getenv("MCQ_DIR") or (REPO_ROOT / "output_files" / "mcqs"))
VALID_STATUS = ("draft", "approved", "rejected")
VALID_DIFFICULTY = ("easy", "medium", "hard")
KEYS = "ABCDE"
BANNED = re.compile(r"\b(all|none) of the above\b", re.I)


def _files() -> List[Path]:
    return sorted(MCQ_DIR.rglob("*.json")) if MCQ_DIR.is_dir() else []


def _load_file(path: Path) -> Dict[str, Any]:
    d = read_json(path, default={}) or {}
    d.setdefault("questions", [])
    return d


def _walk() -> List[Tuple[Path, Dict[str, Any], Dict[str, Any]]]:
    """(file path, file data, question) for every question."""
    out = []
    for p in _files():
        d = _load_file(p)
        for q in d["questions"]:
            if isinstance(q, dict) and q.get("id"):
                out.append((p, d, q))
    return out


def _find(item_id: str):
    for p, d, q in _walk():
        if q["id"] == item_id:
            return p, d, q
    raise ItemNotFound(f"mcqs/{item_id}")


def _view(d: Dict[str, Any], q: Dict[str, Any]) -> Dict[str, Any]:
    src = q.get("source") or {}
    return {
        "id": q["id"],
        "stem": q.get("stem", ""),
        "options": q.get("options") or [],
        "answer": q.get("answer", ""),
        "explanation": q.get("explanation", ""),
        "difficulty": q.get("difficulty", "medium"),
        "tags": q.get("tags") or [],
        "status": q.get("status", "draft"),
        "system": d.get("system", ""),
        "subtopic": d.get("subtopic", ""),
        "source_kind": src.get("kind", ""),
        "source_ref": src.get("ref", ""),
        "source_title": src.get("title", ""),
        "created_at": q.get("created_at", ""),
    }


def list_items(filters: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    f = filters or {}
    kw = (f.get("q") or "").lower().strip()
    out = []
    for _, d, q in _walk():
        v = _view(d, q)
        if f.get("system") and v["system"] != f["system"]:
            continue
        if f.get("status") and v["status"] != f["status"]:
            continue
        if f.get("type") and v["difficulty"] != f["type"]:  # generic `type` filter = difficulty
            continue
        if kw and kw not in " ".join([v["stem"], v["subtopic"], v["source_title"], " ".join(v["tags"])]).lower():
            continue
        out.append(v)
    order = {"draft": 0, "approved": 1, "rejected": 2}
    out.sort(key=lambda r: (order.get(r["status"], 3), r["system"], r["subtopic"], r["created_at"]))
    return out


def get_item(item_id: str) -> Dict[str, Any]:
    _, d, q = _find(item_id)
    return _view(d, q)


def _validate_edit(q: Dict[str, Any]) -> None:
    opts = q.get("options") or []
    if not 4 <= len(opts) <= 5:
        raise ValueError("need 4-5 options")
    texts = [str(o.get("text", "")).strip() for o in opts]
    if any(not t for t in texts) or len({t.lower() for t in texts}) != len(texts):
        raise ValueError("options must be non-empty and unique")
    if any(BANNED.search(t) for t in texts):
        raise ValueError("'all/none of the above' options are not allowed")
    if q.get("answer") not in [o["key"] for o in opts]:
        raise ValueError("answer must match an option key")
    if len(str(q.get("stem", "")).strip()) < 20:
        raise ValueError("stem too short")
    if len(str(q.get("explanation", "")).strip()) < 30:
        raise ValueError("explanation too short")


def _normalize_options(raw: Any) -> List[Dict[str, str]]:
    items = []
    for o in raw or []:
        text = o.get("text", "") if isinstance(o, dict) else str(o)
        items.append(str(text).strip())
    return [{"key": KEYS[i], "text": t} for i, t in enumerate(items[:5])]


def update_item(item_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    path, d, q = _find(item_id)
    before = dict(q)
    if "stem" in fields:
        q["stem"] = str(fields["stem"]).strip()
    if "options" in fields:
        q["options"] = _normalize_options(fields["options"])
    if "answer" in fields:
        q["answer"] = str(fields["answer"]).strip().upper()
    if "explanation" in fields:
        q["explanation"] = str(fields["explanation"]).strip()
    if "difficulty" in fields and fields["difficulty"] in VALID_DIFFICULTY:
        q["difficulty"] = fields["difficulty"]
    if "tags" in fields:
        tags = fields["tags"]
        if isinstance(tags, str):
            tags = [t for t in re.split(r"[,\n]", tags)]
        q["tags"] = [str(t).strip()[:40] for t in tags if str(t).strip()][:5]
    if "status" in fields:
        if fields["status"] not in VALID_STATUS:
            raise ValueError(f"status must be one of {VALID_STATUS}")
        q["status"] = fields["status"]
    content_touched = any(k in fields for k in ("stem", "options", "answer", "explanation"))
    if content_touched:
        _validate_edit(q)
    if q == before:
        return {"id": item_id, "updated": False, "affected_paths": []}
    q["edited_at"] = datetime.utcnow().isoformat(timespec="seconds")
    d["updated_at"] = q["edited_at"]
    write_json_atomic(path, d)
    audit("mcqs", item_id, "update", fields=fields)
    return {"id": item_id, "updated": True, "affected_paths": [_rel(path)]}


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def delete_item(item_id: str) -> Dict[str, Any]:
    path, d, q = _find(item_id)
    d["questions"] = [x for x in d["questions"] if x.get("id") != item_id]
    write_json_atomic(path, d)
    audit("mcqs", item_id, "delete")
    return {"deleted": True, "affected_paths": [_rel(path)]}


def bulk_set_status(ids: List[str], status: str) -> Dict[str, Any]:
    if status not in VALID_STATUS:
        raise ValueError(f"status must be one of {VALID_STATUS}")
    want, touched, paths = set(ids), 0, []
    for p in _files():
        d = _load_file(p)
        changed = False
        for q in d["questions"]:
            if q.get("id") in want and q.get("status") != status:
                q["status"] = status
                touched += 1
                changed = True
        if changed:
            d["updated_at"] = datetime.utcnow().isoformat(timespec="seconds")
            write_json_atomic(p, d)
            paths.append(_rel(p))
    audit("mcqs", ",".join(ids[:5]), "bulk_status", note=f"{status} x{touched}")
    return {"touched": touched, "status": status, "affected_paths": paths}


def bulk_delete(ids: List[str]) -> Dict[str, Any]:
    want, deleted, paths = set(ids), 0, []
    for p in _files():
        d = _load_file(p)
        keep = [q for q in d["questions"] if q.get("id") not in want]
        if len(keep) != len(d["questions"]):
            deleted += len(d["questions"]) - len(keep)
            d["questions"] = keep
            write_json_atomic(p, d)
            paths.append(_rel(p))
    audit("mcqs", "bulk", "bulk_delete", note=f"deleted={deleted}")
    return {"deleted": deleted, "affected_paths": paths}


def stats() -> Dict[str, Any]:
    by_status = {s: 0 for s in VALID_STATUS}
    by_system: Dict[str, Dict[str, int]] = {}
    for _, d, q in _walk():
        st = q.get("status", "draft")
        by_status[st] = by_status.get(st, 0) + 1
        sysd = by_system.setdefault(d.get("system", ""), {s: 0 for s in VALID_STATUS})
        sysd[st] = sysd.get(st, 0) + 1
    return {"total": sum(by_status.values()), "by_status": by_status, "by_system": by_system}


# ---------------------------------------------------------------------------
# Generation job (spawns mcq_generator.py; single-flight, polled by job id)
# ---------------------------------------------------------------------------
JOBS: Dict[str, Dict[str, Any]] = {}
_JOB_LOCK = threading.Lock()


def start_generate(opts: Dict[str, Any]) -> Dict[str, Any]:
    with _JOB_LOCK:
        if any(j["status"] == "running" for j in JOBS.values()):
            raise RuntimeError("an MCQ generation job is already running")
        cmd = [sys.executable, str(REPO_ROOT / "mcq_generator.py")]
        if opts.get("spec"):
            cmd += ["--spec", str(opts["spec"])]
        if opts.get("source") in ("theory", "guidelines", "all"):
            cmd += ["--source", opts["source"]]
        if opts.get("per_source"):
            cmd += ["--per-source", str(int(opts["per_source"]))]
        cmd += ["--max", str(int(opts.get("max") or 3))]
        if opts.get("gemini"):
            cmd.append("--gemini")
        job_id = uuid.uuid4().hex[:12]
        job = {"job_id": job_id, "status": "running", "cmd": " ".join(cmd[1:]),
               "started_at": time.time(), "finished_at": 0, "log": ""}
        JOBS[job_id] = job

    def run():
        try:
            r = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=1800)
            job["log"] = ((r.stdout or "") + (r.stderr or ""))[-4000:]
            job["status"] = "done" if r.returncode == 0 else "failed"
        except Exception as e:  # noqa: BLE001
            job["log"] = str(e)
            job["status"] = "failed"
        job["finished_at"] = time.time()
        audit("mcqs", job_id, "generate", note=job["status"])

    threading.Thread(target=run, daemon=True).start()
    return job


def job_status(job_id: str) -> Dict[str, Any]:
    if job_id not in JOBS:
        raise ItemNotFound(job_id)
    return JOBS[job_id]


SPEC = ModuleSpec(
    name="MCQs",
    kind="mcqs",
    id_field="id",
    list_fn=list_items,
    get_fn=get_item,
    update_fn=update_item,
    delete_fn=delete_item,
    bulk_delete_fn=bulk_delete,
    bulk_status_fn=bulk_set_status,
    has_visibility_flag=False,
)
