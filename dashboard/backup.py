"""Backup / restore logic — cross-platform Python, no external deps.

Called both from the CLI (`ccm_backup.py`) and the dashboard API
(`/console/api/backup/*`).

Backup structure under `backups/<timestamp>__<label>/`:
  - tree.tar.gz       full working tree snapshot (files tracked + untracked,
                      excluding backups/, .venv/, __pycache__/)
  - history.bundle    `git bundle create --all`
  - manifest.json     metadata (ts, label, git HEAD, dirty flag, file count)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = REPO_ROOT / "backups"

EXCLUDE_DIRS = {".venv", "__pycache__", ".git", "backups", "node_modules", ".idea"}

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _run(args: List[str], cwd: Optional[Path] = None) -> Tuple[int, str]:
    p = subprocess.run(
        args,
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return p.returncode, (p.stdout + p.stderr).strip()


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_label(label: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in label).strip("._")


def _backup_path(label: str) -> Path:
    ts = _timestamp()
    safe = _safe_label(label)
    return BACKUP_DIR / f"{ts}__{safe}"


def _list_backup_dirs() -> List[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        [d for d in BACKUP_DIR.iterdir() if d.is_dir() and d.name != ".gitkeep"],
        reverse=True,
    )


# ---------------------------------------------------------------------------
# create backup
# ---------------------------------------------------------------------------
def create_backup(label: str = "manual") -> Path:
    """Create a full snapshot. Returns the path to the backup folder."""
    dest = _backup_path(label)
    dest.mkdir(parents=True, exist_ok=True)

    # ---- manifest ----
    rc, head = _run(["git", "rev-parse", "HEAD"])
    head_sha = head.strip() if rc == 0 else "unknown"

    rc2, dirty_out = _run(["git", "status", "--porcelain"])
    is_dirty = bool(dirty_out.strip())

    rc3, branch_out = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    branch = branch_out.strip() if rc3 == 0 else "detached"

    # ---- tree.tar.gz ----
    tree_path = dest / "tree.tar.gz"
    file_count = _pack_tree(tree_path)

    # ---- git bundle ----
    bundle_path = dest / "history.bundle"
    rc4, bundle_out = _run(
        ["git", "bundle", "create", str(bundle_path), "--all"]
    )
    bundle_ok = rc4 == 0

    manifest = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "label": label,
        "git_head": head_sha,
        "branch": branch,
        "dirty": is_dirty,
        "file_count": file_count,
        "bundle_ok": bundle_ok,
        "tool_version": "hack.CCM-console-0.1",
    }
    manifest_path = dest / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return dest


def _pack_tree(dest: Path) -> int:
    count = 0
    with tarfile.open(dest, "w:gz") as tar:
        for item in REPO_ROOT.iterdir():
            if item.name in EXCLUDE_DIRS or item.name.startswith("."):
                continue
            tar.add(item, arcname=item.relative_to(REPO_ROOT), filter=_exclude_cache)
            count += 1
        # also include selected dotfiles (not whole .git, just .gitignore etc)
        for dot in (".gitignore", ".env.example", ".editorconfig", ".console_edits.log"):
            p = REPO_ROOT / dot
            if p.exists():
                tar.add(p, arcname=dot)
    return count


def _exclude_cache(tarinfo: tarfile.TarInfo) -> Optional[tarfile.TarInfo]:
    if tarinfo.name.startswith("backups/") or "__pycache__" in tarinfo.name:
        return None
    return tarinfo


# ---------------------------------------------------------------------------
# list backups
# ---------------------------------------------------------------------------
def list_backups() -> List[Dict[str, Any]]:
    out = []
    for d in _list_backup_dirs():
        man = d / "manifest.json"
        if not man.exists():
            continue
        with open(man, "r") as f:
            m = json.load(f)
        size_bytes = sum(
            f.stat().st_size for f in d.rglob("*") if f.is_file()
        )
        out.append({
            "name": d.name,
            "path": str(d),
            "timestamp": m.get("timestamp", ""),
            "label": m.get("label", ""),
            "git_head": m.get("git_head", "")[:12],
            "branch": m.get("branch", ""),
            "dirty": m.get("dirty", False),
            "file_count": m.get("file_count", 0),
            "bundle_ok": m.get("bundle_ok", False),
            "size_kb": round(size_bytes / 1024, 1),
        })
    return out


# ---------------------------------------------------------------------------
# verify backup
# ---------------------------------------------------------------------------
def verify_backup(name: str) -> Dict[str, Any]:
    d = BACKUP_DIR / name
    if not d.exists():
        return {"ok": False, "error": f"backup '{name}' not found"}
    man = d / "manifest.json"
    tree = d / "tree.tar.gz"
    bundle = d / "history.bundle"
    issues = []
    if not man.exists():
        issues.append("manifest.json missing")
    if not tree.exists():
        issues.append("tree.tar.gz missing")
    else:
        # test tar integrity
        try:
            with tarfile.open(tree) as tf:
                members = tf.getmembers()
        except (tarfile.TarError, OSError) as e:
            issues.append(f"tree.tar.gz corrupt: {e}")
    if not bundle.exists():
        issues.append("history.bundle missing")
    else:
        rc, out = _run(["git", "bundle", "verify", str(bundle)])
        if rc != 0:
            issues.append(f"history.bundle verify failed: {out}")
    return {"ok": len(issues) == 0, "issues": issues, "name": name}


# ---------------------------------------------------------------------------
# restore
# ---------------------------------------------------------------------------
def restore_backup(backup_name: str, target: str, force: bool = False) -> Dict[str, Any]:
    """Rebuild a working copy inside `target`. Never touches the live repo
    unless target == REPO_ROOT and --force is passed."""
    src = BACKUP_DIR / backup_name
    if not src.exists():
        return {"ok": False, "error": f"backup '{backup_name}' not found"}
    dst = Path(target).resolve()
    if dst.exists() and not force:
        return {"ok": False, "error": f"'{target}' exists; use --force to overwrite"}
    tree = src / "tree.tar.gz"
    bundle = src / "history.bundle"
    if not tree.exists() or not bundle.exists():
        return {"ok": False, "error": "backup is incomplete (tree or bundle missing)"}
    # create the target
    dst.mkdir(parents=True, exist_ok=True)
    # extract tree
    with tarfile.open(tree) as tf:
        tf.extractall(path=dst, filter="data")
    # clone from bundle
    _run(["git", "clone", str(bundle), "."], cwd=dst)
    return {
        "ok": True,
        "restored_to": str(dst),
        "from_backup": str(src),
        "has_git_history": True,
    }
