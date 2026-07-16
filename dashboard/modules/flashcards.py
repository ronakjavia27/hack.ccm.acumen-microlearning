"""Flashcards content module.

Each flashcard deck is a JSON file at output_files/flashcards/{specialty}/{slug}.json
containing an array of structured study cards on subtopics within a clinical topic.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import ModuleSpec, ItemNotFound
from ..storage import REPO_ROOT, read_json, write_json_atomic, audit


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

FLASHCARDS_DIR = REPO_ROOT / "output_files" / "flashcards"

EDITABLE_FIELDS = ["title", "specialty", "status"]

FLASHCARD_REGEN_PROMPT = """You are an expert ICU clinician. Revise the following study card based on the user's edit request.

User request: {edit_comment}

Current card:
{subtopic}: {content}

Output a revised JSON object with "subtopic" and "content" fields. The content must follow this format:
**Core concept:** (1-2 lines)

**Key parameters:** (thresholds, definitions, targets)

**Clinical application:** (bedside decisions)

**Interventions:** (drugs, doses, devices)

**Pitfalls:** (errors, nuances)

Keep it dense, ICU-relevant, and actionable. Output ONLY valid JSON."""


def _walk() -> List[Dict[str, Any]]:
    """Walk FLASHCARDS_DIR recursively and return deck metadata."""
    items = []
    if not FLASHCARDS_DIR.is_dir():
        return items
    for f in sorted(FLASHCARDS_DIR.rglob("*.json")):
        try:
            data = read_json(f, default={})
        except Exception:
            continue
        if not isinstance(data, dict) or not data:
            continue
        rel = f.relative_to(FLASHCARDS_DIR)
        deck_id = str(rel.with_suffix("")).replace("\\", "/").strip()
        cards = data.get("cards", [])
        total = len(cards)
        preserved = sum(1 for c in cards if c.get("status") == "preserved")
        discarded = sum(1 for c in cards if c.get("status") == "discarded")
        pending = total - preserved - discarded
        items.append({
            "id": deck_id,
            "title": data.get("title", rel.parent.name),
            "specialty": data.get("specialty", rel.parent.name),
            "card_count": total,
            "preserved_count": preserved,
            "discarded_count": discarded,
            "pending_count": pending,
            "status": data.get("status", "pending"),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
            "_source": str(f),
            "_raw": data,
        })
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
    specialty = f.get("system", "")
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
        item = {k: v for k, v in r.items() if k not in ("_source", "_raw")}
        out.append(item)
    return out


def get_item(item_id: str) -> Dict[str, Any]:
    """Return the full deck content (not the list wrapper)."""
    rows = _walk()
    r = _find(rows, item_id)
    if r is None:
        raise ItemNotFound(f"flashcards {item_id}")
    deck = r.get("_raw", r)
    deck["id"] = r["id"]
    deck["_source"] = r["_source"]
    # Ensure all cards have IDs
    cards = deck.get("cards", [])
    slug_base = slugify(deck.get("title", "card"))[:30]
    for i, card in enumerate(cards):
        if not card.get("id"):
            card["id"] = f"{slug_base}-{i}"
            card.setdefault("status", "pending")
    return deck


def update_item(item_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    rows = _walk()
    r = _find(rows, item_id)
    if r is None:
        raise ItemNotFound(f"flashcards {item_id}")

    source = Path(r["_source"])
    deck = dict(r["_raw"])
    dirty = False

    # Ensure all cards have IDs (backward-compat with pre-ID cards)
    cards = deck.get("cards", [])
    slug_base = slugify(deck.get("title", "card"))[:30]
    for i, card in enumerate(cards):
        if not card.get("id"):
            card["id"] = f"{slug_base}-{i}"
            card.setdefault("status", "pending")
            dirty = True

    action = fields.get("action", "")

    def _find_card(card_id):
        for card in cards:
            if card.get("id") == card_id:
                return card
        return None

    if action == "preserve":
        card_id = fields.get("card_id", "")
        card = _find_card(card_id)
        if card and card.get("status") != "preserved":
            card["status"] = "preserved"
            dirty = True

    elif action == "discard":
        card_id = fields.get("card_id", "")
        card = _find_card(card_id)
        if card and card.get("status") != "discarded":
            card["status"] = "discarded"
            dirty = True

    elif action == "bulk-preserve":
        for card in cards:
            if card.get("status") != "discarded":
                card["status"] = "preserved"
                dirty = True

    elif action == "bulk-discard":
        for card in cards:
            if card.get("status") != "preserved":
                card["status"] = "discarded"
                dirty = True

    elif action == "edit":
        card_id = fields.get("card_id", "")
        edit_comment = fields.get("edit_comment", "")
        if card_id and edit_comment:
            card = _find_card(card_id)
            if card:
                revised = _regenerate_card(card, edit_comment)
                if revised:
                    card["subtopic"] = revised.get("subtopic", card["subtopic"])
                    card["content"] = revised.get("content", card["content"])
                    dirty = True
                    history = deck.setdefault("edit_history", [])
                    history.append({
                        "card_id": card_id,
                        "edit_comment": edit_comment,
                        "timestamp": datetime.now().isoformat(),
                    })

    if "title" in fields and str(fields["title"]) != str(deck.get("title", "")):
        deck["title"] = fields["title"]
        dirty = True

    if "specialty" in fields and str(fields["specialty"]) != str(deck.get("specialty", "")):
        deck["specialty"] = fields["specialty"]
        dirty = True

    if "status" in fields and str(fields["status"]) != str(deck.get("status", "")):
        deck["status"] = fields["status"]
        dirty = True

    if not dirty:
        return {"id": item_id, "updated": False, "affected_paths": []}

    deck["updated_at"] = datetime.now().isoformat()
    write_json_atomic(source, deck)
    audit("flashcards", item_id, "update", note=f"action={action}")
    return {"id": item_id, "updated": True, "affected_paths": [str(source)]}


def _regenerate_card(card: Dict[str, Any], edit_comment: str) -> Optional[Dict[str, Any]]:
    """Send card + edit comment to LLM for revision."""
    try:
        from acumen_core.llm import execute_with_openrouter
        subtopic = card.get("subtopic", "")
        content = card.get("content", "")
        prompt = FLASHCARD_REGEN_PROMPT.format(
            edit_comment=edit_comment,
            subtopic=subtopic,
            content=content,
        )
        result = execute_with_openrouter(
            "You are a precise ICU study card editor. Output ONLY valid JSON.",
            prompt,
        )
        if result and "subtopic" in result and "content" in result:
            return result
    except Exception as e:
        print(f"  [X] Card regeneration failed: {e}")
    return None


def delete_item(item_id: str) -> Dict[str, Any]:
    rows = _walk()
    r = _find(rows, item_id)
    if r is None:
        raise ItemNotFound(f"flashcards {item_id}")
    source = Path(r["_source"])
    if source.exists():
        source.unlink()
    audit("flashcards", item_id, "delete", note=f"deleted {source}")
    return {"id": item_id, "deleted": True, "affected_paths": []}


def bulk_set_status(ids: List[str], status: str) -> Dict[str, Any]:
    touched = 0
    for deck_id in ids:
        try:
            r = _find(_walk(), deck_id)
            if r is None:
                continue
            source = Path(r["_source"])
            deck = dict(r["_raw"])
            if status == "preserve-all":
                for card in deck.get("cards", []):
                    card["status"] = "preserved"
            elif status == "discard-all":
                for card in deck.get("cards", []):
                    card["status"] = "discarded"
            else:
                deck["status"] = status
            deck["updated_at"] = datetime.now().isoformat()
            write_json_atomic(source, deck)
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
            source = Path(r["_source"])
            if source.exists():
                source.unlink()
                deleted += 1
        except Exception:
            continue
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
