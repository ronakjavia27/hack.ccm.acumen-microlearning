"""Standalone FastAPI app for the hack.CCM Console dashboard.

Run with:
    python dashboard_app.py [--port 8878] [--host 0.0.0.0] [--no-reload]

Or:
    uvicorn dashboard_app:app --host 0.0.0.0 --port 8878
"""
import argparse
import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, Response
from dashboard.app import router

app = FastAPI(title="hack.CCM Dashboard", description="Admin console for managing hack.CCM content")
app.include_router(router)


@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/console")


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="hack.CCM Dashboard")
    parser.add_argument("--port", type=int, default=8878, help="Port to bind")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    args = parser.parse_args()
    uvicorn.run("dashboard_app:app", host=args.host, port=args.port, reload=not args.no_reload)
