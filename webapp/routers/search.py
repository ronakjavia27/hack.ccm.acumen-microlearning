"""Global search over summaries."""
import json
import os

from fastapi import APIRouter, HTTPException, Request

from webapp.auth import get_session_user, require_feature
from webapp.config import OUTPUT_DIR
from webapp.render import extract_metadata, extract_search_text

router = APIRouter()


@router.get("/api/search")
async def search_summaries(request: Request, q: str = ""):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_feature(user, "search")
    if not q.strip():
        return {"matches": []}
    query = q.strip().lower()
    results = []
    if os.path.exists(OUTPUT_DIR):
        for root, dirs, files in os.walk(OUTPUT_DIR):
            for fname in files:
                if not fname.endswith(".json"):
                    continue
                try:
                    fpath = os.path.join(root, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        payload = json.load(f)
                    search_text = extract_search_text(payload)
                    if query in search_text:
                        title, system, article_type, journal = extract_metadata(payload)
                        results.append({"file_name": fname, "title": title, "system": system or "Other", "type": article_type or "Other", "journal": journal})
                except Exception:
                    continue
    return {"matches": results}
