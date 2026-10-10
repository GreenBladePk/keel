# Keel — Claude Code adapter

Wire a Claude Code project to a running Keel server. The hooks inject the team's
active decisions and pending alerts at session start and before each prompt, and
the MCP connector lets the session record decisions and check intent.

## Prerequisites
- A running Keel server (see the repo README). Its URL and a bearer token
  (one token = one person in one project).
- `curl` and `jq` on your PATH. If either is missing, the hooks silently no-op
  (fail open) — Keel never blocks your session.

## Install
1. Copy the hooks into your repo and make them executable:
   ```bash
   cp -r adapters/claude-code/hooks ~/your-repo/.claude/hooks/keel
   chmod +x ~/your-repo/.claude/hooks/keel/*.sh
   ```
2. Merge `adapters/claude-code/settings.hooks.json` into your repo's
   `.claude/settings.json` (the `hooks` block).
3. Merge `adapters/claude-code/.mcp.json` into your project's MCP config and set
   `url` to your Keel server's `/mcp` endpoint.
4. Export the environment the hooks read:
   ```bash
   export KEEL_URL=https://keel.example.com/mcp   # defaults to http://localhost:8000/mcp
   export KEEL_TOKEN=<your token>
   ```
5. (Optional) Install the skill in `SKILL.md` so Claude knows when to call the tools.

## What the hooks do
- **SessionStart** — registers this session and injects the active team decisions
  plus any pending alerts/handoffs as context.
- **UserPromptSubmit** — injects any pending alerts/handoffs before each prompt
  ("before the next action").

## PreToolUse deny-once (optional)
Create `.keel/scopes.json` in your repo (copy `adapters/claude-code/.keel/scopes.example.json`)
mapping file-path regexes to scope tags. On an `Edit`/`Write`/`MultiEdit` whose file maps to a
scope that carries active decisions, Keel checks the edit and — if it contradicts one — **denies
the tool once** with the decision as the reason, so you re-plan. It is NOT a lock and changes no
code. Most edits skip the LLM: the hook first does a cheap decision-free screen and only escalates
when the scope actually carries decisions. Skipped (edit allowed) when `.keel/scopes.json` is
absent, nothing matches, Keel is unreachable, or no LLM is configured.

## Fail-open guarantee
Every hook exits `0` on any error (server down, bad token, missing `jq`/`curl`,
malformed input). A Keel outage never blocks or interrupts your session.
