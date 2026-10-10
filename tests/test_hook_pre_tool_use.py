import hashlib
import json
import os
import subprocess

from keel import repo
from keel.conflict.cache import cache_key, put_cached
from keel.conflict.judge import Judgment
from keel.llm.embeddings import DeterministicEmbedder
from tests.conftest_hookserver import hook_server, hook_server_llm  # noqa: F401

HOOK = os.path.join(os.path.dirname(__file__), "..", "adapters", "claude-code",
                    "hooks", "pre_tool_use.sh")
LLM_MODEL = "anthropic/claude-sonnet-5-5"  # config default when provider=anthropic


def _run(stdin: str, env: dict, cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", HOOK], input=stdin, text=True,
                          capture_output=True, cwd=cwd, env={**os.environ, **env})


def _write_map(tmp_path, entries):
    d = tmp_path / ".keel"
    d.mkdir(parents=True, exist_ok=True)
    (d / "scopes.json").write_text(json.dumps(entries))


def _pre_json(cwd, file_path, new_string):
    return json.dumps({"session_id": "hooksess", "cwd": str(cwd),
                       "hook_event_name": "PreToolUse", "tool_name": "Edit",
                       "tool_input": {"file_path": file_path, "old_string": "x",
                                      "new_string": new_string}})


def test_no_scope_map_allows(tmp_path, hook_server):
    base_url, token = hook_server
    res = _run(_pre_json(tmp_path, "src/api/orders/p.py", "anything"),
               {"KEEL_URL": base_url, "KEEL_TOKEN": token}, str(tmp_path))
    assert res.returncode == 0 and res.stdout.strip() == ""


def test_unmatched_file_allows(tmp_path, hook_server):
    base_url, token = hook_server
    _write_map(tmp_path, [{"pattern": "src/api/orders/", "scope_tags": ["api:orders"]}])
    res = _run(_pre_json(tmp_path, "README.md", "anything"),
               {"KEEL_URL": base_url, "KEEL_TOKEN": token}, str(tmp_path))
    assert res.returncode == 0 and res.stdout.strip() == ""


async def test_mapped_scope_no_decision_allows(conn, db_pool, tmp_path, hook_server):
    base_url, token = hook_server
    pid = await repo.upsert_project(conn, "demo")
    await repo.upsert_person(conn, pid, "vasan", hashlib.sha256(b"dev-token").hexdigest())
    _write_map(tmp_path, [{"pattern": "src/api/orders/", "scope_tags": ["api:orders"]}])
    res = _run(_pre_json(tmp_path, "src/api/orders/p.py", "add pagination"),
               {"KEEL_URL": base_url, "KEEL_TOKEN": token}, str(tmp_path))
    assert res.returncode == 0 and res.stdout.strip() == ""


def test_server_down_allows(tmp_path):
    _write_map(tmp_path, [{"pattern": "src/api/orders/", "scope_tags": ["api:orders"]}])
    res = _run(_pre_json(tmp_path, "src/api/orders/p.py", "x"),
               {"KEEL_URL": "http://127.0.0.1:1/mcp", "KEEL_TOKEN": "dev-token"}, str(tmp_path))
    assert res.returncode == 0 and res.stdout.strip() == ""


async def test_conflicting_edit_is_denied(conn, db_pool, tmp_path, hook_server_llm):
    base_url, token = hook_server_llm
    pid = await repo.upsert_project(conn, "demo")
    person = await repo.upsert_person(conn, pid, "vasan", hashlib.sha256(b"dev-token").hexdigest())
    part = await repo.upsert_participant(conn, pid, person, "cc", "deep", "seed", [])
    statement = "orders API uses cursor-based pagination"
    rationale = "scales better than offset"
    emb = await DeterministicEmbedder().embed(f"{statement}\n{rationale}")
    await repo.insert_decision(conn, project_id=pid, statement=statement, rationale=rationale,
                               scope_tags=["api:orders"], owner_person_id=person,
                               source_participant_id=part, embedding=emb)
    planned = "switch the orders API to offset-based pagination instead"
    candidate_text = f"{statement}\n{rationale}"
    key = cache_key(LLM_MODEL, planned, candidate_text)
    await put_cached(conn, key, LLM_MODEL,
                     Judgment(relation="contradicts", confidence=0.9,
                              explanation="offset contradicts the active cursor pagination decision",
                              evidence="cursor-based pagination"))
    _write_map(tmp_path, [{"pattern": "src/api/orders/", "scope_tags": ["api:orders"]}])
    res = _run(_pre_json(tmp_path, "src/api/orders/pagination.py", planned),
               {"KEEL_URL": base_url, "KEEL_TOKEN": token}, str(tmp_path))
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)
    hso = out["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "deny"
    assert "cursor-based pagination" in hso["permissionDecisionReason"]
