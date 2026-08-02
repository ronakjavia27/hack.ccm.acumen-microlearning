"""Flashcards content module (unified store).

Storage: output_files/flashcards/{System}/{Subtopic}.json — one file per
(system, subtopic), each card a persistent-UUID record with explicit
front/back. The master index (flashcards_index.json) is derived and rebuilt
on every write. Console items = subtopic files; the reader UI keeps the
deck/card view shape (id, subtopic, content with optional '---' divider)
via a thin view bridge.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import ModuleSpec, ItemNotFound
from ..storage import REPO_ROOT, audit
from acumen_core import flashcards as fc


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

EDITABLE_FIELDS = ["title", "specialty", "status"]

FLASHCARD_REGEN_PROMPT = """You are an expert ICU clinician. Revise the following study card based on the user's edit request.

User request: {edit_comment}

Current card:
{subtopic}: {content}

Output a revised JSON object with "subtopic", "front", and "back" fields.
- "subtopic": a short label for the card
- "front": a short crisp question (max ~15 words) the card answers
- "back": dense ICU-relevant content following this format:
**Core concept:** (1-2 lines)

**Key parameters:** (thresholds, definitions, targets)

**Clinical application:** (bedside decisions)

**Interventions:** (drugs, doses, devices)

**Pitfalls:** (errors, nuances)

