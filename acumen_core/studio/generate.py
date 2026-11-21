"""Studio pipeline: compose → derive → verify (+ blind MCQ solve) → lint → triage → revise.

The LLM is injectable (`set_llm`) so tests and dry runs never touch the network.
llm(role, system, user, max_tokens) -> dict, role ∈ compose|derive|verify|blind|revise.
compose/derive/revise use STUDIO_DRAFT_MODEL; verify/blind use STUDIO_VERIFY_MODEL.
"""
from __future__ import annotations

import json
import traceback
from typing import Callable, List, Optional

from acumen_core import config

from . import checks, items as store, prompts, retrieve

DRAFT_ROLES = {"compose", "derive", "revise"}
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


def _call(role: str, system: str, user: str, max_tokens: int = None) -> dict:
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


# ---- stages -----------------------------------------------------------------

def compose(item, context):
    return _call("compose", prompts.COMPOSE_SYSTEM, prompts.compose_user(item, context))


def derive(item, package):
    return _call("derive", prompts.DERIVE_SYSTEM, prompts.derive_user(item, package), max_tokens=6000)


def verify(item, package, context):
    """Returns (verification|None, blind|None, error_note)."""
    ver = blind = None
    note = ""
    try:
        ver = _call("verify", prompts.VERIFY_SYSTEM, prompts.verify_user(item, package, context), max_tokens=6000)
    except Exception as e:
        note = f"verify failed: {e}"
    if package.get("mcqs"):
        try:
            blind = _call("blind", prompts.BLIND_SYSTEM, prompts.blind_user(package["mcqs"]), max_tokens=2000)
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

def generate_item(item: dict, use_context: bool = True, max_revisions: int = None, by: str = "studio",
                  verbose: bool = False, save: bool = True) -> dict:
    """Run the full pipeline on one item; appends a new version. Never raises."""
    max_revisions = config.STUDIO_MAX_REVISIONS if max_revisions is None else max_revisions
    note = (item.get("revision_note") or "").strip()
    prev = store.current_version(item)
    store.transition(item, "generating", by, note)
    if save:
        store.save(item)
    try:
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
        store.add_version(item, {
            "origin": "ai", "models": {"draft": config.STUDIO_DRAFT_MODEL, "verify": config.STUDIO_VERIFY_MODEL},
            "package": package, "verification": ver, "blind": blind, "lint": lint_res,
            "triage": tri, "reasons": reasons, "revisions": rounds, "editor_note": note,
            "context": [{k: c[k] for k in ("id", "kind", "title", "score")} for c in context],
        })
        item["system"], item["subtopic"] = item.get("system") or package["system"], item.get("subtopic") or package["subtopic"]
        item["revision_note"] = ""
        store.transition(item, "generated", by, f"triage={tri}")
    except Exception as e:
        item["error"] = f"{type(e).__name__}: {e}"
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
    context = retrieve.context_for(item)
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
    package = normalize_package(item, package)
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
                     use_context: bool = True) -> dict:
    todo = [it for it in store.all_items(subject) if it["status"] in ("queued", "revision_requested", "error")]
    if max_items:
        todo = todo[:max_items]
    res = {"processed": 0, "green": 0, "amber": 0, "red": 0, "error": 0, "ids": []}
    for it in todo:
        if dry_run:
            print(f"  [dry-run] would generate {it['id']}: {it['question'][:80]}")
            continue
        if verbose:
            print(f"  → {it['id']} ({it['qtype']}): {it['question'][:80]}")
        generate_item(it, use_context=use_context, verbose=verbose)
        res["processed"] += 1
        res["ids"].append(it["id"])
        key = it["triage"] if it["status"] == "generated" else "error"
        res[key] = res.get(key, 0) + 1
        if verbose:
            print(f"     {it['status']} · {it.get('triage')}" + (f" · {it.get('error')}" if it["status"] == "error" else ""))
    return res
