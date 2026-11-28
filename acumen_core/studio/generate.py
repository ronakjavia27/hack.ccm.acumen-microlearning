"""Studio pipelines (question items and note items), with LLM call caps.

Questions: compose → derive → verify (+ blind MCQ solve) → lint → triage → revise.
Notes:     polish (your note, formatting only) → derive_note (Q&A, cards, MCQs) → verify + blind → lint →
           triage → revise_note (Q&A/cards/MCQs only — the author's theory is never auto-revised).

The LLM is injectable (`set_llm`) so tests and dry runs never touch the network.
llm(role, system, user, max_tokens) -> dict. Draft roles use STUDIO_DRAFT_MODEL; verify/blind use
STUDIO_VERIFY_MODEL. Every call is counted against STUDIO_MAX_CALLS_PER_RUN / _PER_DAY (studio/usage.json);
hitting a cap raises CapReached and leaves the item queued, never in error.
"""
from __future__ import annotations

import json
import traceback
from datetime import datetime, timedelta
from typing import Callable, List, Optional

from acumen_core import config
from acumen_core.tracking import load_json_safe, save_json_atomic

from . import checks, items as store, prompts, retrieve

DRAFT_ROLES = {"compose", "derive", "revise", "polish", "derive_note", "revise_note"}
MAX_ATTEMPTS = 3          # error items are retried automatically at most this many times
LLMFn = Callable[[str, str, str, int], dict]


def model_for(role: str) -> str:
    return config.STUDIO_DRAFT_MODEL if role in DRAFT_ROLES else config.STUDIO_VERIFY_MODEL


def default_llm(role: str, system: str, user: str, max_tokens: int) -> dict:
    from acumen_core.llm import execute_openai_compat
    return execute_openai_compat(system, user, api_key=config.STUDIO_API_KEY, model=model_for(role),
                                 base_url=config.STUDIO_BASE_URL,
                                 temperature=0.1 if role in ("verify", "blind") else 0.3,
                                 max_tokens=max_tokens, json_mode=True)


_llm: LLMFn = default_llm


def set_llm(fn: Optional[LLMFn]):
    global _llm
    _llm = fn or default_llm


class CapReached(RuntimeError):
    """LLM call budget for this run or today is used up."""


_RUN_CALLS = 0


def reset_run_counter():
    global _RUN_CALLS
    _RUN_CALLS = 0


def usage_today() -> dict:
    data = load_json_safe(config.STUDIO_USAGE_FILE, default={}) or {}
    return data.get(datetime.now().strftime("%Y-%m-%d"), {"calls": 0, "by_role": {}})


def _count_call(role: str):
    global _RUN_CALLS
    data = load_json_safe(config.STUDIO_USAGE_FILE, default={}) or {}
    day = datetime.now().strftime("%Y-%m-%d")
    d = data.setdefault(day, {"calls": 0, "by_role": {}})
    if _RUN_CALLS >= config.STUDIO_MAX_CALLS_PER_RUN:
        raise CapReached(f"per-run cap of {config.STUDIO_MAX_CALLS_PER_RUN} LLM calls reached")
    if d["calls"] >= config.STUDIO_MAX_CALLS_PER_DAY:
        raise CapReached(f"daily cap of {config.STUDIO_MAX_CALLS_PER_DAY} LLM calls reached")
    _RUN_CALLS += 1
    d["calls"] += 1
    d["by_role"][role] = d["by_role"].get(role, 0) + 1
    cutoff = (datetime.now() - timedelta(days=31)).strftime("%Y-%m-%d")
    data = {k: v for k, v in data.items() if k >= cutoff}
    import os
    os.makedirs(os.path.dirname(config.STUDIO_USAGE_FILE), exist_ok=True)
    save_json_atomic(config.STUDIO_USAGE_FILE, data)


def _call(role: str, system: str, user: str, max_tokens: int = None) -> dict:
    _count_call(role)
    out = _llm(role, system, user, max_tokens or config.STUDIO_MAX_TOKENS)
    if not isinstance(out, dict):
        raise ValueError(f"{role}: model did not return a JSON object")
    return out