Output ONLY valid JSON."""


def _view_card(card: Dict[str, Any]) -> Dict[str, Any]:
    """Store card -> console view card (old deck shape + divider content)."""
    front = (card.get("front") or "").strip()
    back = (card.get("back") or "").strip()
    content = f"{front}\n\n---\n\n{back}" if front else back
    return {
        "id": card.get("id"),
        "subtopic": card.get("data", {}).get("original_subtopic") or card.get("subtopic") or "",
        "content": content,
        "front": front,
        "back": back,
        "status": card.get("status", "pending"),
        "tags": card.get("tags") or [],
        "source": card.get("source"),
    }


def _view_deck(system: str, subtopic: str, data: Dict[str, Any]) -> Dict[str, Any]:
    cards = data.get("cards") or []
    total = len(cards)
    preserved = sum(1 for c in cards if c.get("status") == "preserved")
    discarded = sum(1 for c in cards if c.get("status") == "discarded")
    if total and preserved == total:
        deck_status = "preserved"
    elif total and discarded == total:
        deck_status = "discarded"
    else:
        deck_status = "pending"
    src_files = sorted({str(c.get("source_file")) for c in cards if c.get("source_file")})
    deck_id = f"{system}/{subtopic}"
    return {
        "id": deck_id,
        "title": subtopic,
        "specialty": system,
        "card_count": total,
        "preserved_count": preserved,
        "discarded_count": discarded,
        "pending_count": total - preserved - discarded,
        "status": deck_status,
        "created_at": data.get("created_at", ""),
        "updated_at": data.get("updated_at", ""),
        "source": "store",
        "md_path": src_files[0] if src_files else "",
        "subtopics": sorted({t for c in cards for t in (c.get("tags") or []) if isinstance(t, str)}),
        "_system": system,
        "_subtopic": subtopic,
        "_raw": data,
    }


def _walk() -> List[Dict[str, Any]]:
    """Walk the unified store and return one item per (system, subtopic) file."""
    items = []
    idx = fc.load_flashcards_index()
    for system, subs in idx.get("systems", {}).items():
        for subtopic, meta in subs.items():
            data = fc.load_subtopic_file(system, subtopic)
            if data is None:
                continue
            items.append(_view_deck(system, subtopic, data))
    return items


def _find(rows: List[Dict[str, Any]], deck_id: str) -> Optional[Dict[str, Any]]:
    for r in rows:
        if r["id"] == deck_id:
            return r
    return None


def list_items(filters: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    rows = _walk()
    f = filters or {}
    kw = f.get("q", "").lower().strip()
    specialty = f.get("system", "") or f.get("specialty", "")
    status = f.get("status", "")
    out = []
    for r in rows:
        if specialty and r.get("specialty", "") != specialty:
            continue
        if status and r.get("status", "") != status:
            continue
        if kw:
            hay = " ".join([
                str(r.get("title", "")),
                str(r.get("id", "")),
                str(r.get("specialty", "")),
            ]).lower()
            if kw not in hay:
                continue
        out.append(r)
    return out


def get_item(item_id: str) -> Dict[str, Any]:
    """Return the full subtopic file content (cards in console view shape)."""
    rows = _walk()
    r = _find(rows, item_id)
    if r is None:
        raise ItemNotFound(f"flashcards {item_id}")
    deck = dict(r)
    deck["cards"] = [_view_card(c) for c in r["_raw"].get("cards", [])]
    deck["_raw"] = r["_raw"]
    return deck


def _find_store_card(deck_view: Dict[str, Any], card_id: str) -> Optional[Dict[str, Any]]:
    for c in deck_view["_raw"].get("cards", []):
        if c.get("id") == card_id:
            return c
    return None


def _save_card_view(card: Dict[str, Any]) -> None:
    fc.upsert_card(card)


def _rewrite_md_card(md_abs: Path, subtopic: str, back: str, front: str = "") -> bool:
    """Rewrite the '## {subtopic}' section of a source markdown deck in place."""
    if not md_abs or not md_abs.exists():
        return False
    try:
        lines = md_abs.read_text(encoding="utf-8", errors="replace").split("\n")
    except Exception:
        return False
    starts = [i for i, ln in enumerate(lines) if ln.strip().startswith("## ")]
    target = None
    for i in starts:
        if lines[i].strip()[3:].strip().strip('"').lower() == str(subtopic).strip().strip('"').lower():
            target = i
            break
    if target is None:
        return False
    end = starts[starts.index(target) + 1] if starts.index(target) + 1 < len(starts) else len(lines)
    body = back
    if front:
        body = f"{front}\n\n---\n\n{back}"
    new_sec = [f"## {subtopic}"] + (body.split("\n") if body else [])
    lines[target:end] = new_sec
    try:
        md_abs.write_text("\n".join(lines), encoding="utf-8")
    except Exception:
        return False
    return True


def update_item(item_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    rows = _walk()
    r = _find(rows, item_id)
    if r is None:
        raise ItemNotFound(f"flashcards {item_id}")

    dirty = False
    affected: List[Path] = []
    cards = r["_raw"].get("cards", [])

    action = fields.get("action", "")
    if action in ("preserve", "discard", "bulk-preserve", "bulk-discard"):
        new_status = "preserved" if action.endswith("preserve") else "discarded"
        card_id = fields.get("card_id", "")
        for c in cards:
            if card_id and c.get("id") != card_id:
                continue
            if c.get("status") != new_status:
                c["status"] = new_status
                fc.upsert_card(c)
                dirty = True

    if "specialty" in fields and str(fields["specialty"]).strip() and \
            str(fields["specialty"]).strip() != r["specialty"]:
        new_sys = str(fields["specialty"]).strip()
        for c in cards:
            fc.move_card(c.get("id"), new_sys, r["_subtopic"])
        affected.append(Path("output_files", "flashcards", new_sys))
        dirty = True

    if "title" in fields and str(fields["title"]).strip() and \
            str(fields["title"]).strip() != r["title"]:
        new_sub = fc.canonical_subtopic(r["specialty"], str(fields["title"]).strip())
        for c in cards:
            fc.move_card(c.get("id"), r["specialty"], new_sub)
        affected.append(Path("output_files", "flashcards", r["specialty"]))
        dirty = True

    if not dirty:
        return {"id": item_id, "updated": False, "affected_paths": []}

    audit("flashcards", item_id, "update", note=f"action={action or 'reclassify'}")
    return {"id": item_id, "updated": True,
            "affected_paths": [str(p) for p in affected] or [fc.subtopic_file_path(r["specialty"], r["_subtopic"])]}


def _regenerate_card(card: Dict[str, Any], edit_comment: str) -> Optional[Dict[str, Any]]:
    """Send store card + edit comment to the LLM for revision -> {subtopic, front, back}."""
    try:
        from acumen_core.flashcards import flashcard_llm
        subtopic = card.get("data", {}).get("original_subtopic") or card.get("subtopic", "")
        content = card.get("back") or ""
        prompt = FLASHCARD_REGEN_PROMPT.format(
            edit_comment=edit_comment,
            subtopic=subtopic,
            content=content,
        )
        result = flashcard_llm(
            "You are a precise ICU study card editor. Output ONLY valid JSON.",
            prompt,
            json_mode=True,
        )
        if result and "back" in result:
            return result
    except Exception as e:
        print(f"  [X] Card regeneration failed: {e}")
    return None


def delete_item(item_id: str) -> Dict[str, Any]:
    rows = _walk()
    r = _find(rows, item_id)
    if r is None:
        raise ItemNotFound(f"flashcards {item_id}")
    cards = r["_raw"].get("cards", [])
    has_md = any(c.get("source") == "md" for c in cards)
    path = fc.subtopic_file_path(r["specialty"], r["_subtopic"])
    try:
        if os.path.exists(path):
            os.remove(path)
            fc.rebuild_flashcards_index()
    except OSError:
        pass
    audit("flashcards", item_id, "delete", note=f"deleted {path} (md kept={has_md})")
    return {"id": item_id, "deleted": True, "affected_paths": [str(path)],
            "md_kept": has_md, "ledger_removed": False}


def bulk_set_status(ids: List[str], status: str) -> Dict[str, Any]:
    touched = 0
    for deck_id in ids:
        try:
            r = _find(_walk(), deck_id)
            if r is None:
                continue
            for c in r["_raw"].get("cards", []):
                if status == "preserve-all":
                    c["status"] = "preserved"
                elif status == "discard-all":
                    c["status"] = "discarded"
                else:
                    continue
                fc.upsert_card(c)
                touched += 1
        except Exception:
            continue
    audit("flashcards", ",".join(ids), "bulk_status", note=status)
    return {"touched": touched, "status": status, "affected_paths": []}


def bulk_delete(ids: List[str]) -> Dict[str, Any]:
    deleted = 0
    for deck_id in ids:
        try:
            r = _find(_walk(), deck_id)
            if r is None:
                continue
            path = fc.subtopic_file_path(r["specialty"], r["_subtopic"])
            if os.path.exists(path):
                os.remove(path)
                deleted += 1
        except Exception:
            continue
    if deleted:
        fc.rebuild_flashcards_index()
    audit("flashcards", ",".join(ids), "bulk_delete", note=f"deleted={deleted}")
    return {"deleted": deleted, "affected_paths": []}


SPEC = ModuleSpec(
    name="Flashcards",
    kind="flashcards",
    id_field="id",
    list_fn=list_items,
    get_fn=get_item,
    update_fn=update_item,
    delete_fn=delete_item,
    bulk_delete_fn=bulk_delete,
    bulk_status_fn=bulk_set_status,
)
