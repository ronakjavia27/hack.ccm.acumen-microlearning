"""Deterministic lint + traffic-light triage for Studio packages (no LLM)."""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

_NUM_UNIT = re.compile(
    r"\b\d+(?:\.\d+)?\s?(?:%|mg|mcg|µg|ug|g|kg|ml|l|mmol|meq|units?|iu|mmhg|cmh2o|mosm|h|hrs?|hours?|minutes?|mins?|days?|weeks?)\b",
    re.I)
_DOSE = re.compile(r"\b\d+(?:\.\d+)?\s?(?:mg|mcg|µg|ug|g|units?|iu|mmol|meq)(?:\s?/\s?kg)?(?:\s?/\s?(?:h|hr|min|day|d))?\b", re.I)
_AOTA = re.compile(r"\b(all|none|both)\s+of\s+the\s+above\b", re.I)
_BOILER = re.compile(r"\bas an ai\b|\bi cannot\b|\bconsult (?:a|your) (?:doctor|physician)\b", re.I)


_UNIT_ALIASES = [(r"(hours?|hrs?)$", "h"), (r"(minutes?|mins?)$", "min"), (r"days?$", "d"), (r"weeks?$", "wk"),
                 (r"units?$", "u"), (r"(µg|ug)$", "mcg")]


def _norm_num(s: str) -> str:
    t = re.sub(r"\s+", "", s.lower())
    for pat, rep in _UNIT_ALIASES:
        t = re.sub(pat, rep, t)
    return t


def numbers(text: str) -> set:
    return {_norm_num(m.group(0)) for m in _NUM_UNIT.finditer(text or "")}


POLISH_CHANGE_LIMIT = 0.15


def polish_change_ratio(original: str, polished: str) -> float:
    """Share of the note's wording changed by polishing (whitespace/markdown markers ignored)."""
    import difflib
    norm = lambda t: re.sub(r"[#*_>|`\-]+", " ", (t or "").lower()).split()
    a, b = norm(original), norm(polished)
    if not a:
        return 0.0
    return 1.0 - difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def polish_diff(original: str, polished: str) -> str:
    import difflib
    return "\n".join(difflib.unified_diff((original or "").splitlines(), (polished or "").splitlines(),
                                           "your note", "published theory", lineterm="", n=1))


def expected_words(item: dict) -> Tuple[int, int]:
    qt, marks = item.get("qtype"), item.get("marks")
    if qt == "long":
        m = marks or 10
        return int(m * 55), int(m * 150)
    return {"short": (180, 750), "very_short": (40, 300), "viva": (70, 450), "mcq": (60, 500)}.get(qt, (150, 900))