# ---- normalisation ----------------------------------------------------------

def _as_list(x) -> list:
    return x if isinstance(x, list) else ([] if x in (None, "") else [x])


def _int_list(x) -> List[int]:
    out = []
    for v in _as_list(x):
        try:
            out.append(int(v))
        except (TypeError, ValueError):
            continue
    return out


def normalize_package(item: dict, pkg: dict) -> dict:
    """Coerce model output into the package schema and map taxonomy onto subtopics.json."""
    p = {
        "title": str(pkg.get("title") or item["question"][:80]).strip(),
        "system": str(pkg.get("system") or item.get("system") or "").strip(),
        "subtopic": str(pkg.get("subtopic") or item.get("subtopic") or "").strip(),
        "answer_md": str(pkg.get("answer_md") or "").strip(),
        "key_points": [str(k) for k in _as_list(pkg.get("key_points"))],
        "rubric": [r for r in _as_list(pkg.get("rubric")) if isinstance(r, dict)],
        "claims": [c for c in _as_list(pkg.get("claims")) if isinstance(c, dict)],
        "uncertainties": [str(u) for u in _as_list(pkg.get("uncertainties")) if str(u).strip()],
        "flashcards": [c for c in _as_list(pkg.get("flashcards")) if isinstance(c, dict)],
        "mcqs": [],
    }
    for m in _as_list(pkg.get("mcqs")):
        if isinstance(m, dict):
            p["mcqs"].append({"stem": str(m.get("stem") or "").strip(), "options": [str(o) for o in _as_list(m.get("options"))],
                              "answer": _int_list(m.get("answer")), "explanation": str(m.get("explanation") or ""),
                              "difficulty": int(m.get("difficulty") or 3) if str(m.get("difficulty") or "3").isdigit() else 3})
    if item.get("options"):
        p["mcq_key"] = _int_list(pkg.get("mcq_key"))
    p["system"], p["subtopic"] = canonical_taxonomy(item, p["system"], p["subtopic"])
    return p


SYSTEM_ALIASES = {
    "respiratory": "pulmonology", "respiratory medicine": "pulmonology", "pulmonary": "pulmonology",
    "cardiovascular": "cardiology", "cvs": "cardiology", "renal": "nephrology", "kidney": "nephrology",
    "neuro": "neurology", "neurocritical care": "neurology", "cns": "neurology",
    "gi": "gastroenterology", "gastrointestinal": "gastroenterology", "liver": "hepatology",
    "endocrine": "endocrinology", "haematology": "hematology", "blood": "hematology",
    "microbiology": "infectious diseases", "infection": "infectious diseases", "infectious disease": "infectious diseases",
    "id": "infectious diseases", "antimicrobials": "infectious diseases",
    "critical care": "multisystem", "critical care medicine": "multisystem", "icu": "multisystem",
    "poisoning": "toxicology", "obstetrics": "obstetrics and gynecology", "obstetrics & gynaecology": "obstetrics and gynecology",
    "rheumatology & immunology": "rheumatology", "nutrition & metabolism": "nutrition",
}


def canonical_taxonomy(item: dict, system: str, subtopic: str):
    """Map a model-suggested system/subtopic onto acumen_core/subtopics.json."""
    try:
        from acumen_core.subtopics_config import load_subtopics
        vocab = load_subtopics() or {}
    except Exception:
        vocab = {}
    from acumen_core.flashcards import normalize_subtopic
    systems = {s.lower(): s for s in vocab}
    want = (item.get("system") or system or "").strip().lower()
    want = SYSTEM_ALIASES.get(want, want)
    sub_cand = item.get("subtopic") or subtopic
    sys_ = systems.get(want)
    if sys_ in ("Multisystem", "Other") and sub_cand and not normalize_subtopic(sys_, sub_cand):
        sys_ = None   # generic bucket → prefer a specific system that owns this subtopic
    if not sys_ and vocab and sub_cand:
        # unknown system name → find the system whose vocab contains this subtopic
        sys_ = next((s for s in vocab if normalize_subtopic(s, sub_cand)), None)
    if not sys_:
        default = {"microbiology": "Infectious Diseases", "ccm": "Multisystem", "medicine": "Multisystem"}
        sys_ = default.get(item["subject"], "Other") if vocab else (system or "General")
    sub = normalize_subtopic(sys_, sub_cand) or sub_cand or sys_
    return sys_, sub


