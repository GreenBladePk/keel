# Keel — Open-Source Backlog (issue-ready)

## Context
The hackathon build is done: a vendor-neutral intent/decision ledger over MCP —
17 tools, LLM conflict engine (RouterPlus-validated, f1 0.89), propagation/alerts,
handoff, Claude Code hook adapter (SessionStart/UserPromptSubmit/PreToolUse deny-once/
PostToolUse drift), read-only dashboard, and a live demo. Suite: 173 passed, 2 skipped.
This backlog is the end-to-end task list for the open-source phase. Each item is
written to drop straight into a GitHub issue: **type · priority · effort · labels**,
context, acceptance criteria, touch points, and approach.

**Deliverable on approval:** save this as `keel/BACKLOG.md` (tracked, repo root) so each
item can become an issue. Labels use: `bug` `enhancement` `feature` `ops` `docs` `security`
`good-first-issue` `P0/P1/P2`.

Legend — Effort: S (<0.5d) · M (0.5–2d) · L (>2d).

---

## BUGS (open — most prior review minors already fixed)

### B1 · Make the drift self-alert dedupe atomic
type: bug · P2 · S · labels: bug
- **Context:** `report_activity` dedupes the self change-alert with a check-then-insert (`repo.unacked_change_alert_exists` + `insert_alert`) with no backing constraint. Two concurrent same-(participant,ref_id) calls could both insert. Harmless single-session; real under concurrency.
- **Acceptance:** concurrent duplicate reports yield exactly one unacked change-alert; existing dedupe tests still pass.
- **Touch points:** `keel/db/schema.sql` (partial unique index `alert(target_participant_id, ref_id) WHERE kind='change' AND acknowledged_at IS NULL`), `keel/keel/repo.py` `insert_alert` (ON CONFLICT DO NOTHING path / RETURNING-safe), `keel/keel/tools/report_activity.py`.
- **Approach:** add the partial index; keep the explicit check for the fast path; handle `insert_alert` returning no row on conflict.

### B2 · `create_handoff` silently ignores an unknown `to_session`
type: bug · P2 · S · labels: bug
- **Context:** a non-existent `to_session` is dropped to `None` without feedback; delivery falls back to person-level. Can mask a typo.
- **Acceptance:** an unknown `to_session` either errors clearly or is surfaced in the response (chosen in the issue); valid flows unchanged.
- **Touch points:** `keel/keel/tools/handoff.py` (create_handoff), tests `tests/test_handoff_tools.py`.

### B3 · Inconsistent session enforcement across tools
type: bug · P2 · S · labels: bug
- **Context:** reads (`get_context`, `/api/*`) work with no/placeholder `X-Keel-Session`; writes (`accept_handoff`, `ack_alert`) require a registered participant. Decide one contract and document.
- **Acceptance:** documented, consistent behavior; `_clean_session` + per-tool requirements aligned; tests assert it.
- **Touch points:** `keel/keel/server.py` (`AuthMiddleware`, `_clean_session`), tool handlers, `adapters/claude-code/README.md`.

### B4 · `keel_call` multiline-response parsing edge
type: bug · P3 · S · labels: bug `good-first-issue`
- **Context:** the hook helper splits the curl body/code on the last newline; a multiline body would mis-split. Server returns single-line JSON today, so latent.
- **Acceptance:** parsing robust to multiline bodies; hook tests cover it.
- **Touch points:** `adapters/claude-code/hooks/_keel_call.sh`.

### B5 · Close test-coverage gaps
type: bug · P2 · S · labels: test `good-first-issue`
- **Context:** missing: `user_prompt_submit` no-session-id, `isError:true` tool-response row path, malformed-stdin for hooks, and a browser DOM test for the dashboard (no Playwright in CI yet).
- **Acceptance:** each path has a test; dashboard gets a headless-browser smoke (Playwright) in CI.
- **Touch points:** `tests/test_hook_*`, new `tests/test_dashboard_ui.py` (Playwright, gated).

---

## ENHANCEMENTS

### E1 · Model-complexity router (`select_model`)
type: enhancement · P1 · M · labels: enhancement
- **Context:** `keel/keel/conflict/judge.py:30` `select_model` is a seam returning one model. Route cheap vs strong models by task complexity (RouterPlus gives multi-model).
- **Acceptance:** a classifier chooses a model per (subject, candidate); cache key includes the chosen model; eval floor holds; configurable.
- **Touch points:** `judge.py` (`select_model`, cache-key coupling), `config.py`, `conflict/cache.py`, eval runner.

