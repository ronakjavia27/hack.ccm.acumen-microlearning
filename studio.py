"""
studio.py — uploaded questions → model answer + flashcards + MCQs → verify → review → publish.

  python studio.py ingest                 # split new/changed files in studio_input/{Medicine|Microbiology|CCM}/
  python studio.py generate [--max 10]    # draft + verify + triage queued items (LLM)
  python studio.py run [--max 10]         # ingest then generate
  python studio.py status                 # counts by status / triage
  python studio.py list [--status generated --triage green]
  python studio.py approve-green --by "Dr X"   # bulk-approve green items
  python studio.py publish                # publish every approved item into the portal stores
  python studio.py review                 # print how to open the review UI

Flags: --subject ccm|medicine|microbiology  --file "CCM/paper.txt"  --force  --no-context
       --dry-run  --verbose
Review/approve individual items in the console: python dashboard_app.py → http://localhost:8878/console/studio
Design: docs/studio/DESIGN.md
"""
import argparse
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from acumen_core import config
from acumen_core.studio import generate, intake, items, publish


def cmd_ingest(a):
    r = intake.ingest_folder(only_file=a.file, force=a.force, dry_run=a.dry_run, verbose=True)
    print(f"[+] {len(r['new'])} new questions, {len(r['merged'])} already known, "
          f"{len(r['skipped_files'])} unchanged files skipped")
    return r


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
                    choices=["ingest", "generate", "run", "status", "list", "approve-green", "publish", "review"])
    ap.add_argument("--subject", default="", choices=["", "medicine", "microbiology", "ccm"])
    ap.add_argument("--file", default="")
    ap.add_argument("--max", type=int, default=0)
    ap.add_argument("--status", default="")
    ap.add_argument("--triage", default="")
    ap.add_argument("--by", default=config.STUDIO_REVIEWER)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-context", action="store_true", help="don't pass library excerpts as hints")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    if a.command == "ingest":
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
        print("python dashboard_app.py  →  http://localhost:8878/console/studio")


if __name__ == "__main__":
    main()
