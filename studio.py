"""
studio.py — uploaded questions → model answer + flashcards + MCQs → verify → review → publish.

  python studio.py watch                  # background loop: ingest the inbox + generate, every 5 min (laptop hub)
  python studio.py watch --once           # one pass (testing)
  python studio.py ingest                 # ingest new files in the inbox (STUDIO_INPUT_DIR):
                                          #   {CCM|Medicine|Microbiology}/*.md|docx  → one NOTE item per file
                                          #   {Subject}/Questions/** or *.csv        → one item per question
  python studio.py generate [--max 10]    # draft + verify + triage queued items (LLM)
  python studio.py run [--max 10]         # ingest then generate
  python studio.py status                 # counts by status / triage
  python studio.py list [--status generated --triage green]
  python studio.py approve-green --by "Dr X"   # bulk-approve green items
  python studio.py publish                # publish every approved item into the portal stores
  python studio.py review                 # print how to open the review UI

Flags: --subject ccm|medicine|microbiology  --file "CCM/paper.txt"  --force  --no-context
       --interval 300  --once  --dry-run  --verbose
Caps: STUDIO_MAX_CALLS_PER_RUN (40) and STUDIO_MAX_CALLS_PER_DAY (200) LLM calls; capped items stay queued.
Review/approve individual items in the console: python dashboard_app.py → http://localhost:8878/console/studio
Design: docs/studio/DESIGN.md
"""
import argparse
import sys
import time
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from acumen_core import config
from acumen_core.studio import generate, intake, items, publish


def cmd_ingest(a, verbose=True):
    r = intake.ingest_folder(only_file=a.file, force=a.force, dry_run=a.dry_run, verbose=verbose)
    print(f"[+] {len(r['new'])} new, {len(r['updated'])} updated notes, {len(r['merged'])} already known, "
          f"{len(r['skipped_files'])} unchanged files, {len(r['settling'])} still syncing, {len(r['errors'])} errors")
    for e in r["errors"]:
        print(f"    [X] {e['file']}: {e['error']}")
    return r


def cmd_watch(a):
    if not a.dry_run and not config.STUDIO_API_KEY:
        sys.exit("[X] No STUDIO_API_KEY / OPENROUTER_API_KEY in .env")
    print(f"[*] watching {config.STUDIO_INPUT_DIR} every {a.interval}s · draft={config.STUDIO_DRAFT_MODEL} "
          f"verify={config.STUDIO_VERIFY_MODEL} · caps {config.STUDIO_MAX_CALLS_PER_RUN}/run, "
          f"{config.STUDIO_MAX_CALLS_PER_DAY}/day · Ctrl-C to stop")
    while True:
        stamp = datetime.now().strftime("%H:%M")
        try:
            r = intake.ingest_folder(force=a.force, dry_run=a.dry_run, verbose=a.verbose)
            g = generate.generate_pending(max_items=a.max, subject=a.subject, verbose=a.verbose, dry_run=a.dry_run,
                                          use_context=not a.no_context)
            used = generate.usage_today().get("calls", 0)
            if r["new"] or r["updated"] or g["processed"] or g["capped"] or r["errors"] or a.once:
                print(f"[{stamp}] inbox: +{len(r['new'])} new, {len(r['updated'])} updated, {len(r['settling'])} syncing"
                      f" · generated {g['processed']} (🟢{g['green']} 🟠{g['amber']} 🔴{g['red']} ✖{g['error']})"
                      f" · {used} calls today" + (f" · CAPPED: {g['capped']}" if g["capped"] else ""))
        except KeyboardInterrupt:
            raise
        except Exception as e:  # never let one bad pass kill the watcher
            print(f"[{stamp}] [X] pass failed: {type(e).__name__}: {e}")
        if a.once:
            return
        time.sleep(a.interval)


def cmd_generate(a):
    if not a.dry_run and not config.STUDIO_API_KEY:
        sys.exit("[X] No STUDIO_API_KEY / OPENROUTER_API_KEY in .env")
    print(f"[*] draft={config.STUDIO_DRAFT_MODEL}  verify={config.STUDIO_VERIFY_MODEL}")
    r = generate.generate_pending(max_items=a.max, subject=a.subject, verbose=True, dry_run=a.dry_run,
                                  use_context=not a.no_context)
    print(f"[+] processed {r['processed']}: green {r['green']} · amber {r['amber']} · red {r['red']} · error {r['error']}")


def cmd_status(a):
    all_ = items.all_items(a.subject)
    c = items.counts(all_)
    print(f"Studio items: {len(all_)}")
    for k in ("queued", "revision_requested", "generating", "generated", "generated:green", "generated:amber",
              "generated:red", "approved", "published", "rejected", "error"):
        if c.get(k):
            print(f"  {k:<20} {c[k]}")


def cmd_list(a):
    for it in items.all_items(a.subject):
        if a.status and it["status"] != a.status:
            continue
        if a.triage and it.get("triage") != a.triage:
            continue
        print(f"{it['id']:<24} {it['status']:<12} {str(it.get('triage') or ''):<6} {it['question'][:90]}")


def main():
    ap = argparse.ArgumentParser(description="hack.CCM Content Studio")
    ap.add_argument("command", nargs="?", default="status",
                    choices=["watch", "ingest", "generate", "run", "status", "list", "approve-green", "publish", "review"])
    ap.add_argument("--subject", default="", choices=["", "medicine", "microbiology", "ccm"])
    ap.add_argument("--file", default="")
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--interval", type=int, default=config.STUDIO_WATCH_INTERVAL, help="watch: seconds between passes")
    ap.add_argument("--once", action="store_true", help="watch: run one pass and exit")
    ap.add_argument("--status", default="")
    ap.add_argument("--triage", default="")
    ap.add_argument("--by", default=config.STUDIO_REVIEWER)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-context", action="store_true", help="don't pass library excerpts as hints")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    if a.command == "watch":
        try:
            cmd_watch(a)
        except KeyboardInterrupt:
            print("\n[*] watcher stopped")
    elif a.command == "ingest":
        cmd_ingest(a)
    elif a.command == "generate":
        cmd_generate(a)
    elif a.command == "run":
        cmd_ingest(a)
        cmd_generate(a)
    elif a.command == "status":
        cmd_status(a)
    elif a.command == "list":
        cmd_list(a)
    elif a.command == "approve-green":
        ids = publish.approve_green(a.by, a.subject)
        print(f"[+] approved {len(ids)} green items as '{a.by}'. Next: python studio.py publish")
    elif a.command == "publish":
        r = publish.publish_approved(a.subject)
        print(f"[+] published {len(r['published'])}; failed {len(r['failed'])}")
        for f in r["failed"]:
            print(f"    [X] {f['id']}: {f['error']}")
        if r["published"]:
            print("    Deploy with the console Push button or: python syncer.py --mode data")
    elif a.command == "review":
        print("python dashboard_app.py  →  http://localhost:8878/console/studio  (phone: see docs/console/REMOTE_ACCESS.md)")


if __name__ == "__main__":
    main()
