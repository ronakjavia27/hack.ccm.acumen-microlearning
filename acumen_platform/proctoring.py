"""AI proctoring — server side.

Design: detection runs in the browser (privacy + bandwidth). The client
watches page visibility, focus, fullscreen, clipboard and devtools, and runs a
face-landmark model (e.g. MediaPipe Face Landmarker, WASM) on the webcam
stream locally. Only *events* come to the server — no video is uploaded or
stored by default. Optional periodic snapshots (opt-in, institution tier)
would go to object storage with a short retention policy.

Server responsibilities: ingest events, compute an integrity score, flag the
session for human review. A flag is never an automatic fail.
"""
from __future__ import annotations

from typing import Dict, List

from .store import store, iso

EVENT_WEIGHTS: Dict[str, int] = {
    "tab_hidden": 5,
    "window_blur": 2,
    "fullscreen_exit": 5,
    "paste": 3,
    "copy": 1,
    "devtools_open": 10,
    "face_missing": 4,
    "multiple_faces": 10,
    "gaze_away": 1,
    "voice_detected": 3,
    "network_offline": 1,
    "camera_denied": 15,
}
SEVERE = {"multiple_faces", "devtools_open", "camera_denied"}
MAX_EVENTS_PER_SESSION = 2000
FLAG_BELOW = 70


def ingest(exam_id: str, email: str, events: List[dict]) -> dict:
    log = store.get("proctor", exam_id, default={"email": email, "events": []})
    if log.get("email") != email:
        return {"accepted": 0}
    clean = []
    for e in events[:200]:
        t = str(e.get("type", ""))
        if t in EVENT_WEIGHTS:
            clean.append({"type": t, "at": str(e.get("at") or iso()), "detail": str(e.get("detail", ""))[:200]})
    log["events"] = (log["events"] + clean)[-MAX_EVENTS_PER_SESSION:]
    store.put("proctor", exam_id, value=log)
    return {"accepted": len(clean), **score(log["events"])}


def score(events: List[dict]) -> dict:
    counts: Dict[str, int] = {}
    for e in events:
        counts[e["type"]] = counts.get(e["type"], 0) + 1
    penalty = sum(EVENT_WEIGHTS[t] * min(c, 10) for t, c in counts.items())
    integrity = max(0, 100 - penalty)
    severe = sorted(t for t in counts if t in SEVERE)
    return {"integrity": integrity, "counts": counts, "flagged": integrity < FLAG_BELOW or bool(severe),
            "severe": severe}


def report(exam_id: str) -> dict:
    log = store.get("proctor", exam_id, default={"events": []})
    return {"exam_id": exam_id, "email": log.get("email"), **score(log["events"]), "events": log["events"]}
