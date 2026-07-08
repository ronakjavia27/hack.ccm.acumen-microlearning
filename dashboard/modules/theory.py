"""Theory content module — reads from validated theory directory.

# Scans the validated theory directory recursively for JSON
# files. Each file becomes a theory item. No ledger/index file — the filesystem
# is the source of truth.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from . import ModuleSpec, ItemNotFound
from ..storage import REPO_ROOT, read_json, write_json_atomic, audit

VALIDATED_DIR = Path("C:/RONAK/AI Projects/ACUMEN/THEORY/validated")


def _walk() -> List[Dict[str, Any]]:
    """Scan VALIDATED_DIR recursively for JSON files and return items."""
    items = []
    if not VALIDATED_DIR.is_dir():
        return items
    for f in sorted(VALIDATED_DIR.rglob("*.json")):
        try:
            data = read_json(f, default={})
        except Exception:
            continue
        if not isinstance(data, dict) or not data:
            continue
        rel = f.relative_to(VALIDATED_DIR)
        item_id = str(rel.with_suffix("")).replace("\\", "/").strip()
        items.append({
            "id": item_id,
            "title": data.get("title", ""),
            "specialty": data.get("specialty", rel.parent.name),
            "validation_status": data.get("validation", {}).get("status", "needs_review"),
            "subtopic_count": len(data.get("subtopics", [])),
            "sections_count": len(data.get("sections", {})),
            "_source": str(f),
            "_raw": data,
        })
    return items


def _find(rows: List[Dict[str, Any]], item_id: str) -> Optional[Dict[str, Any]]:
    for r in rows:
        if r["id"] == item_id:
            return r
    return None


def list_items(filters: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    rows = _walk()
    f = filters or {}
    kw = f.get("q", "").lower().strip()
    specialty = f.get("specialty", "")
    status = f.get("status", "")
    out = []
    for r in rows:
        if specialty and r.get("specialty", "") != specialty:
            continue
        if status and r.get("validation_status", "") != status:
            continue
        if kw:
            hay = " ".join([
                str(r.get("title", "")),
                str(r.get("id", "")),
                str(r.get("specialty", "")),
            ]).lower()
            if kw not in hay:
                continue
        # Strip _raw from list results for performance
        item = {k: v for k, v in r.items() if k != "_raw"}
        out.append(item)
    return out


def get_item(item_id: str) -> Dict[str, Any]:
    rows = _walk()
    r = _find(rows, item_id)
    if r is None:
        raise ItemNotFound(f"theory {item_id}")
    return r


def update_item(item_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    rows = _walk()
    r = _find(rows, item_id)
    if r is None:
        raise ItemNotFound(f"theory {item_id}")

    source = Path(r["_source"])
    old = dict(r["_raw"])

    # If client sends _raw, replace the full content
    if "_raw" in fields and isinstance(fields["_raw"], dict):
        new_content = dict(fields["_raw"])
        dirty = new_content != old
    else:
        # Otherwise merge individual fields
        new_content = dict(old)
        dirty = False
        for k, v in fields.items():
            if k in ("_raw", "_source"):
                continue
            if str(new_content.get(k, "")) != str(v):
                new_content[k] = v
                dirty = True

    if not dirty:
        return {"id": item_id, "updated": False, "affected_paths": []}

    write_json_atomic(source, new_content)
    audit("theory", item_id, "update", note=f"saved to {source.name}")
    return {
        "id": item_id,
        "updated": True,
        "affected_paths": [],
    }


def delete_item(item_id: str) -> Dict[str, Any]:
    rows = _walk()
    r = _find(rows, item_id)
    if r is None:
        raise ItemNotFound(f"theory {item_id}")
    source = Path(r["_source"])
    if source.exists():
        source.unlink()
    audit("theory", item_id, "delete", note=f"deleted {source}")
    return {"id": item_id, "deleted": True, "affected_paths": []}


def bulk_set_status(ids: List[str], status: str) -> Dict[str, Any]:
    """Update validation.status on validated files."""
    rows = _walk()
    touched = 0
    for r in rows:
        if r["id"] in ids:
            source = Path(r["_source"])
            data = dict(r["_raw"])
            validation = dict(data.get("validation", {}))
            validation["status"] = status
            data["validation"] = validation
            write_json_atomic(source, data)
            touched += 1
    audit("theory", ",".join(ids), "bulk_status", note=status)
    return {"touched": touched, "status": status, "affected_paths": []}


def bulk_delete(ids: List[str]) -> Dict[str, Any]:
    rows = _walk()
    deleted = 0
    for r in rows:
        if r["id"] in ids:
            source = Path(r["_source"])
            if source.exists():
                source.unlink()
                deleted += 1
    audit("theory", ",".join(ids), "bulk_delete", note=f"deleted={deleted}")
    return {"deleted": deleted, "affected_paths": []}


SPEC = ModuleSpec(
    name="theory",
    kind="theory",
    id_field="id",
    list_fn=list_items,
    get_fn=get_item,
    update_fn=update_item,
    delete_fn=delete_item,
    bulk_delete_fn=bulk_delete,
    bulk_status_fn=bulk_set_status,
)
