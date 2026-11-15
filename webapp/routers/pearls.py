"""Clinical pearls endpoint."""
from fastapi import APIRouter, HTTPException, Request

from webapp import loaders
from webapp.auth import get_session_user, require_feature

router = APIRouter()


@router.get("/api/pearls")
async def get_pearls(request: Request, q: str = "", system: str = "", type: str = "", page: int = 1, limit: int = 50):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_feature(user, "pearls")
    pearls = loaders.load_pearls()
    filtered = []
    for p in pearls:
        if q and q.lower() not in str(p.get("pearl", "")).lower() and q.lower() not in str(p.get("source_paper", "")).lower():
            continue
        if system and p.get("system", "") != system:
            continue
        if type and p.get("type", "") != type:
            continue
        filtered.append(p)
    total = len(filtered)
    start = (page - 1) * limit
    end = start + limit
    return {"pearls": filtered[start:end], "total": total, "page": page, "totalPages": (total + limit - 1) // limit if limit > 0 else 1}
