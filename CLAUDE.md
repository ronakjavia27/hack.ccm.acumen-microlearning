# CLAUDE.md — Permanent instructions for Claude (hack.CCM)

Read this first in **every** chat. Then read `PROJECT_STATUS.md` (what is happening now) and, when you need to find code, `docs/ARCHITECTURE.md` + the graphify map.
Full reference of CLI flags / env vars / pipelines lives in `AGENTS.md` — do not duplicate it here.

## 0. Multi-chat sync protocol (MANDATORY)
Several chats edit this repo. The repo is the shared memory; chat memory is not.
1. **Start of chat:** `git fetch && git pull` (or merge `origin/main` into your branch), then read `PROJECT_STATUS.md`. Check "In progress" so you don't collide with another chat's work.
2. **Before touching a file listed under "In progress / Claimed files"**, stop and tell the user.
3. **End of chat / after any meaningful change:** update `PROJECT_STATUS.md` (completed, in progress, bugs, next) and, if structure/routes/data shapes changed, `docs/ARCHITECTURE.md`. Commit these in the same commit as the code.
4. Keep entries short, dated (`YYYY-MM-DD`) and append-only in "Recent changes" (newest first). Never delete another chat's entry unless it is done/obsolete.
5. Never leave a chat's decisions only in conversation — if it matters later, it goes in these files.

## 1. Code map (graphify) — use before grepping
`graphify-out/` is a committed knowledge graph of the code (~1000 nodes). It updates **automatically**:
- `SessionStart` hook in `.claude/settings.json` runs `scripts/sync_graph.sh` (installs `graphifyy` if missing, installs git hooks, runs `graphify update .`).
- Git hooks (post-commit/checkout/merge/rewrite) rebuild it on every commit/pull; `.gitattributes` union-merges `graph.json` so parallel chats don't conflict.
- Manual: `bash scripts/sync_graph.sh` or `graphify update .` (AST only, no LLM, ~5s).
Usage: read `graphify-out/GRAPH_REPORT.md` for hubs; `graphify query "<question>"`, `graphify explain "<node>"`, `graphify path "A" "B"`, `graphify affected "<node>"` for impact before refactors. If `GRAPH_REPORT.md` "Built from commit" ≠ `git rev-parse HEAD`, run the sync script. Never hand-edit `graphify-out/`. Community names refresh with `graphify label .` (needs an LLM key; optional).

## 2. Architecture rules
- Live app = `webapp_redefined.py` → `webapp_google` → `redefined_ui` → `revamped_webapp`. **Import order matters** (routes are copied at import time). Do not reorder.
- `redefined_ui.py` is read-only over `revamped_webapp.py`; add new portal features in `redefined_ui.py` (`/api/redefined/*`). Edit `revamped_webapp.py` only for shared/auth/bookmark routes or classic UI fixes.
- All paths come from `acumen_core.config` — never hardcode.
- JSON writes are atomic (`tracking.save_json_atomic` / `dashboard.storage.write_json_atomic`).
- Vocab (specialties/subtopics) comes only from `acumen_core/subtopics.json`.
- Persistent user data (auth, sessions, bookmarks, study progress) goes through `acumen_core.kv` (Upstash on Vercel, `local_kv.json` locally). Vercel's filesystem is read-only/ephemeral: never write app state to disk in web routes.
- Content data (summaries, pearls, flashcards, MCQs, theory) is produced by offline pipelines (`generator.py`, `flashcards.py`, `mcq_generator.py`, `linker.py`) and committed as JSON; the web app only reads it.

## 3. Safety rules
- Never commit secrets: `.env`, `API keys.txt`, `local_kv.json`, `data/auth_kv.json` contents. Note `syncer.py` has hard-coded SMTP credentials — do not copy/print them, do not spread the pattern; flag to the user.
- No destructive ops (`rm -rf`, force-push, history rewrite, deleting `output_files/`, `pearls.json`, `sent_summaries.json`) without explicit user approval. Use `--dry-run` first for pipeline scripts.
- Pipeline scripts call paid LLM APIs — run only on request; prefer `--dry-run`/`--max N`.
- Develop on the branch assigned to the session; do not push to `main` or open PRs unless asked.
- Auth/admin routes: preserve gating (`/api/admin/*`, per-user access flags). Don't weaken them for convenience. `scripts/clear_auth_kv.py` wipes auth state — never run unprompted.
- Clinical content: don't invent doses, trial results or citations; data must come from the source JSON.

## 4. Design standards
Source of truth: `design-system/hack-ccm/MASTER.md` (page overrides in `design-system/pages/<page>.md` if present).
- Fonts: Atkinson Hyperlegible (UI/body), Source Serif 4 (long theory reading), JetBrains Mono (labels/data).
- Slate neutrals + one clinical teal accent; green/red/amber **only** for answer feedback and recall ratings. Light + dark themes.
- 44px touch targets, visible focus rings, `prefers-reduced-motion`, keyboard-first study flows (space flip, 1–4 rate, A–E answer, Ctrl/Cmd‑K search). Mobile-first: test ~375px width, no horizontal overflow.
- Minimal motion, standard density. No new color/font without updating MASTER.md.

## 5. Coding practices
- Python 3, match surrounding style; small focused diffs; no drive-by refactors in the 6.5k-line `revamped_webapp.py` (its HTML/JS is one inline f-string — escape `{}` as `{{ }}`).
- Check before committing: `python -c "import webapp_redefined"` (import order/sytax), and for UI changes run `uvicorn webapp_redefined:app --port 8000` and exercise the page (Playwright/Chromium is available; use `--trace off`).
- Prefer editing existing modules over adding root-level scripts. New pipeline script ⇒ ledger (sha256 skip), `--dry-run`, `--max`, logging.
- New API route ⇒ document it in `docs/ARCHITECTURE.md`. New data file/key ⇒ document shape there too.
- Commit messages: imperative, explain why. Commit docs updates with the code.
