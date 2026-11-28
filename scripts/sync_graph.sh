#!/usr/bin/env bash
# Keep the graphify code map (graphify-out/) in sync with the code.
# Idempotent + non-fatal: safe to run at every session start / by hand.
#   bash scripts/sync_graph.sh          -> install tool if missing, install git hooks, update graph
#   bash scripts/sync_graph.sh --quiet  -> same, minimal output
cd "$(dirname "$0")/.." || exit 0
Q=0; [ "${1:-}" = "--quiet" ] && Q=1
say() { [ "$Q" = 1 ] || echo "[sync_graph] $*"; }

if ! command -v graphify >/dev/null 2>&1; then
  say "installing graphifyy (pip)…"
  pip install -q graphifyy >/dev/null 2>&1 || { say "pip install failed; skipping"; exit 0; }
fi

# Git hooks (post-commit/checkout/merge/rewrite) + graph.json union-merge driver.
# .git/hooks is not versioned, so every fresh clone/container re-installs here.
graphify hook install >/dev/null 2>&1 && say "git hooks ready"

# Rebuild code graph from AST (no LLM, ~5s). Never block the session on failure.
graphify update . >/dev/null 2>&1 && say "graph updated @ $(git rev-parse --short HEAD 2>/dev/null)" || say "graph update failed (non-fatal)"
exit 0
