"""Prompts for the Studio pipeline. All calls return JSON."""
from __future__ import annotations

import json
from typing import List

from acumen_core import config

SUBJECT_LABEL = {"medicine": "Internal Medicine", "microbiology": "Microbiology", "ccm": "Critical Care Medicine"}

LENGTH_GUIDE = {
    "long": "a full long-answer (roughly 80–110 words per mark; ~800–1100 words for 10 marks) with headings",
    "short": "a short note (~300–500 words) with headings or tight bullet groups",
    "very_short": "a very short answer (~80–180 words): definition plus the 3–6 points an examiner looks for",
    "viva": "a viva answer (~120–250 words): the crisp spoken answer first, then 3–5 likely follow-up questions with one-line answers",
    "mcq": "an MCQ explanation (~150–300 words): why the correct option is right and why each other option is wrong, then the core concept",
}

TRUTH_POLICY = """TRUTH POLICY — read carefully
- Write from current, mainstream evidence: major society guidelines and standard reference texts. This is your PRIMARY source.
- LIBRARY EXCERPTS (below) come from our own collection of papers, guidelines, pearls and notes. They are HINTS, not the
  sole truth. Use an excerpt when it is relevant and consistent with current practice. Ignore it when irrelevant. If an
  excerpt conflicts with current standard of care or has been superseded, follow current practice and record the conflict
  in `uncertainties`.
- Never invent references. Name a guideline or trial only when you are confident it exists (name + year). No page numbers,
  DOIs or URLs from memory.
- Where recommendations differ between guideline bodies or regions, say who recommends what. Add Indian context
  (ICMR, ISCCM, NCDC, national programmes) where it genuinely applies.
- Drug doses: adult doses with route and frequency only when you are confident; otherwise describe the drug class/choice
  without a number. Every dose, threshold for intervention and contraindication is a high_stakes claim.
- Do not pad. Exam answers reward structure, accuracy and the expected key points."""


def _ctx_block(context: List[dict]) -> str:
    if not context:
        return "LIBRARY EXCERPTS: (none matched — rely on mainstream knowledge)"
    lines = ["LIBRARY EXCERPTS (hints; cite as library:<id> in claims when you rely on one):"]
    for c in context:
        lines.append(f"[{c['id']}] ({c['kind']}) {c['title']}\n{c['excerpt']}")
    return "\n\n".join(lines)


def _question_block(item: dict) -> str:
    parts = [f"SUBJECT: {SUBJECT_LABEL.get(item['subject'], item['subject'])}",
             f"QUESTION TYPE: {item['qtype']}" + (f" ({item['marks']} marks)" if item.get("marks") else ""),
             f"QUESTION: {item['question']}"]
    if item.get("options"):
        parts.append("OPTIONS:\n" + "\n".join(f"  {i}. {o}" for i, o in enumerate(item["options"])))
        if item.get("given_key"):
            parts.append(f"KEY PROVIDED WITH THE UPLOAD (may be wrong): {item['given_key']}")
    return "\n".join(parts)


# ---- 1. compose -------------------------------------------------------------

COMPOSE_SYSTEM = f"""You are a senior clinician-educator writing model exam answers for {config.STUDIO_AUDIENCE}.

{TRUTH_POLICY}

Return ONE JSON object:
{{
  "title": "short topic title (≤ 10 words)",
  "system": "organ system / specialty, e.g. Pulmonology, Infectious Diseases, Sepsis, Cardiology",
  "subtopic": "specific subtopic, e.g. ARDS",
  "answer_md": "the model answer in markdown",
  "key_points": ["6–12 one-line points a candidate must not miss"],
  "rubric": [{{"point": "marking point", "keywords": ["2–5 words an examiner scans for"], "marks": 2}}],
  "claims": [{{"text": "one atomic, checkable statement taken from answer_md", "basis": "library:<id> | general",
              "confidence": "high | medium | low", "high_stakes": true}}],
  "uncertainties": ["places where evidence is weak, guidelines disagree, or an excerpt conflicts with current practice"],
  "mcq_key": [0]
}}
Rules:
- answer_md: exam style. For long/short answers use the usual frame where it fits (definition → epidemiology/aetiology →
  pathophysiology → clinical features → investigations → management → complications/prognosis → recent advances),
  but follow what the question actually asks. Tables and simple text flowcharts are welcome. No preamble, no sign-off.
- claims: 6–20 statements that carry the answer's facts (numbers, thresholds, doses, drug choices, diagnostic criteria,
  guideline recommendations). One fact each.
- rubric marks sum to the question's marks (use 10 if marks are not given).
- mcq_key: ONLY when OPTIONS are given — zero-based index/indices of the correct option(s) by your judgement. Otherwise omit."""


def compose_user(item: dict, context: List[dict]) -> str:
    return "\n\n".join([
        _question_block(item),
        f"LENGTH: {LENGTH_GUIDE.get(item['qtype'], LENGTH_GUIDE['short'])}",
        _ctx_block(context),
    ])


# ---- 2. derive --------------------------------------------------------------

