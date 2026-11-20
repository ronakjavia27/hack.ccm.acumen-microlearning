"""Read-only content loaders: question bank, theory modules, video catalog.

Content is file-based (same as the rest of the repo — authored/generated,
committed, deployed with the app). Empty directories simply mean "no content
yet"; with USE_SAMPLE_DATA on, demo items from sample_data/ are added so the
skeleton is clickable.

Question schema (output_files/question_bank/{Subject}/*.json — a JSON list):
    {
      "id": "ccm-sepsis-0001",            # stable, globally unique
      "subject": "ccm",                   # key in config.SUBJECTS
      "system": "Sepsis",                 # subtopics.json key
      "subtopic": "Fluid resuscitation",
      "kind": "mcq_single" | "mcq_multi" | "written_short" | "written_long" | "image_mcq" | "viva",
      "stem": "...", "options": ["..."], "answer": [0],   # indexes (mcq) | null (written)
      "rubric": [{"point": "...", "keywords": ["..."], "marks": 1}],   # written / viva
      "explanation": "...", "difficulty": 1-5, "tags": [], "media": [],
      "refs": ["paper:<file>.json", "flashcard:<uuid>", "video:<id>"],
      "tier": "free" | "pro", "status": "draft" | "published" | "sample"
    }
"""
from __future__ import annotations

import glob
import json
import os
from functools import lru_cache
from typing import Dict, List, Optional

from . import config


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _sample(name):
    if not config.USE_SAMPLE_DATA:
        return []
    data = _read_json(os.path.join(config.SAMPLE_DIR, name))
    return data if isinstance(data, list) else []


# ---- questions ---------------------------------------------------------------

@lru_cache(maxsize=1)
def question_bank() -> Dict[str, dict]:
    items: List[dict] = []
    for path in sorted(glob.glob(os.path.join(config.QUESTION_BANK_DIR, "**", "*.json"), recursive=True)):
        data = _read_json(path)
        if isinstance(data, list):
            items.extend(q for q in data if isinstance(q, dict) and q.get("id"))
    items.extend(_sample("questions.json"))
    return {q["id"]: q for q in items if q.get("status", "published") != "draft"}


def questions(subject: str = "", system: str = "", kinds: Optional[List[str]] = None) -> List[dict]:
    out = list(question_bank().values())
    if subject:
        out = [q for q in out if q.get("subject") == subject]
    if system:
        out = [q for q in out if q.get("system") == system]
    if kinds:
        out = [q for q in out if q.get("kind") in kinds]
    return out


def public_question(q: dict) -> dict:
    """Strip answer/explanation/rubric before sending to an exam taker."""
    hidden = {"answer", "explanation", "rubric", "model_answer"}
    return {k: v for k, v in q.items() if k not in hidden}


# ---- theory modules --------------------------------------------------------

@lru_cache(maxsize=1)
def theory_modules() -> Dict[str, dict]:
    items = []
    for path in sorted(glob.glob(os.path.join(config.THEORY_MODULES_DIR, "**", "*.json"), recursive=True)):
        data = _read_json(path)
        if isinstance(data, dict) and data.get("id"):
            items.append(data)
    items.extend(_sample("theory_modules.json"))
    return {m["id"]: m for m in items}


# ---- videos ----------------------------------------------------------------

@lru_cache(maxsize=1)
def video_catalog() -> Dict[str, dict]:
    data = _read_json(config.VIDEO_CATALOG_PATH)
    items = data if isinstance(data, list) else []
    items = items + _sample("videos.json")
    return {v["id"]: v for v in items if isinstance(v, dict) and v.get("id")}


# ---- flashcards (existing unified store) ------------------------------------

@lru_cache(maxsize=1)
def flashcard_index() -> Dict[str, dict]:
    """uuid -> card, from output_files/flashcards/{System}/{Subtopic}.json."""
    out: Dict[str, dict] = {}
    for path in glob.glob(os.path.join(config.FLASHCARD_STORE_DIR, "*", "*.json")):
        deck = _read_json(path)
        if not isinstance(deck, dict):
            continue
        for c in deck.get("cards") or []:
            if isinstance(c, dict) and c.get("id") and c.get("status", "active") == "active":
                out[c["id"]] = {"id": c["id"], "front": c.get("front", ""), "back": c.get("back", ""),
                                "system": c.get("system") or deck.get("system", ""),
                                "subtopic": c.get("subtopic") or deck.get("subtopic", "")}
    return out


def subject_for_system(system: str) -> List[str]:
    return [k for k, v in config.SUBJECTS.items() if system in v["systems"]]


def resolve(ref: str) -> Optional[dict]:
    """Turn an SRS ref into displayable study content (answers included — it's a study card)."""
    kind, _, key = ref.partition(":")
    if kind == "flashcard":
        c = flashcard_index().get(key)
        return {"kind": "flashcard", **c} if c else None
    if kind == "q":
        q = question_bank().get(key)
        return {"kind": "question", **q} if q else None
    return None  # pearl:/video: resolvers TODO


def reload():
    for f in (question_bank, theory_modules, video_catalog, flashcard_index):
        f.cache_clear()
