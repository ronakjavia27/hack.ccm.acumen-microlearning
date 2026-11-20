"""Billing — provider-agnostic checkout + webhook → entitlements.

Recommended: Razorpay for INR (UPI, cards, subscriptions, e-mandate) with
Stripe as an optional second provider for international cards. The only
thing the rest of the platform ever sees is entitlements.set_subscription().

Webhook verification is implemented (HMAC) so no unsigned request can grant
a tier; checkout creation is a stub until plans/prices are decided.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import timedelta
from typing import Optional

from fastapi import HTTPException

from . import config, entitlements
from .store import store, utcnow, iso


def plans() -> list:
    return [{"tier": k, "label": v["label"], "price_inr_month": v["price_inr_month"], "limits": v["limits"]}
            for k, v in config.TIERS.items()]


def create_checkout(user: dict, tier: str, months: int = 1) -> dict:
    if tier not in config.TIERS or tier == "free":
        raise HTTPException(400, "unknown paid tier")
    if not config.BILLING_PROVIDER:
        raise HTTPException(501, "billing not configured")
    # TODO razorpay: client.subscription.create(plan_id=..., notes={"email": user["email"], "tier": tier})
    # TODO stripe:   stripe.checkout.Session.create(mode="subscription", client_reference_id=email, ...)
    raise HTTPException(501, f"{config.BILLING_PROVIDER} checkout not implemented yet")


def verify_razorpay(raw: bytes, signature: str) -> bool:
    if not config.RAZORPAY_WEBHOOK_SECRET or not signature:
        return False
    mac = hmac.new(config.RAZORPAY_WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, signature)


def handle_webhook(provider: str, raw: bytes, signature: str) -> dict:
    if provider != "razorpay":
        raise HTTPException(501, f"{provider} webhooks not implemented")
    if not verify_razorpay(raw, signature):
        raise HTTPException(401, "bad signature")
    evt = json.loads(raw or b"{}")
    eid = evt.get("id") or hashlib.sha256(raw).hexdigest()
    if store.get("billing_evt", eid):
        return {"duplicate": True}
    store.put("billing_evt", eid, value={"at": iso(), "event": evt.get("event")}, ttl=90 * 86400)

    ent = ((evt.get("payload") or {}).get("subscription") or {}).get("entity") or {}
    notes = ent.get("notes") or {}
    email, tier = notes.get("email"), notes.get("tier")
    if evt.get("event") in ("subscription.activated", "subscription.charged") and email and tier:
        entitlements.set_subscription(email, tier, expires_at=iso(utcnow() + timedelta(days=32)),
                                      provider="razorpay", ref=ent.get("id", ""))
    elif evt.get("event") in ("subscription.cancelled", "subscription.halted") and email:
        sub = entitlements.get_subscription(email)
        # keep access until the paid period ends; tier_of() handles expiry
        entitlements.set_subscription(email, sub.get("tier", "free"), expires_at=sub.get("expires_at"),
                                      provider="razorpay", ref=ent.get("id", ""))
    return {"ok": True}
