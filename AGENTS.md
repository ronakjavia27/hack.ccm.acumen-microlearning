# hack.CCM — AI Microlearning Platform (Complete Reference)

## Overview
AI-powered clinical microlearning platform. Ingests medical PDFs, extracts structured summaries and clinical pearls via LLMs, and serves them through a FastAPI web dashboard.

## Project Structure

### Root Entry Points
| File | Purpose |
|------|---------|
| `revamped_webapp.py` | THE public knowledge portal (serves `/`, auth-gated) — single FastAPI app, JS/CSS inline in one giant HTML f-string |
| `webapp_google.py` | Vercel entrypoint (see `vercel.json`) — wraps `revamped_webapp` and adds the Google OAuth landing page |
| `dashboard_app.py` | Admin console at `/console` (port 8878) — wraps `dashboard/` |
| `generator.py` | PDF ingestion pipeline (Pass 1: summaries, Pass 2: pearls) |
| `maintainer.py` | Health checks, schema validation, repairs, error reports |
| `syncer.py` | Git sync, email dispatch, subscriber sync |
| `flashcards.py` | Single script for ALL flashcard work: generate (md decks + raw files), watch, theory notes, tag, fronts, status |
| `esbicm_parser.py` | Parses ESBICM trial PDF (~400 trials) into structured JSON |
| `condense_trials.py` | Condenses scraped trial JSON into hack.CCM schema |
| `backfill_markdown.py` | Backfill markdown for existing summaries |
| `build_trials_organsystem.py` | Build trials by organ system index |
| `generate_preview.py` | Preview generation helper |
| `scrape_foundational_trials.py` | Web-scrapes trial data |
| `backfill_markdown.py` | Backfill markdown rendering for old summaries |

### Core Library: `acumen_core/`
| File | Purpose |
|------|---------|
| `config.py` | Central config: paths, API keys, model names, extraction params, `SYSTEM_TO_SPECIALTY` mapping, `CONDENSATION_MODELS` |
| `schema.py` | `EXTRACTION_SYSTEM_PROMPT`, ARTICLE/GUIDELINE JSON schemas, field validation sets (`ARTICLE_REQUIRED_FIELDS`, `VALID_SPECIALTY_VALUES`, etc.) |
| `llm.py` | LLM client abstraction — OpenRouter + Gemini. Functions: `call_chat_api`, `call_gemini_api`, `call_openrouter_api`, `execute_with_fallback`, `execute_with_gemini`, `execute_pearl_extraction`, `classify_subtopic`, `chunk_text`, `merge_chunks_programmatically` |
| `ocr.py` | OCR for scanned PDFs via PyMuPDF + pytesseract + Gemini Vision |
| `markdown.py` | `apply_markdown_emphasis` — bolds clinical numbers/units/keywords |
| `tracking.py` | Atomic JSON save/load, Excel tracker, sent_summaries CRUD, pearl tracker, subtopic mapping registry |
| `errors.py` | Monthly error log `master_error_list_YYYY-MM.txt` (JSONL), error classification, priority levels (CRITICAL→LOW) |
| `vocabulary.py` | Normalizes specialties & article types to controlled vocabulary (reads `specialties.txt`, `article_types.txt`) |
| `flashcards.py` | Shared flashcard pipeline helpers — source parsing (md/txt/pdf/docx/html), authored-md deck import (`parse_markdown_deck`, `cards_from_markdown_deck` with position-matched UUID reuse), LLM convert + tag prompts, subtopic normalization (`normalize_subtopic` with acronym matching), `flashcards_ledger.json` sha256 skip logic, unified store CRUD (`upsert_card`, `remove_card`, `move_card`, `rebuild_flashcards_index`) |
| `subtopics_config.py` | Loads `subtopics.json`, provides `get_subtopics_for_system()`, `is_valid_subtopic()`, `format_subtopics_for_prompt()` |
| `subtopics.json` | Full subtopic vocabulary per specialty — the SINGLE master vocab (also supplies the specialty list via its keys) |

