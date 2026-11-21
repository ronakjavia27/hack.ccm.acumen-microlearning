"""Console endpoints for the Content Studio (/console/studio + /console/api/studio/*).

Included into dashboard.app.router BEFORE its /api/{kind} catch-alls.
LLM work (generate / re-verify) runs in background threads; poll /jobs/{id}.
"""
from __future__ import annotations

import secrets
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from acumen_core import config
from acumen_core.studio import generate, intake, items as store, publish

from .storage import audit

router = APIRouter()
_JOBS: Dict[str, dict] = {}
_BUSY: set = set()
_LOCK = threading.Lock()


def _get(item_id: str) -> dict:
    it = store.load(item_id)
    if not it:
        raise HTTPException(404, f"studio item {item_id} not found")
    return it


def _lite(it: dict) -> dict:
    cur = store.current_version(it) or {}
    pkg = cur.get("package") or {}
    return {"id": it["id"], "subject": it["subject"], "system": it.get("system"), "subtopic": it.get("subtopic"),
            "question": it["question"], "qtype": it["qtype"], "marks": it.get("marks"), "status": it["status"],
            "triage": it.get("triage"), "reasons": (cur.get("reasons") or [])[:3], "n_sources": len(it.get("sources") or []),
            "n_cards": len(pkg.get("flashcards") or []), "n_mcqs": len(pkg.get("mcqs") or []),
            "version": it.get("current"), "updated_at": it.get("updated_at"), "busy": it["id"] in _BUSY,
            "error": it.get("error") if it["status"] == "error" else None}


def _run_job(kind: str, ids: List[str], fn) -> dict:
    jid = secrets.token_hex(5)
    job = {"id": jid, "kind": kind, "total": len(ids), "done": 0, "status": "running", "results": []}
    _JOBS[jid] = job

    def worker():
        for iid in ids:
            with _LOCK:
                if iid in _BUSY:
                    job["results"].append({"id": iid, "skipped": "busy"})
                    job["done"] += 1
                    continue
                _BUSY.add(iid)
            try:
                it = fn(store.load(iid))
                job["results"].append({"id": iid, "status": it["status"], "triage": it.get("triage")})
            except Exception as e:
                job["results"].append({"id": iid, "error": str(e)})
            finally:
                _BUSY.discard(iid)
                job["done"] += 1
        job["status"] = "done"

    threading.Thread(target=worker, daemon=True).start()
    return job


# ---- page ---------------------------------------------------------------------

@router.get("/studio", response_class=HTMLResponse, include_in_schema=False)
async def studio_page():
    html = Path(__file__).parent / "static" / "studio.html"
    return HTMLResponse(html.read_text(encoding="utf-8"))


# ---- read --------------------------------------------------------------------------

@router.get("/api/studio/summary")
async def studio_summary():
    all_ = store.all_items()
    return {"counts": store.counts(all_), "total": len(all_),
            "models": {"draft": config.STUDIO_DRAFT_MODEL, "verify": config.STUDIO_VERIFY_MODEL},
            "api_key": bool(config.STUDIO_API_KEY), "reviewer": config.STUDIO_REVIEWER,
            "subjects": sorted(set(config.STUDIO_SUBJECT_FOLDERS.values()))}


@router.get("/api/studio/items")
async def studio_items(status: str = "", triage: str = "", subject: str = "", q: str = ""):
    out = []
    ql = q.lower().strip()
    for it in store.all_items(subject):
        if status and it["status"] != status:
            continue
        if triage and it.get("triage") != triage:
            continue
        if ql and ql not in (it["question"] + " " + (it.get("system") or "") + " " + (it.get("subtopic") or "")).lower():
            continue
        out.append(_lite(it))
    order = {"red": 0, "amber": 1, "green": 2, None: 3}
    return sorted(out, key=lambda r: (r["status"] != "generated", order.get(r["triage"], 3), r["updated_at"] or ""))


@router.get("/api/studio/items/{item_id}")
async def studio_item(item_id: str):
    it = _get(item_id)
    return {**it, "busy": item_id in _BUSY}


@router.get("/api/studio/jobs/{jid}")
async def studio_job(jid: str):
    if jid not in _JOBS:
        raise HTTPException(404, "job not found")
    return _JOBS[jid]


# ---- intake -------------------------------------------------------------------------

class IngestText(BaseModel):
    subject: str
    text: str
    label: str = "pasted"
    csv: bool = False


@router.post("/api/studio/ingest-text")
async def studio_ingest_text(body: IngestText):
    try:
        r = intake.ingest_text(body.text, body.subject, f"console:{body.label}", label=body.label, is_csv=body.csv)
    except ValueError as e:
        raise HTTPException(400, str(e))
    audit("studio", ",".join(r["new"])[:200], "ingest", note=f"{len(r['new'])} new / {len(r['merged'])} merged")
    return r


