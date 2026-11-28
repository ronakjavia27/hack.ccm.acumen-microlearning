# Graph Report - hack.ccm.acumen-microlearning  (2026-11-28)

## Corpus Check
- 1075 files · ~2,885,925 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 22 file(s) not represented in the graph (top: (none) 12, .log 7, .example 1)

## Summary
- 1017 nodes · 2705 edges · 42 communities (39 shown, 3 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 13 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `27412b92`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Pearl Reclassification Cascade
- Portal Admin User Management
- Key-Value Store Backend
- Bookmarks API and Markdown Backfill
- Excel Tracker and Vocabulary
- generate_health_report
- Flashcard LLM and Linking
- Summary Tracking Ledger
- LLM Provider Clients
- Git Sync and Email
- Console Flashcard CRUD
- Flashcard Source Parsing
- Subtopic Tagging and Questions
- Flashcard CLI Commands
- os
- vocabulary.py
- Raw Trial Data Schema
- Flashcard Store Operations
- PDF OCR and Vision
- maintainer.py
- Condensed Trial Schema
- Subtopic Vocabulary Config
- Trial Appraisal Sections
- cards_from_parsed_deck
- Trial Design Fields
- raw_cards_to_store
- Frontend Package Dependencies
- Backup Manifest Fields
- main
- acumen_core/config.py
- Clinical Markdown Emphasis
- mcq_generator.py
- Clinical Bottom Line
- Critical Appraisal Fields
- PICO Fields
- Study Background Fields
- Results Section Fields
- Vercel Deployment Config
- Quick Recall Fields
- load_json_safe
- sync_graph.sh
- entry_from_payload

## God Nodes (most connected - your core abstractions)
1. `audit()` - 31 edges
2. `kv_get()` - 30 edges
3. `_get_session_user()` - 29 edges
4. `save_json_atomic()` - 25 edges
5. `kv_set()` - 24 edges
6. `_get_session_user()` - 22 edges
7. `ItemNotFound` - 21 edges
8. `render_dashboard()` - 20 edges
9. `write_json_atomic()` - 19 edges
10. `read_json()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `repair_all()` --calls--> `build_specialty_map()`  [EXTRACTED]
  maintainer.py → acumen_core/vocabulary.py
- `render_dashboard()` --calls--> `build_specialty_map()`  [EXTRACTED]
  revamped_webapp.py → acumen_core/vocabulary.py
- `initialize_system()` --calls--> `get_allowed_specialties()`  [EXTRACTED]
  generator.py → acumen_core/vocabulary.py
- `repair_all()` --calls--> `get_allowed_specialties()`  [EXTRACTED]
  maintainer.py → acumen_core/vocabulary.py
- `render_dashboard()` --calls--> `get_allowed_specialties()`  [EXTRACTED]
  revamped_webapp.py → acumen_core/vocabulary.py

## Import Cycles
- None detected.

## Communities (42 total, 3 thin omitted)

### Community 0 - "Pearl Reclassification Cascade"
Cohesion: 0.06
Nodes (44): cascade_apply(), cascade_preview(), cascade_summary_update(), _load_pearls(), _save_pearls(), ItemNotFound, ModuleSpec, register() (+36 more)

### Community 1 - "Portal Admin User Management"
Cohesion: 0.06
Nodes (76): _articles(), classic_ui(), _clean_progress(), _doi_url(), _find_summary_json(), _has_feature(), _load_mcq_store(), _mcq_index() (+68 more)

### Community 2 - "Key-Value Store Backend"
Cohesion: 0.06
Nodes (55): kv_backend(), kv_delete(), kv_get(), kv_scan(), kv_set(), _load(), _save(), _use_upstash() (+47 more)

### Community 3 - "Bookmarks API and Markdown Backfill"
Cohesion: 0.09
Nodes (49): content_signature(), call_chat_api(), api_bookmarks_add(), api_bookmarks_delete(), api_bookmarks_folder_add(), api_bookmarks_folder_delete(), api_bookmarks_folder_update(), api_bookmarks_list() (+41 more)

### Community 4 - "Excel Tracker and Vocabulary"
Cohesion: 0.08
Nodes (24): get_error_list_path(), read_current_month_errors(), write_error(), load_all_entries_from_json(), load_processed_files_from_json(), update_entry_in_json(), update_pearl_tracker(), append_to_log() (+16 more)

### Community 5 - "generate_health_report"
Cohesion: 0.15
Nodes (7): get_all_error_list_paths(), read_all_errors(), build_disk_index(), generate_health_report(), _generate_markdown_report(), _is_on_or_after(), _is_within_days()

### Community 6 - "Flashcard LLM and Linking"
Cohesion: 0.09
Nodes (21): _run_linking(), _flush(), candidate_shortlist(), _collect_text(), deck_entities(), deck_id(), entity_catalog(), fallback_edges() (+13 more)

### Community 7 - "Summary Tracking Ledger"
Cohesion: 0.10
Nodes (12): append_pending_subtopic(), append_subtopic_mapping(), _atomic_write_json(), build_entry_from_metadata(), initialize_excel_tracker(), load_pending_subtopics(), log_transaction_to_excel(), log_transaction_to_json() (+4 more)

### Community 8 - "LLM Provider Clients"
Cohesion: 0.10
Nodes (20): llm_convert_to_markdown(), _linking_call(), llm_pick_edges(), call_gemini_api(), call_openrouter_api(), classify_subtopic(), execute_openai_compat(), execute_pearl_extraction() (+12 more)

### Community 9 - "Git Sync and Email"
Cohesion: 0.07
Nodes (24): _backup_path(), create_backup(), _exclude_cache(), _list_backup_dirs(), list_backups(), _pack_tree(), restore_backup(), _run() (+16 more)

### Community 10 - "Console Flashcard CRUD"
Cohesion: 0.16
Nodes (15): flashcard_llm(), upsert_card(), bulk_delete(), bulk_set_status(), delete_item(), _find(), _find_store_card(), get_item() (+7 more)

### Community 11 - "Flashcard Source Parsing"
Cohesion: 0.12
Nodes (16): build_card(), canonical_systems_for(), _cards_from_dict(), _cards_from_markdown(), extract_docx(), extract_html(), _extract_markdown(), extract_md_txt() (+8 more)

### Community 12 - "Subtopic Tagging and Questions"
Cohesion: 0.15
Nodes (17): _acronym(), normalize_subtopic(), tag_cards_with_llm(), assign_tags(), get_subtopics_for_system(), classify_batch(), clean_specialty(), clean_subtopic() (+9 more)

### Community 13 - "Flashcard CLI Commands"
Cohesion: 0.15
Nodes (21): file_sha256(), load_ledger(), save_ledger(), store_cards_all(), add_provider_args(), canonical_systems(), cmd_fronts(), cmd_generate() (+13 more)

### Community 14 - "os"
Cohesion: 0.06
Nodes (16): _acquire_lock(), main(), _pid_alive(), _print(), _prompt_provider(), _release_lock(), _atomic_write_json(), main() (+8 more)

### Community 15 - "vocabulary.py"
Cohesion: 0.18
Nodes (8): build_specialty_map(), get_allowed_specialties(), get_allowed_types(), load_allowed_vocabulary(), normalize_specialty(), normalize_type(), save_extracted_json(), extract_metadata_from_payload()

### Community 16 - "Raw Trial Data Schema"
Cohesion: 0.09
Nodes (21): citation, citation_text, doi, full_name, id, name, scraped_at, sections (+13 more)

### Community 17 - "Flashcard Store Operations"
Cohesion: 0.15
Nodes (11): canonical_subtopic(), find_card(), load_flashcards_index(), load_subtopic_file(), move_card(), rebuild_flashcards_index(), remove_card(), remove_card_from() (+3 more)

### Community 18 - "PDF OCR and Vision"
Cohesion: 0.13
Nodes (6): call_gemini_vision(), describe_image_via_gemini(), extract_embedded_images(), extract_figure_text(), ocr_pil_image(), extract_text_from_pdf()

### Community 19 - "maintainer.py"
Cohesion: 0.14
Nodes (5): append_removed_entries(), load_pearl_tracker(), load_removed_entries(), build_markdown_for_pearls_from_payload(), normalize_title()

### Community 20 - "Condensed Trial Schema"
Cohesion: 0.11
Nodes (18): citation, doi, evidence_level, id, journal, keywords, one_liner, registration (+10 more)

### Community 21 - "Subtopic Vocabulary Config"
Cohesion: 0.22
Nodes (5): get_all_systems(), is_valid_subtopic(), _load_raw(), load_subtopics(), subtopics_exist()

### Community 22 - "Trial Appraisal Sections"
Cohesion: 0.14
Nodes (14): domains, verdict, domains, verdict, sections, authors_conclusion, context_related_trials, controversies (+6 more)

### Community 23 - "cards_from_parsed_deck"
Cohesion: 0.12
Nodes (8): cards_from_markdown_deck(), cards_from_parsed_deck(), load_import_meta(), parse_card_content(), parse_markdown_deck(), parse_separator_deck(), _separator_block(), import_markdown_as_is()

### Community 24 - "Trial Design Fields"
Cohesion: 0.15
Nodes (13): blinding, comparison, design, follow_up, intervention, population, primary_outcome, sample_size_power (+5 more)

### Community 25 - "raw_cards_to_store"
Cohesion: 0.33
Nodes (3): ensure_fronts(), generate_card_question(), raw_cards_to_store()

### Community 26 - "Frontend Package Dependencies"
Cohesion: 0.29
Nodes (9): dependencies, puppeteer@^25.4.0, tailwindcss@^4.3.1, @tailwindcss/vite@^4.3.1, @vercel/analytics@^2.0.1, puppeteer, tailwindcss, @tailwindcss/vite (+1 more)

### Community 27 - "Backup Manifest Fields"
Cohesion: 0.22
Nodes (8): branch, bundle_ok, dirty, file_count, git_head, label, timestamp, tool_version

### Community 28 - "main"
Cohesion: 0.18
Nodes (8): auto_fix(), error_priority_report(), main(), reclassify_pearls(), reconcile(), repair_all(), validate_all(), validate_json_file()

### Community 29 - "acumen_core/config.py"
Cohesion: 0.17
Nodes (3): classify_error(), get_priority(), read_errors_from_file()

### Community 31 - "mcq_generator.py"
Cohesion: 0.14
Nodes (22): save_related_links(), chunk_text(), save_json_atomic(), call_llm(), cmd_generate(), cmd_status(), collect(), FLASHCARD_LLM_API_KEY_() (+14 more)

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

### Community 39 - "load_json_safe"
Cohesion: 0.18
Nodes (6): load_json_safe(), load_subtopic_mapping(), append_pearls_to_json(), reprocess_pearls(), reset_pearls_for_file(), sync_subtopics()

## Knowledge Gaps
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `audit()` connect `Pearl Reclassification Cascade` to `Bookmarks API and Markdown Backfill`, `LLM Provider Clients`, `Key-Value Store Backend`, `Console Flashcard CRUD`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Should `Pearl Reclassification Cascade` be split into smaller, more focused modules?**
  _Cohesion score 0.05666293393057111 - nodes in this community are weakly interconnected._
- **Why does `google_auth_handler()` connect `os` to `Portal Admin User Management`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Should `Portal Admin User Management` be split into smaller, more focused modules?**
  _Cohesion score 0.057318894697535476 - nodes in this community are weakly interconnected._
- **Why does `kv_get()` connect `Key-Value Store Backend` to `Portal Admin User Management`, `Bookmarks API and Markdown Backfill`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Should `Key-Value Store Backend` be split into smaller, more focused modules?**
  _Cohesion score 0.06264199935086011 - nodes in this community are weakly interconnected._
- **Should `Bookmarks API and Markdown Backfill` be split into smaller, more focused modules?**
  _Cohesion score 0.09317051108095885 - nodes in this community are weakly interconnected._