### Dashboard: `dashboard/`
| File | Purpose |
|------|---------|
| `app.py` | FastAPI router for `/console/api/*` — CRUD for summaries/pearls/flashcards/theory, cascade, backup, push, audit |
| `storage.py` | Atomic JSON writer, git push worker (`PushWorker`), edit locks (`EditLockManager`), audit log |
| `cascade.py` | `cascade_preview()` + `cascade_apply()` — when summary system/subtopic changes, update all matching pearls |
| `backup.py` | `create_backup()` (tree.tar.gz + git bundle + manifest), `restore_backup()`, `list_backups()`, `verify_backup()` |
| `static/dashboard.html` | Single-page admin UI (Vue-like vanilla JS) |
| `modules/__init__.py` | Bootstrap — scans `*.json` files and registers CRUD specs per kind |
| `modules/summaries.py` | Summary CRUD |
| `modules/pearls.py` | Pearl CRUD |
| `modules/flashcards.py` | Flashcard CRUD + card regeneration. Reads the unified store `output_files/flashcards/{System}/{Subtopic}.json` (deck id `System/Subtopic`). Specialty change = reclassify: moves every card's (system, subtopic) file. Card LLM-edit writes back to the authored md in `flashcards_input/` when the card is md-sourced. Delete removes the subtopic file (authored md kept). |
| `modules/theory.py` | Theory note CRUD |

### Data Directories
```
input_pdfs/
├── articles/        → Place medical PDF articles here
├── guidelines/      → Place clinical guidelines here
└── other/           → Other PDFs

flashcards_input/
  {Specialty}/topic.md         — Hand-written flashcard deck (authored; imported as-is)
  {Specialty}/topic.pdf|txt|docx|html   — Raw study material (LLM-converted straight to store)

output_files/
  {Specialty}/{Type}/{filename}.json        — Structured summaries
  esbicm_trials/                            — ESBICM trial data
  trials_database_condensed/                — Condensed trial JSON
  flashcards/{System}/{Subtopic}.json       — Unified flashcard store (system/subtopic files, UUID cards, explicit front/back)
  flashcards_index.json                     — Derived flashcard index (v2) powering portal/global-search/console
  Theory MDs/                               — Theory Topics notes (any extension; markdown, first `# ` line = title)

backups/                                    — Full repo snapshots
quarantine/{date}/{category|errors}/        — Processed/failed PDFs
```

### Tracker / Ledger Files
| File | Purpose |
|------|---------|
| `sent_summaries.json` | Approved summaries ledger — canonical list of processed papers |
| `sent_summaries_removed.json` | Deleted entries log |
| `sent_summaries.xlsx` | Excel version of sent_summaries (dual-tracked) |
| `pearls.json` | All extracted clinical pearls (~2000+) |
| `pearls_processed.xlsx` | Pearl extraction tracker (which files have pearls) |
| `subtopic_mapping.json` | Registry of completed subtopic assignments (auto-filled by generator Pass 1.5) |
| `pearl_updater_progress.json` | Batch pearl operation progress |
| `health_report.json` | Auto-generated health report |
| `health_report.md` | Markdown version of health report |
| `master_error_list_YYYY-MM.txt` | Monthly error logs (JSONL format, auto-rotated) |
| `flashcards_ledger.json` | Flashcard generator progress (sha256 per input file → deck/md paths) |
| `generator.log` | Audit log for each generator run |
| `emails.csv` | Synced subscriber list (from Google Sheets) |
| `.console_edits.log` | Dashboard edit audit trail |

## Running

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in API keys

python generator.py                    # Watch mode (default: openrouter)
python maintainer.py                   # Health report
python dashboard_app.py                # Admin console → http://localhost:8878/console
python revamped_webapp.py               # Local: serves at http://localhost:8000 (see note below)
# Run locally with: uvicorn revamped_webapp:app --port 8000  (no __main__ block).
# On Vercel the entrypoint is webapp_google.py (wraps revamped_webapp + Google OAuth).
```

## Configuration (`.env` + `acumen_core/config.py`)

