# hack.CCM v2 — Revamp Plan

Status: **Phase 0 (skeleton) done.** Content and most integrations are still to come.
Subjects for now: **Medicine · Microbiology · Critical Care Medicine**.
Business model: freemium. The core learning loop is free; heavier AI, live and media features need a paid plan.

---

## 1. Principles

1. **Use the content we already have.** Papers, guidelines, pearls, flashcards and theory notes already exist. SRS and exams should run on them from day one.
2. **One habit loop:** *Learn (theory/video) → Test (exam) → Retain (SRS) → Ask (doubts) → Nudge (push).* Each feature feeds the next one: missed exam questions go into SRS automatically, and SRS due counts go into the daily push.
3. **Keep the free tier useful.** Reading, SRS and a few personalised exams per week stay free. Pay for AI grading, live/proctored exams, the pro video library, WhatsApp and voice.
4. **Privacy by default.** The doubts forum takes de-identified text only. Proctoring sends events, not video. WhatsApp is strictly opt-in.
5. **Build cheap, swap later.** Each external dependency (DB, payments, STT/TTS, video CDN, WhatsApp) sits behind one small adapter.

---

## 2. What exists after Phase 0

New package `acumen_platform/`, mounted onto the existing portal by `revamped_webapp.py`:

| Path | Purpose |
|---|---|
| `config.py` | Subjects, tiers and quotas (**the paywall lives here**), env keys |
| `store.py` | Persistence adapter (Upstash KV now, Postgres later). Only this file changes in the migration |
| `entitlements.py` | Tier lookup, capability checks (`require`), periodic quotas (`consume`). Returns HTTP 402 on paywall hits |
| `srs.py` | SM-2 scheduler (Again/Hard/Good/Easy) and per-user deck. Interface is ready for FSRS |
| `exams.py` | Personalised builder (60% weak / 30% unseen / 10% retention), sessions, MCQ and written grading, mastery EMA, auto-enrol misses into SRS |
| `live.py` | Scheduled cohort exams with a server-enforced deadline, join window, anonymised leaderboard |
| `proctoring.py` | Event ingest, integrity score, flag for human review |
| `content.py` | Loaders for question bank, theory modules, video catalog, and the existing flashcard store |
| `deid.py` | PHI detector/redactor (Aadhaar, PAN, +91 phones, UHID/IPD/MRN, names after honorifics, full dates, emails, PIN, >89 yrs) |
| `doubts.py` | Forum: de-id gate + attestation, moderation queue, votes, reports (auto-hide at 3), accepted answer, pseudonymous handles |
| `notify/` | Preferences, digest builder, hourly cron runner; Email (SMTP) and WhatsApp Cloud API template channels (dry-run by default) |
| `voice.py` | STT/TTS provider protocols and capability report; viva needs the realtime service |
| `billing.py` | Plans list, checkout stub, **HMAC-verified** Razorpay webhook → `set_subscription` |
| `router.py` | `/api/v2/*` (44 endpoints) and the `/learn` page |
| `static/learn.html` | Clickable preview UI covering all 8 areas |
| `sample_data/` | Demo questions, modules and videos (`status: "sample"`). Loaded only when `PLATFORM_SAMPLE_DATA=1` |
| `tests/test_platform_v2.py` | 22 tests: SRS, de-id, quotas, builder, grading, proctoring, API flows |

**Activation:** on locally by default; **off on Vercel** unless `PLATFORM_V2=1` is set. The live portal is unaffected.

```bash
uvicorn revamped_webapp:app --port 8000      # then open http://localhost:8000/learn
python -m pytest tests/test_platform_v2.py -q
```

---

## 3. Feature map

Legend: ✅ working in skeleton · 🟡 interface/stub · ⬜ not started

### 3.1 Spaced repetition ✅
- **Items:** existing flashcards (`flashcard:<uuid>`), missed questions (`q:<id>`, auto-enrolled), pearls (`pearl:<id>`, resolver TODO).
- **Scheduler:** SM-2 now. Move to **FSRS** once there are enough review logs (logs are already kept in `v2:srs_log:*`).
- **Free:** unlimited. **Pro:** nothing extra planned yet. Possible later: "cram mode" and cross-device stats.
- **Next:** "Add to SRS" buttons on portal decks/pearls; daily new-card cap setting; heatmap; FSRS parameter fit per user.

