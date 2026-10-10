#!/usr/bin/env bash
# One-time stage setup for the Keel live demo.
#   cd keel && ./demo/setup.sh
# Requires: demo/env.local (copy from env.sample, add the RouterPlus key), Postgres on :5433.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"      # keel/ repo root
cd "$ROOT"

[ -f "$HERE/env.local" ] || { echo "ERROR: $HERE/env.local missing. cp demo/env.sample demo/env.local and add the key."; exit 1; }
# shellcheck disable=SC1090
source "$HERE/env.local"
[ -d .venv ] || [ -d ../.venv ] || echo "note: no .venv found; ensure deps (incl litellm/instructor) are installed"
# activate venv (repo may keep it at ../.venv)
if [ -d ../.venv ]; then . ../.venv/bin/activate; elif [ -d .venv ]; then . .venv/bin/activate; fi

echo "== 1. Postgres reachable? =="
pg_isready -h localhost -p 5433 >/dev/null 2>&1 && echo "  ok" || { echo "  ERROR: start Postgres (docker compose up -d)"; exit 1; }

echo "== 2. Seed demo DB + prime cache =="
python demo/seed.py

echo "== 3. Refresh the demo workspace hooks from the adapter =="
mkdir -p demo/workspace/.claude/hooks/keel
cp adapters/claude-code/hooks/*.sh demo/workspace/.claude/hooks/keel/
chmod +x demo/workspace/.claude/hooks/keel/*.sh
echo "  hooks copied"

echo "== 4. Start Keel server (:8000, demo DB, RouterPlus) =="
pkill -f "keel.server" 2>/dev/null || true
sleep 1
nohup python -m keel.server > "$HERE/server.log" 2>&1 &
for _ in $(seq 1 40); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 1 -X POST http://localhost:8000/mcp -d '{}' 2>/dev/null || true)
  [ "$code" = "401" ] && break; sleep 0.25
done
echo "  server up (401 w/o auth = healthy): $(curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8000/mcp -d '{}')"

echo "== 5. Start dashboard (:8050) =="
pkill -9 -f "dashboard/serve.py" 2>/dev/null || true
sleep 2   # let the old socket leave TIME_WAIT
PORT=8050 nohup python dashboard/serve.py > "$HERE/dashboard.log" 2>&1 &
for _ in $(seq 1 20); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 1 http://localhost:8050/ 2>/dev/null)" = "200" ] && break
  sleep 0.5
done
echo "  dashboard: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8050/)"

cat <<EOF

================  READY  ================
Dashboard (projector):  http://localhost:8050    token: alice-token  (or bob-token)
Keel server:            http://localhost:8000/mcp
Open TWO terminals in demo/workspace:
  Terminal A (Alice):  cd $ROOT/demo/workspace && source ../env.local && export KEEL_TOKEN=\$ALICE_TOKEN && claude
  Terminal B (Bob):    cd $ROOT/demo/workspace && source ../env.local && export KEEL_TOKEN=\$BOB_TOKEN   && claude
First run only: approve the 'keel' MCP server when prompted (or pre-approve, see DEMO.md).
Between rehearsals:  ./demo/reset.sh
Follow:  demo/DEMO.md
=========================================
EOF