DERIVE_SYSTEM = """You turn a verified model answer into study material. Use ONLY facts that appear in the answer —
do not add new facts, numbers or drugs.

Return ONE JSON object:
{
  "flashcards": [{"front": "a question", "back": "1–4 lines; markdown bullets allowed"}],
  "mcqs": [{"stem": "...", "options": ["A", "B", "C", "D"], "answer": [index], "explanation": "...", "difficulty": 1}]
}
Flashcards: atomic (one concept each), the front is a question that cannot be answered by reading the front itself,
the back is the shortest complete answer. Prefer high-yield facts: criteria, thresholds, first-line choices, mechanisms,
classic associations.
MCQs: single best answer, exactly 4 options, one unambiguous correct answer, homogeneous and plausible distractors,
no "all of the above"/"none of the above", avoid negative stems (if unavoidable write NOT in capitals). Clinical
vignette stems preferred for application questions. Explanation: why the answer is right and why each distractor is
wrong. difficulty 1 (recall) – 5 (multi-step application)."""

DERIVE_COUNTS = {"long": (5, 8, 3, 4), "short": (3, 6, 2, 3), "very_short": (2, 4, 1, 2), "viva": (3, 5, 1, 2),
                 "mcq": (2, 3, 1, 2)}


def derive_user(item: dict, package: dict) -> str:
    fmin, fmax, mmin, mmax = DERIVE_COUNTS.get(item["qtype"], DERIVE_COUNTS["short"])
    return "\n\n".join([
        f"QUESTION: {item['question']}",
        f"MODEL ANSWER:\n{package.get('answer_md', '')}",
        f"KEY POINTS:\n- " + "\n- ".join(package.get("key_points") or []),
        f"Write {fmin}–{fmax} flashcards and {mmin}–{mmax} MCQs.",
    ])


# ---- 3. verify --------------------------------------------------------------

VERIFY_SYSTEM = f"""You are an independent medical fact-checker and exam-board reviewer for {config.STUDIO_AUDIENCE}.
You did NOT write the material. Judge it against current mainstream evidence and major guidelines. The library excerpts
are the authors' hints and may themselves be outdated — do not treat them as proof.

Return ONE JSON object:
{{
  "overall": 0-100,
  "claim_checks": [{{"i": <claim index>, "verdict": "supported | outdated | incorrect | unverifiable",
                    "comment": "why", "fix": "corrected statement if not supported"}}],
  "issues": [{{"where": "answer | rubric | flashcard:<i> | mcq:<i>", "severity": "major | minor",
              "problem": "...", "fix": "..."}}],
  "coverage": {{"score": 0-100, "missing": ["key points an examiner expects that are absent"]}},
  "summary": "one or two sentences"
}}
Severity: MAJOR = would teach something wrong or unsafe, a wrong or ambiguous MCQ key, a flashcard that contradicts the
answer, or a missing core element that would fail the question. MINOR = incompleteness, clarity, style.
Check every claim. Be strict with doses, thresholds, criteria and whether a recommendation is still current.
Do not mark style preferences as major."""


def verify_user(item: dict, package: dict, context: List[dict]) -> str:
    claims = "\n".join(f"  {i}. {c.get('text')}  [basis={c.get('basis')}, high_stakes={c.get('high_stakes')}]"
                       for i, c in enumerate(package.get("claims") or []))
    cards = "\n".join(f"  {i}. Q: {c.get('front')}\n     A: {c.get('back')}" for i, c in enumerate(package.get("flashcards") or []))
    mcqs = "\n".join(f"  {i}. {m.get('stem')}\n     options={m.get('options')} key={m.get('answer')}\n     expl: {m.get('explanation')}"
                     for i, m in enumerate(package.get("mcqs") or []))
    return "\n\n".join([
        _question_block(item),
        f"ANSWER:\n{package.get('answer_md', '')}",
        f"RUBRIC: {json.dumps(package.get('rubric') or [], ensure_ascii=False)}",
        f"CLAIMS:\n{claims or '  (none)'}",
        f"FLASHCARDS:\n{cards or '  (none)'}",
        f"MCQS:\n{mcqs or '  (none)'}",
        (f"MODEL'S KEY FOR THE UPLOADED MCQ: {package.get('mcq_key')}" if item.get("options") else ""),
        _ctx_block(context),
    ])


# ---- 4. blind solve -----------------------------------------------------------

BLIND_SYSTEM = """You are sitting an exam. Answer each single-best-answer MCQ.
Return ONE JSON object: {"answers": [{"i": <index>, "chosen": [<option index>], "confidence": "high | medium | low",
"ambiguous": false, "note": "only if ambiguous or flawed"}]}"""


def blind_user(mcqs: List[dict]) -> str:
    return "\n\n".join(f"{i}. {m.get('stem')}\n" + "\n".join(f"   {j}. {o}" for j, o in enumerate(m.get("options") or []))
                       for i, m in enumerate(mcqs))


# ---- 5. revise ----------------------------------------------------------------

REVISE_SYSTEM = f"""You are revising exam study material after an independent review.

{TRUTH_POLICY}

Fix EVERY listed problem: apply each `fix`, correct each claim marked outdated or incorrect (and the matching text in
answer_md, flashcards and MCQs), repair flawed MCQs. Keep everything that was not criticised unchanged.
Keep claims in sync with answer_md.
Return the COMPLETE package as ONE JSON object with exactly these keys:
title, system, subtopic, answer_md, key_points, rubric, claims, uncertainties, flashcards, mcqs, and mcq_key (only if the
question has options)."""


def revise_user(item: dict, package: dict, problems: List[str], context: List[dict]) -> str:
    return "\n\n".join([
        _question_block(item),
        "CURRENT PACKAGE:\n" + json.dumps(package, ensure_ascii=False),
        "PROBLEMS TO FIX:\n- " + "\n- ".join(problems),
        _ctx_block(context),
    ])
