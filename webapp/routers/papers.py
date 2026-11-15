"""Paper/guideline summary endpoint."""
import json
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from webapp.auth import get_session_user, require_feature
from webapp.config import OUTPUT_DIR
from webapp.render import format_new_schema_as_markdown

router = APIRouter()


@router.get("/api/summary")
async def get_json_summary(request: Request, file_name: str, system: str = "General", type: str = "Unclassified"):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    require_feature(user, "papers")
    base_name = os.path.splitext(file_name)[0]
    clean_system = "".join(x for x in str(system) if x.isalnum() or x in "._- ").strip()
    clean_type = "".join(x for x in str(type) if x.isalnum() or x in "._- ").strip()
    target = os.path.join(OUTPUT_DIR, clean_system, clean_type, f"{base_name}.json")
    if not os.path.exists(target):
        for root, dirs, files in os.walk(OUTPUT_DIR):
            if f"{base_name}.json" in files:
                target = os.path.join(root, f"{base_name}.json")
                break
    if not os.path.exists(target):
        return JSONResponse(status_code=404, content={"error": f"Summary not found: {base_name}.json"})
    try:
        with open(target, "r", encoding="utf-8") as f:
            payload = json.load(f)
        content = payload.get("clinical_summary_markdown", "")
        authors = payload.get("primary_authors", "")
        if not content:
            content = format_new_schema_as_markdown(payload)
        if not authors:
            authors = payload.get("authors", "")
        if not authors:
            issuing = payload.get("issuing_bodies", [])
            if issuing:
                authors = ", ".join(issuing)
        if not authors:
            authors = "Unknown Authors"
        return {
            "content": content,
            "authors": authors,
            "key_pearls": payload.get("key_pearls", []),
            "recommendations": payload.get("recommendation_blocks", []),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
