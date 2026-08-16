"""
linking.py - Cross-link papers, guidelines, theory notes, and flashcard decks.

Hybrid approach:
  1. LLM assigns topic tags (hashtag backbone) to each entity, normalized
     against the subtopics.json vocabulary where possible + freeform concepts.
  2. A candidate shortlist is built from same-system / same-subtopic /
     shared-tag entities so the edge pass stays bounded.
  3. An LLM edge pass picks the top-K relations from the shortlist with a
     fixed reason label (see RELATED_REASON_LABELS in config).
  4. Edges are persisted in output_files/related_links.json:
        entities: { id: { kind, system, type, subtopic, title, tags, links:[{to, kind, reason, weight, updated_at}] } }
  5. A ledger (links_ledger.json) tracks content hashes so re-runs only
     touch NEW or CHANGED entities (incremental linking: new files link to
     new + old files; unchanged entities keep their stored edges).

Canonical entity ids:
    paper:{file_name}            (papers + guidelines from sent_summaries.json)
    theory:{rel/path/under/Theory MDs}
    deck:{System}/{Subtopic}
"""

import hashlib
import json
import os
import re
import time

from .config import (
    FLASHCARDS_DIR,
    FLASHCARD_LLM_API_KEY,
    FLASHCARD_LLM_BASE_URL,
    FLASHCARD_LLM_MODEL,
    JSON_TRACKER_FILE,
    LINKS_LEDGER_FILE,
    LINKING_LLM_MODEL,
    LINKING_MAX_TOKENS,
    LINKING_TEMPERATURE,
    OUTPUT_DIR,
    RELATED_REASON_LABELS,
    RELATED_LINKS_FILE,
    REMOVED_TRACKER_FILE,
    THEORY_MDS_DIR,
)
from .flashcards import load_flashcards_index, load_subtopic_file, normalize_subtopic
from .subtopics_config import get_subtopics_for_system
from .tracking import save_json_atomic


# =====================================================================
# ENTITY IDS
# =====================================================================

def paper_id(file_name):
    return f"paper:{file_name}"


def theory_id(rel_slash):
    return f"theory:{rel_slash}"


def deck_id(system, subtopic):
    return f"deck:{system}/{subtopic}"


# =====================================================================
# TEXT EXCERPT HELPERS
# =====================================================================

_TEXT_FIELD_ORDER = [
    "one_line_summary", "summary", "abstract", "key_pearls", "pearls",
    "recommendation_blocks", "bedside_protocol", "strengths_limitations",
    "conclusion", "title", "content", "back",
]


