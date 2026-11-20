"""HTTP API for the v2 platform, mounted under /api/v2 (+ the /learn shell page).

mount(app, get_user) is called from revamped_webapp.py. `get_user(request)`
is the portal's existing session lookup, so v2 reuses the same login,
cookies and admin flag — there is one user system, not two.

Status codes used for the paywall: 402 = upgrade/quota, 501 = not built yet.
"""
from __future__ import annotations

import os
import random
from typing import Any, Callable, List, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from . import (billing, config, content, deid, doubts, entitlements, exams, live, notify, proctoring, srs,
               voice)

_GET_USER: Optional[Callable[[Request], Optional[dict]]] = None

router = APIRouter(prefix=config.API_PREFIX, tags=["platform-v2"])


def current_user(request: Request) -> dict:
    user = _GET_USER(request) if _GET_USER else None
    if not user:
        raise HTTPException(401, "Login required")
    return user


def admin_user(user: dict = Depends(current_user)) -> dict:
    if not user.get("is_admin"):
        raise HTTPException(403, "Admin access required")
    return user


def _subject(subject: str) -> str:
    if subject and subject not in config.SUBJECTS:
        raise HTTPException(400, f"unknown subject '{subject}'")
    return subject


# ---- plan / subjects ----------------------------------------------------------

@router.get("/me/plan")
def me_plan(user=Depends(current_user)):
    return entitlements.plan_summary(user)


@router.get("/subjects")
def subjects():
    return [{"key": k, "label": v["label"], "systems": v["systems"], "axes": v.get("axes", [])}
            for k, v in config.SUBJECTS.items()]


# ---- 1. spaced repetition ---------------------------------------------------

class EnrollBody(BaseModel):
    refs: List[Any]


class ReviewBody(BaseModel):
    ref: str
    grade: int = Field(ge=1, le=4)


@router.get("/srs/queue")
def srs_queue(subject: str = "", limit: int = 50, user=Depends(current_user)):
    items = srs.queue(user["email"], _subject(subject), limit=min(limit, 200))
    return [{"state": c, "content": content.resolve(c["ref"])} for c in items]


@router.post("/srs/enroll")
def srs_enroll(body: EnrollBody, user=Depends(current_user)):
    return {"added": srs.enroll(user["email"], body.refs)}


@router.post("/srs/enroll/deck")
def srs_enroll_deck(system: str, subtopic: str = "", subject: str = "", user=Depends(current_user)):
    """Add every card of an existing flashcard deck (System[/Subtopic]) to the user's SRS."""
    cards = [c for c in content.flashcard_index().values()
             if c["system"] == system and (not subtopic or c["subtopic"] == subtopic)]
    subj = _subject(subject) or (content.subject_for_system(system) or [""])[0]
    refs = [{"ref": f"flashcard:{c['id']}", "subject": subj, "system": system} for c in cards]
    return {"added": srs.enroll(user["email"], refs), "deck_size": len(cards)}


@router.post("/srs/review")
def srs_review(body: ReviewBody, user=Depends(current_user)):
    lim = entitlements.limits_of(user).get("srs_reviews_per_day")
    if lim is not None:
        entitlements.consume(user, "srs_reviews_per_day")
    return srs.review(user["email"], body.ref, body.grade)


@router.get("/srs/stats")
def srs_stats(user=Depends(current_user)):
    return srs.stats(user["email"])


# ---- 2. personalised exams + 6/8. MCQ / written ----------------------------

class PersonalisedBody(BaseModel):
    subject: str
    n: int = Field(default=10, ge=1, le=300)
    minutes: Optional[int] = None
    kinds: Optional[List[str]] = None
    mode: str = "personalised"            # personalised | practice | mock
    seed: Optional[int] = None


class AnswerBody(BaseModel):
    qid: str
    answer: Any = None


