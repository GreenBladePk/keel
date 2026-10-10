#!/usr/bin/env bash
# Clean slate between demo rehearsals: truncate the demo DB + re-prime the cache.
# Leaves the server/dashboard running.  cd keel && ./demo/reset.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT"
if [ -d ../.venv ]; then . ../.venv/bin/activate; elif [ -d .venv ]; then . .venv/bin/activate; fi
python demo/seed.py
echo "reset done — ledger empty, people + cache ready."
