# Graph Report - hack.ccm.acumen-microlearning  (2026-11-25)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 957 nodes · 2515 edges · 40 communities (38 shown, 2 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 13 edges (avg confidence: 0.85)
- Token cost: 48,669 input · 594 output

## Graph Freshness
- Built from commit: `bf0e88bd`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Pearl Reclassification Cascade
- Portal Admin User Management
- Key-Value Store Backend
- Bookmarks API and Markdown Backfill
- Excel Tracker and Vocabulary
- Schema and JSON Utilities
- Flashcard LLM and Linking
- Summary Tracking Ledger
- LLM Provider Clients
- Git Sync and Email
- Console Flashcard CRUD
- Flashcard Source Parsing
- Subtopic Tagging and Questions
- Flashcard CLI Commands
- Cross-Linker CLI and Lock
- Config and Error Logging
- Raw Trial Data Schema
- Flashcard Store Operations
- PDF OCR and Vision
- Backup Creation and Restore
- Condensed Trial Schema
- Subtopic Vocabulary Config
- Trial Appraisal Sections
- Flashcard Ledger and Import
- Trial Design Fields
- Card Building and Fronts
- Frontend Package Dependencies
- Backup Manifest Fields
- Linking Paper Entities
- Markdown Deck Import
- Clinical Markdown Emphasis
- Pearl Extraction Pass
- Clinical Bottom Line
- Critical Appraisal Fields
- PICO Fields
- Study Background Fields
- Results Section Fields
- Vercel Deployment Config
- Quick Recall Fields