### API Keys
```
OPENROUTER_API_KEY      # Used by default (--llm openrouter)
PRIMARY_GEMINI_API_KEY  # Used with --llm gemini
BACKUP_GEMINI_API_KEY   # Gemini fallback
OPENROUTER_MODEL        # Default: deepseek-ai/DeepSeek-V4-Pro
SUBTOPIC_LLM_MODEL      # Pass 1.5 subtopic classifier (OpenRouter) — default openai/gpt-oss-20b
GEMINI_SUBTOPIC_MODEL   # Pass 1.5 subtopic classifier (Gemini) — default gemini-3.1-flash-lite
QUESTION_LLM_MODEL      # Flashcard front-question model (default: inherits FLASHCARD_LLM_MODEL)
QUESTION_LLM_API_KEY    # Front-question key (defaults to OPENROUTER_API_KEY)
QUESTION_LLM_BASE_URL   # Front-question endpoint (defaults to OpenRouter)
FLASHCARD_LLM_API_KEY   # Dedicated cheap model for flashcard convert/tag/regenerate (defaults to OPENROUTER_API_KEY)
FLASHCARD_LLM_MODEL     # e.g. deepseek/deepseek-chat-v3-0324 on OpenRouter
FLASHCARD_LLM_BASE_URL  # Defaults to OpenRouter
```

### Model Selection
| CLI Flag | Provider | Default Model |
|----------|----------|---------------|
| `--llm openrouter` (default) | OpenRouter | Pass 1 `OPENROUTER_SUMMARY_MODEL` (deepseek-ai/DeepSeek-V4-Pro) · Pass 1.5 `SUBTOPIC_LLM_MODEL` (openai/gpt-oss-20b) · Pass 2 `OPENROUTER_PEARLS_MODEL` (openai/gpt-oss-20b) |
| `--llm gemini` | Google Gemini | Pass 1 `GEMINI_SUMMARY_MODEL` (gemini-3.6-flash) · Pass 1.5 `GEMINI_SUBTOPIC_MODEL` (gemini-3.1-flash-lite) · Pass 2 `GEMINI_PEARLS_MODEL` (gemini-3.6-flash) |

### Pearl Extraction (Pass 2)
- OpenRouter: `openai/gpt-oss-20b` → fallback `openai/gpt-oss-120b`; Gemini: `gemini-3.6-flash`
- Config: `TEMPERATURE_PEARLS=0.2`, `MAX_TOKENS_PEARLS=8192`, `PEARLS_MAX_PER_FILE=25`

### Subtopic Classification (Pass 1.5)
- Auto-assigned at generation time after Pass 1, before Pass 2 (see `classify_subtopic()` in `acumen_core/llm.py`)
- OpenRouter: `SUBTOPIC_LLM_MODEL` (openai/gpt-oss-20b) · Gemini: `GEMINI_SUBTOPIC_MODEL` (gemini-3.1-flash-lite)
- Config: `SUBTOPIC_TEMPERATURE=0.1`, `SUBTOPIC_MAX_TOKENS=256`; non-fatal (falls back to system name)

## Pipeline Scripts — Complete CLI Reference

### `generator.py` — PDF Ingestion Pipeline
```
--mode watch           Watch input folder for new PDFs, run both passes (default)
--mode summary         Only Pass 1 (summaries). Skip pearls entirely
--mode pearls          Only Pass 2 on files with summary but no pearls yet
--mode summary_pearls  Run Pass 1 on pending PDFs, then Pass 2 on all files missing pearls
--ocr                  Enable OCR fallback for scanned PDFs + figure transcription
--max N                Process at most N files (0 = unlimited)
--once                 Process current queue once then exit (no loop)
--dry-run              Preview only, no API calls
--verbose              Detailed per-file logging
--status               Quick dashboard: pending PDFs, missing pearls, errors
--reprocess FILE.pdf   Force re-process a single specific PDF file
--extract-pearls X.json  Run Pass 2 only on one specific existing JSON
--llm {openrouter,gemini}  LLM provider for all passes (default: openrouter)
--api-key KEY          API key (direct OpenAI-compatible call)
--model NAME           Model name override
--no-link              Skip the automatic incremental cross-linking step
```

