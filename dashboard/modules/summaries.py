"""Summaries content module.

A "summary" in hack.CCM has two parts:
  1. A ledger entry in `sent_summaries.json`  — flat metadata (title, doi, system,
     subtopic, show_on_web, email_pushed, ...). This is what the dashboard list shows.
  2. A full content file in `output_files/<System>/<Type>/<file_name>` whose name
     matches the ledger's `file_name` (after swapping the `.pdf`→`.json` suffix).

Edits can touch either or both:
  - editing metadata (system/subtopic/show_on_web/email_pushed) updates the ledger
  - editing body content (one_line_summary / key_pearls / recommendation_blocks /
    bedside_protocol) updates the full content file. The mockup initially shows
    body edits as live markdown because that's what the user wants — "edit theory"
    is just a theory-shaped full-content file edit.

When system changes, the content file must be physically moved across
`output_files/<oldSystem>/<Type>/` → `output_files/<newSystem>/<Type>/`, and the
ledger `file_name` is unchanged (it's a stable id).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import ModuleSpec, ItemNotFound
from ..storage import (
    REPO_ROOT,
    read_json,
    write_json_atomic,
    move_file,
    audit,
)

LEDGER_PATH = REPO_ROOT / "sent_summaries.json"
OUTPUT_DIR = REPO_ROOT / "output_files"
PENDING_SUBTOPICS_PATH = REPO_ROOT / "pending_subtopics.json"
SUBTOPIC_MAPPING_PATH = REPO_ROOT / "subtopic_mapping.json"
PEARLS_PATH = REPO_ROOT / "pearls.json"

# Fields the dashboard may edit on the ledger (flat metadata).
LEDGER_FIELDS = [
    "title", "authors", "journal", "doi", "year",
    "system", "type", "subtopic",
    "md_generated", "email_pushed", "show_on_web",
    "parsing_notes",
]


def _load_ledger() -> List[Dict[str, Any]]:
    data = read_json(LEDGER_PATH, default=[])
    if not isinstance(data, list):
        return []
    return data


def _save_ledger(rows: List[Dict[str, Any]]) -> None:
    write_json_atomic(LEDGER_PATH, rows)


def _row_by_id(item_id: str) -> Optional[Dict[str, Any]]:
    rid = str(item_id)
    for row in _load_ledger():
        if str(row.get("serial_number")) == rid:
            return row
    return None


def _content_path_for_row(row: Dict[str, Any]) -> Optional[Path]:
    """Resolve the on-disk JSON content file. The ledger stores a `.pdf` filename
    (the original source paper); the content file is `.pdf.xml.json`? Or `.json`?
    In practice both patterns appear in the repo. We try the obvious substitutions
    in order and return the first match."""
    fn = row.get("file_name", "")
    if not fn:
        return None
    if fn.endswith(".pdf"):
        candidate = fn[:-4] + ".json"
    else:
        candidate = fn
    system = row.get("system", "")
    type_ = row.get("type", "")
    if not system:
        return None
    candidates = [
        OUTPUT_DIR / system / type_ / candidate,
        OUTPUT_DIR / system / candidate,
    ]
    # Also scan: any file under OUTPUT_DIR/system/**/<candidate>
    if not any(p.exists() for p in candidates):
        for p in (OUTPUT_DIR / system).rglob(candidate):
            return p
    for p in candidates:
        if p.exists():
            return p
    return None


def list_items(filters: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    rows = _load_ledger()
    out = []
    kw = (filters or {}).get("q", "").lower().strip()
    filters = filters or {}
    for r in rows:
        item = {
            "id": str(r.get("serial_number")),
            "serial_number": r.get("serial_number"),
            "file_name": r.get("file_name"),
            "title": r.get("title", ""),
            "authors": r.get("authors", ""),
            "journal": r.get("journal", ""),
            "doi": r.get("doi", ""),
            "year": r.get("year", ""),
            "system": r.get("system", ""),
            "type": r.get("type", ""),
            "subtopic": r.get("subtopic", ""),
            "md_generated": r.get("md_generated", ""),
            "email_pushed": r.get("email_pushed", ""),
            "email_pushed_date": r.get("email_pushed_date", ""),
            "date_added": r.get("date_added", ""),
            "parsing_notes": r.get("parsing_notes", ""),
            "show_on_web": r.get("show_on_web", "No"),
        }
        if filters.get("system") and item["system"] != filters["system"]:
            continue
        if filters.get("status"):
            want = filters["status"]
            shown = item["show_on_web"] == "Yes"
            if want == "published" and not shown:
                continue
            if want == "hidden" and shown:
                continue
        if kw:
            hay = " ".join([
                str(item["title"] or ""), str(item["authors"] or ""),
                str(item["doi"] or ""), str(item["file_name"] or ""),
                str(item["id"] or ""),
            ]).lower()
            if kw not in hay:
                continue
        out.append(item)
    return out


def get_item(item_id: str) -> Dict[str, Any]:
    row = _row_by_id(item_id)
    if not row:
        raise ItemNotFound(f"summary {item_id}")
    return {
        "id": str(row.get("serial_number")),
        "serial_number": row.get("serial_number"),
        "file_name": row.get("file_name"),
        "title": row.get("title", ""),
        "authors": row.get("authors", ""),
        "journal": row.get("journal", ""),
        "doi": row.get("doi", ""),
        "year": row.get("year", ""),
        "system": row.get("system", ""),
        "type": row.get("type", ""),
        "subtopic": row.get("subtopic", ""),
        "md_generated": row.get("md_generated", ""),
        "email_pushed": row.get("email_pushed", ""),
        "email_pushed_date": row.get("email_pushed_date", ""),
        "date_added": row.get("date_added", ""),
        "parsing_notes": row.get("parsing_notes", ""),
        "show_on_web": row.get("show_on_web", "No"),
    }


def get_content(item_id: str) -> Dict[str, Any]:
    """Return the full content document stored in `output_files/.../<file_name>`."""
    row = _row_by_id(item_id)
    if not row:
        raise ItemNotFound(f"summary {item_id}")
    p = _content_path_for_row(row)
    if p is None or not p.exists():
        return {}
    return read_json(p, default={})


def update_item(item_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    rows = _load_ledger()
    rid = str(item_id)
    target_idx = None
    for i, r in enumerate(rows):
        if str(r.get("serial_number")) == rid:
            target_idx = i
            break
    if target_idx is None:
        raise ItemNotFound(f"summary {item_id}")

    old = dict(rows[target_idx])
    new = dict(rows[target_idx])
    dirty_ledger = False
    moved_paths: List[Path] = []

    sys_changed = False
    subtopic_changed = False

    for k, v in fields.items():
        if k not in LEDGER_FIELDS and k != "_content_edits":
            continue
        if k == "_content_edits":
            continue
        if new.get(k) != v:
            new[k] = v
            dirty_ledger = True
            if k == "system":
                sys_changed = True
            if k == "subtopic":
                subtopic_changed = True

    # If system changed → physically move the content file across folders.
    # We do this BEFORE saving the ledger so the new path resolves correctly.
    if sys_changed and old.get("system") and old.get("file_name") and new.get("system"):
        src = _content_path_for_row(old)
        if src and src.exists():
            fname = src.name
            type_ = new.get("type") or "Other"
            dst_dir = OUTPUT_DIR / new["system"] / type_
            dst_dir.mkdir(parents=True, exist_ok=True)
            dst = dst_dir / fname
            if src.resolve() != dst.resolve():
                move_file(src, dst)
                moved_paths.append(src)
                moved_paths.append(dst)

    rows[target_idx] = new
    if dirty_ledger:
        _save_ledger(rows)

    # Sync system/subtopic changes to subtopic tracking files and pearls
    if sys_changed or subtopic_changed:
        file_name = new.get("file_name", "")
        title = new.get("title", "")
        new_system = new.get("system", "")
        new_subtopic = new.get("subtopic", "")

        # Update pending_subtopics.json (match by file_name)
        pending = read_json(PENDING_SUBTOPICS_PATH, default=[])
        if isinstance(pending, list):
            p_dirty = False
            for p in pending:
                if p.get("file_name") == file_name:
                    if p.get("system") != new_system:
                        p["system"] = new_system
                        p_dirty = True
                    if p.get("subtopic") != new_subtopic:
                        p["subtopic"] = new_subtopic
                        p_dirty = True
            if p_dirty:
                write_json_atomic(PENDING_SUBTOPICS_PATH, pending)

        # Update subtopic_mapping.json (match by title)
        mapping = read_json(SUBTOPIC_MAPPING_PATH, default=[])
        if isinstance(mapping, list):
            m_dirty = False
            for m in mapping:
                if m.get("title", "").strip().lower() == title.strip().lower():
                    if m.get("system") != new_system:
                        m["system"] = new_system
                        m_dirty = True
                    if m.get("subtopic") != new_subtopic:
                        m["subtopic"] = new_subtopic
                        m_dirty = True
            if m_dirty:
                write_json_atomic(SUBTOPIC_MAPPING_PATH, mapping)

        # Cascade to pearls (match by file_name)
        if file_name:
            from .pearls import reclassify_by_file_name
            try:
                reclassify_by_file_name(file_name, new_system, new_subtopic)
            except Exception:
                pass  # non-critical; already logged by reclassify

    # Body content edit (the theory-shaped full doc in output_files)
    content_edits = fields.get("_content_edits")
    content_path = None
    if content_edits and isinstance(content_edits, dict) and content_edits:
        content_path = _content_path_for_row(new)
        if content_path and content_path.exists():
            doc = read_json(content_path, default={})
            changed_doc = False
            for k, v in content_edits.items():
                if doc.get(k) != v:
                    doc[k] = v
                    changed_doc = True
            if changed_doc:
                write_json_atomic(content_path, doc)

    audit(
        "summaries",
        item_id,
        "update",
        fields,
        note=(
            f"system->{new.get('system')}, subtopic->{new.get('subtopic')}"
            + (f", moved {len(moved_paths)//2} file(s)" if moved_paths else "")
        ),
    )

    affected_paths: List[str] = []
    if dirty_ledger:
        affected_paths.append(str(LEDGER_PATH.relative_to(REPO_ROOT)))
    if content_path and content_path.exists():
        try:
            affected_paths.append(str(content_path.relative_to(REPO_ROOT)))
        except ValueError:
            affected_paths.append(str(content_path))
    for p in moved_paths:
        try:
            path_str = str(Path(p).relative_to(REPO_ROOT))
        except ValueError:
            path_str = str(p)
        if path_str not in affected_paths:
            affected_paths.append(path_str)

    return {
        "id": rid,
        "updated": dirty_ledger or (content_edits is not None),
        "affected_paths": list(dict.fromkeys(affected_paths)),
        "system_changed": sys_changed,
        "subtopic_changed": subtopic_changed,
        "old": {"system": old.get("system"), "subtopic": old.get("subtopic")},
        "new": {"system": new.get("system"), "subtopic": new.get("subtopic")},
        "moved": moved_paths,
    }


def delete_item(item_id: str) -> Dict[str, Any]:
    rows = _load_ledger()
    rid = str(item_id)
    target_idx = None
    target = None
    for i, r in enumerate(rows):
        if str(r.get("serial_number")) == rid:
            target_idx = i
            target = dict(r)
            break
    if target_idx is None:
        raise ItemNotFound(f"summary {item_id}")

    file_name = target.get("file_name", "")
    deleted_pearls = 0
    if file_name:
        pearls_path = REPO_ROOT / "pearls.json"
        pearls = read_json(pearls_path, default=[])
        if isinstance(pearls, list):
            before = len(pearls)
            pearls = [p for p in pearls if p.get("file_name") != file_name]
            deleted_pearls = before - len(pearls)
            if deleted_pearls:
                write_json_atomic(pearls_path, pearls)

    # Remove content file
    content_path = _content_path_for_row(target)
    if content_path and content_path.exists():
        content_path.unlink()

    # Remove from ledger
    entry = rows.pop(target_idx)
    _save_ledger(rows)

    audit("summaries", item_id, "delete",
          note=f"file={file_name} pearls_deleted={deleted_pearls}")
    return {
        "id": rid,
        "deleted": True,
        "file_name": file_name,
        "pearls_deleted": deleted_pearls,
        "affected_paths": [
            str(LEDGER_PATH.relative_to(REPO_ROOT)),
            *(str(p) for p in ([content_path] if content_path else [])),
        ],
    }


def bulk_delete(ids: List[str]) -> Dict[str, Any]:
    rows = _load_ledger()
    id_set = {str(i) for i in ids}
    pearls_path = REPO_ROOT / "pearls.json"
    pearls = read_json(pearls_path, default=[])
    total_pearls_deleted = 0
    removed_file_names = []
    affected = [str(LEDGER_PATH.relative_to(REPO_ROOT))]

    kept_ledger = []
    for r in rows:
        if str(r.get("serial_number")) in id_set:
            fn = r.get("file_name", "")
            if fn:
                removed_file_names.append(fn)
                before = len(pearls) if isinstance(pearls, list) else 0
                if isinstance(pearls, list):
                    pearls = [p for p in pearls if p.get("file_name") != fn]
                    total_pearls_deleted += before - len(pearls)
            content_path = _content_path_for_row(r)
            if content_path and content_path.exists():
                content_path.unlink()
                affected.append(str(content_path))
        else:
            kept_ledger.append(r)

    _save_ledger(kept_ledger)
    if total_pearls_deleted:
        write_json_atomic(pearls_path, pearls)
        affected.append(str(pearls_path.relative_to(REPO_ROOT)))

    audit("summaries", ",".join(ids), "bulk_delete",
          note=f"pearls_deleted={total_pearls_deleted}")
    return {"deleted": len(ids) - len(kept_ledger), "pearls_deleted": total_pearls_deleted,
            "affected_paths": list(dict.fromkeys(affected))}


def bulk_set_status(ids: List[str], status: str) -> Dict[str, Any]:
    """`status` is one of published/queued/hidden/removed which, for summaries,
    maps to `show_on_web` Yes (published, queued) → or No (hidden, removed).
    Queued is preserved as a hint via `parsing_notes`."""
    rows = _load_ledger()
    id_set = {str(i) for i in ids}
    touched = 0
    for r in rows:
        if str(r.get("serial_number")) in id_set:
            if status in ("published", "queued"):
                r["show_on_web"] = "Yes"
            else:
                r["show_on_web"] = "No"
            if status == "queued":
                r["parsing_notes"] = (r.get("parsing_notes") or "") + "[queued] "
            touched += 1
    if touched:
        _save_ledger(rows)
        audit("summaries", ",".join(ids), "bulk_status", note=status)
    return {"touched": touched, "status": status,
            "affected_paths": [str(LEDGER_PATH.relative_to(REPO_ROOT))]}


SPEC = ModuleSpec(
    name="Summaries",
    kind="summaries",
    id_field="serial_number",
    list_fn=list_items,
    get_fn=get_item,
    update_fn=update_item,
    delete_fn=delete_item,
    bulk_delete_fn=bulk_delete,
    bulk_status_fn=bulk_set_status,
    has_visibility_flag=True,
    visible_value_field="show_on_web",
    extra_endpoints={
        "content": ("GET", "/summaries/{item_id}/content", get_content),
        "bulk_status": ("POST", "/summaries/bulk-status", bulk_set_status),
    },
)