def _collect_text(obj, limit=3000):
    """Best-effort flatten of a summary JSON payload into readable text."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, list):
        return "\n".join(_collect_text(x, limit) for x in obj[:12])
    if not isinstance(obj, dict):
        return ""
    parts = []
    for k in _TEXT_FIELD_ORDER:
        if k in obj and obj[k]:
            val = obj[k]
            if isinstance(val, str):
                parts.append(str(val).strip())
            elif isinstance(val, list):
                parts.extend(str(v).strip() for v in val[:8] if isinstance(v, str) and v.strip())
            elif isinstance(val, dict):
                parts.append(_collect_text(val, limit))
    for k, val in obj.items():
        if k not in _TEXT_FIELD_ORDER and isinstance(val, str) and len(str(val)) > 40:
            parts.append(str(val).strip())
    return "\n".join(p for p in parts if p)[:limit]


def _summary_payload_path(system, type_val, file_name):
    stem = os.path.splitext(file_name)[0]
    return os.path.join(OUTPUT_DIR, system, type_val, f"{stem}.json")


# =====================================================================
# ENTITY CATALOG
# =====================================================================

def summaries_entities():
    """Papers + guidelines from sent_summaries.json (best-effort payload text)."""
    if not os.path.exists(JSON_TRACKER_FILE):
        return []
    try:
        with open(JSON_TRACKER_FILE, "r", encoding="utf-8") as f:
            entries = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    out = []
    for e in entries or []:
        fn = str(e.get("file_name", "")).strip()
        if not fn:
            continue
        system = str(e.get("system", "General")).strip() or "General"
        type_val = str(e.get("type", "Other")).strip() or "Other"
        title = str(e.get("title", "")).strip()
        excerpt = ""
        p = _summary_payload_path(system, type_val, fn)
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    excerpt = _collect_text(json.load(f))
            except (json.JSONDecodeError, OSError):
                excerpt = ""
        if not excerpt:
            excerpt = f"{title} {e.get('authors', '')} {e.get('journal', '')}".strip()
        out.append({
            "id": paper_id(fn),
            "kind": "guideline" if type_val.lower() == "guideline" else "paper",
            "system": system,
            "type": type_val,
            "subtopic": str(e.get("subtopic", "")).strip() or system,
            "title": title,
            "file_name": fn,
            "excerpt": (excerpt or title)[:4000],
        })
    return out


def theory_entities():
    """Theory notes under output_files/Theory MDs/{System}/{Subtopic}/.

    The reserved BOOKS/ subfolder (chaptered books) is skipped — books are
    excluded from cross-linking.
    """
    if not os.path.isdir(THEORY_MDS_DIR):
        return []
    out = []
    for root, dirs, fnames in os.walk(THEORY_MDS_DIR):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        dirs[:] = [d for d in dirs if d.upper() != "BOOKS"]
        for fn in sorted(fnames):
            if fn == "theory_notes_meta.json":
                continue
            path = os.path.join(root, fn)
            if not os.path.isfile(path):
                continue
            rel = os.path.relpath(path, THEORY_MDS_DIR)
            rel_slash = rel.replace(os.sep, "/")
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    md = f.read()
            except OSError:
                continue
            parts = rel.split(os.sep)
            system = parts[0] if len(parts) > 1 else "General"
            subtopic = parts[1] if len(parts) > 1 else "General"
            body = re.sub(r"^\s*#{1,6}\s+.+?$", "", md, flags=re.M)
            body = re.sub(r"^\s*(<img[^>]*>|\!\[[^\]]*\]\([^)]*\))\s*$", "", body, flags=re.M)
            out.append({
                "id": theory_id(rel_slash),
                "kind": "theory",
                "system": system,
                "type": "Theory",
                "subtopic": subtopic,
                "title": os.path.splitext(fn)[0].replace("_", " "),
                "file_name": rel_slash,
                "excerpt": (body or md).strip()[:4000],
            })
    return out


def deck_entities():
    """Flashcard decks from the unified store (deck-level granularity)."""
    try:
        idx = load_flashcards_index()
    except Exception:
        return []
    out = []
    for system in idx.get("systems", {}):
        for subtopic in idx["systems"][system]:
            data = load_subtopic_file(system, subtopic)
            cards = (data or {}).get("cards") or []
            if not cards:
                continue
            backs = []
            for c in cards:
                b = (c.get("back") or "").strip()
                if b:
                    backs.append(b[:600])
                if sum(len(x) for x in backs) >= 3000:
                    break
            title = subtopic
            out.append({
                "id": deck_id(system, subtopic),
                "kind": "flashcard_deck",
                "system": system,
                "type": "Flashcards",
                "subtopic": subtopic,
                "title": title,
                "file_name": f"{system}/{subtopic}",
                "excerpt": (f"Deck: {system} / {subtopic}\n" + "\n\n".join(backs))[:4000],
            })
    return out


def entity_catalog():
    """Full catalog: papers + guidelines + theory notes + flashcard decks."""
    catalog = summaries_entities() + theory_entities() + deck_entities()
    return catalog


# =====================================================================
# CONTENT SIGNATURE (ledger key)
# =====================================================================

def content_signature(entity):
    h = hashlib.sha256()
    h.update(json.dumps({
        "id": entity.get("id"),
        "title": entity.get("title", ""),
        "system": entity.get("system", ""),
        "type": entity.get("type", ""),
        "subtopic": entity.get("subtopic", ""),
        "excerpt": (entity.get("excerpt") or "")[:4000],
    }, sort_keys=True).encode("utf-8"))
    return h.hexdigest()


# =====================================================================
# LEDGER
# =====================================================================

def load_ledger():
    if not os.path.exists(LINKS_LEDGER_FILE):
        return {}
    try:
        with open(LINKS_LEDGER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_ledger(ledger):
    save_json_atomic(LINKS_LEDGER_FILE, ledger)


# =====================================================================
# RELATED LINKS STORE
# =====================================================================

def load_related_links():
    if not os.path.exists(RELATED_LINKS_FILE):
        return {"version": 1, "generated_at": "", "entity_count": 0, "entities": {}}
    try:
        with open(RELATED_LINKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "entities" in data:
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"version": 1, "generated_at": "", "entity_count": 0, "entities": {}}


def save_related_links(links):
    links["version"] = 1
    links["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    links["entity_count"] = len(links.get("entities", {}))
    save_json_atomic(RELATED_LINKS_FILE, links)


def tags_from_store(links):
    """id -> stored tags (baseline for candidate scoring)."""
    tags = {}
    for eid, ent in (links.get("entities") or {}).items():
        t = ent.get("tags") or []
        tags[eid] = [x for x in t if isinstance(x, str) and x.strip()]
    return tags


# =====================================================================
# CHEAP LINKING LLM CALL (default tag/edge engine)
# =====================================================================

def _linking_call(system_prompt, user_prompt, verbose=False, json_mode=True, max_tokens=None):
    """Default cheap call for tag/edge passes: LINKING_LLM_MODEL through the
    flashcard key/endpoint (OpenRouter by default). Falls back to flashcard_llm
    (FLASHCARD_LLM_MODEL) if LINKING_LLM_MODEL is unusable."""
    from .llm import execute_openai_compat
    model = LINKING_LLM_MODEL
    if model:
        try:
            return execute_openai_compat(
                system_prompt, user_prompt,
                api_key=FLASHCARD_LLM_API_KEY,
                model=model,
                base_url=FLASHCARD_LLM_BASE_URL or None,
                temperature=LINKING_TEMPERATURE,
                max_tokens=max_tokens or LINKING_MAX_TOKENS,
                json_mode=json_mode,
            )
        except Exception:
            pass
    from .flashcards import flashcard_llm
    return flashcard_llm(system_prompt, user_prompt, json_mode=json_mode, verbose=verbose,
                         max_tokens=max_tokens or LINKING_MAX_TOKENS)


# =====================================================================
# TAG ASSIGNMENT (hashtag backbone)
# =====================================================================

TAG_SYSTEM_PROMPT = """You assign topic hashtags to a medical learning resource (a paper, guideline, theory note, or flashcard deck).