@router.post("/exams/personalised")
def exam_personalised(body: PersonalisedBody, user=Depends(current_user)):
    subject = _subject(body.subject)
    if body.mode not in ("personalised", "practice", "mock"):
        raise HTTPException(400, "bad mode")
    max_q = entitlements.limits_of(user).get("exam_max_questions") or 20
    n = min(body.n, max_q)
    pool = content.questions(subject=subject, kinds=body.kinds)
    if not pool:
        raise HTTPException(404, "no questions available for this subject yet")
    chosen = exams.build_personalised(pool, exams.get_mastery(user["email"]), exams.seen_ids(user["email"]), n,
                                      rng=random.Random(body.seed) if body.seed is not None else None)
    if body.mode == "personalised":
        entitlements.consume(user, "personalised_exams_per_week")
    sess = exams.create_session(user["email"], body.mode, [q["id"] for q in chosen], minutes=body.minutes,
                                subject=subject)
    return exams.public_session(sess)


@router.get("/exams/history")
def exam_history(user=Depends(current_user)):
    return exams.history(user["email"])


@router.get("/exams/{sid}")
def exam_get(sid: str, user=Depends(current_user)):
    return exams.public_session(exams.get_session(sid, user["email"]))


@router.post("/exams/{sid}/answer")
def exam_answer(sid: str, body: AnswerBody, user=Depends(current_user)):
    return exams.record_answer(exams.get_session(sid, user["email"]), body.qid, body.answer)


@router.post("/exams/{sid}/submit")
def exam_submit(sid: str, user=Depends(current_user)):
    sess = exams.get_session(sid, user["email"])
    written = sum(1 for q in sess["question_ids"]
                  if content.question_bank().get(q, {}).get("kind") not in exams.MCQ_KINDS)
    ai = written > 0 and (entitlements.remaining(user, "written_ai_grading_per_month") or 0) >= written
    if ai:
        entitlements.consume(user, "written_ai_grading_per_month", written)
    return exams.submit(sess, ai_grading=ai)


@router.get("/mastery")
def mastery(user=Depends(current_user)):
    return exams.get_mastery(user["email"])


# ---- 6. live exams + AI proctoring -------------------------------------------

class LiveCreateBody(BaseModel):
    title: str
    subject: str
    starts_at: str
    duration_min: int = Field(ge=1, le=600)
    question_ids: List[str]
    tier: str = "free"
    proctored: bool = False
    join_window_min: int = 15


class ProctorEventsBody(BaseModel):
    events: List[dict]


@router.get("/live")
def live_list(user=Depends(current_user)):
    return live.listing()


@router.post("/live")
def live_create(body: LiveCreateBody, user=Depends(admin_user)):
    bank = content.question_bank()
    missing = [q for q in body.question_ids if q not in bank]
    if missing:
        raise HTTPException(400, {"unknown_questions": missing})
    return live.create(body.title, _subject(body.subject), body.starts_at, body.duration_min, body.question_ids,
                       user["email"], tier=body.tier, proctored=body.proctored, join_window_min=body.join_window_min)


@router.post("/live/{lid}/join")
def live_join(lid: str, user=Depends(current_user)):
    return live.join(lid, user)


@router.get("/live/{lid}/leaderboard")
def live_leaderboard(lid: str, user=Depends(current_user)):
    return live.leaderboard(lid)


@router.post("/proctor/{sid}/events")
def proctor_events(sid: str, body: ProctorEventsBody, user=Depends(current_user)):
    exams.get_session(sid, user["email"])  # ownership check
    return proctoring.ingest(sid, user["email"], body.events)


@router.get("/proctor/{sid}/report")
def proctor_report(sid: str, user=Depends(admin_user)):
    return proctoring.report(sid)


# ---- 3. practical theory ------------------------------------------------------

@router.get("/theory/modules")
def theory_list(subject: str = "", user=Depends(current_user)):
    _subject(subject)
    pro_ok = entitlements.allowed(user, "theory_pro_modules")
    out = []
    for m in content.theory_modules().values():
        if subject and m.get("subject") != subject:
            continue
        out.append({k: m.get(k) for k in ("id", "title", "subject", "system", "tier", "summary", "est_minutes")}
                   | {"locked": m.get("tier") == "pro" and not pro_ok})
    return out