**Two-and-a-half Pass Design:**
- **Pass 1**: PDF text extraction → chunking → LLM extraction (per `EXTRACTION_SYSTEM_PROMPT`) → save to `output_files/{System}/{Type}/{file}.json`
- **Pass 1.5**: Auto subtopic classification (see `classify_subtopic()` in `acumen_core/llm.py`) — openrouter→`SUBTOPIC_LLM_MODEL` (openai/gpt-oss-20b), gemini→`GEMINI_SUBTOPIC_MODEL` (gemini-3.1-flash-lite). Writes back into summary JSON + sent_summaries.json + subtopic_mapping.json.
- **Pass 2**: Load JSON → build markdown → LLM pearl extraction → append to `pearls.json`

**Key Config in generator.py:**
- `DEFAULT_MODE = "watch"`
- `RUN_PASS_2_IMMEDIATELY = True`
- `OCR_ENABLED_DEFAULT = False`
- `QUARANTINE_AFTER_PROCESS = True`
- `PEARLS_ENABLED = True`

### `maintainer.py` — Health & Repairs
```
--reconcile             Sync disk ↔ sent_summaries.json
--validate              Schema-check all JSONs
--repair                Auto-fix safe issues
--reclassify            Fix pearl systems from summaries
--reprocess-pearls      Re-run Pass 2 for failed/missing pearls
--error-priority        Show prioritized error list
--auto-fix              Run reconcile + validate + repair + reprocess-pearls + health report
--full-scan             Include all monthly error logs
--dry-run               Preview only, no writes
--verbose               Detailed per-file logging
--report-only           Health report only, no fixes
--reset-pearls FILE     Remove & re-extract pearls for a specific JSON file
--subtopics             Sync subtopic_mapping.json → sent_summaries.json & pearls.json
--since YYYY-MM-DD      Filter errors/reports since a date
```

**Key Config:**
- `USE_DIRECTORY_AS_GROUND_TRUTH = True` — system/type from folder path overrides JSON
- `AUTO_NORMALIZE_SPECIALTIES = True`
- `REPEATED_FAILURE_THRESHOLD = 3`
- `REPROCESS_PEARL_MAX = 50`

### `syncer.py` — Git & Email
```
--mode all              Git add -A, commit, push (default)
--mode data             Git all except web app files
--mode web              Git web app files only (revamped_webapp.py + webapp_google.py + vercel.json)
--mode pearls           Git pearls.json + sent_summaries.json
--mode email            Dispatch pending emails
--mode subscribers      Sync Google Sheets → emails.csv
--mode full             subscribers → email → all (sequential)
--verify                Pre-flight health check before sync
--dry-run               Preview only, no changes
--verbose               Detailed logging
```

**Email:**
- SMTP: Gmail (hardcoded user/pass in `syncer.py`)
- Subscribers from `emails.csv` (synced from Google Sheets)
- Reads `sent_summaries.xlsx` column `email_pushed` to find pending articles
- Supports interactive selection or `--send-all`

### `flashcards.py` — Single Flashcard Script (generate, watch, theory, tag, fronts, status)
```
python flashcards.py                # generate: process every new/changed file (default command)
python flashcards.py watch          # keep watching flashcards_input/ for new/changed files
python flashcards.py theory         # generate from theory notes (THEORY/processed, env THEORY_PROCESSED_DIR)
python flashcards.py tag            # LLM re-tag store cards missing subtopic tags
python flashcards.py fronts         # generate missing front questions (QUESTION_LLM_* model)
python flashcards.py status         # pending input + store summary
python flashcards.py --as-is --file CVS/deck.md   # verbatim '==='-separated markdown transport

--spec CVS      Only process one specialty folder
--file "CVS/x.md"  Only process one file
--as-is         Verbatim '==='-separated markdown import (requires --file)
--force         Re-run even if unchanged in the ledger
--max N         Cap at N files (0 = unlimited)
--no-tag        Skip LLM subtopic tagging
--no-fronts     Skip front-question generation (raw sources)
--llm NAME      Provider for convert/tag: openrouter|together|gemini (default: openrouter)
--openrouter | --together | --gemini   Explicit provider flags (same as --llm)
--api-key KEY   Override API key -> direct OpenAI-compatible call (convert + tag + fronts)
--model NAME    Override model name (with --api-key, uses --base-url endpoint)
--base-url URL  Override endpoint (default: https://openrouter.ai/api/v1)
--dry-run       Preview only, no API calls
--verbose       Detailed logging
```
**One input folder, one output folder.** Input: `flashcards_input/{Specialty}/` — `.md` files are **authored decks** (imported as-is; `# Title` optional, each `## Card` → one card, optional `---` divider → front/back faces), everything else (pdf/txt/docx/html) is **raw material** (parsed via `acumen_core.flashcards.parse_source_file`, chunked at 30K chars `CHUNK_FLASHCARD`, LLM-refined straight into store cards — no intermediate markdown). Output: unified store `output_files/flashcards/{System}/{Subtopic}.json` + derived `flashcards_index.json`; progress in `flashcards_ledger.json` (sha256 → skip unchanged).

