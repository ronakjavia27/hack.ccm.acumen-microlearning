"""Exams: personalised builder, sessions, grading, mastery tracking.

Exam modes
    practice      — untimed, immediate feedback per question
    personalised  — built from the user's weak areas (see build_personalised)
    mock          — timed, feedback only after submit
    live          — scheduled cohort exam; deadline enforced server-side (see live.py)

Mastery (v2:mastery:<email>) = {"<subject>|<system>|<subtopic>": {"n", "correct", "ema"}}
`ema` is an exponential moving average of correctness (0..1), the single
signal the personaliser and the SRS enrolment both read.
"""
from __future__ import annotations

import random
import secrets
from datetime import timedelta
from typing import Dict, List, Optional

from fastapi import HTTPException

from . import content, srs
from .store import store, utcnow, iso, parse_iso

EMA_ALPHA = 0.3
UNKNOWN_MASTERY = 0.5
BLUEPRINT = {"weak": 0.6, "unseen": 0.3, "review": 0.1}
SUBMIT_GRACE_S = 30
MCQ_KINDS = ("mcq_single", "mcq_multi", "image_mcq")


def area_key(q: dict) -> str:
    return f"{q.get('subject', '')}|{q.get('system', '')}|{q.get('subtopic', '')}"


def get_mastery(email: str) -> Dict[str, dict]:
    return store.get("mastery", email, default={}) or {}


def _update_mastery(email: str, results: List[dict]):
    m = get_mastery(email)
    for r in results:
        if r.get("score") is None:
            continue
        a = m.setdefault(r["area"], {"n": 0, "correct": 0.0, "ema": UNKNOWN_MASTERY})
        a["n"] += 1
        a["correct"] += r["score"]
        a["ema"] = round((1 - EMA_ALPHA) * a["ema"] + EMA_ALPHA * r["score"], 4)
    store.put("mastery", email, value=m)


def seen_ids(email: str) -> Dict[str, str]:
    return store.get("seen", email, default={}) or {}


# ---- personalised builder ---------------------------------------------------

def build_personalised(pool: List[dict], mastery: Dict[str, dict], seen: Dict[str, str], n: int,
                       rng: Optional[random.Random] = None) -> List[dict]:
    """Pick n questions: ~60% weak areas, ~30% never-seen, ~10% strong-area retention.

    Within a bucket, sampling is weighted by weakness (1 - ema) so the weakest
    areas surface most. Difficulty is nudged towards the user's level in that area.
    """
    rng = rng or random.Random()
    if not pool:
        return []

    def ema(q):
        return mastery.get(area_key(q), {}).get("ema", UNKNOWN_MASTERY)

    buckets = {"weak": [], "unseen": [], "review": []}
    for q in pool:
        if q["id"] not in seen:
            buckets["unseen"].append(q)
        elif ema(q) < 0.7:
            buckets["weak"].append(q)
        else:
            buckets["review"].append(q)

    def weight(q):
        target_diff = 1 + 4 * ema(q)
        diff_fit = 1.0 / (1 + abs((q.get("difficulty") or 3) - target_diff))
        return (1.05 - ema(q)) * (0.5 + diff_fit)

    def take(items, k):
        items, out = list(items), []
        while items and len(out) < k:
            ws = [weight(q) for q in items]
            q = rng.choices(items, weights=ws, k=1)[0]
            items.remove(q)
            out.append(q)
        return out

    chosen: List[dict] = []
    for name, frac in BLUEPRINT.items():
        chosen += take([q for q in buckets[name] if q not in chosen], round(n * frac))
    if len(chosen) < n:  # top up from whatever is left
        chosen += take([q for q in pool if q not in chosen], n - len(chosen))
    rng.shuffle(chosen)
    return chosen[:n]


# ---- sessions ---------------------------------------------------------------

def create_session(email: str, mode: str, question_ids: List[str], minutes: Optional[int] = None,
                   subject: str = "", meta: Optional[dict] = None, deadline: Optional[str] = None) -> dict:
    now = utcnow()
    sid = secrets.token_urlsafe(9)
    if deadline is None and minutes:
        deadline = iso(now + timedelta(minutes=minutes))
    sess = {
        "id": sid, "email": email, "mode": mode, "subject": subject,
        "question_ids": question_ids, "answers": {}, "status": "in_progress",
        "started_at": iso(now), "deadline": deadline, "submitted_at": None,
        "result": None, "proctored": bool((meta or {}).get("proctored")), "meta": meta or {},
    }
    store.put("exam", sid, value=sess)
    store.update("exam_index", email, fn=lambda cur: (cur or []) + [sid], default=[])
    return sess


def get_session(sid: str, email: str) -> dict:
    sess = store.get("exam", sid)
    if not sess or sess.get("email") != email:
        raise HTTPException(404, "exam not found")
    return sess


