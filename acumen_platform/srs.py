"""Spaced repetition.

Scheduler: SM-2 with Anki-style grades (1 again, 2 hard, 3 good, 4 easy).
The `Scheduler` interface is deliberately small so FSRS can replace SM-2
later without touching the API or stored refs.

Anything reviewable is a *ref* string:
    flashcard:<uuid>   — card in output_files/flashcards
    q:<question_id>    — question-bank item (missed exam questions auto-enrol)
    pearl:<id>         — pearl (resolver TODO)

Per-user state lives in one doc (v2:srs:<email>) = {ref: CardState}.
Fine up to a few thousand cards; a Postgres table is the long-term home.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .store import store, utcnow, iso, parse_iso

AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4
LEARNING_STEPS_MIN = [1, 10]      # minutes, for new/lapsed cards
GRADUATING_INTERVAL_D = 1
EASY_INTERVAL_D = 4
MIN_EASE, START_EASE = 1.3, 2.5


@dataclass
class CardState:
    ref: str
    subject: str = ""
    system: str = ""
    ease: float = START_EASE
    interval_d: float = 0.0
    reps: int = 0
    lapses: int = 0
    step: int = 0                 # index into LEARNING_STEPS_MIN while learning
    phase: str = "new"            # new | learning | review | relearning
    due: str = field(default_factory=iso)
    last_review: Optional[str] = None
    suspended: bool = False


class SM2Scheduler:
    def review(self, c: CardState, grade: int, now: Optional[datetime] = None) -> CardState:
        if grade not in (AGAIN, HARD, GOOD, EASY):
            raise ValueError("grade must be 1-4")
        now = now or utcnow()
        c.reps += 1
        c.last_review = iso(now)

        if c.phase in ("new", "learning", "relearning"):
            if grade == AGAIN:
                c.step = 0
                c.phase = "learning" if c.phase == "new" else c.phase
                due = now + timedelta(minutes=LEARNING_STEPS_MIN[0])
            elif grade == EASY:
                c.phase, c.interval_d = "review", float(EASY_INTERVAL_D)
                due = now + timedelta(days=c.interval_d)
            else:
                nxt = c.step + (1 if grade == GOOD else 0)
                if nxt >= len(LEARNING_STEPS_MIN):
                    c.phase = "review"
                    c.interval_d = max(c.interval_d, float(GRADUATING_INTERVAL_D)) if c.lapses else float(GRADUATING_INTERVAL_D)
                    due = now + timedelta(days=c.interval_d)
                else:
                    c.step = nxt
                    c.phase = "learning" if c.phase == "new" else c.phase
                    due = now + timedelta(minutes=LEARNING_STEPS_MIN[nxt])
        else:  # review
            if grade == AGAIN:
                c.lapses += 1
                c.ease = max(MIN_EASE, c.ease - 0.2)
                c.interval_d = max(1.0, c.interval_d * 0.5)
                c.phase, c.step = "relearning", 0
                due = now + timedelta(minutes=LEARNING_STEPS_MIN[0])
            else:
                if grade == HARD:
                    c.ease = max(MIN_EASE, c.ease - 0.15)
                    c.interval_d = max(c.interval_d + 1, c.interval_d * 1.2)
                elif grade == GOOD:
                    c.interval_d = max(c.interval_d + 1, c.interval_d * c.ease)
                else:
                    c.ease += 0.15
                    c.interval_d = max(c.interval_d + 1, c.interval_d * c.ease * 1.3)
                c.interval_d = min(c.interval_d, 365.0)
                due = now + timedelta(days=c.interval_d)
        c.due = iso(due)
        return c


scheduler = SM2Scheduler()


# ---- per-user deck ----------------------------------------------------------

def _load(email: str) -> Dict[str, dict]:
    return store.get("srs", email, default={}) or {}


def _save(email: str, deck: Dict[str, dict]):
    store.put("srs", email, value=deck)


def enroll(email: str, refs: List[dict]) -> int:
    """refs: [{"ref": "flashcard:...", "subject": "ccm", "system": "Sepsis"}]. Idempotent."""
    deck = _load(email)
    added = 0
    for r in refs:
        ref = r.get("ref") if isinstance(r, dict) else str(r)
        if not ref or ref in deck:
            continue
        meta = r if isinstance(r, dict) else {}
        deck[ref] = asdict(CardState(ref=ref, subject=meta.get("subject", ""), system=meta.get("system", "")))
        added += 1
    if added:
        _save(email, deck)
    return added


def review(email: str, ref: str, grade: int, now: Optional[datetime] = None) -> dict:
    deck = _load(email)
    if ref not in deck:
        deck[ref] = asdict(CardState(ref=ref))
    state = scheduler.review(CardState(**deck[ref]), grade, now=now)
    deck[ref] = asdict(state)
    _save(email, deck)
    _log_review(email, ref, grade)
    return deck[ref]


def _log_review(email: str, ref: str, grade: int):
    day = utcnow().strftime("%Y-%m-%d")
    store.update("srs_log", email, day, fn=lambda cur: (cur or []) + [{"ref": ref, "g": grade, "t": iso()}], default=[])


def queue(email: str, subject: str = "", limit: int = 50, new_limit: int = 20, now: Optional[datetime] = None) -> List[dict]:
    now = now or utcnow()
    deck = [c for c in _load(email).values() if not c.get("suspended")]
    if subject:
        deck = [c for c in deck if c.get("subject") == subject]
    due = sorted([c for c in deck if c["phase"] != "new" and parse_iso(c["due"]) <= now], key=lambda c: c["due"])
    new = [c for c in deck if c["phase"] == "new"][:new_limit]
    return (due + new)[:limit]


def stats(email: str, now: Optional[datetime] = None) -> dict:
    now = now or utcnow()
    deck = list(_load(email).values())
    by_phase: Dict[str, int] = {}
    for c in deck:
        by_phase[c["phase"]] = by_phase.get(c["phase"], 0) + 1
    due_now = sum(1 for c in deck if c["phase"] != "new" and parse_iso(c["due"]) <= now)
    return {"total": len(deck), "due_now": due_now, "by_phase": by_phase,
            "mature": sum(1 for c in deck if c.get("interval_d", 0) >= 21)}