- Raw sources: LLM convert (`llm_convert_to_markdown`, markdown `## ` cards) → store cards `source="engine"` → LLM-tag against the subtopics vocab (`THEORY_SPEC_TO_CANONICAL` system mapping, `normalize_subtopic` fuzzy+acronym match, 1-3 tags/card) → auto front questions (`ensure_fronts`, QUESTION_LLM_* model).
- Authored md decks: imported via `acumen_core.flashcards.cards_from_markdown_deck` — re-imports match existing store cards by position and update in place (stable UUIDs, preserved tags/status/edit_history); md sections removed since last import get their store cards deleted.
- `--as-is` transport: one `.md`/`.txt` file whose cards are separated by standalone `===` lines (3+ equals) → each block = one store card (`source="md"`), content kept **verbatim** (only `---` inside a block still splits front/back). Block heading (`#`/`##`/`###`) becomes the subtopic hint, else first non-empty line. A `===` directly under a heading/text line (no blank line) is a setext underline, not a separator. After transport, the normal LLM enrichment applies (subtopic tags + front questions, unless `--no-tag`/`--no-fronts`). Implemented by `parse_separator_deck` + shared `cards_from_parsed_deck` (same position-matched UUID reuse as authored decks).
- `theory` mode walks `THEORY_PROCESSED_DIR` (default `C:/RONAK/AI Projects/ACUMEN/THEORY/processed`; override in `.env`) and skips notes already in the store by `source_file` unless `--force`.
- When `--api-key` or `--model` is set, convert/tag/fronts calls go directly to an OpenAI-compatible endpoint (`execute_openai_compat` in `acumen_core/llm.py`, base_url defaulting to OpenRouter) instead of the configured provider chain.

**Portal Theory section** (`revamped_webapp.py`, run via `uvicorn revamped_webapp:app` — it has no `__main__` block): hero with two mode cards — **Theory Topics** (rendered markdown notes from `output_files/Theory MDs/`, any file extension; title from first `# ` line; loaded by `load_theory_notes()`) and **Flashcards** (unified store). Flashcards loads decks via `load_flashcard_decks()` from `output_files/flashcards/` subtopic files (deck id `System/Subtopic`; cards carry explicit `front`/`back`/`tags`, UUID ids, no `---` divider). Features: specialty chips, deck search (incl. front/back/tags), subtopic chips when exactly one specialty active (filter decks + restrict card navigation; non-matching dots dimmed/disabled), deck list, card reader with Next/Prev + keyboard arrows, Single-face/Flip view toggle, per-card save via bookmarks API (kind `flashcard`, ref `flashcard:{uuid}`; locator stores `{deck, card: uuid, cardIdx}`), "Saved only" filter, jump dots. Flip mode shows `front` on the front face and `back` on the back; browsers without `backface-visibility` support get a `.no-3d` display-swap fallback (faces never stack). Single-face mode shows the back only. Global search adds "Flashcards" and "Theory Topics" result groups with deep links (`data-theory-card` uuid / `data-theory-note`); URL deep links supported: `?theory=flashcards[&system=…&subtopic=…&card=<uuid>]` and `?theory=notes[&note=<id>]`. Console reader likewise shows the question as a small label above the answer.

