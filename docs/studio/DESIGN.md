# Content Studio: question → answer, flashcards, MCQs (semi-automatic)

**Goal:** you upload exam questions. The system drafts a model theory answer, flashcards and MCQs for each one, checks the draft automatically, sends it to a human for sign-off, and publishes what was approved into the portal. All three outputs come from **one verified answer**, so they can't contradict each other.

---

## 1. Deliberation: the choices and why

| Question | Options considered | Decision | Why |
|---|---|---|---|
| **What is the unit of work?** | per file · per question · per topic | **Per question**: one *item* holds its answer, cards, MCQs, rubric, checks and review | Each question is reviewed, versioned and published on its own. A bad MCQ doesn't block a good answer. |
| **Where does the truth come from?** | papers/guidelines only (strict RAG) · model knowledge only · **guided** | **Guided, not grounded.** The model answers from mainstream current knowledge (standard textbooks, major society guidelines). Library excerpts (our papers, guidelines, pearls, theory notes) are passed in as *hints*. | As you asked. Strict RAG would leave gaps wherever the library has none, and would repeat outdated papers. Every claim is tagged `library:<id>` or `general`, so the reviewer knows which claims have no library backing. |
| **How do we "authenticate" content?** | human only · AI only · **layered** | **Four layers:** (1) a second, *different* model reviews every claim; (2) MCQs are **blind-solved** by the reviewer without the key, and a mismatch means a broken question; (3) deterministic lint (MCQ structure, numbers that disagree between answer and cards, dose statements, length vs marks, PHI); (4) **human sign-off** bound to that exact version. | Two models from different families rarely share the same hallucination. Blind-solving catches wrong keys and ambiguous stems cheaply. Lint costs nothing. A human remains the final authority for medical content. |
| **How much is automatic?** | fully auto · fully manual · **traffic light** | Items are triaged **green / amber / red** after an automatic fix-up round. Green items can be **bulk-approved**. Amber shows the reviewer exactly what to check. Red needs an edit or regenerate. **Nothing publishes without a human approval.** | Semi-automatic: the routine 70–80% is a one-click batch, and attention goes to the risky rest. |
| **One LLM call or several?** | 1 big call · **compose → derive → verify → (revise)** | Compose the answer, claims, key points and rubric first. Then derive cards and MCQs **from that answer**. Then verify. Then one revise round if needed. | Deriving from the answer keeps everything consistent and makes the consistency lint meaningful. |
| **Where does it run?** | Vercel · **local, like generator.py** | Local CLI `studio.py` plus a review page in the existing console (`/console/studio`). Items are JSON files in git. | Matches how the repo works today (generate locally → commit → deploy). No new infrastructure. |
| **What if content changes after approval?** | ignore · **version-bound approval** | Every regenerate or edit creates a new version. Approval records the version and its hash. Editing an approved item sends it back for review. Republishing reuses the same card/question IDs. | Provenance stays honest. Bookmarks and SRS state survive republishing. |
| **Can the reviewer approve parts?** | all-or-nothing · **per part** | Approve the answer, each flashcard and each MCQ individually. | Commonly one MCQ is weak while everything else is fine. |

---

## 2. Pipeline

```
 studio_input/{Medicine|Microbiology|CCM}/*.txt|md|docx|pdf|csv     (or paste in /console/studio)
        │
 1 INTAKE   split into questions · detect marks/type/MCQ options · dedup (exact + near) · classify system/subtopic
        │                                                        → studio/items/{subject}/{id}.json  status=queued
 2 CONTEXT  BM25 over papers + guidelines + pearls + theory notes → top-k excerpts as *hints*
        │
 3 COMPOSE  model A: answer_md (structured by marks) + key_points + rubric + claims[basis, confidence, high_stakes]
 4 DERIVE   model A: flashcards + MCQs derived from the answer
        │
 5 VERIFY   model B: claim verdicts · issues · coverage   +   blind MCQ solve   +   lint (no LLM)
        │
 6 REVISE   if red/amber with fixable issues → model A applies the fixes → re-verify (max STUDIO_MAX_REVISIONS)
        │
 7 TRIAGE   green / amber / red                                              status=generated
        │
 8 REVIEW   /console/studio: approve (whole or per part) · edit · regenerate-with-note · reject
        │                                                                     status=approved
 9 PUBLISH  answer → Theory MDs/{System}/{Subtopic}/qna-{id}.md   (+ theory_notes_meta.json)
            cards  → flashcard store (source="studio", stable UUIDs)
            MCQs + the question itself (written, with rubric) → output_files/question_bank/{subject}/studio.json
            provenance on everything: drafted-by, verified-by, reviewed-by, date, version      status=published
        │
 10 DEPLOY  existing: console "Push" or `python syncer.py --mode data`
```

## 3. Triage rules (`acumen_core/studio/checks.py`)

| Red (must fix) | Amber (look first) | Green |
|---|---|---|
| Verifier marks any claim **incorrect** | High-stakes claim (dose, threshold, contraindication) marked **outdated/unverifiable** | None of the red or amber conditions apply |
| Any **major** issue | Verifier overall score < 80, or coverage < 70 | |
| Blind MCQ solve ≠ key | > 2 minor issues | |
| Malformed MCQ (options/key) | Numbers in cards/MCQs that are absent from the answer | |
| PHI (HIGH) in the uploaded question or the answer | Length outside the expected range for the marks | |
| Verifier call failed | Model listed uncertainties | |

## 4. Files

```
studio.py                         CLI: ingest | generate | run | status | approve-green | publish
acumen_core/studio/
  intake.py     parse uploads → questions; dedup; marks/type detection
  retrieve.py   BM25 over the library (hints only)
  prompts.py    compose / derive / verify / blind-solve / revise prompts
  generate.py   the pipeline with an injectable LLM (tests run offline)
  checks.py     lint + triage
  items.py      item store, versions, state machine, history
  publish.py    write to Theory MDs / flashcard store / question bank; unpublish
dashboard/studio_api.py           /console/api/studio/* endpoints
dashboard/static/studio.html      review page at /console/studio
studio_input/  studio/items/      inputs and item records (git-tracked)
```

## 5. Config (`.env`)

```
STUDIO_DRAFT_MODEL      default OPENROUTER_MODEL
STUDIO_VERIFY_MODEL     default openai/gpt-oss-120b  (use a different family from the draft model)
STUDIO_API_KEY / STUDIO_BASE_URL     default OpenRouter
STUDIO_AUDIENCE         who answers are written for (default: PG residents, MD/DNB/IDCCM level)
STUDIO_MAX_REVISIONS    default 1
STUDIO_REVIEWER         default reviewer name shown in provenance
```

## 6. Not in this version (next steps)

- **Citation check against PubMed** for named trials and guidelines (NCBI E-utilities). The hook point is `checks.py`.
- **Multi-reviewer roles** (faculty accounts, 2-person sign-off for red items). The console is local-only today.
- **Images in questions** (CXR/ECG stems): needs the vision model and an image store.
- **Feedback loop:** learner "report error" on published items → reopens the item as `revision_requested`.
