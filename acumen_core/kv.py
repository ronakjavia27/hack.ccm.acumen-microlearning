"""Local file-backed key-value store (replaces Vercel KV for local dev)."""

import json
import os
import re

_KV_FILE = os.path.join(os.path.dirname(__file__), "..", "local_kv.json")
_KV_FILE = os.path.normpath(_KV_FILE)
_lock = __import__("threading").Lock()


def _load():
    if not os.path.exists(_KV_FILE):
        return {}
    try:
        with open(_KV_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return {}


def _save(data):
    tmp = _KV_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, _KV_FILE)


def kv_get(key: str):
    with _lock:
        data = _load()
        return data.get(key)


def kv_set(key: str, value):
    with _lock:
        data = _load()
        data[key] = value
        _save(data)


def kv_delete(key: str):
    with _lock:
        data = _load()
        data.pop(key, None)
        _save(data)


def kv_scan(pattern: str):
    with _lock:
        data = _load()
        regex = re.escape(pattern).replace(r"\*", ".*")
        return [k for k in data if re.match(regex, k)]
