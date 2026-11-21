"""Library retrieval for Studio — excerpts are HINTS, not ground truth.

BM25 over papers/guidelines (sent_summaries payloads), pearls and theory
notes. Pure Python, built once per process (a few thousand docs → <1 s).
Same-system documents get a mild boost.
"""
from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from typing import Dict, List, Optional

from acumen_core import config

_STOP = set("""a an the of and or to in on for with by from at as is are was were be been this that these those
which what when how why who whom whose discuss describe write short note notes on about its it into than then
management approach role patient patients define definition explain enumerate list mention outline briefly
classify classification principles recent advances""".split())
_TOK = re.compile(r"[a-z0-9]+(?:[-/][a-z0-9]+)*")


def tokenize(text: str) -> List[str]:
    return [t for t in _TOK.findall((text or "").lower()) if t not in _STOP and len(t) > 1]


class Library:
    def __init__(self, docs: List[dict]):
        self.docs = docs
        self.tf = [Counter(tokenize(d["title"] + " " + d["title"] + " " + d["text"])) for d in docs]
        self.len = [sum(c.values()) for c in self.tf]
        self.avg = (sum(self.len) / len(self.len)) if self.len else 1.0
        df: Counter = Counter()
        for c in self.tf:
            df.update(c.keys())
        n = len(docs) or 1
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int = 6, system: str = "", k1: float = 1.4, b: float = 0.75) -> List[dict]:
        q = tokenize(query)
        if not q or not self.docs:
            return []
        scores = []
        for i, tf in enumerate(self.tf):
            s = 0.0
            for t in q:
                f = tf.get(t)
                if f:
                    s += self.idf.get(t, 0) * f * (k1 + 1) / (f + k1 * (1 - b + b * self.len[i] / self.avg))
            if s > 0:
                if system and self.docs[i].get("system") == system:
                    s *= 1.2
                scores.append((s, i))
        scores.sort(reverse=True)
        out, seen_titles = [], set()
        for s, i in scores:
            d = self.docs[i]
            key = (d["kind"], d["title"].lower()[:80])
            if key in seen_titles:      # several pearls from one paper → keep the best
                continue
            seen_titles.add(key)
            out.append({**d, "score": round(s, 2)})
            if len(out) >= k:
                break
        return out


def _pearl_docs() -> List[dict]:
    path = os.path.join(config.PROJECT_DIR, "pearls.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            pearls = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    out = []
    for p in pearls if isinstance(pearls, list) else []:
        txt = str(p.get("pearl") or "").strip()
        if not txt:
            continue
        out.append({"id": f"pearl:{p.get('id')}", "kind": "pearl", "system": p.get("system", ""),
                    "title": str(p.get("source_paper") or "")[:200], "text": txt,
                    "year_hint": str(p.get("timestamp", ""))[-10:]})
    return out


def build_library() -> Library:
    from acumen_core import linking
    docs: List[dict] = []
    for e in linking.summaries_entities() + linking.theory_entities():
        docs.append({"id": e["id"], "kind": e["kind"], "system": e.get("system", ""),
                     "title": e.get("title", ""), "text": e.get("excerpt", "")})
    docs += _pearl_docs()
    return Library(docs)


_LIB: Optional[Library] = None


def library() -> Library:
    global _LIB
    if _LIB is None:
        _LIB = build_library()
    return _LIB


def context_for(item: dict, k: int = None) -> List[dict]:
    k = k or config.STUDIO_CONTEXT_K
    hits = library().search(item["question"], k=k, system=item.get("system", ""))
    return [{"id": h["id"], "kind": h["kind"], "title": h["title"], "system": h.get("system", ""),
             "excerpt": h["text"][:900], "score": h["score"]} for h in hits]