NOTE_QTYPES = ("long", "short", "very_short", "viva")


def normalize_note_package(item: dict, pkg: dict) -> dict:
    """Note packages: theory_md (the author's note) + qna + flashcards + mcqs + claims."""
    base = normalize_package(item, {**pkg, "answer_md": pkg.get("theory_md") or item.get("note_md", "")})
    base["theory_md"] = base.pop("answer_md")
    base.pop("rubric", None)
    base["edits"] = [str(e) for e in _as_list(pkg.get("edits")) if str(e).strip()]
    base["qna"] = []
    for q in _as_list(pkg.get("qna")):
        if not isinstance(q, dict) or not str(q.get("question") or "").strip():
            continue
        marks = int(q["marks"]) if str(q.get("marks") or "").strip().isdigit() else None
        qt = q.get("qtype") if q.get("qtype") in NOTE_QTYPES else ("long" if (marks or 0) >= 10 else "short")
        base["qna"].append({"question": str(q["question"]).strip(), "qtype": qt, "marks": marks,
                            "answer_md": str(q.get("answer_md") or "").strip(),
                            "rubric": [r for r in _as_list(q.get("rubric")) if isinstance(r, dict)]})
    return base


def normalize_any(item: dict, pkg: dict) -> dict:
    return normalize_note_package(item, pkg) if item.get("kind") == "note" else normalize_package(item, pkg)


# ---- stages -----------------------------------------------------------------

def compose(item, context):
    return _call("compose", prompts.COMPOSE_SYSTEM, prompts.compose_user(item, context))


def derive(item, package):
    return _call("derive", prompts.DERIVE_SYSTEM, prompts.derive_user(item, package), max_tokens=6000)


def verify(item, package, context):
    """Returns (verification|None, blind|None, error_note)."""
    ver = blind = None
    note = ""
    user = (prompts.verify_note_user if item.get("kind") == "note" else prompts.verify_user)(item, package, context)
    try:
        ver = _call("verify", prompts.VERIFY_SYSTEM, user, max_tokens=6000)
    except CapReached:
        raise
    except Exception as e:
        note = f"verify failed: {e}"
    if package.get("mcqs"):
        try:
            blind = _call("blind", prompts.BLIND_SYSTEM, prompts.blind_user(package["mcqs"]), max_tokens=2000)
        except CapReached:
            raise
        except Exception as e:
            note += f" blind-solve failed: {e}"
    return ver, blind, note.strip()


def revise(item, package, problems, context):
    return _call("revise", prompts.REVISE_SYSTEM, prompts.revise_user(item, package, problems, context))


def assess(item, package, context):
    ver, blind, note = verify(item, package, context)
    lint_res = checks.lint(item, package)
    tri, reasons = checks.triage(item, package, ver, blind, lint_res)
    if note:
        reasons = [note] + reasons
    return ver, blind, lint_res, tri, reasons


# ---- item-level entry points ---------------------------------------------------

def _ctx_meta(context):
    return [{k: c[k] for k in ("id", "kind", "title", "score")} for c in context]


def _finish(item, package, ver, blind, lint_res, tri, reasons, rounds, context, note, extra=None):
    store.add_version(item, {
        "origin": "ai", "models": {"draft": config.STUDIO_DRAFT_MODEL, "verify": config.STUDIO_VERIFY_MODEL},
        "package": package, "verification": ver, "blind": blind, "lint": lint_res,
        "triage": tri, "reasons": reasons, "revisions": rounds, "editor_note": note,
        "context": _ctx_meta(context), **(extra or {}),
    })
    item["system"] = item.get("system") or package["system"]
    item["subtopic"] = item.get("subtopic") or package["subtopic"]


