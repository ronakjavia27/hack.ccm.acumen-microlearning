# PROJECT_STATUS.md — Live state of hack.CCM

> Shared memory across chats. **Read before working, update before ending.** Protocol in `CLAUDE.md` §0.
> Last updated: 2026-11-28

## Production
- Vercel entrypoint `webapp_redefined.py` (theory-first UI at `/`, classic UI at `/classic`, Google OAuth landing). URL: `hack-ccm-acumen-microlearning.vercel.app`.

## Completed
- PDF ingestion pipeline: summaries (Pass 1), subtopic classification (1.5), pearls (Pass 2); maintainer health/repair tooling.
- Unified flashcard store (`output_files/flashcards/{System}/{Subtopic}.json`) + index; flashcard generator (md decks, raw sources, `--as-is`).
- Cross-linker (`acumen_core/linker.py`) with auto-run after generator.
- Admin console (`/console`) with CRUD, cascade, backup, audit.
- Redefined portal (`redefined_ui.py`): Today, Topics, Flashcards (SM-2), MCQs (tutor/exam), Pearls, Guidelines, Papers, Trials; per-user progress API.
- MCQ generator (`mcq_generator.py`) → `output_files/mcqs/` (draft status).
- Google OAuth sign-in; auth/session/bookmarks in KV; per-user access flags (`theory` on by default for non-admins in redefined UI).
- Design system record `design-system/hack-ccm/MASTER.md`.
- Latest fixes: mobile overflow/specialty chips/pearls layout; topic links opening with no data.
- Graphify code map committed + auto-sync (hook, git hooks, merge driver) — 2026-11-28.
- Shared-memory docs: `CLAUDE.md`, `PROJECT_STATUS.md`, `docs/ARCHITECTURE.md` — 2026-11-28.

## In progress / Claimed files
_Add a line when you start work that spans multiple commits; remove it when done._
| Chat/branch | Area / files | Since | Notes |
|---|---|---|---|
| — | — | — | nothing claimed |

## Known issues / outstanding bugs
- `syncer.py` contains hard-coded SMTP user/password (security risk) — should move to `.env`.
- `revamped_webapp.py` is a 6.5k-line single file with inline HTML/JS f-string; hard to review/test.
- MCQs are all `status: draft`; no reviewer workflow in console/portal yet (verify whether portal shows drafts).
- `theory` flashcard mode in `flashcards.py` defaults to a Windows path (`C:/RONAK/...`) — set `THEORY_PROCESSED_DIR` on other machines.
- Repo root has clutter (`linker*.log`, `backups/`, `FILE_INDEX.txt` dated 2026-07, `HOW_TO_RUN.txt`) — `FILE_INDEX.txt` is stale vs. current layout.
- Graph community labels go stale after large changes; refresh with `graphify label .` (needs LLM key).

## Recent major changes (newest first)
- 2026-11-28 — Added CLAUDE.md, PROJECT_STATUS.md, docs/ARCHITECTURE.md; `scripts/sync_graph.sh` + SessionStart hook + `.gitattributes` for dynamic graphify updates; untracked machine-local graphify files.
- 2026-11-2x — Mobile overflow / chips / pearls layout fixes; topic-link fix (`27412b9`, `2520c65`).
- 2026-11-2x — Live portal switched to redefined UI (`6983acf`); theory-first overhaul, MCQ generator, design-system record (`75ff801`).
- 2026-11-25 — `redefined_ui.py` + graphify code map (`b578fe9`).

## Next priorities
1. MCQ review/approve flow (console + portal) and surface approved MCQs only.
2. Move SMTP creds to env; remove from repo history.
3. Split `revamped_webapp.py` (extract inline HTML/JS) to cut review cost.
4. Refresh/clean `FILE_INDEX.txt`/`HOW_TO_RUN.txt` or fold into `docs/ARCHITECTURE.md`.
5. Add smoke tests (`scripts/test_auth.py` is the only one) for `/api/redefined/*`.