### `esbicm_parser.py` — ESBICM Trial Parsing
```
--pdf-path PATH    Override PDF location
--debug            Debug logging
--max-trials N     Cap at N trials
```
Parses the ESBICM "Recent and Landmark Trials" PDF using PyMuPDF, outputs to `output_files/esbicm_trials/`.

### `condense_trials.py` — Trial Condensation
```
--model deepseek|tencent   LLM model (default: tencent via OpenRouter)
--single Path              Process one trial file
--max N                    Cap at N trials
```
Reads raw scraped trials from `trials_database/`, condenses via LLM, saves to `output_files/trials_database_condensed/`.

### `acumen_core/linker.py` — Cross-Linking (papers ↔ guidelines ↔ theory ↔ decks)
```
python acumen_core/linker.py                 # interactive: inline [G]emini / [O]penRouter choice
--llm gemini|openrouter                      # pick provider explicitly (no prompt)
--no-prompt                                  # skip the G/O prompt (default: openrouter)
--tag-only                                   # tags only, skip LLM edge pass
--edges-only                                 # edge pass only for already-tagged entities
--force                                      # recompute everything (ignore ledger)
--max N                                      # cap at N entities (0 = unlimited)
--dry-run                                    # preview only, no writes
--api-key K --model M [--base-url U]         # direct OpenAI-compatible call
--verbose                                    # detailed logging
```
Incremental cross-linker. For each entity (paper/guideline from `sent_summaries.json`, theory note from `output_files/Theory MDs/`, flashcard deck from the unified store) it: (1) LLM-assigns topic tags (hashtag backbone, matched to `subtopics.json` vocab), (2) builds a bounded candidate shortlist (same system / same subtopic / shared tags), (3) runs a cheap LLM edge pass picking top relations with a fixed reason label (`same topic | guideline recommendation | complementary | background theory | practice deck | shared concept`). Edges persist in `output_files/related_links.json`; progress in `links_ledger.json` (content sha256 → skip unchanged). Re-runs only touch NEW/CHANGED entities (matched against the full catalog: new files link to new + old), prune deleted ones, and checkpoint-save every 50 tags / 25 edges. Interactive starts ask for the provider inline — `G` = Gemini (`GEMINI_LINKING_MODEL`, default `gemini-3.1-flash-lite`), `O` = OpenRouter (`LINKING_LLM_MODEL`, default `openai/gpt-oss-20b`); Enter defaults to O, and non-interactive runs (pipes, `--no-prompt`, `--dry-run`, explicit `--llm`) never prompt. `linker.lock` is a single-writer lock so concurrent generator/linker runs can't corrupt `related_links.json`. Portal (`revamped_webapp.py`) embeds the merged forward+reverse index as `RELATED_INDEX`/`RELATED_CATALOG` and shows a **Related** button (paper/guideline reader, pearl reader, theory note header, deck header) opening a grouped modal — Papers & Guidelines / Theory Notes / Flashcard Decks / nested Pearls — with a reason-label filter (no timestamps shown). Core logic in `acumen_core/linking.py` (`entity_catalog`, `assign_tags`, `candidate_shortlist`, `llm_pick_edges`, `related_index`).

**Auto-linking in generator.py**: every `generator.py` run (any mode; in watch-mode also on Ctrl-C exit) triggers an incremental cross-linking pass when it finishes, so new/updated content is automatically linked to the whole catalog — `--no-link` skips it, `--dry-run` never runs it, and the generator forwards its own `--llm gemini` choice to the linker (no prompt, never blocks). Since the ledger is content-hashed, a fully-linked catalog makes that pass a no-op.

## Data Flow Summary

