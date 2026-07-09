# hack.CCM — AI Microlearning Platform

## Overview
AI-powered clinical microlearning platform. Ingests medical PDFs, extracts structured summaries and clinical pearls via LLMs, and serves them through a FastAPI web dashboard.

## Project Structure

### Root Scripts (Entry Points)
```
main_app.py             — FastAPI web app serving the public dashboard at /
dashboard_app.py        — Admin console at /console
revamped_webapp.py      — Alternative/legacy web app
generator.py            — PDF ingestion pipeline (Pass 1: summaries, Pass 2: pearls)
maintainer.py           — Health checks, schema validation, repairs, error reports
syncer.py               — Git sync, email dispatch, subscriber sync
esbicm_parser.py        — ESICM trials parser
backfill_markdown.py    — Backfill markdown for existing summaries
build_trials_organsystem.py — Build trials by organ system index
```

### Core Library: `acumen_core/`
```
acumen_core/
├── config.py              — Paths, API keys, model names, extraction params
├── schema.py              — JSON schemas & system prompts for LLM extraction
├── llm.py                 — LLM client abstraction (Together, Gemini, custom)
├── ocr.py                 — OCR pipeline for scanned PDFs
├── markdown.py            — Markdown enrichment utilities
├── tracking.py            — Atomic JSON save/load, edit locks
├── errors.py              — Monthly error log rotation & reading
├── vocabulary.py          — Specialty/type normalization
├── subtopic_mapper.py     — Subtopic classification (interactive + batch LLM)
├── subtopics_config.py    — Subtopic configuration data
└── subtopics.json         — Allowed subtopics per specialty
```

### Dashboard: `dashboard/`
```
dashboard/
├── app.py                 — FastAPI router for /console/api/*
├── storage.py             — Atomic JSON writer, git push worker
├── cascade.py             — Bulk pearl reclassification on summary changes
├── backup.py              — Cross-platform backup/restore
└── static/dashboard.html  — Single-page admin UI
```

### Data Directories
```
input_pdfs/
├── articles/              — Place medical PDF articles here
├── guidelines/            — Place clinical guidelines here
└── other/                 — Other PDFs

output_files/              — Generated JSON summaries by specialty/type
  {Specialty}/{Type}/{filename}.json
```

### Tracker / Ledger Files (root)
```
sent_summaries.json       — Approved summaries ledger
sent_summaries_removed.json — Removed/deleted entries
pearls.json               — All extracted clinical pearls (~2000)
pearls_processed.json     — Pearl extraction tracker
pearls_processed.xlsx     — Excel version
pending_subtopics.json    — Unclassified subtopics
subtopic_mapping.json     — Subtopic assignments
pearl_updater_progress.json — Batch operation progress
health_report.json        — Auto-generated health report
health_report.md          — Markdown health report
```

### Pipeline Scripts
| Script | Purpose | Key Modes |
|--------|---------|-----------|
| `generator.py` | PDF ingestion: extract → pearls | `--mode watch` (default), `summary`, `pearls`, `summary_pearls` |
| `maintainer.py` | Health & repairs | `--reconcile`, `--validate`, `--repair`, `--auto-fix` |
| `syncer.py` | Git sync & email | `--mode all`, `data`, `web`, `pearls`, `email` |

## Running
```bash
pip install -r requirements.txt
cp .env.example .env   # fill in API keys

python generator.py                    # Watch mode
python maintainer.py                   # Health report
python dashboard_app.py                # Admin console
```

## Configuration
- **Env**: `.env` with `TOGETHER_API_KEY`, `DEEPSEEK_API_KEY`, `PRIMARY_GEMINI_API_KEY`, `BACKUP_GEMINI_API_KEY`
- **Models**: `acumen_core/config.py` — extraction, pearl, and vision model names
- **LLM Provider**: `--llm together` (default), `--llm gemini`, `--llm other`

## Key Conventions
- All paths use `acumen_core.config` constants (not hardcoded strings)
- Error logging: monthly rotation to `master_error_list_YYYY-MM.txt`
- JSON writes use atomic save (`acumen_core.tracking.save_json_atomic`)
- Specialties list (23): Cardiology, Pulmonology, Infectious Diseases, Neurology, Nephrology, Gastroenterology, Hematology, Hepatology, Immunology, Sepsis, Trauma, Endocrinology, General, Multisystem, Nutrition, Obstetrics And Gynecology, Rheumatology, Toxicology, Oncology, Surgery, Cardiothoracic, Vascular, Other
- Type values: Review, RCT, Meta-analysis, Guideline, Observational, Case Series, Trial, etc.