### 3.2 Personalised exams ✅
- **Inputs:** mastery per `subject|system|subtopic` (EMA of correctness), seen history, difficulty fit.
- **Modes:** practice (instant feedback), personalised, timed mock.
- **Free:** 2 personalised per week, ≤20 questions. **Pro:** unlimited, ≤200 questions.
- **Biggest gap: there is no question bank yet.** Plan: (a) LLM-draft MCQs from existing summaries/pearls with a new `questions.py` pipeline that mirrors `flashcards.py` (ledger, sha256 skip); (b) faculty review in the console (`draft → published`); (c) store each question with `refs` back to its source paper/pearl so every explanation cites evidence.

### 3.3 Practical-oriented theory 🟡
- **Module format** (`output_files/theory_modules/{Subject}/*.json`): case vignette → **decision points** (options with feedback) → concept → **bedside how-to** (links to videos) → pitfalls → checklist → linked questions/decks/papers.
- Existing `Theory MDs` stay as reference notes. Modules are the "practical" layer on top.
- **Free:** core modules. **Pro:** advanced modules (`tier: "pro"`).
- **Next:** console editor for modules; LLM scaffold from existing notes + guidelines; a "calc" section type (P/F ratio, anion gap, CrCl, fluid deficit).

### 3.4 Clinical doubt-solving (de-identified) ✅ core / 🟡 AI
- Gate: live de-id check while typing → hard block on HIGH findings → required attestation → moderation queue.
- **Free:** read everything, 3 posts/month. **Pro:** 30 posts/month and an AI first response.
- The AI response should be RAG over our own papers/guidelines/pearls via `acumen_core.llm`. It is labelled as AI and can never be the accepted answer.
- **Images are disabled** until server-side DICOM tag stripping, EXIF strip and burnt-in-text OCR exist.
- **Next:** reputation (trusted users skip the queue), faculty "verified answer" badge, moderation UI in the console, report reasons.

### 3.5 Videos (Echo · USG/POCUS · CXR) 🟡
- Catalog only (`output_files/videos/catalog.json`). Files live on a video CDN, not in git or on Vercel.
- **Host:** YouTube unlisted for free/sample videos; **Bunny Stream** or **Cloudflare Stream** for pro videos (signed, expiring URLs; HLS).
- Each video has chapters and linked questions ("watch → answer 3 MCQs").
- **Free:** sample set. **Pro:** full library.
- **Check licensing** for any third-party echo/USG clips before upload.

### 3.6 Live MCQ / written exams with AI proctoring 🟡
- **Live:** scheduled window, join window, deadline enforced server-side (30 s grace), anonymised leaderboard. ✅
- **Proctoring:** browser signals already in `learn.html` (tab hidden, blur, paste, fullscreen exit). Still to add: in-browser **face detection** (e.g. MediaPipe Face Landmarker, WASM) for face missing / multiple faces / gaze. Only events go to the server. ✅ scoring, 🟡 face detection.
- **No video upload by default.** Optional snapshot evidence would be institution-only, opt-in, with short retention.
- A flag means **human review**, never an automatic fail.
- **Written answers:** keyword-rubric preview now; LLM rubric grading (`exams.ai_grade_written`) for Pro, to be validated against faculty marks before release.
- **Realtime pieces** (synced countdown, live leaderboard push, invigilator chat) need websockets → **separate realtime service** (§5).

### 3.7 Email / WhatsApp push 🟡
- Digest: SRS due count, pearl of the day, upcoming live exams, replies to your doubts.
- **Free:** weekly email. **Pro:** daily email + WhatsApp.
- **WhatsApp:** Meta Cloud API, **template messages only** for business-initiated sends, explicit opt-in with a timestamp, STOP handling. The digest template needs Meta approval first.
- **Scheduler:** hourly `POST /api/v2/cron/digest` with `Authorization: Bearer $CRON_SECRET`, from a Vercel Cron or a GitHub Action. Dry-run by default.
- **Fold `syncer.py` email into this module** and move its hard-coded SMTP credentials into env vars (security fix, Phase 1).