```
PDF in input_pdfs/
    │
    ▼ Pass 1 (generator.py)
    ├─ Read PDF text (pypdf)
    ├─ OCR fallback if enabled & text < 150 chars
    ├─ Optional figure extraction (Gemini Vision)
    ├─ Chunk if > 400K chars
    ├─ LLM extraction (EXTRACTION_SYSTEM_PROMPT schema)
    ├─ Merge chunks if needed
    ├─ Enrich with markdown emphasis
    ├─ Normalize specialty & type to controlled vocab
    ├─ Save to output_files/{System}/{Type}/{file}.json
    ├─ Log to sent_summaries.json + sent_summaries.xlsx
    └─ Move PDF to quarantine/
        │
        ▼ Pass 1.5 (generator.py) — AUTO SUBTOPIC CLASSIFICATION
        ├─ classify_subtopic() on the subtopics.json vocab
        ├─ openrouter → SUBTOPIC_LLM_MODEL (openai/gpt-oss-20b)
        │  gemini   → GEMINI_SUBTOPIC_MODEL (gemini-3.1-flash-lite)
        ├─ Write subtopic into summary JSON + sent_summaries.json
        └─ Append to subtopic_mapping.json (cumulative registry)
            │
            ▼ Pass 2 (generator.py or maintainer.py)
            ├─ Build markdown from JSON
            ├─ LLM pearl extraction (openai/gpt-oss-20b)
            └─ Append to pearls.json
                │
                ▼ Dashboard (revamped_webapp.py → webapp_google.py → Vercel)
                ├─ Reads sent_summaries.json for articles
                ├─ Reads pearls.json for pearls
                └─ Reads esbicm_trials_index.json for trials
```

## Key Conventions
- **All paths** use `acumen_core.config` constants — never hardcoded strings
- **JSON writes** use `tracking.save_json_atomic()` or `storage.write_json_atomic()` (atomic tmp + replace)
- **Error logging**: monthly rotation to `master_error_list_YYYY-MM.txt` (JSONL)
- **Specialties** (23): Cardiology, Pulmonology, Infectious Diseases, Neurology, Nephrology, Gastroenterology, Hematology, Hepatology, Immunology, Sepsis, Trauma, Endocrinology, General, Multisystem, Nutrition, Obstetrics And Gynecology, Rheumatology, Toxicology, Oncology, Surgery, Cardiothoracic, Vascular, Other
- **Type values**: Review, RCT, Meta-analysis, Guideline, Observational, Case Series, Trial, Other
- **Dashboard specialties** in `revamped_webapp.py` `SPEC_COLORS` dict: 24 entries (slightly different from above)
- **Sent summaries tracking**: dual-tracked in both JSON + Excel
- **Subtopics**: auto-assigned via LLM during generation (generator Pass 1.5 — see `classify_subtopic()` in `acumen_core/llm.py`); stored in `subtopics.json` (master vocabulary, its keys = the specialty list) + `subtopic_mapping.json` (auto-filled registry). Retired manual tools (`subtopic_mapper.py`, `bulk_subtopic_classifier.py`, `specialties.txt`/`subtopics.txt`, `pending_subtopics.json`) are quarantined under `quarantine/{date}/subtopic-mapping/`.
- **LLM provider fallback**: OpenRouter pass chains try their primary then fallback model; Gemini chains primary key then backup key (no Together/DeepSeek remnants)
- **File naming**: output file = `{basename}.json` (same stem as PDF). pearl `file_name` = `{basename}.json`
- **Audit trail**: `generator.log`, `.console_edits.log`, `master_error_list_*.txt`

## Dependencies (requirements.txt)
```
pypdf, together, openai, python-dotenv, openpyxl, google-genai,
PyMuPDF, pdf2image, pytesseract, fastapi, uvicorn, requests, beautifulsoup4
```

## Vercel Deployment
- Entrypoint: `webapp_google.py` (see `vercel.json`) — imports `revamped_webapp.app` and adds Google OAuth landing
- URL: `hack-ccm-acumen-microlearning.vercel.app`
- Serves the public knowledge portal with papers, guidelines, pearls, and trials views

## Console Dashboard
- `dashboard_app.py` → `http://localhost:8878/console`
- Single-page vanilla JS app (`dashboard/static/dashboard.html`)
- CRUD for summaries, pearls, flashcards, theory
- Cascade reclassification when summary system/subtopic changes
- Git push from UI via async `PushWorker`
- Backup/restore system
- Audit log viewer