def lint(item: dict, pkg: dict) -> List[dict]:
    out: List[dict] = []

    def add(sev, where, code, msg):
        out.append({"severity": sev, "where": where, "code": code, "msg": msg})

    is_note = item.get("kind") == "note"
    ans = (pkg.get("theory_md") if is_note else pkg.get("answer_md")) or ""
    main = "theory" if is_note else "answer"
    if not ans.strip():
        add("error", main, "empty_answer", "Theory note is empty" if is_note else "Answer is empty")
    if not is_note:
        words = len(ans.split())
        lo, hi = expected_words(item)
        if ans and not lo <= words <= hi:
            add("warn", "answer", "length", f"{words} words; expected {lo}–{hi} for {item.get('qtype')}"
                + (f" ({item['marks']} marks)" if item.get("marks") else ""))
    if _BOILER.search(ans):
        add("warn", main, "boilerplate", "Contains AI/disclaimer boilerplate")

    reference = ans
    if is_note:
        ratio = polish_change_ratio(item.get("note_md", ""), ans)
        if ratio > POLISH_CHANGE_LIMIT:
            add("warn", "theory", "polish_changed",
                f"Polish changed {round(ratio * 100)}% of your note — check the diff (should be formatting only)")
        qna = pkg.get("qna") or []
        if not qna:
            add("warn", "qna", "no_qna", "No exam questions derived")
        for i, q in enumerate(qna):
            a = (q.get("answer_md") or "").strip()
            if not (q.get("question") or "").strip() or not a:
                add("error", f"qna:{i}", "qna_empty", "Question or answer missing")
                continue
            lo, hi = expected_words({"qtype": q.get("qtype"), "marks": q.get("marks")})
            if not lo <= len(a.split()) <= hi:
                add("warn", f"qna:{i}", "length", f"{len(a.split())} words; expected {lo}–{hi} for {q.get('qtype')}")
            rub = q.get("rubric") or []
            if q.get("marks") and rub and sum(int(r.get("marks") or 0) for r in rub) != int(q["marks"]):
                add("warn", f"qna:{i}", "rubric_sum", f"Rubric sums to {sum(int(r.get('marks') or 0) for r in rub)}, "
                                                     f"question is {q['marks']} marks")
            extra = numbers(a) - numbers(ans)
            if extra:
                add("warn", f"qna:{i}", "number_mismatch", f"Numbers not in your note: {', '.join(sorted(extra))}")
            reference += "\n" + a

    # rubric
    rub = pkg.get("rubric") or []
    if item.get("qtype") not in ("mcq", "note"):
        if not rub:
            add("warn", "rubric", "no_rubric", "No marking rubric")
        elif item.get("marks") and sum(int(r.get("marks") or 0) for r in rub) != item["marks"]:
            add("warn", "rubric", "rubric_sum", f"Rubric marks sum to {sum(int(r.get('marks') or 0) for r in rub)}, "
                                                f"question is {item['marks']}")

    # claims / doses
    claims = pkg.get("claims") or []
    if not claims:
        add("warn", "claims", "no_claims", "No checkable claims listed — verifier has nothing to check")
    doses = _DOSE.findall(ans)
    if doses and not any(c.get("high_stakes") for c in claims):
        add("warn", "claims", "undeclared_doses", f"{len(doses)} dose statements but no high-stakes claims declared")

    # flashcards
    cards = pkg.get("flashcards") or []
    if not cards:
        add("warn", "flashcards", "no_cards", "No flashcards")
    ans_nums = numbers(reference)
    for i, c in enumerate(cards):
        f, b = (c.get("front") or "").strip(), (c.get("back") or "").strip()
        if not f or not b:
            add("error", f"flashcard:{i}", "card_empty", "Flashcard front or back missing")
            continue
        if len(b) > 700:
            add("warn", f"flashcard:{i}", "card_long", f"Back is {len(b)} chars (keep cards atomic)")
        extra = numbers(b) - ans_nums
        if extra:
            add("warn", f"flashcard:{i}", "number_mismatch",
                f"Numbers not in the {'note' if is_note else 'answer'}: {', '.join(sorted(extra))}")

    # MCQs
    for i, m in enumerate(pkg.get("mcqs") or []):
        where = f"mcq:{i}"
        opts = m.get("options") or []
        key = m.get("answer") or []
        if len((m.get("stem") or "").strip()) < 15:
            add("error", where, "mcq_stem", "Stem missing or too short")
        if not 4 <= len(opts) <= 5:
            add("error", where, "mcq_options", f"{len(opts)} options (need 4–5)")
        if len({str(o).strip().lower() for o in opts}) != len(opts):
            add("error", where, "mcq_dup_options", "Duplicate options")
        if not key or any(not isinstance(k, int) or not 0 <= k < len(opts) for k in key):
            add("error", where, "mcq_key", f"Answer key {key} invalid")
        elif len(key) != 1:
            add("error", where, "mcq_single", "Single-best-answer MCQ must have exactly one key")
        if any(_AOTA.search(str(o)) for o in opts):
            add("warn", where, "mcq_aota", "Uses all/none/both of the above")
        if key and all(isinstance(k, int) and 0 <= k < len(opts) for k in key):
            extra = numbers(" ".join(str(opts[k]) for k in key)) - ans_nums
            if extra:
                add("warn", where, "number_mismatch", f"Correct option has numbers not in the answer: {', '.join(sorted(extra))}")

    # uploaded MCQ key vs model
    if item.get("options"):
        mk = pkg.get("mcq_key")
        if not mk:
            add("error", "answer", "mcq_key_missing", "Model did not give a key for the uploaded MCQ")
        elif item.get("given_key") and sorted(mk) != sorted(item["given_key"]):
            add("error", "answer", "upload_key_disagrees",
                f"Uploaded key {item['given_key']} ≠ model key {mk} — decide which is right")

    # PHI (case-based questions sometimes carry identifiers)
    try:
        from acumen_platform import deid
        for where, text in (("question", item.get("question", "")), (main, ans)):
            highs = [f for f in deid.scan(text) if f.severity == "high"]
            if highs:
                add("error", where, "phi", "Possible patient identifiers: " + ", ".join(f.kind for f in highs))
    except Exception:
        pass
    return out


def blind_mismatches(pkg: dict, blind: Optional[dict]) -> List[dict]:
    if not blind:
        return []
    by_i = {a.get("i"): a for a in blind.get("answers") or []}
    out = []
    for i, m in enumerate(pkg.get("mcqs") or []):
        a = by_i.get(i)
        if not a:
            continue
        if sorted(a.get("chosen") or []) != sorted(m.get("answer") or []) or a.get("ambiguous"):
            out.append({"i": i, "key": m.get("answer"), "chosen": a.get("chosen"),
                        "ambiguous": bool(a.get("ambiguous")), "note": a.get("note", "")})
    return out


