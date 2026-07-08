"""Speciality / subtopic reclassification cascade.

When a summary's `system` or `subtopic` changes, all pearls sharing the same
`file_name` should be reclassified. This module provides:
  - `cascade_preview()` — returns count of affected pearls without committing
  - `cascade_apply()` — performs the reclassification after user confirm
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .modules import pearls as pearls_module
from .storage import REPO_ROOT, read_json, write_json_atomic, audit

PEARLS_PATH = REPO_ROOT / "pearls.json"


def _load_pearls() -> List[Dict[str, Any]]:
    data = read_json(PEARLS_PATH, default=[])
    return data if isinstance(data, list) else []


def _save_pearls(rows: List[Dict[str, Any]]) -> None:
    write_json_atomic(PEARLS_PATH, rows)


def cascade_preview(file_name: str, old: dict, new: dict) -> Dict[str, Any]:
    """Return preview info: how many pearls share this file_name, sample of them."""
    rows = _load_pearls()
    matched = [r for r in rows if r.get("file_name") == file_name]
    return {
        "file_name": file_name,
        "total_pearls": len(matched),
        "old": old,
        "new": new,
        "sample": [
            {"id": r.get("id"), "pearl": (r.get("pearl") or "")[:120],
             "current_system": r.get("system"), "current_subtopic": r.get("subtopic")}
            for r in matched[:5]
        ],
    }


def cascade_apply(file_name: str, new_system: str, new_subtopic: Optional[str] = None) -> Dict[str, Any]:
    """Apply reclassification to all pearls matching file_name.
    Returns counts of touched pearls."""
    rows = _load_pearls()
    touched = 0
    for r in rows:
        if r.get("file_name") == file_name:
            r["system"] = new_system
            if new_subtopic:
                r["subtopic"] = new_subtopic
            touched += 1
    if touched:
        _save_pearls(rows)
        audit("cascade", file_name, "apply",
              note=f"{touched} pearls reclassified → {new_system}/{new_subtopic or '(unchanged)'}")
    return {
        "file_name": file_name,
        "touched": touched,
        "new": {"system": new_system, "subtopic": new_subtopic},
        "affected_paths": [str(PEARLS_PATH.relative_to(REPO_ROOT))],
    }


def cascade_summary_update(
    summary_id: str,
    old_system: str,
    old_subtopic: str,
    new_system: str,
    new_subtopic: str,
    file_name: str,
    confirmed: bool = False,
) -> Dict[str, Any]:
    """Called from the summaries update endpoint when system/subtopic changed.

    If confirmed=False: return preview (cascade_preview result + merge instructions).
    If confirmed=True: apply cascade + mark changed paths for git push.

    Returns a result dict that the frontend can use to show a confirm modal."""
    if not confirmed:
        preview = cascade_preview(file_name,
                                   {"system": old_system, "subtopic": old_subtopic},
                                   {"system": new_system, "subtopic": new_subtopic})
        return {"need_confirm": True, **preview}
    return cascade_apply(file_name, new_system, new_subtopic or old_subtopic)
