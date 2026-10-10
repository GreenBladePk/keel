import hashlib
import json
import os
import subprocess

from keel import repo
from tests.conftest_hookserver import hook_server  # noqa: F401

HOOK = os.path.join(os.path.dirname(__file__), "..", "adapters", "claude-code",
                    "hooks", "post_tool_use.sh")


def _run(stdin, env, cwd):
    return subprocess.run(["bash", HOOK], input=stdin, text=True, capture_output=True,
                          cwd=cwd, env={**os.environ, **env})


def _write_map(tmp_path, entries):
    d = tmp_path / ".keel"
    d.mkdir(parents=True, exist_ok=True)
    (d / "scopes.json").write_text(json.dumps(entries))


def _post_json(cwd, fp, new):
    return json.dumps({"session_id": "hooksess", "cwd": str(cwd),
                       "hook_event_name": "PostToolUse", "tool_name": "Edit",
                       "tool_input": {"file_path": fp, "new_string": new}})


def test_no_map_allows_silent(tmp_path, hook_server):
    base_url, token = hook_server
    res = _run(_post_json(tmp_path, "src/api/orders/p.py", "x"),
               {"KEEL_URL": base_url, "KEEL_TOKEN": token}, str(tmp_path))
    assert res.returncode == 0 and res.stdout.strip() == ""


async def test_mapped_scope_with_decision_injects_context(conn, db_pool, tmp_path, hook_server):
    base_url, token = hook_server
    pid = await repo.upsert_project(conn, "demo")
    person = await repo.upsert_person(conn, pid, "vasan", hashlib.sha256(b"dev-token").hexdigest())
    part = await repo.upsert_participant(conn, pid, person, "cc", "deep", "hooksess", [])
    await repo.insert_decision(conn, project_id=pid, statement="orders use cursor pagination",
                               rationale="r", scope_tags=["api:orders"], owner_person_id=person,
                               source_participant_id=part)
    _write_map(tmp_path, [{"pattern": "src/api/orders/", "scope_tags": ["api:orders"]}])
    res = _run(_post_json(tmp_path, "src/api/orders/p.py", "touch pagination"),
               {"KEEL_URL": base_url, "KEEL_TOKEN": token}, str(tmp_path))
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)
    hso = out["hookSpecificOutput"]
    assert hso["hookEventName"] == "PostToolUse" and "Keel" in hso["additionalContext"]


async def test_mapped_scope_no_decision_silent(conn, db_pool, tmp_path, hook_server):
    base_url, token = hook_server
    pid = await repo.upsert_project(conn, "demo")
    person = await repo.upsert_person(conn, pid, "vasan", hashlib.sha256(b"dev-token").hexdigest())
    await repo.upsert_participant(conn, pid, person, "cc", "deep", "hooksess", [])
    _write_map(tmp_path, [{"pattern": "src/api/orders/", "scope_tags": ["api:orders"]}])
    res = _run(_post_json(tmp_path, "src/api/orders/p.py", "x"),
               {"KEEL_URL": base_url, "KEEL_TOKEN": token}, str(tmp_path))
    assert res.returncode == 0 and res.stdout.strip() == ""


def test_server_down_silent(tmp_path):
    _write_map(tmp_path, [{"pattern": "src/api/orders/", "scope_tags": ["api:orders"]}])
    res = _run(_post_json(tmp_path, "src/api/orders/p.py", "x"),
               {"KEEL_URL": "http://127.0.0.1:1/mcp", "KEEL_TOKEN": "dev-token"}, str(tmp_path))
    assert res.returncode == 0 and res.stdout.strip() == ""
