"""
linker.py - Standalone cross-linker for papers, guidelines, theory notes, flashcard decks.

Incremental design:
  - A ledger (links_ledger.json) stores a content hash per entity.
  - On each run only NEW or CHANGED entities are re-linked. Each is matched
    against the FULL catalog (old + new), so new files link to both new and
    old content. Unchanged entities keep their stored edges.
  - Deleted papers (sent_summaries_removed.json) and vanished theory/deck
    entities are pruned every run.

Usage:
  python acumen_core/linker.py                # interactive: choose [G]emini or [O]penRouter
  python acumen_core/linker.py --llm gemini   # Gemini provider chain (no prompt)
  python acumen_core/linker.py --no-prompt    # skip the G/O prompt (default: openrouter)
  python acumen_core/linker.py --tag-only     # skip the LLM edge pass (tags only)
  python acumen_core/linker.py --force        # recompute everything
  python acumen_core/linker.py --dry-run      # preview only, no writes
  python acumen_core/linker.py --max 10       # cap entities processed
  python acumen_core/linker.py --api-key K --model M [--base-url U]  # direct OpenAI-compat

Flags:
  --llm gemini|openrouter  pick the provider explicitly (default: interactive G/O prompt)
  --no-prompt              don't ask; use openrouter (gemini-3.1-flash-lite on --llm gemini)
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_LOCK_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "linker.lock")


def _pid_alive(pid):
    if os.name == "nt":
        import subprocess
        try:
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                                 capture_output=True, text=True, timeout=10).stdout
            return str(pid) in out and "No tasks" not in out
        except Exception:
            return True
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _acquire_lock():
    """Single-writer lock so concurrent linker/generator runs cannot corrupt
    related_links.json. Returns True when this process owns the lock."""
    try:
        if os.path.exists(_LOCK_FILE):
            try:
                with open(_LOCK_FILE, "r", encoding="utf-8") as f:
                    holder = json.load(f)
                if _pid_alive(int(holder.get("pid") or 0)):
                    _print(f"Another linker run is active (PID {holder.get('pid')}) — skipping (incremental run can continue later).")
                    return False
            except (OSError, ValueError, json.JSONDecodeError):
                pass
        with open(_LOCK_FILE, "w", encoding="utf-8") as f:
            json.dump({"pid": os.getpid(), "start": time.time()}, f)
        return True
    except OSError:
        return True


def _release_lock():
    try:
        if os.path.exists(_LOCK_FILE):
            os.remove(_LOCK_FILE)
    except OSError:
        pass


def _print(*args, **kwargs):
    if hasattr(sys.stdout, "encoding") and sys.stdout.encoding:
        enc = sys.stdout.encoding.lower()
        safe = True
        for arg in args:
            if isinstance(arg, str):
                try:
                    arg.encode(sys.stdout.encoding)
                except UnicodeEncodeError:
                    safe = False
                    break
        if not safe:
            print(*(str(a).encode("ascii", errors="replace").decode("ascii") if isinstance(a, str) else a for a in args), **kwargs, flush=True)
            return
    print(*args, **kwargs, flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Incremental cross-linking of clinical content")
    ap.add_argument("--llm", default=None, choices=["openrouter", "gemini"],
                    help="Provider for the cheap tag/edge calls. Interactive runs "
                         "choose first instead (G=gemini, O=openrouter).")
    ap.add_argument("--no-prompt", action="store_true",
                    help="skip the interactive provider choice (use the default)")
    ap.add_argument("--api-key", default="", help="override API key (direct OpenAI-compatible call)")
    ap.add_argument("--model", default="", help="override model (with --api-key)")
    ap.add_argument("--base-url", default="", help="override endpoint (default: OpenRouter)")
    ap.add_argument("--tag-only", action="store_true", help="assign tags but skip the LLM edge pass")
    ap.add_argument("--edges-only", action="store_true", help="edge pass only (no re-tagging)")
    ap.add_argument("--force", action="store_true", help="recompute every entity (ignore ledger)")
    ap.add_argument("--max", type=int, default=0, help="cap at N entities (0 = unlimited)")
    ap.add_argument("--dry-run", action="store_true", help="preview only; no API calls or writes")
    ap.add_argument("--verbose", action="store_true", help="verbose logging")
    args = ap.parse_args(argv)

    from acumen_core import linking as li

    if args.llm is None and not args.no_prompt and not args.dry_run \
            and not (args.api_key or args.model) and sys.stdin.isatty():
        args.llm = _prompt_provider()

    try:
        from acumen_core.config import GEMINI_LINKING_MODEL, LINKING_LLM_MODEL
        if args.api_key or args.model:
            provider_note = f"direct API ({args.model or LINKING_LLM_MODEL})"
        elif (args.llm or "openrouter") == "gemini":
            provider_note = f"gemini ({GEMINI_LINKING_MODEL})"
        else:
            provider_note = f"openrouter ({LINKING_LLM_MODEL})"
        _print(f"Linking provider: {provider_note}")
    except ImportError:
        pass

    if not _acquire_lock():
        return
    try:
        _run_linking(args, li)
    finally:
        _release_lock()


def _prompt_provider():
    """Inline G/O choice for interactive runs. Returns 'gemini' or 'openrouter'."""
    for attempt in range(2):
        try:
            ans = input("Linking provider - [G]emini (gemini-3.1-flash-lite) or "
                        "[O]penRouter (gpt-oss-20b)? [O]: ").strip().lower()
        except EOFError:
            return "openrouter"
        if ans in ("g", "gemini"):
            return "gemini"
        if ans in ("o", "openrouter", ""):
            return "openrouter"
        if attempt == 0:
            _print("  please answer G or O (Enter defaults to O)...")
    return "openrouter"


def _run_linking(args, li):
    catalog = li.entity_catalog()
    catalog.sort(key=lambda e: e.get("id", ""))
    _print(f"Catalog: {len(catalog)} entities "
           f"({sum(1 for e in catalog if e['kind'] == 'paper')} papers, "
           f"{sum(1 for e in catalog if e['kind'] == 'guideline')} guidelines, "
           f"{sum(1 for e in catalog if e['kind'] == 'theory')} theory, "
           f"{sum(1 for e in catalog if e['kind'] == 'flashcard_deck')} decks)")

    links = li.load_related_links()
    ledger = li.load_ledger()
    existing_ids = set(links.get("entities", {}).keys())

    # ---- decide which entities need work ----
    changed = []
    for e in catalog:
        sig = li.content_signature(e)
        if args.force or ledger.get(e["id"]) != sig:
            changed.append(e)
        elif e["id"] not in existing_ids:
            changed.append(e)

    if args.edges_only:
        changed = [e for e in changed
                   if ((links.get("entities") or {}).get(e["id"]) or {}).get("tags")]

    if args.max > 0:
        changed = changed[: args.max]

    need_work = [e["id"] for e in changed]
    skip = len(catalog) - len(need_work)
    _print(f"To process: {len(need_work)} (unchanged: {skip}); "
           f"tags={'on' if not args.edges_only else 'skip'} | edges={'on' if not args.tag_only else 'off'}")

    if args.dry_run:
        _print("--dry-run: nothing written. Would re-link:")
        for e in changed:
            _print(f"  {e['id']}  [{e['kind']} | {e.get('system')} | {e.get('subtopic')}]")
        if not changed:
            _print("  (nothing to do)")
        return

    # ---- tags (unless edges-only) + edge scores for candidates ----
    all_tags = li.tags_from_store(links)

    def _flush():
        li.save_related_links(links)
        li.save_ledger(ledger)

    tagged_count = 0
    for e in changed:
        ent = links["entities"].get(e["id"]) or {}
        if not args.edges_only:
            if args.verbose:
                _print(f"[tag] {e['id']}")
            tags = li.assign_tags(e, verbose=args.verbose,
                                  api_key=args.api_key or None,
                                  model=args.model or None,
                                  base_url=args.base_url or None,
                                  llm=args.llm)
            ent["tags"] = tags
            all_tags[e["id"]] = tags
            li.log_line(f"tagged {e['id']} -> {len(tags)} tags")
            tagged_count += 1
            if tagged_count % 50 == 0:
                _flush()
                _print(f"  ...tag checkpoint saved at {tagged_count}/{len(changed)}")
        else:
            all_tags[e["id"]] = ent.get("tags") or []
        ent.setdefault("kind", e["kind"])
        ent.setdefault("system", e.get("system", ""))
        ent.setdefault("type", e.get("type", ""))
        ent.setdefault("subtopic", e.get("subtopic", ""))
        ent.setdefault("title", e.get("title", ""))
        links["entities"][e["id"]] = ent

    # ---- edge pass ----
    if not args.tag_only:
        processed_count = 0
        for e in changed:
            if args.verbose:
                _print(f"[edges] {e['id']}")
            candidates = li.candidate_shortlist(e, catalog, all_tags)
            edges = li.llm_pick_edges(e, candidates, verbose=args.verbose,
                                      api_key=args.api_key or None,
                                      model=args.model or None,
                                      base_url=args.base_url or None,
                                      llm=args.llm)
            if not edges:
                edges = li.fallback_edges(e, candidates)
            links["entities"][e["id"]]["links"] = edges
            li.log_line(f"linked {e['id']} -> {len(edges)} targets")
            processed_count += 1
            if processed_count % 25 == 0:
                _flush()
                _print(f"  ...checkpoint saved at {processed_count}/{len(changed)}")
    else:
        for e in changed:
            links["entities"][e["id"]].setdefault("links", [])

    # ---- update ledger ----
    for e in changed:
        ledger[e["id"]] = li.content_signature(e)

    # ---- prune removed / deleted entities ----
    live_ids = {e["id"] for e in catalog}
    pruned_ids = [eid for eid in list(links["entities"].keys()) if eid not in live_ids]
    for eid in pruned_ids:
        del links["entities"][eid]
        ledger.pop(eid, None)
    for eid in list(links["entities"].keys()):
        kept = [lb for lb in links["entities"][eid].get("links") or [] if lb.get("to") in live_ids]
        links["entities"][eid]["links"] = kept
    if pruned_ids:
        _print(f"Pruned {len(pruned_ids)} deleted entities")

    _flush()
    li.log_line(f"linker run complete: processed={len(changed)}")
    _print(f"Saved related_links.json ({len(links['entities'])} entities, "
           f"{sum(len(e.get('links') or []) for e in links['entities'].values())} edges)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted — progress was checkpoint-saved.")
        raise SystemExit(130)