def triage(item: dict, pkg: dict, ver: Optional[dict], blind: Optional[dict], lint_res: List[dict],
           human: bool = False) -> Tuple[str, List[str]]:
    red, amber = [], []
    claims = pkg.get("claims") or []
    if ver is None and not human:
        red.append("Verifier unavailable — not independently checked")
    if ver:
        for cc in ver.get("claim_checks") or []:
            i, verdict = cc.get("i"), cc.get("verdict")
            c = claims[i] if isinstance(i, int) and 0 <= i < len(claims) else {}
            label = (c.get("text") or f"claim {i}")[:90]
            if verdict == "incorrect":
                red.append(f"Incorrect: {label}")
            elif verdict in ("outdated", "unverifiable") and c.get("high_stakes"):
                amber.append(f"{verdict.capitalize()} high-stakes: {label}")
            elif verdict == "outdated":
                amber.append(f"Outdated: {label}")
        issues = ver.get("issues") or []
        for iss in issues:
            if iss.get("severity") == "major":
                red.append(f"Major [{iss.get('where')}]: {str(iss.get('problem'))[:120]}")
        minors = [x for x in issues if x.get("severity") != "major"]
        if len(minors) > 2:
            amber.append(f"{len(minors)} minor issues")
        if ver.get("overall") is not None and ver["overall"] < 80:
            amber.append(f"Verifier score {ver.get('overall')}")
        cov = (ver.get("coverage") or {}).get("score")
        if cov is not None and cov < 70:
            amber.append(f"Coverage {cov}")
    for mm in blind_mismatches(pkg, blind):
        red.append(f"MCQ {mm['i']}: blind solver chose {mm['chosen']} vs key {mm['key']}"
                   + (" (ambiguous)" if mm["ambiguous"] else ""))
    for l in lint_res:
        if l["severity"] == "error":
            red.append(f"Lint [{l['where']}]: {l['msg']}")
        elif l["severity"] == "warn":
            amber.append(f"Lint [{l['where']}]: {l['msg']}")
    if pkg.get("uncertainties"):
        amber.append(f"{len(pkg['uncertainties'])} uncertainties flagged by author model")
    if red:
        return "red", red + amber
    if amber:
        return "amber", amber
    return "green", []


LOCKED_NOTE_PARTS = ("theory", "answer", "claims", "rubric", "question")


def problems_for_revision(pkg: dict, ver: Optional[dict], blind: Optional[dict], lint_res: List[dict],
                          locked: tuple = ()) -> List[str]:
    """Actionable fix list for the reviser. Empty → nothing an LLM can fix.

    `locked` parts (e.g. the author's theory note) are never sent for auto-revision — their issues stay
    flagged for the human."""
    out = []
    claims = pkg.get("claims") or []
    is_locked = lambda where: str(where or "").split(":")[0] in locked
    for cc in ([] if "claims" in locked else (ver or {}).get("claim_checks") or []):
        if cc.get("verdict") in ("incorrect", "outdated"):
            i = cc.get("i")
            text = claims[i].get("text") if isinstance(i, int) and 0 <= i < len(claims) else f"claim {i}"
            out.append(f"Claim {i} is {cc['verdict']}: \"{text}\" — {cc.get('comment', '')} Fix: {cc.get('fix', '')}")
    for iss in (ver or {}).get("issues") or []:
        if is_locked(iss.get("where")):
            continue
        out.append(f"[{iss.get('severity')}] {iss.get('where')}: {iss.get('problem')} Fix: {iss.get('fix', '')}")
    for mm in blind_mismatches(pkg, blind):
        out.append(f"mcq:{mm['i']}: an independent solver chose {mm['chosen']} but the key is {mm['key']}"
                   f"{' and found it ambiguous' if mm['ambiguous'] else ''}. {mm['note']} Make the stem and key unambiguous.")
    missing = ((ver or {}).get("coverage") or {}).get("missing") or []
    if missing and not locked:
        out.append("Add missing key points: " + "; ".join(missing))
    for l in lint_res:
        if is_locked(l["where"]):
            continue
        if l["code"] in ("qna_empty", "mcq_options", "mcq_dup_options", "mcq_key", "mcq_single", "mcq_stem", "mcq_aota",
                         "card_empty", "card_long", "number_mismatch", "length", "rubric_sum", "undeclared_doses",
                         "boilerplate"):
            out.append(f"{l['where']}: {l['msg']}")
    return out