@router.post("/api/studio/ingest-folder")
async def studio_ingest_folder(force: bool = False):
    return intake.ingest_folder(force=force)


# ---- generation -----------------------------------------------------------------------

class GenBody(BaseModel):
    ids: Optional[List[str]] = None
    max: int = 0
    subject: str = ""


@router.post("/api/studio/generate")
async def studio_generate(body: GenBody):
    if not config.STUDIO_API_KEY:
        raise HTTPException(400, "No STUDIO_API_KEY / OPENROUTER_API_KEY configured")
    if body.ids:
        ids = body.ids
    else:
        ids = [it["id"] for it in store.all_items(body.subject)
               if it["status"] in ("queued", "revision_requested", "error")]
        ids = ids[:body.max] if body.max else ids
    return _run_job("generate", ids, lambda it: generate.generate_item(it))


@router.post("/api/studio/items/{item_id}/reverify")
async def studio_reverify(item_id: str):
    _get(item_id)
    return _run_job("reverify", [item_id], lambda it: generate.reverify_item(it))


# ---- review ----------------------------------------------------------------------------

class ReviewBody(BaseModel):
    by: str = ""
    note: str = ""
    parts: Optional[Dict[str, Any]] = None


class EditBody(BaseModel):
    by: str = ""
    note: str = ""
    package: Dict[str, Any]


def _by(b: str) -> str:
    return (b or config.STUDIO_REVIEWER).strip()[:60]


def _guard(item_id):
    if item_id in _BUSY:
        raise HTTPException(409, "item is being generated — wait for it to finish")


@router.post("/api/studio/items/{item_id}/approve")
async def studio_approve(item_id: str, body: ReviewBody):
    _guard(item_id)
    try:
        it = publish.approve(_get(item_id), _by(body.by), body.parts, body.note)
    except (publish.PublishError, store.TransitionError) as e:
        raise HTTPException(400, str(e))
    audit("studio", item_id, "approve", note=f"{_by(body.by)} v{it['review']['version']}")
    return _lite(it)


@router.post("/api/studio/items/{item_id}/reject")
async def studio_reject(item_id: str, body: ReviewBody):
    _guard(item_id)
    try:
        it = publish.reject(_get(item_id), _by(body.by), body.note)
    except store.TransitionError as e:
        raise HTTPException(400, str(e))
    audit("studio", item_id, "reject", note=body.note)
    return _lite(it)


@router.post("/api/studio/items/{item_id}/revise")
async def studio_revise(item_id: str, body: ReviewBody, run: bool = True):
    _guard(item_id)
    try:
        publish.request_revision(_get(item_id), _by(body.by), body.note)
    except (publish.PublishError, store.TransitionError) as e:
        raise HTTPException(400, str(e))
    audit("studio", item_id, "revision_requested", note=body.note)
    if run and config.STUDIO_API_KEY:
        return _run_job("generate", [item_id], lambda it: generate.generate_item(it))
    return {"queued": True}


@router.put("/api/studio/items/{item_id}/edit")
async def studio_edit(item_id: str, body: EditBody):
    _guard(item_id)
    try:
        it = generate.human_edit(_get(item_id), body.package, _by(body.by), body.note)
    except (ValueError, store.TransitionError) as e:
        raise HTTPException(400, str(e))
    audit("studio", item_id, "edit", note=f"v{it['current']} by {_by(body.by)}")
    return it


@router.post("/api/studio/items/{item_id}/requeue")
async def studio_requeue(item_id: str, body: ReviewBody):
    it = _get(item_id)
    try:
        store.transition(it, "queued", _by(body.by), body.note or "requeued")
    except store.TransitionError as e:
        raise HTTPException(400, str(e))
    store.save(it)
    return _lite(it)


@router.post("/api/studio/items/{item_id}/publish")
async def studio_publish(item_id: str):
    _guard(item_id)
    try:
        it = publish.publish(_get(item_id))
    except (publish.PublishError, store.TransitionError) as e:
        raise HTTPException(400, str(e))
    audit("studio", item_id, "publish", note=str(it["published"]))
    return it["published"]


@router.post("/api/studio/approve-green")
async def studio_approve_green(body: ReviewBody, subject: str = ""):
    ids = [i for i in publish.approve_green(_by(body.by), subject) if i not in _BUSY]
    audit("studio", f"{len(ids)} items", "bulk_approve_green", note=_by(body.by))
    return {"approved": ids}


@router.post("/api/studio/publish-approved")
async def studio_publish_approved(subject: str = ""):
    r = publish.publish_approved(subject)
    audit("studio", f"{len(r['published'])} items", "bulk_publish", note=f"failed={len(r['failed'])}")
    return r
