"""Print-friendly export of summaries and notes."""
import html
import json
import os
import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from webapp.auth import get_session_user, require_feature
from webapp.config import OUTPUT_DIR
from webapp.render import format_new_schema_as_markdown, render_printable

router = APIRouter()


@router.get("/export/print")
async def export_print(request: Request, kind: str = "paper", file_name: str = "", title: str = ""):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    feature = "theory" if kind == "note" else "papers"
    require_feature(user, feature)
    meta_html = ""
    content = ""
    kind_label = "Print Friendly"
    try:
        if kind == "note":
            note = None
            base = os.path.join(OUTPUT_DIR, "Theory MDs")
            if os.path.isdir(base):
                for root, dirs, files in os.walk(base):
                    if file_name in files:
                        try:
                            with open(os.path.join(root, file_name), "r", encoding="utf-8", errors="replace") as f:
                                note = {"md": f.read()}
                        except Exception:
                            pass
                        break
            if not note:
                return JSONResponse(status_code=404, content={"error": f"Note not found: {file_name}"})
            content = note["md"]
            stem = os.path.splitext(file_name)[0].replace("_", " ")
            m = re.search(r"^\s*#{1,6}\s+(.+?)\s*$", content, re.M)
            t = m.group(1).strip() if m else stem
            title_label = title or t
            meta_html = f"<span>{html.escape(title or t)}</span>"
            kind_label = "Theory Topic"
        else:
            base_name = os.path.splitext(file_name)[0]
            clean_system = "".join(x for x in str(request.query_params.get("system", "General")) if x.isalnum() or x in "._- ").strip()
            clean_type = "".join(x for x in str(request.query_params.get("type", "Other")) if x.isalnum() or x in "._- ").strip()
            target = os.path.join(OUTPUT_DIR, clean_system, clean_type, f"{base_name}.json")
            if not os.path.exists(target):
                for root, dirs, files in os.walk(OUTPUT_DIR):
                    if f"{base_name}.json" in files:
                        target = os.path.join(root, f"{base_name}.json")
                        break
            if not os.path.exists(target):
                return JSONResponse(status_code=404, content={"error": f"Summary not found: {base_name}.json"})
            with open(target, "r", encoding="utf-8") as f:
                payload = json.load(f)
            content = payload.get("clinical_summary_markdown", "") or format_new_schema_as_markdown(payload)
            title_label = payload.get("title") or base_name
            authors = payload.get("primary_authors") or payload.get("authors") or ""
            if not authors:
                issuing = payload.get("issuing_bodies", [])
                if issuing:
                    authors = ", ".join(issuing)
            meta = []
            if authors:
                meta.append(html.escape(authors))
            if payload.get("journal"):
                meta.append(html.escape(str(payload["journal"])))
            if payload.get("year"):
                meta.append(html.escape(str(payload["year"])))
            meta_html = " &middot; ".join(meta)
            kind_label = "Guideline" if str(payload.get("doc_type", "")).lower() == "guideline" else "Paper"
        return HTMLResponse(content=render_printable(title_label, meta_html, content, kind_label))
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
