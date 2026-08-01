"""Key-value store — uses Upstash Redis when KV_URL/KV_TOKEN are set, else local file."""

import json
import os
import re

# Load repo-level .env (KV keys) BEFORE reading env vars below, so local
# uvicorn runs talk to the same Upstash KV as production by default.
# Set KV_LOCAL=1 to force the local file backend regardless of .env.
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    load_dotenv(dotenv_path=_env_path)
except Exception:
    pass

_KV_FILE = os.path.join(os.path.dirname(__file__), "..", "local_kv.json")
_KV_FILE = os.path.normpath(_KV_FILE)
_lock = __import__("threading").Lock()

KV_URL = os.environ.get("KV_REST_API_URL", "") or os.environ.get("KV_URL", "")
KV_TOKEN = os.environ.get("KV_REST_API_TOKEN", "") or os.environ.get("KV_TOKEN", "")
KV_LOCAL_ONLY = os.environ.get("KV_LOCAL", "").strip().lower() in ("1", "true", "yes")


def _use_upstash():
    return bool(KV_URL and KV_TOKEN) and not KV_LOCAL_ONLY


def kv_backend():
    """Diagnostic: which backend is active and why."""
    if KV_LOCAL_ONLY:
        return {"backend": "local", "reason": "KV_LOCAL=1 forced local file"}
    if KV_URL and KV_TOKEN:
        return {"backend": "upstash", "reason": "KV_URL/KV_TOKEN from env"}
    return {"backend": "local", "reason": "KV_URL/KV_TOKEN not set"}


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
    if _use_upstash():
        import requests
        try:
            r = requests.get(f"{KV_URL}/get/{key}", headers={"Authorization": f"Bearer {KV_TOKEN}"}, timeout=5)
            if r.ok:
                res = r.json().get("result")
                if res is not None:
                    if isinstance(res, str):
                        parsed = json.loads(res)
                        if isinstance(parsed, dict) and "value" in parsed:
                            raw = parsed["value"]
                            return json.loads(raw) if raw and isinstance(raw, str) else raw
                        return parsed
                    if isinstance(res, dict):
                        raw = res.get("value")
                        return json.loads(raw) if raw and isinstance(raw, str) else raw
                    return res
            return None
        except Exception:
            return None
    with _lock:
        data = _load()
        return data.get(key)


def kv_set(key: str, value, ttl=None):
    if _use_upstash():
        import requests
        try:
            url = f"{KV_URL}/set/{key}"
            if ttl:
                url += f"?EX={int(ttl)}"
            r = requests.post(url, json={"key": key, "value": json.dumps(value)}, headers={"Authorization": f"Bearer {KV_TOKEN}"}, timeout=5)
            return r.ok
        except Exception:
            return False
    with _lock:
        data = _load()
        data[key] = value
        _save(data)
        return True


def kv_delete(key: str):
    if _use_upstash():
        import requests
        try:
            r = requests.post(f"{KV_URL}/del/{key}", headers={"Authorization": f"Bearer {KV_TOKEN}"}, timeout=5)
            return r.ok
        except Exception:
            return False
    with _lock:
        data = _load()
        data.pop(key, None)
        _save(data)
        return True


def kv_scan(pattern: str):
    if _use_upstash():
        import requests
        try:
            r = requests.get(f"{KV_URL}/keys/{pattern}", headers={"Authorization": f"Bearer {KV_TOKEN}"}, timeout=10)
            if r.ok:
                res = r.json().get("result")
                if isinstance(res, list):
                    return res
                return []
            return []
        except Exception:
            return []
    with _lock:
        data = _load()
        regex = re.escape(pattern).replace(r"\*", ".*")
        return [k for k in data if re.match(regex, k)]
