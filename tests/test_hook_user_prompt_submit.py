import hashlib
import os
import subprocess

from keel import repo
from tests.conftest_hookserver import hook_server  # noqa: F401

HOOK = os.path.join(os.path.dirname(__file__), "..", "adapters", "claude-code",
                    "hooks", "user_prompt_submit.sh")


def _run(stdin: str, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", HOOK], input=stdin, text=True,
                          capture_output=True, env={**os.environ, **env})


async def test_prompt_hook_injects_pending_alert(conn, db_pool, hook_server):
    base_url, token = hook_server
    pid = await repo.upsert_project(conn, "demo")
    person = await repo.upsert_person(conn, pid, "vasan", hashlib.sha256(b"dev-token").hexdigest())
    part = await repo.upsert_participant(conn, pid, person, "cc", "deep", "hooksess", [])
    d = await repo.insert_decision(conn, project_id=pid, statement="use cursor pagination",
                                   rationale="r", scope_tags=["api:orders"],
                                   owner_person_id=person, source_participant_id=part)
    await repo.insert_alert(conn, project_id=pid, target_participant_id=part,
                            target_person_id=person, kind="change", ref_id=d["id"])
    res = _run('{"session_id":"hooksess","hook_event_name":"UserPromptSubmit"}',
               {"KEEL_URL": base_url, "KEEL_TOKEN": token})
    assert res.returncode == 0
    assert "use cursor pagination" in res.stdout  # alert summary = decision statement


async def test_prompt_hook_empty_inbox_no_output(conn, db_pool, hook_server):
    base_url, token = hook_server
    pid = await repo.upsert_project(conn, "demo")
    person = await repo.upsert_person(conn, pid, "vasan", hashlib.sha256(b"dev-token").hexdigest())
    await repo.upsert_participant(conn, pid, person, "cc", "deep", "hooksess", [])
    res = _run('{"session_id":"hooksess"}', {"KEEL_URL": base_url, "KEEL_TOKEN": token})
    assert res.returncode == 0 and res.stdout.strip() == ""


def test_prompt_hook_fails_open_when_down():
    res = _run('{"session_id":"s1"}',
               {"KEEL_URL": "http://127.0.0.1:1/mcp", "KEEL_TOKEN": "dev-token"})
    assert res.returncode == 0 and res.stdout.strip() == ""
