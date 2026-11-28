# ARCHITECTURE.md — Technical map of hack.CCM

Keep in sync with code (see `CLAUDE.md` §0). For CLI flags and env vars see `AGENTS.md`. For call-graph exploration use `graphify-out/GRAPH_REPORT.md` and `graphify query/explain/path`.

## 1. High-level
```
Offline pipelines (run on a dev machine, paid LLM calls)        Online app (Vercel, read-only FS)
 generator.py   PDFs → summaries → subtopics → pearls            webapp_redefined.py   (entrypoint, 23 lines)
 flashcards.py  md/pdf/... → flashcard store                        └ imports webapp_google  (Google OAuth + landing)
 mcq_generator  theory+guidelines → MCQ store                       └ imports redefined_ui   (new SPA at /, old at /classic)
 linker.py      cross-link edges                                          └ imports revamped_webapp (shared FastAPI app: auth,
 maintainer.py  health/repair   syncer.py git/email                          bookmarks, summaries, search, trials, admin, classic UI)
        │ write JSON files committed to git                          reads JSON from repo; writes user state to KV only
        └──────────────────────────────►  output_files/, *.json  ────────────────────────►
 dashboard_app.py → dashboard/ (admin console :8878/console) edits the same JSON files
```
Import order is load-bearing: `webapp_google` first, then `redefined_ui` (copies routes at import time).

## 2. File structure
| Path | Role |
|---|---|
| `webapp_redefined.py` | Vercel entrypoint; `app = redefined_ui.app` |
| `webapp_google.py` (460 L) | Google OAuth routes `/api/auth/google*`, landing HTML |
| `redefined_ui.py` (1.5k L) | Theory-first SPA (inline HTML/CSS/JS) + `/api/redefined/*` |
| `revamped_webapp.py` (6.5k L) | Base FastAPI app, classic UI, auth, admin users, bookmarks, search, pearls, trials, print export, loaders (`load_theory_notes`, `load_flashcard_decks`) |
| `acumen_core/` | `config` (paths/models), `schema`, `llm`, `ocr`, `markdown`, `tracking`, `errors`, `vocabulary`, `flashcards`, `linking`/`linker`, `subtopics_config`+`subtopics.json`, `kv` |
| `dashboard/` | Admin console: `app.py` router, `storage.py` (atomic write, PushWorker, locks, audit), `cascade.py`, `backup.py`, `modules/{summaries,pearls,flashcards,theory}.py`, `static/dashboard.html` |
| `scripts/` | `sync_graph.sh` (graphify sync), `test_auth.py`, `clear_auth_kv.py` (destructive) |
| `design-system/hack-ccm/MASTER.md` | Design tokens/rules |
| `graphify-out/` | Auto-generated code graph (`graph.json`, `GRAPH_REPORT.md`, `graph.html`) |
| `.claude/settings.json` | Plugins + SessionStart hook → `scripts/sync_graph.sh` |
| `vercel.json` | Routes everything to `webapp_redefined.py` (`@vercel/python`) |
| `package.json` | Node deps (tailwind, puppeteer, vercel analytics) — not used by the Python runtime |

## 3. Data stores (no SQL database)
**Files (committed JSON — source of content):**
| File / dir | Shape / purpose |
|---|---|
| `sent_summaries.json` | List of article/guideline summaries (`file_name, title, authors, journal, doi, system, type, subtopic, show_on_web, recommendation_blocks, key_pearls…`) ~2.3k |
| `output_files/{Specialty}/{Type}/{stem}.json` | Full structured summary per paper |
| `pearls.json` | Atomic pearls (`id, source_paper, doi, system, type, pearl, topic, file_name`) |
| `output_files/flashcards/{System}/{Subtopic}.json` + `flashcards_index.json` | UUID cards `front/back/tags/source/status`; deck id `System/Subtopic` |
| `output_files/mcqs/{System}/{Subtopic}.json` | MCQs (options, answer, explanation, source, status draft/approved/rejected) |
| `output_files/Theory MDs/` | Markdown theory notes (title = first `# `) |
| `output_files/esbicm_trials/`, `trials_database_condensed/` | Trial data |
| `output_files/related_links.json` | Cross-link edges (reason-labelled) |
| `subtopic_mapping.json`, `acumen_core/subtopics.json` | Subtopic registry / master vocabulary |
| Ledgers: `flashcards_ledger.json`, `mcq_ledger.json`, `links_ledger.json`, `pearls_processed.json` | sha256 skip logic |

