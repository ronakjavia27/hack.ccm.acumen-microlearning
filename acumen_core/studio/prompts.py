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
  "issues": [{{"where": "answer | theory | rubric | qna:<i> | flashcard:<i> | mcq:<i>", "severity": "major | minor",
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


# =====================================================================
# NOTES MODE — the author's note becomes the theory section
# =====================================================================

POLISH_SYSTEM = f"""You are a copy-editor for clinical teaching notes written for {config.STUDIO_AUDIENCE}.
The author wrote this note. It will be published as the THEORY section nearly verbatim.

POLISH RULES — strict
- Keep the author's wording, content, order and emphasis. Do NOT add new facts, remove facts, or "correct" content.
- Only fix: markdown structure (headings, bullet levels, tables), obvious typos, inconsistent abbreviations,
  broken formatting from copy/paste. Make it scan well on a phone.
- If something looks factually wrong, outdated or unsafe, LEAVE IT in theory_md and report it in `uncertainties`
  (quote the text, say why, give the current standard). The author decides.
- List every non-formatting change you made in `edits` ("typo: 'pulmonory' → 'pulmonary'").

Return ONE JSON object:
{{
  "title": "note title (≤ 10 words)",
  "system": "organ system / specialty, e.g. Pulmonology, Infectious Diseases, Sepsis",
  "subtopic": "specific subtopic",
  "theory_md": "the polished note in markdown, starting with '# <title>'",
  "edits": ["each change that is more than formatting"],
  "key_points": ["6–12 one-line must-know points, taken from the note"],
  "claims": [{{"text": "atomic checkable statement from the note", "basis": "note", "confidence": "high | medium | low",
              "high_stakes": true}}],
  "uncertainties": ["possible errors, outdated statements or gaps — quote the text"]
}}
claims: 8–25 statements carrying the note's facts (numbers, thresholds, doses, drug choices, criteria,
recommendations). high_stakes = doses, thresholds for intervention, contraindications."""


def polish_user(item: dict) -> str:
    return "\n\n".join([f"SUBJECT: {SUBJECT_LABEL.get(item['subject'], item['subject'])}",
                        f"AUTHOR'S NOTE:\n{item.get('note_md', '')}"])


DERIVE_NOTE_SYSTEM = f"""You turn a clinical teaching note into exam practice material for {config.STUDIO_AUDIENCE}.

{TRUTH_POLICY}
The NOTE is the primary source: base everything on it. Where an exam-quality answer needs a point the note does not
cover, you may add it from mainstream knowledge — keep such additions brief and accurate.

Return ONE JSON object:
{{
  "qna": [{{"question": "exam-style question", "qtype": "long | short | very_short | viva", "marks": 10,
           "answer_md": "model answer in markdown", "rubric": [{{"point": "...", "keywords": ["..."], "marks": 2}}]}}],
  "flashcards": [{{"front": "a question", "back": "1–4 lines"}}],
  "mcqs": [{{"stem": "...", "options": ["A", "B", "C", "D"], "answer": [index], "explanation": "...", "difficulty": 1}}]
}}
qna: 3–6 questions an examiner would actually set on this topic (mix long, short and viva). Answer length by type:
long ~80–110 words per mark, short ~300–500 words, very_short ~80–180, viva ~120–250. Rubric marks sum to `marks`.
flashcards: 6–12, atomic, high-yield (criteria, thresholds, first-line choices, mechanisms, classic associations).
mcqs: 3–6 single-best-answer, exactly 4 options, one unambiguous key, plausible homogeneous distractors,
no "all/none of the above", vignette stems preferred; explanation says why right and why each distractor is wrong."""


def derive_note_user(item: dict, polished: dict) -> str:
    return "\n\n".join([f"SUBJECT: {SUBJECT_LABEL.get(item['subject'], item['subject'])}",
                        f"NOTE:\n{polished.get('theory_md') or item.get('note_md', '')}",
                        "KEY POINTS:\n- " + "\n- ".join(polished.get("key_points") or [])])


def verify_note_user(item: dict, package: dict, context: List[dict]) -> str:
    claims = "\n".join(f"  {i}. {c.get('text')}  [high_stakes={c.get('high_stakes')}]"
                       for i, c in enumerate(package.get("claims") or []))
    qna = "\n".join(f"  {i}. ({q.get('qtype')}, {q.get('marks')}m) {q.get('question')}\n     ANSWER: {q.get('answer_md')}"
                    for i, q in enumerate(package.get("qna") or []))
    cards = "\n".join(f"  {i}. Q: {c.get('front')}\n     A: {c.get('back')}" for i, c in enumerate(package.get("flashcards") or []))
    mcqs = "\n".join(f"  {i}. {m.get('stem')}\n     options={m.get('options')} key={m.get('answer')}\n     expl: {m.get('explanation')}"
                     for i, m in enumerate(package.get("mcqs") or []))
    return "\n\n".join([
        f"SUBJECT: {SUBJECT_LABEL.get(item['subject'], item['subject'])}",
        "This is a TEACHING NOTE written by the author (lightly copy-edited), plus exam material derived from it.\n"
        "Use where=\"theory\" for problems in the note itself, \"qna:<i>\" for exam questions/answers.",
        f"THEORY NOTE:\n{package.get('theory_md', '')}",
        f"CLAIMS FROM THE NOTE:\n{claims or '  (none)'}",
        f"EXAM QUESTIONS:\n{qna or '  (none)'}",
        f"FLASHCARDS:\n{cards or '  (none)'}",
        f"MCQS:\n{mcqs or '  (none)'}",
        _ctx_block(context),
    ])


REVISE_NOTE_SYSTEM = f"""You are revising exam material derived from an author's teaching note after an independent review.

{TRUTH_POLICY}

Fix EVERY listed problem in the exam questions (qna), flashcards and MCQs. Keep everything not criticised unchanged.
The theory note itself is the author's and is NOT yours to change.
Return ONE JSON object with exactly these keys: qna, flashcards, mcqs (same schemas as given)."""

REVISE_NOTE_EDITOR_SYSTEM = f"""You are applying the AUTHOR'S OWN change request to their teaching note and its exam material.

{TRUTH_POLICY}

Apply the request exactly. You may change theory_md only as far as the request asks; keep the rest of the author's
wording. Update claims, key_points, qna, flashcards and mcqs so they stay consistent with the note.
Return the COMPLETE package as ONE JSON object with keys: title, system, subtopic, theory_md, edits, key_points,
claims, uncertainties, qna, flashcards, mcqs."""


def revise_note_user(item: dict, package: dict, problems: List[str], context: List[dict], editor: bool) -> str:
    pkg = package if editor else {k: package.get(k) for k in ("qna", "flashcards", "mcqs")}
    parts = [f"SUBJECT: {SUBJECT_LABEL.get(item['subject'], item['subject'])}"]
    if not editor:
        parts.append(f"THEORY NOTE (read-only context):\n{package.get('theory_md', '')}")
    parts += ["CURRENT " + ("PACKAGE" if editor else "EXAM MATERIAL") + ":\n" + json.dumps(pkg, ensure_ascii=False),
              ("AUTHOR'S REQUEST:\n- " if editor else "PROBLEMS TO FIX:\n- ") + "\n- ".join(problems),
              _ctx_block(context)]
    return "\n\n".join(parts)
