"""Approve / publish / unpublish Studio items into the live content stores.

Targets (all existing stores — the portal needs no change to show them):
  theory answer → output_files/Theory MDs/{System}/{Subtopic}/qna-{id}.md  (+ theory_notes_meta.json entry)
  flashcards    → unified flashcard store (source="studio", stable UUIDs reused by position)
  questions     → output_files/question_bank/{subject}/studio.json
                  {id}-w  the uploaded question as a written/viva item (rubric + model answer)
                  {id}-u  the uploaded MCQ itself (when the upload was an MCQ)
                  {id}-m<n> derived MCQs
Every published object carries `studio` provenance: item id, version, draft/verify models, reviewer, date.
"""
from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional

from acumen_core import config
from acumen_core.tracking import load_json_safe, save_json_atomic

from . import items as store

def _theory_meta() -> str:
    return os.path.join(config.THEORY_MDS_DIR, "theory_notes_meta.json")


WRITTEN_KIND = {"long": "written_long", "short": "written_short", "very_short": "written_short", "viva": "viva"}


class PublishError(ValueError):
    pass


# ---- review ---------------------------------------------------------------------

def default_parts(pkg: dict) -> dict:
    return {"answer": True, "flashcards": list(range(len(pkg.get("flashcards") or []))),
            "mcqs": list(range(len(pkg.get("mcqs") or [])))}


def approve(item: dict, by: str, parts: Optional[dict] = None, note: str = "", save: bool = True) -> dict:
    cur = store.current_version(item)
    if not cur:
        raise PublishError("nothing to approve")
    if item["status"] not in ("generated", "approved", "published"):
        raise PublishError(f"cannot approve an item in status {item['status']}")
    pkg = cur["package"]
    p = {**default_parts(pkg), **(parts or {})}
    p["flashcards"] = sorted({int(i) for i in p["flashcards"] if 0 <= int(i) < len(pkg.get("flashcards") or [])})
    p["mcqs"] = sorted({int(i) for i in p["mcqs"] if 0 <= int(i) < len(pkg.get("mcqs") or [])})
    p["answer"] = bool(p.get("answer"))
    item["review"] = {"by": by, "at": store.now(), "version": cur["v"], "hash": cur["hash"], "parts": p,
                      "note": note, "triage_at_review": cur.get("triage")}
    store.transition(item, "approved", by, note or f"v{cur['v']}")
    if save:
        store.save(item)
    return item


def reject(item: dict, by: str, note: str = "", save: bool = True) -> dict:
    if item.get("published"):
        unpublish(item, save=False)
    store.transition(item, "rejected", by, note)
    if save:
        store.save(item)
    return item


def request_revision(item: dict, by: str, note: str, save: bool = True) -> dict:
    if not note.strip():
        raise PublishError("say what should change")
    item["revision_note"] = note.strip()
    store.transition(item, "revision_requested", by, note)
    if save:
        store.save(item)
    return item


def approve_green(by: str, subject: str = "") -> List[str]:
    done = []
    for it in store.all_items(subject):
        if it["status"] == "generated" and it.get("triage") == "green":
            approve(it, by, note="bulk-approved (green)")
            done.append(it["id"])
    return done


# ---- helpers ----------------------------------------------------------------------

def _safe(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\n\r\t]+', " ", name or "General").strip()[:80] or "General"


def _provenance(item: dict, ver: dict) -> dict:
    r = item["review"]
    return {"studio_id": item["id"], "version": ver["v"], "origin": ver.get("origin"),
            "drafted_by": (ver.get("models") or {}).get("draft"), "verified_by": (ver.get("models") or {}).get("verify")
            if ver.get("verification") else None,
            "reviewed_by": r["by"], "reviewed_at": r["at"], "triage": ver.get("triage")}


def _theory_md(item: dict, pkg: dict, prov: dict) -> str:
    lines = [f"# {pkg.get('title') or item['question'][:80]}", "",
             f"> **Question{' (' + str(item['marks']) + ' marks)' if item.get('marks') else ''}:** {item['question']}", ""]
    if item.get("options"):
        key = pkg.get("mcq_key") or item.get("given_key") or []
        for i, o in enumerate(item["options"]):
            lines.append(f"- {'**' if i in key else ''}{chr(65 + i)}. {o}{'** ✓' if i in key else ''}")
        lines.append("")
    lines += [pkg.get("answer_md", "").strip(), ""]
    if pkg.get("key_points"):
        lines += ["## Key points", ""] + [f"- {k}" for k in pkg["key_points"]] + [""]
    lines += ["---",
              f"_hack.CCM Studio · AI-drafted{', independently AI-verified' if prov.get('verified_by') else ''}"
              f", reviewed by {prov['reviewed_by']} on {prov['reviewed_at'][:10]} · v{prov['version']}_", ""]
    return "\n".join(lines)


def _bank_path(subject: str) -> str:
    return os.path.join(config.QUESTION_BANK_DIR, subject, "studio.json")


def _write_bank(subject: str, item_id: str, entries: List[dict]):
    path = _bank_path(subject)
    bank = load_json_safe(path, default=[]) or []
    bank = [q for q in bank if (q.get("studio") or {}).get("studio_id") != item_id] + entries
    os.makedirs(os.path.dirname(path), exist_ok=True)
    save_json_atomic(path, bank)


