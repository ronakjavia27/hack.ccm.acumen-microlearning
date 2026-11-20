"""Paywall: which tier a user is on, what it allows, and quota counting.

Subscription record (v2:sub:<email>):
    {"tier": "pro", "expires_at": iso|None, "provider": "razorpay", "ref": "..."}
Admins are treated as institution tier.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException

from . import config
from .store import store, utcnow, parse_iso, iso

_PERIOD_TTL = {"day": 2 * 86400, "week": 8 * 86400, "month": 32 * 86400}


def get_subscription(email: str) -> Dict[str, Any]:
    return store.get("sub", email, default={}) or {}


def set_subscription(email: str, tier: str, expires_at: Optional[str] = None, provider: str = "manual", ref: str = ""):
    if tier not in config.TIERS:
        raise ValueError(f"unknown tier {tier}")
    rec = {"tier": tier, "expires_at": expires_at, "provider": provider, "ref": ref, "updated_at": iso()}
    store.put("sub", email, value=rec)
    return rec


def tier_of(user: Dict[str, Any]) -> str:
    if user.get("is_admin"):
        return "institution"
    sub = get_subscription(user["email"])
    tier = sub.get("tier") or config.DEFAULT_TIER
    exp = sub.get("expires_at")
    if exp and parse_iso(exp) < utcnow():
        return config.DEFAULT_TIER
    return tier if tier in config.TIERS else config.DEFAULT_TIER


def limits_of(user) -> Dict[str, Any]:
    return dict(config.TIERS[tier_of(user)]["limits"])


def allowed(user, capability: str) -> bool:
    return bool(limits_of(user).get(capability, False))


def require(user, capability: str):
    if not allowed(user, capability):
        raise HTTPException(status_code=402, detail={"error": "upgrade_required", "capability": capability,
                                                     "tier": tier_of(user)})


def _period_bucket(period: str) -> str:
    now = utcnow()
    if period == "day":
        return now.strftime("%Y-%m-%d")
    if period == "week":
        y, w, _ = now.isocalendar()
        return f"{y}-W{w:02d}"
    if period == "month":
        return now.strftime("%Y-%m")
    raise ValueError(period)


def _split_limit(limit_key: str):
    # "doubt_posts_per_month" -> ("doubt_posts", "month")
    for p in ("day", "week", "month"):
        suffix = f"_per_{p}"
        if limit_key.endswith(suffix):
            return limit_key[: -len(suffix)], p
    raise ValueError(f"{limit_key} is not a periodic quota")


def usage(user, limit_key: str) -> int:
    metric, period = _split_limit(limit_key)
    return int(store.get("usage", user["email"], metric, _period_bucket(period), default=0) or 0)


def remaining(user, limit_key: str) -> Optional[int]:
    lim = limits_of(user).get(limit_key)
    if lim is None:
        return None
    return max(0, int(lim) - usage(user, limit_key))


def consume(user, limit_key: str, amount: int = 1):
    """Check-and-increment a periodic quota; raises 402 when exhausted."""
    rem = remaining(user, limit_key)
    if rem is not None and rem < amount:
        raise HTTPException(status_code=402, detail={"error": "quota_exhausted", "quota": limit_key,
                                                     "tier": tier_of(user)})
    metric, period = _split_limit(limit_key)
    bucket = _period_bucket(period)
    cur = int(store.get("usage", user["email"], metric, bucket, default=0) or 0)
    store.put("usage", user["email"], metric, bucket, value=cur + amount, ttl=_PERIOD_TTL[period])


def plan_summary(user) -> Dict[str, Any]:
    lim = limits_of(user)
    quotas = {}
    for k, v in lim.items():
        if "_per_" in k:
            quotas[k] = {"limit": v, "used": usage(user, k)}
    return {"tier": tier_of(user), "label": config.TIERS[tier_of(user)]["label"],
            "limits": lim, "quotas": quotas, "subscription": get_subscription(user["email"])}
