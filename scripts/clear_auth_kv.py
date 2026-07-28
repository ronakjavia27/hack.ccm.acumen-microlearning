"""Delete ALL auth-related keys (auth:users:* and auth:session:*) from Vercel KV.

Usage:
    $env:KV_REST_API_URL = "https://your-url.upstash.io"
    $env:KV_REST_API_TOKEN = "your-token"
    python scripts/clear_auth_kv.py

Get credentials from: Vercel Dashboard → Storage → KV → Settings → Environment Variables
"""
import os, sys, json, requests

url = os.environ.get("KV_REST_API_URL")
token = os.environ.get("KV_REST_API_TOKEN")
if not url or not token:
    print("ERROR: Set KV_REST_API_URL and KV_REST_API_TOKEN")
    sys.exit(1)

# Scan for all auth keys
patterns = ["auth:users:*", "auth:session:*", "auth:access_defaults"]
total = 0
for pattern in patterns:
    print(f"\nScanning {pattern}...")
    r = requests.get(
        f"{url}/scan/0?match={pattern}&count=200",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if not r.ok:
        print(f"  Scan failed: {r.status_code} {r.text}")
        continue
    keys = r.json().get("result", [])
    if not keys:
        print("  No keys found")
        continue
    for key in keys:
        rd = requests.delete(
            f"{url}/del/{key}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        status = "OK" if rd.ok else f"FAIL ({rd.status_code})"
        print(f"  DEL {key} → {status}")
        total += 1

print(f"\nDone. Deleted {total} keys total.")