def _remove_theory(rel: Optional[str]):
    if not rel:
        return
    path = os.path.join(config.THEORY_MDS_DIR, rel)
    if os.path.isfile(path):
        os.remove(path)
    meta = load_json_safe(_theory_meta(), default={}) or {}
    if rel in meta:
        meta.pop(rel)
        save_json_atomic(_theory_meta(), meta)


# ---- publish --------------------------------------------------------------------------

def publish(item: dict, save: bool = True) -> dict:
    from acumen_core.flashcards import build_card, canonical_subtopic, remove_card, upsert_card

    if item["status"] not in ("approved", "published"):
        raise PublishError(f"{item['id']} is {item['status']} — approve it first")
    review = item.get("review") or {}
    ver = next((v for v in item["versions"] if v["v"] == review.get("version")), None)
    if not ver or ver["hash"] != review.get("hash") or review.get("stale"):
        raise PublishError("approval does not match a current version — re-approve")
    pkg, parts = ver["package"], review["parts"]
    prov = _provenance(item, ver)
    prev = item.get("published") or {}
    system = item.get("system") or pkg.get("system") or "General"
    subtopic = canonical_subtopic(system, item.get("subtopic") or pkg.get("subtopic")) or system

    # 1. theory answer
    rel = None
    if parts.get("answer"):
        rel = f"{_safe(system)}/{_safe(subtopic)}/qna-{item['id']}.md"
        if prev.get("theory_rel") and prev["theory_rel"] != rel:
            _remove_theory(prev["theory_rel"])
        path = os.path.join(config.THEORY_MDS_DIR, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            f.write(_theory_md(item, pkg, prov))
        os.replace(path + ".tmp", path)
        meta = load_json_safe(_theory_meta(), default={}) or {}
        meta[rel] = {"title": pkg.get("title") or item["question"][:80], "system": system, "subtopic": subtopic,
                     "original": os.path.basename(rel), "processed_at": store.now(), "source": "studio",
                     "studio_id": item["id"]}
        save_json_atomic(_theory_meta(), meta)
    else:
        _remove_theory(prev.get("theory_rel"))

    # 2. flashcards — reuse ids by position so bookmarks/SRS survive republishing
    prev_ids = list(prev.get("flashcard_ids") or [])
    new_ids = []
    for j, idx in enumerate(parts.get("flashcards") or []):
        c = pkg["flashcards"][idx]
        card = build_card(c.get("front"), c.get("back"), system, subtopic, tags=[subtopic], source="studio",
                          source_file=f"studio:{item['id']}", data={"studio": prov, "question": item["question"]},
                          card_id=prev_ids[j] if j < len(prev_ids) else None)
        upsert_card(card)
        new_ids.append(card["id"])
    for stale in prev_ids[len(new_ids):]:
        remove_card(stale)

    # 3. question bank
    bank = []
    base = {"subject": item["subject"], "system": system, "subtopic": subtopic, "tier": "free",
            "status": "published", "studio": prov, "refs": [f"theory:{rel}"] if rel else []}
    if parts.get("answer"):
        if item.get("options"):
            bank.append({**base, "id": f"{item['id']}-u", "kind": "mcq_single" if len(pkg.get("mcq_key") or []) <= 1 else "mcq_multi",
                         "stem": item["question"], "options": item["options"],
                         "answer": pkg.get("mcq_key") or item.get("given_key") or [],
                         "explanation": pkg.get("answer_md", ""), "difficulty": 3})
        else:
            bank.append({**base, "id": f"{item['id']}-w", "kind": WRITTEN_KIND.get(item["qtype"], "written_short"),
                         "stem": item["question"], "marks": item.get("marks"), "rubric": pkg.get("rubric") or [],
                         "model_answer": pkg.get("answer_md", ""), "explanation": "\n".join(pkg.get("key_points") or []),
                         "difficulty": 4 if item["qtype"] == "long" else 3})
    for n, idx in enumerate(parts.get("mcqs") or []):
        m = pkg["mcqs"][idx]
        bank.append({**base, "id": f"{item['id']}-m{n}", "kind": "mcq_single", "stem": m["stem"],
                     "options": m["options"], "answer": m["answer"], "explanation": m.get("explanation", ""),
                     "difficulty": m.get("difficulty", 3)})
    _write_bank(item["subject"], item["id"], bank)

    item["published"] = {"version": ver["v"], "at": store.now(), "theory_rel": rel,
                         "flashcard_ids": new_ids, "question_ids": [q["id"] for q in bank]}
    store.transition(item, "published", review["by"], f"v{ver['v']}: answer={bool(rel)}, "
                                                       f"{len(new_ids)} cards, {len(bank)} questions")
    if save:
        store.save(item)
    return item


def unpublish(item: dict, save: bool = True) -> dict:
    from acumen_core.flashcards import remove_card
    prev = item.get("published") or {}
    _remove_theory(prev.get("theory_rel"))
    for cid in prev.get("flashcard_ids") or []:
        remove_card(cid)
    _write_bank(item["subject"], item["id"], [])
    item["published"] = None
    store.log(item, "unpublished")
    if save:
        store.save(item)
    return item


def publish_approved(subject: str = "") -> Dict[str, list]:
    res = {"published": [], "failed": []}
    for it in store.all_items(subject):
        if it["status"] == "approved":
            try:
                publish(it)
                res["published"].append(it["id"])
            except Exception as e:
                res["failed"].append({"id": it["id"], "error": str(e)})
    return res