### E2 · Real embeddings provider for retrieval
type: enhancement · P1 · M · labels: enhancement
- **Context:** embeddings default to `DeterministicEmbedder` (not semantic); retrieval leans on FTS. Wire a real provider (OpenAI/RouterPlus) for semantic recall.
- **Acceptance:** `KEEL_EMBEDDING_PROVIDER` can select a live model; retrieval recall improves on the eval set; deterministic stays the offline default.
- **Touch points:** `keel/keel/llm/embeddings.py` (`ProviderEmbedder`), `config.py`, eval.

### E3 · Fuzzy scope-tag normalization
type: enhancement · P1 · M · labels: enhancement
- **Context:** `keel/keel/scope.py:36` `reconcile` has a seam for edit-distance matching; today it's identity. Scope-tag mismatch is the documented single point of failure.
- **Acceptance:** near-duplicate tags (`api:order` vs `api:orders`) reconcile to the canonical existing tag; threshold configurable; no false merges in tests.
- **Touch points:** `scope.py` (`reconcile`), tests.

### E4 · Alert fan-out cap / batching
type: enhancement · P2 · M · labels: enhancement
- **Context:** a decision on a broad scope with many claimers creates unbounded alerts (spec §8 risk).
- **Acceptance:** per-decision fan-out is bounded/batched (configurable); event still records the batch.
- **Touch points:** `keel/keel/propagation.py`, `config.py`.

### E5 · Event cursor pagination
type: enhancement · P2 · S · labels: enhancement
- **Context:** `/api/events` caps at 500, no cursor; dashboard can't page.
- **Acceptance:** `before_id`/cursor param; dashboard "load more".
- **Touch points:** `keel/keel/server.py` (`api_events`), `keel/keel/repo.py` (`list_events`), `dashboard/app.js`.

### E6 · Judgment cache TTL / invalidation
type: enhancement · P2 · S · labels: enhancement
- **Context:** `judgment_cache` never expires; a model/prompt change leaves stale verdicts.
- **Acceptance:** TTL and/or model+prompt-version key; configurable; stale entries ignored.
- **Touch points:** `keel/keel/conflict/cache.py`, schema.

### E7 · Enforce `allowed_scopes` / `allowed_categories`
type: enhancement · P1 · M · labels: enhancement security
- **Context:** stored on `participant` (`register_session`) but never enforced. Authorize tool actions against a participant's allowed scopes.
- **Acceptance:** a participant acting outside allowed_scopes is rejected (configurable, default permissive); tested.
- **Touch points:** tool handlers (`record_decision`, `claim_scope`, `check_intent`, …), `repo.py`.

### E8 · Observability (logs, request ids, metrics)
type: enhancement · P1 · M · labels: enhancement ops
- **Context:** minimal logging; no request correlation or metrics (conflict rate, degraded rate, latency).
- **Acceptance:** structured logs with a request/session id; counters/timers exposed (e.g. `/metrics` or logs); degraded-detection events auditable.
- **Touch points:** `keel/keel/server.py` (middleware), `conflict/pipeline.py`, `record_decision.py`.

### E9 · Versioned DB migrations
type: enhancement · P1 · M · labels: enhancement ops
- **Context:** schema evolves via `CREATE TABLE IF NOT EXISTS` + ad-hoc `ALTER … IF NOT EXISTS`. Fine now, fragile long-term.
- **Acceptance:** a migration tool (alembic/sqitch) with ordered migrations; `ensure_schema` replaced/augmented; CI runs migrations.
- **Touch points:** `keel/keel/db/` (new migrations dir), `pool.py`, docs.

### E10 · CI pipeline (GitHub Actions)
type: enhancement · P0 · M · labels: ops
- **Context:** no CI. OSS needs PR gating.
- **Acceptance:** Actions workflow: spin Postgres service, run `pytest`, lint (ruff), on PR+push; gated live-LLM job (nightly, keyed secret); secret scan.
- **Touch points:** `.github/workflows/ci.yml`, `pyproject.toml` (ruff), `tests/conftest.py`.

### E11 · Dashboard write-actions + detail
type: enhancement · P2 · M · labels: enhancement
- **Context:** dashboard is read-only. Add ack-alert / resolve-conflict from the UI, conflict drill-down, scope filters.
- **Acceptance:** actions call the tools with the entered token; read-only stays the default; separate write scope optional (see F10).
- **Touch points:** `dashboard/app.js`, `dashboard/index.html`, maybe new REST or reuse MCP.