def _question_pipeline(item, use_context, max_revisions, verbose, note, prev):
    context = retrieve.context_for(item) if use_context else []
    if note and prev:
        # Editor asked for changes on an existing draft → targeted revision, not a rewrite.
        package = normalize_package(item, revise(item, prev["package"], [f"Editor's request: {note}"], context))
    else:
        package = normalize_package(item, compose(item, context))
        derived = derive(item, package)
        package = normalize_package(item, {**package, "flashcards": derived.get("flashcards"),
                                           "mcqs": derived.get("mcqs")})
    ver, blind, lint_res, tri, reasons = assess(item, package, context)
    rounds = 0
    while tri != "green" and rounds < max_revisions:
        problems = checks.problems_for_revision(package, ver, blind, lint_res)
        if not problems:
            break
        if verbose:
            print(f"    revise round {rounds + 1}: {len(problems)} problems")
        package = normalize_package(item, revise(item, package, problems, context))
        ver, blind, lint_res, tri, reasons = assess(item, package, context)
        rounds += 1
    _finish(item, package, ver, blind, lint_res, tri, reasons, rounds, context, note)


def _note_pipeline(item, use_context, max_revisions, verbose, note, prev):
    context = retrieve.context_for(item, k=3) if use_context else []   # hints for the verifier only
    if note and prev:
        # The author's own change request may touch the theory text.
        raw = _call("revise_note", prompts.REVISE_NOTE_EDITOR_SYSTEM,
                    prompts.revise_note_user(item, prev["package"], [note], context, editor=True))
        package = normalize_note_package(item, raw)
    else:
        polished = normalize_note_package(item, _call("polish", prompts.POLISH_SYSTEM, prompts.polish_user(item)))
        der = _call("derive_note", prompts.DERIVE_NOTE_SYSTEM, prompts.derive_note_user(item, polished), max_tokens=12000)
        package = normalize_note_package(item, {**polished, "qna": der.get("qna"), "flashcards": der.get("flashcards"),
                                                "mcqs": der.get("mcqs")})
    ver, blind, lint_res, tri, reasons = assess(item, package, context)
    rounds = 0
    while tri != "green" and rounds < max_revisions:
        problems = checks.problems_for_revision(package, ver, blind, lint_res, locked=checks.LOCKED_NOTE_PARTS)
        if not problems:
            break                       # only theory issues left → those are the author's call
        if verbose:
            print(f"    revise round {rounds + 1}: {len(problems)} problems (Q&A/cards/MCQs only)")
        fixed = _call("revise_note", prompts.REVISE_NOTE_SYSTEM,
                      prompts.revise_note_user(item, package, problems, context, editor=False))
        package = normalize_note_package(item, {**package, **{k: fixed[k] for k in ("qna", "flashcards", "mcqs")
                                                               if fixed.get(k) is not None}})
        ver, blind, lint_res, tri, reasons = assess(item, package, context)
        rounds += 1
    _finish(item, package, ver, blind, lint_res, tri, reasons, rounds, context, note,
            extra={"polish_diff": checks.polish_diff(item.get("note_md", ""), package["theory_md"]),
                   "polish_change": round(checks.polish_change_ratio(item.get("note_md", ""), package["theory_md"]), 3),
                   "note_sha": item.get("note_sha")})


def generate_item(item: dict, use_context: bool = True, max_revisions: int = None, by: str = "studio",
                  verbose: bool = False, save: bool = True) -> dict:
    """Run the right pipeline on one item and append a new version.

    Model/parse failures put the item in `error` (retried up to MAX_ATTEMPTS by the watcher).
    Only CapReached propagates — the item goes back to its previous queue status first."""
    max_revisions = config.STUDIO_MAX_REVISIONS if max_revisions is None else max_revisions
    note = (item.get("revision_note") or "").strip()
    prev = store.current_version(item)
    prev_status = item.get("status")
    store.transition(item, "generating", by, note)
    if save:
        store.save(item)
    try:
        pipeline = _note_pipeline if item.get("kind") == "note" else _question_pipeline
        pipeline(item, use_context, max_revisions, verbose, note, prev)
        item["revision_note"] = ""
        item["attempts"] = 0
        item.pop("error", None)
        store.transition(item, "generated", by, f"triage={item['triage']}")
    except CapReached as e:
        back = prev_status if prev_status in ("queued", "revision_requested") else "queued"
        store.transition(item, back, by, f"not generated: {e}")
        if save:
            store.save(item)
        raise
    except Exception as e:
        item["error"] = f"{type(e).__name__}: {e}"
        item["attempts"] = int(item.get("attempts") or 0) + 1
        if verbose:
            traceback.print_exc()
        store.transition(item, "error", by, item["error"])
    if save:
        store.save(item)
    return item


