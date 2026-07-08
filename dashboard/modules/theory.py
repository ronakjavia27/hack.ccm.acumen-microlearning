"""Theory content module.

`theory.json` is a flat array of guideline / theory docs. Each entry has
the same shape as the inline sample from the mockup. We create this file
from the embedded sample if it doesn't exist yet.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import ModuleSpec, ItemNotFound
from ..storage import REPO_ROOT, read_json, write_json_atomic, audit

THEORY_PATH = REPO_ROOT / "theory.json"

# Seed theory doc — extracted from the mockup's embedded data-theory script.
_SEED_DOC = {
    "id": "sccm-esicm-surviving-sepsis-campaign-international-guidelines-management-sepsis-septic-shock-2026",
    "doc_type": "guideline",
    "title": "Surviving Sepsis Campaign: International Guidelines for Management of Sepsis and Septic Shock 2026",
    "issuing_bodies": ["SCCM", "ESICM"],
    "year": 2026,
    "doi": "10.1097/CCM.0000000000007075",
    "specialty": ["Multisystem"],
    "tags": ["sepsis", "septic shock", "guidelines", "critical care",
             "antimicrobials", "fluid resuscitation", "vasopressors",
             "ards", "corticosteroids"],
    "one_line_summary": (
        "- **2026 Surviving Sepsis Campaign (SSC) International Guidelines** "
        "provide an exhaustive, evidence-based framework for:\n"
        "  - **Screening**\n  - **Resuscitation**\n"
        "  - **Comprehensive management** of **adult patients** with "
        "**sepsis** and **septic shock**\n"
        "- Emphasize a **personalized, physiology-driven approach**."),
    "key_pearls": [
        "Screen high-risk patients using NEWS/NEWS2/MEWS; avoid qSOFA or isolated biomarkers for sepsis diagnosis.",
        "Administer broad-spectrum IV antimicrobials within 1 hour for septic shock or definite/probable sepsis, and **30 mL**/kg IV crystalloids for hypoperfusion.",
        "Target MAP of **65 mmHg** with norepinephrine as first-line vasopressor, using dynamic measures like Capillary Refill Time (target **\u2264 3 seconds**) to guide fluid responsiveness.",
        "Prolonged infusion of beta-lactams is strongly **recommended** for maintenance therapy after a loading dose, based on high-certainty evidence of **mortality** reduction.",
        "Consider IV hydrocortisone (**200 mg**/day) for septic shock requiring ongoing vasopressors, but conditionally recommend against IV vitamin C, IVIG, and most blood purification therapies.",
        "Initiate active fluid removal (diuresis) once acute resuscitation concludes and discuss goals of care and **prognosis** early (within 72 hours).",
    ],
    "consensus_method": "GRADE methodology, Evidence to Decision (EtD) framework",
    "search_period": None,
    "recommendation_blocks": [
        {"order": 1, "topic": "Screening and Early Management",
         "narrative": "(placeholder body - edit in dashboard)",
         "recommendations": []},
        {"order": 2, "topic": "Infection and Antimicrobial Therapy",
         "narrative": "(placeholder body - edit in dashboard)",
         "recommendations": []},
    ],
    "bedside_protocol": [
        {"step": 1, "title": "Screening & Recognition", "action": "(placeholder)"},
        {"step": 2, "title": "Hour-1 Resuscitation", "action": "(placeholder)"},
    ],
    "strengths_limitations": "Exhaustive GRADE synthesis.",
    "related_ids": [],
    "added_date": "2026-06-30",
    "_format_version": "reformatted_via_gpt-oss",
    "visibility": "published",
}


def _ensure_seed() -> None:
    if not THEORY_PATH.exists():
        write_json_atomic(THEORY_PATH, [_SEED_DOC])


def _load() -> List[Dict[str, Any]]:
    _ensure_seed()
    data = read_json(THEORY_PATH, default=[])
    return data if isinstance(data, list) else []


def _save(rows: List[Dict[str, Any]]) -> None:
    write_json_atomic(THEORY_PATH, rows)


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
    status = f.get("status", "")
    out = []
    for r in rows:
        item = dict(r)
        item["id"] = str(r.get("id"))
        item["status"] = r.get("visibility", "published")
        if status and item["status"] != status:
            continue
        if kw:
            hay = " ".join([
                str(r.get("title", "")),
                str(r.get("id", "")),
                " ".join(r.get("tags", []) or []),
            ]).lower()
            if kw not in hay:
                continue
        out.append(item)
    return out


def get_item(item_id: str) -> Dict[str, Any]:
    r = _row_by_id(item_id)
    if r is None:
        raise ItemNotFound(f"theory {item_id}")
    return dict(r)


def _touch_block_list(blocks: List[Any], edits: Dict[str, Any]) -> List[Any]:
    """Patch a list of recommendation blocks given a dict of edits.
    Edits format:
      {
        "blocks": [
          {"order": 1, "topic": "...", "narrative": "...",
           "recommendations": [{"statement": "...", "strength": "...", "evidence_grade": "..."}]}
        ]
      }
    Blocks in `blocks` are matched by `order` and updated; new ones appended.
    """
    if not isinstance(blocks, list):
        blocks = []
    out = list(blocks)
    by_order = {b.get("order"): i for i, b in enumerate(out) if isinstance(b, dict)}

    for new_b in edits.get("blocks", []):
        order = new_b.get("order")
        if order in by_order:
            i = by_order[order]
            merged = dict(out[i])
            for k, v in new_b.items():
                if k == "recommendations" and isinstance(v, list):
                    merged["recommendations"] = v  # wholesale replace for simplicity
                else:
                    merged[k] = v
            out[i] = merged
        else:
            out.append(new_b)
    return out


def _touch_steps(steps: List[Any], edits: List[Any]) -> List[Any]:
    """Patch the numbered bedside_protocol steps by `step` field, replace or append."""
    if not isinstance(steps, list):
        steps = []
    out = list(steps)
    by_n = {s.get("step"): i for i, s in enumerate(out) if isinstance(s, dict)}
    for new_s in edits or []:
        n = new_s.get("step")
        if n in by_n:
            out[by_n[n]] = dict(new_s)
        else:
            out.append(dict(new_s))
    out.sort(key=lambda s: s.get("step", 0))
    return out


def update_item(item_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    rows = _load()
    target_idx = None
    for i, r in enumerate(rows):
        if str(r.get("id")) == str(item_id):
            target_idx = i
            break
    if target_idx is None:
        raise ItemNotFound(f"theory {item_id}")

    old = dict(rows[target_idx])
    new = dict(rows[target_idx])
    dirty = False

    # Top-level scalar fields
    for k, v in fields.items():
        if k in ("recommendation_blocks_edits", "bedside_protocol_edits", "_content_edits"):
            continue
        if k in ("recommendation_blocks", "bedside_protocol"):
            continue  # handled via *_edits
        if new.get(k) != v:
            new[k] = v
            dirty = True

    # Nested block edits
    if "recommendation_blocks_edits" in fields and isinstance(fields["recommendation_blocks_edits"], dict):
        prev = new.get("recommendation_blocks", [])
        new_blocks = _touch_block_list(prev, fields["recommendation_blocks_edits"])
        if prev != new_blocks:
            new["recommendation_blocks"] = new_blocks
            dirty = True

    if "bedside_protocol_edits" in fields and isinstance(fields["bedside_protocol_edits"], list):
        prev = new.get("bedside_protocol", [])
        new_steps = _touch_steps(prev, fields["bedside_protocol_edits"])
        if prev != new_steps:
            new["bedside_protocol"] = new_steps
            dirty = True

    if (new_blocks_edits := fields.get("recommendation_blocks")) and isinstance(new_blocks_edits, list):
        if new.get("recommendation_blocks") != new_blocks_edits:
            new["recommendation_blocks"] = new_blocks_edits
            dirty = True
    if (new_steps_edits := fields.get("bedside_protocol")) and isinstance(new_steps_edits, list):
        if new.get("bedside_protocol") != new_steps_edits:
            new["bedside_protocol"] = new_steps_edits
            dirty = True

    if dirty:
        rows[target_idx] = new
        _save(rows)

    audit("theory", item_id, "update", fields)

    return {
        "id": str(item_id),
        "updated": dirty,
        "affected_paths": [str(THEORY_PATH.relative_to(REPO_ROOT))],
        "old": {"specialty": old.get("specialty")},
        "new": {"specialty": new.get("specialty")},
    }


def bulk_set_status(ids: List[str], status: str) -> Dict[str, Any]:
    rows = _load()
    id_set = {str(i) for i in ids}
    touched = 0
    for r in rows:
        if str(r.get("id")) in id_set:
            r["visibility"] = status
            touched += 1
    if touched:
        _save(rows)
        audit("theory", ",".join(ids), "bulk_status", note=status)
    return {"touched": touched, "status": status,
            "affected_paths": [str(THEORY_PATH.relative_to(REPO_ROOT))]}


SPEC = ModuleSpec(
    name="theory",
    kind="theory",
    id_field="id",
    list_fn=list_items,
    get_fn=get_item,
    update_fn=update_item,
    extra_endpoints={
        "bulk_status": ("POST", "/theory/bulk-status", bulk_set_status),
    },
)