### E12 · Deploy profiles (prod compose + GCP)
type: enhancement · P1 · L · labels: ops
- **Context:** dev docker-compose only. OPEN_QUESTIONS Q9 chose GCP hosting.
- **Acceptance:** prod `docker-compose` (or Cloud Run + Cloud SQL) manifests, env-driven config, healthcheck, TLS notes; documented deploy.
- **Touch points:** `docker-compose*.yml`, `Dockerfile`, deploy docs, `config.py`.

---

## FEATURES

### F1 · Lessons (`decision.kind='lesson'`)
type: feature · P1 · M · labels: feature
- **Context:** schema + checks already treat a lesson as a decision with an expiry; `inbox.new_lessons` is always `[]`. Deliver lessons.
- **Acceptance:** record a lesson (kind=lesson, expires_at); active, non-expired lessons surface in `get_context` + `inbox.new_lessons` + hook injection; same contradiction checks apply.
- **Touch points:** `record_decision` (kind/expiry), `get_context`, `inbox.py`, hooks, tests.

### F2 · decision_request lifecycle (deliver + answer/expire)
type: feature · P1 · M · labels: feature
- **Context:** only creation exists (`request_decision`). No owner delivery, no answer/decline/expire.
- **Acceptance:** open requests surface to the owner (inbox key or tool); `answer_decision_request` links an `answer_decision_id` and closes it; expiry supported.
- **Touch points:** `keel/keel/tools/decision_request.py`, `inbox.py`, `repo.py`, `server.py`, tests.

### F3 · Inferred outcomes (drift/CI → outcome)
type: feature · P2 · M · labels: feature
- **Context:** `outcome.source` supports `inferred` but only `manual` is produced.
- **Acceptance:** a signal (PostToolUse drift, CI result) can create an `inferred` outcome; feeds drift/eval.
- **Touch points:** `report_activity`/new tool, `repo.insert_outcome`, docs.

### F4 · Handoff: `list_handoffs` + re-handoff policy
type: feature · P2 · M · labels: feature
- **Context:** no way to list sent/received handoffs; re-handoff behavior undefined.
- **Acceptance:** `list_handoffs(status?)` (sent+received); re-handoff of an accepted scope defined + tested.
- **Touch points:** `keel/keel/tools/handoff.py`, `repo.py`, `server.py`.

### F5 · Stop / SessionEnd hook
type: feature · P2 · S · labels: feature
- **Context:** no end-of-session capture. A Stop/SessionEnd hook could flush a session summary or auto-release claims.
- **Acceptance:** hook script + settings entry; releases the session's claims and/or records a summary; fail-open.
- **Touch points:** `adapters/claude-code/hooks/`, `settings.hooks.json`, a tool if needed.

### F6 · Real multi-harness adapters (Codex, generic MCP)
type: feature · P1 · M · labels: feature
- **Context:** shipped a harness-agnostic SKILL/AGENTS; build tested adapters for Codex + a generic MCP client beyond Claude Code.
- **Acceptance:** a Codex adapter (AGENTS + any hook equivalent) and a generic-MCP quickstart, each e2e-verified.
- **Touch points:** `adapters/` (new dirs), docs.

### F7 · Slack integration
type: feature · P2 · L · labels: feature
- **Context:** light-tier delivery to Slack for alerts/handoffs/requests (ARCHITECTURE names Slack as a channel).
- **Acceptance:** opt-in Slack app posts alerts/handoffs to a channel/DM; links back; configurable.
- **Touch points:** new `keel/keel/integrations/slack.py`, config, docs.

### F8 · Artifact-level dependency refs (remediation)
type: feature · P2 · M · labels: feature
- **Context:** §8.2 — `change` alerts should say "re-check these files"; needs artifact-level dependency refs (`dependency.dependent_type='artifact'` exists in schema, unused).
- **Acceptance:** declare artifact deps; change alerts carry affected file refs; surfaced in inbox/PostToolUse.
- **Touch points:** `declare_dependency` (artifact type), `propagation.py`, `inbox.py`.

### F9 · Eval growth + feedback-driven tuning
type: feature · P1 · M · labels: feature
- **Context:** `alert_feedback` (useful/noise) and the eval dataset exist but aren't looped back.
- **Acceptance:** grow the eval dataset; a report from `alert_feedback`; CI eval-floor gate; threshold/model tuning guided by it.
- **Touch points:** `keel/keel/evals/`, `rate_alert` consumers, CI.

