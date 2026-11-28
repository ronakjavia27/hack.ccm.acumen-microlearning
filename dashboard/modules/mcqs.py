"""MCQs module — store browser + user-report triage for the console.

MCQs are auto-published (mcq_generator.py writes status "published"). Portal
users can report a question; reports live in the shared KV store
(`mcqreport:{qid}:{user-hash}`) so the console sees reports made on production.

Console actions: list (reported first), edit text, set status
(published | rejected), dismiss/resolve reports. Status/edits change the JSON
store under output_files/mcqs/ and must be pushed to take effect on prod.
Like accounts, this module does not use ModuleSpec: it has its own endpoints.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from acumen_core.kv import kv_get, kv_scan, kv_set

from . import ItemNotFound
from ..storage import REPO_ROOT, audit, read_json, write_json_atomic

MCQ_DIR = os.getenv("MCQ_DIR", str(REPO_ROOT / "output_files" / "mcqs"))
REPORT_PREFIX = "mcqreport:"
EDITABLE = ("stem", "explanation", "answer", "difficulty", "status")
STATUSES = ("published", "draft", "approved", "rejected")


def _files() -> List[str]:
    out = []
    for root, _, names in os.walk(MCQ_DIR):
        out += [os.path.join(root, n) for n in sorted(names) if n.endswith(".json")]
    return out


def _rel(path: str) -> str:
    return os.path.relpath(path, REPO_ROOT).replace("\\", "/")


def list_reports(status: str = "open") -> List[Dict[str, Any]]:
    keys = kv_scan(REPORT_PREFIX + "*") or []
    rows = [r for r in (kv_get(k) for k in keys) if isinstance(r, dict)]
    if status:
        rows = [r for r in rows if r.get("status", "open") == status]
    rows.sort(key=lambda r: r.get("at", ""), reverse=True)
    return rows


def list_items(filters: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    f = filters or {}
    open_reports: Dict[str, List[Dict[str, Any]]] = {}
    for r in list_reports("open"):
        open_reports.setdefault(r.get("qid", ""), []).append(r)
    kw = (f.get("q") or "").lower().strip()
    rows = []
    for path in _files():
        d = read_json(path, default={}) or {}
        for q in d.get("questions") or []:
            qid = q.get("id")
            if not qid:
                continue
            reps = open_reports.get(qid, [])
            item = {
                "id": qid, "system": d.get("system", ""), "subtopic": d.get("subtopic", ""),
                "stem": q.get("stem", ""), "difficulty": q.get("difficulty", ""),
                "status": q.get("status", "published"),
                "source": (q.get("source") or {}).get("title") or (q.get("source") or {}).get("ref", ""),
                "reports": len(reps),
                "report_reasons": sorted({r.get("reason", "") for r in reps if r.get("reason")}),
            }
            if f.get("system") and item["system"] != f["system"]:
                continue
            if f.get("reported") and not reps:
                continue
            if kw and kw not in (item["stem"] + item["subtopic"] + item["source"]).lower():
                continue
            rows.append(item)
    rows.sort(key=lambda r: (-r["reports"], r["system"], r["subtopic"]))
    return rows


def _locate(qid: str):
    for path in _files():
        d = read_json(path, default={}) or {}
        for i, q in enumerate(d.get("questions") or []):
            if q.get("id") == qid:
                return path, d, i
    raise ItemNotFound(f"mcq {qid}")


def get_item(qid: str) -> Dict[str, Any]:
    path, d, i = _locate(qid)
    q = dict(d["questions"][i])
    q.update(system=d.get("system", ""), subtopic=d.get("subtopic", ""))
    q["reports"] = [r for r in list_reports("open") if r.get("qid") == qid]
    return q


def update_item(qid: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    path, d, i = _locate(qid)
    q = d["questions"][i]
    changed = []
    for k, v in fields.items():
        if k not in EDITABLE:
            continue
        if k == "status" and v not in STATUSES:
            raise ValueError(f"invalid status {v!r}")
        if k == "answer" and v not in [o.get("key") for o in q.get("options", [])]:
            raise ValueError("answer must match an option key")
        if q.get(k) != v:
            q[k] = v
            changed.append(k)
    if changed:
        write_json_atomic(path, d)
    audit("mcqs", qid, "update", {k: fields[k] for k in changed})
    return {"id": qid, "updated": bool(changed), "affected_paths": [_rel(path)]}


def resolve_reports(qid: str, note: str = "") -> Dict[str, Any]:
    n = 0
    for k in kv_scan(f"{REPORT_PREFIX}{qid}:*") or []:
        r = kv_get(k)
        if isinstance(r, dict) and r.get("status", "open") == "open":
            r.update(status="resolved", resolved_note=note[:300])
            kv_set(k, r)
            n += 1
    audit("mcqs", qid, "resolve_reports", note=f"{n} reports. {note[:100]}")
    return {"id": qid, "resolved": n}

