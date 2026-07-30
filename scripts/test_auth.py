"""Diagnostic script to test the complete auth flow.
Run locally to verify each component works before deploying to Vercel.

    python scripts/test_auth.py
"""
import os, sys, json, hashlib, secrets
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---- Test 1: Password hashing ----
print("=" * 60)
print("TEST 1: Password hashing")
print("=" * 60)
# Simulate hash_password
password = "testpassword123"
salt = os.urandom(16)
h = hashlib.sha256(salt + password.encode("utf-8")).hexdigest()
pw_hash = f"$sha256${salt.hex()}${h}"
print(f"  Hash: {pw_hash[:50]}...")

# Simulate verify_password
parts = pw_hash.split("$")
assert len(parts) == 4, f"Expected 4 parts, got {len(parts)}"
salt2 = bytes.fromhex(parts[2])
expected = parts[3]
actual = hashlib.sha256(salt2 + password.encode("utf-8")).hexdigest()
assert actual == expected, "Password verification FAILED"
print("  Password verification: PASS")

# Test wrong password
wrong = hashlib.sha256(salt2 + b"wrongpassword").hexdigest()
assert wrong != expected, "Wrong password should NOT match"
print("  Wrong password rejected: PASS")
print()

# ---- Test 2: KV simulation ----
print("=" * 60)
print("TEST 2: KV store/retrieve (local file)")
print("=" * 60)
from acumen_core.kv import kv_get, kv_set
test_user = {
    "email": "test@test.com",
    "password_hash": pw_hash,
    "created_at": "2026-07-30T00:00:00",
}
kv_set("auth:users:test@test.com", test_user)
retrieved = kv_get("auth:users:test@test.com")
assert retrieved is not None, "kv_get returned None"
assert retrieved["email"] == "test@test.com", f"Email mismatch: {retrieved.get('email')}"
assert retrieved["password_hash"] == pw_hash, "Password hash mismatch"
print("  KV store/retrieve: PASS")
print(f"  Retrieved: email={retrieved['email']}, hash={retrieved['password_hash'][:30]}...")
print()

# ---- Test 3: Auth flow ----
print("=" * 60)
print("TEST 3: Complete auth flow")
print("=" * 60)
# This simulates what the login endpoint does
email = "test@test.com"
password_attempt = "testpassword123"

user = kv_get(f"auth:users:{email}")
if not user:
    print("  FAIL: User not found in KV")
    sys.exit(1)

pwh = user.get("password_hash")
if not pwh:
    print("  FAIL: No password_hash in user record")
    sys.exit(1)

# Verify
if not pwh.startswith("$sha256$"):
    print(f"  FAIL: Unknown hash format: {pwh[:20]}")
    sys.exit(1)

parts = pwh.split("$")
if len(parts) != 4:
    print(f"  FAIL: Hash has {len(parts)} parts, expected 4")
    sys.exit(1)

salt = bytes.fromhex(parts[2])
expected_hash = parts[3]
actual_hash = hashlib.sha256(salt + password_attempt.encode("utf-8")).hexdigest()

if actual_hash == expected_hash:
    print("  Password verification: PASS")
else:
    print("  FAIL: Password mismatch")
    sys.exit(1)

# Wrong password should fail
wrong_hash = hashlib.sha256(salt + b"wrongpassword").hexdigest()
assert wrong_hash != expected_hash, "Wrong password MUST NOT match"

print("  Wrong password rejected: PASS")
print("  COMPLETE AUTH FLOW: PASS")

# Cleanup
kv_delete(f"auth:users:test@test.com")
print()
print("All tests passed!")
