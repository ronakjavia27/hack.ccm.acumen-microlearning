"""Delivery channels. Each has send_digest(to, name, digest) -> bool.

dry_run=True (default everywhere) only logs — nothing leaves the box until
credentials are configured AND the caller opts in.
"""
from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from .. import config

log = logging.getLogger("acumen_platform.notify")


def _digest_text(name: str, d: dict) -> str:
    lines = [f"Hi {name or 'there'},", ""]
    lines.append(f"• {d.get('srs_due', 0)} flashcards due for review today")
    if d.get("pearl"):
        lines.append(f"• Pearl of the day: {d['pearl']}")
    for e in d.get("live_exams") or []:
        lines.append(f"• Live exam: {e.get('title')} at {e.get('starts_at')}")
    if d.get("doubt_replies"):
        lines.append(f"• {d['doubt_replies']} new replies on your doubts")
    lines += ["", "— hack.CCM"]
    return "\n".join(lines)


class EmailChannel:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run or not (config.SMTP_USER and config.SMTP_PASSWORD)

    def send_digest(self, to: str, name: str, digest: dict) -> bool:
        body = _digest_text(name, digest)
        if self.dry_run:
            log.info("[dry-run email] to=%s\n%s", to, body)
            return True
        msg = MIMEText(body)
        msg["Subject"] = f"hack.CCM — {digest.get('srs_due', 0)} cards due today"
        msg["From"] = config.SMTP_USER
        msg["To"] = to
        try:
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15) as s:
                s.starttls()
                s.login(config.SMTP_USER, config.SMTP_PASSWORD)
                s.send_message(msg)
            return True
        except Exception as e:  # pragma: no cover - network
            log.warning("email send failed to %s: %s", to, e)
            return False


class WhatsAppChannel:
    """Meta WhatsApp Cloud API, template messages only."""

    GRAPH = "https://graph.facebook.com/v21.0"

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run or not (config.WHATSAPP_TOKEN and config.WHATSAPP_PHONE_NUMBER_ID)

    def send_digest(self, phone: str, name: str, digest: dict) -> bool:
        params = [name or "Doctor", str(digest.get("srs_due", 0))]
        payload = {
            "messaging_product": "whatsapp", "to": phone.lstrip("+"), "type": "template",
            "template": {"name": config.WHATSAPP_DIGEST_TEMPLATE, "language": {"code": "en"},
                         "components": [{"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}]},
        }
        if self.dry_run:
            log.info("[dry-run whatsapp] %s", payload)
            return True
        import requests
        try:
            r = requests.post(f"{self.GRAPH}/{config.WHATSAPP_PHONE_NUMBER_ID}/messages", json=payload,
                              headers={"Authorization": f"Bearer {config.WHATSAPP_TOKEN}"}, timeout=10)
            return r.ok
        except Exception as e:  # pragma: no cover - network
            log.warning("whatsapp send failed: %s", e)
            return False
