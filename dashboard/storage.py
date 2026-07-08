"""Atomic JSON writer, async git-push worker, edit locks, audit log.

All on-disk mutations from the dashboard flow through here. We keep:
  - a per-process edit lock (prevents concurrent saves on the same id)
  - an append-only audit log (`.console_edits.log`)
  - a single asyncio task queue for git push jobs so only one push ever runs
    at a time on this server (git is not safe to call concurrently on the
    same repo).
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Path to the repo root as seen from this package.
# dashboard/ is at <repo>/dashboard/  → repo root is parent of this file's parent.
REPO_ROOT = Path(__file__).resolve().parent.parent

AUDIT_LOG = REPO_ROOT / ".console_edits.log"

# ---------------------------------------------------------------------------
# Atomic JSON write
# ---------------------------------------------------------------------------
def write_json_atomic(path: Path, data: Any) -> None:
    """Write `data` as pretty JSON to `path` using temp-file + atomic rename.

    Survives crash mid-write: either the old file is fully intact or the
    new file is fully in place, never a half-written file on disk.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def read_json(path: Path, default: Any = None) -> Any:
    path = Path(path)
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Atomic file move across specialty folders
# ---------------------------------------------------------------------------
def move_file(src: Path, dst: Path) -> None:
    """Move a file. Creates destination parent dirs. Uses os.replace for
    atomicity when on the same filesystem, falls back to copy+unlink."""
    src = Path(src)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() == dst.resolve():
        return
    try:
        os.replace(src, dst)
    except OSError:
        # cross-device link: copy then delete
        import shutil
        shutil.copy2(src, dst)
        os.unlink(src)


# ---------------------------------------------------------------------------
# Edit locks (in-process; single-user is the design assumption)
# ---------------------------------------------------------------------------
@dataclass
class EditLockManager:
    locked: Dict[str, str] = field(default_factory=dict)  # key -> locker tag

    def acquire(self, kind: str, item_id: str, tag: str = "user") -> bool:
        k = f"{kind}:{item_id}"
        if k in self.locked:
            return self.locked[k] == tag
        self.locked[k] = tag
        return True

    def release(self, kind: str, item_id: str) -> None:
        self.locked.pop(f"{kind}:{item_id}", None)

    def is_locked(self, kind: str, item_id: str) -> bool:
        return f"{kind}:{item_id}" in self.locked


LOCKS = EditLockManager()


# ---------------------------------------------------------------------------
# Audit log — append-only, single-line JSON per event
# ---------------------------------------------------------------------------
def audit(
    kind: str,
    item_id: str,
    action: str,
    fields: Optional[Dict[str, Any]] = None,
    note: str = "",
) -> None:
    entry = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "kind": kind,
        "id": str(item_id),
        "action": action,
        "fields": list(fields.keys()) if fields else [],
        "note": note,
    }
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def audit_tail(n: int = 200) -> List[Dict[str, Any]]:
    if not AUDIT_LOG.exists():
        return []
    with open(AUDIT_LOG, "r", encoding="utf-8") as f:
        lines = f.readlines()[-n:]
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return list(reversed(out))


# ---------------------------------------------------------------------------
# Per-process git push worker — singleton, only one push at a time
# ---------------------------------------------------------------------------
@dataclass
class PushJob:
    job_id: str
    kind: str
    ids: List[str]
    paths: List[str]
    status: str = "pending"      # pending | running | done | failed
    message: str = ""
    commit_sha: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "kind": self.kind,
            "ids": self.ids,
            "status": self.status,
            "message": self.message,
            "commit_sha": self.commit_sha,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


class PushWorker:
    """Single-flight git push queue.

    submit() schedules a coroutine that does, in order:
      1. git add <paths>      (only files touched by this edit)
      2. git commit -m "..."
      3. git push origin HEAD
    The returned job_id can be polled via status().
    """

    def __init__(self) -> None:
        self.jobs: Dict[str, PushJob] = {}
        self._queue: asyncio.Queue = None  # created lazily on first submit
        self._runner: Optional[asyncio.Task] = None

    def _ensure(self) -> None:
        if self._queue is None:
            self._queue = asyncio.Queue()
        if self._runner is None or self._runner.done():
            self._runner = asyncio.create_task(self._run())

    def submit(self, kind: str, ids: List[str], paths: List[str], message: str = "") -> str:
        self._ensure()
        job_id = uuid.uuid4().hex[:12]
        job = PushJob(job_id=job_id, kind=kind, ids=ids, paths=list(dict.fromkeys(paths)))
        self.jobs[job_id] = job
        msg = message or f"console({kind}): edit {', '.join(ids)}"
        self._queue.put_nowait((job, msg))
        return job_id

    def status(self, job_id: str) -> Optional[Dict[str, Any]]:
        j = self.jobs.get(job_id)
        return j.to_dict() if j else None

    async def _run(self) -> None:
        while True:
            job, msg = await self._queue.get()
            job.status = "running"
            job.started_at = time.time()
            try:
                sha, err = await self._git_push(job.paths, msg)
                if err:
                    job.status = "failed"
                    job.message = err
                else:
                    job.status = "done"
                    job.message = "pushed"
                    job.commit_sha = sha
            except Exception as e:
                job.status = "failed"
                job.message = f"{type(e).__name__}: {e}"
            job.finished_at = time.time()
            self._queue.task_done()
            # don't keep old jobs in memory forever
            while len(self.jobs) > 50:
                oldest = next(iter(self.jobs))
                self.jobs.pop(oldest, None)

    async def _git_push(self, paths: List[str], message: str) -> Tuple[str, str]:
        """Returns (commit_sha, error_or_empty). Synchronous git wrapped in to_thread."""
        return await asyncio.to_thread(self._git_push_sync, paths, message)

    def _git_push_sync(self, paths: List[str], message: str) -> Tuple[str, str]:
        import subprocess

        if not paths:
            return "", "no paths to push"

        repo = str(REPO_ROOT)

        def run(args: List[str]) -> Tuple[int, str]:
            p = subprocess.run(
                args,
                cwd=repo,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            return p.returncode, (p.stdout + p.stderr).strip()

        # 1. add
        add_args = ["git", "add", "--"] + paths
        rc, out = run(add_args)
        if rc != 0:
            return "", f"git add failed: {out}"

        # 2. commit (allow empty? no — empty commit means no diff, fine to skip)
        rc, out = run(["git", "commit", "-m", message, "--no-verify"])
        if rc != 0 and "nothing to commit" not in out and "no changes" not in out:
            return "", f"git commit failed: {out}"

        # fetch SHA (whether or not we just committed, HEAD is the right answer)
        rc, sha = run(["git", "rev-parse", "HEAD"])
        if rc != 0:
            return "", f"git rev-parse failed: {sha}"
        sha = sha.strip()

        # 3. push
        rc, out = run(["git", "push", "origin", "HEAD"])
        if rc != 0:
            # if push fails, the commit is still local; report but say done-with-warn
            return sha, f"git push failed (commit {sha[:8]} is local only): {out}"

        return sha, ""


PUSH = PushWorker()