**KV (`acumen_core/kv.py`; Upstash on Vercel via `KV_REST_API_URL/TOKEN`, else `local_kv.json`):**
| Key | Content |
|---|---|
| `auth:users:{email}` | user record (role, access flags, profile) |
| `auth:session:{sid}` | `{email, created_at}`, TTL `SESSION_MAX_AGE` |
| `auth:oauth:state:{state}` | OAuth state, TTL 600s |
| `auth:access_defaults` | default per-user access flags |
| `user:{email}:{key}` | per-user data: bookmarks/folders, study progress (cards SM-2, mcq, notes, activity) |

## 4. HTTP API
**Base app (`revamped_webapp.py`, also exposed by redefined app):** `GET /` (classic UI), `GET /api/debug`, `POST /api/signup|login|logout`, `GET /api/me`, admin: `GET /api/admin/users`, `GET|PUT /api/admin/users/defaults`, `PUT|DELETE /api/admin/users/{email}`; `GET|POST|DELETE /api/bookmarks`, `POST|DELETE /api/bookmarks/folders`; `GET /api/summary`, `GET /export/print`, `GET /api/search`, `GET /api/pearls`, `GET /api/trials`, `/api/trials/stats`, `/api/trial/{slug}`, `/api/condensed-trials`, `/api/condensed-trial/{system}/{name}`, `GET /favicon.ico`.
**Google (`webapp_google.py`):** `/api/auth/google*` (start + callback).
**Redefined (`redefined_ui.py`):** `GET /` (SPA), `GET /classic`, `GET /api/redefined/{bootstrap,note,related,guideline,pearls,mcqs,progress}`, `PATCH /api/redefined/progress`.
**Console (`dashboard_app.py` → `dashboard/app.py`, port 8878):** `/console`, `/console/api/*` (CRUD summaries/pearls/flashcards/theory, cascade, backup, push, audit).

## 5. Key flows
- **Sign-in:** Google OAuth (`webapp_google`) or email/password → session id cookie → KV `auth:session:*`; gating helpers in `revamped_webapp` check `auth:users:{email}` flags (`theory` etc.).
- **Content ingest:** PDF → `generator.py` Pass 1/1.5/2 → JSON + `sent_summaries.json` + `pearls.json` → linker pass → commit/push (`syncer.py`) → Vercel redeploy.
- **Study UI:** SPA calls `/api/redefined/bootstrap` for the catalog, lazy-loads notes/guidelines/pearls/MCQs, saves SM-2/MCQ progress via `PATCH /api/redefined/progress` (KV).
- **Admin edits:** console edits JSON atomically → optional PushWorker git push → cascade updates pearls when summary system/subtopic changes.

## 6. Dependencies
Python (`requirements.txt`): fastapi, uvicorn, requests, openai, google-genai, together, pypdf, PyMuPDF, pdf2image, pytesseract, openpyxl, python-dotenv, beautifulsoup4. Dev tool: `graphifyy` (auto-installed by `scripts/sync_graph.sh`). External: OpenRouter, Gemini, Upstash Redis, Google OAuth, Vercel, Gmail SMTP (`syncer.py`), Google Sheets (subscribers).
Env: see `.env.example` and `AGENTS.md` (API keys, `KV_*`, `MCQ_DIR`, `THEORY_PROCESSED_DIR`, `FLASHCARD_LLM_*`, `QUESTION_LLM_*`, Google OAuth client id/secret).

## 7. Graphify auto-sync
`SessionStart` hook → `scripts/sync_graph.sh` → (install `graphifyy`, `graphify hook install`, `graphify update .`). Git hooks refresh on commit/checkout/merge/rewrite; `.gitattributes` registers the `graphify` union-merge driver for `graph.json`. Machine-local files (`manifest.json`, `.graphify_root`, build-state, dated backups, `cache/`) are git-ignored via `graphify-out/.gitignore`.