### F10 · Separate read-only dashboard token
type: feature · P2 · S · labels: feature security
- **Context:** the dashboard reuses a full person token. A read-only token would be safer for sharing a view.
- **Acceptance:** mint/scope a read-only token; `/api/*` accepts it, tools reject it.
- **Touch points:** auth (`server.py`), `repo.py`, docs.

### F11 · Web light-tier connector session identity
type: feature · P2 · M · labels: feature
- **Context:** Claude Code doesn't auto-populate `${CLAUDE_SESSION_ID}` into MCP headers (fixed to fail safe). Provide a real per-session path for connector tool-calls.
- **Acceptance:** connector calls carry a stable per-session id without manual env; documented for other harnesses.
- **Touch points:** adapter, `server.py` session handling, docs.

---

## OSS / OPS / DOCS

### O1 · OSS hygiene files
type: docs · P0 · S · labels: docs `good-first-issue`
- **Acceptance:** LICENSE (choose: Apache-2.0/MIT), CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, `.github/ISSUE_TEMPLATE/*`, PR template.
- **Touch points:** repo root, `.github/`.

### O2 · Product README + architecture in-repo
type: docs · P0 · M · labels: docs
- **Context:** `context/` (PRD/ARCHITECTURE/etc.) is git-ignored; repo lacks a product-facing README.
- **Acceptance:** top-level README (what/why/quickstart/demo); architecture doc committed (curated from `context/`); tool reference.
- **Touch points:** `README.md`, `docs/` (un-ignore curated subset or copy).

### O3 · Finalize the name (Keel is a placeholder)
type: ops · P1 · S · labels: ops
- **Context:** OPEN_QUESTIONS #1 — name not settled; avoid hardening into package/domain prematurely.
- **Acceptance:** decision recorded; package/repo/domain aligned if renamed.
- **Touch points:** pyproject, imports, docs.

### O4 · Secret hygiene
type: security · P0 · S · labels: security ops
- **Context:** RouterPlus key was pasted in chat/shell + lives in git-ignored `demo/env.local`.
- **Acceptance:** key rotated; gitleaks/secret-scan in CI; `.env*`/`env.local` ignored (done); docs warn.
- **Touch points:** CI, docs.

### O5 · Prompt-injection hardening (parked)
type: security · P1 · M · labels: security
- **Context:** parked from Slice 2: evidence min-length, prompt-delimiter escaping, "decisions-are-data" audit for injected ledger text.
- **Acceptance:** evidence min-length enforced; injected text escaped/delimited; adversarial tests (decision text containing instructions is not followed).
- **Touch points:** `conflict/judge.py` (`_SYSTEM`, evidence gate), `pipeline.py`, hooks (additionalContext framing), tests.

### O6 · Config reference
type: docs · P1 · S · labels: docs
- **Acceptance:** every `KEEL_*` / `DATABASE_URL` / provider env documented (default, effect) in one place.
- **Touch points:** README/docs, cross-check `keel/keel/config.py`.

### O7 · Versioning + release
type: ops · P1 · M · labels: ops
- **Acceptance:** semver + CHANGELOG; tagged releases; publish (container image; PyPI optional); `contract`/schema versioning noted.
- **Touch points:** repo, CI release workflow.

### O8 · GitHub repo setup + push `master`
type: ops · P0 · S · labels: ops
- **Context:** ~32 commits unpushed; `master` not yet on origin.
- **Acceptance:** `master` pushed; branch protection; default branch set; CI required on PR.
- **Touch points:** GitHub settings (user action), `git push -u origin master`.

---

## Suggested first wave (if sequencing)
1. **O8, O4, O1, O2** (push + secure + make it a real OSS repo).
2. **E10** (CI) → gates everything after.
3. **F1 (lessons), E2 (real embeddings), E1 (router), E3 (fuzzy scope)** — core product depth.
4. **E7, O5** (authz + injection hardening) before any public deployment (**E12**).

## Verification (for each issue when implemented)
- TDD per item; `KEEL_TEST_DATABASE_URL=… pytest -q` stays green.
- Engine/tool changes: exercise via MCP (`curl` one stateless `tools/call`) + the dashboard.
- LLM-touching changes: run the gated live tests with a provider key (RouterPlus) and keep the eval floor (f1 ≥ 0.7).
