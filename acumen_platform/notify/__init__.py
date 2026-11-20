"""Email / WhatsApp push.

Preferences (v2:notify:<email>):
    {"email": true, "whatsapp": false, "phone": "+91...", "whatsapp_opt_in_at": iso|None,
     "cadence": "daily"|"weekly"|"off", "hour_local": 7, "tz": "Asia/Kolkata",
     "subjects": ["ccm"], "kinds": ["srs_due", "pearl", "live_exam", "doubt_reply"]}

WhatsApp rules (Meta Cloud API): business-initiated messages need explicit
opt-in and a pre-approved *template*; free-form text is only allowed inside a
24h window after the user messages you. So the digest is a template with
variables, not arbitrary HTML.

Scheduling: a Vercel cron (or GitHub Action) hits POST /api/v2/cron/digest
with the CRON_SECRET header once an hour; run_digest() sends to users whose
local hour matches. See docs/revamp/PLAN.md §Notifications.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .. import entitlements, srs
from ..store import store, utcnow, iso
from .channels import EmailChannel, WhatsAppChannel

DEFAULT_PREFS = {"email": True, "whatsapp": False, "phone": "", "whatsapp_opt_in_at": None,
                 "cadence": "weekly", "hour_local": 7, "tz_offset_min": 330, "subjects": [],
                 "kinds": ["srs_due", "pearl", "live_exam", "doubt_reply"]}


def get_prefs(email: str) -> dict:
    return {**DEFAULT_PREFS, **(store.get("notify", email, default={}) or {})}


def set_prefs(user: dict, body: dict) -> dict:
    prefs = get_prefs(user["email"])
    for k in DEFAULT_PREFS:
        if k in body:
            prefs[k] = body[k]
    if prefs.get("whatsapp"):
        entitlements.require(user, "push_whatsapp")
        if not prefs.get("phone"):
            raise ValueError("phone required for WhatsApp")
        prefs["whatsapp_opt_in_at"] = prefs.get("whatsapp_opt_in_at") or iso()
    else:
        prefs["whatsapp_opt_in_at"] = None
    # free tier: weekly email at most
    if entitlements.limits_of(user).get("push_email") == "weekly" and prefs.get("cadence") == "daily":
        prefs["cadence"] = "weekly"
    store.put("notify", user["email"], value=prefs)
    return prefs


def build_digest(email: str) -> dict:
    st = srs.stats(email)
    return {
        "srs_due": st["due_now"],
        "pearl": None,          # TODO: pick a pearl from pearls.json in a preferred subject
        "live_exams": [],       # TODO: upcoming live.listing() within 48h
        "doubt_replies": 0,     # TODO: replies on the user's doubts since last digest
    }


def _due_now(prefs: dict, now: datetime) -> bool:
    if prefs.get("cadence") == "off":
        return False
    local = now + timedelta(minutes=int(prefs.get("tz_offset_min", 330)))
    if local.hour != int(prefs.get("hour_local", 7)):
        return False
    if prefs.get("cadence") == "weekly" and local.weekday() != 0:   # Mondays
        return False
    return True


def run_digest(users: List[dict], dry_run: bool = True, now: Optional[datetime] = None) -> Dict[str, int]:
    """Send digests to users whose schedule matches `now`. Returns counters."""
    now = now or utcnow()
    email_ch, wa_ch = EmailChannel(dry_run=dry_run), WhatsAppChannel(dry_run=dry_run)
    sent = {"email": 0, "whatsapp": 0, "skipped": 0}
    for u in users:
        prefs = get_prefs(u["email"])
        if not _due_now(prefs, now):
            sent["skipped"] += 1
            continue
        stamp = now.strftime("%Y-%m-%d")
        if store.get("notify_sent", u["email"], stamp):
            sent["skipped"] += 1
            continue
        d = build_digest(u["email"])
        if prefs.get("email") and email_ch.send_digest(u["email"], u.get("first_name", ""), d):
            sent["email"] += 1
        wa_ok = prefs.get("whatsapp") and prefs.get("whatsapp_opt_in_at") and entitlements.allowed(u, "push_whatsapp")
        if wa_ok and wa_ch.send_digest(prefs["phone"], u.get("first_name", ""), d):
            sent["whatsapp"] += 1
        if not dry_run:
            store.put("notify_sent", u["email"], stamp, value=True, ttl=3 * 86400)
    return sent
