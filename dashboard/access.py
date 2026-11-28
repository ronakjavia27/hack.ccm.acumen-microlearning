"""Console access guard — private remote access through Tailscale Serve.

The console binds to 127.0.0.1. Remote access goes through
`tailscale serve --bg 8878`, which proxies tailnet HTTPS traffic to localhost
and adds identity headers (Tailscale-User-Login / Tailscale-User-Name).

Rules (see docs/console/REMOTE_ACCESS.md):
  loopback, no Tailscale-User-Login header   → allowed (your browser on the laptop)
  loopback, Tailscale-User-Login == owner    → allowed (you, via Tailscale, e.g. phone)
  loopback, any other Tailscale login        → 403
  non-loopback (someone on the same Wi-Fi)   → 403, unless CONSOLE_ALLOW_LAN=1
Env: CONSOLE_OWNER (your Tailscale login, e.g. you@gmail.com), CONSOLE_ALLOW_LAN.
"""
from __future__ import annotations

import os
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse

LOOPBACK = {"127.0.0.1", "::1", "localhost"}
LOGIN_HEADER = "tailscale-user-login"
NAME_HEADER = "tailscale-user-name"


def owner() -> str:
    return os.environ.get("CONSOLE_OWNER", "").strip().lower()


def allow_lan() -> bool:
    return os.environ.get("CONSOLE_ALLOW_LAN", "").strip().lower() in ("1", "true", "yes")


def decide(client_host: Optional[str], login: Optional[str]) -> Optional[str]:
    """Return None if allowed, else the reason for refusing."""
    login = (login or "").strip().lower()
    if client_host not in LOOPBACK:
        return None if allow_lan() else "Console is private: use it on the laptop or through Tailscale."
    if not login:
        return None
    if owner() and login == owner():
        return None
    if not owner():
        return "Set CONSOLE_OWNER to your Tailscale login to allow remote access."
    return f"{login} is not allowed to use this console."


def reviewer_name(request: Request) -> str:
    """Display name for audit/reviewer fields when the request came via Tailscale."""
    return (request.headers.get(NAME_HEADER) or request.headers.get(LOGIN_HEADER) or "").strip()


class ConsoleAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        host = request.client.host if request.client else None
        reason = decide(host, request.headers.get(LOGIN_HEADER))
        if reason:
            return PlainTextResponse(f"403 — {reason}", status_code=403)
        return await call_next(request)


def startup_warning() -> Optional[str]:
    if not owner():
        return ("[console] CONSOLE_OWNER is not set — remote (Tailscale) access is refused. "
                "Set it in .env to your Tailscale login to use the console from your phone.")
    return None
