"""Studio item store: one JSON file per uploaded question.

studio/items/{subject}/{item_id}.json
{
  "id", "subject", "system", "subtopic", "question", "qtype", "marks",
  "options": [...] | null, "given_key": [..] | null,      # when the upload itself was an MCQ
  "sources": [{"file", "label", "index"}],                # every upload it appeared in
  "status": queued|generating|generated|revision_requested|approved|published|rejected|error,
  "triage": green|amber|red|null,
  "versions": [{"v", "at", "origin": "ai"|"human", "models", "package", "verification", "lint",
                "triage", "reasons", "context", "hash"}],
  "current": <v>,
  "review": {"by", "at", "version", "hash", "parts": {"answer": bool, "flashcards": [i..], "mcqs": [i..]}, "note"},
  "published": {"version", "at", "theory_rel", "flashcard_ids": [..], "question_ids": [..]} | null,
  "revision_note": str,
  "history": [{"at", "event", "by", "note"}]
}
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from acumen_core import config
from acumen_core.tracking import save_json_atomic

STATUSES = ("queued", "generating", "generated", "revision_requested", "approved", "published",
            "rejected", "error")

# from-status -> allowed to-statuses
# "queued" is reachable from most states because re-saving a note with new content re-queues it
# (published content stays live until the new version is approved and published).
TRANSITIONS = {
    "queued": {"generating", "error", "rejected"},
    "generating": {"generated", "error", "queued", "revision_requested"},   # back to queued/revision_requested = call cap hit
    "generated": {"approved", "rejected", "revision_requested", "generating", "generated", "queued"},
    "revision_requested": {"generating", "generated", "rejected", "error", "queued"},
    "approved": {"published", "generated", "rejected", "revision_requested", "generating", "queued"},
    "published": {"generated", "rejected", "revision_requested", "generating", "published", "approved", "queued"},
    "rejected": {"queued"},
    "error": {"queued", "generating"},
}


class TransitionError(ValueError):
    pass


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def normalize_question(text: str) -> str:
    t = (text or "").lower()
    t = re.sub(r"\(\s*\d+\s*(marks?|m)\s*\)|\[\s*\d+\s*\]", " ", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def make_note_id(subject: str, filename: str) -> str:
    """Notes are identified by subject + file name, so re-saving an edited note updates the same item."""
    stem = os.path.splitext(os.path.basename(filename or ""))[0]
    stem = re.sub(r"\s*\(\d+\)$", "", stem)            # "ARDS (1).docx" from a re-download = same note
    key = re.sub(r"[^a-z0-9]+", " ", stem.lower()).strip()
    return f"{subject}-n{hashlib.sha1(key.encode('utf-8')).hexdigest()[:10]}"


def make_id(subject: str, question: str) -> str:
    h = hashlib.sha1(normalize_question(question).encode("utf-8")).hexdigest()[:10]
    return f"{subject}-{h}"


def content_hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def _path(subject: str, item_id: str) -> str:
    return os.path.join(config.STUDIO_ITEMS_DIR, subject, f"{item_id}.json")


def load(item_id: str) -> Optional[dict]:
    subject = item_id.split("-", 1)[0]
    p = _path(subject, item_id)
    if not os.path.isfile(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def save(item: dict) -> dict:
    p = _path(item["subject"], item["id"])
    os.makedirs(os.path.dirname(p), exist_ok=True)
    item["updated_at"] = now()
    save_json_atomic(p, item)
    return item


def all_items(subject: str = "") -> List[dict]:
    pattern = os.path.join(config.STUDIO_ITEMS_DIR, subject or "*", "*.json")
    out = []
    for p in sorted(glob.glob(pattern)):
        try:
            with open(p, "r", encoding="utf-8") as f:
                out.append(json.load(f))
        except (OSError, json.JSONDecodeError):
            continue
    return out


def new_item(subject: str, question: str, qtype: str, marks: Optional[int], source: dict,
             options: Optional[List[str]] = None, given_key: Optional[List[int]] = None,
             system: str = "", subtopic: str = "") -> dict:
    return {
        "id": make_id(subject, question), "subject": subject, "system": system, "subtopic": subtopic,
        "question": question.strip(), "qtype": qtype, "marks": marks,
        "options": options, "given_key": given_key, "sources": [source],
        "status": "queued", "triage": None, "versions": [], "current": None,
        "review": None, "published": None, "revision_note": "",
        "created_at": now(), "updated_at": now(),
        "history": [{"at": now(), "event": "ingested", "by": "studio", "note": source.get("file", "")}],
    }


def current_version(item: dict) -> Optional[dict]:
    if not item.get("versions"):
        return None
    cur = item.get("current")
    for v in item["versions"]:
        if v["v"] == cur:
            return v
    return item["versions"][-1]


def log(item: dict, event: str, by: str = "studio", note: str = ""):
    item.setdefault("history", []).append({"at": now(), "event": event, "by": by, "note": note[:500]})


def transition(item: dict, to: str, by: str = "studio", note: str = "") -> dict:
    frm = item.get("status", "queued")
    if to not in STATUSES:
        raise TransitionError(f"unknown status {to}")
    if to != frm and to not in TRANSITIONS.get(frm, set()):
        raise TransitionError(f"cannot go {frm} → {to}")
    item["status"] = to
    log(item, f"status:{to}", by, note)
    return item


def add_version(item: dict, version: dict) -> dict:
    v = (max((x["v"] for x in item["versions"]), default=0)) + 1
    version = {**version, "v": v, "at": now()}
    version["hash"] = content_hash(version.get("package"))
    item["versions"].append(version)
    item["current"] = v
    item["triage"] = version.get("triage")
    # An approval is bound to a version; a new version invalidates it.
    if item.get("review") and item["review"].get("version") != v:
        item["review"] = {**item["review"], "stale": True}
    return version


def counts(items: Iterable[dict]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for it in items:
        out[it["status"]] = out.get(it["status"], 0) + 1
        if it["status"] == "generated" and it.get("triage"):
            k = f"generated:{it['triage']}"
            out[k] = out.get(k, 0) + 1
    return out
