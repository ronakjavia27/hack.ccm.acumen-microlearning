# hack.CCM — AI Microlearning Platform (Complete Reference)

## Overview
AI-powered clinical microlearning platform. Ingests medical PDFs, extracts structured summaries and clinical pearls via LLMs, and serves them through a FastAPI web dashboard.

## Project Structure

### Root Entry Points
| File | Purpose |
|------|---------|
| `main_app.py` | Public dashboard (Vercel-deployed, serves `/`) |
| `revamped_webapp.py` | Identical to main_app.py (old backup) — same content, separate deployment |
| `dashboard_app.py` | Admin console at `/console` (port 8878) — wraps `dashboard/` |
| `generator.py` | PDF ingestion pipeline (Pass 1: summaries, Pass 2: pearls) |
| `maintainer.py` | Health checks, schema validation, repairs, error reports |
| `syncer.py` | Git sync, email dispatch, subscriber sync |
| `flashcard_engine.py` | Generates study flashcards from theory notes |
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
| `llm.py` | LLM client abstraction — Together AI, Gemini, OpenRouter, custom OpenAI-compat. Functions: `execute_with_fallback`, `execute_with_gemini`, `execute_with_openrouter`, `execute_pearl_extraction`, `chunk_text`, `merge_chunks_programmatically` |
| `ocr.py` | OCR for scanned PDFs via PyMuPDF + pytesseract + Gemini Vision |
| `markdown.py` | `apply_markdown_emphasis` — bolds clinical numbers/units/keywords |
| `tracking.py` | Atomic JSON save/load, Excel tracker, sent_summaries CRUD, pearl tracker, pending subtopics queue |
| `errors.py` | Monthly error log `master_error_list_YYYY-MM.txt` (JSONL), error classification, priority levels (CRITICAL→LOW) |
| `vocabulary.py` | Normalizes specialties & article types to controlled vocabulary (reads `specialties.txt`, `article_types.txt`) |
| `subtopic_mapper.py` | Interactive CLI + batch LLM for assigning subtopics to pending papers |
| `subtopics_config.py` | Loads `subtopics.json`, provides `get_subtopics_for_system()`, `is_valid_subtopic()`, `format_subtopics_for_prompt()` |
| `subtopics.json` | 272 lines — full subtopic vocabulary per specialty (e.g. Cardiology→ACS, Shock, HF...) |

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
| `modules/flashcards.py` | Flashcard CRUD + card regeneration |
| `modules/theory.py` | Theory note CRUD |

### Data Directories
```
input_pdfs/
├── articles/        → Place medical PDF articles here
├── guidelines/      → Place clinical guidelines here
└── other/           → Other PDFs

output_files/
  {Specialty}/{Type}/{filename}.json        — Structured summaries
  esbicm_trials/                            — ESBICM trial data
  trials_database_condensed/                — Condensed trial JSON
  flashcards/{Specialty}/{slug}.json        — Generated flashcards

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
| `pending_subtopics.json` | Queue of papers awaiting subtopic assignment |
| `subtopic_mapping.json` | Registry of completed subtopic assignments |
| `pearl_updater_progress.json` | Batch pearl operation progress |
| `health_report.json` | Auto-generated health report |
| `health_report.md` | Markdown version of health report |
| `master_error_list_YYYY-MM.txt` | Monthly error logs (JSONL format, auto-rotated) |
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
python main_app.py                     # Public dashboard → http://localhost:8000
```

## Configuration (`.env` + `acumen_core/config.py`)

### API Keys
```
OPENROUTER_API_KEY      # Used by default (--llm openrouter)
PRIMARY_GEMINI_API_KEY  # Used with --llm gemini
BACKUP_GEMINI_API_KEY   # Gemini fallback
TOGETHER_API_KEY        # Used with --llm together (also for pearl extraction)
DEEPSEEK_API_KEY        # Fallback in execute_with_fallback chain
OPENROUTER_MODEL        # Default: deepseek-ai/DeepSeek-V4-Pro
```

### Model Selection
| CLI Flag | Provider | Default Model |
|----------|----------|---------------|
| `--llm openrouter` (default) | OpenRouter | `OPENROUTER_MODEL` from `.env` |
| `--llm together` | Together AI | `deepseek-ai/DeepSeek-V4-Pro` → fallback to same → fallback to Direct DeepSeek |
| `--llm gemini` | Google Gemini | `gemini-2.5-flash` → fallback `gemini-2.5-flash` (backup key) |
| `--llm other` | Custom OpenAI-compat | Provide `--api-key` and `--model` |

### Pearl Extraction (Pass 2)
- Always uses Together AI: `openai/gpt-oss-20b` → fallback `openai/gpt-oss-120b`
- Config: `TEMPERATURE_PEARLS=0.2`, `MAX_TOKENS_PEARLS=8192`, `PEARLS_MAX_PER_FILE=25`

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
--llm {together,gemini,openrouter,other}  LLM provider for Pass 1
--api-key KEY          API key for --llm openrouter/other
--model NAME           Model name for --llm openrouter/other
```

**Two-Pass Design:**
- **Pass 1**: PDF text extraction → chunking → LLM extraction (per `EXTRACTION_SYSTEM_PROMPT`) → save to `output_files/{System}/{Type}/{file}.json`
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
--mode data             Git all except main_app.py
--mode web              Git main_app.py only
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

### `flashcard_engine.py` — Flashcard Generation
```
--force       Re-generate all (default: skip existing)
--max         Generate more cards (10-15 per note, default ~6-8)
--limit N     Process only first N files
--model NAME  Override OpenRouter model
--dry-run     Show what would be processed
```
Scans `THEORY/processed/` for `.md` files, sends to OpenRouter, saves to `output_files/flashcards/`.

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
    ├─ Queue to pending_subtopics.json
    └─ Move PDF to quarantine/
        │
        ▼ Pass 2 (generator.py or maintainer.py)
        ├─ Build markdown from JSON
        ├─ LLM pearl extraction (openai/gpt-oss-20b)
        └─ Append to pearls.json
            │
            ▼ Dashboard (main_app.py → Vercel)
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
- **Dashboard specialties** in `main_app.py` `SPEC_COLORS` dict: 24 entries (slightly different from above)
- **Sent summaries tracking**: dual-tracked in both JSON + Excel
- **Subtopics**: assigned interactively via `subtopic_mapper.py` or batch LLM; stored in `subtopics.json` (master vocabulary) + `pending_subtopics.json` (queue) + `subtopic_mapping.json` (registry)
- **LLM provider fallback order** for `--llm together`: Together Pro → Together Flash → Direct DeepSeek API
- **File naming**: output file = `{basename}.json` (same stem as PDF). pearl `file_name` = `{basename}.json`
- **Audit trail**: `generator.log`, `.console_edits.log`, `master_error_list_*.txt`

## Dependencies (requirements.txt)
```
pypdf, together, openai, python-dotenv, openpyxl, google-genai,
PyMuPDF, pdf2image, pytesseract, fastapi, uvicorn, requests, beautifulsoup4
```

## Vercel Deployment
- `main_app.py` is deployed to Vercel (see `vercel.json`)
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