"""Tests for the v2 platform skeleton (acumen_platform). Run: python -m pytest tests/ -q"""
import os
import random
import sys
from datetime import timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("PLATFORM_V2", "1")
os.environ.setdefault("PLATFORM_SAMPLE_DATA", "1")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from acumen_platform import config, deid, entitlements, exams, proctoring, srs  # noqa: E402
from acumen_platform import router as v2router  # noqa: E402
from acumen_platform.store import MemoryBackend, store, utcnow, iso  # noqa: E402

config.USE_SAMPLE_DATA = True
config.PLATFORM_ENABLED = True


@pytest.fixture(autouse=True)
def mem_store():
    store.set_backend(MemoryBackend())
    from acumen_platform import content
    content.reload()
    yield


USERS = {
    "free": {"email": "free@example.com", "first_name": "F"},
    "admin": {"email": "admin@example.com", "first_name": "A", "is_admin": True},
}


@pytest.fixture
def client():
    app = FastAPI()
    who = {"u": USERS["free"]}
    v2router._GET_USER = None
    v2router.mount(app, get_user=lambda req: who["u"])
    c = TestClient(app)
    c.who = who
    return c


# ---- SRS ---------------------------------------------------------------------

def test_sm2_progression():
    c = srs.CardState(ref="q:x")
    now = utcnow()
    c = srs.scheduler.review(c, srs.GOOD, now)       # step 0 -> 1 (10 min)
    assert c.phase == "learning"
    c = srs.scheduler.review(c, srs.GOOD, now)       # graduates
    assert c.phase == "review" and c.interval_d == 1
    c = srs.scheduler.review(c, srs.GOOD, now)
    assert c.interval_d == pytest.approx(2.5)
    c = srs.scheduler.review(c, srs.AGAIN, now)      # lapse
    assert c.phase == "relearning" and c.lapses == 1 and c.ease < 2.5


def test_srs_queue_due_and_new():
    srs.enroll("a@x", [{"ref": "q:1", "subject": "ccm"}, {"ref": "q:2", "subject": "medicine"}])
    assert {c["ref"] for c in srs.queue("a@x")} == {"q:1", "q:2"}
    assert [c["ref"] for c in srs.queue("a@x", subject="ccm")] == ["q:1"]
    srs.review("a@x", "q:1", srs.EASY)
    assert srs.queue("a@x", subject="ccm") == []                     # not due for 4 days
    later = utcnow() + timedelta(days=5)
    assert [c["ref"] for c in srs.queue("a@x", subject="ccm", now=later)] == ["q:1"]


# ---- de-identification ------------------------------------------------------

@pytest.mark.parametrize("text,kind", [
    ("Contact me at someone@hospital.org", "email"),
    ("Mobile 98765 43210 for details", "phone"),
    ("Aadhaar 2345 6789 0123", "aadhaar"),
    ("UHID: 2024/55821 admitted", "record_number"),
    ("Mr. Ramesh Kumar presented with fever", "name"),
    ("Patient name: Sita", "name"),
    ("admitted on 12/03/2025 with sepsis", "full_date"),
])
def test_deid_catches(text, kind):
    kinds = {f.kind for f in deid.scan(text)}
    assert kind in kinds, (text, kinds)


def test_deid_clean_clinical_text_passes():
    text = ("58M, known DM/HTN, fever x3 days, BP 80/50, lactate 4.2, PEEP 8, FiO2 0.6. "
            "Started meropenem. Case no improvement on day 2. What next?")
    res = deid.check(text)
    assert res["ok"], res["findings"]


def test_deid_redact():
    out = deid.redact("Mr. Arjun Rao, call +91 98765 43210")
    assert "Arjun" not in out and "98765" not in out and "[NAME]" in out


# ---- entitlements -----------------------------------------------------------

def test_quota_and_tiers():
    u = USERS["free"]
    assert entitlements.tier_of(u) == "free"
    for _ in range(2):
        entitlements.consume(u, "personalised_exams_per_week")
    with pytest.raises(Exception) as ei:
        entitlements.consume(u, "personalised_exams_per_week")
    assert getattr(ei.value, "status_code", None) == 402
    entitlements.set_subscription(u["email"], "pro", expires_at=iso(utcnow() + timedelta(days=30)))
    assert entitlements.tier_of(u) == "pro"
    entitlements.consume(u, "personalised_exams_per_week")             # unlimited now
    entitlements.set_subscription(u["email"], "pro", expires_at=iso(utcnow() - timedelta(days=1)))
    assert entitlements.tier_of(u) == "free"                            # expired
    assert entitlements.tier_of(USERS["admin"]) == "institution"


# ---- exam builder -----------------------------------------------------------

def test_personalised_prefers_weak_areas():
    pool = [{"id": f"w{i}", "subject": "ccm", "system": "Sepsis", "subtopic": "a", "difficulty": 2} for i in range(20)] + \
           [{"id": f"s{i}", "subject": "ccm", "system": "Cardiology", "subtopic": "b", "difficulty": 2} for i in range(20)]
    mastery = {"ccm|Sepsis|a": {"ema": 0.2}, "ccm|Cardiology|b": {"ema": 0.95}}
    seen = {q["id"]: "t" for q in pool}
    picked = exams.build_personalised(pool, mastery, seen, 10, rng=random.Random(1))
    assert len(picked) == 10 and len({q["id"] for q in picked}) == 10
    assert sum(q["system"] == "Sepsis" for q in picked) >= 6