### 3.8 Voice: STT / speech-to-speech 🟡
- **Level 1, dictation:** browser Web Speech API (free) → server STT with a medical-term prompt (Pro).
- **Level 2, TTS:** stems read aloud ("audio mode").
- **Level 3, live AI viva:** speech-to-speech examiner using the question `rubric`, follow-up questions and grading. Needs WebRTC/websocket → realtime service. Metered as `voice_minutes_per_month`.

---

## 4. Tiers (edit `acumen_platform/config.py`)

| Capability | Free | Pro | Institution |
|---|---|---|---|
| Papers, guidelines, pearls, flashcards, theory notes | ✓ | ✓ | ✓ |
| SRS reviews | ∞ | ∞ | ∞ |
| Personalised exams / week | 2 | ∞ | ∞ |
| Max questions per exam | 20 | 200 | 300 |
| AI written grading / month | — | 100 | 500 |
| Doubt posts / month | 3 | 30 | ∞ |
| AI first response on doubts | — | ✓ | ✓ |
| Pro theory modules / video library | — | ✓ | ✓ |
| Live exams | free events | all | all + cohort admin |
| Proctored exams | — | ✓ | ✓ + reports |
| Voice minutes / month | 0 | 60 | 300 |
| Push | weekly email | daily email + WhatsApp | same |
| Price | 0 | **TBD** | **TBD** |

Admins resolve to Institution. Manual grants (faculty, beta testers): `PUT /api/v2/admin/subscription/{email}`.

---

## 5. Architecture and repos

```
                    ┌──────────────── Vercel (this repo) ────────────────┐
 Browser / PWA ───► │ webapp_google.py → revamped_webapp.app             │
                    │   ├─ existing portal routes (/ , /api/*)           │
                    │   └─ acumen_platform  (/api/v2/*, /learn)          │
                    └──────┬──────────────┬──────────────┬───────────────┘
                           │              │              │
                     Postgres (Phase 1)  Upstash KV    Video CDN (Bunny/CF Stream)
                           │          (sessions, cache)
          ┌────────────────┴───────────┐
          │ hackccm-realtime (new repo)│  websockets/WebRTC: live exam sync,
          │ Fly.io / Railway / Render  │  leaderboard push, AI viva (STT↔LLM↔TTS)
          └────────────────────────────┘
 Local/CI: generator.py · flashcards.py · questions.py (new) · linker.py → commit content → deploy
 External: Razorpay (+Stripe) · Meta WhatsApp Cloud API · SMTP/transactional email · STT/TTS/LLM providers
```

**Repos.** Stay a monorepo for as long as possible. Add only what has to run elsewhere:

| Repo | When | Why |
|---|---|---|
| `hack.ccm.acumen-microlearning` (this) | now | Content pipeline, portal, v2 API, console |
| `hackccm-realtime` | Phase 4 | Vercel functions can't hold websockets/WebRTC |
| `hackccm-content` (private) | when outside authors join | Question bank/modules with separate permissions and review flow; this repo pulls it as a submodule or at build time |
| Frontend app (Next.js or similar) | when the v2 UI outgrows one HTML file | The portal is currently a 6.5K-line inline f-string; v2 UI is kept in `static/learn.html` so it can move out cleanly |
| Mobile | after PWA | Ship a PWA first (install prompt, offline SRS); native only if push/offline needs it |

**Storage migration (Phase 1).** KV is fine for the skeleton but has no queries, transactions or atomic counters. The live-exam participant list and quota counters are read-modify-write, which is noted in the code. Move v2 data to **Postgres (Neon or Supabase)** with these tables:
`subscriptions, usage_counters, srs_cards, srs_reviews, questions (optional mirror), exam_sessions, exam_answers, mastery, live_exams, live_participants, proctor_events, doubts, doubt_replies, doubt_votes, doubt_reports, notify_prefs, notify_log, billing_events`.
Only `store.py` (or a SQL repository beside it) changes. User accounts/sessions can stay in KV at first.