def public_session(sess: dict) -> dict:
    bank = content.question_bank()
    out = {k: v for k, v in sess.items() if k != "email"}
    out["questions"] = [content.public_question(bank[q]) for q in sess["question_ids"] if q in bank]
    return out


def _past_deadline(sess) -> bool:
    return bool(sess.get("deadline")) and utcnow() > parse_iso(sess["deadline"]) + timedelta(seconds=SUBMIT_GRACE_S)


def record_answer(sess: dict, qid: str, answer) -> dict:
    if sess["status"] != "in_progress":
        raise HTTPException(409, "exam already submitted")
    if _past_deadline(sess):
        raise HTTPException(409, "time is up")
    if qid not in sess["question_ids"]:
        raise HTTPException(400, "question not in this exam")
    sess["answers"][qid] = {"value": answer, "at": iso()}
    store.put("exam", sess["id"], value=sess)
    if sess["mode"] == "practice":  # immediate feedback
        q = content.question_bank()[qid]
        return {"saved": True, "feedback": grade_one(q, answer) | {"explanation": q.get("explanation", "")}}
    return {"saved": True}


# ---- grading ----------------------------------------------------------------

def grade_one(q: dict, answer) -> dict:
    kind = q.get("kind", "mcq_single")
    if kind in MCQ_KINDS:
        correct = sorted(q.get("answer") or [])
        given = sorted(answer if isinstance(answer, list) else ([answer] if answer is not None else []))
        if kind == "mcq_multi":
            hits = len(set(given) & set(correct))
            wrong = len(set(given) - set(correct))
            score = max(0.0, (hits - wrong) / max(1, len(correct)))
        else:
            score = 1.0 if given == correct else 0.0
        return {"score": round(score, 3), "correct": correct, "status": "graded"}
    # written / viva: keyword heuristic now, AI rubric grading later
    return grade_written_heuristic(q, answer or "")


def grade_written_heuristic(q: dict, text: str) -> dict:
    """Provisional score from rubric keywords. Replaced by ai_grade_written when wired."""
    rubric = q.get("rubric") or []
    total = sum(r.get("marks", 1) for r in rubric) or 1
    low = str(text).lower()
    got, hits = 0, []
    for r in rubric:
        if any(k.lower() in low for k in r.get("keywords", [])):
            got += r.get("marks", 1)
            hits.append(r.get("point"))
    return {"score": round(got / total, 3), "status": "provisional", "rubric_hits": hits,
            "note": "Keyword-matched preview. AI rubric grading pending (Pro)."}


def ai_grade_written(q: dict, text: str) -> Optional[dict]:
    """TODO: call acumen_core.llm with the rubric + model answer; return
    {"score", "feedback", "rubric": [{point, awarded, comment}]}. Returns None
    until an LLM grading prompt is written and evaluated against faculty marks."""
    return None


def submit(sess: dict, ai_grading: bool = False) -> dict:
    if sess["status"] == "submitted":
        return sess["result"]
    bank = content.question_bank()
    results = []
    for qid in sess["question_ids"]:
        q = bank.get(qid)
        if not q:
            continue
        ans = (sess["answers"].get(qid) or {}).get("value")
        r = grade_one(q, ans)
        if ai_grading and q.get("kind") not in MCQ_KINDS:
            r = ai_grade_written(q, ans or "") or r
        results.append({"qid": qid, "area": area_key(q), "answered": ans is not None, **r,
                        "explanation": q.get("explanation", "")})
    scored = [r["score"] for r in results if r.get("score") is not None]
    result = {
        "score_pct": round(100 * sum(scored) / len(scored), 1) if scored else None,
        "n": len(results), "answered": sum(r["answered"] for r in results),
        "items": results, "late": _past_deadline(sess),
    }
    sess.update(status="submitted", submitted_at=iso(), result=result)
    store.put("exam", sess["id"], value=sess)

    email = sess["email"]
    _update_mastery(email, results)
    store.update("seen", email, fn=lambda cur: {**(cur or {}), **{r["qid"]: iso() for r in results}}, default={})
    # Missed questions flow into spaced repetition automatically.
    missed = [{"ref": f"q:{r['qid']}", "subject": r["area"].split("|")[0], "system": r["area"].split("|")[1]}
              for r in results if (r.get("score") or 0) < 0.6]
    if missed:
        srs.enroll(email, missed)
    return result


def history(email: str, limit: int = 20) -> List[dict]:
    ids = (store.get("exam_index", email, default=[]) or [])[-limit:]
    out = []
    for sid in reversed(ids):
        s = store.get("exam", sid)
        if s:
            out.append({"id": sid, "mode": s["mode"], "subject": s.get("subject"), "status": s["status"],
                        "started_at": s["started_at"], "n": len(s["question_ids"]),
                        "score_pct": (s.get("result") or {}).get("score_pct")})
    return out
