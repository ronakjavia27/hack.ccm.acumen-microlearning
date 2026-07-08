#!/usr/bin/env python3
"""hack.CCM — Manual Absolute Backup & Restore CLI.

Usage:
  python ccm_backup.py backup --label my-label
  python ccm_backup.py list
  python ccm_backup.py verify <name>
  python ccm_backup.py restore --from <name> --to <path> [--force]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard.backup import create_backup, list_backups, verify_backup, restore_backup


def cmd_backup(args):
    dest = create_backup(args.label)
    print(f"Backup created at {dest}")
    sys.exit(0)


def cmd_list(args):
    backups = list_backups()
    if not backups:
        print("No backups found.")
        sys.exit(0)
    print(f"{'Name':<40} {'Timestamp':<22} {'Label':<20} {'HEAD':<12} {'Files':<7} {'Size':<8} {'Dirty':<6}")
    print("-" * 120)
    for b in backups:
        print(f"{b['name']:<40} {b['timestamp']:<22} {b['label']:<20} {b['git_head']:<12} "
              f"{b['file_count']:<7} {b['size_kb']:<8} {'Y' if b['dirty'] else 'N':<6}")
    sys.exit(0)


def cmd_verify(args):
    result = verify_backup(args.name)
    if result["ok"]:
        print(f"Backup '{args.name}' is VALID.")
        sys.exit(0)
    print(f"Backup '{args.name}' has ISSUES:")
    for iss in result.get("issues", []):
        print(f"  - {iss}")
    sys.exit(1)


def cmd_restore(args):
    result = restore_backup(args.from_backup, args.to, args.force)
    if result["ok"]:
        print(f"Restored to {result['restored_to']} (from {result['from_backup']})")
        sys.exit(0)
    print(f"ERROR: {result['error']}")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="hack.CCM absolute backup/restore")
    sub = parser.add_subparsers(dest="command", required=True)

    p_backup = sub.add_parser("backup", help="Create a full snapshot")
    p_backup.add_argument("--label", default="manual", help="Optional label (default: manual)")
    p_backup.set_defaults(func=cmd_backup)

    p_list = sub.add_parser("list", help="List all backups")
    p_list.set_defaults(func=cmd_list)

    p_verify = sub.add_parser("verify", help="Verify backup integrity")
    p_verify.add_argument("name", help="Backup folder name")
    p_verify.set_defaults(func=cmd_verify)

    p_restore = sub.add_parser("restore", help="Restore a backup to a directory")
    p_restore.add_argument("--from-backup", required=True, help="Backup folder name")
    p_restore.add_argument("--to", required=True, help="Target directory path")
    p_restore.add_argument("--force", action="store_true", help="Overwrite target if exists")
    p_restore.set_defaults(func=cmd_restore)

    parsed = parser.parse_args()
    parsed.func(parsed)


if __name__ == "__main__":
    main()
