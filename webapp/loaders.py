"""Readers for the content files the portal serves (ledger, pearls, trials, flashcards, theory notes, related links)."""
import json
import logging
import os
import re
from datetime import datetime

from webapp.config import (
    CONDENSED_TRIALS_DIR,
    ESBICM_INDEX_PATH,
    JSON_TRACKER_FILE,
    OUTPUT_DIR,
    PEARLS_JSON,
)

log = logging.getLogger("hackccm")


# ---- End auth ----

def load_approved_ledger():
    if not os.path.exists(JSON_TRACKER_FILE):
        return []
    try:
        with open(JSON_TRACKER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return []


def load_pearls():
    if not os.path.exists(PEARLS_JSON):
        return []
    try:
        with open(PEARLS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        expected = ["id", "timestamp", "source_paper", "doi", "author", "system", "type", "pearl", "remarks", "file_name", "topic"]
        for entry in data:
            for k in expected:
                if k not in entry:
                    entry[k] = ""
        # Backfill system from source summaries
        try:
            with open("sent_summaries.json", "r", encoding="utf-8") as f:
                summaries = json.load(f)
            summary_map = {}
            for s in summaries:
                fn = str(s.get("file_name", "")).strip()
                sys = str(s.get("system", "")).strip()
                if fn and sys:
                    summary_map[fn] = sys
            for p in data:
                fn = str(p.get("file_name", "")).strip()
                fn_pdf = fn[:-5] + ".pdf" if fn.endswith(".json") else fn
                cur = str(p.get("system", "")).strip()
                if fn_pdf in summary_map and not cur:
                    p["system"] = summary_map[fn_pdf]
        except Exception:
            pass
        return data
    except (json.JSONDecodeError, Exception):
        return []


def load_trial_index():
    if not os.path.exists(ESBICM_INDEX_PATH):
        return []
    try:
        with open(ESBICM_INDEX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return []


def load_flashcard_decks():
    """Load flashcard decks from the unified store (output_files/flashcards/).
    One deck per (system, subtopic) file; cards carry explicit front/back."""
    try:
        from acumen_core import flashcards as fc
    except Exception:
        return []
    decks = []
    try:
        idx = fc.load_flashcards_index()
    except Exception:
        return []
    for system in idx.get("systems", {}):
        for subtopic in idx["systems"][system]:
            data = fc.load_subtopic_file(system, subtopic)
            if not data or not data.get("cards"):
                continue
            cards = []
            for c in data["cards"]:
                if not isinstance(c, dict):
                    continue
                cards.append({
                    "id": str(c.get("id", "")),
                    "subtopic": str((c.get("data") or {}).get("original_subtopic") or c.get("subtopic", "")),
                    "front": str(c.get("front", "")),
                    "back": str(c.get("back", "")),
                    "status": str(c.get("status", "pending")),
                    "tags": sorted({str(t) for t in (c.get("tags") or []) if isinstance(t, str) and str(t).strip()}),
                })
            if cards:
                decks.append({
                    "id": f"{system}/{subtopic}",
                    "specialty": system,
                    "title": subtopic,
                    "cards": cards,
                    "subtopics": sorted({t for c in cards for t in c["tags"]}),
                })
    return decks


def load_theory_notes():
    """Load Theory Topics: every file under output_files/Theory MDs/ (any
    extension) rendered as markdown by the portal. Notes are organized into
    {Specialty}/{Subtopic}/ subfolders (see classify_theory.py); a sidecar
    theory_notes_meta.json provides clean titles + taxonomy overrides."""
    notes = []
    base = os.path.join(OUTPUT_DIR, "Theory MDs")
    if not os.path.isdir(base):
        return notes
    meta = {}
    meta_path = os.path.join(base, "theory_notes_meta.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {}
    for root, dirs, fnames in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        if root == base:
            fnames = [f for f in fnames if f != "theory_notes_meta.json"]
        for fn in sorted(fnames):
            path = os.path.join(root, fn)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    md_in = f.read()
            except Exception:
                continue
            rel = os.path.relpath(path, base)
            rel_slash = rel.replace(os.sep, "/")
            # The reserved BOOKS/ subfolder (chaptered books) is quarantined from
            # the portal for now — skip it so books don't surface as notes.
            if rel_slash.upper().startswith("BOOKS/"):
                continue
            m_entry = meta.get(rel_slash) or {}
            # folder-derived taxonomy (ground truth = folder structure)
            parts = rel.split(os.sep)
            system = m_entry.get("system") or (parts[0] if len(parts) > 1 else "General")
            subtopic = m_entry.get("subtopic") or (parts[1] if len(parts) > 1 else "General")
            # title: manifest > first heading (any level, after any leading img) > cleaned filename
            title = m_entry.get("title") or ""
            if not title:
                body_head = md_in
                if body_head.startswith("<img") and "\n" in body_head:
                    body_head = body_head.split("\n", 1)[1]
                mm = re.search(r"^\s*#{1,6}\s+(.+?)\s*$", body_head, re.M)
                title = mm.group(1).strip() if mm else ""
            if not title:
                title = os.path.splitext(fn)[0].replace("_", " ")
            processed_at = m_entry.get("processed_at") or ""
            date_added = processed_at[:10] if processed_at else datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")
            notes.append({
                "id": fn,
                "title": title,
                "md": md_in,
                "system": system,
                "subtopic": subtopic,
                "rel": rel_slash,
                "date_added": date_added,
            })
    notes.sort(key=lambda n: (n.get("system") or "", n.get("subtopic") or "", n["title"].lower()))
    return notes


def load_related_links():
    """Load output_files/related_links.json (precomputed by acumen_core/linker.py).

    Returns {catalog, index, generated_at, entity_count}:
      catalog = [{id, kind, system, type, subtopic, title, tags}] for every
                known entity — built from the full entity catalog so entries
                that haven't been linked yet still resolve; stored tags from
                the links file are merged in.
      index   = {entity_id: [{to, kind, reason, weight}]} — forward + reverse
                edges merged per entity so both directions resolve instantly."""
    from acumen_core.linking import entity_catalog
    path = os.path.join(OUTPUT_DIR, "related_links.json")
    empty = {"catalog": [], "index": {}, "generated_at": "", "entity_count": 0}
    if not os.path.exists(path):
        return empty
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, Exception):
        return empty
    entities = data.get("entities") or {}
    if not isinstance(entities, dict):
        return empty

    # Full catalog: every known entity (complete even mid-run); merge stored tags
    catalog = []
    try:
        base_catalog = entity_catalog()
    except Exception:
        base_catalog = []
    if base_catalog:
        for ent in base_catalog:
            eid = ent["id"]
            stored = entities.get(eid) or {}
            catalog.append({
                "id": eid,
                "kind": stored.get("kind") or ent.get("kind", ""),
                "system": stored.get("system") or ent.get("system", ""),
                "type": stored.get("type") or ent.get("type", ""),
                "subtopic": stored.get("subtopic") or ent.get("subtopic", ""),
                "title": stored.get("title") or ent.get("title", "") or eid,
                "tags": stored.get("tags") or [],
            })
    else:
        for eid, ent in entities.items():
            catalog.append({
                "id": eid,
                "kind": ent.get("kind", ""),
                "system": ent.get("system", ""),
                "type": ent.get("type", ""),
                "subtopic": ent.get("subtopic", ""),
                "title": ent.get("title", "") or eid,
                "tags": ent.get("tags") or [],
            })
    catalog_ids = {c["id"] for c in catalog}

    index = {}
    for eid, ent in entities.items():
        if eid not in catalog_ids:
            continue
        index.setdefault(eid, [])
        for lb in ent.get("links") or []:
            t = lb.get("to")
            if not t or t == eid or t not in catalog_ids:
                continue
            edge = {
                "to": t,
                "kind": lb.get("kind", ""),
                "reason": lb.get("reason", "same topic"),
                "weight": lb.get("weight", 0.5),
            }
            index.setdefault(eid, []).append(edge)
            index.setdefault(t, []).append(dict(edge, to=eid, kind=ent.get("kind", "")))
    for eid, lst in index.items():
        dedup = {}
        for lb in lst:
            cur = dedup.get(lb["to"])
            if cur is None or (lb.get("weight") or 0) > (cur.get("weight") or 0):
                dedup[lb["to"]] = lb
        index[eid] = sorted(dedup.values(), key=lambda x: -(x.get("weight") or 0))
    return {
        "catalog": catalog,
        "index": index,
        "generated_at": data.get("generated_at", ""),
        "entity_count": data.get("entity_count", 0),
    }


def load_condensed_trial_index():
    if not os.path.exists(CONDENSED_TRIALS_DIR):
        return []
    index = []
    for root, dirs, fnames in os.walk(CONDENSED_TRIALS_DIR):
        for fname in fnames:
            if not fname.endswith(".json"):
                continue
            rel = os.path.relpath(os.path.join(root, fname), CONDENSED_TRIALS_DIR)
            parts = rel.split(os.sep)
            system = parts[0] if len(parts) > 1 else "Other"
            name = os.path.splitext(fname)[0]
            entry = {"system": system, "name": name, "file_rel": rel}
            try:
                with open(os.path.join(root, fname), "r", encoding="utf-8") as f:
                    payload = json.load(f)
                entry["trial_name"] = payload.get("trial_name", "")
                entry["one_liner"] = payload.get("one_liner", "")
                entry["trial_type"] = payload.get("trial_type", "")
                entry["result_category"] = payload.get("result_category", "")
                entry["sample_size"] = payload.get("sample_size", "")
                y = payload.get("year", "")
                entry["year"] = int(y) if y and str(y).isdigit() else 0
                keywords = payload.get("keywords", [])
                entry["keywords_str"] = " ".join(keywords) if isinstance(keywords, list) else str(keywords)
            except Exception:
                pass
            index.append(entry)
    return sorted(index, key=lambda x: x["name"])


def load_condensed_trial(system, name):
    target = os.path.join(CONDENSED_TRIALS_DIR, system, f"{name}.json")
    if not os.path.exists(target):
        return None
    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)