@router.get("/theory/modules/{mid}")
def theory_get(mid: str, user=Depends(current_user)):
    m = content.theory_modules().get(mid)
    if not m:
        raise HTTPException(404, "module not found")
    if m.get("tier") == "pro":
        entitlements.require(user, "theory_pro_modules")
    return m


# ---- 4. clinical doubts -------------------------------------------------------

class DeidBody(BaseModel):
    text: str


class DoubtBody(BaseModel):
    title: str
    body: str
    subject: str
    system: str = ""
    tags: List[str] = []
    attest_deidentified: bool = False


class ReplyBody(BaseModel):
    body: str
    attest_deidentified: bool = False


class VoteBody(BaseModel):
    value: int = Field(ge=-1, le=1)


class ReportBody(BaseModel):
    reason: str


class ModerateBody(BaseModel):
    status: str
    reply_id: Optional[str] = None


@router.post("/doubts/check")
def doubts_check(body: DeidBody, user=Depends(current_user)):
    return deid.check(body.text)


@router.get("/doubts")
def doubts_list(subject: str = "", status: str = "approved", user=Depends(current_user)):
    return doubts.listing(user["email"], bool(user.get("is_admin")), _subject(subject), status)


@router.post("/doubts")
def doubts_create(body: DoubtBody, user=Depends(current_user)):
    entitlements.consume(user, "doubt_posts_per_month")
    rec = doubts.create(user["email"], body.title, body.body, _subject(body.subject), body.system, body.tags,
                        attest=body.attest_deidentified, auto_approve=bool(user.get("is_admin")))
    return doubts.public(rec, user["email"])


@router.get("/doubts/{did}")
def doubts_get(did: str, user=Depends(current_user)):
    mod = bool(user.get("is_admin"))
    return doubts.public(doubts.get(did, user["email"], mod), user["email"], mod)


@router.post("/doubts/{did}/replies")
def doubts_reply(did: str, body: ReplyBody, user=Depends(current_user)):
    r = doubts.reply(did, user["email"], body.body, body.attest_deidentified, auto_approve=bool(user.get("is_admin")))
    return {k: v for k, v in r.items() if k != "author"}


@router.post("/doubts/{did}/ai-answer")
def doubts_ai_answer(did: str, user=Depends(current_user)):
    entitlements.require(user, "doubt_ai_answer")
    raise HTTPException(501, "AI first-response not wired yet (acumen_core.llm + RAG over papers/pearls)")


@router.post("/doubts/{did}/vote")
def doubts_vote(did: str, body: VoteBody, user=Depends(current_user)):
    return {"score": doubts.vote(did, user["email"], body.value)}


@router.post("/doubts/{did}/report")
def doubts_report(did: str, body: ReportBody, user=Depends(current_user)):
    doubts.report(did, user["email"], body.reason)
    return {"ok": True}


@router.post("/doubts/{did}/accept/{reply_id}")
def doubts_accept(did: str, reply_id: str, user=Depends(current_user)):
    doubts.accept(did, user["email"], reply_id)
    return {"ok": True}


@router.post("/doubts/{did}/moderate")
def doubts_moderate(did: str, body: ModerateBody, user=Depends(admin_user)):
    doubts.moderate(did, body.status, body.reply_id)
    return {"ok": True}


# ---- 5. videos --------------------------------------------------------------

@router.get("/videos")
def videos_list(modality: str = "", subject: str = "", user=Depends(current_user)):
    pro_ok = entitlements.allowed(user, "video_pro_library")
    out = []
    for v in content.video_catalog().values():
        if modality and v.get("modality") != modality:
            continue
        if subject and v.get("subject") != subject:
            continue
        out.append({k: v.get(k) for k in ("id", "title", "modality", "subject", "level", "duration_s", "tier",
                                           "thumbnail")} | {"locked": v.get("tier") == "pro" and not pro_ok})
    return out


