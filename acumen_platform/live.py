"""Live (scheduled) exams.

A LiveExam is a scheduled window everyone sits together. Joining creates a
normal exam session whose deadline is the window end, so timing is enforced
server-side regardless of the client clock.

Realtime bits (countdown sync, live leaderboard, invigilator chat) need
websockets, which Vercel serverless can't hold open — they belong in the
separate realtime service (REALTIME_SERVICE_URL). Until then clients poll.
"""
from __future__ import annotations

import secrets
from datetime import timedelta
from typing import List, Optional

from fastapi import HTTPException

from . import entitlements, exams
from .store import store, utcnow, iso, parse_iso


def create(title: str, subject: str, starts_at: str, duration_min: int, question_ids: List[str],
           created_by: str, tier: str = "free", proctored: bool = False, join_window_min: int = 15,
           cohort: Optional[str] = None) -> dict:
    lid = secrets.token_urlsafe(8)
    rec = {"id": lid, "title": title, "subject": subject, "starts_at": starts_at,
           "duration_min": duration_min, "join_window_min": join_window_min,
           "question_ids": question_ids, "tier": tier, "proctored": proctored,
           "cohort": cohort, "created_by": created_by, "created_at": iso(), "participants": {}}
    store.put("live", lid, value=rec)
    return rec


def _window(rec):
    start = parse_iso(rec["starts_at"])
    return start, start + timedelta(minutes=rec["duration_min"]), start + timedelta(minutes=rec["join_window_min"])


def status_of(rec) -> str:
    start, end, _ = _window(rec)
    now = utcnow()
    return "upcoming" if now < start else ("running" if now <= end else "ended")


def listing() -> List[dict]:
    out = []
    for rec in store.list("live"):
        pub = {k: v for k, v in rec.items() if k not in ("question_ids", "participants")}
        pub["status"] = status_of(rec)
        pub["n_participants"] = len(rec.get("participants", {}))
        out.append(pub)
    return sorted(out, key=lambda r: r["starts_at"])


def join(lid: str, user: dict) -> dict:
    rec = store.get("live", lid)
    if not rec:
        raise HTTPException(404, "live exam not found")
    if rec["tier"] != "free":
        entitlements.require(user, "live_exams_pro")
    if rec["proctored"]:
        entitlements.require(user, "proctored_exams")
    start, end, join_close = _window(rec)
    now = utcnow()
    if now < start:
        raise HTTPException(425, "not started yet")
    if now > join_close:
        raise HTTPException(409, "joining window closed")
    email = user["email"]
    if email in rec["participants"]:
        return exams.public_session(exams.get_session(rec["participants"][email], email))
    sess = exams.create_session(email, "live", rec["question_ids"], subject=rec["subject"],
                                deadline=iso(end), meta={"live_id": lid, "proctored": rec["proctored"]})
    rec["participants"][email] = sess["id"]
    store.put("live", lid, value=rec)   # TODO: not atomic — move participants to Postgres before real cohorts
    return exams.public_session(sess)


def leaderboard(lid: str, top: int = 20) -> List[dict]:
    rec = store.get("live", lid)
    if not rec:
        raise HTTPException(404, "live exam not found")
    rows = []
    for email, sid in rec.get("participants", {}).items():
        s = store.get("exam", sid) or {}
        res = s.get("result") or {}
        if res.get("score_pct") is not None:
            rows.append({"user": email.split("@")[0][:3] + "***", "score_pct": res["score_pct"],
                         "submitted_at": s.get("submitted_at")})
    return sorted(rows, key=lambda r: (-r["score_pct"], r["submitted_at"] or ""))[:top]
