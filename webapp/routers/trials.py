"""ESBICM trials and condensed trials endpoints."""
import json
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from webapp import loaders
from webapp.auth import get_session_user, require_feature
from webapp.config import OUTPUT_DIR

router = APIRouter()


@router.get("/api/trials/stats")
async def get_trials_stats(request: Request):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_feature(user, "trials")
    idx = loaders.load_trial_index()
    counts = {}
    for t in idx:
        sp = t.get("specialty", "Other")
        counts[sp] = counts.get(sp, 0) + 1
    return {"stats": counts}


@router.get("/api/trials")
async def get_trials(
    request: Request,
    specialty: str = "",
    result_category: str = "",
    trial_type: str = "",
    q: str = "",
    page: int = 1,
    limit: int = 50
):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_feature(user, "trials")
    idx = loaders.load_trial_index()
    filtered = []
    for t in idx:
        if specialty and t.get("specialty", "") != specialty:
            continue
        if result_category and t.get("result_category", "") != result_category:
            continue
        if trial_type and t.get("trial_type", "") != trial_type:
            continue
        if q and q.lower() not in t.get("trial_name", "").lower() and q.lower() not in t.get("one_liner", "").lower():
            continue
        filtered.append(t)
    total = len(filtered)
    start = (page - 1) * limit
    end = start + limit
    return {
        "trials": filtered[start:end],
        "total": total,
        "page": page,
        "totalPages": (total + limit - 1) // limit if limit > 0 else 1
    }


@router.get("/api/trial/{slug}")
async def get_trial(request: Request, slug: str):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_feature(user, "trials")
    idx = loaders.load_trial_index()
    match = None
    for t in idx:
        if t.get("slug", "") == slug:
            match = t
            break
    if not match:
        return JSONResponse(status_code=404, content={"error": f"Trial not found: {slug}"})
    file_path = match.get("file_path", "")
    target = os.path.join(OUTPUT_DIR, file_path)
    if not os.path.exists(target):
        return JSONResponse(status_code=404, content={"error": f"Trial file not found: {file_path}"})
    try:
        with open(target, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/api/condensed-trials")
async def get_condensed_trials(request: Request, system: str = ""):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_feature(user, "condensed_trials")
    idx = loaders.load_condensed_trial_index()
    if system:
        idx = [c for c in idx if c["system"] == system]
    return {"trials": idx}


@router.get("/api/condensed-trial/{system}/{name}")
async def get_condensed_trial(request: Request, system: str, name: str):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_feature(user, "condensed_trials")
    from urllib.parse import unquote
    system = unquote(system)
    name = unquote(name)
    payload = loaders.load_condensed_trial(system, name)
    if payload is None:
        return JSONResponse(status_code=404, content={"error": f"Condensed trial not found: {system}/{name}"})
    return payload
