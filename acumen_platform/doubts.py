"""Clinical doubt-solving forum (de-identified cases only).

Flow
    1. Client calls /doubts/check while typing → deid findings shown inline.
    2. POST /doubts requires: deid.check ok (no HIGH findings) AND the author's
       `attest_deidentified` tick. MEDIUM findings are auto-redacted.
    3. New posts start `pending` → visible to author + moderators; approved
       posts are public. Trusted users (future: reputation) skip the queue.
    4. Replies follow the same gate. The asker can accept an answer.
    5. Pro: optional AI first-response (clearly labelled, never "accepted").

Images (CXR/echo/USG stills) stay disabled until DICOM tag stripping +
burnt-in-text OCR exist server-side.
"""
from __future__ import annotations

import hashlib
import os
import secrets
from typing import List, Optional

from fastapi import HTTPException

from . import deid
from .store import store, iso

STATUSES = ("pending", "approved", "rejected", "closed")


def _gate(text: str, attested: bool) -> str:
    if not attested:
        raise HTTPException(422, {"error": "attestation_required",
                                  "message": "Confirm the case contains no patient identifiers."})
    res = deid.check(text)
    if not res["ok"]:
        raise HTTPException(422, {"error": "identifiers_found", "findings": res["findings"]})
    return res["redacted_preview"]


def _author_handle(email: str) -> str:
    """Stable pseudonym so the forum never shows emails/real names."""
    salt = os.environ.get("DOUBTS_HANDLE_SALT", "hackccm")
    return "dr_" + hashlib.sha256(f"{salt}:{email}".encode()).hexdigest()[:6]


def create(email: str, title: str, body: str, subject: str, system: str = "", tags: Optional[List[str]] = None,
           attest: bool = False, auto_approve: bool = False) -> dict:
    title = _gate(title, attest)
    body = _gate(body, attest)
    did = secrets.token_urlsafe(8)
    rec = {"id": did, "author": email, "handle": _author_handle(email), "title": title[:200], "body": body[:8000],
           "subject": subject, "system": system, "tags": (tags or [])[:8],
           "status": "approved" if auto_approve else "pending", "created_at": iso(),
           "replies": [], "votes": {}, "reports": [], "accepted_reply": None}
    store.put("doubt", did, value=rec)
    return rec


def public(rec: dict, viewer: str = "", is_mod: bool = False) -> dict:
    out = {k: v for k, v in rec.items() if k not in ("author", "votes", "reports")}
    out["score"] = sum(rec.get("votes", {}).values())
    out["mine"] = rec.get("author") == viewer
    out["replies"] = [{k: v for k, v in r.items() if k not in ("author",)} | {"mine": r.get("author") == viewer}
                      for r in rec.get("replies", []) if r.get("status") == "approved" or is_mod or r.get("author") == viewer]
    if is_mod:
        out["reports"] = rec.get("reports", [])
    return out


def get(did: str, viewer: str, is_mod: bool) -> dict:
    rec = store.get("doubt", did)
    if not rec or (rec["status"] != "approved" and rec["author"] != viewer and not is_mod):
        raise HTTPException(404, "not found")
    return rec


def listing(viewer: str, is_mod: bool, subject: str = "", status: str = "approved") -> List[dict]:
    rows = []
    for rec in store.list("doubt"):
        visible = rec["status"] == "approved" or rec["author"] == viewer or is_mod
        if not visible or (subject and rec.get("subject") != subject):
            continue
        if status and status != "all" and rec["status"] != status and rec["author"] != viewer:
            continue
        p = public(rec, viewer, is_mod)
        p["n_replies"] = len(p.pop("replies"))
        p["body"] = p["body"][:280]
        rows.append(p)
    return sorted(rows, key=lambda r: r["created_at"], reverse=True)


def reply(did: str, email: str, body: str, attest: bool, auto_approve: bool = False, ai: bool = False) -> dict:
    rec = get(did, email, False)
    body = _gate(body, attest)
    r = {"id": secrets.token_urlsafe(6), "author": email, "handle": "AI assistant" if ai else _author_handle(email),
         "body": body[:8000], "ai": ai, "created_at": iso(), "status": "approved" if auto_approve else "pending"}
    rec["replies"].append(r)
    store.put("doubt", did, value=rec)
    return r


def vote(did: str, email: str, value: int) -> int:
    rec = get(did, email, False)
    rec["votes"][email] = max(-1, min(1, int(value)))
    store.put("doubt", did, value=rec)
    return sum(rec["votes"].values())


def report(did: str, email: str, reason: str):
    rec = get(did, email, False)
    rec["reports"].append({"by": email, "reason": reason[:500], "at": iso()})
    if len(rec["reports"]) >= 3:
        rec["status"] = "pending"   # auto-hide for moderator review
    store.put("doubt", did, value=rec)


def moderate(did: str, status: str, reply_id: Optional[str] = None):
    if status not in STATUSES:
        raise HTTPException(400, "bad status")
    rec = store.get("doubt", did)
    if not rec:
        raise HTTPException(404, "not found")
    if reply_id:
        for r in rec["replies"]:
            if r["id"] == reply_id:
                r["status"] = status
    else:
        rec["status"] = status
    store.put("doubt", did, value=rec)
    return rec


def accept(did: str, email: str, reply_id: str):
    rec = get(did, email, False)
    if rec["author"] != email:
        raise HTTPException(403, "only the asker can accept")
    if not any(r["id"] == reply_id and not r.get("ai") for r in rec["replies"]):
        raise HTTPException(400, "reply not found (AI replies can't be accepted)")
    rec["accepted_reply"] = reply_id
    store.put("doubt", did, value=rec)