@router.get("/videos/{vid}")
def videos_get(vid: str, user=Depends(current_user)):
    v = content.video_catalog().get(vid)
    if not v:
        raise HTTPException(404, "video not found")
    if v.get("tier") == "pro":
        entitlements.require(user, "video_pro_library")
        # TODO: return a short-lived signed playback URL (Bunny Stream / Cloudflare Stream token)
    return v


# ---- 7. notifications ---------------------------------------------------------

@router.get("/notify/prefs")
def notify_get(user=Depends(current_user)):
    return notify.get_prefs(user["email"])


@router.put("/notify/prefs")
def notify_put(body: dict, user=Depends(current_user)):
    try:
        return notify.set_prefs(user, body)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/cron/digest")
def cron_digest(request: Request, dry_run: bool = True):
    secret = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if not config.CRON_SECRET or secret != config.CRON_SECRET:
        raise HTTPException(401, "bad cron secret")
    from acumen_core.kv import kv_get, kv_scan
    users = [u for u in (kv_get(k) for k in kv_scan("auth:users:*") or []) if u]
    return notify.run_digest(users, dry_run=dry_run)


# ---- 8. voice -----------------------------------------------------------------

@router.get("/voice/config")
def voice_config(user=Depends(current_user)):
    return voice.capabilities() | {"minutes_left": entitlements.remaining(user, "voice_minutes_per_month")}


@router.post("/voice/stt")
async def voice_stt(request: Request, user=Depends(current_user)):
    entitlements.consume(user, "voice_minutes_per_month")   # TODO: meter by audio duration, not per call
    text = voice.transcribe(await request.body(), request.headers.get("content-type", ""))
    if text is None:
        raise HTTPException(501, "server STT not configured — use browser dictation")
    return {"text": text}


@router.post("/voice/viva/session")
def voice_viva(user=Depends(current_user)):
    entitlements.require(user, "voice_minutes_per_month")
    if not config.REALTIME_SERVICE_URL:
        raise HTTPException(501, "realtime service not deployed yet")
    # TODO: mint a short-lived token the realtime service verifies (HMAC of email+exp)
    raise HTTPException(501, "viva token minting not implemented")


# ---- billing ------------------------------------------------------------------

class CheckoutBody(BaseModel):
    tier: str
    months: int = 1


@router.get("/billing/plans")
def billing_plans():
    return billing.plans()


@router.post("/billing/checkout")
def billing_checkout(body: CheckoutBody, user=Depends(current_user)):
    return billing.create_checkout(user, body.tier, body.months)


@router.post("/billing/webhook/{provider}")
async def billing_webhook(provider: str, request: Request):
    raw = await request.body()
    sig = request.headers.get("x-razorpay-signature", "") or request.headers.get("stripe-signature", "")
    return billing.handle_webhook(provider, raw, sig)


@router.put("/admin/subscription/{email}")
def admin_set_sub(email: str, body: dict, user=Depends(admin_user)):
    """Manual grant (comp accounts, faculty, beta testers)."""
    try:
        return entitlements.set_subscription(email, body.get("tier", "free"), body.get("expires_at"), provider="manual")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/admin/content/reload")
def admin_reload(user=Depends(admin_user)):
    content.reload()
    return {"questions": len(content.question_bank()), "modules": len(content.theory_modules()),
            "videos": len(content.video_catalog()), "flashcards": len(content.flashcard_index())}


# ---- shell page ---------------------------------------------------------------

_SHELL = os.path.join(os.path.dirname(__file__), "static", "learn.html")


def _shell_page(request: Request):
    if not (_GET_USER and _GET_USER(request)):
        return HTMLResponse('<meta http-equiv="refresh" content="0;url=/">', status_code=401)
    with open(_SHELL, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


def mount(app: FastAPI, get_user: Callable[[Request], Optional[dict]]) -> bool:
    """Attach the v2 API + /learn page to the portal app. No-op when disabled."""
    global _GET_USER
    if not config.PLATFORM_ENABLED:
        return False
    _GET_USER = get_user
    app.include_router(router)
    app.add_api_route("/learn", _shell_page, methods=["GET"], response_class=HTMLResponse, include_in_schema=False)
    return True
