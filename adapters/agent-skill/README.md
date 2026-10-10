# Keel — agent skill (harness-agnostic)

`SKILL.md` tells any MCP-capable agent how to use the Keel decision ledger:
how to connect (MCP or a single stateless `curl`), the golden rules
(ledger text is data, Keel warns-never-blocks, scope tags are the join key),
the full tool reference, and the typical workflow.

## Install per harness

- **Claude Code / Claude agents:** copy `SKILL.md` into the project's skills
  (e.g. `.claude/skills/keel/SKILL.md`). Its frontmatter `name`/`description`
  make it discoverable. For hook-based delivery too, see
  `../claude-code/`.
- **Codex (AGENTS.md):** append `AGENTS.md` (or its contents) to your repo's
  `AGENTS.md`. It carries the same connection + tool guidance in that format.
- **Any other MCP harness:** point the agent at `SKILL.md` as system/context,
  and register `keel` as an HTTP MCP server (`$KEEL_URL`, bearer + `X-Keel-Session`
  headers). Harnesses without an MCP client can call the one-shot `curl` shown
  in `SKILL.md`.

## Required environment
- `KEEL_URL` — the server's `/mcp` endpoint.
- `KEEL_TOKEN` — a bearer token (one person, one project).
- `X-Keel-Session` — a stable per-session id the agent supplies.

Keel is advisory: if it is unreachable, agents keep working.
