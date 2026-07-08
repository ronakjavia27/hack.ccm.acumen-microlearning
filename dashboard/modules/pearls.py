"""Pearls content module.

`pearls.json` is a single 1,991-entry flat array on disk. The dashboard edits
items in place by id. Bulk-status edits write the whole file.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import ModuleSpec, ItemNotFound
from ..storage import (
    REPO_ROOT,
    read_json,
    write_json_atomic,
    audit,
)

PEARLS_PATH = REPO_ROOT / "pearls.json"

EDITABLE_FIELDS = [
    "pearl", "system", "type", "subtopic", "remarks", "topic", "visibility",
]


def _load() -> List[Dict[str, Any]]:
    data = read_json(PEARLS_PATH, default=[])
    return data if isinstance(data, list) else []


def _save(rows: List[Dict[str, Any]]) -> None:
    write_json_atomic(PEARLS_PATH, rows)


def _row_by_id(item_id: str) -> Optional[Dict[str, Any]]:
    rid = str(item_id)
    for r in _load():
        if str(r.get("id")) == rid:
            return r
    return None


def list_items(filters: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    rows = _load()
    f = filters or {}
    kw = f.get("q", "").lower().strip()
    out = []
    for r in rows:
        item = {
            "id": str(r.get("id")),
            "timestamp": r.get("timestamp", ""),
            "source_paper": r.get("source_paper", ""),
            "doi": r.get("doi", ""),
            "author": r.get("author", ""),
            "system": r.get("system", ""),
            "type": (r.get("type") or "").title(),
            "raw_type": r.get("type", ""),
            "pearl": r.get("pearl", ""),
            "remarks": r.get("remarks", ""),
            "file_name": r.get("file_name", ""),
            "topic": r.get("topic", ""),
            "subtopic": r.get("subtopic", ""),
        }
        if f.get("system") and item["system"] != f["system"]:
            continue
        if f.get("type") and item["type"] != f["type"]:
            continue
        if kw:
            hay = " ".join([
                str(item.get("pearl", "")), str(item.get("doi", "")),
                str(item.get("topic", "")), str(item.get("subtopic", "")),
                str(item.get("id", "")), str(item.get("source_paper", "")),
            ]).lower()
            if kw not in hay:
                continue
        out.append(item)
    return out


def get_item(item_id: str) -> Dict[str, Any]:
    r = _row_by_id(item_id)
    if r is None:
        raise ItemNotFound(f"pearl {item_id}")
    return {
        "id": str(r.get("id")),
        "timestamp": r.get("timestamp", ""),
        "source_paper": r.get("source_paper", ""),
        "doi": r.get("doi", ""),
        "author": r.get("author", ""),
        "system": r.get("system", ""),
        "type": (r.get("type") or "").title(),
        "pearl": r.get("pearl", ""),
        "remarks": r.get("remarks", ""),
        "file_name": r.get("file_name", ""),
        "topic": r.get("topic", ""),
        "subtopic": r.get("subtopic", ""),
    }


def update_item(item_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    rows = _load()
    rid = str(item_id)
    target_idx = None
    for i, r in enumerate(rows):
        if str(r.get("id")) == rid:
            target_idx = i
            break
    if target_idx is None:
        raise ItemNotFound(f"pearl {item_id}")

    old = dict(rows[target_idx])
    new = dict(rows[target_idx])
    dirty = False
    for k, v in fields.items():
        if k not in EDITABLE_FIELDS:
            continue
        if str(new.get(k, "")) != str(v):
            new[k] = v
            dirty = True

    if dirty:
        rows[target_idx] = new
        _save(rows)

    audit("pearls", item_id, "update", fields,
          note=f"old_system={old.get('system')} new_system={new.get('system')}")

    return {
        "id": rid,
        "updated": dirty,
        "affected_paths": [str(PEARLS_PATH.relative_to(REPO_ROOT))],
        "system_changed": str(old.get("system", "")) != str(new.get("system", "")),
        "subtopic_changed": str(old.get("subtopic", "")) != str(new.get("subtopic", "")),
        "old": {"system": old.get("system"), "subtopic": old.get("subtopic")},
        "new": {"system": new.get("system"), "subtopic": new.get("subtopic")},
    }


def delete_item(item_id: str) -> Dict[str, Any]:
    rows = _load()
    rid = str(item_id)
    target_idx = None
    target = None
    for i, r in enumerate(rows):
        if str(r.get("id")) == rid:
            target_idx = i
            target = dict(r)
            break
    if target_idx is None:
        raise ItemNotFound(f"pearl {item_id}")

    removed = rows.pop(target_idx)
    _save(rows)

    audit("pearls", item_id, "delete",
          note=f"file={removed.get('file_name','')}")
    return {
        "id": rid,
        "deleted": True,
        "affected_paths": [str(PEARLS_PATH.relative_to(REPO_ROOT))],
    }


def bulk_delete(ids: List[str]) -> Dict[str, Any]:
    rows = _load()
    id_set = {str(i) for i in ids}
    before = len(rows)
    rows = [r for r in rows if str(r.get("id")) not in id_set]
    deleted = before - len(rows)
    if deleted:
        _save(rows)
    audit("pearls", ",".join(ids), "bulk_delete", note=f"deleted={deleted}")
    return {"deleted": deleted,
            "affected_paths": [str(PEARLS_PATH.relative_to(REPO_ROOT))]}


def bulk_set_status(ids: List[str], status: str) -> Dict[str, Any]:
    """Pearls have no native `show_on_web` flag yet. We add an inline
    `visibility` field on each pearl so the dashboard can hide/show without
    a schema change. Existing rows without it default to `visible`."""
    rows = _load()
    id_set = {str(i) for i in ids}
    touched = 0
    for r in rows:
        if str(r.get("id")) in id_set:
            r["visibility"] = status
            touched += 1
    if touched:
        _save(rows)
        audit("pearls", ",".join(ids), "bulk_status", note=status)
    return {"touched": touched, "status": status,
            "affected_paths": [str(PEARLS_PATH.relative_to(REPO_ROOT))]}


def reclassify_by_file_name(file_name: str, new_system: str, new_subtopic: str) -> Dict[str, Any]:
    """Used by the cascade — bulk re-classify all pearls that originated from
    `file_name` to a new system/subtopic. Returns counts.
    Does NOT trigger git push on its own; the cascade orchestrator runs it."""
    rows = _load()
    touched = 0
    for r in rows:
        if r.get("file_name") == file_name:
            r["system"] = new_system
            if new_subtopic:
                r["subtopic"] = new_subtopic
            touched += 1
    if touched:
        _save(rows)
        audit("pearls", file_name, "cascade", note=f"{touched} pearls → {new_system}/{new_subtopic}")
    return {
        "touched": touched,
        "file_name": file_name,
        "new": {"system": new_system, "subtopic": new_subtopic},
        "affected_paths": [str(PEARLS_PATH.relative_to(REPO_ROOT))],
    }


SPEC = ModuleSpec(
    name="Pearls",
    kind="pearls",
    id_field="id",
    list_fn=list_items,
    get_fn=get_item,
    update_fn=update_item,
    delete_fn=delete_item,
    bulk_delete_fn=bulk_delete,
    bulk_status_fn=bulk_set_status,
    has_visibility_flag=True,                   # uses inline `visibility` field
    visible_value_field="visibility",
    extra_endpoints={
        "bulk_status": ("POST", "/pearls/bulk-status", bulk_set_status),
    },
)
