"""Guards against committing credentials or runtime data again."""
import ast
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "backups", "node_modules", "quarantine", "tests", "venv", ".venv", "__pycache__", "old_output_files"}
SECRET_NAME = re.compile(r"(PASS|PASSWORD|SECRET|TOKEN|API_KEY|APIKEY)", re.I)
# a known, public default that exists only so it can be rejected
ALLOWED = {"_RETIRED_DEFAULT_PASSWORD"}


def python_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if f.endswith(".py"):
                yield Path(dirpath, f)


def test_no_credentials_assigned_in_source():
    offenders = []
    for path in python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
                continue
            if not isinstance(node.value.value, str) or len(node.value.value) < 8:
                continue
            for t in node.targets:
                name = getattr(t, "id", "") or getattr(t, "attr", "")
                if SECRET_NAME.search(name) and name not in ALLOWED:
                    offenders.append(f"{path.relative_to(ROOT)}:{node.lineno} {name}")
    assert not offenders, "credential-looking string literals: " + ", ".join(offenders)


def test_runtime_auth_data_is_not_tracked():
    try:
        tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    except (OSError, subprocess.CalledProcessError):
        return  # not a git checkout
    assert "data/auth_kv.json" not in tracked
    assert "local_kv.json" not in tracked and ".env" not in tracked


def test_env_files_are_ignored_by_git_and_docker():
    assert re.search(r"^\.env$", (ROOT / ".gitignore").read_text(), re.M)
    assert re.search(r"^data/auth_kv\.json$", (ROOT / ".gitignore").read_text(), re.M)
    assert re.search(r"^\.env$", (ROOT / ".dockerignore").read_text(), re.M)


def test_dockerfile_does_not_bake_secrets_or_run_missing_scripts():
    docker = (ROOT / "Dockerfile").read_text()
    assert "COPY .env" not in docker
    cmd = re.search(r'^CMD \[(.*)\]', docker, re.M).group(1)
    script = re.findall(r'"([^"]+\.py)"', cmd)[0]
    assert (ROOT / script).exists(), f"Dockerfile runs {script}, which does not exist"
    for src in re.findall(r"^COPY (?!\.)(\S+) ", docker, re.M):
        assert (ROOT / src).exists(), src


def test_vercelignore_excludes_backups_but_keeps_runtime_data():
    lines = {l.strip() for l in (ROOT / ".vercelignore").read_text().splitlines() if l.strip() and not l.startswith("#")}
    assert "backups/" in lines
    for needed in ("output_files/", "output_files", "pearls.json", "sent_summaries.json", "acumen_core/", "webapp/", "webapp"):
        assert needed not in lines, f".vercelignore would drop {needed}, which the portal reads"
