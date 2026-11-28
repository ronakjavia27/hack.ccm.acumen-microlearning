"""Standalone FastAPI app for the hack.CCM Console dashboard.

Run with:
    python dashboard_app.py [--port 8878] [--host 127.0.0.1] [--no-reload]

Or:
    uvicorn dashboard_app:app --host 127.0.0.1 --port 8878

Private by default: binds to localhost only. Use it from your phone through
Tailscale Serve (`tailscale serve --bg 8878`) — see docs/console/REMOTE_ACCESS.md.
dashboard/access.py refuses other devices and other Tailscale logins.
"""
import argparse
import os
from pathlib import Path
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, Response

# Load .env so KV module can find Upstash credentials
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

from dashboard.app import router
from dashboard.access import ConsoleAccessMiddleware, startup_warning

app = FastAPI(title="hack.CCM Dashboard", description="Admin console for managing hack.CCM content")
app.add_middleware(ConsoleAccessMiddleware)
app.include_router(router)

_warn = startup_warning()
if _warn:
    print(_warn)


@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/console")


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="hack.CCM Dashboard")
    parser.add_argument("--port", type=int, default=8878, help="Port to bind")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Host to bind (default localhost; remote access goes through Tailscale Serve)")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    args = parser.parse_args()
    uvicorn.run("dashboard_app:app", host=args.host, port=args.port, reload=not args.no_reload)