def test_grading_kinds():
    assert exams.grade_one({"kind": "mcq_single", "answer": [2]}, [2])["score"] == 1
    assert exams.grade_one({"kind": "mcq_multi", "answer": [0, 2, 3]}, [0, 1])["score"] == 0
    assert exams.grade_one({"kind": "mcq_multi", "answer": [0, 2, 3]}, [0, 2])["score"] == pytest.approx(0.667, 0.01)
    w = exams.grade_one({"kind": "written_short", "rubric": [{"point": "x", "keywords": ["bilateral"], "marks": 1},
                                                             {"point": "y", "keywords": ["peep"], "marks": 1}]},
                        "bilateral opacities")
    assert w["score"] == 0.5 and w["status"] == "provisional"


def test_proctor_score():
    s = proctoring.score([{"type": "tab_hidden"}] * 3 + [{"type": "multiple_faces"}])
    assert s["integrity"] == 75 and s["flagged"] and s["severe"] == ["multiple_faces"]


# ---- API end-to-end -----------------------------------------------------------

def test_api_exam_flow_enrolls_misses(client):
    r = client.post("/api/v2/exams/personalised", json={"subject": "ccm", "n": 3, "mode": "mock", "seed": 3})
    assert r.status_code == 200, r.text
    sess = r.json()
    assert all("answer" not in q for q in sess["questions"])
    for q in sess["questions"]:
        ans = "nothing" if not q.get("options") else [0]
        assert client.post(f"/api/v2/exams/{sess['id']}/answer", json={"qid": q["id"], "answer": ans}).status_code == 200
    res = client.post(f"/api/v2/exams/{sess['id']}/submit").json()
    assert res["n"] == 3 and res["score_pct"] is not None
    assert client.post(f"/api/v2/exams/{sess['id']}/answer", json={"qid": sess["questions"][0]["id"]}).status_code == 409
    missed = [i for i in res["items"] if i["score"] < 0.6]
    assert client.get("/api/v2/srs/stats").json()["total"] == len(missed)


def test_api_personalised_quota_402(client):
    body = {"subject": "ccm", "n": 1}
    assert client.post("/api/v2/exams/personalised", json=body).status_code == 200
    assert client.post("/api/v2/exams/personalised", json=body).status_code == 200
    assert client.post("/api/v2/exams/personalised", json=body).status_code == 402


def test_api_doubts_gate(client):
    bad = {"title": "Sepsis query", "body": "Mrs. Lakshmi Devi, UHID 445512, hypotensive", "subject": "ccm",
           "attest_deidentified": True}
    r = client.post("/api/v2/doubts", json=bad)
    assert r.status_code == 422 and r.json()["detail"]["error"] == "identifiers_found"
    good = {"title": "Vasopressor choice", "body": "60F septic shock on norepinephrine 0.3 mcg/kg/min, MAP 60.",
            "subject": "ccm"}
    assert client.post("/api/v2/doubts", json=good).status_code == 422          # no attestation
    r = client.post("/api/v2/doubts", json={**good, "attest_deidentified": True})
    assert r.status_code == 200 and r.json()["status"] == "pending"
    did = r.json()["id"]
    client.who["u"] = {"email": "other@example.com"}
    assert client.get(f"/api/v2/doubts/{did}").status_code == 404                # pending: hidden from others
    client.who["u"] = USERS["admin"]
    assert client.post(f"/api/v2/doubts/{did}/moderate", json={"status": "approved"}).status_code == 200
    client.who["u"] = {"email": "other@example.com"}
    assert client.get(f"/api/v2/doubts/{did}").status_code == 200
    assert "author" not in client.get(f"/api/v2/doubts/{did}").json()


def test_api_paywalled_content(client):
    vids = {v["id"]: v for v in client.get("/api/v2/videos").json()}
    assert vids["sample-usg-rush"]["locked"] is True
    assert client.get("/api/v2/videos/sample-usg-rush").status_code == 402
    assert client.get("/api/v2/videos/sample-echo-plax").status_code == 200


def test_api_live_exam_window(client):
    client.who["u"] = USERS["admin"]
    start = iso(utcnow() - timedelta(minutes=1))
    r = client.post("/api/v2/live", json={"title": "Mock", "subject": "ccm", "starts_at": start, "duration_min": 30,
                                          "question_ids": ["sample-ccm-sepsis-001"]})
    assert r.status_code == 200, r.text
    lid = r.json()["id"]
    client.who["u"] = USERS["free"]
    s1 = client.post(f"/api/v2/live/{lid}/join").json()
    s2 = client.post(f"/api/v2/live/{lid}/join").json()
    assert s1["id"] == s2["id"] and s1["deadline"]


def test_api_requires_login(client):
    client.who["u"] = None
    assert client.get("/api/v2/me/plan").status_code == 401
    assert client.get("/api/v2/subjects").status_code == 200


def test_billing_webhook_rejects_unsigned(client):
    r = client.post("/api/v2/billing/webhook/razorpay", content=b'{"event":"subscription.activated"}')
    assert r.status_code == 401
