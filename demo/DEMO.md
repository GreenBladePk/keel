# Keel — Live Demo Runbook

**Story (3–4 min):** Two engineers + their Claude agents build the **Orders API**.
Alice sets the pagination contract; Bob's agent, unaware, tries the opposite. Keel
catches the contradiction *with evidence* and blocks the bad edit *before it lands* —
shared memory for multiplayer AI.

- **Alice** — owns the orders API. Token `alice-token`.
- **Bob** — building against it in a second terminal. Token `bob-token`.
- Dashboard on the projector. Real LLM (RouterPlus / gpt-4.1-mini).

---

## One-time setup (before the stage)

```bash
cd keel
cp demo/env.sample demo/env.local          # then edit: paste your RouterPlus key into OPENAI_API_KEY
./demo/setup.sh                             # seeds demo DB, primes cache, starts server :8000 + dashboard :8050
```

**Pre-approve the MCP connector** (so no permission prompt mid-demo) — in each terminal once:
```bash
cd demo/workspace && source ../env.local && export KEEL_TOKEN=$ALICE_TOKEN
claude                                       # run once; when it asks, approve the 'keel' MCP server; /exit
```
(Repeat with `KEEL_TOKEN=$BOB_TOKEN` in Bob's terminal.) Alternatively launch with
`claude --allowedTools "mcp__keel__*"` to skip the prompt.

**Open the dashboard** `http://localhost:8050`, enter Keel URL `http://localhost:8000`,
token `alice-token`, click **Connect**, tick **auto**. Leave it on the projector.

**Two terminals, in `demo/workspace/`:**
```bash
# Terminal A — Alice
cd keel/demo/workspace && source ../env.local && export KEEL_TOKEN=$ALICE_TOKEN && claude
# Terminal B — Bob
cd keel/demo/workspace && source ../env.local && export KEEL_TOKEN=$BOB_TOKEN   && claude
```

> Between rehearsals: `./demo/reset.sh` (clears the ledger, keeps people + primed cache), then refresh the dashboard.

---

## The demo (4 beats)

### Beat 1 — Context + the decision  *(Alice)*  ~45s
Alice's session already got the team's active decisions injected at start (empty on a
fresh run — point that out: "Keel injects our shared decisions at session start").

**Say:** "We're standardizing orders pagination on cursors. Alice records that."
**Alice types:**
> Record a team decision: the orders API uses cursor-based pagination, because cursors scale better than offset for large tables. Scope it to `api:orders`.

Her agent calls `record_decision` via the `keel` connector.
**Audience sees (dashboard):** a new row under **Active decisions** + an entry in the **Event timeline**.

### Beat 2 — Contradiction caught, with evidence  *(Bob)*  ~60s
**Say:** "Bob didn't see that. His agent decides on offset pagination and records it."
**Bob types:**
> Record a decision: switch the orders API to offset-based pagination with page numbers, because it's simpler for clients. Scope `api:orders`.

His agent calls `record_decision` → Keel records it **and returns a conflict** with the
real-LLM **explanation + a verbatim quote** of Alice's decision (it warns, it doesn't
block — humans resolve). The conflict is persisted.
**Audience sees:** Bob's terminal prints the conflict; the dashboard's **Open conflicts**
panel lights up with the explanation.

> Prefer the non-persisting "ask first" variant? Have Bob say *"check this against our
> team decisions for api:orders"* → the agent calls `check_intent` (same conflict, but it
> records nothing, so the dashboard's Open-conflicts panel stays empty).

### Beat 3 — Deny-once: blocked before the edit  *(Bob)*  ~60s
**Say:** "Watch what happens when he tries to write it anyway."
**Bob types:**
> Edit src/api/orders/pagination.py to implement offset pagination with page and page_size.

The **PreToolUse hook** screens the edit (file → `api:orders`), finds the active cursor
decision, and **denies the edit** with the decision as the reason — the tool call is
blocked. Claude reports it can't make the edit and explains why.
**Audience sees:** Claude's edit is refused "before the next action," citing Alice's decision.

### Beat 4 — The trail  *(Dashboard)*  ~30s
Pan to the dashboard: **decision → conflict → event timeline**, the whole multiplayer
loop, captured append-only. **Close:** "Every agent and teammate now shares one source of
truth — contradictions caught with evidence, before they cost a rewrite."

---

## Scripted fallback (if a live agent wanders)

A tiny helper — paste once per terminal:
```bash
keel () { curl -s -X POST "$KEEL_URL" \
  -H "Authorization: Bearer $KEEL_TOKEN" -H "X-Keel-Session: $1" \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"$2\",\"arguments\":$3}}" \
  | python3 -c "import sys,json;print(json.loads(json.load(sys.stdin)['result']['content'][0]['text']))"; }
```

- **Beat 1 (Alice):**
  `KEEL_TOKEN=alice-token; keel alice register_session '{"harness":"cli","tier":"deep","session_id":"alice"}'`
  `keel alice record_decision '{"statement":"The orders API uses cursor-based pagination","rationale":"cursors scale better than offset for large tables","scope_tags":["api:orders"]}'`
- **Beat 2 (Bob):**
  `KEEL_TOKEN=bob-token; keel bob register_session '{"harness":"cli","tier":"deep","session_id":"bob"}'`
  `keel bob record_decision '{"statement":"Switch the orders API to offset-based pagination with page numbers","rationale":"simpler for clients","scope_tags":["api:orders"]}'`  → persisted + conflict with evidence (dashboard lights up).
  (Non-persisting variant: `keel bob check_intent '{"planned_action":"Switch the orders API to offset-based pagination with page numbers","scope_tags":["api:orders"]}'`.)
- **Beat 3 (Bob):** run the PreToolUse hook directly on a sample edit:
  `echo '{"session_id":"bob","cwd":"'"$PWD"'","tool_name":"Edit","tool_input":{"file_path":"src/api/orders/pagination.py","new_string":"switch the orders API to offset pagination with page and page_size"}}' | KEEL_TOKEN=bob-token .claude/hooks/keel/pre_tool_use.sh`
  → prints the `permissionDecision:"deny"` JSON with the reason.

---

## Troubleshooting
- **Dashboard empty / 401:** check token in the field; server up? `curl -s -o /dev/null -w '%{http_code}' -X POST localhost:8000/mcp -d '{}'` → `401` is healthy.
- **No conflict detected:** confirm `OPENAI_API_KEY` (RouterPlus) is set in `env.local` and the server was started after sourcing it; `demo/server.log` shows errors. The primed cache covers the canonical phrasings regardless.
- **Edit not blocked:** the file must match `.keel/scopes.json` (`src/api/orders/…`) and an active decision must exist on `api:orders` (do Beat 1 first). Hooks fail **open** — if Keel is down, edits are allowed (never blocked), so keep the server up.
- **MCP tool not called:** approve the `keel` server once, or launch `claude --allowedTools "mcp__keel__*"`.
- **Reset mid-show:** `./demo/reset.sh` + refresh dashboard.

## What each beat proves
1. Shared context injected into every agent session (hooks) + decisions recorded over MCP.
2. Semantic contradiction detection with calibrated evidence (real LLM, not keywords).
3. Prevention — "before the next action" deny-once in a real Claude Code session.
4. Append-only, auditable multiplayer trail, live.
