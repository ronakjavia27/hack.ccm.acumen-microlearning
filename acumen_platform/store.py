"""Persistence layer for the v2 platform.

All v2 modules go through `store` — never through acumen_core.kv directly —
so the planned move from Upstash KV to Postgres touches only this file.

Keys are namespaced: v2:<domain>:<...parts>.
"""
from __future__ import annotations

import fnmatch
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from . import config


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: Optional[datetime] = None) -> str:
    return (dt or utcnow()).isoformat()


def parse_iso(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class MemoryBackend:
    """In-process dict backend — used by tests."""

    def __init__(self):
        self.data: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ttl=None):
        with self._lock:
            self.data[key] = value
        return True

    def delete(self, key):
        with self._lock:
            self.data.pop(key, None)
        return True

    def scan(self, pattern):
        return [k for k in list(self.data) if fnmatch.fnmatchcase(k, pattern)]


class KVBackend:
    """Delegates to acumen_core.kv (Upstash in prod, local_kv.json locally)."""

    def __init__(self):
        from acumen_core import kv
        self._kv = kv

    def get(self, key):
        return self._kv.kv_get(key)

    def set(self, key, value, ttl=None):
        return self._kv.kv_set(key, value, ttl=ttl)

    def delete(self, key):
        return self._kv.kv_delete(key)

    def scan(self, pattern):
        return self._kv.kv_scan(pattern) or []


class Store:
    def __init__(self, backend=None, prefix: str = config.KV_PREFIX):
        self._backend = backend
        self.prefix = prefix

    @property
    def backend(self):
        if self._backend is None:
            self._backend = KVBackend()
        return self._backend

    def set_backend(self, backend):
        self._backend = backend

    def key(self, *parts) -> str:
        return ":".join([self.prefix, *[str(p) for p in parts]])

    def get(self, *parts, default=None):
        v = self.backend.get(self.key(*parts))
        return default if v is None else v

    def put(self, *parts, value, ttl: Optional[int] = None) -> bool:
        return bool(self.backend.set(self.key(*parts), value, ttl=ttl))

    def delete(self, *parts) -> bool:
        return bool(self.backend.delete(self.key(*parts)))

    def list(self, *parts) -> List[Any]:
        """All values under a prefix (KV scan — fine for the skeleton, replace with SQL later)."""
        keys = self.backend.scan(self.key(*parts, "*"))
        out = []
        for k in keys:
            v = self.backend.get(k)
            if v is not None:
                out.append(v)
        return out

    def update(self, *parts, fn: Callable[[Any], Any], default=None):
        """Read-modify-write. NOT atomic on KV — acceptable for per-user docs, not for shared counters."""
        cur = self.get(*parts, default=default)
        new = fn(cur)
        self.put(*parts, value=new)
        return new


store = Store()