def reverify_item(item: dict, by: str = "studio", save: bool = True) -> dict:
    """Fresh independent check of the current version (e.g. after a human edit)."""
    cur = store.current_version(item)
    if not cur:
        raise ValueError("nothing to verify")
    context = retrieve.context_for(item, k=3 if item.get("kind") == "note" else None)
    ver, blind, lint_res, tri, reasons = assess(item, cur["package"], context)
    store.add_version(item, {**{k: cur[k] for k in ("origin", "models", "package") if k in cur},
                             "verification": ver, "blind": blind, "lint": lint_res, "triage": tri,
                             "reasons": reasons, "revisions": 0, "reverified_from": cur["v"],
                             "context": [{k: c[k] for k in ("id", "kind", "title", "score")} for c in context]})
    if item["status"] != "generated":
        store.transition(item, "generated", by, "re-verified")
    if save:
        store.save(item)
    return item


def human_edit(item: dict, package: dict, by: str, note: str = "", save: bool = True) -> dict:
    """Store an editor's version. Lint-only triage; approval is still a separate step."""
    package = normalize_any(item, package)
    lint_res = checks.lint(item, package)
    tri, reasons = checks.triage(item, package, None, None, lint_res, human=True)
    prev = store.current_version(item) or {}
    store.add_version(item, {"origin": "human", "edited_by": by, "models": prev.get("models"),
                             "package": package, "verification": None, "blind": None, "lint": lint_res,
                             "triage": tri, "reasons": ["Human-edited (not re-verified)"] + reasons,
                             "editor_note": note, "context": prev.get("context", [])})
    if item["status"] != "generated":
        store.transition(item, "generated", by, "edited")
    if save:
        store.save(item)
    return item


def generate_pending(max_items: int = 0, subject: str = "", verbose: bool = False, dry_run: bool = False,
                     use_context: bool = True, retry_errors: bool = True) -> dict:
    """Generate queued / revision-requested items (and error items with attempts left). Stops at a call cap."""
    reset_run_counter()
    todo = []
    for it in store.all_items(subject):
        if it["status"] in ("queued", "revision_requested"):
            todo.append(it)
        elif it["status"] == "error" and retry_errors and int(it.get("attempts") or 0) < MAX_ATTEMPTS:
            todo.append(it)
    todo.sort(key=lambda it: (it["status"] != "revision_requested", it.get("created_at") or ""))  # your requests first
    if max_items:
        todo = todo[:max_items]
    res = {"processed": 0, "green": 0, "amber": 0, "red": 0, "error": 0, "ids": [], "pending": len(todo),
           "capped": ""}
    for it in todo:
        if dry_run:
            print(f"  [dry-run] would generate {it['id']} ({it.get('kind', 'question')}): {it['question'][:80]}")
            continue
        if verbose:
            print(f"  → {it['id']} ({it['qtype']}): {it['question'][:80]}")
        try:
            generate_item(it, use_context=use_context, verbose=verbose)
        except CapReached as e:
            res["capped"] = str(e)
            if verbose:
                print(f"  [=] {e} — remaining items stay queued")
            break
        res["processed"] += 1
        res["ids"].append(it["id"])
        key = it["triage"] if it["status"] == "generated" else "error"
        res[key] = res.get(key, 0) + 1
        if verbose:
            print(f"     {it['status']} · {it.get('triage')}" + (f" · {it.get('error')}" if it["status"] == "error" else ""))
    return res