Rules:
- Prefer tags from the provided vocabulary for the item's specialty — use the EXACT vocabulary wording (case-insensitive match is fine).
- Add at most 2 freeform clinical concepts as extra hashtags (short noun phrases) that the vocabulary misses, if genuinely needed.
- 1 to 6 tags total. No hashes (#) in output. No preamble.

Return ONLY valid JSON: {{"tags": ["Tag One", "Tag Two"]}}"""


def assign_tags(entity, verbose=False, api_key=None, model=None, base_url=None, llm="openrouter"):
    """LLM-assign topic tags for one entity. Returns a normalized tag list.
    Vocab matches are exact-normalized; freeform tags are kept as-is.
    On LLM failure returns an empty list (caller falls back to scoring only)."""
    from .llm import execute_openai_compat, execute_with_gemini

    system_name = entity.get("system", "General")
    vocab = get_subtopics_for_system(system_name) or []
    if entity.get("kind") == "theory":
        vocab_extra = []
        for cand in [entity.get("system"), entity.get("subtopic")]:
            n = cand or ""
            if n and n not in vocab and n not in vocab_extra:
                vocab_extra.append(n)
        vocab = vocab + vocab_extra
    vocab_str = "\n".join(f"{i+1}. {v}" for i, v in enumerate(vocab)) if vocab else "(no vocabulary available)"

    user_prompt = (
        f"Specialty: {system_name}\n"
        f"Type: {entity.get('type', '')}\n"
        f"Title: {entity.get('title', '')}\n"
        f"Subtopic: {entity.get('subtopic', '')}\n"
        f"Vocabulary for {system_name}:\n{vocab_str}\n\n"
        f"Content excerpt:\n{(entity.get('excerpt') or '')[:2500]}"
    )

    try:
        if api_key or model:
            result = execute_openai_compat(
                TAG_SYSTEM_PROMPT, user_prompt,
                api_key=api_key, model=model, base_url=base_url,
                temperature=LINKING_TEMPERATURE, max_tokens=LINKING_MAX_TOKENS,
                json_mode=True,
            )
        elif llm == "gemini":
            result = execute_with_gemini(TAG_SYSTEM_PROMPT, user_prompt, "linking")
        else:
            result = _linking_call(TAG_SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        if verbose:
            print(f"    [X] Tagging failed for {entity.get('id')}: {e}")
        return []

    if isinstance(result, str):
        stripped = result.strip()
        if stripped.startswith(("{")):
            try:
                result = json.loads(stripped)
            except json.JSONDecodeError:
                m = re.search(r'\{.*"tags".*\}', stripped, re.DOTALL)
                if m:
                    try:
                        result = json.loads(m.group(0))
                    except json.JSONDecodeError:
                        return []
    raw = (result or {}).get("tags") if isinstance(result, dict) else None
    if not isinstance(raw, list):
        return []

    tags = []
    for cand in raw:
        c = str(cand or "").strip().lstrip("#").strip()
        if not c or len(c) > 60:
            continue
        if c.lower() in {t.lower() for t in tags}:
            continue
        norm = None
        for v in vocab:
            if v.lower() == c.lower():
                norm = v
                break
        if not norm and vocab:
            norm = normalize_subtopic(system_name, c)
        tags.append(norm or c)
        if len(tags) >= 6:
            break
    return tags


# =====================================================================
# CANDIDATE SHORTLIST (bounded edge pass)
# =====================================================================

def candidate_shortlist(entity, catalog, all_tags, max_candidates=30):
    """Score every other entity: same system +3, same subtopic +4, shared
    tag +2 each. Returns sorted (score, candidate) list capped at max."""
    eid = entity.get("id")
    my_tags = set(t.lower() for t in (all_tags.get(eid) or []))
    my_sub = str(entity.get("subtopic", "")).lower()
    my_sys = str(entity.get("system", "")).lower()
    scored = []
    for c in catalog:
        if c.get("id") == eid:
            continue
        score = 0
        csys = str(c.get("system", "")).lower()
        csub = str(c.get("subtopic", "")).lower()
        if csys and csys == my_sys:
            score += 3
        if csub and my_sub and csub == my_sub:
            score += 4
        ctags = set(t.lower() for t in (all_tags.get(c.get("id")) or []))
        shared = my_tags & ctags
        score += 2 * len(shared)
        if score > 0:
            scored.append((score, c, sorted(shared)[:3]))
    scored.sort(key=lambda x: (-x[0], x[1].get("title", "")))
    return scored[:max_candidates]


# =====================================================================
# LLM EDGE PICK (labeled recommendations)
# =====================================================================

EDGE_SYSTEM_PROMPT = """You recommend related learning resources for one clinical item.

Below is the source item followed by a numbered candidate list. Pick the 3 to 6 most useful candidates to study alongside it. Base the decision on clinical relevance and synergy, not just identical wording.

Reason labels — use ONLY one of these exact strings:
{labels}

Return ONLY valid JSON: {{"links": [{{"index": 0, "reason": "same topic"}}]}} — at most 6 entries, indices from the candidate list. No preamble."""


def _normalize_reason(raw):
    r = str(raw or "").strip().lower()
    for label in RELATED_REASON_LABELS:
        if label.lower() == r or label.lower() in r:
            return label
    return "same topic"


def llm_pick_edges(entity, candidates, verbose=False, api_key=None, model=None, base_url=None, llm="openrouter"):
    """One LLM call: pick top relations from the shortlist with reason labels.
    Returns list of {to, kind, reason, weight}. Empty list on failure (caller
    falls back to score-based edges)."""
    from .llm import execute_openai_compat, execute_with_gemini

    if not candidates:
        return []

    labels_str = "\n".join(f"- {l}" for l in RELATED_REASON_LABELS)
    system_prompt = EDGE_SYSTEM_PROMPT.format(labels=labels_str)

    lines = [f"SOURCE ITEM:\nType: {entity.get('type')} | Specialty: {entity.get('system')} | Subtopic: {entity.get('subtopic')}\nTitle: {entity.get('title')}\n{(entity.get('excerpt') or '')[:1500]}"]
    lines.append("\nCANDIDATES:")
    for i, (score, c, shared) in enumerate(candidates):
        tag_str = ", ".join(shared) if shared else ""
        lines.append(
            f"[{i}] {c.get('kind')} | {c.get('system')} | {c.get('type')} | {c.get('subtopic')}\n"
            f"    Title: {c.get('title')}\n"
            f"    Shared topics: {tag_str or '-'}\n"
            f"    Snippet: {(c.get('excerpt') or '')[:400]}"
        )
    user_prompt = "\n".join(lines)

    try:
        if api_key or model:
            result = execute_openai_compat(
                system_prompt, user_prompt,
                api_key=api_key, model=model, base_url=base_url,
                temperature=LINKING_TEMPERATURE, max_tokens=LINKING_MAX_TOKENS,
                json_mode=True,
            )
        elif llm == "gemini":
            result = execute_with_gemini(system_prompt, user_prompt, "linking")
        else:
            result = _linking_call(system_prompt, user_prompt)
    except Exception as e:
        if verbose:
            print(f"    [X] Edge pass failed for {entity.get('id')}: {e}")
        return []

    if isinstance(result, str):
        stripped = result.strip()
        if stripped.startswith("{"):
            try:
                result = json.loads(stripped)
            except json.JSONDecodeError:
                m = re.search(r'\{.*"links".*\}', stripped, re.DOTALL)
                if m:
                    try:
                        result = json.loads(m.group(0))
                    except json.JSONDecodeError:
                        return []

    raw_links = (result or {}).get("links") if isinstance(result, dict) else None
    if not isinstance(raw_links, list):
        return []

    edges = []
    seen = set()
    for lk in raw_links:
        if not isinstance(lk, dict):
            continue
        try:
            idx = int(lk.get("index"))
        except (TypeError, ValueError):
            continue
        if idx < 0 or idx >= len(candidates):
            continue
        score, c, _ = candidates[idx]
        to_id = c.get("id")
        if to_id in seen:
            continue
        seen.add(to_id)
        edges.append({
            "to": to_id,
            "kind": c.get("kind"),
            "reason": _normalize_reason(lk.get("reason")),
            "weight": round(min(0.99, 0.5 + 0.05 * score), 2),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
    return edges


def fallback_edges(entity, candidates, max_edges=5):
    """Score-based fallback when the LLM edge pass fails."""
    edges = []
    for score, c, _ in candidates[:max_edges]:
        edges.append({
            "to": c.get("id"),
            "kind": c.get("kind"),
            "reason": "same topic" if score >= 4 else "shared concept",
            "weight": round(min(0.95, 0.4 + 0.05 * score), 2),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
    return edges


# =====================================================================
# DERIVED REVERSE INDEX (for the portal modal)
# =====================================================================

def related_index(links):
    """Merge forward + reverse edges into one lookup: id -> [{to, kind, reason, weight}].
    Forward edges (from the entity itself) are preferred; reverse edges fill gaps.
    Self-loops and duplicates are dropped. Unrelated ids get empty lists."""
    entities = links.get("entities") or {}
    merged = {eid: [] for eid in entities}
    seen = {}
    for eid, ent in entities.items():
        for lb in ent.get("links") or []:
            t = lb.get("to")
            if not t or t == eid or t not in entities:
                continue
            key = (eid, t)
            if key not in seen:
                seen[key] = 0
            seen[key] += 1
            merged.setdefault(eid, []).append(dict(lb))
            merged.setdefault(t, []).append({
                "to": eid,
                "kind": ent.get("kind"),
                "reason": lb.get("reason"),
                "weight": lb.get("weight"),
                "updated_at": lb.get("updated_at"),
            })
    out = {}
    for eid, lst in merged.items():
        dedup = {}
        for lb in lst:
            to = lb.get("to")
            cur = dedup.get(to)
            if cur is None or (cur.get("updated_at") or "") < (lb.get("updated_at") or ""):
                dedup[to] = lb
        lst = sorted(dedup.values(), key=lambda x: -(x.get("weight") or 0))
        out[eid] = lst
    return out


def removed_entity_ids():
    """Ids no longer present (deleted papers ledger)."""
    ids = set()
    if os.path.exists(REMOVED_TRACKER_FILE):
        try:
            with open(REMOVED_TRACKER_FILE, "r", encoding="utf-8") as f:
                for e in json.load(f) or []:
                    fn = str(e.get("file_name", "")).strip()
                    if fn:
                        ids.add(paper_id(fn))
        except (json.JSONDecodeError, OSError):
            pass
    return ids


def log_line(msg):
    from .config import LINKER_LOG_FILE
    try:
        with open(LINKER_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except OSError:
        pass