---

## 6. Compliance and safety

- **India DPDP Act 2023:** consent notices for data collection (phone for WhatsApp, webcam for proctoring), purpose limitation, deletion on request, grievance contact. Add a privacy policy page before launching paid features.
- **De-identification:** regex gate + attestation + moderation. Also add an "identifiers?" report reason and a fast takedown path. Audit the regex against real (synthetic) case text before launch.
- **Medical disclaimer:** extend the existing disclaimer to cover forum and AI answers ("educational, not for patient-specific decisions").
- **Proctoring:** explicit consent screen, events-only, retention policy, appeal path.
- **Security debt to fix in Phase 1:**
  - Passwords are single-round salted SHA-256 (`revamped_webapp._hash_password`). Move to argon2/bcrypt and re-hash on login.
  - **A Gmail app password is committed in plain text in `syncer.py` (and in git history). Revoke it in Google Account → App passwords now**, issue a new one, and read it from env (`SMTP_USER`/`SMTP_PASSWORD`, already used by `acumen_platform/notify`).
- **Payments:** never grant a tier from the client. Only verified webhooks (already enforced) or admin grants.

---

## 7. Roadmap

| Phase | Scope | Exit criteria |
|---|---|---|
| **0 — Skeleton** ✅ | Package, API, preview UI, tests, flag-gated mount | This commit |
| **1 — Foundation** | Postgres for v2; password-hash upgrade; SMTP env; `questions.py` MCQ generator from summaries/pearls; console tab for question review; "Add to SRS" in portal; Razorpay checkout; privacy policy | 500+ reviewed MCQs across 3 subjects; SRS + personalised exams in public beta (free) |
| **2 — Learn** | Practical theory modules (editor + 10 flagship modules per subject); video catalog + CDN + signed URLs; weekly email digest live; WhatsApp template approved + daily digest for Pro | First paid users |
| **3 — Community** | Doubts forum public: moderation UI, reputation, faculty badges, AI first response (RAG) | Moderation turnaround < 24 h |
| **4 — Live** | `hackccm-realtime`; live cohort exams; face-detection proctoring; AI written grading validated vs faculty | One proctored mock with ≥100 concurrent users |
| **5 — Voice** | Server STT dictation → TTS audio mode → live AI viva | Viva graded within ±1 mark of faculty on a test set |

Rationale for this order: Phases 1–2 reuse content we already have and build the daily habit. Phases 3–5 need moderation capacity, legal review and new infrastructure.

---

## 8. Open decisions (owner: you)

1. **Pricing** for Pro and Institution, monthly vs annual, student discount.
2. **Database:** Neon (plain Postgres) vs Supabase (Postgres + auth + storage + realtime; could cut the realtime repo for simple cases).
3. **Video host:** Bunny Stream vs Cloudflare Stream, and who records the echo/USG/CXR content.
4. **Question authorship:** LLM-drafted + faculty-reviewed vs faculty-only; who the reviewers are.
5. **Frontend:** keep vanilla HTML for v2 or start a separate frontend app now.
6. **Microbiology taxonomy:** currently borrows Infectious Diseases/Sepsis/Immunology plus axes (Bacteriology, Virology, …). Should it get its own `subtopics.json` vocabulary?
7. **Institution tier:** sold per seat or per cohort; does it need SSO?

---

## 9. Adding content (no code changes needed)

| What | Where | Format |
|---|---|---|
| Questions | `output_files/question_bank/{Subject}/*.json` | JSON list. Schema in `acumen_platform/content.py` docstring |
| Theory modules | `output_files/theory_modules/{Subject}/*.json` | One module per file. See `sample_data/theory_modules.json` |
| Videos | `output_files/videos/catalog.json` | JSON list. See `sample_data/videos.json` |
| Tiers/quotas/subjects | `acumen_platform/config.py` | Python dicts |

After deploying content: `POST /api/v2/admin/content/reload` (or restart).