## God Nodes (most connected - your core abstractions)
1. `audit()` - 31 edges
2. `kv_get()` - 30 edges
3. `_get_session_user()` - 27 edges
4. `kv_set()` - 24 edges
5. `_get_session_user()` - 22 edges
6. `save_json_atomic()` - 22 edges
7. `ItemNotFound` - 21 edges
8. `write_json_atomic()` - 19 edges
9. `render_dashboard()` - 19 edges
10. `read_json()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `_access_defaults()` --calls--> `kv_get()`  [EXTRACTED]
  revamped_webapp.py → acumen_core/kv.py
- `_access_defaults()` --calls--> `kv_set()`  [EXTRACTED]
  revamped_webapp.py → acumen_core/kv.py
- `_admin_save_defaults()` --calls--> `kv_set()`  [EXTRACTED]
  revamped_webapp.py → acumen_core/kv.py
- `_admin_users_list()` --calls--> `kv_scan()`  [EXTRACTED]
  revamped_webapp.py → acumen_core/kv.py
- `api_debug()` --calls--> `kv_backend()`  [EXTRACTED]
  revamped_webapp.py → acumen_core/kv.py

## Import Cycles
- None detected.

## Communities (40 total, 2 thin omitted)

### Community 0 - "Pearl Reclassification Cascade"
Cohesion: 0.06
Nodes (42): cascade_apply(), cascade_preview(), cascade_summary_update(), _load_pearls(), _save_pearls(), ItemNotFound, bulk_delete(), bulk_set_status() (+34 more)

### Community 1 - "Portal Admin User Management"
Cohesion: 0.07
Nodes (60): _access_defaults(), _admin_save_defaults(), _admin_users_list(), api_admin_users_defaults(), api_admin_users_defaults_update(), api_admin_users_delete(), api_admin_users_list(), api_admin_users_update() (+52 more)

### Community 2 - "Key-Value Store Backend"
Cohesion: 0.06
Nodes (55): kv_backend(), kv_delete(), kv_get(), kv_scan(), kv_set(), _load(), _save(), _use_upstash() (+47 more)

### Community 3 - "Bookmarks API and Markdown Backfill"
Cohesion: 0.09
Nodes (50): content_signature(), _atomic_write_json(), main(), api_bookmarks_add(), api_bookmarks_delete(), api_bookmarks_folder_add(), api_bookmarks_folder_delete(), api_bookmarks_folder_update() (+42 more)

### Community 4 - "Excel Tracker and Vocabulary"
Cohesion: 0.07
Nodes (26): initialize_excel_tracker(), load_processed_files_from_json(), build_specialty_map(), get_allowed_specialties(), get_allowed_types(), load_allowed_vocabulary(), normalize_specialty(), normalize_type() (+18 more)

### Community 5 - "Schema and JSON Utilities"
Cohesion: 0.08
Nodes (21): load_json_safe(), load_subtopic_mapping(), save_json_atomic(), update_pearl_tracker(), auto_fix(), build_disk_index(), build_markdown_for_pearls_from_payload(), entry_from_payload() (+13 more)

### Community 6 - "Flashcard LLM and Linking"
Cohesion: 0.09
Nodes (23): flashcard_llm(), llm_convert_to_markdown(), _run_linking(), _flush(), assign_tags(), candidate_shortlist(), deck_entities(), deck_id() (+15 more)

### Community 7 - "Summary Tracking Ledger"
Cohesion: 0.08
Nodes (16): append_pending_subtopic(), append_removed_entries(), append_subtopic_mapping(), _atomic_write_json(), build_entry_from_metadata(), load_all_entries_from_json(), load_pearl_tracker(), load_pending_subtopics() (+8 more)

### Community 8 - "LLM Provider Clients"
Cohesion: 0.13
Nodes (15): call_gemini_api(), call_openrouter_api(), classify_subtopic(), execute_pearl_extraction(), execute_with_fallback(), execute_with_gemini(), execute_with_openrouter(), execute_with_openrouter_text() (+7 more)

### Community 9 - "Git Sync and Email"
Cohesion: 0.11
Nodes (13): convert_markdown_to_html(), dispatch_emails(), full_sync(), generate_button_ribbon(), git_diff_cached_stat(), git_status_porcelain(), git_sync(), main() (+5 more)

### Community 10 - "Console Flashcard CRUD"
Cohesion: 0.15
Nodes (17): upsert_card(), api_flashcard_regenerate(), bulk_delete(), bulk_set_status(), delete_item(), _find(), _find_store_card(), get_item() (+9 more)

### Community 11 - "Flashcard Source Parsing"
Cohesion: 0.12
Nodes (16): build_card(), canonical_systems_for(), _cards_from_dict(), _cards_from_markdown(), extract_docx(), extract_html(), _extract_markdown(), extract_md_txt() (+8 more)

### Community 12 - "Subtopic Tagging and Questions"
Cohesion: 0.15
Nodes (16): _acronym(), generate_card_question(), normalize_subtopic(), tag_cards_with_llm(), call_chat_api(), classify_batch(), clean_specialty(), clean_subtopic() (+8 more)

### Community 13 - "Flashcard CLI Commands"
Cohesion: 0.15
Nodes (16): store_cards_all(), chunk_text(), add_provider_args(), canonical_systems(), cmd_fronts(), cmd_generate(), cmd_status(), cmd_tag() (+8 more)

### Community 14 - "Cross-Linker CLI and Lock"
Cohesion: 0.11
Nodes (10): _acquire_lock(), main(), _pid_alive(), _print(), _prompt_provider(), _release_lock(), get_all_error_list_paths(), get_error_list_path() (+2 more)

### Community 15 - "Config and Error Logging"
Cohesion: 0.13
Nodes (9): get_all_error_list_paths(), get_error_list_path(), classify_error(), get_priority(), read_all_errors(), read_current_month_errors(), read_errors_from_file(), write_error() (+1 more)

### Community 16 - "Raw Trial Data Schema"
Cohesion: 0.09
Nodes (21): citation, citation_text, doi, full_name, id, name, scraped_at, sections (+13 more)

### Community 17 - "Flashcard Store Operations"
Cohesion: 0.17
Nodes (10): find_card(), load_flashcards_index(), load_subtopic_file(), move_card(), rebuild_flashcards_index(), remove_card(), remove_card_from(), _save_card() (+2 more)

### Community 18 - "PDF OCR and Vision"
Cohesion: 0.13
Nodes (6): call_gemini_vision(), describe_image_via_gemini(), extract_embedded_images(), extract_figure_text(), ocr_pil_image(), extract_text_from_pdf()

### Community 19 - "Backup Creation and Restore"
Cohesion: 0.21
Nodes (11): _backup_path(), create_backup(), _exclude_cache(), _list_backup_dirs(), list_backups(), _pack_tree(), restore_backup(), _run() (+3 more)

### Community 20 - "Condensed Trial Schema"
Cohesion: 0.11
Nodes (18): citation, doi, evidence_level, id, journal, keywords, one_liner, registration (+10 more)

### Community 21 - "Subtopic Vocabulary Config"
Cohesion: 0.19
Nodes (7): format_subtopics_for_prompt(), get_all_systems(), get_subtopics_for_system(), is_valid_subtopic(), _load_raw(), load_subtopics(), subtopics_exist()

### Community 22 - "Trial Appraisal Sections"
Cohesion: 0.14
Nodes (14): domains, verdict, domains, verdict, sections, authors_conclusion, context_related_trials, controversies (+6 more)

### Community 23 - "Flashcard Ledger and Import"
Cohesion: 0.18
Nodes (9): file_sha256(), load_ledger(), parse_separator_deck(), save_ledger(), _separator_block(), pending(), import_markdown_as_is(), ledger_path() (+1 more)

### Community 24 - "Trial Design Fields"
Cohesion: 0.15
Nodes (13): blinding, comparison, design, follow_up, intervention, population, primary_outcome, sample_size_power (+5 more)

### Community 25 - "Card Building and Fronts"
Cohesion: 0.20
Nodes (5): canonical_subtopic(), cards_from_parsed_deck(), ensure_fronts(), load_import_meta(), parse_card_content()

### Community 26 - "Frontend Package Dependencies"
Cohesion: 0.29
Nodes (9): dependencies, puppeteer@^25.4.0, tailwindcss@^4.3.1, @tailwindcss/vite@^4.3.1, @vercel/analytics@^2.0.1, puppeteer, tailwindcss, @tailwindcss/vite (+1 more)

### Community 27 - "Backup Manifest Fields"
Cohesion: 0.22
Nodes (8): branch, bundle_ok, dirty, file_count, git_head, label, timestamp, tool_version

### Community 28 - "Linking Paper Entities"
Cohesion: 0.25
Nodes (5): _collect_text(), paper_id(), removed_entity_ids(), summaries_entities(), _summary_payload_path()

### Community 29 - "Markdown Deck Import"
Cohesion: 0.33
Nodes (3): cards_from_markdown_deck(), parse_markdown_deck(), import_md_deck()

### Community 31 - "Pearl Extraction Pass"
Cohesion: 0.33
Nodes (3): append_pearls_to_json(), build_markdown_for_pearls(), run_pearl_extraction_pass()

### Community 32 - "Clinical Bottom Line"
Cohesion: 0.40
Nodes (5): applies_to, does_not_mean, implementation_caveats, verdict, clinical_bottom_line

### Community 33 - "Critical Appraisal Fields"
Cohesion: 0.40
Nodes (5): rating, strengths, summary, weaknesses, critical_appraisal

### Community 34 - "PICO Fields"
Cohesion: 0.40
Nodes (5): pico, comparison, intervention, outcome, population

### Community 35 - "Study Background Fields"
Cohesion: 0.50
Nodes (4): existing_knowledge, hypothesis, knowledge_gap, background

### Community 36 - "Results Section Fields"
Cohesion: 0.50
Nodes (4): headline_bullets, outcomes_table, subgroup_table, results

### Community 37 - "Vercel Deployment Config"
Cohesion: 0.50
Nodes (3): builds, routes, version

### Community 38 - "Quick Recall Fields"
Cohesion: 0.67
Nodes (3): numbers_to_remember, one_line_takeaway, quick_recall

## Knowledge Gaps
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `audit()` connect `Pearl Reclassification Cascade` to `Bookmarks API and Markdown Backfill`, `LLM Provider Clients`, `Key-Value Store Backend`, `Console Flashcard CRUD`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Should `Pearl Reclassification Cascade` be split into smaller, more focused modules?**
  _Cohesion score 0.05792759051186017 - nodes in this community are weakly interconnected._
- **Why does `write_json_atomic()` connect `Pearl Reclassification Cascade` to `Bookmarks API and Markdown Backfill`, `Excel Tracker and Vocabulary`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Should `Portal Admin User Management` be split into smaller, more focused modules?**
  _Cohesion score 0.06964443138407288 - nodes in this community are weakly interconnected._
- **Should `Key-Value Store Backend` be split into smaller, more focused modules?**
  _Cohesion score 0.06265432098765432 - nodes in this community are weakly interconnected._
- **Should `Bookmarks API and Markdown Backfill` be split into smaller, more focused modules?**
  _Cohesion score 0.0886615515771526 - nodes in this community are weakly interconnected._
- **Should `Excel Tracker and Vocabulary` be split into smaller, more focused modules?**
  _Cohesion score 0.07441016333938294 - nodes in this community are weakly interconnected._